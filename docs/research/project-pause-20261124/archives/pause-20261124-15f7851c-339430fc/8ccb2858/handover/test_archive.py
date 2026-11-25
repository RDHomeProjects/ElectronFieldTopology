"""Offline integrity/deletion tests. No GitHub or workstation data are accessed."""
import gzip,hashlib,io,json,os,shutil,struct,subprocess,tarfile,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import archive,capsule,restore
from common import sha,save,load,ROOT

def npy(shape,descr='<f8',value=None):
    header=repr({'descr':descr,'fortran_order':False,'shape':shape}).encode();header+=b' '*((64-(10+len(header)+1)%64)%64)+b'\n';count=1
    for x in shape:count*=x
    data=struct.pack('<q',value) if value is not None else b'\0'*(8*count)
    return b'\x93NUMPY\x01\x00'+struct.pack('<H',len(header))+header+data

def checkpoint(path):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for key in ['n','old_g','old_z','direction']:z.writestr(key+'.npy',npy((2,2,2,3)))
        z.writestr('iteration.npy',npy((),'<i8',665));z.writestr('alpha.npy',npy((),'<f8')[:-8]+struct.pack('<d',0.01))

class Checks(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_partition_and_reproducible_full_member_verification(self):
        source=self.d/'data';source.write_bytes(b'payload'*1024);digest=sha(source);objects={digest:{'bytes':source.stat().st_size,'source':str(source)}};parts=capsule.partition(objects,20000)
        a=capsule.make_part(self.d/'a.gz',parts[0],objects);b=capsule.make_part(self.d/'b.gz',parts[0],objects);self.assertEqual(a['sha256'],b['sha256'])
        target=self.d/'restored';self.assertEqual(capsule.inspect_part(self.d/'a.gz',parts[0],objects,{digest:target}),[digest]);self.assertEqual(sha(target),digest)
        source.write_bytes(b'changed')
        with self.assertRaises(RuntimeError):capsule.make_part(self.d/'bad.gz',parts[0],objects)
    def test_reject_duplicate_missing_wrong_hash_and_traversal(self):
        digest=hashlib.sha256(b'x').hexdigest();part={'objects':[digest]};objects={digest:{'bytes':1}}
        for names,payload in [([],b'x'),(['objects/'+digest]*2,b'x'),(['../escape'],b'x'),(['objects/'+digest],b'y')]:
            p=self.d/'bad.gz'
            with tarfile.open(p,'w:gz') as z:
                for name in names:
                    i=tarfile.TarInfo(name);i.size=1;z.addfile(i,io.BytesIO(payload))
            with self.assertRaises(RuntimeError):capsule.inspect_part(p,part,objects,{})
    def test_checkpoint_geometry_iteration_and_conjugacy(self):
        p=self.d/'state.npz';checkpoint(p);self.assertTrue(capsule.checkpoint_check(p,{'nodes':2,'iteration':665,'optimizer_memory':True})['passed'])
        for expectation in [{'nodes':3},{'nodes':2,'iteration':663}]:
            with self.assertRaises(RuntimeError):capsule.checkpoint_check(p,expectation)
    def test_duplicate_checkpoint_roles_keep_strong_expectation(self):
        plan={'required':[{'label':'latest/cases/exact-cg/endpoint.npz','sha256':'a'},{'label':'latest/cases/exact-cg/restart-0.npz','sha256':'a'}]};self.assertEqual(archive.expected_checkpoints(plan)['a']['iteration'],665)
    def test_deletion_is_exact_and_rejects_changed_symlink_outside_and_git(self):
        root=self.d/'root';root.mkdir();p=root/'one';p.write_bytes(b'one');digest=sha(p);p.write_bytes(b'two')
        with self.assertRaises(RuntimeError):capsule.exact_unlink(p,digest,[root])
        link=root/'alias';link.symlink_to(p)
        with self.assertRaises(RuntimeError):capsule.exact_unlink(link,sha(p),[root])
        with self.assertRaises(RuntimeError):capsule.exact_unlink(p,sha(p),[self.d/'elsewhere'])
        git=root/'.git';git.mkdir();q=git/'config';q.write_bytes(b'a')
        with self.assertRaises(RuntimeError):capsule.exact_unlink(q,sha(q),[root])
        capsule.exact_unlink(p,sha(p),[root]);self.assertFalse(p.exists());self.assertTrue(link.is_symlink())
    def test_interrupted_journal_final_line_recovers_but_corrupt_completed_line_blocks(self):
        p=self.d/'DELETIONS.jsonl';p.write_bytes(b'{"path":"ok","result":"deleted"}\n{"pa')
        self.assertEqual(len(archive.journal_rows(p,repair=True)),1);self.assertTrue(p.read_bytes().endswith(b'\n'));self.assertEqual(len(list(self.d.glob('DELETIONS-interrupted-tail-*'))),1)
        p.write_bytes(b'invalid\n')
        with self.assertRaises(RuntimeError):archive.journal_rows(p,repair=True)
    def test_tracked_runtime_and_download_classification(self):
        self.assertEqual(archive.classify(Path('/home/rd/a'),{'/home/rd/a'},[]),'keep_git_tracked')
        self.assertTrue(archive.classify(Path('/home/rd/sample-browser-env/bin/python'),set(),[]).startswith('keep'))
        self.assertEqual(archive.classify(Path('/home/rd/Downloads/project.zip'),set(),[]),'delete_verified_project_download')

class EndToEnd(unittest.TestCase):
    def test_local_asset_roundtrip_restore_and_guarded_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);source=home/'source';source.mkdir();work=home/'archive';work.mkdir();store=home/'assets';store.mkdir();downloads=home/'Downloads';downloads.mkdir()
            def git(*args):return subprocess.check_output(['git',*map(str,args)],stderr=subprocess.DEVNULL,text=True).strip()
            git('init',source);git('-C',source,'config','user.email','test@example.invalid');git('-C',source,'config','user.name','Offline Test');(source/'README.md').write_text('source\n');git('-C',source,'add','README.md');git('-C',source,'commit','-m','fixture');head=git('-C',source,'rev-parse','HEAD')
            bundle=work/'git/code.bundle';bundle.parent.mkdir();git('-C',source,'bundle','create',bundle,'--all','HEAD');checkpoint(source/'endpoint.npz');(downloads/'old.zip').write_bytes(b'old project');(downloads/'unrelated.txt').write_text('keep');(source/'changed.txt').write_text('old')
            rows=[];objects={}
            for p in [source/'endpoint.npz',downloads/'old.zip',source/'changed.txt',source/'README.md']:
                digest=sha(p);objects[digest]={'bytes':p.stat().st_size,'source':str(p),'kind':'inventoried_file'};rows.append({'path':str(p),'root_id':'r' if source in p.parents else 'd','relative_path':p.name,'bytes':p.stat().st_size,'sha256':digest,'cleanup_action':'keep_git_tracked' if p.name=='README.md' else 'delete_verified_untracked_record'})
            bd=sha(bundle);objects[bd]={'bytes':bundle.stat().st_size,'source':str(bundle),'kind':'git_bundle'};record={'source':str(source),'head':head,'refs':archive.git_snapshot(source)[2],'bundle_name':bundle.name,'bundle_sha256':bd};field=sha(source/'endpoint.npz');plan={'recorded_at':{},'inventory_sha256':archive.SPEC['inventory_sha256'],'home':str(home),'tag':'offline-test','main_commit':head,'source_snapshot':str(source),'files':rows,'objects':objects,'parts':capsule.partition(objects,20000),'git':[record],'primary_git':record,'roots':[{'id':'r','path':str(source),'kind':'directory'},{'id':'d','path':str(downloads),'kind':'directory'}],'required':[{'sha256':field,'relative_to_numerical_repo':'artifacts/endpoint.npz','label':'fixture'}]}
            with gzip.open(work/'PLAN.json.gz','wt') as f:json.dump(plan,f)
            save(work/'IDENTITY.json',{'inventory_sha256':archive.SPEC['inventory_sha256'],'package_sha256':sha(ROOT/'SHA256SUMS'),'plan_sha256':sha(work/'PLAN.json.gz')});save(work/'STATUS.json',{})
            remote={'id':1,'draft':True,'html_url':'https://example.invalid/offline','assets':[]};counter=[0]
            def upload(plan,p):
                p=Path(p);digest=sha(p);found=next((a for a in remote['assets'] if a['name']==p.name),None)
                if found:self.assertEqual(found['digest'],'sha256:'+digest);return found,digest
                counter[0]+=1;a={'id':counter[0],'name':p.name,'size':p.stat().st_size,'digest':'sha256:'+digest};shutil.copyfile(p,store/p.name);remote['assets'].append(a);return a,digest
            def download(tag,name,directory):directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);shutil.copyfile(store/name,directory/name);return directory/name
            original=archive.checked
            def checked(cmd,**kw):
                if cmd[:3]==['gh','release','edit']:remote['draft']=False;return ''
                return original(cmd,**kw)
            patches=[patch.object(shutil,'disk_usage',lambda p:type('Disk',(),{'free':10**15})()),patch.object(archive,'release',lambda tag:json.loads(json.dumps(remote))),patch.object(archive,'ensure_release',lambda plan:remote),patch.object(archive,'checked_upload',upload),patch.object(archive,'download',download),patch.object(archive,'checked',checked),patch.object(archive,'expected_checkpoints',lambda p:{field:{'nodes':2,'iteration':665,'optimizer_memory':True}}),patch.object(archive,'verify_package',lambda:1),patch.object(archive.os,'geteuid',lambda:1000),patch.object(Path,'home',lambda:home)]
            from contextlib import ExitStack
            with ExitStack() as stack:
                for p in patches:stack.enter_context(p)
                # Interrupt after verified part bytes, during metadata verification.
                def interrupted_download(tag,name,directory):
                    if name=='RESTORE.md':raise RuntimeError('simulated interrupted metadata download')
                    return download(tag,name,directory)
                with patch.object(archive,'download',interrupted_download):
                    with self.assertRaises(RuntimeError):archive.upload(work,source)
                self.assertTrue(remote['draft']);self.assertTrue((work/'TRANSFER.json').exists());self.assertFalse((work/'VERIFIED-UPLOAD.json').exists())
                # Lost local retained checkpoint cache is re-downloaded on resume.
                (work/'restore-check'/('checkpoint-'+field+'.npz')).unlink()
                archive.upload(work,source);self.assertFalse(remote['draft']);archive.verify_remote(work)
                # Reuse completed upload; don't rebuild or modify source state.
                archive.upload(work,source)
                # Restore from fresh downloaded assets before removing originals.
                restored=home/'restart';restore.restore(work/'MATTER-WAVES-ARCHIVE.json.gz',work/'VERIFIED-UPLOAD.json',restored,fetch=lambda name,folder:download('offline',name,folder));self.assertEqual(sha(restored/'code/numerical/artifacts/endpoint.npz'),field)
                full=home/'full';restore.restore(work/'MATTER-WAVES-ARCHIVE.json.gz',work/'VERIFIED-UPLOAD.json',full,'full',fetch=lambda name,folder:download('offline',name,folder));self.assertEqual((full/'roots/d/old.zip').read_bytes(),b'old project')
                # Replacing even a same-size asset blocks deletion.
                remote['assets'][0]['id']+=999
                with self.assertRaises(RuntimeError):archive.cleanup(work)
                self.assertTrue((source/'endpoint.npz').exists());remote['assets'][0]['id']-=999
                (source/'changed.txt').write_text('new measurements');archive.cleanup(work)
                self.assertFalse((source/'endpoint.npz').exists());self.assertFalse((downloads/'old.zip').exists());self.assertTrue((downloads/'unrelated.txt').exists());self.assertTrue((source/'README.md').exists());self.assertTrue((source/'changed.txt').exists());self.assertEqual(load(work/'CLEANUP-RECEIPT.json')['forced_recursive_deletions'],0)
                archive.cleanup(work);archive.verify_remote(work)
                self.assertEqual(load(work/'CLEANUP-RECEIPT.json')['results']['deleted'],2)
                # Upload/status retry still works after generated staging is pruned.
                archive.upload(work,source)

if __name__=='__main__':unittest.main()
