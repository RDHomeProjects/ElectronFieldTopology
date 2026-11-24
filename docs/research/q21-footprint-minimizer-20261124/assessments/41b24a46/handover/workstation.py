"""Local-only publication and resource-limited, resumable zbook execution."""
import argparse,json,os,shutil,signal,subprocess,sys,time,uuid,zipfile
from pathlib import Path
from datetime import datetime,timezone
from common import *
UNIT='matter-waves-q21-footprint-minimizer.service'

def pointer(repo):return repo/'.git/q21-footprint-last.json'
def output(repo):need(pointer(repo).exists(),'No run has been created');return Path(load(pointer(repo))['output'])
def service_active():
    r=subprocess.run(['systemctl','is-active',UNIT],capture_output=True,text=True);return r.stdout.strip() in ['active','activating','deactivating']
def live(out):return any(alive(load(out/n)) for n in ['supervisor.json','worker-launch.json','heartbeat.json'] if (out/n).exists())
def pressure():
    return {label:{k:float(v) for k,v in (x.split('=') for x in fields)} for label,*fields in (line.split() for line in Path('/proc/pressure/memory').read_text().splitlines())}
def cgroup_info():
    path=next(line.split('::',1)[1] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'));root=Path('/sys/fs/cgroup')/path.lstrip('/');result={}
    for name in ['memory.current','memory.peak','memory.swap.current']:
        if (root/name).exists():result[name]=int((root/name).read_text())
    if (root/'memory.events').exists():result['memory.events']={k:int(v) for k,v in (line.split() for line in (root/'memory.events').read_text().splitlines())}
    return root,result

def environment(repo):
    return dict(os.environ,PYTHONPATH=str(repo/'src'),OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg')

def preflight(repo,a):
    pack=verify_package();spec=load(ROOT/'SOURCE.json');plan=load(ROOT/'PLAN.json');source=(a.source_run or repo/spec['relative_run']).expanduser().resolve()
    need(source.is_dir(),'Last CPU source run missing; use --source-run for the authenticated 20261123t130300z-db9ba00c directory')
    hashes=verify_zip(source/'evidence.zip',spec['evidence_sha256'])
    for name in ['identity.json','record.json','status.json','FIELD-MANIFEST.json']:
        need(sha(source/name)==hashes[name],'Source metadata differs from compact evidence: '+name)
    need(load(source/'identity.json')['run_id']==spec['run_id'],'Wrong prior run selected')
    need(load(source/'status.json')['status']=='complete_pending_review','Declared source run is not complete')
    for nodes in [177,193]:
        p=source_endpoint(source,nodes);sealname=p.relative_to(source).with_suffix('.seal.json').as_posix()
        need(sealname in hashes and sha(source/sealname)==hashes[sealname],'Source endpoint seal differs')
        with zipfile.ZipFile(p) as z:need(z.testzip() is None,'Source checkpoint CRC failure: '+str(p))
    for name,digest in load(ROOT/'NUMERICAL-SOURCE.json')['source_sha256'].items():
        need((repo/name).is_file() and sha(repo/name)==digest,'Pinned numerical source or lock differs: '+name)
    h=host();need(h['available_gib']>=plan['minimum_available_gib'],'Require at least 10 GiB available RAM');need(h['swap_free_gib']>=plan['minimum_swap_free_gib'],'Require at least 1 GiB free swap');need(shutil.disk_usage(repo).free>=40*GIB,'Require at least 40 GiB free disk')
    mapping_estimate=193**3*600/GIB+.5
    need(mapping_estimate<=min(6.5,h['available_gib']-plan['host_reserve_gib']),'193-cubed read-only mapping cannot preserve the 6 GiB host reserve; free resources and repeat preflight')
    for name in ['sudo','systemd-run','systemctl','systemd-inhibit','setpriv']:need(shutil.which(name),'Required executable missing: '+name)
    python=repo/'.venv/bin/python3';need(python.exists(),'Existing pinned numerical .venv is missing')
    r=subprocess.run([str(python),'-B',str(ROOT/'probe.py'),'--backend',a.backend],cwd=repo,env=environment(repo),capture_output=True,text=True)
    need(r.returncode==0,'Backend qualification failed: '+r.stderr+' '+r.stdout);backend=json.loads(r.stdout.strip().splitlines()[-1]);need(backend['status']=='pass','Backend probe failed')
    result={'recorded_at':stamp(),**pack,'source_run':str(source),'source_run_id':spec['run_id'],'source_evidence_sha256':spec['evidence_sha256'],'host':h,'backend_probe':backend,'python':str(python),'maximum_optimizer_attempts':240,'physical_time_steps':0}
    save(repo/'.git/q21-footprint-preflight.json',result);return result

def start(repo,a,resume=False):
    need(os.geteuid()!=0,'Run as the normal user; only the system service requires sudo');need(not service_active(),'Campaign service is already active');receipt=preflight(repo,a)
    if resume:
        out=output(repo);need(not live(out),'A campaign worker is still alive');ident=load(out/'identity.json')
        need(ident['package_sha256']==sha(ROOT/'SHA256SUMS'),'Resume package differs');need(ident['source_run']==receipt['source_run'],'Resume source location differs');need(load(out/'status.json')['status'] in ['working','starting','interrupted'],'Run is complete or failed; review before restarting')
        # Keep the prior arithmetic backend; never silently migrate a live branch.
        need(receipt['backend_probe']['selected']==ident['backend'],'Resume backend differs; use --backend '+ident['backend'])
        if (out/'STOP.json').exists():(out/'STOP.json').rename(out/('STOP-retained-'+uuid.uuid4().hex[:8]+'.json'))
    else:
        need(not pointer(repo).exists(),'A campaign already exists; use status/resume rather than starting a duplicate')
        rid=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+uuid.uuid4().hex[:8];out=repo/'artifacts/q21-footprint-minimizer'/rid;out.mkdir(parents=True)
        shutil.copytree(ROOT,out/'handover',ignore=shutil.ignore_patterns('__pycache__'));save(out/'identity.json',{'recorded_at':stamp(),'run_id':rid,'package_sha256':sha(ROOT/'SHA256SUMS'),'source_run':receipt['source_run'],'source_run_id':receipt['source_run_id'],'backend':receipt['backend_probe']['selected'],'maximum_optimizer_attempts':240})
        save(pointer(repo),{'recorded_at':stamp(),'output':str(out),'unit':UNIT})
    save(out/'PREFLIGHT.json',receipt);cfg={'recorded_at':stamp(),'uid':os.getuid(),'gid':os.getgid(),'repo':str(repo),'output':str(out),'source_run':receipt['source_run'],'python':receipt['python'],'backend':load(out/'identity.json')['backend']};save(out/'LAUNCH-CONFIG.json',cfg)
    save(out/'status.json',{'recorded_at':stamp(),'status':'starting','phase':{'name':'supervisor-launch'},'maximum_optimizer_attempts':240,'physical_time_steps':0})
    argv=['sudo','systemd-run','--unit='+UNIT,'--collect','--service-type=exec','--property=WorkingDirectory='+str(repo),'--property=MemoryAccounting=yes','--property=MemoryHigh='+str(7*GIB),'--property=MemoryMax='+str(8*GIB),'--property=MemorySwapMax='+str(GIB),'--property=Restart=no','--property=OOMPolicy=stop','--property=TimeoutStopSec=infinity','--property=SendSIGKILL=no',shutil.which('systemd-inhibit'),'--what=sleep:idle:handle-lid-switch','--mode=block','--who=Matter Waves','--why=Q21 footprint and minimizer assessment',shutil.which('setpriv'),'--reuid='+str(os.getuid()),'--regid='+str(os.getgid()),'--init-groups','--reset-env','/usr/bin/python3','-B',str(out/'handover/workstation.py'),'supervise','--repo',str(repo),'--output',str(out)]
    subprocess.run(['sudo','-v'],check=True);subprocess.run(argv,check=True);log('Q21 assessment service requested',output=str(out),backend=cfg['backend'],report=str(out/'REPORT.html'))

def supervise(repo,out):
    cfg=load(out/'LAUNCH-CONFIG.json');need(os.geteuid()!=0 and cfg['uid']==os.getuid() and cfg['repo']==str(repo) and cfg['output']==str(out),'Supervisor identity differs');verify_package();group,_=cgroup_info();need(group.name==UNIT,'Supervisor is not in the declared service')
    for name,value in [('memory.high',7*GIB),('memory.max',8*GIB),('memory.swap.max',GIB)]:need((group/name).read_text().strip()==str(value),'Service memory policy differs')
    save(out/'supervisor.json',{'recorded_at':stamp(),'pid':os.getpid(),'process_identity':process_identity(os.getpid())});stop=False;began=None;signalled=False
    def request(*_):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,request);signal.signal(signal.SIGINT,request)
    argv=[cfg['python'],'-u','-B',str(out/'handover/worker.py'),'--repo',str(repo),'--output',str(out),'--source-run',cfg['source_run'],'--backend',cfg['backend']]
    with (out/'runner.log').open('a') as stream:
        p=subprocess.Popen(argv,cwd=repo,env=environment(repo),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);save(out/'worker-launch.json',{'recorded_at':stamp(),'pid':p.pid,'process_identity':process_identity(p.pid)})
        while p.poll() is None:
            _,cg=cgroup_info();sample={'recorded_at':stamp(),'host':host(),'pressure':pressure(),'cgroup':cg};save(out/'telemetry-latest.json',sample)
            with (out/'telemetry.jsonl').open('a') as f:f.write(json.dumps(sample)+'\n')
            bad=sample['host']['available_gib']<2 or (sample['host']['available_gib']<4 and sample['pressure'].get('full',{}).get('avg10',0)>=20);began=time.monotonic() if bad and began is None else began if bad else None;unsafe=bool(bad and time.monotonic()-began>=30)
            if (stop or unsafe or (out/'STOP.json').exists()) and not signalled:save(out/'STOP.json',{'recorded_at':stamp(),'reason':'resource_pressure' if unsafe else 'operator_orderly_pause'});os.killpg(p.pid,signal.SIGTERM);signalled=True
            time.sleep(5)
    current=load(out/'status.json')
    if p.returncode!=0 and current['status'] not in ['failed','interrupted']:save(out/'status.json',{'recorded_at':stamp(),'status':'interrupted','error':'Worker exited before final seal; attempt ledgers remain charged','exit_code':p.returncode,'physical_time_steps':0})
    log('Q21 assessment supervisor finished',output=str(out),status=load(out/'status.json'));return p.returncode

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','install','publish','merge','preflight','run','resume','status','stop','collect','record-results','supervise']);p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-adaptive-q-screen-20261117');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-Q21-footprint-publication-20261124');p.add_argument('--source-run',type=Path);p.add_argument('--backend',choices=['auto','cpu','cuda'],default='auto');p.add_argument('--output',type=Path);a=p.parse_args();repo=a.repo.expanduser().resolve();pub=a.publication.expanduser().resolve()
    if a.mode=='verify':log('Q21 footprint/minimizer package verified',**verify_package(),production_started=False)
    elif a.mode in ['install','publish','merge','record-results']:
        from local_publication import execute
        out=output(repo) if a.mode=='record-results' else None
        if out:need(not service_active() and not live(out),'Wait for service and worker exit');need(load(out/'status.json')['status']=='complete_pending_review','Collect incomplete evidence for review; only complete results publish automatically')
        result=execute(a.mode,repo,pub,out);log('Workstation publication status',**{k:result.get(k) for k in ['kind','phase','pr']})
    elif a.mode=='preflight':log('Q21 footprint/minimizer preflight',**preflight(repo,a))
    elif a.mode in ['run','resume']:start(repo,a,a.mode=='resume')
    elif a.mode=='supervise':return supervise(repo,a.output.resolve())
    elif a.mode=='status':
        marker=pub/'.git/q21-footprint-publication.json'
        if marker.exists():log('Publication status',**{k:load(marker).get(k) for k in ['kind','phase','pr']})
        if pointer(repo).exists():
            out=output(repo);log('Q21 footprint/minimizer status',output=str(out),runner_alive=live(out),service_active=service_active(),status=load(out/'status.json'),heartbeat=load(out/'heartbeat.json') if (out/'heartbeat.json').exists() else None,telemetry=load(out/'telemetry-latest.json') if (out/'telemetry-latest.json').exists() else None,report=str(out/'REPORT.html'),evidence=str(out/'evidence.zip'))
        else:log('No Q21 footprint/minimizer run created')
    elif a.mode=='stop':save(output(repo)/'STOP.json',{'recorded_at':stamp(),'reason':'operator_orderly_pause'});log('Orderly pause requested; wait for a sealed accepted update')
    elif a.mode=='collect':
        out=output(repo);need(not service_active() and not live(out),'Wait for service and worker exit');verify_zip(out/'evidence.zip');dest=Path.home()/'Downloads'/('ElectronFieldTopology-Q21-footprint-minimizer-'+load(out/'identity.json')['run_id']+'-evidence.zip');need(not dest.exists() or sha(dest)==sha(out/'evidence.zip'),'Existing collection name has different bytes');shutil.copy2(out/'evidence.zip',dest);log('Assessment evidence collected',file=str(dest),sha256=sha(dest),status=load(out/'status.json')['status'])
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:log('Q21 footprint/minimizer handover stopped',error=str(exc));raise SystemExit(1)
