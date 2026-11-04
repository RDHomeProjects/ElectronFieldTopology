"""Local-only background launch, status, checkpoint stop/resume and offline rendering."""
import argparse
from collections import deque
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
from .sf_checkpoints import atomic_json,timestamp

ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'artifacts';POINTER=ART/'SF-LOWQ-CURRENT'


def process_identity(pid):
    try:
        value=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        if value[0]=='Z':return None
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        namespace=os.readlink(f'/proc/{pid}/ns/pid')
        return boot+':'+namespace+':'+value[19]
    except (OSError,IndexError):return None


def current():
    if not POINTER.exists():raise ValueError('No local campaign pointer; run start first')
    out=Path(POINTER.read_text().strip());meta=json.loads((out/'launch.json').read_text())
    return out,meta


def alive(meta):return process_identity(meta['pid'])==meta['process_identity'] and meta['process_identity'] is not None


def launch(config,profile,out=None,wait=False):
    ART.mkdir(exist_ok=True)
    if out is None:
        stamp=timestamp()['melbourne'].replace(':','').replace('.','-')
        out=ART/f'lowq-motion-{stamp}-{os.getpid()}'
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    logfile=out/'runner.log'
    cmd=[sys.executable,'-u','-m','electron_field_topology.sf_lowq_motion','--config',str(config),'--profile',str(profile),'--output',str(out)]
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':os.environ.get('OMP_NUM_THREADS','2')}
    with logfile.open('a') as stream:
        stream.write(json.dumps({'launched_at':timestamp(),'command':cmd})+'\n');stream.flush()
        p=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,start_new_session=not wait,cwd=ROOT,env=env)
    identity=process_identity(p.pid)
    if identity is None and not wait:
        p.terminate();p.wait()
        raise ValueError('Linux process identity unavailable; the new child was stopped. Use foreground mode instead.')
    meta={'launched_at':timestamp(),'pid':p.pid,'process_identity':identity,'config':str(config),'profile':str(profile),'log':str(logfile),'output':str(out)}
    atomic_json(out/'launch.json',meta);POINTER.write_text(str(out)+'\n');print(json.dumps(meta,indent=2),flush=True)
    if wait:
        code=p.wait();print(json.dumps({'finished_at':timestamp(),'exit_code':code}),flush=True)
        if code:raise SystemExit(code)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['start','resume','status','stop','smoke','foreground','render'])
    p.add_argument('--config',type=Path,default=ROOT/'experiments/configs/sf-motion/lowq-motion.json')
    p.add_argument('--profile',type=Path);p.add_argument('--case')
    a=p.parse_args();a.profile=a.profile or ROOT/('experiments/configs/renderers/basic.json' if a.mode=='smoke' else 'experiments/configs/renderers/lowq.json');print(json.dumps({'recorded_at':timestamp(),'mode':a.mode}),flush=True)
    if a.mode in ('start','smoke','foreground'):
        if POINTER.exists():
            _,meta=current()
            if alive(meta):raise ValueError('Current campaign is running; use status/stop before starting another')
        config=ROOT/'experiments/configs/sf-motion/smoke.json' if a.mode=='smoke' else a.config.resolve()
        launch(config,a.profile.resolve(),wait=a.mode=='foreground');return
    out,meta=current()
    if a.mode=='status':
        print(json.dumps({'runner_alive':alive(meta),'output':str(out),'summary':str(out/'SUMMARY.md'),'evidence':str(out/'evidence.zip')},indent=2))
        if (out/'campaign.json').exists():
            c=json.loads((out/'campaign.json').read_text());print(json.dumps({'updated_at':c['updated_at'],'status':c['status'],'rest_candidates_recorded':len(c['seeds']),'case_records':len(c['cases']),'error':c.get('error')},indent=2))
        with Path(meta['log']).open() as stream:print(''.join(deque(stream,maxlen=6)))
    elif a.mode=='stop':
        if alive(meta):os.kill(meta['pid'],signal.SIGTERM);print('Checkpoint stop requested. Use status until the runner is stopped.')
        else:print('Runner is already stopped; retained files were preserved.')
    elif a.mode=='resume':
        if alive(meta):raise ValueError('Runner is already running')
        launch(Path(meta['config']),Path(meta['profile']),out)
    elif a.mode=='render':
        if alive(meta):raise ValueError('Wait for the solver to stop before offline rendering')
        c=json.loads((out/'campaign.json').read_text());cases=[r for r in c['cases'].values() if r['status']=='complete']
        if a.case:cases=[r for r in cases if r['id']==a.case]
        if not cases:raise ValueError('No requested complete case to render')
        cases.sort(key=lambda r:(r['beta']==0,r['physical']['dt'],-max(r['physical']['grid']),r['id']))
        row=cases[0];source=Path(row['attempts'][-1]);target=ART/f'render-lowq-{timestamp()["utc"].replace(":","")}-{os.getpid()}'
        subprocess.run([sys.executable,'-m','electron_field_topology.sf_renderer','--input',str(source),'--profile',str(a.profile.resolve()),'--output',str(target)],check=True,cwd=ROOT)
        (ART/'SF-LOWQ-RENDER-CURRENT').write_text(str(target)+'\n')
        print(json.dumps({'rendered_at':timestamp(),'case':row['id'],'case_admitted':row['assessment']['bounded_case_gates_pass'],'viewer':str(target/'viewer.html')},indent=2))
        print('Open: xdg-open '+shlex.quote(str(target/'viewer.html')))
        print('ParaView: paraview '+shlex.quote(str(source/'preview/series.pvd')))
        print('In ParaView select energy_density and change Outline to Volume, then Play.')


if __name__=='__main__':main()
