"""Local-only publication and bounded supervised scientific campaign."""
import argparse,json,os,shutil,signal,subprocess,time,uuid
from pathlib import Path
from datetime import datetime,timezone
from common import ROOT,load,save,sha,stamp,need,log,verify_manifest
from integrity import verify_sources,authenticate,reserves,merged_source,alive,process_identity,host
from supervision import UNIT,service_active,group_path,group_info,pressure,pressure_stop
GIB=1024**3

def pointer(repo):return repo/'.git/q21-resolution-last.json'
def output(repo):need(pointer(repo).exists(),'No resolution run created');return Path(load(pointer(repo))['output'])
def live(out):return any(alive(load(out/n)) for n in ['supervisor.json','heartbeat.json'] if (out/n).exists())
def launch_argv(repo,out):
    return ['sudo','systemd-run','--unit='+UNIT,'--collect','--service-type=exec','--property=WorkingDirectory='+str(repo),'--property=MemoryAccounting=yes','--property=MemoryHigh='+str(7*GIB),'--property=MemoryMax='+str(8*GIB),'--property=MemorySwapMax='+str(GIB),'--property=Restart=no','--property=OOMPolicy=stop','--property=TimeoutStopSec=infinity','--property=SendSIGKILL=no',shutil.which('systemd-inhibit'),'--what=sleep:idle:handle-lid-switch','--mode=block','--who=Matter Waves','--why=Retained-field audit and fixed-box Q21 resolution pilot',shutil.which('setpriv'),'--reuid='+str(os.getuid()),'--regid='+str(os.getgid()),'--init-groups','--reset-env','/usr/bin/python3','-B',str(out/'handover/handover.py'),'supervise','--repo',str(repo),'--output',str(out)]

def runtime_preflight(repo,requested,source_pub,pub=None):
    verify_manifest(ROOT);verify_sources(repo);reserves(repo,True);prior=merged_source(source_pub);receipt=authenticate(repo)
    if pub is not None:
        from publication import require_plan_merged
        receipt['registered_plan_merge']=require_plan_merged(pub)
    for exe in ['uv','sudo','systemd-run','systemctl','systemd-inhibit','setpriv','gcc']:need(shutil.which(exe),'Required local executable missing: '+exe)
    env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run(['uv','run','--frozen','--extra','gpu','--python','3.12.14','python','-B',str(ROOT/'probe.py'),'--repo',str(repo),'--backend',requested],cwd=repo,env=env,text=True,capture_output=True)
    need(result.returncode==0,'Read-only scientific preflight failed:\n'+result.stdout+'\n'+result.stderr);receipt.update(recorded_at=stamp(),merge_check=prior,probe=json.loads(result.stdout.strip().splitlines()[-1]),package_sha256=sha(ROOT/'SHA256SUMS'));save(repo/'.git/q21-resolution-preflight.json',receipt);return receipt

def start(repo,requested,source_pub,resume=False,pub=None):
    need(os.geteuid()!=0,'Use the normal account; sudo is only used to create the resource-limited service');need(not service_active(),'Resolution service already active')
    chosen=load(output(repo)/'identity.json')['backend']['selected'] if resume else requested;receipt=runtime_preflight(repo,chosen,source_pub,pub)
    if resume:
        out=output(repo);identity=load(out/'identity.json');need(not live(out),'Worker still active');need(load(out/'status.json')['status'] in ['interrupted','working','starting'],'Completed/failed runs require review')
        need(identity['package_sha256']==sha(ROOT/'SHA256SUMS') and identity['requested_backend']==requested,'Resume must retain the original package and requested backend')
        need(identity['backend']['selected']==receipt['probe']['backend']['selected'] and identity['backend']['device']==receipt['probe']['backend']['device'],'Resume backend/device changed')
        verify_manifest(out/'handover')
        if (out/'STOP.json').exists():(out/'STOP.json').rename(out/('STOP-retained-'+uuid.uuid4().hex[:8]+'.json'))
    else:
        need(not pointer(repo).exists(),'A run already exists; use status/resume to preserve lineage and charged work')
        rid=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+uuid.uuid4().hex[:8];out=repo/'artifacts/q21-fixedbox-resolution-retained-audit'/rid;out.mkdir(parents=True,exist_ok=False);shutil.copytree(ROOT,out/'handover',ignore=shutil.ignore_patterns('__pycache__'))
        save(out/'identity.json',{'recorded_at':stamp(),'run_id':rid,'package_sha256':sha(ROOT/'SHA256SUMS'),'plan_sha256':sha(ROOT/'PLAN.json'),'source_evidence_sha256':receipt['evidence_sha256'],'source_identity':receipt['endpoint_sha256'],'requested_backend':requested,'backend':receipt['probe']['backend'],'maximum_optimizer_attempts':720});save(pointer(repo),{'recorded_at':stamp(),'output':str(out),'unit':UNIT})
    save(out/'PREFLIGHT.json',receipt);save(out/'LAUNCH-CONFIG.json',{'recorded_at':stamp(),'uid':os.getuid(),'repo':str(repo),'output':str(out),'executable_path':str(Path(shutil.which('uv')).parent)+':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'});save(out/'status.json',{'recorded_at':stamp(),'status':'starting','phase':{'name':'supervisor-launch'},'physical_time_steps':0});subprocess.run(['sudo','-v'],check=True);subprocess.run(launch_argv(repo,out),check=True);log('Bounded scientific service requested',output=str(out),maximum_optimizer_attempts=720,report=str(out/'REPORT.html'))

