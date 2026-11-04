"""Local launch/status/stop/resume for S5-B-005."""
import argparse
from collections import deque
import json
import os
from pathlib import Path
import subprocess
import sys

from .sf_checkpoints import atomic_json, timestamp
from .sf_motion_local import process_identity
from .sf_boost_study import CONFIG, ROOT

ART=ROOT/'artifacts'
POINTER=ART/'SF-BOOST-STUDY-CURRENT'


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
        out=ART/'s5-b'/'005-boost-initialization'/label
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    (out/'stop-request.json').unlink(missing_ok=True)
    command=[sys.executable,'-u','-m','electron_field_topology.sf_boost_study',
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
        if (out/'study.json').exists():
            d=json.loads((out/'study.json').read_text())
            info.update(status=d['status'],case_records=len(d['cases']),expected_cases=d['expected_cases'],
                        controls_passed=d.get('controls',{}).get('passed'),error=d.get('error'))
        else:info['status']='authenticating_inputs_or_startup_failed; inspect log'
        if (out/'exit.json').exists():info['exit']=json.loads((out/'exit.json').read_text())
        print(json.dumps(info,indent=2))
        with (out/'runner.log').open() as f:print(''.join(deque(f,maxlen=8)))
    elif a.mode=='stop':
        if alive(meta):
            atomic_json(out/'stop-request.json',{'requested_at':timestamp()})
            print('Stop requested. Current audit unit will finish; use status until stopped.')
        else:print('Runner is stopped; diagnostic and source records are retained.')
    elif a.mode=='resume':
        if alive(meta):raise ValueError('Diagnostics are already running')
        launch(Path(meta['source']),Path(meta['config']),out)


if __name__=='__main__':main()
