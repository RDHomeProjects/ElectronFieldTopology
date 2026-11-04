"""Independent archival roundtrip and failure controls. No real remote writes or physics."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

import workstation_archive as a


class FakeGitHub:
    location=None
    fail_after=None
    uploads=0
    def __init__(self,repo,tag):self.repo=repo;self.tag=tag;self.root=self.location/tag
    def ensure(self,target,notes):
        self.root.mkdir(parents=True,exist_ok=True)
        p=self.root/'release.json'
        if p.exists():a.need(a.load(p)['target']==target,'Existing release target differs')
        else:a.save(p,{'target':target,'draft':True})
    def upload(self,path,tmp):
        dest=self.root/path.name
        if dest.exists():a.need(a.digest(dest)==a.digest(path),'Existing asset differs');return
        if self.fail_after is not None and self.uploads>=self.fail_after:raise ValueError('Simulated network interruption')
        type(self).uploads+=1;shutil.copy2(path,dest)
    def download(self,name,folder,expected=None):
        folder.mkdir(parents=True,exist_ok=True);dest=folder/name
        shutil.copy2(self.root/name,dest)
        if expected:a.need(a.digest(dest)==expected,'Downloaded release asset SHA-256 mismatch')
        return dest
    def publish(self):
        d=a.load(self.root/'release.json');d['draft']=False;a.save(self.root/'release.json',d)


class Archives(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='eft-archive-control-')
        self.root=Path(self.tmp.name);self.home=self.root/'home';self.home.mkdir();(self.home/'Downloads').mkdir()
        self.project=self.home/'ElectronFieldTopology-lowq-motion';self.project.mkdir()
        self.work=self.root/'work'
        self.extra=self.root/'consolidated-workspace';self.extra.mkdir();(self.extra/'additional.bin').write_bytes(b'Explicitly selected extra source\n')
        self.real=a.GitHub;a.GitHub=FakeGitHub;FakeGitHub.location=self.root/'remote';FakeGitHub.fail_after=None;FakeGitHub.uploads=0
        self.output=io.StringIO();self.redirect=contextlib.redirect_stdout(self.output);self.redirect.__enter__()
        self.git('init','--quiet');self.git('config','user.name','Archive control');self.git('config','user.email','control@example.invalid')
        (self.project/'.gitignore').write_text('.venv/\n__pycache__/\nartifacts/\n')
        (self.project/'source.py').write_text('baseline = 1\n')
        self.git('add','.');self.git('commit','--quiet','-m','Synthetic archival control')
        (self.project/'source.py').write_text('staged = 2\n');self.git('add','source.py')
        (self.project/'source.py').write_text('working = 3\n')
        (self.project/'.venv').mkdir();(self.project/'.venv'/'cache.bin').write_bytes(b'REBUILDABLE')
        (self.project/'artifacts').mkdir();self.binary=self.project/'artifacts/final.npz'
        self.binary.write_bytes(bytes(range(256))*5000);self.binary.chmod(0o640)
        (self.project/'empty').mkdir()
        self.orphan=self.git('hash-object','-w','--stdin',input=b'Unreachable synthetic research blob\n').stdout.decode().strip()
        (self.home/'Downloads'/'ElectronFieldTopology-handoff.zip').write_bytes(b'Synthetic handoff fixture; not a scientific ZIP.\n')
    def tearDown(self):
        self.redirect.__exit__(None,None,None);a.GitHub=self.real;self.tmp.cleanup()
    def git(self,*args,input=None):
        return subprocess.run(['git','-C',str(self.project),*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    def inventory(self):return a.inventory(self.home,self.work,[self.extra])
    def complete(self):
        s=self.inventory();a.archive(s,a.REPO,a.TARGET,a.MIB);return s
    def test_inventory_is_read_only_and_counts_ignored_fields(self):
        before=self.git('status','--porcelain=v1').stdout;index=a.git_state(self.project)['index_sha256']
        s=self.inventory();d=a.load(s/'inventory.json');p=next(r for r in d['roots'] if r['name']==self.project.name)
        self.assertEqual(p['field_files'],1);self.assertIn('.venv',p['scan']['excluded'])
        self.assertEqual(before,self.git('status','--porcelain=v1').stdout)
        self.assertEqual(index,a.git_state(self.project)['index_sha256'])
    def test_full_remote_roundtrip_restores_data_modes_and_all_git_objects(self):
        s=self.complete();out=self.root/'restored';a.restore(s/'CATALOG.json',out,None)
        r=out/'home'/self.project.name
        self.assertEqual((r/'artifacts/final.npz').read_bytes(),self.binary.read_bytes())
        self.assertEqual(stat.S_IMODE((r/'artifacts/final.npz').stat().st_mode),0o640)
        self.assertEqual((r/'source.py').read_bytes(),(self.project/'source.py').read_bytes())
        self.assertTrue((r/'empty').is_dir());self.assertFalse((r/'.venv').exists())
        self.assertEqual(a.git_state(r),a.git_state(self.project))
        self.assertEqual(a.git(r,'cat-file','blob',self.orphan).stdout,b'Unreachable synthetic research blob\n')
        extras=list((out/'extra').glob('*/consolidated-workspace/additional.bin'))
        self.assertEqual(len(extras),1);self.assertEqual(extras[0].read_bytes(),(self.extra/'additional.bin').read_bytes())
        d=a.load(s/'ARCHIVE.json');self.assertTrue(all(p['bytes']<=a.MIB for x in d['roots'] for p in x['parts']))
    def test_changed_source_is_not_archived(self):
        s=self.inventory();self.binary.write_bytes(b'Changed after inventory')
        with self.assertRaisesRegex(ValueError,'changed since inventory'):a.archive(s,a.REPO,a.TARGET,a.MIB)
        self.assertEqual(self.binary.read_bytes(),b'Changed after inventory')
    def test_secret_filename_blocks_publication_before_release_creation(self):
        (self.project/'.env').write_text('synthetic=not-a-secret\n');s=self.inventory()
        with self.assertRaisesRegex(ValueError,'blockers'):a.archive(s,a.REPO,a.TARGET,a.MIB)
        self.assertFalse(FakeGitHub.location.exists())
    def test_external_symlink_blocks_publication(self):
        (self.project/'linked').symlink_to(self.root,target_is_directory=True);s=self.inventory()
        with self.assertRaisesRegex(ValueError,'blockers'):a.archive(s,a.REPO,a.TARGET,a.MIB)
    def test_network_interruption_resumes_without_clobbering_assets(self):
        s=self.inventory();FakeGitHub.fail_after=1
        with self.assertRaisesRegex(ValueError,'network interruption'):a.archive(s,a.REPO,a.TARGET,a.MIB)
        existing={p.name:p.read_bytes() for p in FakeGitHub.location.rglob('*.json')}
        FakeGitHub.fail_after=None;a.archive(s,a.REPO,a.TARGET,a.MIB)
        for name,data in existing.items():
            if name!='release.json':self.assertEqual(next(FakeGitHub.location.rglob(name)).read_bytes(),data)
        self.assertEqual(a.load(s/'VERIFIED.json')['status'],'all_remote_bytes_verified')
    def test_completed_archive_rerun_does_not_replace_master(self):
        s=self.complete();before=(s/'ARCHIVE.json').read_bytes();a.archive(s,a.REPO,a.TARGET,a.MIB)
        self.assertEqual(before,(s/'ARCHIVE.json').read_bytes())
    def test_remote_corruption_invalidates_receipt_and_blocks_cleanup(self):
        s=self.complete();catalog=a.load(s/'CATALOG.json');idx=a.load(s/'ARCHIVE.json')
        p=FakeGitHub.location/catalog['tag']/idx['roots'][0]['parts'][0]['name'];p.write_bytes(b'Corrupt remote bytes')
        with self.assertRaises(ValueError):a.cleanup_plan(s)
        self.assertFalse((s/'VERIFIED.json').exists());self.assertFalse((s/'CLEANUP-REVIEW.json').exists())
    def test_cleanup_review_retains_sources_and_flags_later_changes(self):
        s=self.complete();self.binary.write_bytes(b'New local result after archival')
        a.cleanup_plan(s);d=a.load(s/'CLEANUP-REVIEW.json')
        self.assertTrue(any(r['status'].startswith('KEEP_SOURCE_CHANGED') for r in d['roots']))
        self.assertFalse(d['deletion_performed']);self.assertEqual(self.binary.read_bytes(),b'New local result after archival')
    def test_restore_refuses_existing_directory(self):
        s=self.complete();out=self.root/'existing';out.mkdir();(out/'keep').write_text('Keep me')
        with self.assertRaisesRegex(ValueError,'new directory'):a.restore(s/'CATALOG.json',out,None)
        self.assertEqual((out/'keep').read_text(),'Keep me')
    def test_traversal_member_is_rejected(self):
        import tarfile
        raw=io.BytesIO()
        with tarfile.open(fileobj=raw,mode='w') as tar:
            t=tarfile.TarInfo('../escape');t.size=1;tar.addfile(t,io.BytesIO(b'x'))
        raw.seek(0)
        m={'location':'home','name':'safe','directories':[],'git_locations':[],'files':[]}
        with self.assertRaisesRegex(ValueError,'Unsafe archive member'):a.verify_tar(raw,m)
    def test_linked_worktree_restores_as_standalone_git_store(self):
        linked=self.home/'ElectronFieldTopology-linked'
        self.git('worktree','add','--quiet','--detach',str(linked),'HEAD')
        s=self.complete();out=self.root/'restore-linked';a.restore(s/'CATALOG.json',out,None)
        r=out/'home'/linked.name
        self.assertEqual(a.git_state(r),a.git_state(linked))


if __name__=='__main__':unittest.main()
