"""Remove one EOF blank line and reseal the stopped, unpublished preparation."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,uuid
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
OLD_PACKAGE='727420c970f18a5dabbc0942866d3818d90bd9ea156dc979bf30df0faf6c3949'
OLD_PUBLICATION='35218a2a21f93c0cf07bf089f737e2153a476ddb85ccb7942caa0b5b68ccd2e8'
NEW_PUBLICATION='d85e8f9c466dd655b17b3c5814f07922fc54ed61d7dd0249ac7a90cd19acbe73'
BRANCH='work/adaptive-q17-q32-screen-20261117'
MARKER='adaptive-q17-q32-publication.json'
POINTER='adaptive-eof-format-repair.json'
def stamp():
 n=datetime.now(timezone.utc);return {'utc':n.isoformat(),'melbourne':n.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def log(message,**kw):print(json.dumps({'recorded_at':stamp(),'message':message,**kw}),flush=True)
def need(x,message):
 if not x:raise RuntimeError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,x):
 p=Path(p);tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(x,indent=2)+'\n');tmp.replace(p)
def names(root):return {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
def manifest(root):
 (root/'SHA256SUMS').write_text(''.join(sha(root/n)+'  '+n+'\n' for n in sorted(names(root)-{'SHA256SUMS'})))
def verify_manifest(root):
 seen=set()
 for line in (root/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);q=PurePosixPath(n);need(not q.is_absolute() and '..' not in q.parts and n not in seen and sha(root/n)==h,'Checksum differs: '+n);seen.add(n)
 need(seen==names(root)-{'SHA256SUMS'},'Checksum coverage differs: '+str(root))
def git(repo,*args):
 argv=['git','-C',str(repo),*map(str,args)];log('Command',argv=argv);r=subprocess.run(argv,capture_output=True)
 need(r.returncode==0,'Command failed: '+repr(argv)+'\n'+r.stderr.decode(errors='replace')+r.stdout.decode(errors='replace'))
 return r.stdout
def validate_unchanged(root,backup):
 need(names(root)==names(backup),'Package members changed outside the repair')
 for n in names(backup)-{'publication.py','SHA256SUMS'}:need(sha(root/n)==sha(backup/n),'Original payload changed outside formatting repair: '+n)
 need(sha(root/'publication.py') in (OLD_PUBLICATION,NEW_PUBLICATION),'Unexpected publication helper content')

def run(package,repo):
 verify_manifest(ROOT);package=package.resolve();repo=repo.resolve();marker=repo/'.git'/MARKER;pointer=repo/'.git'/POINTER
 need(marker.is_file(),'Stopped publication marker is absent')
 if pointer.exists():
  state=load(pointer);need(state['repair_package_sha256']==sha(ROOT/'SHA256SUMS') and state['package']==str(package),'This repair pointer belongs to different inputs')
  if state['phase']=='complete':
   verify_manifest(package);need(sha(package/'publication.py')==NEW_PUBLICATION and load(marker)['package_sha256']==sha(package/'SHA256SUMS'),'Completed repair changed')
   verify_manifest(Path(state['preparation']));log('Formatting repair already complete',preparation=state['preparation']);return state
 else:
  m=load(marker);need(m['phase']=='applied' and m['package_sha256']==OLD_PACKAGE and not m.get('pr') and not m.get('commit'),'Repair accepts only the original uncommitted applied preparation')
  need(not (repo/'.git/adaptive-last-run.json').exists(),'A screening run already exists; preserve its identity')
  need(git(repo,'rev-parse','HEAD').decode().strip()==m['base'] and git(repo,'branch','--show-current').decode().strip()==BRANCH,'Stopped checkout HEAD/branch changed')
  need(not git(repo,'diff','--name-only').strip(),'Unstaged changes present; preserve them')
  verify_manifest(package);need(sha(package/'SHA256SUMS')==OLD_PACKAGE and sha(package/'publication.py')==OLD_PUBLICATION,'Original extracted package differs')
  cfg=load(package/'RESULTS.json');rel=Path(m['preparation_path']);need(not rel.is_absolute() and '..' not in rel.parts and rel.name==cfg['record_id'],'Preparation identity/path differs')
  preparation=repo/rel;verify_manifest(preparation);verify_manifest(preparation/'handover')
  need(sha(preparation/'handover/SHA256SUMS')==OLD_PACKAGE and load(preparation/'record.json')['handover_sha256']==OLD_PACKAGE,'Staged preparation differs from the original package')
  backup=repo/'.git'/('before-adaptive-eof-repair-'+uuid.uuid4().hex[:8]);backup.mkdir()
  shutil.copytree(package,backup/'package-before',ignore=shutil.ignore_patterns('__pycache__'));shutil.copytree(preparation,backup/'preparation-before',ignore=shutil.ignore_patterns('__pycache__'));shutil.copy2(marker,backup/'publication-marker.json');(backup/'staged.patch').write_bytes(git(repo,'diff','--cached','--binary'))
  state={'recorded_at':stamp(),'phase':'backed_up','package':str(package),'publication':str(repo),'preparation':str(preparation),'relative_preparation':rel.as_posix(),'backup':str(backup),'repair_package_sha256':sha(ROOT/'SHA256SUMS'),'repair_script_sha256':sha(__file__),'original_package_sha256':OLD_PACKAGE};save(pointer,state)
 backup=Path(state['backup']);preparation=Path(state['preparation']);original=backup/'package-before';verify_manifest(original);need(sha(original/'SHA256SUMS')==OLD_PACKAGE,'Repair backup differs')
 need(git(repo,'rev-parse','HEAD').decode().strip()==load(backup/'publication-marker.json')['base'],'Publication was committed or HEAD changed during repair')
 validate_unchanged(package,original);validate_unchanged(preparation/'handover',original)
 before=(original/'publication.py').read_bytes();after=before.rstrip()+b'\n';need(hashlib.sha256(after).hexdigest()==NEW_PUBLICATION,'Unexpected formatting transformation')
 # Prove the transformation changes no executable Python syntax.
 import ast
 need(ast.dump(ast.parse(before))==ast.dump(ast.parse(after)),'Formatting repair changes Python syntax')
 (package/'publication.py').write_bytes(after);manifest(package);verify_manifest(package)
 (preparation/'handover/publication.py').write_bytes(after);shutil.copy2(package/'SHA256SUMS',preparation/'handover/SHA256SUMS');verify_manifest(preparation/'handover')
 new_package=sha(package/'SHA256SUMS');receipt={**state,'phase':'complete','new_package_sha256':new_package,'publication_py_before_sha256':OLD_PUBLICATION,'publication_py_after_sha256':NEW_PUBLICATION,'scientific_payloads_byte_identical':True,'relaxation_steps':0,'physical_time_steps':0}
 rec=load(backup/'preparation-before/record.json');rec.update(handover_sha256=new_package,original_handover_sha256=OLD_PACKAGE,formatting_repair={'recorded_at':state['recorded_at'],'repair_package_sha256':state['repair_package_sha256'],'receipt':'FORMAT-REPAIR.json'});save(preparation/'record.json',rec)
 shutil.copytree(ROOT,preparation/'format-repair',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'));save(preparation/'FORMAT-REPAIR.json',receipt)
 text=(backup/'preparation-before/README.md').read_text().rstrip()+'\n\n## Publication formatting correction\n\nThe publication helper had one extra blank line at EOF. The syntax-identical correction preserves every scientific payload and reseals the handover. [Repair receipt](FORMAT-REPAIR.json) · [Repair tooling and validation](format-repair/README.md).\n';(preparation/'README.md').write_text(text)
 manifest(preparation)
 for f in preparation.rglob('SHA256SUMS'):verify_manifest(f.parent)
 m=load(backup/'publication-marker.json');m.update(package_sha256=new_package,formatting_repair=receipt,phase='applied');save(marker,m)
 git(repo,'add','--',state['relative_preparation']);git(repo,'diff','--cached','--check')
 save(pointer,receipt);log('Adaptive preparation formatting repaired',preparation=str(preparation),backup=str(backup),old_package_sha256=OLD_PACKAGE,new_package_sha256=new_package,scientific_payloads_byte_identical=True,phase='applied',next_action='Rerun the original package install/publish/merge/preflight/run commands')
 return receipt
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['verify','run']);p.add_argument('--package',type=Path,default=Path.home()/'Downloads/ElectronFieldTopology-adaptive-Q17-Q32-screen-20261117');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-adaptive-q-screen-20261117');a=p.parse_args()
 if a.mode=='verify':verify_manifest(ROOT);log('Formatting repair package verified')
 else:run(a.package.expanduser(),a.publication.expanduser())
if __name__=='__main__':
 try:main()
 except Exception as e:log('Formatting repair stopped',error=str(e));sys.exit(1)
