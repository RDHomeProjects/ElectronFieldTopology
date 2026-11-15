"""Workstation publication and controlled campaign runner. GitHub operations run locally only."""
import argparse,os,subprocess,sys,secrets,signal,zipfile
from pathlib import Path
from datetime import datetime,timezone
from support import *
p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','install','publish','merge','preflight','benchmark','run','resume','status','stop']);p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-campaign2');p.add_argument('--source-repo',type=Path,default=Path.home()/'ElectronFieldTopology-rapid-q-followup');p.add_argument('--prior-run',type=Path);p.add_argument('--source-run',type=Path);p.add_argument('--output',type=Path);p.add_argument('--backend',choices=['auto','cpu','cuda'],default='auto');a=p.parse_args()
def alive(pid):
 try:os.kill(pid,0);return True
 except ProcessLookupError:return False

def busy():
 parents={os.getpid()};pid=os.getppid()
 while pid>1 and pid not in parents:
  parents.add(pid)
  try:pid=int(next(v.split()[1] for v in (Path('/proc')/str(pid)/'status').read_text().splitlines() if v.startswith('PPid:')))
  except (FileNotFoundError,PermissionError,StopIteration):break
 found=[]
 for path in Path('/proc').iterdir():
  if not path.name.isdigit() or int(path.name) in parents:continue
  try:
   if path.stat().st_uid!=os.getuid():continue
   args=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');exe=args.split(' ',1)[0]
   if ('python' in exe or exe.endswith('/uv')) and (any(t in args for t in ['screen_worker.py','followup_worker.py','sf_candidate_survey','sf_temporal_run','run_measurements.py','run_calibration.py',str(ROOT/'worker.py')]) or ('ElectronFieldTopology-' in args and '/worker.py' in args)):found.append(int(path.name))
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
 need(not found,'Another analysis worker is active; leave it running and retry later: '+str(found))

def main():
 package=verify_package()
 if a.mode in ['verify','install','publish','merge']:
  import publication
  from types import SimpleNamespace
  args=SimpleNamespace(repo=a.source_repo.resolve(),publication=a.repo.resolve(),run=a.source_run)
  if a.mode=='verify':publication.verify(a.source_run)
  elif a.mode=='install':publication.install(args)
  elif a.mode=='publish':publication.publish(args)
  else:publication.merge(args)
  return
 repo=a.repo.resolve();need((repo/'pyproject.toml').is_file(),'Install and publish campaign2 first, or set --repo to its publication checkout')
 base=repo/'artifacts/targeted-q-campaign2';base.mkdir(parents=True,exist_ok=True);pointer=base/'LATEST-CAMPAIGN2-20261115.json'
 if a.output:out=a.output.resolve()
 elif pointer.exists():
  selected=load(pointer);need(selected['package_sha256']==package,'Previous allocation uses another package; choose a new --output path');out=Path(selected['output'])
 elif a.mode in ['preflight','benchmark']:
  rid=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4);out=base/rid
 else:raise RuntimeError('Run preflight first, or supply the existing --output path')
 if a.mode in ['status','stop']:
  status=load(out/'status.json') if (out/'status.json').exists() else {};heartbeat=load(out/'heartbeat.json') if (out/'heartbeat.json').exists() else {};launch=load(out/'launch.json') if (out/'launch.json').exists() else {}
  running=False;pid=None
  for candidate in [heartbeat.get('pid'),status.get('pid'),launch.get('pid')]:
   if not candidate or not alive(candidate):continue
   try:
    proc=Path('/proc')/str(candidate);cmdline=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()
    if proc.stat().st_uid==os.getuid() and str(ROOT/'worker.py') in cmdline and str(out) in cmdline:running=True;pid=candidate;break
   except (FileNotFoundError,PermissionError):pass
  if a.mode=='stop':
   if running:os.kill(pid,signal.SIGTERM);log('Graceful stop requested',pid=pid,output=str(out))
   else:log('No matching analysis worker is running',output=str(out))
  else:log('Analysis status',runner_alive=running,output=str(out),status=status,heartbeat=heartbeat,report=str(out/'REPORT.html'),evidence=str(out/'evidence.zip'))
  return
 busy()
 import publication
 marker=publication.marker(repo);need(marker.is_file() and load(marker).get('merged'),'Publish and merge the campaign preparation before numerical preflight/run')
 source=a.source_run
 if source is None:
  candidates=[];expected=load(ROOT/'PLAN.json')['completed_evidence_sha256']
  for root in [a.source_repo.resolve(),Path.home()/'ElectronFieldTopology-rapid-q-followup',Path.home()/'ElectronFieldTopology-repository-admin']:
   if root.exists():
    for path in root.glob('artifacts/targeted-q-diagnostic/*/evidence.zip'):
     if sha(path)==expected:candidates.append(path.parent.resolve())
  candidates=sorted(set(candidates));need(len(candidates)==1,'Supply --source-run for the completed targeted600-step run; matching candidates: '+str(candidates));source=candidates[0]
 prior=a.prior_run
 if prior is None:
  with zipfile.ZipFile(ROOT/'data/completed-evidence.zip') as z:prior=Path(__import__('json').loads(z.read('record.json'))['identity']['source_run'])
 prior=prior.resolve();need((prior/'evidence.zip').is_file(),'Original retained Q4 run is missing; supply --prior-run')
 source=source.resolve();out.mkdir(parents=True,exist_ok=True)
 config={'package_sha256':package,'repo':str(repo),'source_run':str(source),'prior_run':str(prior),'backend':a.backend}
 if (out/'allocation.json').exists():need(load(out/'allocation.json')==config,'Allocation configuration differs; use its original paths/backend or choose a new --output')
 else:need(not any(out.iterdir()),'Output is not empty and has no allocation identity');save(out/'allocation.json',config)
 save(pointer,{'recorded_at':stamp(),'package_sha256':package,'output':str(out)})
 env=os.environ.copy()
 for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:env[k]='4'
 mode='preflight' if a.mode in ['preflight','benchmark'] else 'run'
 argv=['uv','run','--frozen','--python','3.12.14']
 if a.backend!='cpu':argv+=['--extra','gpu']
 argv+=['python',str(ROOT/'worker.py'),mode,'--repo',str(repo),'--source-run',str(source),'--output',str(out),'--prior-run',str(prior),'--backend',a.backend]
 if mode=='preflight':
  result=subprocess.run(argv,cwd=repo,env=env);need(result.returncode==0,'Local preflight stopped; inspect output and status');log('Preflight complete; run may now be launched',output=str(out));return
 need((out/'preflight.json').is_file(),'Run preflight first')
 if (out/'record.json').is_file() and load(out/'record.json').get('status')=='complete_pending_review' and (out/'evidence.zip').exists():log('Already complete',output=str(out));return
 with (out/'runner.log').open('a') as log_file:child=subprocess.Popen(argv,cwd=repo,env=env,stdout=log_file,stderr=subprocess.STDOUT,start_new_session=True)
 save(out/'launch.json',{'recorded_at':stamp(),'pid':child.pid,'argv':argv});log('Background analysis launched',pid=child.pid,output=str(out),log=str(out/'runner.log'))
try:main()
except Exception as ex:log('Handover stopped',error=str(ex));sys.exit(1)
