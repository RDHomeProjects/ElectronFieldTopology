"""Six-parent, policy-versioned continuation. No mesh/domain/motion execution."""
import argparse
import csv
import fcntl
import gc
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import traceback
import zipfile
import numpy as np
from common import ROOT, canonical, load, log, need, save, sha, stamp
from integrity import baseline, check_sources, original_identity, parent_check, process_identity, source_out
from science.engine import Engine, checkpoint, restore
from science.numeric import Branch, boundary, immutable_field, metrics, representation, resources, stationary
from science.fits import decide

STOP = threading.Event()

class HostCheckpoint:
    """Read CUDA-origin float64 state on CPU without taking an optimizer step."""
    kind = 'cuda'
    xp = np
    def host(self, value):
        return np.array(value, copy=True)

def state_digests(state):
    result = {k: state.get(k, 0) for k in ['alpha', 'iteration', 'next_observe', 'observe_spacing']}
    for key in ['n', 'old_g', 'old_z', 'direction']:
        a = state[key]
        result[key] = None if a is None else {'dtype': str(a.dtype), 'shape': list(a.shape), 'sha256': hashlib.sha256(memoryview(np.ascontiguousarray(a)).cast('B')).hexdigest()}
    return result

def validate_state(state, spec):
    shape = (spec['nodes'],) * 3 + (3,)
    need(state['n'] is not None and state['n'].shape == shape, 'Retained field shape differs')
    need(state['iteration'] == spec['initial_iteration'] and np.isfinite(state['alpha']) and state['alpha'] > 0, 'Retained optimizer scalar differs')
    memory = [state[k] is not None for k in ['old_g', 'old_z', 'direction']]
    need(all(memory) or not any(memory), 'Partial conjugacy memory is invalid')
    for key in ['old_g', 'old_z', 'direction']:
        need(state[key] is None or state[key].shape == shape, 'Optimizer memory shape differs: ' + key)

def migrate(repo, out, spec, identity, p, grid):
    folder = out / 'continuation' / spec['id']
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / 'MIGRATION.json'
    parent = parent_check(repo, spec)
    branch_identity = {**identity, 'parent_checkpoint_sha256': parent['state_sha256'],
                       'seed': spec['seed'], 'shape': list(grid.shape), 'lengths': list(grid.lengths), 'backend': spec['backend']}
    if marker.exists():
        m = load(marker)
        need(m['new_identity'] == canonical(branch_identity) and m['source_sha256'] == parent['state_sha256'], 'Migration identity differs')
        need(sha(folder / 'parent-state.npz') == parent['state_sha256'], 'Immutable copied optimizer parent differs')
        return parent['receipt'], branch_identity
    host_engine = HostCheckpoint()
    state = restore(parent['state'], host_engine, parent['original_identity'])
    validate_state(state, spec)
    before = state_digests(state)
    need(np.max(np.abs(np.linalg.norm(state['n'], axis=-1) - 1)) < p['unit_limit'], 'Retained field unit gate failed')
    need(np.max(np.abs(state['n'][grid.fixed_mask()] - [0, 0, 1])) < 1e-12, 'Retained held layers changed; no projection permitted')
    with np.load(parent['endpoint'], allow_pickle=False) as z:
        need(np.array_equal(state['n'], z['field']), 'Optimizer state and terminal field differ')
    # Authenticate the actual field against its saved scientific measurements.
    resources(out, p)
    measured = metrics(state['n'], grid, p)
    expected = parent['history'][-1]
    for key in ['energy', 'relative_force_l2', 'acceleration_max', 'acceleration_rms', 'hopf_integral', 'minimum_corner_cone', 'unit_error', 'tail_fraction', 'guard_fraction']:
        need(np.isclose(measured[key], expected[key], rtol=1e-6, atol=1e-10), 'Retained CPU metric replay differs: ' + spec['id'] + '/' + key)
    need(representation(measured, spec['seed']['q'], p), 'Retained parent no longer meets representation gates')
    # Keep the byte-exact original parent as well as a new-identity checkpoint.
    target = folder / 'parent-state.npz'
    if not target.exists():
        shutil.copy2(parent['state'], target)
    need(sha(target) == parent['state_sha256'], 'Parent copy differs')
    checkpoint(folder / 'state-0.npz', state, host_engine, branch_identity)
    restored = restore(folder / 'state-0.npz', host_engine, branch_identity)
    need(state_digests(restored) == before, 'Migration altered optimizer arrays or scalar memory')
    del restored
    save(folder / 'history.json', parent['history'])
    save(folder / 'attempts.json', {'recorded_at': stamp(), 'attempts': spec['already_spent_attempts'], 'scope': 'Original attempts retained; interrupted/replayed attempts remain charged'})
    save(folder / 'latest.json', {'recorded_at': stamp(), 'slot': 0, 'iteration': state['iteration'], 'identity': canonical(branch_identity), 'history_sha256': canonical(parent['history'])})
    # The terminal decision will be evaluated once using the corrected PRE-decision
    # memory. Seeding its post-decision count would count the same vote twice.
    save(folder / 'planner.json', {'plateau_count': spec['prior_plateau_count'], 'plateau_epoch': spec['prior_plateau_epoch'], 'migration_seed': True})
    save(marker, {'recorded_at': stamp(), 'source': parent['state'], 'source_sha256': parent['state_sha256'], 'original_identity': canonical(parent['original_identity']),
                  'new_identity': canonical(branch_identity), 'optimizer_arrays_and_scalars_byte_equal': True, 'state_digests': before,
                  'cpu_metric_replay': measured, 'original_metrics': expected, 'spent_attempts_preserved': spec['already_spent_attempts'],
                  'total_ceiling': 500, 'additional_ceiling': spec['maximum_additional_attempts'], 'source_modified': False})
    del state
    gc.collect()
    return parent['receipt'], branch_identity

