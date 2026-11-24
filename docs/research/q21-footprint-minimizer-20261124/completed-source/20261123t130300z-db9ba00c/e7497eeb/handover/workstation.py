"""Workstation-only publication, resource-limited CPU execution and resumable status."""
import argparse,gc,json,os,shutil,signal,subprocess,sys,time,uuid,zipfile
from pathlib import Path
from datetime import datetime,timezone
from criteria_common import ROOT,GIB,load,save,sha,stamp,need,log,verify_package,verify_zip,host,process_identity,alive
UNIT='matter-waves-q21-criteria-cpu.service'

def pointer(repo):return repo/'.git/q21-criteria-cpu-last.json'
def output(repo):need(pointer(repo).exists(),'No supplementary run created');return Path(load(pointer(repo))['output'])
def service_active():
 r=subprocess.run(['systemctl','is-active',UNIT],capture_output=True,text=True);return r.stdout.strip() in ['active','activating','deactivating']
def live(out):return any(alive(load(out/n)) for n in ['supervisor.json','heartbeat.json'] if (out/n).exists())
def mempressure(path=Path('/proc/pressure/memory')):
 return {label:{k:float(v) for k,v in (x.split('=') for x in fields)} for label,*fields in (line.split() for line in path.read_text().splitlines())}
def cgroup_info():
 path=next(line.split('::',1)[1] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'));root=Path('/sys/fs/cgroup')/path.lstrip('/');result={}
 for name in ['memory.current','memory.peak','memory.swap.current']:
  if (root/name).exists():result[name]=int((root/name).read_text())
 if (root/'memory.events').exists():result['memory.events']={k:int(v) for k,v in (line.split() for line in (root/'memory.events').read_text().splitlines())}
 return root,result

def source_paths(repo,a):
 p=load(ROOT/'PLAN.json');return (a.source_run or repo/p['source_relative_run']).expanduser().resolve(),(a.parent or repo/p['source_parent_relative']).expanduser().resolve()

def preflight(repo,a):
 pack=verify_package();plan=load(ROOT/'PLAN.json');source,parent=source_paths(repo,a);need(source.is_dir(),'Completed source run is missing; supply --source-run with the same authenticated run');hashes=verify_zip(source/'evidence.zip',plan['source_evidence_sha256'])
 for name in ['identity.json','record.json','status.json','FIELD-MANIFEST.json']:
  need(sha(source/name)==hashes[name],'Local source metadata differs from compact evidence: '+name)
 need(load(source/'status.json')['status']=='complete_pending_review','Source is not the completed declared run')
 need(sha(parent)==plan['source_parent_sha256'],'Iteration-545 parent differs or is missing')
 with zipfile.ZipFile(parent) as z:need(z.testzip() is None,'Parent NPZ CRC failure')
 num=load(ROOT/'legacy/NUMERICAL-SOURCE.json');expected={**num['complete_numerical_source_sha256'],**num['source_sha256']}
 for name,digest in expected.items():need((repo/name).is_file() and sha(repo/name)==digest,'Numerical source/lock differs: '+name)
 fields=load(source/'FIELD-MANIFEST.json')['fields'];count=0
 for row in fields:
  path=source/row['path'];need(path.is_file() and path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'Retained source field differs/missing: '+row['path']);count+=1
 stats=host();need(stats['available_gib']>=10,'Require 10 GiB available host RAM before launch');need(stats['swap_free_gib']>=1,'Require 1 GiB free swap before launch');need(shutil.disk_usage(repo).free>=56*GIB,'Require 56 GiB free disk before launch')
 for name in ['sudo','systemd-run','systemctl','systemd-inhibit','setpriv']:need(shutil.which(name),'Required workstation executable missing: '+name)
 python=repo/'.venv/bin/python3';need(python.exists(),'Use the existing numerical checkout .venv; do not replace it with system Python')
 env=dict(os.environ,PYTHONPATH=str(repo/'src'),OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1')
 r=subprocess.run([str(python),'-c',"import sys,numpy,scipy,matplotlib; assert sys.version_info[:3]==(3,12,14); print(numpy.__version__,scipy.__version__,matplotlib.__version__)"],capture_output=True,text=True,env=env,cwd=repo);need(r.returncode==0,'Pinned CPU runtime qualification failed: '+r.stderr)
 # Geometry estimates are advisory here; admission is repeated immediately before each branch.
 def estimate(n):return n**3*600/GIB+.5
 result={'recorded_at':stamp(),**pack,'source_run':str(source),'parent':str(parent),'authenticated_original_full_fields':count,'source_parent_sha256':plan['source_parent_sha256'],'host':stats,'cpu_estimates_gib':{str(n):estimate(n) for n in [177,193]},'backend':'cpu','runtime_versions':r.stdout.strip(),'python':str(python),'maximum_new_optimizer_attempts':160,'physical_time_steps':0};save(repo/'.git/q21-criteria-preflight.json',result);return result

def start(repo,a,resume=False):
 need(os.geteuid()!=0,'Run as the normal account; sudo is used only for the service');need(not service_active(),'Supplementary service is already active');receipt=preflight(repo,a)
 if resume:
  out=output(repo);need(not live(out),'Worker is still alive');identity=load(out/'identity.json');need(identity['package_sha256']==sha(ROOT/'SHA256SUMS'),'Resume package differs');need(load(out/'status.json')['status'] in ['interrupted','working','starting'],'Completed/failed runs require assessment, not automatic restart');need(identity['source_run']==receipt['source_run'] and identity['parent']==receipt['parent'],'Resume source location differs')
  if (out/'STOP.json').exists():(out/'STOP.json').rename(out/('STOP-retained-'+uuid.uuid4().hex[:8]+'.json'))
 else:
  need(not pointer(repo).exists(),'A supplementary run already exists; use status or resume to retain accounting');rid=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+uuid.uuid4().hex[:8];out=repo/'artifacts/q21-criteria-audit-cpu-resolution'/rid;out.mkdir(parents=True);shutil.copytree(ROOT,out/'handover',ignore=shutil.ignore_patterns('__pycache__'));save(out/'identity.json',{'recorded_at':stamp(),'run_id':rid,'package_sha256':sha(ROOT/'SHA256SUMS'),'backend':'cpu','source_run':receipt['source_run'],'parent':receipt['parent'],'maximum_optimizer_attempts':160});save(pointer(repo),{'recorded_at':stamp(),'output':str(out),'unit':UNIT})
 save(out/'PREFLIGHT.json',receipt);save(out/'LAUNCH-CONFIG.json',{'recorded_at':stamp(),'uid':os.getuid(),'gid':os.getgid(),'repo':str(repo),'output':str(out),'source_run':receipt['source_run'],'parent':receipt['parent'],'python':receipt['python']});save(out/'status.json',{'recorded_at':stamp(),'status':'starting','phase':{'name':'supervisor-launch'},'charged_optimizer_attempts':0 if not resume else load(out/'record.json').get('charged_optimizer_attempts',0) if (out/'record.json').exists() else None,'maximum_optimizer_attempts':160,'physical_time_steps':0})
 argv=['sudo','systemd-run','--unit='+UNIT,'--collect','--service-type=exec','--property=WorkingDirectory='+str(repo),'--property=MemoryAccounting=yes','--property=MemoryHigh='+str(7*GIB),'--property=MemoryMax='+str(8*GIB),'--property=MemorySwapMax='+str(GIB),'--property=Restart=no','--property=OOMPolicy=stop','--property=TimeoutStopSec=infinity','--property=SendSIGKILL=no',shutil.which('systemd-inhibit'),'--what=sleep:idle:handle-lid-switch','--mode=block','--who=Matter Waves','--why=Q21 CPU resolution and literature measurements',shutil.which('setpriv'),'--reuid='+str(os.getuid()),'--regid='+str(os.getgid()),'--init-groups','--reset-env','/usr/bin/python3','-B',str(out/'handover/workstation.py'),'supervise','--repo',str(repo),'--output',str(out)]
 subprocess.run(['sudo','-v'],check=True);subprocess.run(argv,check=True);log('CPU supplement requested',output=str(out),report=str(out/'REPORT.html'),backend='cpu',maximum_attempts=160)

def supervise(repo,out):
 cfg=load(out/'LAUNCH-CONFIG.json');need(os.geteuid()!=0 and cfg['uid']==os.getuid() and cfg['repo']==str(repo) and cfg['output']==str(out),'Supervisor identity differs');verify_package();group,_=cgroup_info();need(group.name==UNIT,'Supervisor is not in the declared service')
 for name,value in [('memory.high',7*GIB),('memory.max',8*GIB),('memory.swap.max',GIB)]:need((group/name).read_text().strip()==str(value),'Service memory policy differs')
 save(out/'supervisor.json',{'recorded_at':stamp(),'pid':os.getpid(),'process_identity':process_identity(os.getpid())});stop=False;began=None;signalled=False
 def request(*_):
  nonlocal stop
  stop=True
 signal.signal(signal.SIGTERM,request);signal.signal(signal.SIGINT,request)
 env=dict(os.environ,PYTHONPATH=str(repo/'src'),OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1');argv=[cfg['python'],'-u','-B',str(out/'handover/worker.py'),'--repo',str(repo),'--output',str(out),'--source-run',cfg['source_run'],'--parent',cfg['parent']]
 with (out/'runner.log').open('a') as stream:
  process=subprocess.Popen(argv,cwd=repo,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);save(out/'worker-launch.json',{'recorded_at':stamp(),'pid':process.pid,'process_identity':process_identity(process.pid)})
  while process.poll() is None:
   _,cg=cgroup_info();sample={'recorded_at':stamp(),'host':host(),'pressure':mempressure(),'cgroup':cg};save(out/'telemetry-latest.json',sample)
   with (out/'telemetry.jsonl').open('a') as f:f.write(json.dumps(sample)+'\n')
   available=sample['host']['available_gib'];bad=available<2 or (available<4 and sample['pressure'].get('full',{}).get('avg10',0)>=20);began=time.monotonic() if bad and began is None else began if bad else None;unsafe=bool(bad and time.monotonic()-began>=30)
   if (stop or unsafe or (out/'STOP.json').exists()) and not signalled:
    save(out/'STOP.json',{'recorded_at':stamp(),'reason':'resource_pressure' if unsafe else 'operator_orderly_pause'});os.killpg(process.pid,signal.SIGTERM);signalled=True
   time.sleep(5)
 current=load(out/'status.json')
 if process.returncode!=0 and current['status'] not in ['interrupted','failed']:
  save(out/'status.json',{'recorded_at':stamp(),'status':'interrupted','error':'Worker exited before final seal; retained charged ledger/checkpoints are authoritative','exit_code':process.returncode,'physical_time_steps':0})
 log('Supplementary supervisor finished',output=str(out),status=load(out/'status.json'));return process.returncode

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','install','publish','merge','preflight','run','resume','status','stop','collect','record-results','supervise']);p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-adaptive-q-screen-20261117');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-Q21-criteria-publication-20261123');p.add_argument('--source-run',type=Path);p.add_argument('--parent',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();repo=a.repo.expanduser().resolve();pub=a.publication.expanduser().resolve()
 if a.mode=='verify':log('Criteria/CPU package verified',**verify_package(),new_production_started=False)
 elif a.mode in ['install','publish','merge','record-results']:
  from local_publication import execute
  out=output(repo) if a.mode=='record-results' else None
  if out:need(not service_active() and not live(out),'Wait for the supplement service and worker to stop before publication');need(load(out/'status.json')['status']=='complete_pending_review','Only a complete supplement can be published automatically; interrupted evidence is collected for review')
  result=execute(a.mode,repo,pub,out);log('Workstation publication status',**{k:result.get(k) for k in ['kind','phase','pr']})
 elif a.mode=='preflight':log('CPU supplement preflight',**preflight(repo,a))
 elif a.mode in ['run','resume']:start(repo,a,a.mode=='resume')
 elif a.mode=='supervise':return supervise(repo,a.output.resolve())
 elif a.mode=='status':
  marker=pub/'.git/q21-criteria-publication.json'
  if marker.exists():log('Publication status',**{k:load(marker).get(k) for k in ['kind','phase','pr']})
  if pointer(repo).exists():
   out=output(repo);log('Q21 criteria/CPU supplement status',output=str(out),runner_alive=live(out),service_active=service_active(),status=load(out/'status.json'),heartbeat=load(out/'heartbeat.json') if (out/'heartbeat.json').exists() else None,telemetry=load(out/'telemetry-latest.json') if (out/'telemetry-latest.json').exists() else None,report=str(out/'REPORT.html'),evidence=str(out/'evidence.zip'))
  else:log('No supplementary run created')
 elif a.mode=='stop':save(output(repo)/'STOP.json',{'recorded_at':stamp(),'reason':'operator_orderly_pause'});log('Orderly pause requested; wait for a sealed accepted update')
 elif a.mode=='collect':
  out=output(repo);need(not service_active() and not live(out),'Wait for worker/service exit before collection');verify_zip(out/'evidence.zip');dest=Path.home()/'Downloads'/('ElectronFieldTopology-Q21-criteria-CPU-'+load(out/'identity.json')['run_id']+'-evidence.zip');need(not dest.exists() or sha(dest)==sha(out/'evidence.zip'),'Existing collection name has different content');shutil.copy2(out/'evidence.zip',dest);log('Supplementary evidence collected',file=str(dest),sha256=sha(dest),status=load(out/'status.json')['status'])
 return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as exc:log('Criteria/CPU handover stopped',error=str(exc));raise SystemExit(1)
