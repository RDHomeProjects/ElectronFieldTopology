"""Linux local lifecycle for the staged higher-Q screen. Apache-2.0."""
import argparse,hashlib,json,os,secrets,shutil,signal,subprocess,sys
from collections import deque
from datetime import datetime,timezone
from pathlib import Path
from .sf_higher_q import ROOT,CONFIG,validate
from .sf_higher_q_sources import event,need,load
from .sf_motion_local import process_identity
from .sf_checkpoints import timestamp,atomic_json
ART=ROOT/'artifacts';POINTER=ART/'SF-HIGHER-Q-CURRENT'
def alive(meta):return meta.get('process_identity') is not None and process_identity(meta['pid'])==meta['process_identity']
def current():
    need(POINTER.is_file(),'No higher-Q screen has been started in this checkout');out=Path(POINTER.read_text().strip());return out,load(out/'launch.json')
def retain_handover(out):
    package=os.environ.get('EFT_HIGHER_Q_HANDOVER')
    if not package:return
    package=Path(package);names=['SHA256SUMS'];target=out/'handover';target.mkdir(exist_ok=True)
    for line in (package/'SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1);need(Path(name).name==name and hashlib.sha256((package/name).read_bytes()).hexdigest()==digest,'Handover changed before archival snapshot');names.append(name)
    for name in names:
        p=target/name
        if p.exists():need(p.read_bytes()==(package/name).read_bytes(),'Retained handover differs; preserve existing run')
        else:shutil.copy2(package/name,p)
def launch(config,out=None,source_map=None,wait=False):
    validate(load(config))
    if out is None:out=ART/'s5-b/007-higher-q-motion'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz')+'-'+secrets.token_hex(4))
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);(out/'stop-request.json').unlink(missing_ok=True);retain_handover(out)
    command=[sys.executable,'-u','-m','electron_field_topology.sf_higher_q','--output',str(out),'--config',str(Path(config).resolve())]
    if source_map:command+=['--source-map',str(Path(source_map).resolve())]
    env={**os.environ,'OMP_NUM_THREADS':os.environ.get('OMP_NUM_THREADS','2'),'OPENBLAS_NUM_THREADS':'1','MPLBACKEND':'Agg','PYTHONDONTWRITEBYTECODE':'1'}
    with (out/'runner.log').open('a') as f:
        f.write(json.dumps({'recorded_at':timestamp(),'command':command})+'\n');f.flush();child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    identity=process_identity(child.pid)
    if identity is None:child.terminate();child.wait();raise ValueError('Linux process identity unavailable; worker stopped')
    meta={'recorded_at':timestamp(),'pid':child.pid,'process_identity':identity,'output':str(out),'config':str(Path(config).resolve()),'source_map':str(Path(source_map).resolve()) if source_map else None};atomic_json(out/'launch.json',meta);POINTER.parent.mkdir(exist_ok=True);POINTER.write_text(str(out)+'\n');event('Higher-Q worker launched',**meta,summary=str(out/'SUMMARY.md'),evidence=str(out/'evidence.zip'),log=str(out/'runner.log'))
    if wait:
        try:code=child.wait()
        except KeyboardInterrupt:
            if alive(meta):os.kill(child.pid,signal.SIGTERM)
            code=child.wait()
        event('Worker exited',exit_code=code,output=str(out))
        if code:raise SystemExit(code)
def status(out,meta):
    info={'runner_alive':alive(meta),'output':str(out),'summary':str(out/'SUMMARY.md'),'evidence':str(out/'evidence.zip'),'followup':str(out/'followup.json')}
    if (out/'campaign.json').exists():
        d=load(out/'campaign.json');info.update(status=d['status'],rest_candidates={k:r['status'] for k,r in d['rest'].items()},case_states={k:r['status'] for k,r in d['cases'].items()},error=d.get('error'))
        for key,r in d['rest'].items():
            if r['status'] in {'preparing','rest_stationary'}:
                h=out/'rest'/key/'history.json'
                if h.exists():info['latest_preparation_observation']=load(h)[-1]
        for key,r in d['cases'].items():
            if r['status']=='working' and r['attempts']:
                h=Path(r['attempts'][-1])/'history.json'
                if h.exists():info['latest_motion_observation']=load(h)[-1]
    else:info['status']='starting; inspect runner.log if worker has exited'
    for name in ['heartbeat.json','exit.json']:
        if (out/name).exists():info[name[:-5]]=load(out/name)
    event('Status',**info)
    if (out/'runner.log').exists():
        with (out/'runner.log').open() as f:print(''.join(deque(f,maxlen=6)))
def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('mode',choices=['start','foreground','status','stop','resume']);a.add_argument('--config',type=Path,default=CONFIG);a.add_argument('--source-map',type=Path);x=a.parse_args();event('Higher-Q local command',mode=x.mode)
    if x.mode in {'start','foreground'}:
        if POINTER.exists():need(not alive(current()[1]),'Higher-Q worker already running')
        launch(x.config,source_map=x.source_map,wait=x.mode=='foreground');return
    out,meta=current()
    if x.mode=='status':status(out,meta)
    elif x.mode=='stop':
        if alive(meta):atomic_json(out/'stop-request.json',{'recorded_at':timestamp()});os.kill(meta['pid'],signal.SIGTERM);event('Checkpoint stop requested; inspect status until stopped')
        else:event('Worker already stopped; all states retained')
    else:
        need(not alive(meta),'Worker already running')
        if (out/'campaign.json').exists():need(not load(out/'campaign.json')['status'].startswith('complete'),'Completed screen is immutable; start creates a new record')
        launch(Path(meta['config']),out,Path(meta['source_map']) if meta.get('source_map') else None)
if __name__=='__main__':main()
