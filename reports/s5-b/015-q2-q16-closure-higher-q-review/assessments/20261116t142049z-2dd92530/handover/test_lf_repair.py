"""Exercise exact legacy -> r2 recovery using real local Git; no network/service calls."""
import argparse,csv,hashlib,importlib.util,io,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=argparse.ArgumentParser();p.add_argument('--legacy-package',type=Path,required=True);p.add_argument('--output',type=Path);args=p.parse_args()
new=module('new_handover',ROOT/'handover.py');old=module('old_handover',args.legacy_package/'handover.py')
assert old.sha(old.ROOT/'SHA256SUMS')==new.LEGACY_PACKAGE_SHA256
old.verify_manifest(old.ROOT);new.verify_manifest(ROOT)
def git(dest,*args):return subprocess.check_output(['git','-C',str(dest),*args],text=True,stderr=subprocess.STDOUT).strip()
fixture={'studies':[{'id':'s5-b-012','stage':'s5-b','number':12,'slug':'rapid-q-screening','state':'assessed','records':[]},{'id':'s5-b-013','stage':'s5-b','number':13,'slug':'rapid-q-bounded-followup','state':'assessed','records':[]},{'id':'s5-b-014','stage':'s5-b','number':14,'slug':'targeted-q-campaign2','state':'prepared','records':[]}],'priority':['s5-b-014'],'current':{'latest_assessed_study':'s5-b-014','summary':'pending'}}
checks=[]
with tempfile.TemporaryDirectory() as td:
 dest=Path(td);git(dest,'init','-q');git(dest,'config','user.name','Local fixture');git(dest,'config','user.email','fixture@example.invalid')
 (dest/'docs/project').mkdir(parents=True);new.save(dest/'docs/project/roadmap.json',fixture);git(dest,'add','.');git(dest,'commit','-qm','fixture base');git(dest,'switch','-c',new.BRANCH)
 base=git(dest,'rev-parse','HEAD');m={'package_sha256':new.LEGACY_PACKAGE_SHA256,'base':base,'installed_at':new.stamp(),'phase':'applied'}
 old.apply(dest,m);new.save(new.marker(dest),m);git(dest,'add','.');original_patch=subprocess.check_output(['git','-C',str(dest),'diff','--cached','--binary'])
 folder=dest/m['assessment_path'];old_archive_hash=new.sha(folder/'handover/data/decision-audit-evidence.zip')
 assert any(b'\r' in f.read_bytes() for f in (folder/'handover').glob('*.csv'))
 # An altered worktree is refused before mutation or creation of repair backups.
 (folder/'README.md').write_text('unstaged user edit\n')
 try:new.upgrade_lf(dest,dict(m),new.sha(ROOT/'SHA256SUMS'))
 except RuntimeError as e:assert 'Unstaged edits' in str(e)
 else:raise AssertionError('Unstaged edit was accepted')
 git(dest,'restore','--worktree',str((folder/'README.md').relative_to(dest)))
 checks.append('Real Git recovery refuses unstaged user edits before mutation')
 fixed=new.upgrade_lf(dest,m,new.sha(ROOT/'SHA256SUMS'));backup=Path(fixed['repair_backup'])
 assert (backup/'staged.patch').read_bytes()==original_patch
 assert new.load(backup/'publication.json')['package_sha256']==new.LEGACY_PACKAGE_SHA256
 assert new.sha(backup/'assessment-0/handover/SHA256SUMS')==new.LEGACY_PACKAGE_SHA256
 assert new.sha(folder/'handover/data/decision-audit-evidence.zip')==old_archive_hash
 for name in ['SCREEN-LEDGER.csv','Q2-Q16-CLOSURE.csv','ENDPOINTS.csv']:
  before=(backup/'assessment-0/handover'/name).read_bytes();after=(folder/'handover'/name).read_bytes()
  assert b'\r' in before and b'\r' not in after
  assert list(csv.reader(io.StringIO(before.decode())))==list(csv.reader(io.StringIO(after.decode())))
 for f in [folder,dest/m['campaign_assessment_path']]:new.verify_manifest(f)
 new.verify_manifest(folder/'handover')
 assert new.load(new.marker(dest))['package_sha256']==new.sha(ROOT/'SHA256SUMS')
 checks.append('Exact legacy staged failure repaired with real Git; backups, byte-identical scientific archive, unchanged CSV cells and enclosing manifests verified')
 # Resume actual install() after repair; use explicit offline equivalents for checks unavailable here.
 original_checks=new.checks
 def offline_checks(dest,m):
  for f in (dest/'reports').rglob('SHA256SUMS'):new.verify_manifest(f.parent)
  for f in (dest/'reports').rglob('*.csv'):assert b'\r' not in f.read_bytes()
  git(dest,'add','README.md','docs','reports') if (dest/'README.md').exists() else git(dest,'add','docs','reports')
  git(dest,'diff','--cached','--check')
 new.checks=offline_checks
 try:
  a=argparse.Namespace(publication=dest,repo=dest);first=new.install(a);second=new.install(a)
  assert first['phase']==second['phase']=='staged' and first['staged']==second['staged'] and not git(dest,'diff','--name-only')
 finally:new.checks=original_checks
 checks.append('Actual install() resumes repaired state, stages cleanly and repeats idempotently; offline manifest/LF/whitespace checks substitute for unavailable project validators')
 # Existing committed state must never enter the repair path.
 bad=dict(m,phase='committed',package_sha256=new.LEGACY_PACKAGE_SHA256)
 try:new.upgrade_lf(dest,bad,new.sha(ROOT/'SHA256SUMS'))
 except RuntimeError as e:assert 'Only the exact original uncommitted' in str(e)
 else:raise AssertionError('Committed record accepted for repair')
 checks.append('Committed/different lifecycle states rejected for automatic repair')
result={'recorded_at':new.stamp(),'status':'passed','checks':checks,'limitations':['No network calls or numerical replay','Actual project_records.py and check_docs.py execute on the zbook; their complete implementation is not available in this workspace']}
if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
else:print(json.dumps(result,indent=2))
