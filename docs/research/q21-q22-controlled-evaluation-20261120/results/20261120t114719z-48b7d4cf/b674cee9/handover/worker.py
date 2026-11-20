"""Sequential, resource-supervised Q21/Q22 evaluations; zero physical time."""
import argparse
import fcntl
import gc
import hashlib
import html
import json
import os
from pathlib import Path
import signal
import sys
import threading
import traceback
import zipfile
import numpy as np
from common import ROOT, canonical, load, log, need, save, sha, stamp, verify_manifest
from integrity import alive, check_file, host, original_run, process_identity, q21_sources, source_run, verify_sources
from engine import Engine, checkpoint, restore
from evaluations import array_sha, derivative_check, fit_history, gate_result, metrics, paired_summary, q22_compare, split_state, state_digest

STOP = threading.Event()

class HostReader:
    xp = np
    def __init__(self, kind):
        self.kind = kind
    def host(self, a):
        return np.array(a, copy=True)

def source_state(repo, spec):
    path, endpoint = q21_sources(repo)
    seal = load(path.with_suffix('.seal.json'))
    need(seal['identity_sha256'] == spec['source_state_identity'], 'Pinned Q21 state identity differs')
    with np.load(path, allow_pickle=False) as z:
        backend = str(z['backend'])
        need(str(z['identity_sha256']) == spec['source_state_identity'], 'Q21 embedded optimizer identity differs')
        state = {key: z[key].copy() if z[key].size else None for key in ['n', 'old_g', 'old_z', 'direction']}
        state.update(alpha=float(z['alpha']), iteration=int(z['iteration']), next_observe=int(z['next_observe']), observe_spacing=int(z['observe_spacing']))
    need(state['iteration'] == 295 and np.isclose(state['alpha'], spec['spec']['expected']['optimizer_alpha'], rtol=0, atol=1e-15), 'Q21 retained iteration/alpha differs')
    for key in ['n', 'old_g', 'old_z', 'direction']:
        need(state[key] is not None and state[key].shape == (97, 97, 97, 3) and state[key].dtype == np.float64 and np.isfinite(state[key]).all(), 'Q21 incomplete/invalid memory: ' + key)
    with np.load(endpoint, allow_pickle=False) as z:
        need(np.array_equal(z['field'], state['n']), 'Q21 optimizer state differs from assessed endpoint')
    return state, backend

def choose_backend(state, original, requested, grid):
    # auto preserves the retained backend. Availability failure is explicit;
    # selecting cpu requests a documented common backend transfer for BOTH arms.
    kind = original if requested == 'auto' else requested
    engine = Engine(kind)
    initial = engine.xp.asarray(state['n'])
    audit = engine.audit(initial, grid)
    if kind == 'cuda':
        free, total = engine.xp.cuda.runtime.memGetInfo()
        need(free > 2 * 1024**3, 'Require 2 GiB free GPU memory before Q21; choose cpu explicitly if unavailable')
    record = {'recorded_at': stamp(), 'requested': requested, 'source_backend': original, 'selected_backend': kind,
              'backend_transfer': kind != original, 'same_backend_for_both_arms': True, 'initial_energy_gradient_audit': audit,
              'cuda_identity': engine.port.identity() if kind == 'cuda' else None,
              'scope': 'Exact optimizer arrays/scalars retained. A requested backend transfer is shared by both arms and is not claimed as bitwise continuation of the original floating-point path.'}
    del initial, engine
    gc.collect()
    return record

def check_reserve(out):
    import shutil
    need(host()['available_gib'] >= 6, 'Host memory reserve reached; resume after closing unrelated applications')
    need(shutil.disk_usage(out).free >= 40 * 1024**3, 'Disk reserve reached; retained fields must not be deleted')

