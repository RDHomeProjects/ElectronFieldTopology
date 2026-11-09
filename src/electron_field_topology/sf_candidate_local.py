"""Linux lifecycle and offline previews for S5-B-010. Apache-2.0."""
import argparse,fcntl,hashlib,json,os,secrets,shutil,signal,subprocess,sys
from collections import deque
from datetime import datetime,timezone
from pathlib import Path
from .sf_candidate_survey import ROOT,CONFIG,validate
from .sf_higher_q_sources import event,need,load,recover,validate_field,sha
from .sf_checkpoints import timestamp,atomic_json
from .sf_motion_local import process_identity
ART=ROOT/'artifacts';POINTER=ART/'SF-CANDIDATE-SURVEY-CURRENT'
PROFILE=ROOT/'experiments/configs/renderers/candidate-survey.json'

def alive(meta):return meta.get('process_identity') is not None and process_identity(meta['pid'])==meta['process_identity']
def current():
    need(POINTER.is_file(),'No candidate survey has been started in this checkout');out=Path(POINTER.read_text().strip());return out,load(out/'launch.json')
def retain_handover(out):
    package=os.environ.get('EFT_CANDIDATE_HANDOVER')
    if not package:return
    package=Path(package);target=out/'handover';target.mkdir(exist_ok=True);names=['SHA256SUMS']
    for line in (package/'SHA256SUMS').read_text().splitlines():
        h,name=line.split('  ',1);need(Path(name).name==name and sha(package/name)==h,'Handover changed before snapshot');names.append(name)
    for name in names:
        p=target/name
        if p.exists():need(p.read_bytes()==(package/name).read_bytes(),'Retained handover differs; preserve this run')
        else:shutil.copy2(package/name,p)

def preflight(config):
    c=validate(load(config));free=shutil.disk_usage(ROOT).free/1024**3;need(free>=c['minimum_free_gib'],f'At least {c["minimum_free_gib"]} GiB free headroom required; {free:.1f} available')
    source=recover(c['reference_source'],ART/'cache/s5-b-010');validate_field(source,c['reference_source']);event('Preflight passed',free_gib=free,q2_source=str(source),q2_sha256=sha(source),rest_seeds=6,mesh_nodes=[s['nodes'] for s in c['levels']],domain_nodes=c['domain']['nodes'],precision='CPU float64; unchanged D4 action/projected RK4',scope='Authenticated Q2 source and configuration/resources only; no preparation or trajectory has run')

def launch(config,out=None,wait=False):
    c=validate(load(config));need(shutil.disk_usage(ROOT).free/1024**3>=c['minimum_free_gib'],'Insufficient declared disk headroom; no new worker launched')
    ART.mkdir(exist_ok=True)
    if out is None:out=ART/'s5-b/010-intermediate-q-survey'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz')+'-'+secrets.token_hex(4));need(not out.exists(),'New run ID already exists')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);retain_handover(out);(out/'stop-request.json').unlink(missing_ok=True)
    cmd=[sys.executable,'-u','-m','electron_field_topology.sf_candidate_survey','--output',str(out),'--config',str(Path(config).resolve())]
    env={**os.environ,'OMP_NUM_THREADS':os.environ.get('OMP_NUM_THREADS','2'),'OPENBLAS_NUM_THREADS':'1','MPLBACKEND':'Agg','PYTHONDONTWRITEBYTECODE':'1'}
    with (out/'runner.log').open('a') as f:
        f.write(json.dumps({'recorded_at':timestamp(),'command':cmd})+'\n');f.flush();child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    identity=process_identity(child.pid)
    if identity is None:
        child.terminate();child.wait();raise ValueError('Linux process identity unavailable; inspect '+str(out/'runner.log'))
    meta={'recorded_at':timestamp(),'pid':child.pid,'process_identity':identity,'output':str(out),'config':str(Path(config).resolve())};atomic_json(out/'launch.json',meta);POINTER.write_text(str(out)+'\n');event('Candidate worker launched',**meta,summary=str(out/'SUMMARY.md'),evidence=str(out/'evidence.zip'),log=str(out/'runner.log'))
    if wait:
        try:code=child.wait()
        except KeyboardInterrupt:
            if alive(meta):atomic_json(out/'stop-request.json',{'recorded_at':timestamp()});os.kill(child.pid,signal.SIGTERM)
            code=child.wait()
        event('Worker exited',exit_code=code,output=str(out))
        if code:raise SystemExit(code)