class SafeBranch(Branch):
    def batch_pending(self, pending):
        """Persist a fixed target and observation schedule across an interruption."""
        interval = pending['choice']['observe']
        target = pending['target_iteration']
        if not self.s.get('next_observe') or self.s.get('observe_spacing') != interval:
            self.s['next_observe'] = self.s['iteration'] + interval
            self.s['observe_spacing'] = interval
        reason = None
        while self.s['iteration'] < target and self.attempts < 500:
            if STOP.is_set():
                self.persist()
                raise KeyboardInterrupt('Orderly pause at an optimizer-step boundary')
            if not representation(self.history[-1], self.seed['q'], self.p) or stationary(self.history[-1], self.seed['q'], self.p):
                break
            resources(self.folder, self.p)
            self.attempts += 1
            save(self.folder / 'attempts.json', {'recorded_at': stamp(), 'attempts': self.attempts, 'scope': 'Every attempted step, including interrupted/replayed work, consumes the total 500 ceiling'})
            accepted, step = self.engine.step(self.s, self.g)
            if not accepted:
                reason = step['reason']
                break
            reset_observation = self.s['iteration'] % 200 in (199, 0)
            if self.s['iteration'] >= self.s['next_observe'] or self.s['iteration'] >= target or reset_observation:
                self.observe()
                self.s['next_observe'] = self.s['iteration'] + interval
                self.persist()
                if self.s['iteration'] % 200 == 199:
                    checkpoint(self.folder / f'before-reset-{self.s["iteration"]:05d}.npz', self.s, self.engine, self.identity)
                elif reset_observation:
                    immutable_field(self.folder / f'after-reset-{self.s["iteration"]:05d}.npz', self.engine.host(self.s['n']), self.g, self.seed['q'], self.identity, self.s['iteration'])
        if self.history[-1]['iteration'] != self.s['iteration']:
            self.observe()
        self.persist()
        return reason

def plan_once(branch, folder, spec, p):
    pending_path = folder / 'pending.json'
    if pending_path.exists():
        retained = load(pending_path)
        if retained['status'] == 'pending' or (retained['choice']['action'] == 'stop' and retained['base_iteration'] == branch.s['iteration']):
            return retained
    previous = load(folder / 'planner.json')
    choice = decide(branch.history, p, 500 - branch.attempts, previous.get('plateau_count', 0), plateau_epoch=previous.get('plateau_epoch'))
    pending = {'recorded_at': stamp(), 'status': 'pending', 'choice': choice, 'base_iteration': branch.s['iteration'],
               'base_attempts': branch.attempts, 'target_iteration': branch.s['iteration'] + choice['steps'],
               'history_sha256': canonical(branch.history)}
    # Journal first: a crash can never consume a plateau vote without retaining
    # its executable decision. Reusing a pending decision does not vote again.
    save(pending_path, pending)
    return pending

