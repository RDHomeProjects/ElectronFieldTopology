"""Authenticate existing local fields; never fetch or regenerate a candidate."""
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from common import ROOT, canonical, load, need, sha, stamp, verify_manifest

def source_run(repo):
    return repo / 'artifacts/q17-q32-policy-v2/20261120t003653z-a200a9db'

def original_run(repo):
    return repo / 'artifacts/adaptive-q17-q32-screen/20261117t133953z-d6617788'

def verify_sources(repo):
    expected = load(ROOT / 'SOURCES.json')
    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    need(head == expected['checkout_commit'], 'Numerical checkout HEAD changed; preserve it and use the separate publication clone')
    for name, digest in {**expected['complete_numerical_source_sha256'], **expected['source_sha256']}.items():
        need((repo / name).is_file() and sha(repo / name) == digest, 'Numerical source/lock differs: ' + name)
    return canonical(expected)

def check_file(path, digest):
    need(path.is_file() and not path.is_symlink() and sha(path) == digest, 'Exact checkpoint missing or SHA256 differs: ' + str(path))
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None, 'NPZ CRC failure: ' + str(path))

def q21_sources(repo):
    p = load(ROOT / 'PLAN.json')['q21']
    folder = source_run(repo) / 'continuation/q21-axial-7-3'
    for name, expected in p['prior_records'].items():
        need(load(folder / name) == expected, 'Q21 pinned source metadata differs: ' + name)
    state = source_run(repo) / p['state']['path']
    endpoint = source_run(repo) / p['spec']['relative_path']
    check_file(state, p['state']['sha256'])
    check_file(endpoint, p['spec']['sha256'])
    return state, endpoint

def q22_inventory(repo, explicit=None):
    """Only inspect declared roots; authenticate by full SHA, never filename alone."""
    spec = load(ROOT / 'PLAN.json')['q22']
    if explicit:
        path = Path(explicit).expanduser().resolve()
        check_file(path, spec['sha256'])
        return {'recorded_at': stamp(), 'status': 'authenticated', 'path': str(path), 'sha256': spec['sha256'], 'selection': 'explicit exact-hash match'}
    direct = Path.home() / spec['path']
    checked, candidates = [], [direct]
    # Bounded search of the original study, not unrelated home directories.
    study = Path.home() / 'ElectronFieldTopology-q22-study/artifacts'
    if study.is_dir():
        candidates += sorted(study.glob('q22-fresh-20261101T102757+1100/cases/*/final.npz'))
    for path in dict.fromkeys(candidates):
        if not path.is_file():
            checked.append({'path': str(path), 'status': 'absent'})
            continue
        digest = sha(path)
        checked.append({'path': str(path), 'sha256': digest, 'status': 'match' if digest == spec['sha256'] else 'different_field'})
        if digest == spec['sha256']:
            check_file(path, digest)
            return {'recorded_at': stamp(), 'status': 'authenticated', 'path': str(path), 'sha256': digest, 'checked': checked}
    return {'recorded_at': stamp(), 'status': 'deferred_missing_exact_historical_field', 'expected_sha256': spec['sha256'], 'checked': checked,
            'reason': 'Historical Q22 checkpoint unavailable in declared locations; no fresh-seed substitution, regeneration, resampling or Q17 replacement'}

def host():
    values = {line.split(':', 1)[0]: int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if len(line.split()) > 1 and line.split()[1].isdigit()}
    return {key: values[name] / 1024**3 for key, name in [('total_gib', 'MemTotal'), ('available_gib', 'MemAvailable'), ('swap_free_gib', 'SwapFree')]}

def process_identity(pid):
    try:
        raw = (Path('/proc') / str(pid) / 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        if fields[0] == 'Z':
            return None
        return {'pid': pid, 'start_ticks': fields[19], 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (FileNotFoundError, ProcessLookupError):
        return None

def alive(record):
    return bool(record and record.get('process_identity') and process_identity(record['pid']) == record['process_identity'])

def preflight(repo, q22=None):
    count = verify_manifest(ROOT)
    identity = verify_sources(repo)
    for path in [source_run(repo), original_run(repo)]:
        with (path / '.worker.lock').open('r') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    state, endpoint = q21_sources(repo)
    p = load(ROOT / 'PLAN.json')['q2']
    control = original_run(repo) / p['original_relative_path']
    check_file(control, p['sha256'])
    inventory = q22_inventory(repo, q22)
    information = host()
    need(information['available_gib'] >= 10 and information['swap_free_gib'] >= 1, 'Require 10 GiB available RAM and 1 GiB free swap; keep Open WebUI stopped')
    need(shutil.disk_usage(repo).free >= 40 * 1024**3, 'Require 40 GiB free disk')
    for name in ['uv', 'sudo', 'systemd-run', 'systemctl', 'systemd-inhibit', 'setpriv', 'gcc']:
        need(shutil.which(name), 'Required local executable absent: ' + name)
    return {'recorded_at': stamp(), 'status': 'preflight_pass', 'package_files': count, 'source_identity': identity,
            'q21_state': str(state), 'q21_endpoint': str(endpoint), 'q2_control': str(control), 'q22_inventory': inventory, 'host': information,
            'new_optimizer_attempt_ceiling': 40, 'q22_optimizer_steps': 0, 'physical_time_steps': 0}
