import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import draft_api

def need(value,message):
    if not value:raise RuntimeError(message)
def save(path,value):Path(path).write_text(json.dumps(value))
def load(path):return json.loads(Path(path).read_text())

class DraftLookup(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.work=Path(self.tmp.name);self.calls=[];self.value={'id':123,'tag_name':'pause-test','draft':True};self.pages={1:[copy.deepcopy(self.value)]};self.assets=[{'id':456,'name':'part.tar.gz','size':9}]
        def api(path):
            self.calls.append(path)
            if path.startswith('repos/owner/repo/releases?'):return copy.deepcopy(self.pages.get(int(path.split('page=')[-1]),[]))
            if path=='repos/owner/repo/releases/123':return copy.deepcopy(self.value)
            if path=='repos/owner/repo/releases/123/assets?per_page=100&page=1':return copy.deepcopy(self.assets)
            raise RuntimeError('Unexpected API path; draft tag endpoint is forbidden in this test: '+path)
        self.a=SimpleNamespace(need=need,save=save,load=load,stamp=lambda:{'utc':'test','melbourne':'test'},api=api,REPO='owner/repo')
    def tearDown(self):self.tmp.cleanup()
    def test_draft_discovered_without_published_tag_endpoint_then_pinned(self):
        release=draft_api.install(self.a,self.work);got=release('pause-test');self.assertTrue(got['draft']);self.assertEqual(got['assets'],self.assets);self.assertEqual(load(self.work/'DRAFT-RELEASE-ID.json')['release_id'],123)
        self.calls=[];got=release('pause-test');self.assertEqual(got['id'],123);self.assertEqual(self.calls[0],'repos/owner/repo/releases/123');self.assertFalse(any('/tags/' in p for p in self.calls))
    def test_pagination_matches_later_draft(self):
        self.pages={1:[{'id':i+1000,'tag_name':'other-'+str(i)} for i in range(100)],2:[self.value]};release=draft_api.install(self.a,self.work);self.assertEqual(release('pause-test')['id'],123);self.assertTrue(any('page=2' in c for c in self.calls))
    def test_duplicate_tag_blocks(self):
        self.pages[1].append({'id':124,'tag_name':'pause-test','draft':True});release=draft_api.install(self.a,self.work)
        with self.assertRaises(RuntimeError):release('pause-test')
        self.assertFalse((self.work/'DRAFT-RELEASE-ID.json').exists())
    def test_not_visible_never_creates_replacement(self):
        self.pages={};release=draft_api.install(self.a,self.work)
        with self.assertRaises(draft_api.MissingRelease):release('pause-test')
        self.assertFalse((self.work/'DRAFT-RELEASE-ID.json').exists());self.assertTrue(all(c.startswith('repos/owner/repo/releases?') for c in self.calls))
    def test_pinned_identity_or_tag_change_blocks(self):
        release=draft_api.install(self.a,self.work);release('pause-test');self.value['tag_name']='different'
        with self.assertRaises(RuntimeError):release('pause-test')
        with self.assertRaises(RuntimeError):release('another-tag')
    def test_duplicate_asset_names_block(self):
        self.assets*=2;release=draft_api.install(self.a,self.work)
        with self.assertRaises(RuntimeError):release('pause-test')
    def test_existing_tag_commit_checked_without_create_or_push(self):
        draft_api.install(self.a,self.work);plan={'source_snapshot':str(self.work),'tag':'pause-test','main_commit':'a'*40};result=SimpleNamespace(returncode=0,stdout='b'*40+'\trefs/tags/pause-test\n'+'a'*40+'\trefs/tags/pause-test^{}\n')
        with patch.object(draft_api.subprocess,'run',return_value=result) as run:self.assertEqual(self.a.ensure_release(plan)['id'],123);self.assertEqual(run.call_args.args[0][3:5],['ls-remote','--tags'])
        plan['main_commit']='c'*40
        with patch.object(draft_api.subprocess,'run',return_value=result):
            with self.assertRaises(RuntimeError):self.a.ensure_release(plan)
    def test_published_release_keeps_same_pinned_identity(self):
        release=draft_api.install(self.a,self.work);release('pause-test');self.value['draft']=False;self.assertFalse(release('pause-test')['draft'])
if __name__=='__main__':unittest.main()
