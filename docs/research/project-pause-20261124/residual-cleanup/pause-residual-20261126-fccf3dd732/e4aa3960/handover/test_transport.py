import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from transport import Remote,asset_matches
from common import sha

class Transport(unittest.TestCase):
    def test_release_listing_paginates_and_preserves_draft(self):
        r=Remote('owner/repo');calls=[]
        def api(path):
            calls.append(path)
            if path.endswith('/releases/7'):return {'id':7,'tag_name':'t','draft':True}
            if path.endswith('page=1'):return [{'id':i,'name':'a'+str(i)} for i in range(100)]
            return [{'id':101,'name':'last'}]
        with patch.object(r,'api',side_effect=api):result=r.release(7)
        self.assertTrue(result['draft']);self.assertEqual(len(result['assets']),101);self.assertTrue(any('page=2' in c for c in calls))
    def test_draft_found_without_published_by_tag_endpoint(self):
        r=Remote('owner/repo')
        with patch.object(r,'api',return_value=[{'id':7,'tag_name':'t','draft':True}]) as api,patch.object(r,'release',return_value={'id':7}):self.assertEqual(r.find_release('t')['id'],7);self.assertNotIn('/tags/',api.call_args.args[0])
    def test_duplicate_release_blocks(self):
        r=Remote('owner/repo')
        with patch.object(r,'api',return_value=[{'id':7,'tag_name':'t'},{'id':8,'tag_name':'t'}]):
            with self.assertRaises(RuntimeError):r.find_release('t')
    def test_existing_asset_size_or_digest_conflict_blocks_without_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'m.gz';p.write_bytes(b'one');r=Remote('owner/repo');value={'tag_name':'t','assets':[{'name':'m.gz','id':9,'size':3,'state':'uploaded','digest':'sha256:'+'0'*64}]}
            with patch.object(r,'release',return_value=value),patch('transport.subprocess.run') as run:
                with self.assertRaises(RuntimeError):r.upload(7,'t',p)
                run.assert_not_called()
    def test_422_collision_reused_when_size_digest_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'m.gz';p.write_bytes(b'one');r=Remote('owner/repo');asset={'name':'m.gz','id':9,'size':3,'state':'uploaded','digest':'sha256:'+sha(p)}
            with patch.object(r,'release',side_effect=[{'tag_name':'t','assets':[]},{'tag_name':'t','assets':[asset]}]),patch('transport.subprocess.run',return_value=SimpleNamespace(returncode=1,stderr='HTTP 422 name already exists',stdout='')) as run:
                got,digest=r.upload(7,'t',p);self.assertEqual(got['id'],9);self.assertEqual(digest,sha(p));self.assertNotIn('--clobber',run.call_args.args[0])
    def test_auth_failure_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'m';p.write_bytes(b'one');r=Remote('owner/repo')
            with patch.object(r,'release',return_value={'tag_name':'t','assets':[]}),patch('transport.subprocess.run',return_value=SimpleNamespace(returncode=1,stderr='HTTP 401 Bad credentials',stdout='')):
                with self.assertRaisesRegex(RuntimeError,'401'):r.upload(7,'t',p)
    def test_asset_id_and_digest_replacement_block(self):
        expected={'name':'a','asset_id':7,'bytes':3,'sha256':'a'*64};actual={'name':'a','id':8,'size':3,'digest':'sha256:'+'a'*64}
        with self.assertRaises(RuntimeError):asset_matches(actual,expected)
        actual['id']=7;actual['digest']='sha256:'+'b'*64
        with self.assertRaises(RuntimeError):asset_matches(actual,expected)
    def test_publish_keeps_release_identity(self):
        r=Remote('owner/repo')
        with patch.object(r,'release',side_effect=[{'id':7,'tag_name':'t','draft':True},{'id':7,'tag_name':'t','draft':False}]),patch.object(r,'api',return_value={}) as api:self.assertFalse(r.publish(7,'t')['draft']);self.assertEqual(api.call_args.kwargs['fields']['draft'],False)
if __name__=='__main__':unittest.main()
