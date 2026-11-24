"""Small local fixtures only; no scientific data or remote GitHub access."""
import gzip,hashlib,json,os,sqlite3,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import inventory as inv
from common import ROOT,load,save,sha,verify_package,verify_zip,process_identity

class Checks(unittest.TestCase):
    def setup_fixture(self,home):
        repo=home/'ElectronFieldTopology-fixture';repo.mkdir();(repo/'.git').mkdir();(repo/'.venv').mkdir();(repo/'.venv/ignored').write_bytes(b'cache');(repo/'source.py').write_text('fixture source\n');(repo/'.env').write_text('not inventoried\n')
        data=repo/'artifacts/run';data.mkdir(parents=True)
        # A ZIP CRC fixture, deliberately not a scientific NumPy field.
        with zipfile.ZipFile(data/'endpoint.npz','w') as z:z.writestr('n.npy',b'fixture bytes, not an actual ndarray')
        (data/'duplicate.npz').write_bytes((data/'endpoint.npz').read_bytes())
        save(data/'FIELD-MANIFEST.json',{'fields':[{'path':'endpoint.npz','sha256':sha(data/'endpoint.npz')},{'path':'missing.npz','sha256':'0'*64}]})
        (home/'Downloads').mkdir();(home/'Downloads/evidence(1).zip').write_bytes(b'unassigned fixture')
        (home/'unrelated.txt').write_text('not a project file')
        return repo

    def fake_command(self,args,cwd=None):
        value=''
        if 'get-url' in args:value='https://github.com/RDHomeProjects/ElectronFieldTopology.git'
        elif 'rev-parse' in args:value='a'*40
        elif 'for-each-ref' in args:value='refs/heads/main '+'a'*40
        elif '--show-current' in args:value='main'
        return {'ok':True,'stdout':value,'stderr':''}

    def execute_fixture(self,home,repo,resume=None):
        destination=home/'MatterWaves-PauseInventory';pub=home/'ElectronFieldTopology-pause-publication-20261124'
        with patch.object(inv,'command',self.fake_command):return inv.run(home,repo,[],destination,pub,resume)

    def test_scope_excludes_runtime_outputs_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);repo=self.setup_fixture(home);out=self.execute_fixture(home,repo)
            with gzip.open(out/'FILES.jsonl.gz','rt') as f:rows=[json.loads(x) for x in f]
            self.assertTrue(any(x['path'].endswith('endpoint.npz') for x in rows));self.assertFalse(any('/.venv/' in x['path'] or x['path'].endswith('.env') or x['path'].endswith('unrelated.txt') for x in rows))
            self.assertEqual(len(load(out/'UNASSIGNED-DOWNLOADS.json')['files']),1);self.assertEqual(load(out/'SUMMARY.json')['errors'],0)

    def test_hash_cache_invalidated_by_source_change(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'a';p.write_bytes(b'abc');db=sqlite3.connect(root/'cache');db.execute('create table cache(path text primary key,signature text,sha256 text,crc text)')
            first=inv.hash_file(p,db,lambda *_:None);second=inv.hash_file(p,db,lambda *_:None);self.assertFalse(first[2]);self.assertTrue(second[2]);p.write_bytes(b'changed');third=inv.hash_file(p,db,lambda *_:None);self.assertFalse(third[2]);self.assertNotEqual(first[0],third[0]);db.close()

    def test_bad_zip_hash_is_retained_with_failed_crc(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'bad.npz';p.write_bytes(b'not a zip');db=sqlite3.connect(root/'cache');db.execute('create table cache(path text primary key,signature text,sha256 text,crc text)');r=inv.hash_file(p,db,lambda *_:None);self.assertEqual(r[0],sha(p));self.assertTrue(r[1].startswith('failed:'));db.close()

    def test_resume_reuses_unchanged_hashes_and_no_source_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);repo=self.setup_fixture(home);before=sha(repo/'artifacts/run/endpoint.npz');out=self.execute_fixture(home,repo);first=load(out/'SUMMARY.json');out2=self.execute_fixture(home,repo,out);second=load(out2/'SUMMARY.json');self.assertEqual(out,out2);self.assertEqual(second['cached_hashes'],first['files']);self.assertEqual(sha(repo/'artifacts/run/endpoint.npz'),before);self.assertFalse(second['full_data_uploaded'])

    def test_reference_relocation_and_duplicate_accounting(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);repo=self.setup_fixture(home);out=self.execute_fixture(home,repo);s=load(out/'SUMMARY.json');self.assertLess(s['unique_content_bytes'],s['logical_bytes']);refs=load(out/'FIELD-REFERENCES.json')['references'];self.assertEqual(refs[0]['state'],'present_at_declared_path');self.assertEqual(refs[1]['state'],'not_found_as_individual_file')
            by_hash={refs[0]['sha256']:{'example':'/relocated/field.npz'}};found,_=inv.field_references([repo/'artifacts/run/FIELD-MANIFEST.json'],{},by_hash);self.assertEqual(found[0]['state'],'present_elsewhere_same_hash')

    def test_named_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);outside=home/'outside';outside.mkdir();(home/'ElectronFieldTopology-alias').symlink_to(outside,target_is_directory=True);roots,links,_=inv.discover(home,[],set());self.assertFalse(roots);self.assertEqual(len(links),1)

    def test_live_worker_blocks_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);repo=self.setup_fixture(home);save(repo/'artifacts/run/heartbeat.json',{'pid':os.getpid(),'process_identity':process_identity(os.getpid())})
            with self.assertRaisesRegex(RuntimeError,'still alive'):self.execute_fixture(home,repo)

    def test_metadata_seal_and_restart_document(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);repo=self.setup_fixture(home);out=self.execute_fixture(home,repo);items=verify_zip(out/'inventory-evidence.zip');self.assertIn('PAUSE-AND-RESUME.md',items);self.assertNotIn('HASH-CACHE.sqlite',items);self.assertFalse(any(n.endswith('.npz') for n in items));text=(out/'PAUSE-AND-RESUME.md').read_text();self.assertIn('665',text);self.assertIn('663',text);self.assertIn('not been uploaded',text)

    def test_publication_payload_staging_without_network(self):
        import publication as pub
        def fake(repo,args,capture=False):
            if args[:3]==['git','remote','get-url']:return pub.REMOTE
            if args[:2]==['git','status']:return ''
            if args[:2]==['git','rev-parse']:return 'a'*40
            return '' if capture else None
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);repo=self.setup_fixture(home);out=self.execute_fixture(home,repo);target=home/'publication';target.mkdir();(target/'.git').mkdir();(target/'README.md').write_text('# Fixture\n')
            with patch.object(pub,'cmd',fake),patch.object(pub,'checks') as checks:state=pub.prepare(repo,target,out)
            self.assertEqual(state['phase'],'applied');checks.assert_called_once();self.assertTrue(any(k.endswith('PAUSE-AND-RESUME.md') for k in state['immutable_files']));self.assertFalse(any(k.endswith('.npz') for k in state['immutable_files']))
            for name,digest in state['immutable_files'].items():self.assertEqual(sha(target/name),digest)

    def test_origin_credentials_redacted(self):
        self.assertEqual(inv.public_url('https://fixture:credential@github.com/RDHomeProjects/ElectronFieldTopology.git?token=fixture'),'https://github.com/RDHomeProjects/ElectronFieldTopology.git')

if __name__=='__main__':unittest.main(verbosity=2)
