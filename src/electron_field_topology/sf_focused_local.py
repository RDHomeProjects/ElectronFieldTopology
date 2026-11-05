"""Local launch/status/stop/resume for S5-B-006."""
import argparse
from collections import deque
import json
import os
from pathlib import Path
import subprocess
import sys

from .sf_checkpoints import atomic_json, timestamp
from .sf_motion_local import process_identity
from .sf_focused_motion import CONFIG, ROOT, PROFILE

ART=ROOT/'artifacts'
POINTER=ART/'SF-FOCUSED-MOTION-CURRENT'


def alive(meta):
    identity=meta.get('process_identity')
    return identity is not None and process_identity(meta['pid'])==identity


def current():
    if not POINTER.exists():raise ValueError('No diagnostic campaign has been started in this checkout')
    out=Path(POINTER.read_text().strip())
    return out,json.loads((out/'launch.json').read_text())


def launch(source,config,out=None,wait=False):
    ART.mkdir(exist_ok=True)
    if out is None:
        from datetime import datetime, timezone
        import secrets
        label=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz').lower()+'-'+secrets.token_hex(4)
        out=ART/'s5-b'/'006-focused-motion-convergence'/label
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    (out/'stop-request.json').unlink(missing_ok=True)
    command=[sys.executable,'-u','-m','electron_field_topology.sf_focused_motion',
             '--source',str(Path(source).resolve()),'--config',str(Path(config).resolve()),'--output',str(out)]
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':os.environ.get('OMP_NUM_THREADS','2')}
    with (out/'runner.log').open('a') as log:
        log.write(json.dumps({'recorded_at':timestamp(),'command':command})+'\n');log.flush()
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,env=env,start_new_session=True)
    identity=process_identity(child.pid)
    if identity is None and not wait:
        child.terminate();child.wait()
        raise ValueError('Linux process identity unavailable; newly launched child stopped. Use foreground mode.')
    meta={'recorded_at':timestamp(),'pid':child.pid,'process_identity':identity,
          'source':str(Path(source).resolve()),'config':str(Path(config).resolve()),'output':str(out)}
    atomic_json(out/'launch.json',meta);POINTER.write_text(str(out)+'\n')
    print(json.dumps({**meta,'log':str(out/'runner.log'),'summary':str(out/'SUMMARY.md'),
                      'evidence':str(out/'evidence.zip')},indent=2),flush=True)
    if wait:
        try:code=child.wait()
        except KeyboardInterrupt:
            atomic_json(out/'stop-request.json',{'requested_at':timestamp()});code=child.wait()
        print(json.dumps({'recorded_at':timestamp(),'exit_code':code,'output':str(out)}),flush=True)
        if code:raise SystemExit(code)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['start','foreground','status','stop','resume'])
    p.add_argument('--source',type=Path);p.add_argument('--config',type=Path,default=CONFIG)
    a=p.parse_args();print(json.dumps({'recorded_at':timestamp(),'mode':a.mode}),flush=True)
    if a.mode in ('start','foreground'):
        if a.source is None:raise ValueError('--source must identify the completed original campaign')
        if POINTER.exists() and alive(current()[1]):raise ValueError('Diagnostics already running; use status')
        launch(a.source,a.config,wait=a.mode=='foreground');return
    out,meta=current()
    if a.mode=='status':
        info={'recorded_at':timestamp(),'runner_alive':alive(meta),'output':str(out),
              'summary':str(out/'SUMMARY.md'),'evidence':str(out/'evidence.zip')}
        if (out/'campaign.json').exists():
            d=json.loads((out/'campaign.json').read_text())
            info.update(status=d['status'],case_records=len(d['cases']),expected_cases=d['expected_cases'],
                        complete_cases=sum(r['status']=='complete' for r in d['cases'].values()),
                        error=d.get('error'))
            info['admission_records']=len(d['admissions'])
            for key,row in d['cases'].items():
                if row['status']=='working':
                    info['current_case']=key
                    if row['attempts']:
                        h=Path(row['attempts'][-1])/'history.json'
                        if h.exists():info['current_case_solver_step']=json.loads(h.read_text())[-1]['step']
                    info['current_case_total_steps']=row['physics']['steps']
        else:info['status']='authenticating_inputs_or_startup_failed; inspect log'
        if (out/'heartbeat.json').exists():info['heartbeat']=json.loads((out/'heartbeat.json').read_text())
        if (out/'exit.json').exists():info['exit']=json.loads((out/'exit.json').read_text())
        print(json.dumps(info,indent=2))
        with (out/'runner.log').open() as f:print(''.join(deque(f,maxlen=8)))
    elif a.mode=='stop':
        if alive(meta):
            atomic_json(out/'stop-request.json',{'requested_at':timestamp()})
            import signal
            os.kill(meta['pid'],signal.SIGTERM)
            print('Checkpoint stop requested. Use status until stopped; latest complete checkpoints are retained.')
        else:print('Runner is stopped; diagnostic and source records are retained.')
    elif a.mode=='resume':
        if alive(meta):raise ValueError('Diagnostics are already running')
        launch(Path(meta['source']),Path(meta['config']),out)


if __name__=='__main__':main()