def charge_attempt(folder, committed_attempts, ceiling):
    ledger = load(folder / 'attempt-ledger.json') if (folder / 'attempt-ledger.json').exists() else []
    need(len(ledger) >= committed_attempts, 'Attempt ledger lost committed charges; refuse to refund or continue')
    need(all(row['attempt'] == index + 1 and row['charged_before_execution'] for index, row in enumerate(ledger)), 'Attempt ledger sequence differs')
    need(len(ledger) < ceiling, 'Arm attempt ceiling exhausted')
    if ledger and len(ledger) > committed_attempts:
        ledger[-1]['interrupted_or_uncommitted'] = True
    ledger.append({'recorded_at': stamp(), 'attempt': len(ledger) + 1, 'charged_before_execution': True})
    save(folder / 'attempt-ledger.json', ledger)
    return len(ledger)

def history_plot(path, arms):
    colors = {'exact': '#2563eb', 'memory-reset': '#dc2626'}
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="450" viewBox="0 0 1100 450"><rect width="100%" height="100%" fill="white"/><style>text{font:14px Arial}</style>']
    for panel, key in enumerate(['relative_force_l2', 'acceleration_max']):
        xs, ys = [], []
        for record in arms.values():
            xs += [r['iteration'] for r in record['history']]
            ys += [r['metrics'][key] for r in record['history']]
        left, top, width, height = 70 + panel * 540, 60, 450, 280
        parts += [f'<text x="{left}" y="30">{key}: measured observations</text>', f'<path d="M{left} {top}V{top+height}H{left+width}" fill="none" stroke="#334155"/>']
        for name, record in arms.items():
            points = ' '.join(f'{left+width*(r["iteration"]-min(xs))/max(max(xs)-min(xs),1):.2f},{top+height-height*r["metrics"][key]/max(max(ys),1e-30):.2f}' for r in record['history'])
            parts += [f'<polyline points="{points}" fill="none" stroke="{colors[name]}" stroke-width="2"/>']
        parts += [f'<text x="{left}" y="365">Iteration {min(xs)} to {max(xs)}; linear y scale 0 to {max(ys):.6g}</text>']
    parts += ['<text x="70" y="405" fill="#2563eb">Blue: exact continuation</text><text x="400" y="405" fill="#dc2626">Red: memory-only reset</text><text x="70" y="435">Optimizer iteration is not physical time. Gates are evaluated from full fields; no fitted gate passes.</text></svg>']
    path.write_text('\n'.join(parts) + '\n')

