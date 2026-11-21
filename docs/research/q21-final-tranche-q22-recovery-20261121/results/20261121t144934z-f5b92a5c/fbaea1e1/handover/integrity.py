"""Authenticate the reviewed exact-315 parent and the unchanged numerical source."""
import fcntl
from functools import lru_cache
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile
from common import ROOT, canonical, load, need, sha, stamp, verify_manifest

def source_run(repo):
    return repo / 'artifacts/q21-q22-controlled-evaluation/20261120t114719z-48b7d4cf'

def original_run(repo):
    return repo / 'artifacts/adaptive-q17-q32-screen/20261117t133953z-d6617788'

def checked_zip(z):
    names = z.namelist()
    need(len(names) == len(set(names)) and z.testzip() is None, 'Evidence CRC/duplicate failure')
    hashes = {}
    for row in z.read('SHA256SUMS').decode().splitlines():
        digest, name = row.split('  ', 1)
        path = PurePosixPath(name)
        need(not path.is_absolute() and '..' not in path.parts and name not in hashes, 'Unsafe compact member')
        need(hashlib.sha256(z.read(name)).hexdigest() == digest, 'Compact evidence checksum differs: ' + name)
        hashes[name] = digest
    need(set(hashes) == set(names) - {'SHA256SUMS'}, 'Compact evidence checksum coverage differs')
    return hashes

@lru_cache(maxsize=1)
def baseline():
    plan = load(ROOT / 'PLAN.json')
    path = ROOT / 'assessment/data/completed-evidence.zip'
    need(sha(path) == plan['source_evidence_sha256'], 'Reviewed source evidence differs')
    with zipfile.ZipFile(path) as z:
        hashes = checked_zip(z)
        objects = {name: json.loads(z.read(name)) for name in ['record.json', 'identity.json', 'q21/exact/record.json', 'q21/exact/endpoint.seal.json']}
    return objects, hashes

def verify_sources(repo):
    expected = load(ROOT / 'SOURCES.json')
    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    need(head == expected['checkout_commit'], 'Keep numerical checkout at its pinned commit; use the separate publication clone')
    for name, digest in {**expected['complete_numerical_source_sha256'], **expected['source_sha256']}.items():
        need((repo / name).is_file() and sha(repo / name) == digest, 'Pinned numerical source/lock differs: ' + name)
    return canonical(expected)

def check_file(path, digest):
    need(path.is_file() and not path.is_symlink() and sha(path) == digest, 'Exact field missing or SHA256 differs: ' + str(path))
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None, 'NPZ CRC failed: ' + str(path))

def source_checkpoint(repo):
    plan = load(ROOT / 'PLAN.json')
    out = source_run(repo)
    need(sha(out / 'evidence.zip') == plan['source_evidence_sha256'], 'Local completed source evidence changed')
    for name, digest in plan['source_compact_files'].items():
        need(sha(out / name) == digest, 'Reviewed source metadata changed: ' + name)
    need(load(out / 'status.json')['status'] == 'complete_pending_review', 'Previous comparison is not complete')
    spec = plan['q21']
    path = out / spec['source_field']['path']
    check_file(path, spec['source_field']['sha256'])
    need(path.stat().st_size == spec['source_field']['bytes'], 'Source optimizer checkpoint size differs')
    return path

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
    baseline()
    for old in [source_run(repo), original_run(repo)]:
        with (old / '.worker.lock').open('r') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    source = source_checkpoint(repo)
    control = load(ROOT / 'PLAN.json')['q2']
    check_file(original_run(repo) / control['original_relative_path'], control['sha256'])
    if q22:
        check_file(Path(q22).expanduser().resolve(), load(ROOT / 'PLAN.json')['q22']['sha256'])
    information = host()
    need(information['available_gib'] >= 10 and information['swap_free_gib'] >= 1, 'Require 10 GiB available RAM and 1 GiB free swap; keep Open WebUI stopped')
    need(shutil.disk_usage(repo).free >= 40 * 1024**3, 'Require 40 GiB free disk')
    for name in ['uv', 'sudo', 'systemd-run', 'systemctl', 'systemd-inhibit', 'setpriv', 'gcc']:
        need(shutil.which(name), 'Required local executable absent: ' + name)
    return {'recorded_at': stamp(), 'status': 'preflight_pass', 'package_files': count, 'source_identity': identity,
            'source_checkpoint': str(source), 'source_sha256': load(ROOT / 'PLAN.json')['q21']['source_field']['sha256'],
            'explicit_q22': str(Path(q22).expanduser().resolve()) if q22 else None, 'host': information,
            'maximum_new_q21_attempts': 20, 'q22_optimizer_steps': 0, 'physical_time_steps': 0}
