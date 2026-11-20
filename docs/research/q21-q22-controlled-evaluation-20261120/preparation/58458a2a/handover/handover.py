"""Record the assessment locally and run bounded Q21/Q22 evaluations."""
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
from integrity import alive, host, preflight, process_identity
from supervision import UNIT, group_info, group_path, pressure, pressure_stop, service_active

GIB = 1024**3

def pointer(repo):
    return repo / '.git/q21-q22-evaluation-last.json'

def output(repo):
    need(pointer(repo).exists(), 'No Q21/Q22 run exists; run after preflight')
    return Path(load(pointer(repo))['output'])

def live(out):
    return any(alive(load(out / name)) for name in ['supervisor.json', 'heartbeat.json'] if (out / name).exists())

def launch_argv(repo, out):
    return ['sudo', 'systemd-run', '--unit=' + UNIT, '--collect', '--service-type=exec', '--property=WorkingDirectory=' + str(repo),
            '--property=MemoryAccounting=yes', '--property=MemoryHigh=' + str(7 * GIB), '--property=MemoryMax=' + str(8 * GIB),
            '--property=MemorySwapMax=' + str(GIB), '--property=Restart=no', '--property=OOMPolicy=stop',
            '--property=TimeoutStopSec=infinity', '--property=SendSIGKILL=no', shutil.which('systemd-inhibit'),
            '--what=sleep:idle:handle-lid-switch', '--mode=block', '--who=Matter Waves', '--why=Bounded Q21 and native Q22 evaluation',
            shutil.which('setpriv'), '--reuid=' + str(os.getuid()), '--regid=' + str(os.getgid()), '--init-groups', '--reset-env',
            '/usr/bin/python3', '-B', str(out / 'handover/handover.py'), 'supervise', '--repo', str(repo), '--output', str(out)]

def runtime_preflight(repo, requested, q22=None):
    receipt = preflight(repo, q22)
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4', PYTHONDONTWRITEBYTECODE='1')
    argv = ['uv', 'run', '--frozen', '--extra', 'gpu', '--python', '3.12.14', 'python', '-B', str(ROOT / 'probe.py'), '--repo', str(repo), '--backend', requested]
    result = subprocess.run(argv, cwd=repo, env=env, text=True, capture_output=True)
    need(result.returncode == 0, 'Requested backend failed before run creation. Keep auto/CUDA only when available, or choose --backend cpu for both arms before starting.\n' + result.stderr)
    receipt['backend_probe'] = json.loads(result.stdout.strip().splitlines()[-1])
    return receipt

def start(repo, requested, q22=None, resume=False):
    need(os.geteuid() != 0, 'Run as your normal user; only service creation uses sudo')
    need(not service_active(), 'Evaluation service is active; use status or stop')
    receipt = runtime_preflight(repo, requested, q22)
    if resume:
        out = output(repo)
        need(not live(out), 'An evaluation worker is already active')
        need(load(out / 'status.json')['status'] in ['interrupted', 'working', 'starting'], 'Completed/failed evaluation needs review before another run')
        identity = load(out / 'identity.json')
        need(identity['package_sha256'] == sha(ROOT / 'SHA256SUMS') and identity['requested_backend'] == requested, 'Resume must retain package and backend')
        verify_manifest(out / 'handover')
        inventory = load(out / 'Q22-INVENTORY.json')
        if inventory['status'] == 'authenticated':
            from integrity import check_file
            check_file(Path(inventory['path']), inventory['sha256'])
        if q22:
            need(receipt['q22_inventory'].get('path') == inventory.get('path'), 'Resume cannot change the recorded Q22 source')
        if (out / 'STOP.json').exists():
            (out / 'STOP.json').rename(out / ('STOP-retained-' + uuid.uuid4().hex[:8] + '.json'))
    else:
        need(not pointer(repo).exists(), 'A run already exists; use status/resume to preserve its budget and lineage')
        rid = datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-') + uuid.uuid4().hex[:8]
        out = repo / 'artifacts/q21-q22-controlled-evaluation' / rid
        out.mkdir(parents=True, exist_ok=False)
        shutil.copytree(ROOT, out / 'handover', ignore=shutil.ignore_patterns('__pycache__'))
        save(out / 'identity.json', {'recorded_at': stamp(), 'run_id': rid, 'package_sha256': sha(ROOT / 'SHA256SUMS'), 'plan_sha256': sha(ROOT / 'PLAN.json'),
                                    'source_identity': receipt['source_identity'], 'requested_backend': requested, 'maximum_q21_attempts': 40, 'q22_optimizer_steps': 0, 'physical_time_steps': 0})
        save(out / 'Q22-INVENTORY.json', receipt['q22_inventory'])
        save(pointer(repo), {'recorded_at': stamp(), 'output': str(out), 'unit': UNIT})
    save(out / 'PREFLIGHT.json', receipt)
    save(out / 'LAUNCH-CONFIG.json', {'recorded_at': stamp(), 'uid': os.getuid(), 'repo': str(repo), 'output': str(out),
                                    'executable_path': str(Path(shutil.which('uv')).parent) + ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})
    save(out / 'status.json', {'recorded_at': stamp(), 'status': 'starting', 'phase': 'supervisor-launch', 'physical_time_steps': 0})
    subprocess.run(['sudo', '-v'], check=True)
    subprocess.run(launch_argv(repo, out), check=True)
    log('Bounded evaluation service requested', output=str(out), maximum_q21_attempts=40, q22_inventory=load(out / 'Q22-INVENTORY.json'), report=str(out / 'REPORT.html'))