def status(out,meta):
    info={'runner_alive':alive(meta),'output':str(out),'summary':str(out/'SUMMARY.md'),'evidence':str(out/'evidence.zip'),'log':str(out/'runner.log'),'free_gib':shutil.disk_usage(ROOT).free/1024**3}
    if (out/'campaign.json').exists():
        d=load(out/'campaign.json');info.update(status=d['status'],phase=d.get('phase'),current_operation=d.get('current_operation'),rest_records=len(d['rest']),stationary_states=sum(r['status']=='stationary' for r in d['rest'].values()),case_records=len(d['cases']),motion_passes=sum(r['status']=='screen_pass' for r in d['cases'].values()),selected=d['selected'],error=d.get('error'))
        op=d.get('current_operation',{})
        if op.get('kind')=='preparation':
            p=out/'rest'/op['rest_id']/'history.json'
            if p.exists():info['latest_preparation_observation']=load(p)[-1]
        elif op.get('kind')=='motion':
            r=d['cases'].get(op['case_id'],{})
            if r.get('attempts'):
                from .sf_candidate_motion import local_path
                p=local_path(out,r['attempts'][-1])/'history.json'
                if p.exists():info['latest_motion_observation']=load(p)[-1]
    else:info['status']='starting; inspect runner.log if worker has exited'
    for name in ['heartbeat.json','exit.json']:
        if (out/name).exists():info[name[:-5]]=load(out/name)
    event('Status',**info)
    if (out/'runner.log').exists():
        with (out/'runner.log').open() as f:print(''.join(deque(f,maxlen=6)))

def preview(out,key,profile):
    import numpy as np
    from .sf_time import Grid,densities
    from .sf_candidate_motion import at,local_path
    from .sf_preview import PreviewWriter
    d=load(out/'campaign.json');need(d['status'].startswith('complete'),'Offline preview waits for campaign completion');need(key in d['cases'],'Unknown case; inspect case-metrics.csv');row=d['cases'][key];need(row.get('final_time',0)>0,'No evolved field in this case');g=Grid(tuple(row['physical']['grid']),tuple(row['physical']['lengths']),'fixed');times={0.,row['final_time']}
    for old in row['attempts']:
        p=local_path(out,old)/'snapshots.json'
        times.update(s['time'] for s in load(p) if s['time']<=row['final_time']+1e-12) if p.exists() else None
    dest=ART/'previews/s5-b-010'/out.name/(key+'-'+datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz'));need(not dest.exists(),'Preview destination exists');writer=PreviewWriter(dest,load(profile),g,key,{'recorded_at':timestamp(),'source_run':out.name,'config_sha256':d['config_sha256']})
    for t in sorted(times):
        n,v=at(out,row,t);writer.write(round(t/row['dt']),t,densities(n,v,g),{'recorded_at':timestamp(),'scope':'Offline display replay only'},initial=t==0.,final=abs(t-row['final_time'])<1e-12)
    writer.finish('complete');event('Offline ParaView preview created',output=str(dest),pvd=str(dest/'series.pvd'),instruction='Open series.pvd, Apply, select Volume representation and color by energy_density; reset camera and play. Full solver arrays and diagnostics are unchanged.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['preflight','start','foreground','status','stop','resume','preview','replay']);p.add_argument('--config',type=Path,default=CONFIG);p.add_argument('--case');p.add_argument('--profile',type=Path,default=PROFILE);a=p.parse_args();event('Candidate local command',mode=a.mode);ART.mkdir(exist_ok=True)
    with (ART/'SF-CANDIDATE-SURVEY-LAUNCH.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if a.mode=='preflight':preflight(a.config);return
        if a.mode in {'start','foreground'}:
            if POINTER.exists():need(not alive(current()[1]),'A candidate worker is already running')
            launch(a.config,wait=a.mode=='foreground');return
        out,meta=current()
        if a.mode=='status':status(out,meta)
        elif a.mode=='stop':
            if alive(meta):atomic_json(out/'stop-request.json',{'recorded_at':timestamp()});os.kill(meta['pid'],signal.SIGTERM);event('Checkpoint stop requested; wait for runner_alive=false before resume/publication')
            else:event('Worker already stopped; states retained')
        elif a.mode=='preview':need(a.case,'Preview requires --case CASE_ID');preview(out,a.case,a.profile)
        elif a.mode=='replay':
            need(not alive(meta) and load(out/'campaign.json')['status'].startswith('complete'),'Replay requires a completed campaign');dest=ART/'replays/s5-b-010'/out.name/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz')+'-'+secrets.token_hex(4));cmd=[sys.executable,'-m','electron_field_topology.sf_candidate_replay','--run',str(out),'--output',str(dest)]
            if a.case:cmd+=['--case',a.case]
            subprocess.run(cmd,cwd=ROOT,check=True)
        else:
            need(not alive(meta),'Worker already running')
            if (out/'campaign.json').exists():need(not load(out/'campaign.json')['status'].startswith('complete'),'Completed run is immutable; start makes a new record')
            launch(Path(meta['config']),out)
if __name__=='__main__':main()
