import hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import asset_api

def need(value,message):
    if not value:raise RuntimeError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class AssetRepair(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.path=self.d/'MATTER-WAVES-ARCHIVE.json.gz';self.path.write_bytes(b'current manifest');self.remote=self.path.read_bytes();self.asset={'id':11,'name':self.path.name,'size':len(self.remote),'state':'uploaded','digest':'sha256:'+sha(self.path)};self.list_calls=0;self.uploads=[];self.api_calls=[];self.visible=True;self.error=None;self.replace_during_compare=False
        def checked(cmd,**kwargs):
            if cmd[:2]==['gh','api']:self.api_calls.append(cmd);return '{}'
            self.uploads.append(cmd)
            if self.error:
                self.visible=True
                raise RuntimeError(self.error)
            self.visible=True;return 'success'
        def release(tag):
            self.list_calls+=1;asset=dict(self.asset)
            if self.replace_during_compare and self.list_calls>1:asset['id']=12
            return {'assets':[asset] if self.visible else []}
        self.a=SimpleNamespace(need=need,sha=sha,checked=checked,REPO='owner/repo',save=lambda p,v:Path(p).write_text(json.dumps(v)),release=release,log=lambda *a,**k:None,stamp=lambda:{'utc':'test','melbourne':'test'})
        self.audit=asset_api.install(self.a,self.d);self.plan={'tag':'pause'}
        def run(cmd,stdout=None,stderr=None):stdout.write(self.remote);return SimpleNamespace(returncode=0,stderr=b'')
        self.runner=patch.object(asset_api.subprocess,'run',side_effect=run);self.runner.start();self.sleeper=patch.object(asset_api.time,'sleep');self.sleeper.start()
    def tearDown(self):self.runner.stop();self.sleeper.stop();self.tmp.cleanup()
    def test_existing_asset_downloaded_and_reused_without_upload(self):
        asset,digest=self.a.checked_upload(self.plan,self.path);self.assertEqual(asset['id'],11);self.assertEqual(digest,sha(self.path));self.assertEqual(self.uploads,[]);self.assertTrue(json.loads((self.d/'ASSET-COMPARISONS.jsonl').read_text())['download_comparison_passed'])
    def test_422_collision_reconciles_and_reuses_exact_bytes(self):
        self.visible=False;self.error='HTTP 422 ReleaseAsset.name already exists';self.a.checked_upload(self.plan,self.path);self.assertEqual(len(self.uploads),1);self.assertNotIn('--clobber',self.uploads[0]);self.assertEqual(json.loads((self.d/'ASSET-COMPARISONS.jsonl').read_text())['reason'],'duplicate-name response reconciled')
    def test_new_upload_confirmed_by_download(self):
        self.visible=False;self.a.checked_upload(self.plan,self.path);self.assertEqual(len(self.uploads),1)
    def test_different_bytes_same_size_without_server_digest_block(self):
        self.asset.pop('digest');self.remote=b'X'*self.asset['size']
        with self.assertRaisesRegex(RuntimeError,'bytes differ'):self.a.checked_upload(self.plan,self.path)
        self.assertFalse((self.d/'ASSET-COMPARISONS.jsonl').exists());self.assertEqual(self.uploads,[])
    def test_wrong_server_digest_blocks(self):
        self.asset['digest']='sha256:'+'0'*64
        with self.assertRaisesRegex(RuntimeError,'SHA256 differs'):self.a.checked_upload(self.plan,self.path)
    def test_starter_asset_is_kept_and_blocks(self):
        self.asset['state']='starter'
        with self.assertRaisesRegex(RuntimeError,'incomplete'):self.a.checked_upload(self.plan,self.path)
        self.assertEqual(self.uploads,[])
    def test_401_is_not_retried_as_collision(self):
        self.visible=False;self.error='HTTP 401 Bad credentials'
        with self.assertRaisesRegex(RuntimeError,'401'):self.a.checked_upload(self.plan,self.path)
        self.assertEqual(len(self.uploads),1);self.assertEqual(self.list_calls,1)
    def test_replaced_asset_blocks_after_download(self):
        self.replace_during_compare=True
        with self.assertRaisesRegex(RuntimeError,'changed during'):self.a.checked_upload(self.plan,self.path)
    def test_read_only_audit_uses_no_upload(self):
        self.audit(self.plan);self.assertEqual(self.uploads,[])
    def test_cache_bypass_headers(self):
        self.a.api('repos/owner/repo/releases/1');self.assertIn('Cache-Control: no-cache',self.api_calls[0]);self.assertIn('Pragma: no-cache',self.api_calls[0])
if __name__=='__main__':unittest.main()