def supervise(repo, out):
    need(os.geteuid() != 0, 'Worker must run as the normal user')
    cfg = load(out / 'LAUNCH-CONFIG.json')
    need(cfg['uid'] == os.getuid() and cfg['repo'] == str(repo) and cfg['output'] == str(out), 'Supervisor identity differs')
    os.environ['PATH'] = cfg['executable_path']
    verify_manifest(ROOT)
    group = group_path()
    need(group.name == UNIT and 'system.slice' in group.parts, 'Worker not in the isolated service')
    for name, limit in [('memory.high', 7 * GIB), ('memory.max', 8 * GIB), ('memory.swap.max', GIB)]:
        need((group / name).read_text().strip() == str(limit), 'Resource limit differs: ' + name)
    save(out / 'supervisor.json', {'recorded_at': stamp(), 'pid': os.getpid(), 'process_identity': process_identity(os.getpid())})
    stop = False
    def request(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, request)
    signal.signal(signal.SIGINT, request)
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4', PYTHONDONTWRITEBYTECODE='1')
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
                save(out / 'STOP.json', {'recorded_at': stamp(), 'reason': 'resource_pressure' if unsafe else 'operator_stop'})
                os.killpg(process.pid, signal.SIGTERM)
                signalled = True
                log('Orderly pause requested; wait for the current accepted step or static evaluation to finish')
            time.sleep(5)
    current = load(out / 'status.json')
    if process.returncode != 0 and current['status'] not in ['interrupted', 'failed']:
        oom = group_info(group).get('memory.events', {}).get('oom_kill', 0) > 0
        save(out / 'status.json', {'recorded_at': stamp(), 'status': 'interrupted' if oom else 'failed', 'exit_code': process.returncode, 'error': 'Worker exited before final seal; committed checkpoints and charged attempts retained'})
    current = load(out / 'status.json')
    log('Evaluation supervisor finished', status=current, output=str(out))
    return 0 if current['status'] in ['complete_pending_review', 'interrupted'] else process.returncode or 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['verify', 'install', 'publish', 'merge', 'preflight', 'run', 'resume', 'status', 'stop', 'record-results', 'supervise'])
    parser.add_argument('--repo', type=Path, default=Path.home() / 'ElectronFieldTopology-adaptive-q-screen-20261117')
    parser.add_argument('--publication', type=Path, default=Path.home() / 'ElectronFieldTopology-q21-q22-evaluation-record-20261120')
    parser.add_argument('--backend', choices=['auto', 'cpu', 'cuda'], default='auto')
    parser.add_argument('--q22', type=Path, help='Optional exact historical Q22 checkpoint; full SHA256 must match')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    repo, pub = args.repo.expanduser().resolve(), args.publication.expanduser().resolve()
    if args.mode == 'verify':
        count = verify_manifest(ROOT)
        # The included audit CLI is exercised by HOST-VALIDATION; archive
        # integrity is checked directly here without importing its CLI entrypoint.
        import zipfile
        with zipfile.ZipFile(ROOT / 'assessment/data/diagnostic-evidence.zip') as z:
            need(z.testzip() is None, 'Retained diagnosis archive CRC failed')
        need(sha(ROOT / 'assessment/data/diagnostic-evidence.zip') == load(ROOT / 'REFERENCES.json')['diagnosis_evidence_sha256'], 'Diagnosis evidence identity differs')
        log('Q21/Q22 handover verified', payload_files=count, maximum_new_optimizer_attempts=40, physical_time_steps=0)
    elif args.mode in ['install', 'publish', 'merge', 'record-results']:
        import publication
        publication.execute(args.mode, repo, pub)
    elif args.mode == 'preflight':
        log('Evaluation preflight', **runtime_preflight(repo, args.backend, args.q22))
    elif args.mode in ['run', 'resume']:
        start(repo, args.backend, args.q22, args.mode == 'resume')
    elif args.mode == 'supervise':
        need(args.output is not None, 'Supervisor output required')
        return supervise(repo, args.output.resolve())
    elif args.mode == 'stop':
        if not pointer(repo).exists():
            log('No evaluation run exists; nothing to stop')
        else:
            out = output(repo)
            if live(out) or service_active():
                save(out / 'STOP.json', {'recorded_at': stamp(), 'reason': 'operator_stop'})
                log('Orderly stop requested', output=str(out))
            else:
                log('Evaluation is already inactive', output=str(out))
    else:
        from publication import marker
        if marker(pub).exists():
            state = load(marker(pub))
            log('Publication status', phase=state['phase'], kind=state['kind'], pr=state.get('pr'))
        if pointer(repo).exists():
            out = output(repo)
            log('Q21/Q22 evaluation status', runner_alive=live(out), service_active=service_active(), output=str(out), status=load(out / 'status.json'),
                heartbeat=load(out / 'heartbeat.json') if (out / 'heartbeat.json').exists() else None, telemetry=load(out / 'telemetry-latest.json') if (out / 'telemetry-latest.json').exists() else None,
                report=str(out / 'REPORT.html'), evidence=str(out / 'evidence.zip'))
        else:
            log('No Q21/Q22 evaluation run exists')
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        log('Q21/Q22 handover stopped', error=str(error))
        raise SystemExit(1)