def run_branch(repo, out, spec, identity, p):
    from electron_field_topology.sf_time import Grid
    grid = Grid((spec['nodes'],) * 3, (spec['length'],) * 3, 'fixed')
    folder = out / 'continuation' / spec['id']
    receipt, branch_identity = migrate(repo, out, spec, identity, p, grid)
    if (folder / 'result.json').exists():
        old = load(folder / 'result.json')
        need(load(folder / 'result.seal.json')['sha256'] == sha(folder / 'result.json'), 'Continuation result seal differs')
        if old['status'] != 'active':
            need(old['identity'] == canonical(branch_identity) and sha(Path(old['endpoint'])) == old['checkpoint_sha256'], 'Terminal continuation endpoint differs')
            return old
    # Branch constructs exactly this identity; it restores all CG memory.
    root_identity = {k: v for k, v in branch_identity.items() if k not in ('seed', 'shape', 'lengths', 'backend')}
    b = SafeBranch(folder, grid, spec['seed'], p, receipt, root_identity)
    try:
        ready = folder / 'BACKEND-REPLAY.json'
        if not ready.exists():
            audit = b.engine.audit(b.s['n'], grid, p['qualification_rtol'], p['qualification_atol'])
            save(ready, {'recorded_at': stamp(), 'identity': canonical(b.identity), 'audit': audit, 'device': b.engine.port.identity() if b.engine.port is not None else None})
        else:
            need(load(ready)['identity'] == canonical(b.identity), 'Backend replay receipt identity differs')
        need(b.attempts >= spec['already_spent_attempts'] and b.attempts <= 500, 'Continuation attempt accounting differs')
        status = reason = None
        last = b.history[-1]
        if not representation(last, spec['seed']['q'], p):
            status = 'representation_unresolved'
        elif stationary(last, spec['seed']['q'], p):
            status = 'static_survivor' if boundary(last, p) else 'stationary_boundary_unresolved'
        elif b.attempts >= 500:
            status, reason = 'budget_exhausted_unresolved', 'Total 500-attempt ceiling reached'
        else:
            pending = plan_once(b, folder, spec, p)
            choice = pending['choice']
            save(folder / 'planner.json', choice)
            ds = load(folder / 'decisions.json') if (folder / 'decisions.json').exists() else []
            key = canonical({k: pending[k] for k in ['base_iteration', 'base_attempts', 'history_sha256']})
            if not any(x['decision_id'] == key for x in ds):
                ds.append({'recorded_at': stamp(), 'decision_id': key, **choice})
                save(folder / 'decisions.json', ds)
            need(not choice.get('systemic_fault'), choice['reason'])
            if choice['action'] == 'stop':
                status = 'preparation_unresolved'
                reason = choice['reason']
            else:
                if choice.get('turn_detected'):
                    prefix = f'turn-e{b.s["iteration"] // 200}-'
                    if len(list(folder.glob(prefix + '*.npz'))) < p['maximum_turn_snapshots_per_optimizer_epoch']:
                        immutable_field(folder / f'{prefix}{b.s["iteration"]:05d}.npz', b.engine.host(b.s['n']), grid, spec['seed']['q'], b.identity, b.s['iteration'])
                reason = b.batch_pending(pending)
            save(folder / 'pending.json', {**pending, 'status': 'completed', 'finished_at': stamp()})
            last = b.history[-1]
            if not representation(last, spec['seed']['q'], p):
                status = 'representation_unresolved'
            elif stationary(last, spec['seed']['q'], p):
                status = 'static_survivor' if boundary(last, p) else 'stationary_boundary_unresolved'
            elif reason and status is None:
                status = 'preparation_unresolved'
            elif b.attempts >= 500:
                status = 'budget_exhausted_unresolved'
        result = b.result(status or 'active', reason)
        result.update(original_attempts=spec['already_spent_attempts'], additional_attempts=b.attempts - spec['already_spent_attempts'], total_attempt_ceiling=500,
                      parent_checkpoint_sha256=load(folder / 'MIGRATION.json')['source_sha256'], policy_version=2)
        save(folder / 'result.json', result)
        save(folder / 'result.seal.json', {'sha256': sha(folder / 'result.json'), 'identity': canonical(b.identity)})
        return result
    except BaseException:
        b.persist()
        raise
    finally:
        engine = b.engine
        del b
        gc.collect()
        if engine.kind == 'cuda':
            engine.xp.get_default_memory_pool().free_all_blocks()