def run_arm(out, name, parent, backend, grid, p, spec, phase):
    folder = out / 'q21' / name
    folder.mkdir(parents=True, exist_ok=True)
    identity = {'run_identity': load(out / 'identity.json'), 'arm': name, 'source_sha256': spec['state']['sha256'], 'backend': backend['selected_backend'], 'source_iteration': 295, 'grid': list(grid.shape), 'lengths': list(grid.lengths)}
    if (folder / 'DONE.json').exists():
        seal = load(folder / 'DONE.json')
        need(seal['identity'] == canonical(identity) and sha(folder / 'record.json') == seal['record_sha256'], 'Cached arm record differs')
        need(sha(folder / 'endpoint.npz') == seal['endpoint_sha256'], 'Cached arm endpoint differs')
        return load(folder / 'record.json')
    engine = Engine(backend['selected_backend'])
    if engine.kind == 'cuda':
        need(engine.port.identity() == backend['cuda_identity'], 'CUDA device/runtime changed on resume')
    control = folder / 'control.json'
    if control.exists():
        c = load(control)
        need(c['identity'] == canonical(identity), 'Arm checkpoint identity differs')
        state = restore(folder / ('state-' + str(c['slot']) + '.npz'), engine, identity)
        history, slot, committed_attempts = c['history'], c['slot'], c['committed_attempts']
        need(c['history_sha256'] == canonical(history) and history[-1]['iteration'] == state['iteration'], 'Committed history/checkpoint differs')
        ledger = load(folder / 'attempt-ledger.json') if (folder / 'attempt-ledger.json').exists() else []
        need(len(ledger) >= committed_attempts and int(state['iteration']) - 295 <= committed_attempts, 'Committed attempt ledger differs; refuse budget refund')
        replay = metrics(engine.host(state['n']), grid, p)
        for key in ['energy', 'relative_force_l2', 'acceleration_max', 'tail_fraction', 'guard_fraction']:
            need(np.isclose(replay[key], history[-1]['metrics'][key], rtol=1e-6, atol=1e-10), 'Resumed field/history metric replay differs: ' + key)
    else:
        state = split_state(parent, name == 'memory-reset')
        initial_digest = state_digest(state)
        before = state_digest(parent)
        need(initial_digest['n'] == before['n'] and initial_digest['alpha'] == before['alpha'] and initial_digest['iteration'] == before['iteration'], 'Memory intervention altered field/alpha/iteration')
        if name == 'exact':
            need(initial_digest == before, 'Exact arm memory differs from retained optimizer state')
        else:
            need(all(initial_digest[k] is None for k in ['old_g', 'old_z', 'direction']), 'Reset arm retained conjugacy memory')
        save(folder / 'INTERVENTION.json', {'recorded_at': stamp(), 'before': before, 'after': initial_digest, 'cleared_memory_only': name == 'memory-reset', 'initial_alpha_equal': True})
        for key in ['n', 'old_g', 'old_z', 'direction']:
            if state[key] is not None:
                state[key] = engine.xp.asarray(state[key]).copy()
        m = metrics(engine.host(state['n']), grid, p)
        history = [{'recorded_at': stamp(), 'iteration': state['iteration'], 'attempts': 0, 'alpha': state['alpha'], 'metrics': m, 'gates': gate_result(m, 21, p), 'objective_calls': 0}]
        slot, committed_attempts = 0, 0
        checkpoint(folder / 'state-0.npz', state, engine, identity)
        save(control, {'identity': canonical(identity), 'slot': slot, 'history': history, 'history_sha256': canonical(history), 'committed_attempts': 0})
    reason = 'diagnostic_attempt_budget'
    while True:
        if (folder / 'LINE-SEARCH-STOP.json').exists():
            reason = 'line_search_stalled'
            break
        ledger = load(folder / 'attempt-ledger.json') if (folder / 'attempt-ledger.json').exists() else []
        if len(ledger) >= spec['attempts_per_arm']:
            break
        if STOP.is_set() or (out / 'STOP.json').exists():
            raise KeyboardInterrupt('Orderly pause before next optimizer attempt')
        if not history[-1]['gates']['representation']:
            reason = 'representation_gate_failed'
            break
        if history[-1]['gates']['strict_stationary']:
            reason = 'strict_stationarity_measured_boundary_reported_separately'
            break
        check_reserve(out)
        attempt = charge_attempt(folder, committed_attempts, spec['attempts_per_arm'])
        phase.update(name='q21-paired-test', arm=name, iteration=int(state['iteration']), charged_arm_attempts=attempt)
        charged_total = sum(len(load(path)) for path in (out / 'q21').glob('*/attempt-ledger.json'))
        save(out / 'status.json', {'recorded_at': stamp(), 'status': 'working', 'phase': dict(phase), 'charged_q21_attempts': charged_total, 'maximum_q21_attempts': 40, 'physical_time_steps': 0, 'error': None})
        accepted, step = engine.step(state, grid)
        if not accepted:
            reason = 'line_search_stalled'
            save(folder / 'LINE-SEARCH-STOP.json', {'recorded_at': stamp(), 'attempt': attempt, **step})
            break
        engine.sync()
        audit = engine.audit(state['n'], grid)
        m = metrics(engine.host(state['n']), grid, p)
        history.append({'recorded_at': stamp(), 'iteration': int(state['iteration']), 'attempts': attempt, 'alpha': float(state['alpha']), 'metrics': m, 'gates': gate_result(m, 21, p), 'objective_calls': step['objective_calls'], 'step': step, 'backend_audit': audit})
        new_slot = 1 - slot
        checkpoint(folder / ('state-' + str(new_slot) + '.npz'), state, engine, identity)
        save(control, {'identity': canonical(identity), 'slot': new_slot, 'history': history, 'history_sha256': canonical(history), 'committed_attempts': attempt})
        slot, committed_attempts = new_slot, attempt
        phase.update(iteration=int(state['iteration']), relative_force_l2=m['relative_force_l2'], acceleration_max=m['acceleration_max'])
        log('Q21 measured observation', arm=name, iteration=int(state['iteration']), attempts=attempt, force=m['relative_force_l2'], acceleration=m['acceleration_max'], all_gates=history[-1]['gates']['all_readiness_gates'])
    endpoint = folder / 'endpoint.npz'
    checkpoint(endpoint, state, engine, identity)
    ledger = load(folder / 'attempt-ledger.json') if (folder / 'attempt-ledger.json').exists() else []
    record = {'recorded_at': stamp(), 'status': 'measured_pending_review', 'arm': name, 'identity': canonical(identity), 'reason': reason,
              'attempts_charged': len(ledger), 'accepted_steps': int(state['iteration']) - 295, 'source_iteration': 295,
              'history': history, 'final': history[-1], 'objective_calls_committed': sum(r['objective_calls'] for r in history),
              'objective_calls_scope': 'Committed observations only; interrupted/uncommitted calls may be unknown and remain charged as attempts',
              'fits': {key: fit_history(history, key) for key in ['relative_force_l2', 'acceleration_max']},
              'physical_time_steps': 0, 'all_gates_preserved': True}
    save(folder / 'record.json', record)
    save(folder / 'DONE.json', {'recorded_at': stamp(), 'identity': canonical(identity), 'record_sha256': sha(folder / 'record.json'), 'endpoint_sha256': sha(endpoint)})
    del engine, state
    gc.collect()
    return record

