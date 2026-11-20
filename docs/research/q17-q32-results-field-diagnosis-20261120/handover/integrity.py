"""Frozen compact evidence and local full-field authentication."""
import fcntl
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile
from common import ROOT, canonical, load, log, need, sha, stamp, verify_manifest

COMPLETED_SHA = 'cc17e740f2217cb072420c715d22a11cf1cf15b1d81e9c585251a89869edd643'
RUN_ID = '20261120t003653z-a200a9db'
ORIGINAL_ID = '20261117t133953z-d6617788'

def checked_zip(z):
    names = z.namelist()
    need(len(names) == len(set(names)) and z.testzip() is None, 'Archive CRC/duplicate failure')
    hashes = {}
    for line in z.read('SHA256SUMS').decode().splitlines():
        digest, name = line.split('  ', 1)
        p = PurePosixPath(name)
        need(not p.is_absolute() and '..' not in p.parts and name not in hashes, 'Unsafe archive member')
        need(hashlib.sha256(z.read(name)).hexdigest() == digest, 'Compact checksum differs: ' + name)
        hashes[name] = digest
    need(set(hashes) == set(names) - {'SHA256SUMS'}, 'Archive coverage differs')
    return hashes

@lru_cache(maxsize=1)
def baseline():
    path = ROOT / 'assessment/data/completed-evidence.zip'
    need(sha(path) == COMPLETED_SHA, 'Completed source evidence differs')
    with zipfile.ZipFile(path) as z:
        hashes = checked_zip(z)
        objects = {n: json.loads(z.read(n)) for n in z.namelist() if n.endswith('.json')}
        with zipfile.ZipFile(io.BytesIO(z.read('handover/assessment/data/source-evidence.zip'))) as old:
            checked_zip(old)
            original = {n: json.loads(old.read(n)) for n in old.namelist() if n.endswith('.json')}
    return objects, hashes, original

def completed(repo):
    return repo / 'artifacts/q17-q32-policy-v2' / RUN_ID

def original(repo):
    return repo / 'artifacts/adaptive-q17-q32-screen' / ORIGINAL_ID

def verify_sources(repo):
    expected = load(ROOT / 'SOURCES.json')
    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    need(head == expected['checkout_commit'], 'Keep the numerical checkout at its pinned commit; use the separate publication clone')
    for name, digest in {**expected['complete_numerical_source_sha256'], **expected['source_sha256']}.items():
        need(sha(repo / name) == digest, 'Pinned numerical source/lock differs: ' + name)
    return canonical(expected)

def host():
    m = {line.split(':', 1)[0]: int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if len(line.split()) > 1 and line.split()[1].isdigit()}
    return {k: m[v] / 1024**3 for k, v in [('total_gib', 'MemTotal'), ('available_gib', 'MemAvailable'), ('swap_total_gib', 'SwapTotal'), ('swap_free_gib', 'SwapFree')]}

def field_path(repo, spec):
    return (original(repo) / spec['original_relative_path']) if spec['kind'] == 'control' else completed(repo) / spec['relative_path']

def check_file(path, digest):
    need(path.is_file() and sha(path) == digest, 'Full-field SHA256 differs or file absent: ' + str(path))
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None, 'NPZ CRC failed: ' + str(path))

