"""Local-workstation launcher, memory supervision and local-only publication."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from common import ROOT, canonical, load, log, need, save, sha, stamp, verify_manifest
from integrity import AUDIT_SHA, UNIT, alive, baseline, host, preflight, process_identity

GIB = 1024**3

def pointer(repo):
    return repo / '.git/policy-v2-last-run.json'

def output(repo):
    need(pointer(repo).exists(), 'No continuation run exists; use run after preflight')
    return Path(load(pointer(repo))['output'])

def service_active():
    p = subprocess.run(['systemctl', 'is-active', UNIT], text=True, capture_output=True)
    return p.stdout.strip() in ('active', 'activating', 'deactivating')

def is_live(out):
    return any(alive(load(out / name)) for name in ['supervisor.json', 'heartbeat.json'] if (out / name).exists())

def status(repo):
    if not pointer(repo).exists():
        log('No continuation run created', original_campaign_modified=False)
        return
    out = output(repo)
    log('Policy-v2 continuation status', output=str(out), runner_alive=is_live(out), service_active=service_active(),
        status=load(out / 'status.json') if (out / 'status.json').exists() else {'status': 'not_started'},
        heartbeat=load(out / 'heartbeat.json') if (out / 'heartbeat.json').exists() else None,
        telemetry=load(out / 'telemetry-latest.json') if (out / 'telemetry-latest.json').exists() else None,
        evidence=str(out / 'evidence.zip'), report=str(out / 'REPORT.html'), log=str(out / 'runner.log'))

def pressure(path=Path('/proc/pressure/memory')):
    return {label: {k: float(v) for k, v in (x.split('=') for x in fields)} for label, *fields in (line.split() for line in path.read_text().splitlines())}

def pressure_stop(sample, clock, began):
    available = sample['host']['available_gib']
    psi = sample['pressure'].get('full', {}).get('avg10', 0)
    condition = available < 2 or (available < 4 and psi >= 20)
    began = clock if condition and began is None else began if condition else None
    return bool(condition and clock - began >= 30), began

def cgroup():
    name = next(x.split('::', 1)[1] for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::'))
    return Path('/sys/fs/cgroup') / name.lstrip('/')

def cgroup_info(group):
    result = {}
    for name in ['memory.current', 'memory.peak', 'memory.swap.current']:
        if (group / name).exists():
            result[name] = int((group / name).read_text())
    for name in ['memory.events', 'cpu.stat']:
        if (group / name).exists():
            result[name] = {k: int(v) for k, v in (line.split() for line in (group / name).read_text().splitlines())}
    if (group / 'memory.pressure').exists():
        result['memory.pressure'] = pressure(group / 'memory.pressure')
    return result

def launch_argv(repo, out):
    return ['sudo', 'systemd-run', '--unit=' + UNIT, '--collect', '--service-type=exec',
            '--property=WorkingDirectory=' + str(repo), '--property=MemoryAccounting=yes',
            '--property=MemoryHigh=' + str(7 * GIB), '--property=MemoryMax=' + str(8 * GIB), '--property=MemorySwapMax=' + str(GIB),
            '--property=Restart=no', '--property=OOMPolicy=stop', '--property=TimeoutStopSec=infinity', '--property=SendSIGKILL=no',
            shutil.which('systemd-inhibit'), '--what=sleep:idle:handle-lid-switch', '--mode=block', '--who=Matter Waves',
            '--why=Checkpoint-preserving Q17-Q32 policy-v2 continuation', shutil.which('setpriv'),
            '--reuid=' + str(os.getuid()), '--regid=' + str(os.getgid()), '--init-groups', '--reset-env',
            '/usr/bin/python3', '-B', str(out / 'handover/handover.py'), 'supervise', '--repo', str(repo), '--output', str(out)]

def start(repo, resume=False):
    need(os.geteuid() != 0, 'Run as rd; sudo is used only for the isolated system service')
    need(not service_active(), 'Continuation service is already active; use status or stop')
    receipt = preflight(repo)
    if resume:
        out = output(repo)
        need(not is_live(out), 'A continuation worker is already active')
        current = load(out / 'status.json')
        need(current['status'] in ('interrupted', 'working', 'starting'), 'Only an interrupted/abandoned working run can resume; failed/completed runs require assessment')
        need(load(out / 'identity.json')['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Use the same continuation package to resume')
        verify_manifest(out / 'handover')
        if (out / 'STOP.json').exists():
            old = out / ('STOP-retained-' + uuid.uuid4().hex[:8] + '.json')
            (out / 'STOP.json').rename(old)
    else:
        need(not pointer(repo).exists(), 'An existing continuation record is retained; use status/resume, never silently create a duplicate run')
        rid = datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-') + uuid.uuid4().hex[:8]
        out = repo / 'artifacts/q17-q32-policy-v2' / rid
        out.mkdir(parents=True, exist_ok=False)
        shutil.copytree(ROOT, out / 'handover', ignore=shutil.ignore_patterns('__pycache__'))
        identity = {'recorded_at': stamp(), 'run_id': rid, 'policy_version': 2, 'package_sha256': sha(ROOT / 'SHA256SUMS'),
                    'original_source_identity': canonical(baseline()[0]['identity.json']), 'original_run_id': '20261117t133953z-d6617788',
                    'audit_archive_sha256': AUDIT_SHA,
                    'total_attempt_ceiling_per_selected_branch': 500, 'maximum_additional_attempts': 1738,
                    'backend': 'retained CUDA per branch; CPU diagnostics; no backend substitution', 'cpu_threads': 4}
        save(out / 'identity.json', identity)
        save(pointer(repo), {'recorded_at': stamp(), 'output': str(out), 'unit': UNIT})
    save(out / 'PREFLIGHT.json', receipt)
    save(out / 'LAUNCH-CONFIG.json', {'recorded_at': stamp(), 'uid': os.getuid(), 'repo': str(repo), 'output': str(out),
                                    'executable_path': str(Path(shutil.which('uv')).parent) + ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})
    save(out / 'status.json', {'recorded_at': stamp(), 'status': 'starting', 'phase': 'supervisor-launch'})
    subprocess.run(['sudo', '-v'], check=True)
    subprocess.run(launch_argv(repo, out), check=True)
    log('Continuation service requested', output=str(out), unit=UNIT, maximum_additional_attempts=1738,
        note='Startup is not proof of numerical progress; inspect status', report=str(out / 'REPORT.html'))

def supervise(repo, out):
    need(os.geteuid() != 0, 'Worker must not run as root')
    cfg = load(out / 'LAUNCH-CONFIG.json')
    need(cfg['uid'] == os.getuid() and cfg['repo'] == str(repo) and cfg['output'] == str(out), 'Supervisor launch identity differs')
    os.environ['PATH'] = cfg['executable_path']
    verify_manifest(ROOT)
    group = cgroup()
    need(group.name == UNIT and 'system.slice' in group.parts, 'Supervisor must be inside the isolated system service')
    for name, limit in [('memory.high', 7 * GIB), ('memory.max', 8 * GIB), ('memory.swap.max', GIB)]:
        need((group / name).read_text().strip() == str(limit), 'Resource limit was not applied: ' + name)
    save(out / 'supervisor.json', {'recorded_at': stamp(), 'pid': os.getpid(), 'process_identity': process_identity(os.getpid())})
    stop = False
    def request(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, request)
    signal.signal(signal.SIGINT, request)
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4', PYTHONDONTWRITEBYTECODE='1')
    command = ['uv', 'run', '--frozen', '--extra', 'gpu', '--python', '3.12.14', 'python', '-u', '-B', str(ROOT / 'worker.py'), '--repo', str(repo), '--output', str(out)]
    began = None
    signalled = False
    with (out / 'runner.log').open('a') as stream:
        process = subprocess.Popen(command, cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        save(out / 'worker-launch.json', {'recorded_at': stamp(), 'pid': process.pid, 'process_identity': process_identity(process.pid), 'argv': command})
        def child_alive():
            return (out / 'heartbeat.json').exists() and alive(load(out / 'heartbeat.json'))
        # uv can exit on SIGTERM before its child finishes a diagnostic and
        # orderly checkpoint. Wait for the actual worker identity as well.
        while process.poll() is None or child_alive():
            sample = {'recorded_at': stamp(), 'host': host(), 'pressure': pressure(), 'cgroup': cgroup_info(group)}
            save(out / 'telemetry-latest.json', sample)
            with (out / 'telemetry.jsonl').open('a') as telemetry:
                telemetry.write(json.dumps(sample) + '\n')
            unsafe, began = pressure_stop(sample, time.monotonic(), began)
            if (unsafe or stop or (out / 'STOP.json').exists()) and not signalled:
                save(out / 'PAUSE-REQUEST.json', {'recorded_at': stamp(), 'reason': 'resource_pressure' if unsafe else 'operator_stop', 'sample': sample})
                os.killpg(process.pid, signal.SIGTERM)
                signalled = True
                log('Orderly continuation pause requested; waiting for optimizer boundary')
            time.sleep(5)
    state = load(out / 'status.json')
    if process.returncode != 0 and state['status'] not in ('failed', 'interrupted'):
        events = cgroup_info(group).get('memory.events', {})
        interrupted = events.get('oom_kill', 0) > 0
        save(out / 'status.json', {'recorded_at': stamp(), 'status': 'interrupted' if interrupted else 'failed',
                                  'error': 'Memory kill; last sealed checkpoint retained' if interrupted else 'Worker exited before sealing; inspect runner.log',
                                  'exit_code': process.returncode})
    log('Continuation supervisor finished', exit_code=process.returncode, output=str(out), status=load(out / 'status.json'))
    return 0 if load(out / 'status.json')['status'] in ('interrupted', 'complete_pending_review') else process.returncode or 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['verify', 'install', 'publish', 'merge', 'preflight', 'run', 'resume', 'status', 'stop', 'record-results', 'supervise'])
    parser.add_argument('--repo', type=Path, default=Path.home() / 'ElectronFieldTopology-adaptive-q-screen-20261117')
    parser.add_argument('--publication', type=Path, default=Path.home() / 'ElectronFieldTopology-policy-v2-record-20261120')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    pub = args.publication.expanduser().resolve()
    if args.mode == 'verify':
        count = verify_manifest(ROOT)
        baseline()
        old = baseline()[0]['handover/PLAN.json']
        new = load(ROOT / 'PLAN.json')
        need({k: v for k, v in new.items() if k != 'branch_attempt_budget'} == {k: v for k, v in old.items() if k != 'branch_attempt_budget'}, 'Unexpected plan/gate change')
        need(new['branch_attempt_budget'] == 500, 'Selected branch ceiling must be 500')
        selected = load(ROOT / 'SELECTION.json')
        need(len(selected['branches']) == 6 and sum(s['maximum_additional_attempts'] for s in selected['branches']) == 1738, 'Selection allocation differs')
        log('Policy-v2 handover verified', files=count, branches=6, total_attempt_ceiling=500, maximum_additional_attempts=1738, production_started=False)
    elif args.mode in ('install', 'publish', 'merge', 'record-results'):
        import publication
        publication.execute(args.mode, repo, pub)
    elif args.mode == 'preflight':
        log('Continuation preflight', **preflight(repo))
    elif args.mode in ('run', 'resume'):
        start(repo, args.mode == 'resume')
    elif args.mode == 'supervise':
        need(args.output is not None, 'Supervisor output required')
        return supervise(repo, args.output.resolve())
    elif args.mode == 'stop':
        out = output(repo)
        if is_live(out) or service_active():
            save(out / 'STOP.json', {'recorded_at': stamp(), 'reason': 'operator_stop'})
            log('Orderly stop requested', output=str(out), note='Allow the current optimizer step/CPU diagnostic/checkpoint to finish; check status before resuming')
        else:
            log('Continuation already stopped; all retained states preserved', output=str(out))
    else:
        status(repo)
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        log('Policy-v2 handover stopped', error=str(error))
        raise SystemExit(1)
