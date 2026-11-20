"""Authenticate the old compact record and the six local optimizer parents."""
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from functools import lru_cache
from pathlib import Path, PurePosixPath
from common import ROOT, canonical, load, need, sha, stamp, verify_manifest

RUN_ID = '20261117t133953z-d6617788'
AUDIT_SHA = '1967a35025b750e89f52aa6d6ca6c34d525628c9573521e17e62dd01d63705d0'
UNIT = 'matter-waves-q17-q32-policy-v2.service'

@lru_cache(maxsize=1)
def baseline():
    archive = ROOT / 'assessment/data/source-evidence.zip'
    need(sha(archive) == AUDIT_SHA, 'Policy-audit source archive changed')
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        need(len(names) == len(set(names)) and z.testzip() is None, 'Source archive CRC/duplicate failure')
        hashes = {}
        for line in z.read('SHA256SUMS').decode().splitlines():
            digest, name = line.split('  ', 1)
            p = PurePosixPath(name)
            need(not p.is_absolute() and '..' not in p.parts and name not in hashes, 'Unsafe source member')
            need(hashlib.sha256(z.read(name)).hexdigest() == digest, 'Source payload changed: ' + name)
            hashes[name] = digest
        need(set(hashes) == set(names) - {'SHA256SUMS'}, 'Source coverage differs')
        objects = {n: json.loads(z.read(n)) for n in names if n.endswith('.json')}
    return objects, hashes

def source_out(repo):
    return repo / 'artifacts/adaptive-q17-q32-screen' / RUN_ID

def process_identity(pid):
    try:
        raw = (Path('/proc') / str(pid) / 'stat').read_text()
        rest = raw[raw.rfind(')') + 2:].split()
        if rest[0] == 'Z':
            return None
        return {'pid': pid, 'start_ticks': rest[19], 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (FileNotFoundError, ProcessLookupError):
        return None

def alive(record):
    return bool(record and record.get('process_identity') and process_identity(record['pid']) == record['process_identity'])

def host():
    m = {line.split(':', 1)[0]: int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if len(line.split()) > 1 and line.split()[1].isdigit()}
    return {k: m[v] / 1024**3 for k, v in [('total_gib', 'MemTotal'), ('available_gib', 'MemAvailable'), ('swap_total_gib', 'SwapTotal'), ('swap_free_gib', 'SwapFree')]}

def check_sources(repo):
    objects, _ = baseline()
    identity = objects['identity.json']
    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    need(head == identity['checkout_commit'], 'Keep the numerical checkout at its original pinned commit; publish from the separate record clone')
    for name, digest in {**identity['complete_numerical_source_sha256'], **identity['source_sha256']}.items():
        need(sha(repo / name) == digest, 'Pinned numerical source/lock differs: ' + name)
    need(load(source_out(repo) / 'identity.json') == identity, 'Original run identity differs')
    return identity

def original_identity(spec, root_identity):
    return {**root_identity, 'seed': spec['seed'], 'shape': [spec['nodes']] * 3,
            'lengths': [spec['length']] * 3, 'backend': spec['backend']}

def parent_check(repo, spec):
    objects, hashes = baseline()
    out = source_out(repo)
    prefix = 'broad/' + spec['id'] + '/optimizer/'
    names = ['latest.json', 'history.json', 'attempts.json', 'result.json', 'result.seal.json', 'planner.json', 'decisions.json']
    pointer = objects[prefix + 'latest.json']
    names += ['state-' + str(pointer['slot']) + '.seal.json', 'endpoint.json']
    for name in names:
        need(sha(out / (prefix + name)) == hashes[prefix + name], 'Retained parent metadata differs: ' + prefix + name)
    state_name = prefix + 'state-' + str(pointer['slot']) + '.npz'
    files = {x['path']: x for x in objects['field-manifest.json']['fields']}
    checked = []
    for name in [state_name, prefix + 'endpoint.npz']:
        declared = files[name]
        path = out / name
        need(path.stat().st_size == declared['bytes'] and sha(path) == declared['sha256'], 'Retained field hash differs: ' + name)
        with zipfile.ZipFile(path) as z:
            need(z.testzip() is None, 'Retained NPZ CRC failed: ' + name)
        checked.append({'path': name, **declared})
    seal = objects[prefix + 'state-' + str(pointer['slot']) + '.seal.json']
    need(seal['sha256'] == files[state_name]['sha256'], 'Checkpoint seal/manifest disagree')
    old_identity = original_identity(spec, objects['identity.json'])
    need(pointer['identity'] == seal['identity_sha256'] == canonical(old_identity), 'Parent identity cannot be reconstructed exactly')
    history = objects[prefix + 'history.json']
    need(canonical(history) == pointer['history_sha256'], 'Parent history pointer differs')
    need(pointer['iteration'] == history[-1]['iteration'] == spec['initial_iteration'], 'Parent iteration differs')
    need(objects[prefix + 'attempts.json']['attempts'] == spec['already_spent_attempts'], 'Parent spent-attempt count differs')
    receipt_name = 'qualification/' + '-'.join([str(spec['nodes'])] * 3) + '-L' + str(spec['length']) + '/benchmark.json'
    need(sha(out / receipt_name) == hashes[receipt_name], 'Original geometry/backend qualification differs')
    receipt = objects[receipt_name]
    need(receipt['selected_backend'] == spec['backend'] == 'cuda', 'No backend replacement is permitted in this continuation')
    return {'seed': spec['id'], 'state': str(out / state_name), 'state_sha256': files[state_name]['sha256'],
            'endpoint': str(out / (prefix + 'endpoint.npz')), 'original_identity': old_identity,
            'history': history, 'receipt': receipt, 'checked_fields': checked}

def preflight(repo, check_ram=True):
    count = verify_manifest(ROOT)
    identity = check_sources(repo)
    out = source_out(repo)
    need(load(out / 'status.json')['status'] == 'interrupted', 'Original campaign must remain interrupted; do not resume its old queue')
    # Opening an existing lock read-only never changes original evidence.
    with (out / '.worker.lock').open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    rows = [parent_check(repo, spec) for spec in load(ROOT / 'SELECTION.json')['branches']]
    info = host()
    if check_ram:
        need(info['available_gib'] >= 10 and info['swap_free_gib'] >= 1, 'Require 10 GiB available RAM and 1 GiB free swap before launch; keep Open WebUI stopped')
    need(shutil.disk_usage(out).free / 1024**3 >= 40, 'Require 40 GiB free disk')
    for exe in ['uv', 'sudo', 'systemd-run', 'systemctl', 'systemd-inhibit', 'setpriv']:
        need(shutil.which(exe), 'Required command missing: ' + exe)
    need(Path('/sys/fs/cgroup/cgroup.controllers').exists(), 'Unified cgroup v2 required')
    need('memory' in Path('/sys/fs/cgroup/cgroup.controllers').read_text().split(), 'Memory controller unavailable')
    return {'recorded_at': stamp(), 'status': 'preflight_pass', 'package_files': count, 'source_identity': canonical(identity),
            'host': info, 'full_field_hashes_and_npz_crcs': 12, 'parents': [{k: row[k] for k in ['seed', 'state', 'state_sha256']} for row in rows],
            'cpu_metric_and_cuda_gradient_replay': 'required under the supervised worker before continuation',
            'maximum_additional_attempts': 1738, 'solver_steps': 0}