def outcomes(out, selection):
    rows = []
    for spec in selection:
        folder = out / 'continuation' / spec['id']
        result = folder / 'result.json'
        row = load(result) if result.exists() else {'seed': spec['seed'], 'status': 'pending', 'attempts': spec['already_spent_attempts'], 'iteration': spec['initial_iteration']}
        # The result may predate a pause or a failed attempt; charged attempts
        # and accepted checkpoint iteration remain authoritative separately.
        if (folder / 'attempts.json').exists():
            row['attempts'] = load(folder / 'attempts.json')['attempts']
        if (folder / 'latest.json').exists():
            row['iteration'] = load(folder / 'latest.json')['iteration']
        if (folder / 'history.json').exists():
            row['metrics'] = load(folder / 'history.json')[-1]
            row['measured_iteration'] = row['metrics']['iteration']
            row['strict_stationary'] = stationary(row['metrics'], spec['seed']['q'], load(ROOT / 'PLAN.json'))
            row['boundary_admitted'] = boundary(row['metrics'], load(ROOT / 'PLAN.json'))
        row['additional_attempts'] = row['attempts'] - spec['already_spent_attempts']
        rows.append(row)
    return rows

def render(out, record, seal=False):
    rows = record['branches']
    columns = ['seed', 'status', 'iteration', 'measured_iteration', 'total_attempts', 'additional_attempts', 'force', 'acceleration', 'tail', 'strict_stationary', 'boundary_admitted']
    flat = []
    for row in rows:
        m = row.get('metrics', {})
        flat.append(dict(zip(columns, [row['seed']['id'], row['status'], row['iteration'], row.get('measured_iteration'), row['attempts'], row['additional_attempts'], m.get('relative_force_l2'), m.get('acceleration_max'), m.get('tail_fraction'), row.get('strict_stationary'), row.get('boundary_admitted')])))
    with (out / 'screening.csv').open('w', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
        w.writeheader()
        w.writerows(flat)
    table = '<tr>' + ''.join('<th>' + x + '</th>' for x in columns) + '</tr>'
    table += ''.join('<tr>' + ''.join('<td>' + html.escape(str(row[k])) + '</td>' for k in columns) + '</tr>' for row in flat)
    plots = []
    for row in rows:
        hpath = out / 'continuation' / row['seed']['id'] / 'history.json'
        if not hpath.exists():
            continue
        history = load(hpath)
        xmax = max(history[-1]['iteration'], 1)
        import math
        keys = [('relative_force_l2', 1e-4, '#2563eb'), ('acceleration_max', 1e-3, '#dc2626')]
        values = [math.log10(max(h[k] / gate, 1e-12)) for h in history for k, gate, color in keys]
        low, high = min(-.2, min(values)), max(.2, max(values))
        xy = lambda iteration, value: (45 + 600 * iteration / xmax, 210 - 170 * (math.log10(max(value, 1e-12)) - low) / (high - low))
        svg = '<svg viewBox="0 0 680 255" role="img" aria-label="Measured residual histories" style="max-width:900px;width:100%"><rect x="45" y="40" width="600" height="170" fill="#f8fafc"/>'
        gate_y = xy(0, 1)[1]
        svg += f'<path d="M45 {gate_y}H645" stroke="#444" stroke-dasharray="4 4"/>'
        for k, gate, color in keys:
            points = ' '.join('%.2f,%.2f' % xy(h['iteration'], h[k] / gate) for h in history)
            svg += f'<polyline points="{points}" fill="none" stroke="{color}"/>'
        svg += f'<text x="45" y="25">Force/gate (blue); acceleration/gate (red); log scale</text><text x="45" y="240">Optimizer iteration 0–{xmax}; not physical time</text></svg>'
        plots.append('<h3>' + html.escape(row['seed']['id']) + '</h3>' + svg)
    intro = 'Six retained optimizer parents; 500 total attempted steps each, including original and interrupted work. CUDA optimizer plus independent CPU diagnostics; unchanged gates. Curves show measured optimizer histories, not physical motion. Dashed horizontal line is the stationarity threshold. A fit never grants admission. Original Q18 partial refinement remains a separate old-parent diagnostic; no mesh, domain or motion steps are run here.'
    (out / 'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Q17–Q32 policy-v2 continuation</title><style>body{font:15px/1.5 system-ui;max-width:1400px;margin:30px}td,th{padding:6px;border-bottom:1px solid #ddd}table{border-collapse:collapse}pre{white-space:pre-wrap}</style><h1>Q17–Q32 policy-v2 continuation</h1><p>' + html.escape(intro) + '</p><p>' + html.escape(record['status']) + '</p><p><a href="record.json">Full record</a> · <a href="screening.csv">CSV</a> · <a href="handover/assessment/ASSESSMENT.html">Prior policy audit</a></p><table>' + table + '</table>' + ''.join(plots) + '<h2>Deferrals and accounting</h2><pre>' + html.escape(json.dumps(record['deferrals'], indent=2)) + '</pre></html>\n')
    (out / 'SUMMARY.md').write_text('# Policy-v2 continuation\n\n' + json.dumps(stamp()) + '\n\nStatus: **' + record['status'] + '**. Additional attempts: ' + str(record['additional_attempts']) + ' / 1738 maximum.\n\nNo Q sector is physically rejected. Static gates do not establish long-time stability or electron acceptance. Mesh, domain and motion are deferred for review.\n')
    if seal:
        fields = [{'path': p.relative_to(out).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(out.rglob('*.npz'))]
        save(out / 'field-manifest.json', {'recorded_at': stamp(), 'fields': fields, 'scope': 'Full float64 fields and optimizer memory stay local; compact evidence contains declarations only'})
        allowed = {'.json', '.csv', '.md', '.html', '.py', '.sh', '.png', '.svg', '.zip'}
        files = [p for p in sorted(out.rglob('*')) if p.is_file() and p.suffix in allowed and p.name != 'evidence.zip' and '__pycache__' not in p.parts]
        # Include source evidence archives and nested package manifests as payloads.
        files += [p for p in sorted((out / 'handover').rglob('SHA256SUMS')) if p not in files]
        manifest = ''.join(sha(p) + '  ' + p.relative_to(out).as_posix() + '\n' for p in sorted(files))
        (out / 'SHA256SUMS').write_text(manifest)
        temporary = out / 'evidence.tmp'
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as z:
            for path in sorted(files):
                z.write(path, path.relative_to(out).as_posix())
            z.write(out / 'SHA256SUMS', 'SHA256SUMS')
        with zipfile.ZipFile(temporary) as z:
            need(z.testzip() is None, 'New compact evidence CRC failure')
        temporary.replace(out / 'evidence.zip')

def execute(repo, out):
    identity = load(out / 'identity.json')
    need(identity['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Frozen continuation package identity differs')
    need(identity['original_source_identity'] == canonical(check_sources(repo)), 'Original source identity differs')
    sys.path.insert(0, str(repo / 'src'))
    p = load(ROOT / 'PLAN.json')
    selection = load(ROOT / 'SELECTION.json')['branches']
    record = {'recorded_at': stamp(), 'status': 'working', 'identity': identity, 'plan': p,
              'deferrals': {'other_preparation_cases': 23, 'representation_cases': 5, 'mesh': 'deferred pending corrected preparation review',
                            'domain': 'deferred pending parent/mesh findings', 'motion': 'deferred; all original scientific gates retained',
                            'old_q18_mesh': {'attempts': 33, 'checkpoint_iteration': 32, 'latest_measured_iteration': 30, 'disposition': 'retained separately; never attached to a changed parent; 33 attempts remain charged against original mesh allocation'}},
              'maximum_additional_attempts': 1738, 'old_campaign_total_attempts': 5725, 'old_broad_attempts': 5692, 'branches': []}
    phase = {'name': 'migration-and-continuation'}
    finished = threading.Event()
    def heartbeat():
        while not finished.is_set():
            data = dict(phase)
            if data.get('seed'):
                folder = out / 'continuation' / data['seed']
                if (folder / 'history.json').exists():
                    last = load(folder / 'history.json')[-1]
                    data.update(iteration=last['iteration'], force=last['relative_force_l2'], acceleration=last['acceleration_max'])
            save(out / 'heartbeat.json', {'recorded_at': stamp(), 'pid': os.getpid(), 'process_identity': process_identity(os.getpid()), 'operation': data})
            finished.wait(15)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    def update(seal=False):
        record['branches'] = outcomes(out, selection)
        record['additional_attempts'] = sum(r['additional_attempts'] for r in record['branches'])
        record['campaign_total_attempts_including_original'] = 5725 + record['additional_attempts']
        save(out / 'record.json', record)
        save(out / 'status.json', {'recorded_at': stamp(), 'status': record['status'], 'phase': dict(phase), 'additional_attempts': record['additional_attempts'],
                                   'maximum_additional_attempts': 1738, 'terminal_branches': sum(r['status'] not in ('active', 'pending') for r in record['branches']), 'error': record.get('error')})
        render(out, record, seal)
    try:
        update()
        while True:
            results = outcomes(out, selection)
            if all(r['status'] not in ('active', 'pending') for r in results):
                break
            for spec, row in zip(selection, results):
                if STOP.is_set() or (out / 'STOP.json').exists():
                    raise KeyboardInterrupt('Operator/resource pause requested')
                if row['status'] not in ('active', 'pending'):
                    continue
                phase.update(seed=spec['id'], nodes=spec['nodes'], backend=spec['backend'], total_attempt_ceiling=500)
                run_branch(repo, out, spec, identity, p)
                update()
        phase.update(name='complete', seed=None)
        record.update(status='complete_pending_review', finished_at=stamp())
        combined = {row['seed']['id']: row for row in baseline()[0]['record.json']['broad']}
        combined.update({row['seed']['id']: row for row in outcomes(out, selection)})
        measured_parents = sorted([row for row in combined.values() if row.get('strict_stationary')], key=lambda row: (not row.get('boundary_admitted', False), row['q'], row['seed']['id']))
        save(out / 'NEXT-STAGE.json', {'recorded_at': stamp(), 'scope': 'Measured preparation reassessment for review; no automatic refinement or motion queue',
                                     'all_34_dispositions': list(combined.values()), 'stationary_parent_ids_for_review': [row['seed']['id'] for row in measured_parents],
                                     'stationary_and_boundary_admitted_ids': [row['seed']['id'] for row in measured_parents if row.get('boundary_admitted')],
                                     'mesh_steps': 0, 'domain_steps': 0, 'physical_time_steps': 0, 'old_q18_mesh_attempts_still_charged': 33,
                                     'original_deferrals_retained': baseline()[0]['record.json'].get('deferrals', []),
                                     'conditions': 'New refinement must name its exact corrected parent. Failed boundary admission remains visible. All original mesh/domain/motion gates and budgets require explicit subsequent assessment.'})
        update(True)
        log('Policy-v2 continuation completed', output=str(out), additional_attempts=record['additional_attempts'], evidence=str(out / 'evidence.zip'))
    except BaseException as error:
        resource = isinstance(error, RuntimeError) and ('reserve reached' in str(error).lower())
        record.update(status='interrupted' if isinstance(error, KeyboardInterrupt) or resource else 'failed', error=str(error))
        update(True)
        if record['status'] == 'failed':
            traceback.print_exc()
            raise
        log('Continuation paused; checkpoints retained', output=str(out), reason=str(error))
    finally:
        finished.set()
        thread.join(timeout=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    # Hold the old campaign lock for the entire new run, preventing old resume.
    with (source_out(args.repo) / '.worker.lock').open('r') as original_lock, (args.output / '.worker.lock').open('a') as new_lock:
        fcntl.flock(original_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(new_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        execute(args.repo.resolve(), args.output.resolve())

if __name__ == '__main__':
    main()