def supervise(repo,out):
    need(os.geteuid()!=0,'Worker must run as normal user');cfg=load(out/'LAUNCH-CONFIG.json');need(cfg['uid']==os.getuid() and cfg['repo']==str(repo) and cfg['output']==str(out),'Supervisor identity differs');os.environ['PATH']=cfg['executable_path'];verify_manifest(ROOT);group=group_path();need(group.name==UNIT and 'system.slice' in group.parts,'Worker is not in the isolated service')
    for n,value in [('memory.high',7*GIB),('memory.max',8*GIB),('memory.swap.max',GIB)]:need((group/n).read_text().strip()==str(value),'Resource limit differs: '+n)
    save(out/'supervisor.json',{'recorded_at':stamp(),'pid':os.getpid(),'process_identity':process_identity(os.getpid())});stop=False
    def request(*_):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,request);signal.signal(signal.SIGINT,request)
    env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1');argv=['uv','run','--frozen','--extra','gpu','--python','3.12.14','python','-u','-B',str(ROOT/'worker.py'),'--repo',str(repo),'--output',str(out)]
    began=None;signalled=False
    with (out/'runner.log').open('a') as stream:
        process=subprocess.Popen(argv,cwd=repo,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);save(out/'worker-launch.json',{'recorded_at':stamp(),'pid':process.pid,'process_identity':process_identity(process.pid)})
        while process.poll() is None or ((out/'heartbeat.json').exists() and alive(load(out/'heartbeat.json'))):
            sample={'recorded_at':stamp(),'host':host(),'pressure':pressure(),'cgroup':group_info(group)};save(out/'telemetry-latest.json',sample)
            with (out/'telemetry.jsonl').open('a') as f:f.write(json.dumps(sample)+'\n')
            unsafe,began=pressure_stop(sample,time.monotonic(),began)
            if (unsafe or stop or (out/'STOP.json').exists()) and not signalled:
                save(out/'STOP.json',{'recorded_at':stamp(),'reason':'resource_pressure' if unsafe else 'operator_stop'});os.killpg(process.pid,signal.SIGTERM);signalled=True
            time.sleep(5)
    current=load(out/'status.json')
    if process.returncode!=0 and current['status'] not in ['interrupted','failed']:
        save(out/'status.json',{'recorded_at':stamp(),'status':'interrupted' if group_info(group).get('memory.events',{}).get('oom_kill',0) else 'failed','exit_code':process.returncode,'error':'Worker exited before final seal. Retained checkpoints and charged work remain.'})
    current=load(out/'status.json');log('Scientific supervisor finished',status=current,output=str(out));return 0 if current['status'] in ['complete_pending_review','interrupted'] else process.returncode or 1

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','install','publish','merge','preflight','run','resume','status','stop','record-results','supervise']);p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-adaptive-q-screen-20261117');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-scientific-publication');p.add_argument('--source-publication',type=Path,default=Path.home()/'ElectronFieldTopology-Q21-conditioning-results-record-20261123');p.add_argument('--backend',choices=['auto','cpu','cuda'],default='auto');p.add_argument('--output',type=Path);a=p.parse_args();repo=a.repo.expanduser().resolve();pub=a.publication.expanduser().resolve();source_pub=a.source_publication.expanduser().resolve()
    if a.mode=='verify':
        count=verify_manifest(ROOT);plan=load(ROOT/'PLAN.json');need(5*80+80+2*80+2*40==plan['maximum_new_optimizer_attempts']==720,'Budget differs');need(plan['fixed_length']==30.72 and plan['baseline_shift']==.25,'Registered factor controls differ');log('Scientific package verified',files=count,maximum_optimizer_attempts=720,catalogued_endpoints=len(load(ROOT/'CATALOGUE.json')['candidates']),physical_time_steps=0)
    elif a.mode in ['install','publish','merge','record-results']:
        import publication
        publication.execute(a.mode,repo,pub,source_pub,output(repo) if a.mode=='record-results' else None)
    elif a.mode=='preflight':log('Scientific preflight',**runtime_preflight(repo,a.backend,source_pub,pub))
    elif a.mode in ['run','resume']:start(repo,a.backend,source_pub,a.mode=='resume',pub)
    elif a.mode=='supervise':return supervise(repo,a.output.resolve())
    elif a.mode=='status':
        if marker_exists:= (pub/'.git/q21-resolution-publication.json').exists():log('Publication status',**{k:v for k,v in load(pub/'.git/q21-resolution-publication.json').items() if k in ['phase','kind','pr']})
        if pointer(repo).exists():
            out=output(repo);log('Scientific campaign status',runner_alive=live(out),service_active=service_active(),output=str(out),status=load(out/'status.json'),heartbeat=load(out/'heartbeat.json') if (out/'heartbeat.json').exists() else None,telemetry=load(out/'telemetry-latest.json') if (out/'telemetry-latest.json').exists() else None,evidence=str(out/'evidence.zip'),report=str(out/'REPORT.html'),log=str(out/'runner.log'))
        else:log('No scientific run created')
    elif a.mode=='stop':
        out=output(repo);save(out/'STOP.json',{'recorded_at':stamp(),'reason':'operator_requested_orderly_pause'});log('Orderly pause requested; wait for accepted-step commitment',output=str(out))
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:log('Scientific handover stopped',error=str(error));raise SystemExit(1)
