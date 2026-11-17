import json,os,signal,subprocess,sys,time,uuid
from pathlib import Path
from common import ROOT,load,save,sha,stamp,log,need

def process_identity(pid):
 try:
  raw=(Path('/proc')/str(pid)/'stat').read_text();rest=raw[raw.rfind(')')+2:].split()
  if rest[0]=='Z':return None
  return {'pid':pid,'start_ticks':rest[19],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
 except (FileNotFoundError,ProcessLookupError):return None
def pointer(a):return a.publication/'.git/adaptive-last-run.json'
def running(launch):
 identity=process_identity(launch['pid'])
 return identity==launch.get('process_identity')
def worker_alive(out):
 p=out/'heartbeat.json'
 if not p.exists():return False
 h=load(p)
 return bool(h.get('process_identity') and process_identity(h['pid'])==h['process_identity'])
def prepare(a):
 import publication as pub
 pub.verify();need(pub.marker(a.publication).is_file(),'Install/publish/merge this screening preparation first');m=pub.load(pub.marker(a.publication));need(m['phase']=='merged','Merge the preparation PR before numerical execution')
 need(1<=a.cpu_threads<=os.cpu_count(),'CPU thread count is outside the host allocation')
 point=pointer(a)
 if point.exists() and not a.new_run:
  r=load(point);need(r['package_sha256']==sha(ROOT/'SHA256SUMS') and r['backend']==a.backend and r['cpu_threads']==a.cpu_threads,'Run configuration changed; use the original options to resume, or --new-run to preserve and create another run');out=Path(r['output'])
 else:
  rid=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+uuid.uuid4().hex[:8];out=a.publication/'artifacts/adaptive-q17-q32-screen'/rid;out.mkdir(parents=True,exist_ok=False)
  r={'recorded_at':stamp(),'output':str(out),'backend':a.backend,'cpu_threads':a.cpu_threads,'package_sha256':sha(ROOT/'SHA256SUMS')};save(point,r)
 return out,m
def command(a,out,mode,m):
 # Execute the exact published handover, not an editable working copy in Downloads.
 worker=a.publication/m['preparation_path']/'handover/worker.py'
 argv=['uv','run','--frozen','--python','3.12.14']
 if a.backend!='cpu':argv+=['--extra','gpu']
 argv+=['python','-u',str(worker),mode,'--repo',str(a.publication),'--output',str(out),'--backend',a.backend]
 if a.no_restore:argv+=['--no-restore']
 return argv
def environment(a):
 return dict(os.environ,OMP_NUM_THREADS=str(a.cpu_threads),OPENBLAS_NUM_THREADS=str(a.cpu_threads),MKL_NUM_THREADS=str(a.cpu_threads),PYTHONDONTWRITEBYTECODE='1')
def activity_guard():
 signatures=['screen_worker.py','sf_candidate_survey','sf_temporal_run','sf_time_gpu_run','run_measurements.py','run_calibration.py','run_science.py','worker.py run --repo']
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name)==os.getpid():continue
  try:
   raw=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');exe=raw.split(' ',1)[0]
   if ('python' in exe or exe.endswith('/uv')) and any(s in raw for s in signatures):raise RuntimeError('Another numerical worker may be active (PID '+p.name+'); finish or stop it before this campaign')
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
def foreground(a,mode):
 out,m=prepare(a);need(not (out/'launch.json').exists() or not running(load(out/'launch.json')),'A campaign is already running');activity_guard();argv=command(a,out,mode,m);log('Starting local '+mode,argv=argv,output=str(out))
 subprocess.run(argv,cwd=a.publication,env=environment(a),check=True);log('Local '+mode+' complete',output=str(out))
def start(a):
 out,m=prepare(a)
 if ((out/'launch.json').exists() and running(load(out/'launch.json'))) or worker_alive(out):log('Existing campaign remains active',output=str(out));return
 if (out/'status.json').exists() and load(out/'status.json')['status']=='complete_pending_review':log('Completed immutable campaign retained',output=str(out),evidence=str(out/'evidence.zip'));return
 need((out/'Q2-CONTROL.json').exists() and (out/'host-instruments.json').exists(),'Run preflight first');activity_guard();argv=command(a,out,'run',m);save(out/'status.json',{'recorded_at':stamp(),'status':'working','phase':'starting'})
 with (out/'runner.log').open('a') as stream:
  process=subprocess.Popen(argv,cwd=a.publication,env=environment(a),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 identity=process_identity(process.pid);need(identity,'Worker launcher exited during startup; inspect runner.log');save(out/'launch.json',{'recorded_at':stamp(),'pid':process.pid,'process_identity':identity,'argv':argv})
 log('Adaptive campaign started',pid=process.pid,output=str(out),log=str(out/'runner.log'),report=str(out/'REPORT.html'),evidence=str(out/'evidence.zip'))
def status(a):
 if not pointer(a).exists():log('No screening run created');return
 r=load(pointer(a));out=Path(r['output']);launch=load(out/'launch.json') if (out/'launch.json').exists() else None
 current=load(out/'status.json') if (out/'status.json').exists() else {'status':'not_started'}
 heartbeat=load(out/'heartbeat.json') if (out/'heartbeat.json').exists() else None
 log('Adaptive screening status',runner_alive=bool((launch and running(launch)) or worker_alive(out)),output=str(out),status=current,heartbeat=heartbeat,log=str(out/'runner.log'),report=str(out/'REPORT.html'),evidence=str(out/'evidence.zip'))
def stop(a):
 need(pointer(a).exists(),'No run to stop');out=Path(load(pointer(a))['output']);need((out/'launch.json').exists(),'No launch identity');launch=load(out/'launch.json')
 if running(launch):target=launch['pid']
 elif worker_alive(out):target=load(out/'heartbeat.json')['pid']
 else:log('Worker already stopped; retained state unchanged');return
 command=(Path('/proc')/str(target)/'cmdline').read_bytes().decode(errors='replace')
 need('worker.py' in command and str(out) in command,'PID command no longer matches this worker/output')
 group=os.getpgid(target);need(group==launch['pid'],'Worker process group no longer matches launch identity')
 os.killpg(group,signal.SIGTERM);log('Orderly stop requested; wait for checkpoint and interrupted status',output=str(out))
