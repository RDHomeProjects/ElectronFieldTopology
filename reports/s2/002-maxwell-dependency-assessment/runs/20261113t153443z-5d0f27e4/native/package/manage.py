"""Local workstation lifecycle; standard-library only, no GitHub calls."""
import argparse,hashlib,json,os,secrets,signal,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

PACKAGE=Path(__file__).resolve().parent
def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def emit(**kw):print(json.dumps({'recorded_at':stamp(),**kw}))
def verify(repo):
    if not __debug__:raise ValueError('Run without Python optimization')
    manifest=PACKAGE/'SHA256SUMS'
    for line in manifest.read_text().splitlines():
        expected,name=line.split('  ',1);path=(PACKAGE/name).resolve()
        if not path.is_relative_to(PACKAGE) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Package hash mismatch: '+name)
    expected={'fields.py':'1926edeeabb360b77f87eb8f00bcce412ab102b540d9d5282e56007e0f577688','evolution.py':'c1a3b8820fc192ce25fca332004623be838d400404830ddbabaf97d35d3d8735'}
    for n,h in expected.items():
        if hashlib.sha256((repo/'src/electron_field_topology'/n).read_bytes()).hexdigest()!=h:raise ValueError('Workstation source mismatch: '+n+'; no files were overwritten')
    for n in ['pyproject.toml','uv.lock','docs/project/roadmap.json']:
        if not (repo/n).is_file():raise ValueError('Missing existing checkout file: '+n)
    return True
def alive(pid,out):
    try:
        os.kill(pid,0)
        args=Path('/proc')/str(pid)/'cmdline'
        raw=args.read_bytes().replace(b'\0',b' ').decode()
        return 'extension.py' in raw and str(out) in raw
    except (ProcessLookupError,FileNotFoundError,PermissionError):return False
def running_pid(out,status):
    pid=status.get('pid',0)
    if pid and alive(pid,out):return pid
    launch=out/'launch.json'
    if launch.exists():
        pid=json.loads(launch.read_text()).get('launcher_pid',0)
        if pid and alive(pid,out):return pid
    return None
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','qualify','run','status','resume','stop','smoke']);p.add_argument('--repo',type=Path,default=Path(os.environ.get('EFT_REPO',str(Path.home()/'ElectronFieldTopology-repository-admin'))));a=p.parse_args();repo=a.repo.expanduser().resolve();artifacts=repo/'artifacts';pointer=artifacts/'MAXWELL-BOUNDED-VALIDATION-CURRENT'
    if a.mode not in ['status','stop']:verify(repo)
    current=Path(pointer.read_text().strip()) if pointer.exists() else None
    if a.mode=='verify':emit(status='package_and_source_verified',repo=str(repo));return 0
    if a.mode in ['status','stop']:
        if current is None:emit(status='not_started');return 0
        sp=current/'status.json';status=json.loads(sp.read_text()) if sp.exists() else {};pid=running_pid(current,status);running=pid is not None
        if a.mode=='stop' and running:
            os.kill(pid,signal.SIGTERM);emit(status='stop_requested',output=str(current));return 0
        emit(**{**status,'runner_alive':running,'output':str(current),'log':str(current/'runner.log')});return 0
    env=os.environ.copy()
    for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:env[n]=os.environ.get('EFT_THREADS','6')
    if a.mode in ['qualify','smoke']:
        kind='qualification' if a.mode=='qualify' else 'smoke';out=artifacts/'maxwell-bounded-validation'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4)+'-'+kind)
        cmd=['uv','run','--frozen','--python','3.12.14','python',str(PACKAGE/'extension.py'),'qualify' if a.mode=='qualify' else 'run','--repo',str(repo),'--output',str(out)]
        if a.mode=='smoke':cmd.append('--smoke')
        emit(status='starting_'+kind,output=str(out));return subprocess.run(cmd,cwd=repo,env=env).returncode
    if current is not None:
        status=json.loads((current/'status.json').read_text()) if (current/'status.json').exists() else {}
        if running_pid(current,status):emit(status='already_running',output=str(current));return 0
        if a.mode=='resume' and status.get('status')=='complete_pending_review':emit(status='already_complete_pending_review',output=str(current));return 0
    if a.mode=='resume':
        if current is None or not (current/'record.json').exists():raise ValueError('No resumable current run')
        out=current
    else:
        out=artifacts/'maxwell-bounded-validation'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4));out.mkdir(parents=True)
    pointer.parent.mkdir(parents=True,exist_ok=True);pointer.write_text(str(out)+'\n')
    cmd=['uv','run','--frozen','--python','3.12.14','python',str(PACKAGE/'extension.py'),'run','--repo',str(repo),'--output',str(out)]
    with (out/'runner.log').open('a') as log:proc=subprocess.Popen(cmd,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    # uv may launch a child Python process; extension status owns its real PID.
    (out/'launch.json').write_text(json.dumps({'recorded_at':stamp(),'launcher_pid':proc.pid,'argv':cmd},indent=2)+'\n')
    time.sleep(.5);emit(status='started',output=str(out),log=str(out/'runner.log'));return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as e:emit(status='error',error=str(e));raise SystemExit(1)