def seal(out):
    live = {'evidence.zip', 'heartbeat.json', 'telemetry-latest.json', 'supervisor.json', 'worker-launch.json', 'status.json', 'STOP.json', 'SHA256SUMS'}
    manifest = [{'path': p.relative_to(out).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in sorted(out.rglob('*.npz'))]
    save(out / 'FIELD-MANIFEST.json', {'recorded_at': stamp(), 'fields': manifest, 'contents': 'Full float64 optimizer states/endpoints retained locally; compact evidence contains hashes only'})
    members = [p for p in sorted(out.rglob('*')) if p.is_file() and p.suffix not in ['.npz', '.so', '.tmp', '.lock'] and not (p.parent == out and p.name in live) and '__pycache__' not in p.parts]
    checks = ''.join(sha(p) + '  ' + p.relative_to(out).as_posix() + '\n' for p in members)
    (out / 'SHA256SUMS').write_text(checks)
    with zipfile.ZipFile(out / 'evidence.tmp', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in members:
            z.write(path, path.relative_to(out).as_posix())
        z.writestr('SHA256SUMS', checks)
    with zipfile.ZipFile(out / 'evidence.tmp') as z:
        need(z.testzip() is None, 'Evidence CRC failed')
    (out / 'evidence.tmp').replace(out / 'evidence.zip')

def report(out, record):
    text = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Q21 paired test and native Q22 comparison</title><style>body{font:16px/1.5 system-ui;max-width:1200px;margin:30px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:100%}</style><h1>Q21 controlled test and historical Q22 comparison</h1>'
    text += '<p>Optimizer iterations are not physical time. Q21 changes conjugacy memory only between paired arms. Historical Q22 is evaluated without normalization, relaxation or resampling. Existing positive static findings remain recorded within their original scope.</p><p><a href="handover/assessment/ASSESSMENT.html">Prior diagnosis assessment</a> · <a href="record.json">Full measured results</a> · <a href="Q22-INVENTORY.json">Historical field inventory and deferral</a></p>'
    if len(record.get('arms', {})) == 2:
        history_plot(out / 'q21-comparison.svg', record['arms'])
        text += '<h2>Measured Q21 histories</h2><img src="q21-comparison.svg" alt="Paired force and acceleration histories"/>'
        for name, arm in record['arms'].items():
            description = {'reason': arm['reason'], 'attempts_charged': arm['attempts_charged'], 'accepted_steps': arm['accepted_steps'], 'final_gates': arm['final']['gates'], 'fits': arm['fits']}
            text += '<details><summary>' + html.escape(name) + ': measured disposition and descriptive fits</summary><pre>' + html.escape(json.dumps(description, indent=2)) + '</pre></details>'
    for key in ['status', 'q2', 'derivative_check', 'comparison', 'q22', 'deferred', 'error']:
        text += '<h2>' + html.escape(key) + '</h2><pre>' + html.escape(json.dumps(record.get(key), indent=2)) + '</pre>'
    text += '<p>Original stationarity, representation and boundary gates remain unchanged. A failed boundary check remains failed during this diagnostic test; it is never described as motion readiness. Fits are descriptive and cannot extend the 40-attempt allocation.</p></html>\n'
    (out / 'REPORT.html').write_text(text)
    (out / 'SUMMARY.md').write_text('# Q21/Q22 controlled evaluations\n\n' + json.dumps(stamp()) + '\n\nStatus: **' + record['status'] + '**. Q21 charged attempts: ' + str(sum(r.get('attempts_charged', 0) for r in record.get('arms', {}).values())) + ' / 40. Q22 optimizer steps: 0. Physical-time steps: 0.\n\nRead REPORT.html and the exact-source inventory; every unresolved and deferred outcome is retained.\n')

def execute(repo, out):
    from electron_field_topology.sf_time import Grid
    verify_manifest(ROOT)
    verify_sources(repo)
    identity = load(out / 'identity.json')
    need(identity['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Frozen evaluation package differs')
    plan = load(ROOT / 'PLAN.json')
    phase = {'name': 'controls-and-source-authentication'}
    done = threading.Event()
    record = {'recorded_at': stamp(), 'identity': identity, 'status': 'working', 'arms': {}, 'q22': None, 'error': None, 'physical_time_steps': 0,
              'deferred': ['Larger-domain intervention', 'Mesh changes', 'Motion simulations', 'Further Q values', 'Any continuation beyond 40 new Q21 attempts']}
    def heartbeat():
        while not done.is_set():
            save(out / 'heartbeat.json', {'recorded_at': stamp(), 'pid': os.getpid(), 'process_identity': process_identity(os.getpid()), 'operation': dict(phase)})
            done.wait(15)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    def update(final=False):
        for name in ['exact', 'memory-reset']:
            path = out / 'q21' / name / 'record.json'
            if (path.parent / 'DONE.json').exists():
                record['arms'][name] = load(path)
        charged = sum(len(load(path)) for path in (out / 'q21').glob('*/attempt-ledger.json')) if (out / 'q21').exists() else 0
        need(charged <= 40, 'Global diagnostic allocation exceeded')
        record['charged_q21_attempts'] = charged
        save(out / 'record.json', record)
        save(out / 'status.json', {'recorded_at': stamp(), 'status': record['status'], 'phase': dict(phase), 'charged_q21_attempts': charged, 'maximum_q21_attempts': 40, 'error': record['error'], 'q22_status': record['q22'].get('status') if record['q22'] else None, 'physical_time_steps': 0})
        report(out, record)
        if final:
            seal(out)
    try:
        check_reserve(out)
        control = plan['q2']
        path = original_run(repo) / control['original_relative_path']
        check_file(path, control['sha256'])
        with np.load(path, allow_pickle=False) as z:
            n = z['field'].copy()
        control_grid = Grid((control['nodes'],) * 3, (control['length'],) * 3, 'fixed')
        m = metrics(n, control_grid, plan['registered_gates'])
        for key in ['energy', 'relative_force_l2', 'acceleration_max', 'tail_fraction', 'guard_fraction']:
            need(np.isclose(m[key], control['expected'][key], rtol=1e-6, atol=1e-10), 'Q2 replay mismatch: ' + key)
        record['q2'] = {'recorded_at': stamp(), 'metrics': m, 'gates': gate_result(m, 2, plan['registered_gates']), 'source_sha256': control['sha256']}
        need(record['q2']['gates']['all_readiness_gates'], 'Q2 control failed; no candidate optimizer work allowed')
        del n
        parent, original_backend = source_state(repo, plan['q21'])
        grid = Grid((plan['q21']['spec']['nodes'],) * 3, (plan['q21']['spec']['length'],) * 3, 'fixed')
        measured = metrics(parent['n'], grid, plan['registered_gates'])
        for key in ['energy', 'relative_force_l2', 'acceleration_max', 'tail_fraction', 'guard_fraction']:
            need(np.isclose(measured[key], plan['q21']['spec']['expected'][key], rtol=1e-6, atol=1e-10), 'Q21 source replay mismatch: ' + key)
        need(np.max(np.abs(parent['n'][grid.fixed_mask()] - [0, 0, 1])) < 1e-12, 'Q21 held layers differ; no projection permitted')
        derivative_path = out / 'DIRECTIONAL-DERIVATIVES.json'
        phase.update(name='q21-constrained-directional-derivatives')
        if derivative_path.exists():
            need(load(out / 'DERIVATIVE-SEAL.json')['sha256'] == sha(derivative_path), 'Cached derivative check changed')
            record['derivative_check'] = load(derivative_path)
        else:
            record['derivative_check'] = derivative_check(parent['n'], grid, plan['directional_derivatives'])
            save(derivative_path, record['derivative_check'])
            save(out / 'DERIVATIVE-SEAL.json', {'sha256': sha(derivative_path), 'source_state_sha256': plan['q21']['state']['sha256']})
        update()
        if record['derivative_check']['passed']:
            backend_path = out / 'BACKEND.json'
            if backend_path.exists():
                backend = load(backend_path)
                need(backend['requested'] == identity['requested_backend'], 'Resume backend request differs')
            else:
                backend = choose_backend(parent, original_backend, identity['requested_backend'], grid)
                save(backend_path, backend)
            for name in ['exact', 'memory-reset']:
                record['arms'][name] = run_arm(out, name, parent, backend, grid, plan['registered_gates'], plan['q21'], phase)
                update()
            record['comparison'] = paired_summary(record['arms'])
            save(out / 'PAIRED-COMPARISON.json', record['comparison'])
        else:
            record['deferred'].append('Both Q21 optimizer arms blocked by failed constrained derivative validation')
        del parent
        gc.collect()
        if STOP.is_set() or (out / 'STOP.json').exists():
            raise KeyboardInterrupt('Orderly pause before native Q22 evaluation')
        inventory = load(out / 'Q22-INVENTORY.json')
        if inventory['status'] == 'authenticated':
            phase.update(name='historical-native-q22-cell-d4-comparison', arm=None)
            target = out / 'q22'
            target.mkdir(exist_ok=True)
            if (target / 'DONE.json').exists():
                need(sha(target / 'record.json') == load(target / 'DONE.json')['sha256'], 'Cached native Q22 result changed')
                record['q22'] = load(target / 'record.json')
            else:
                check_reserve(out)
                check_file(Path(inventory['path']), plan['q22']['sha256'])
                record['q22'] = q22_compare(Path(inventory['path']), plan['q22'], plan['registered_gates'], target)
                check_file(Path(inventory['path']), plan['q22']['sha256'])
                save(target / 'record.json', record['q22'])
                save(target / 'DONE.json', {'recorded_at': stamp(), 'sha256': sha(target / 'record.json')})
        else:
            record['q22'] = inventory
            record['deferred'].append('Historical native Q22 operator comparison: exact original field unavailable')
        q21_sources(repo)
        record.update(status='complete_pending_review', finished_at=stamp())
        phase.update(name='complete', arm=None)
        update(True)
        log('Q21/Q22 evaluations complete', output=str(out), charged_q21_attempts=record['charged_q21_attempts'], q22_status=record['q22']['status'], evidence=str(out / 'evidence.zip'))
    except BaseException as error:
        resource = isinstance(error, RuntimeError) and 'reserve reached' in str(error).lower()
        record.update(status='interrupted' if isinstance(error, KeyboardInterrupt) or resource else 'failed', error=str(error))
        update(True)
        if record['status'] == 'failed':
            traceback.print_exc()
            raise
    finally:
        done.set()
        thread.join(timeout=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo / 'src'))
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    with (original_run(args.repo) / '.worker.lock').open('r') as a, (source_run(args.repo) / '.worker.lock').open('r') as b, (args.output / '.worker.lock').open('a') as c:
        for lock in [a, b, c]:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        execute(args.repo.resolve(), args.output.resolve())

if __name__ == '__main__':
    main()
