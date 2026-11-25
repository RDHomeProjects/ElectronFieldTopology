"""Offline fixtures only. No user's workstation or GitHub is accessed."""
import copy,gzip,hashlib,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import engine,filesystem,restore
from common import ROOT,sha,save,load

class LocalRemote:
    def __init__(self,d):self.d=d;self.d.mkdir();self.values={};self.counter=0;self.transfers=0
    def release(self,rid):return copy.deepcopy(self.values[rid])
    def ensure(self,tag,commit,workspace):
        for v in self.values.values():
            if v['tag_name']==tag:return self.release(v['id'])
        rid=max(self.values,default=10)+1;self.values[rid]={'id':rid,'tag_name':tag,'draft':True,'html_url':'https://example.invalid/'+tag,'assets':[]};return self.release(rid)
    def upload(self,rid,tag,path):
        path=Path(path);old=next((a for a in self.values[rid]['assets'] if a['name']==path.name),None)
        if old:
            assert old['digest']=='sha256:'+sha(path);return old,sha(path)
        self.counter+=1;asset={'id':self.counter,'name':path.name,'size':path.stat().st_size,'digest':'sha256:'+sha(path),'state':'uploaded'};shutil.copyfile(path,self.d/str(asset['id']));self.values[rid]['assets'].append(asset);return copy.deepcopy(asset),sha(path)
    def download(self,asset,path):self.transfers+=1;Path(path).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(self.d/str(asset['id']),path);return Path(path)
    def publish(self,rid,tag):self.values[rid]['draft']=False;return self.release(rid)

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.d=Path(self.temp.name);self.home=self.d/'home';self.home.mkdir();self.work=self.home/'MatterWaves-FinalCleanup';self.work.mkdir();self.workspace=self.home/'MatterWaves-Workspace';self.workspace.mkdir();self.remote=LocalRemote(self.d/'remote');self.repo=self.home/'ElectronFieldTopology-old';self.repo.mkdir();self.download=self.home/'Downloads';self.download.mkdir()
        def git(*args):return subprocess.check_output(['git',*map(str,args)],stderr=subprocess.DEVNULL,text=True).strip()
        self.git=git;git('init',self.repo);git('-C',self.repo,'config','user.name','Offline Test');git('-C',self.repo,'config','user.email','test@example.invalid');(self.repo/'README.md').write_bytes(b'already archived content');git('-C',self.repo,'add','README.md');git('-C',self.repo,'commit','-m','fixture');self.head=git('-C',self.repo,'rev-parse','HEAD');(self.repo/'new.bin').write_bytes(bytes(range(255))*17)
        old=self.download/'ElectronFieldTopology-old-handover';old.mkdir();(old/'kept.json').write_bytes(b'already archived content');(old/'empty').mkdir();self.old=old
        (self.download/'unrelated.txt').write_text('leave alone');env=self.home/'EFT-archive-work/.venv';env.mkdir(parents=True);(env/'pyvenv.cfg').write_text('home = /usr/bin\n');(env/'sitecode.py').write_text('rebuild me');(env/'python').symlink_to('/usr/bin/python3');self.env=env
        orbit=self.home/'Matter-Waves-orbit';orbit.mkdir();(orbit/'data').write_text('new rendering');(orbit/'link').symlink_to('data');self.orbit=orbit
        secret=self.home/'EFT-secret';secret.mkdir();(secret/'.env').write_text('PRIVATE=do-not-publish');self.secret=secret
        (self.home/'Library').mkdir();(self.home/'Library/other').write_text('other project')
        self.base_file=self.d/'base-data';self.base_file.write_bytes(b'already archived content');digest=sha(self.base_file);objects={digest:{'bytes':self.base_file.stat().st_size}};part={'name':'base-0000.tar.gz','objects':[digest]};source={digest:{'source':str(self.base_file),'bytes':self.base_file.stat().st_size}}
        from capsule import make_part
        path=self.d/part['name'];make_part(path,part,source);rid=engine.SETTINGS['base_release_id'];self.remote.values[rid]={'id':rid,'tag_name':engine.SETTINGS['base_tag'],'draft':False,'html_url':'https://example.invalid/base','assets':[]};a,d=self.remote.upload(rid,engine.SETTINGS['base_tag'],path);self.base={'objects':objects,'parts':[{**part,'asset_id':a['id'],'bytes':a['size'],'sha256':d}],'tag':engine.SETTINGS['base_tag']}
        def base_check(home,work,workspace,remote):
            base=work/'base';base.mkdir(exist_ok=True);engine.gzsave(base/'MATTER-WAVES-ARCHIVE.json.gz',self.base);m,d=remote.upload(rid,engine.SETTINGS['base_tag'],base/'MATTER-WAVES-ARCHIVE.json.gz');proof={'all_parts_downloaded_and_objects_rehashed':True,'metadata':[{'name':m['name'],'asset_id':m['id'],'bytes':m['size'],'sha256':d}]};save(base/'VERIFIED-UPLOAD.json',proof);p,d=remote.upload(rid,engine.SETTINGS['base_tag'],base/'VERIFIED-UPLOAD.json');save(base/'PROOF-ASSET.json',{'name':p['name'],'asset_id':p['id'],'bytes':p['size'],'sha256':d});return self.base
        self.patches=[patch.object(engine,'workspace_prepare',return_value=self.head),patch.object(engine,'base_check',side_effect=base_check),patch.object(engine.shutil,'disk_usage',lambda p:type('Disk',(),{'free':10**15})()),patch.dict(engine.SETTINGS,{'chunk_bytes':256,'part_bytes':30000})]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def run_archive(self):
        plan=engine.scan(self.home,self.work,self.workspace,self.remote);engine.archive(self.work,self.remote);return plan
    def test_full_preservation_restore_and_folder_removal(self):
        plan=self.run_archive();self.assertTrue(any(f['storage']=='base' for r in plan['roots'] for f in r['files']));self.assertTrue(any(f['storage']=='rebuildable' for r in plan['roots'] for f in r['files']));self.assertTrue(plan['git']);self.assertGreater(len(plan['parts']),0)
        engine.cleanup(self.work,self.remote);self.assertFalse(self.repo.exists());self.assertFalse(self.old.exists());self.assertFalse(self.env.parent.exists());self.assertFalse(self.orbit.exists());self.assertTrue(self.secret.exists());self.assertTrue((self.download/'unrelated.txt').exists());self.assertTrue(self.workspace.exists());self.assertTrue((self.home/'Library/other').exists())
        report=load(self.work/'CLEANUP-RECEIPT.json');self.assertEqual(report['root_count_removed'],4);self.assertEqual(len(report['retained_items']),1);self.assertEqual(report['forced_recursive_deletions'],0)
        restored=self.d/'restored';restore.restore(self.work/'RESIDUAL-MANIFEST.json.gz',self.work/'VERIFIED-SUPPLEMENT.json',self.work/'base/MATTER-WAVES-ARCHIVE.json.gz',restored,remote=self.remote)
        repo_id=next(r['id'] for r in plan['roots'] if r['path']==str(self.repo));restored_repo=restored/'roots'/repo_id;self.assertEqual((restored_repo/'new.bin').read_bytes(),bytes(range(255))*17);self.assertEqual(self.git('-C',restored_repo,'rev-parse','HEAD'),self.head)
        orbit_id=next(r['id'] for r in plan['roots'] if r['path']==str(self.orbit));self.assertEqual((restored/'roots'/orbit_id/'link').read_text(),'new rendering')
        # Neither repeated verification nor repeated cleanup needs original folders.
        engine.archive(self.work,self.remote);engine.cleanup(self.work,self.remote);self.assertEqual(load(self.work/'CLEANUP-RECEIPT.json')['files_and_links_removed'],report['files_and_links_removed'])
    def test_missing_or_replaced_remote_asset_blocks_all_deletion(self):
        plan=self.run_archive();proof=load(self.work/'VERIFIED-SUPPLEMENT.json');self.remote.values[proof['release_id']]['assets'][0]['id']+=999
        with self.assertRaises(RuntimeError):engine.cleanup(self.work,self.remote)
        self.assertTrue(self.repo.exists());self.assertTrue(self.old.exists())
    def test_changed_and_new_files_leave_entire_root_in_place(self):
        self.run_archive();(self.repo/'new.bin').write_bytes(b'new work after archive');(self.old/'new-note.txt').write_text('keep this');engine.cleanup(self.work,self.remote);self.assertEqual((self.repo/'new.bin').read_bytes(),b'new work after archive');self.assertTrue((self.repo/'.git').exists());self.assertTrue((self.old/'new-note.txt').exists());self.assertGreaterEqual(len(load(self.work/'CLEANUP-RECEIPT.json')['retained_items']),3)
    def test_interrupted_publish_resumes_without_reupload_or_deletion(self):
        plan=engine.scan(self.home,self.work,self.workspace,self.remote)
        with patch.object(self.remote,'publish',side_effect=RuntimeError('interrupted publish')):
            with self.assertRaises(RuntimeError):engine.archive(self.work,self.remote)
        self.assertTrue((self.work/'PROOF-ASSET.json').exists());self.assertTrue(self.repo.exists())
        with self.assertRaises(RuntimeError):engine.cleanup(self.work,self.remote)
        engine.archive(self.work,self.remote);engine.verify_remote(self.work,self.remote)
        self.assertTrue(self.repo.exists())
    def test_publication_staging_is_repeatable_and_matches_git_index(self):
        import publication,transport
        self.git('clone',self.repo,self.workspace)
        self.run_archive();engine.cleanup(self.work,self.remote);pub=self.work/'publication';original_cmd=publication.cmd
        def cmd(repo,args,capture=False):
            if args[:3]==['git','fetch','origin']:
                args=['git','fetch',str(self.workspace),'HEAD:refs/remotes/origin/main']
            return original_cmd(repo,args,capture)
        def checks(repo,state):
            staged=set(self.git('-C',repo,'diff','--cached','--name-only').splitlines());self.assertLessEqual(staged,set(state['stage_paths']));self.git('-C',repo,'diff','--cached','--check');publication.verify_bytes(repo,'',state['immutable_files'])
        with patch.object(transport,'Remote',return_value=self.remote),patch.object(publication,'cmd',side_effect=cmd),patch.object(publication,'checks',side_effect=checks):
            state=publication.prepare(self.workspace,pub,self.work);again=publication.prepare(self.workspace,pub,self.work);self.assertEqual(state['immutable_files'],again['immutable_files']);self.assertEqual(state['phase'],'applied')
    def test_scoped_discovery_preserves_controls_unrelated_and_git_recovery_parent(self):
        parent=self.home/'git-recovery';parent.mkdir();(parent/'unrelated').mkdir();(parent/'ElectronFieldTopology-recovered').mkdir();paths,outside=filesystem.discover(self.home,engine.SETTINGS,self.work,self.workspace);self.assertIn(parent/'ElectronFieldTopology-recovered',paths);self.assertNotIn(parent,paths);self.assertNotIn(self.work,paths);self.assertNotIn(self.workspace,paths);self.assertNotIn(self.home/'Library',paths)
    def test_credential_and_external_link_roots_blocked(self):
        external=self.home/'Matter-Waves-external';external.mkdir();(external/'link').symlink_to(self.home/'Library/other');root,objects=filesystem.scan_root(external,'r',{},256);self.assertTrue(root['blocked']);root,_=filesystem.scan_root(self.secret,'s',{},256);self.assertTrue(root['blocked']);self.assertFalse(root['files'])
    def test_interrupted_rename_resumes_from_known_quarantine(self):
        plan=self.run_archive();root=next(r for r in plan['roots'] if r['path']==str(self.old));q=self.work/'quarantine';q.mkdir();self.old.rename(q/root['id']);engine.cleanup(self.work,self.remote);self.assertFalse((q/root['id']).exists());self.assertFalse(self.old.exists())
    def test_partial_unlink_without_receipt_is_reported_and_resumed(self):
        plan=self.run_archive();root=next(r for r in plan['roots'] if r['path']==str(self.old));q=self.work/'quarantine';q.mkdir();self.old.rename(q/root['id']);(q/root['id']/'kept.json').unlink();engine.cleanup(self.work,self.remote);self.assertFalse((q/root['id']).exists());self.assertIn('already_absent_after_verified_quarantine',(self.work/'DELETIONS.jsonl').read_text())
    def test_setup_launcher_survives_removal_of_downloads_package(self):
        import handover
        source=self.download/'ElectronFieldTopology-cleanup-package';shutil.copytree(ROOT,source,ignore=shutil.ignore_patterns('__pycache__'));control=self.home/'retained-launcher'
        with patch.object(handover,'ROOT',source):handover.setup(control)
        shutil.rmtree(source)
        p=subprocess.run(['bash',str(control/'RUN.sh'),'verify'],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('package verified',p.stdout)
    def test_git_authorization_configuration_retained_without_upload(self):
        config=self.repo/'.git/config';config.write_text(config.read_text()+'\n[http]\n    extraheader = Authorization: basic PRIVATE_FIXTURE\n');root,objects=filesystem.scan_root(self.repo,'r',{},256);self.assertTrue(any('Credential-bearing' in x for x in root['blocked']));self.assertFalse(any(x['path']==str(config) for x in root['files']))
    def test_chunk_geometry_and_corruption_rejected(self):
        plan=engine.scan(self.home,self.work,self.workspace,self.remote);part=plan['parts'][0];path=self.work/'part-cache/test.gz';engine.make_part(path,part,plan['objects']);from capsule import inspect_part
        inspect_part(path,part,plan['objects'],{});source=Path(plan['objects'][part['objects'][0]]['source']);source.write_bytes(source.read_bytes()+b'changed')
        with self.assertRaises(RuntimeError):engine.make_part(path,part,plan['objects'])

if __name__=='__main__':unittest.main()
