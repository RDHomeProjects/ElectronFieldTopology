"""Real local-Git regression of the exact stopped publication; no network."""
import argparse,importlib.util,json,shutil,subprocess,tempfile
from pathlib import Path
import repair as fix
p=argparse.ArgumentParser();p.add_argument('--original-package',type=Path,required=True);a=p.parse_args();original=a.original_package.resolve()
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
pub=module('original_publication',original/'publication.py')
def git(repo,*args,check=True):return subprocess.run(['git','-C',str(repo),*args],text=True,capture_output=True,check=check)
def fixture(root):
 package=root/'package';shutil.copytree(original,package,ignore=shutil.ignore_patterns('__pycache__'));repo=root/'repo';repo.mkdir();git(repo,'init','-q','-b',fix.BRANCH);git(repo,'config','user.name','Offline Fixture');git(repo,'config','user.email','fixture@example.invalid')
 d=json.loads((package/'validation/ROADMAP.json').read_text());s=next(s for s in d['studies'] if s['id']=='s5-b-016');s['state']='assessed';s['records'].append({'role':'assessment','path':fix.load(package/'RESULTS.json')['parent_assessment'],'label':'PR79 assessed parent'})
 (repo/'docs/project').mkdir(parents=True);fix.save(repo/'docs/project/roadmap.json',d);(repo/'README.md').write_text('# Fixture\n');(repo/'untouched-sentinel.txt').write_text('preserve existing source\n');git(repo,'add','.');git(repo,'commit','-qm','fixture baseline');base=git(repo,'rev-parse','HEAD').stdout.strip()
 m={'base':base,'installed_at':fix.stamp(),'package_sha256':fix.OLD_PACKAGE,'phase':'applied','origin':'https://github.com/RDHomeProjects/ElectronFieldTopology.git'};pub.apply(repo,m);fix.save(repo/'.git'/fix.MARKER,m);git(repo,'add','.')
 return package,repo,m
checks=[]
with tempfile.TemporaryDirectory() as td:
 root=Path(td);package,repo,m=fixture(root);before=git(repo,'diff','--cached','--check',check=False)
 assert before.returncode!=0 and 'new blank line at EOF' in before.stdout
 original_head=git(repo,'rev-parse','HEAD').stdout;sentinel=fix.sha(repo/'untouched-sentinel.txt');receipt=fix.run(package,repo)
 assert git(repo,'diff','--cached','--check',check=False).returncode==0
 assert fix.sha(package/'publication.py')==fix.NEW_PUBLICATION and receipt['scientific_payloads_byte_identical']
 for n in fix.names(original)-{'publication.py','SHA256SUMS'}:assert fix.sha(package/n)==fix.sha(original/n),n
 for f in (repo/m['preparation_path']).rglob('SHA256SUMS'):fix.verify_manifest(f.parent)
 module('fixed_publication',package/'publication.py').verify()
 assert fix.load(repo/'.git'/fix.MARKER)['phase']=='applied' and git(repo,'rev-parse','HEAD').stdout==original_head and fix.sha(repo/'untouched-sentinel.txt')==sentinel
 staged=git(repo,'diff','--cached','--binary').stdout;fix.run(package,repo);assert git(repo,'diff','--cached','--binary').stdout==staged
 checks+=['Reproduced original Git staged EOF-whitespace failure','Repair passes actual git diff --cached --check','Every non-formatting original payload remains byte-identical; Python AST unchanged','All nested manifests and original package verification pass','HEAD, unrelated source and applied state preserved; repeat repair is idempotent']
with tempfile.TemporaryDirectory() as td:
 package,repo,m=fixture(Path(td));real=fix.git;failed=[False]
 def interrupted(repo,*args):
  if args==('diff','--cached','--check') and not failed[0]:failed[0]=True;raise RuntimeError('fixture interrupted after reseal')
  return real(repo,*args)
 fix.git=interrupted
 try:fix.run(package,repo)
 except RuntimeError as e:assert 'fixture interrupted' in str(e)
 else:raise AssertionError('Interruption was hidden')
 fix.git=real;assert fix.load(repo/'.git'/fix.POINTER)['phase']=='backed_up';fix.run(package,repo)
 assert fix.load(repo/'.git'/fix.POINTER)['phase']=='complete' and git(repo,'diff','--cached','--check',check=False).returncode==0
 checks.append('Interrupted resealing resumes from the saved backup without duplicating the correction')
with tempfile.TemporaryDirectory() as td:
 package,repo,m=fixture(Path(td));(package/'PLAN.json').write_text('{}\n');old=git(repo,'diff','--cached','--binary').stdout
 try:fix.run(package,repo)
 except RuntimeError:pass
 else:raise AssertionError('Modified scientific payload was accepted')
 assert git(repo,'diff','--cached','--binary').stdout==old and not (repo/'.git'/fix.POINTER).exists()
 checks.append('Changed scientific input is rejected before modification')
result={'recorded_at':fix.stamp(),'status':'passed','checks':checks,'limits':['No network call, reset or CPU/GPU analysis','Actual repository record/document checks rerun on the zbook before commit','Numerical payloads and previously declared gates/budgets are unchanged']};fix.save(fix.ROOT/'VALIDATION.json',result);print(json.dumps(result,indent=2))
