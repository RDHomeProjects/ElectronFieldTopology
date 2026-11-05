"""Local S5-B-008 worker lifecycle; exact Linux process identity. Apache-2.0."""
import argparse
import hashlib
import shutil
from collections import deque
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
from datetime import datetime,timezone
from .sf_tail_domain import CONFIG,ROOT,source_inventory
from .sf_motion_local import process_identity
from .sf_motion_diagnostics import atomic_json,event
from .sf_checkpoints import timestamp
ART=ROOT/'artifacts';POINTER=ART/'SF-TAIL-DOMAIN-CURRENT'
DEFAULT_SOURCE=Path.home()/'ElectronFieldTopology-lowq-motion/artifacts/lowq-motion-2026-11-03T104629-568611+1100-30672'
def alive(meta):return meta.get('process_identity') is not None and process_identity(meta['pid'])==meta['process_identity']
def current():
    if not POINTER.is_file():raise ValueError('No tail-domain campaign has been started in this checkout')
    out=Path(POINTER.read_text().strip());return out,json.loads((out/'launch.json').read_text())
def launch(source,config,out=None,wait=False):
    source=Path(source).resolve();config=Path(config).resolve()
    inv,_=source_inventory(source,json.loads(config.read_text()));event('Two source rest fields authenticated',input_fingerprint=inv['input_fingerprint'])
    if out is None:
        rid=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz')+'-'+secrets.token_hex(4)
        out=ART/'s5-b/008-tail-domain-screening'/rid
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);(out/'stop-request.json').unlink(missing_ok=True)
    # Retain the runnable download with the full run archive, without secrets/caches.
    package=os.environ.get('EFT_TAIL_HANDOVER')
    if package:
        package=Path(package);snapshot=out/'handover';snapshot.mkdir(exist_ok=True)
        names=['SHA256SUMS']
        for line in (package/'SHA256SUMS').read_text().splitlines():
            digest,name=line.split('  ',1)
            if Path(name).name!=name or hashlib.sha256((package/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Handover snapshot checksum differs')
            names.append(name)
        for name in names:
            target=snapshot/name
            if target.exists() and target.read_bytes()!=(package/name).read_bytes():
                raise ValueError('Retained handover snapshot differs; preserve completed records')
            if not target.exists():shutil.copy2(package/name,target)
    command=[sys.executable,'-u','-m','electron_field_topology.sf_tail_domain','--source',str(source),'--config',str(config),'--output',str(out)]
    env={**os.environ,'OMP_NUM_THREADS':os.environ.get('OMP_NUM_THREADS','2'),'OPENBLAS_NUM_THREADS':'1','MPLBACKEND':'Agg'}
    with (out/'runner.log').open('a') as log:
        log.write(json.dumps({'recorded_at':timestamp(),'command':command})+'\n');log.flush()
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    identity=process_identity(child.pid)
    if identity is None:
        child.terminate();child.wait();raise ValueError('Linux identity unavailable; worker stopped before unsafe PID tracking')
    meta={'recorded_at':timestamp(),'pid':child.pid,'process_identity':identity,'source':str(source),'config':str(config),'output':str(out)}
    atomic_json(out/'launch.json',meta);POINTER.parent.mkdir(exist_ok=True);POINTER.write_text(str(out)+'\n')
    event('Worker launched',**meta,log=str(out/'runner.log'),summary=str(out/'SUMMARY.md'),evidence=str(out/'evidence.zip'))
    if wait:
        try:code=child.wait()
        except KeyboardInterrupt:
            if alive(meta):os.kill(child.pid,signal.SIGTERM)
            code=child.wait()
        event('Worker exited',exit_code=code,output=str(out))
        if code:raise SystemExit(code)
def status(out,meta):
    info={'runner_alive':alive(meta),'output':str(out),'summary':str(out/'SUMMARY.md'),'evidence':str(out/'evidence.zip')}
    if (out/'campaign.json').is_file():
        d=json.loads((out/'campaign.json').read_text());info.update(status=d['status'],expected_cases=6,
            recorded_cases=len(d['cases']),stationary_cases=sum(r['status']=='stationary' for r in d['cases'].values()),error=d.get('error'))
        working=[r for r in d['cases'].values() if r['status']=='working']
        if working:
            r=working[-1];info['current_case']=r['id'];h=out/'readmission'/r['id']/'history.json'
            if h.is_file():info['last_optimizer_record']=json.loads(h.read_text())[-1]
    else:info['status']='starting; inspect runner.log if the worker has exited'
    for name in ['heartbeat.json','exit.json']:
        if (out/name).is_file():info[name[:-5]]=json.loads((out/name).read_text())
    event('Status',**info)
    with (out/'runner.log').open() as f:print(''.join(deque(f,maxlen=6)))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['start','foreground','status','stop','resume'])
    p.add_argument('--source',type=Path,default=DEFAULT_SOURCE);p.add_argument('--config',type=Path,default=CONFIG);a=p.parse_args();event('Tail-domain local command',mode=a.mode)
    if a.mode in {'start','foreground'}:
        if POINTER.exists() and alive(current()[1]):raise ValueError('Tail-domain worker already running')
        launch(a.source,a.config,wait=a.mode=='foreground');return
    out,meta=current()
    if a.mode=='status':status(out,meta)
    elif a.mode=='stop':
        if alive(meta):
            atomic_json(out/'stop-request.json',{'recorded_at':timestamp()});os.kill(meta['pid'],signal.SIGTERM);event('Checkpoint stop requested; use status until stopped')
        else:event('Worker already stopped; all local results retained')
    else:
        if alive(meta):raise ValueError('Worker already running')
        if (out/'campaign.json').is_file() and json.loads((out/'campaign.json').read_text())['status'].startswith('complete'):
            raise ValueError('Completed campaign is immutable; use start for a genuinely new run')
        launch(Path(meta['source']),Path(meta['config']),out)
if __name__=='__main__':main()