def preflight(repo, check_ram=True, check_fields=True):
    count = verify_manifest(ROOT)
    identity = verify_sources(repo)
    objects, hashes, _ = baseline()
    out = completed(repo)
    need(sha(out / 'evidence.zip') == COMPLETED_SHA, 'Local completed evidence differs from reviewed source')
    for name in ['record.json', 'identity.json', 'field-manifest.json', 'NEXT-STAGE.json']:
        need(sha(out / name) == hashes[name], 'Completed record changed: ' + name)
    need(load(out / 'status.json')['status'] == 'complete_pending_review', 'Expected the completed immutable continuation')
    for old in [original(repo), out]:
        with (old / '.worker.lock').open('r') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    checked = []
    if check_fields:
        for index, row in enumerate(objects['field-manifest.json']['fields'], start=1):
            path = out / row['path']
            need(path.stat().st_size == row['bytes'], 'Retained field size differs: ' + row['path'])
            check_file(path, row['sha256'])
            checked.append(row)
            if index % 5 == 0:
                log('Checking retained full-field hashes and NPZ CRCs', checked=index, total=37)
        control = load(ROOT / 'PLAN.json')['fields'][0]
        check_file(field_path(repo, control), control['sha256'])
    information = host()
    if check_ram:
        need(information['available_gib'] >= 10 and information['swap_free_gib'] >= 1, 'Require 10 GiB available RAM and 1 GiB free swap; keep Open WebUI stopped')
    need(shutil.disk_usage(out).free / 1024**3 >= 40, 'Require 40 GiB free disk')
    for exe in ['uv', 'sudo', 'systemd-run', 'systemctl', 'systemd-inhibit', 'setpriv']:
        need(shutil.which(exe), 'Required executable absent: ' + exe)
    need(Path('/sys/fs/cgroup/cgroup.controllers').exists() and 'memory' in Path('/sys/fs/cgroup/cgroup.controllers').read_text().split(), 'Unified memory cgroup required')
    return {'recorded_at': stamp(), 'status': 'preflight_pass', 'package_files': count, 'source_identity': identity,
            'completed_run': str(out), 'completed_sha256': COMPLETED_SHA, 'full_field_hashes_and_crcs': len(checked) + (1 if check_fields else 0),
            'retained_continuation_fields': checked, 'q2_control_hash': load(ROOT / 'PLAN.json')['fields'][0]['sha256'],
            'host': information, 'optimizer_steps': 0, 'physical_time_steps': 0}

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

def collect_completed(repo, destination):
    """Preserve all non-field result files, not only the compact ZIP filter."""
    source = completed(repo)
    need(sha(source / 'evidence.zip') == COMPLETED_SHA, 'Completed evidence changed before collection')
    need(load(source / 'status.json')['status'] == 'complete_pending_review', 'Source continuation is not complete')
    destination.mkdir(parents=True, exist_ok=True)
    copied, retained, omitted = [], [], []
    with (source / '.worker.lock').open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for path in sorted(source.rglob('*')):
            if not path.is_file():
                continue
            name = path.relative_to(source).as_posix()
            need(not path.is_symlink(), 'Unexpected source symlink: ' + name)
            if path.suffix == '.npz':
                retained.append({'path': name, 'absolute_local_path': str(path), 'bytes': path.stat().st_size})
                continue
            if '__pycache__' in path.parts or path.name.endswith(('.tmp', '.lock')):
                omitted.append({'path': name, 'reason': 'runtime lock/cache/temporary file; not a result payload'})
                continue
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                need(sha(target) == sha(path), 'Existing collected result differs: ' + name)
            else:
                shutil.copy2(path, target)
            digest = sha(path)
            need(sha(target) == digest, 'Copied result differs: ' + name)
            copied.append({'path': name, 'sha256': digest, 'bytes': target.stat().st_size})
    manifest = baseline()[0]['field-manifest.json']['fields']
    need({x['path'] for x in retained} == {x['path'] for x in manifest}, 'Full-field inventory differs from reviewed manifest')
    receipt = {'recorded_at': stamp(), 'source': str(source), 'source_evidence_sha256': COMPLETED_SHA,
               'copied_nonfield_files': copied, 'retained_full_fields': manifest, 'retained_absolute_locations': retained,
               'excluded_runtime_files': omitted, 'full_field_contents_verified_by_collection': False,
               'scope': 'All non-field result files, logs, telemetry and full frozen handover are retained byte-exact. NPZ fields remain local and are hash/CRC-checked by diagnostic preflight; no remote full-field archive is claimed.'}
    save = __import__('common').save
    save(destination / 'COLLECTION.json', receipt)
    (destination / 'COLLECTED-SHA256SUMS').write_text(''.join(x['sha256'] + '  ' + x['path'] + '\n' for x in copied))
    return receipt
