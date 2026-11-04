"""Administrative invariants and failure injection; no simulations. Apache-2.0."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import project_records as p


class RecordIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='eft-layout-controls-')
        cls.root=Path(cls.tmp.name)/'repo'
        shutil.copytree(p.ROOT,cls.root,ignore=shutil.ignore_patterns('.git','.venv','artifacts','__pycache__'))
        cls.data=json.loads((cls.root/p.REGISTRY).read_text())

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_published_reports_preserved(self):
        self.assertEqual(p.check(self.root)['protected_files'],964)

    def test_duplicate_study_rejected(self):
        d=copy.deepcopy(self.data);d['studies'].append(d['studies'][0])
        with self.assertRaisesRegex(AssertionError,'Duplicate study'):p.validate(d,self.root)

    def test_dependency_cycle_rejected(self):
        d=copy.deepcopy(self.data);d['studies'][0]['depends_on']=[d['studies'][1]['id']]
        with self.assertRaisesRegex(AssertionError,'Dependency cycle'):p.validate(d,self.root)

    def test_missing_evidence_rejected(self):
        d=copy.deepcopy(self.data);d['studies'][0]['records'][0]['path']='reports/missing.txt'
        with self.assertRaises(AssertionError):p.validate(d,self.root)

    def test_timezones_must_match(self):
        d=copy.deepcopy(self.data);d['updated_at']['melbourne']='2026-11-04T11:00:00+11:00'
        with self.assertRaises(AssertionError):p.validate(d,self.root)

    def test_generated_status_drift_rejected(self):
        path=self.root/'docs/STATUS.md';original=path.read_bytes()
        try:
            path.write_bytes(original+b'Another current priority.\n')
            with self.assertRaisesRegex(AssertionError,'navigation drift'):p.check(self.root)
        finally:path.write_bytes(original)

    def test_report_byte_change_rejected(self):
        path=self.root/'reports/s1-a/README.md';original=path.read_bytes()
        try:
            path.write_bytes(original+b'Changed result.\n')
            with self.assertRaisesRegex(AssertionError,'Changed protected bytes'):p.check(self.root)
        finally:path.write_bytes(original)

    def test_legacy_archive_corruption_rejected(self):
        path=self.root/'docs/history/layout-20261104/README.md.txt';original=path.read_bytes()
        try:
            path.write_bytes(original+b'Altered archive.\n')
            with self.assertRaisesRegex(AssertionError,'navigation archive'):p.check(self.root)
        finally:path.write_bytes(original)

    def test_new_ad_hoc_root_rejected(self):
        folder=self.root/'reports/another-run-20261104';folder.mkdir()
        try:
            (folder/'README.md').write_text('Unregistered result\n')
            with self.assertRaisesRegex(AssertionError,'Noncanonical new report'):p.check(self.root)
        finally:shutil.rmtree(folder)

    def test_canonical_record_checksums_and_registration(self):
        rel='reports/s5-b/005-boost-initialization/runs/20261104t010000z-1234abcd'
        folder=self.root/rel;folder.mkdir(parents=True)
        register=self.root/p.REGISTRY;original=register.read_bytes()
        generated={}
        try:
            record={'study_id':'s5-b-005','record_id':folder.name,'role':'measurement',
                    'recorded_at':self.data['updated_at'],'source_commit':'a'*40,'outcome':'synthetic administrative control'}
            (folder/'record.json').write_text(json.dumps(record)+'\n')
            (folder/'README.md').write_text('Synthetic administrative control, not a scientific run.\n')
            (folder/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in sorted(folder.iterdir()) if f.name!='SHA256SUMS'))
            d=copy.deepcopy(self.data)
            next(s for s in d['studies'] if s['id']=='s5-b-005')['records'].append({'role':'measurement','path':rel+'/README.md','label':'Synthetic control'})
            for name,text in p.documents(d,self.root).items():
                path=self.root/name;generated[path]=path.read_bytes();path.write_text(text)
            register.write_text(json.dumps(d)+'\n')
            p.check(self.root)
            (folder/'README.md').write_text('Deliberately damaged synthetic payload.\n')
            with self.assertRaisesRegex(AssertionError,'payload hash mismatch'):p.check(self.root)
        finally:
            register.write_bytes(original)
            for path,data in generated.items():path.write_bytes(data)
            shutil.rmtree(folder)

    def test_published_canonical_payload_cannot_be_rewritten(self):
        with tempfile.TemporaryDirectory(prefix='eft-append-control-') as tmp:
            root=Path(tmp)
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL,text=True).strip()
            git('init','--quiet');git('config','user.name','Administrative test');git('config','user.email','test@example.invalid')
            payload=root/'reports/s5-b/005-boost-initialization/runs/20261104t010000z-1234abcd/value.json'
            payload.parent.mkdir(parents=True);payload.write_text('{"value":1}\n')
            git('add','.');git('commit','--quiet','-m','Synthetic published record');base=git('rev-parse','HEAD')
            payload.write_text('{"value":2}\n')
            with self.assertRaisesRegex(AssertionError,'Published record is immutable'):p.immutable_changes(root,base)

    def test_new_superseding_assessment_can_be_appended(self):
        with tempfile.TemporaryDirectory(prefix='eft-append-control-') as tmp:
            root=Path(tmp)
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL,text=True).strip()
            git('init','--quiet');git('config','user.name','Administrative test');git('config','user.email','test@example.invalid')
            (root/'README.md').write_text('Synthetic baseline\n');git('add','.');git('commit','--quiet','-m','Synthetic baseline');base=git('rev-parse','HEAD')
            payload=root/'reports/s5-b/005-boost-initialization/assessments/20261104t010000z-1234abcd/README.md'
            payload.parent.mkdir(parents=True);payload.write_text('Synthetic superseding assessment\n');git('add','.')
            p.immutable_changes(root,base)


if __name__=='__main__':unittest.main()
