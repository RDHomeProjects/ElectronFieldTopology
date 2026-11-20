"""Record completed research locally, then run a static field diagnosis."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import uuid
from common import ROOT, load, log, need, save, sha, stamp, verify_manifest
from integrity import alive, baseline, host, preflight, process_identity, verify_sources

UNIT = 'matter-waves-field-diagnosis.service'
GIB = 1024**3

def pointer(repo):
    return repo / '.git/field-diagnosis-last.json'

def output(repo):
    need(pointer(repo).exists(), 'No field diagnosis exists; run after preflight')
    return Path(load(pointer(repo))['output'])

def live(out):
    return any(alive(load(out / name)) for name in ['supervisor.json', 'heartbeat.json'] if (out / name).exists())

def service_active():
    p = subprocess.run(['systemctl', 'is-active', UNIT], text=True, capture_output=True)
    return p.stdout.strip() in ('active', 'activating', 'deactivating')

def pressure(path=Path('/proc/pressure/memory')):
    return {label: {k: float(v) for k, v in (item.split('=') for item in fields)} for label, *fields in (row.split() for row in path.read_text().splitlines())}

def pressure_stop(sample, clock, began):
    available = sample['host']['available_gib']
    condition = available < 2 or (available < 4 and sample['pressure'].get('full', {}).get('avg10', 0) >= 20)
    began = clock if condition and began is None else began if condition else None
    return bool(condition and clock - began >= 30), began

def group_path():
    group = next(row.split('::', 1)[1] for row in Path('/proc/self/cgroup').read_text().splitlines() if row.startswith('0::'))
    return Path('/sys/fs/cgroup') / group.lstrip('/')

def group_info(group):
    result = {}
    for name in ['memory.current', 'memory.peak', 'memory.swap.current']:
        if (group / name).exists():
            result[name] = int((group / name).read_text())
    if (group / 'memory.events').exists():
        result['memory.events'] = {k: int(v) for k, v in (line.split() for line in (group / 'memory.events').read_text().splitlines())}
    if (group / 'memory.pressure').exists():
        result['memory.pressure'] = pressure(group / 'memory.pressure')
    return result

def launch_argv(repo, out):
    return ['sudo', 'systemd-run', '--unit=' + UNIT, '--collect', '--service-type=exec', '--property=WorkingDirectory=' + str(repo),
            '--property=MemoryAccounting=yes', '--property=MemoryHigh=' + str(7 * GIB), '--property=MemoryMax=' + str(8 * GIB),
            '--property=MemorySwapMax=' + str(GIB), '--property=Restart=no', '--property=OOMPolicy=stop',
            '--property=TimeoutStopSec=infinity', '--property=SendSIGKILL=no', shutil.which('systemd-inhibit'),
            '--what=sleep:idle:handle-lid-switch', '--mode=block', '--who=Matter Waves', '--why=Read-only retained-field diagnosis',
            shutil.which('setpriv'), '--reuid=' + str(os.getuid()), '--regid=' + str(os.getgid()), '--init-groups', '--reset-env',
            '/usr/bin/python3', '-B', str(out / 'handover/handover.py'), 'supervise', '--repo', str(repo), '--output', str(out)]

def start(repo, resume=False):
    need(os.geteuid() != 0, 'Run as rd; sudo is needed only for the isolated service')
    need(not service_active(), 'Diagnostic service already active; use status/stop')
    receipt = preflight(repo)
    if resume:
        out = output(repo)
        need(not live(out), 'A diagnostic worker is already active')
        need(load(out / 'status.json')['status'] in ('interrupted', 'working', 'starting'), 'Failed/completed diagnosis needs review, not automatic resume')
        need(load(out / 'identity.json')['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Resume with the same package')
        verify_manifest(out / 'handover')
        if (out / 'STOP.json').exists():
            (out / 'STOP.json').rename(out / ('STOP-retained-' + uuid.uuid4().hex[:8] + '.json'))
    else:
        need(not pointer(repo).exists(), 'A diagnosis is already recorded; use status/resume rather than silently duplicating it')
        rid = datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-') + uuid.uuid4().hex[:8]
        out = repo / 'artifacts/q17-q32-field-diagnosis' / rid
        out.mkdir(parents=True, exist_ok=False)
        shutil.copytree(ROOT, out / 'handover', ignore=shutil.ignore_patterns('__pycache__'))
        save(out / 'identity.json', {'recorded_at': stamp(), 'run_id': rid, 'package_sha256': sha(ROOT / 'SHA256SUMS'),
                                    'plan_sha256': sha(ROOT / 'PLAN.json'), 'source_identity': verify_sources(repo), 'completed_source_run_id': '20261120t003653z-a200a9db',
                                    'execution': 'CPU static diagnostics only', 'cpu_threads': 4, 'optimizer_steps': 0, 'physical_time_steps': 0})
        save(pointer(repo), {'recorded_at': stamp(), 'output': str(out), 'unit': UNIT})
    save(out / 'PREFLIGHT.json', receipt)
    save(out / 'LAUNCH-CONFIG.json', {'recorded_at': stamp(), 'uid': os.getuid(), 'repo': str(repo), 'output': str(out),
                                    'executable_path': str(Path(shutil.which('uv')).parent) + ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})
    save(out / 'status.json', {'recorded_at': stamp(), 'status': 'starting', 'phase': 'supervisor-launch', 'optimizer_steps': 0, 'physical_time_steps': 0})
    subprocess.run(['sudo', '-v'], check=True)
    subprocess.run(launch_argv(repo, out), check=True)
    log('Static diagnosis service requested', output=str(out), report=str(out / 'REPORT.html'), optimizer_steps=0, physical_time_steps=0)

def supervise(repo, out):
    need(os.geteuid() != 0, 'Diagnostic worker must run as the normal user')
    cfg = load(out / 'LAUNCH-CONFIG.json')
    need(cfg['uid'] == os.getuid() and cfg['repo'] == str(repo) and cfg['output'] == str(out), 'Supervisor identity differs')
    os.environ['PATH'] = cfg['executable_path']
    verify_manifest(ROOT)
    group = group_path()
    need(group.name == UNIT and 'system.slice' in group.parts, 'Worker is not in the isolated system service')
    for name, limit in [('memory.high', 7 * GIB), ('memory.max', 8 * GIB), ('memory.swap.max', GIB)]:
        need((group / name).read_text().strip() == str(limit), 'Resource limit not applied: ' + name)
    save(out / 'supervisor.json', {'recorded_at': stamp(), 'pid': os.getpid(), 'process_identity': process_identity(os.getpid())})
    stop = False
    def request(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, request)
    signal.signal(signal.SIGINT, request)
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4', PYTHONDONTWRITEBYTECODE='1')
    # Retain the existing GPU dependency set, but never initialize CUDA here.
    argv = ['uv', 'run', '--frozen', '--extra', 'gpu', '--python', '3.12.14', 'python', '-u', '-B', str(ROOT / 'worker.py'), '--repo', str(repo), '--output', str(out)]
    began, signalled = None, False
    with (out / 'runner.log').open('a') as stream:
        process = subprocess.Popen(argv, cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        save(out / 'worker-launch.json', {'recorded_at': stamp(), 'pid': process.pid, 'process_identity': process_identity(process.pid), 'argv': argv})
        def child_alive():
            return (out / 'heartbeat.json').exists() and alive(load(out / 'heartbeat.json'))
        while process.poll() is None or child_alive():
            sample = {'recorded_at': stamp(), 'host': host(), 'pressure': pressure(), 'cgroup': group_info(group)}
            save(out / 'telemetry-latest.json', sample)
            with (out / 'telemetry.jsonl').open('a') as telemetry:
                telemetry.write(json.dumps(sample) + '\n')
            unsafe, began = pressure_stop(sample, time.monotonic(), began)
            if (unsafe or stop or (out / 'STOP.json').exists()) and not signalled:
                save(out / 'PAUSE-REQUEST.json', {'recorded_at': stamp(), 'reason': 'resource_pressure' if unsafe else 'operator_stop'})
                os.killpg(process.pid, signal.SIGTERM)
                signalled = True
                log('Orderly diagnostic pause requested; current static field evaluation may take several minutes')
            time.sleep(5)
    current = load(out / 'status.json')
    if process.returncode != 0 and current['status'] not in ('interrupted', 'failed'):
        oom = group_info(group).get('memory.events', {}).get('oom_kill', 0) > 0
        save(out / 'status.json', {'recorded_at': stamp(), 'status': 'interrupted' if oom else 'failed', 'error': 'Worker exited before sealing; completed cases remain reusable', 'exit_code': process.returncode})
    current = load(out / 'status.json')
    log('Diagnostic supervisor finished', status=current, exit_code=process.returncode, output=str(out))
    return 0 if current['status'] in ('complete_pending_review', 'interrupted') else process.returncode or 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['verify', 'install', 'publish', 'merge', 'preflight', 'run', 'resume', 'status', 'stop', 'record-diagnosis', 'supervise'])
    parser.add_argument('--repo', type=Path, default=Path.home() / 'ElectronFieldTopology-adaptive-q-screen-20261117')
    parser.add_argument('--publication', type=Path, default=Path.home() / 'ElectronFieldTopology-results-diagnosis-record-20261120')
    parser.add_argument('--output', type=Path)
    a = parser.parse_args()
    repo, pub = a.repo.expanduser().resolve(), a.publication.expanduser().resolve()
    if a.mode == 'verify':
        count = verify_manifest(ROOT)
        objects, hashes, _ = baseline()
        plan = load(ROOT / 'PLAN.json')
        need(plan['optimizer_steps'] == plan['physical_time_steps'] == 0 and len(plan['fields']) == 5, 'Diagnostic scope differs')
        need(objects['record.json']['additional_attempts'] == 225, 'Completed result identity differs')
        log('Results-and-diagnosis package verified', files=count, compact_payloads=len(hashes), fields=5, optimizer_steps=0, physical_time_steps=0)
    elif a.mode in ('install', 'publish', 'merge', 'record-diagnosis'):
        import publication
        publication.execute(a.mode, repo, pub)
    elif a.mode == 'preflight':
        log('Read-only field preflight', **preflight(repo))
    elif a.mode in ('run', 'resume'):
        start(repo, a.mode == 'resume')
    elif a.mode == 'supervise':
        need(a.output is not None, 'Supervisor output is required')
        return supervise(repo, a.output.resolve())
    elif a.mode == 'stop':
        out = output(repo)
        if live(out) or service_active():
            save(out / 'STOP.json', {'recorded_at': stamp(), 'reason': 'operator_stop'})
            log('Orderly stop requested; wait for current field diagnosis and status update', output=str(out))
        else:
            log('Diagnosis already stopped', output=str(out))
    else:
        if not pointer(repo).exists():
            log('No field diagnosis created')
            return 0
        out = output(repo)
        log('Retained-field diagnosis status', output=str(out), runner_alive=live(out), service_active=service_active(),
            status=load(out / 'status.json'), heartbeat=load(out / 'heartbeat.json') if (out / 'heartbeat.json').exists() else None,
            telemetry=load(out / 'telemetry-latest.json') if (out / 'telemetry-latest.json').exists() else None,
            report=str(out / 'REPORT.html'), evidence=str(out / 'evidence.zip'), log=str(out / 'runner.log'))
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        log('Results-and-diagnosis handover stopped', error=str(error))
        raise SystemExit(1)
