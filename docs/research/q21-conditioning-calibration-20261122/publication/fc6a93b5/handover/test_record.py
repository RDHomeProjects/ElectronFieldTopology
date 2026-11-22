"""Publication/integrity controls; no production field or GitHub access invented."""
import copy,hashlib,json,os,subprocess,tempfile,unittest,zipfile,fcntl
from pathlib import Path
from unittest.mock import patch
from common import ROOT,load,save,sha,canonical
import verification as v
import publication as pub


def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True,stderr=subprocess.STDOUT).strip()

def init(repo):
    subprocess.run(['git','init','-q','--initial-branch=main',str(repo)],check=True);git(repo,'config','user.name','Local publication control');git(repo,'config','user.email','local-test@example.invalid')

def npz(path,tag=b'fixture'):
    path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_STORED) as z:z.writestr('array.npy',tag*100)
    return {'path':path.name,'sha256':sha(path),'bytes':path.stat().st_size}

class RecordControls(unittest.TestCase):
    def test_reviewed_archive_and_registered_outcomes(self):
        spec,members,sums,r=v.package();self.assertEqual(r['compact_hashes'],182);self.assertEqual(r['accepted_updates'],580);self.assertEqual(r['q21_readiness_passes'],0);self.assertEqual(r['q21_observations'],593);self.assertEqual(len(json.loads(members['FIELD-MANIFEST.json'])['fields']),52)
    def test_unsafe_compact_members_are_rejected(self):
        for name in ['../escape','/absolute','a\\b','line\nbreak']:
            with self.assertRaises(RuntimeError):v.safe_name(name)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'bad.zip'
            with zipfile.ZipFile(path,'w') as z:z.writestr('SHA256SUMS','0'*64+'  value\n');z.writestr('value','changed')
            with self.assertRaises(RuntimeError):v.archive(path)
    def test_full_field_hash_and_crc_checks(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);path=run/'state.npz';row=npz(path);r=v.check_field(run,row);self.assertEqual(r['npz_crc'],'pass')
            data=bytearray(path.read_bytes());name_size=int.from_bytes(data[26:28],'little');extra_size=int.from_bytes(data[28:30],'little');data[30+name_size+extra_size+5]^=1;path.write_bytes(data)
            with self.assertRaises(RuntimeError):v.check_field(run,row)
            row['sha256']=sha(path)
            with self.assertRaises(RuntimeError):v.check_field(run,row)
    def test_active_recorded_process_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);identity={'pid':123,'start_ticks':'fixture','boot_id':'fixture'};save(run/'heartbeat.json',{'pid':123,'process_identity':identity})
            with patch.object(v,'process_identity',return_value=identity):
                with self.assertRaises(RuntimeError):v.inactive(run)
    def test_worker_lock_prevents_concurrent_recording(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);(run/'.worker.lock').touch()
            with (run/'.worker.lock').open('r') as f:
                fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(RuntimeError):
                    with v.retained_lock(run):pass
    def test_field_verification_cache_invalidates_on_change(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);(repo/'.git').mkdir();run=repo/'run';run.mkdir();(run/'.worker.lock').touch();save(run/'status.json',{'status':'complete_pending_review'});save(run/'identity.json',{'run_id':'fixture'});(run/'evidence.zip').write_bytes(b'compact fixture');row=npz(run/'one.npz');members={'FIELD-MANIFEST.json':json.dumps({'fields':[row]}).encode()};spec={'relative_run':'run','run_id':'fixture','evidence_sha256':sha(run/'evidence.zip')};summary={'status':'fixture','new_optimizer_attempts':0}
            with patch.object(v,'package',return_value=(spec,members,{},summary)),patch.object(v,'gitdir',return_value=repo/'.git'),patch.object(v,'inactive',return_value=None),patch.object(v,'check_field',wraps=v.check_field) as check:
                first=v.local(repo,reuse=False);self.assertEqual(check.call_count,1);again=v.local(repo,reuse=True);self.assertEqual(check.call_count,1);self.assertEqual(first,again)
                st=(run/'one.npz').stat();os.utime(run/'one.npz',ns=(st.st_atime_ns,st.st_mtime_ns+1000000));v.local(repo,reuse=True);self.assertEqual(check.call_count,2)
                with (run/'one.npz').open('ab') as f:f.write(b'changed')
                with self.assertRaises(RuntimeError):v.local(repo,reuse=True)
    def test_live_plan_check_validates_pr_and_preparation_bytes(self):
        spec,members,_,summary=v.package()
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo';init(repo);prefix=pub.DOC/'preparation'/spec['handover_manifest_sha256'][:8]/'handover'
            for name in ['PLAN.json','SOURCE.json','GATES.json','engine.py','worker.py','SHA256SUMS']:
                f=repo/prefix/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(members['handover/'+name])
            git(repo,'add','.');git(repo,'commit','-qm','Synthetic source preparation');head=git(repo,'rev-parse','HEAD');pr=copy.deepcopy(spec['required_plan_pr']);pr.update(headRefOid=head,mergeCommit={'oid':head},url='synthetic-local-only');fixture=spec|{'required_plan_pr':pr}
            with patch.object(pub,'package',return_value=(fixture,members,{},summary)),patch.object(pub,'view',return_value=pr):
                self.assertEqual(pub.plan_check(repo,'HEAD')['status'],'merged_preparation_verified_on_workstation');(repo/prefix/'PLAN.json').write_text('changed\n');git(repo,'add','.');git(repo,'commit','-qm','Changed source bytes')
                with self.assertRaises(RuntimeError):pub.plan_check(repo,'HEAD')
                bad=pr|{'state':'OPEN'}
                with patch.object(pub,'view',return_value=bad):
                    with self.assertRaises(RuntimeError):pub.plan_check(repo,'HEAD')
    def test_real_git_additive_publication_and_merged_byte_verification(self):
        spec,members,_,_=v.package()
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);repo=base/'numerical';remote=base/'remote.git';target=base/'publication';init(repo)
            original=b'# Original project\n\nPreserve this introduction.\n';(repo/'README.md').write_bytes(original);(repo/'reports').mkdir();csv=repo/'reports/original.csv';csv.write_bytes(b'key,value\r\noriginal,retained\r\n');(repo/'old-chart.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Keep</text></svg>\n')
            # The original compact result is already present as if recorded by
            # the preceding package; adding the new analysis must preserve it.
            raw,_,_=pub.paths(spec)
            for n,data in members.items():
                f=repo/raw/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
            (repo/raw/'evidence.zip').write_bytes(v.EVIDENCE.read_bytes());git(repo,'add','.');git(repo,'commit','-qm','Original local fixture');original_head=git(repo,'rev-parse','HEAD');subprocess.run(['git','clone','-q','--bare',str(repo),str(remote)],check=True)
            receipt={'recorded_at':{'utc':'fixture','melbourne':'fixture'},'source_run':str(repo/'artifacts/fixture'),'evidence_sha256':spec['evidence_sha256'],'package_sha256':sha(ROOT/'SHA256SUMS'),'fields':[{'path':'synthetic.npz','sha256':'fixture-only','bytes':1,'npz_crc':'synthetic-control-only','fingerprint':{}}],'scope':'Synthetic verification receipt for local publication control only; production fields were not replayed here'}
            with patch.object(pub,'REMOTE',str(remote)),patch.object(pub,'local',return_value=receipt),patch.object(pub,'plan_check',return_value={'status':'synthetic_local_plan_control','github_connections':0}):
                state=pub.prepare(repo,target);self.assertEqual(state['phase'],'applied');self.assertEqual(pub.prepare(repo,target)['branch'],state['branch']);self.assertTrue((target/'README.md').read_bytes().startswith(original));self.assertEqual((target/'reports/original.csv').read_bytes(),csv.read_bytes());self.assertEqual((target/'old-chart.svg').read_bytes(),(repo/'old-chart.svg').read_bytes());self.assertEqual(sha(target/state['raw_path']/'evidence.zip'),spec['evidence_sha256']);self.assertTrue((target/state['review_path']/'ASSESSMENT.html').exists())
                git(target,'config','user.name','Local publication control');git(target,'config','user.email','local-test@example.invalid');git(target,'commit','-qm','Synthetic completed record rehearsal');head=git(target,'rev-parse','HEAD');count=pub.published_bytes(target,'HEAD',state['immutable_files']);self.assertEqual(count,len(state['immutable_files']))
                # A missing/wrong immutable Git blob cannot pass post-merge verification.
                wrong=dict(state['immutable_files']);first=next(iter(wrong));wrong[first]='0'*64
                with self.assertRaises(RuntimeError):pub.published_bytes(target,'HEAD',wrong)
                # Unexpected staged content is never swept into the result PR.
                (target/'unrelated.txt').write_text('preserve\n');git(target,'add','unrelated.txt')
                with self.assertRaises(RuntimeError):pub.checks(target,state)
                git(target,'restore','--staged','unrelated.txt');(target/'unrelated.txt').unlink()
                # This is a temporary local bare repository, not GitHub.
                git(target,'push','origin','HEAD:main');state.update(phase='published',commit=head);save(pub.marker(target),state);pr={'state':'MERGED','headRefOid':head,'mergeCommit':{'oid':head},'url':'synthetic-local-only'};merged=pub.finalize_merge(target,state,pr);self.assertTrue(merged['merged_verification']['all_published_bytes_match']);self.assertEqual(pub.prepare(repo,target)['phase'],'merged');self.assertEqual(git(repo,'rev-parse','HEAD'),original_head);self.assertFalse(git(repo,'status','--porcelain'));self.assertEqual((target/'reports/original.csv').read_bytes(),csv.read_bytes())
                field=target/next(iter(state['immutable_files']));field.write_bytes(b'local mutation')
                with self.assertRaises(RuntimeError):pub.working_bytes(target,state)
    def test_no_numerical_execution_entrypoint(self):
        source=(ROOT/'handover.py').read_text();self.assertIn("['verify','install','record-results','publish','merge','status']",source);self.assertNotIn('systemd-run',source);self.assertNotIn('import numpy',source)

if __name__=='__main__':unittest.main(verbosity=2)
