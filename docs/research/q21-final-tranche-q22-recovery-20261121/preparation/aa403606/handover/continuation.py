"""Exact-memory migration and a finite, adaptively scheduled final tranche."""
import copy
import gc
import os
from pathlib import Path
import shutil
import numpy as np
from common import ROOT, canonical, load, log, need, save, sha, stamp
from engine import Engine, checkpoint, restore
from evaluations import gate_result, metrics, state_digest
from integrity import baseline, host, source_checkpoint
from planner import decide

def read_parent(repo, spec):
    path = source_checkpoint(repo)
    with np.load(path, allow_pickle=False) as z:
        need(str(z['identity_sha256']) == spec['source_identity'], 'Exact-315 embedded optimizer identity differs')
        kind = str(z['backend'])
        state = {key: z[key].copy() if z[key].size else None for key in ['n', 'old_g', 'old_z', 'direction']}
        state.update(alpha=float(z['alpha']), iteration=int(z['iteration']), next_observe=int(z['next_observe']), observe_spacing=int(z['observe_spacing']))
    need(state['iteration'] == spec['source_iteration'] and state['alpha'] == spec['expected_alpha'], 'Exact-315 scalar memory differs')
    for key in ['n', 'old_g', 'old_z', 'direction']:
        a = state[key]
        need(a is not None and a.shape == (spec['nodes'],)*3+(3,) and a.dtype == np.float64 and np.isfinite(a).all(), 'Exact-315 float64 conjugacy array differs: ' + key)
    return state, kind

def check_reserve(out):
    need(host()['available_gib'] >= 6, 'Host memory reserve reached; retained fields unchanged')
    need(shutil.disk_usage(out).free >= 40*1024**3, 'Disk reserve reached; retained fields unchanged')

def charge(folder, committed, ceiling):
    path = folder / 'attempt-ledger.json'
    ledger = load(path) if path.exists() else []
    need(len(ledger) >= committed, 'Attempt ledger lost committed charges; refusing budget refund')
    need(all(row['attempt'] == i+1 and row['charged_before_execution'] for i, row in enumerate(ledger)), 'Attempt ledger sequence differs')
    need(len(ledger) < ceiling, 'Final tranche attempt ceiling exhausted')
    if ledger and len(ledger) > committed:
        ledger[-1]['interrupted_or_uncommitted'] = True
    ledger.append({'recorded_at': stamp(), 'attempt': len(ledger)+1, 'charged_before_execution': True})
    save(path, ledger)
    return len(ledger)

def ledger_count(folder):
    return len(load(folder/'attempt-ledger.json')) if (folder/'attempt-ledger.json').exists() else 0

def control_save(folder, control):
    control['history_sha256'] = canonical(control['history'])
    control['decisions_sha256'] = canonical(control['decisions'])
    save(folder/'control.json', control)

def run(repo, out, parent, backend, grid, plan, stop, phase):
    spec, p, policy = plan['q21'], plan['registered_gates'], plan['adaptive_policy']
    folder = out/'q21/exact'
    folder.mkdir(parents=True, exist_ok=True)
    origin = spec['source_iteration']
    ceiling = spec['maximum_additional_attempts']
    identity = {'run_identity': load(out/'identity.json'), 'arm': 'exact-final-tranche', 'parent_sha256': spec['source_field']['sha256'],
                'source_iteration': origin, 'backend': backend['selected_backend'], 'grid': list(grid.shape), 'lengths': list(grid.lengths), 'maximum_new_attempts': ceiling}
    if (folder/'DONE.json').exists():
        receipt = load(folder/'DONE.json')
        need(receipt['identity'] == canonical(identity) and sha(folder/'record.json') == receipt['record_sha256'] and sha(folder/'endpoint.npz') == receipt['endpoint_sha256'], 'Completed final-tranche record differs')
        return load(folder/'record.json')
    engine = Engine(backend['selected_backend'])
    if engine.kind == 'cuda':
        need(engine.port.identity() == backend['cuda_identity'], 'CUDA runtime/device changed; no mid-tranche backend substitution')
    if (folder/'control.json').exists():
        control = load(folder/'control.json')
        need(control['identity'] == canonical(identity) and control['history_sha256'] == canonical(control['history']) and control['decisions_sha256'] == canonical(control['decisions']), 'Committed tranche metadata differs')
        state = restore(folder/control['checkpoint'], engine, identity)
        need(control['history'][-1]['iteration'] == state['iteration'], 'Restored state/history iteration differs')
        need(ledger_count(folder) >= control['committed_attempts'] >= state['iteration']-origin, 'Committed budget/checkpoint differs')
        replay = metrics(engine.host(state['n']), grid, p)
        for key in ['energy', 'relative_force_l2', 'acceleration_max', 'tail_fraction', 'guard_fraction']:
            need(np.isclose(replay[key], control['history'][-1]['metrics'][key], rtol=1e-6, atol=1e-10), 'Resumed metric replay differs: ' + key)
    else:
        state = {k: v.copy() if isinstance(v, np.ndarray) else v for k, v in parent.items()}
        before = state_digest(parent)
        need(state_digest(state) == before, 'Exact migration altered optimizer arrays or scalar memory')
        m = metrics(state['n'], grid, p)
        for key in ['energy', 'relative_force_l2', 'acceleration_max', 'acceleration_rms', 'tail_fraction', 'guard_fraction']:
            need(np.isclose(m[key], spec['expected_metrics'][key], rtol=1e-6, atol=1e-10), 'Exact-315 source metric replay differs: ' + key)
        need(np.max(np.abs(state['n'][grid.fixed_mask()]-[0., 0., 1.])) < 1e-12 and gate_result(m, 21, p)['representation'], 'Source representation/held layers differ; no projection allowed')
        history = copy.deepcopy(baseline()[0]['q21/exact/record.json']['history'])
        need(history[-1]['iteration'] == origin, 'Wrong prior-state selection; only exact iteration 315 is allowed')
        save(folder/'PARENT-REPLAY.json', {'recorded_at': stamp(), 'source_sha256': spec['source_field']['sha256'], 'before': before, 'after': state_digest(state), 'memory_and_alpha_preserved': True, 'cpu_metrics': m, 'source_modified': False})
        save(folder/'PARENT-HISTORY.json', history)
        for key in ['n', 'old_g', 'old_z', 'direction']:
            state[key] = engine.xp.asarray(state[key]).copy()
        relative = 'states/initial-i%05d.npz' % origin
        checkpoint(folder/relative, state, engine, identity)
        control = {'identity': canonical(identity), 'checkpoint': relative, 'history': history, 'decisions': [], 'committed_attempts': 0, 'pending_block': None}
        control_save(folder, control)
    reason = None
    while reason is None:
        charged = ledger_count(folder)
        latest = control['history'][-1]
        classification = gate_result(latest['metrics'], 21, p)
        if not classification['representation']:
            reason = 'representation_gate_failed'; break
        if classification['strict_stationary']:
            reason = 'strict_stationarity_measured_boundary_reported_separately'; break
        if (folder/'LINE-SEARCH-STOP.json').exists():
            reason = 'line_search_stalled'; break
        if charged >= ceiling:
            reason = 'declared_final_tranche_budget_reached'; break
        if stop() or (out/'STOP.json').exists():
            raise KeyboardInterrupt('Orderly pause before next Q21 attempt; memory and charged budget preserved')
        pending = control['pending_block']
        if pending is not None and charged >= pending['attempt_limit']:
            accepted_in_block = state['iteration']-pending['authorized_at_iteration']
            if accepted_in_block < policy['minimum_new_accepted_points_between_decisions']:
                reason = 'insufficient_new_committed_observations_after_interrupted_probe'; break
            control['pending_block'] = None
            control_save(folder, control)
            pending = None
        if pending is None:
            decision = decide(control['history'], charged, policy, p, ceiling)
            need(not control['decisions'] or control['decisions'][-1]['iteration'] != decision['iteration'], 'Refusing repeated decision vote at the same observation')
            control['decisions'].append(decision)
            if decision['action'] == 'stop':
                reason = decision['reason']
                control_save(folder, control)
                break
            pending = {'authorized_at_iteration': state['iteration'], 'authorized_charged_attempts': charged, 'attempt_limit': charged+decision['next_attempts'], 'requested_attempts': decision['next_attempts']}
            need(pending['attempt_limit'] <= ceiling, 'Planner exceeded final tranche ceiling')
            control['pending_block'] = pending
            control_save(folder, control)
            log('Q21 adaptive block authorized', iteration=int(state['iteration']), charged=charged, attempts=decision['next_attempts'], reason=decision['reason'])
        check_reserve(out)
        attempt = charge(folder, control['committed_attempts'], ceiling)
        phase.update(name='q21-final-adaptive-tranche', iteration=int(state['iteration']), charged_attempts=attempt, block_attempt_limit=pending['attempt_limit'])
        save(out/'status.json', {'recorded_at': stamp(), 'status': 'working', 'phase': dict(phase), 'new_q21_attempts_charged': attempt, 'maximum_new_q21_attempts': ceiling, 'physical_time_steps': 0, 'error': None})
        accepted, step = engine.step(state, grid)
        if not accepted:
            save(folder/'LINE-SEARCH-STOP.json', {'recorded_at': stamp(), 'attempt': attempt, **step})
            reason = 'line_search_stalled'; break
        engine.sync()
        audit = engine.audit(state['n'], grid)
        measured = metrics(engine.host(state['n']), grid, p)
        row = {'recorded_at': stamp(), 'iteration': int(state['iteration']), 'new_attempt': attempt, 'alpha': float(state['alpha']), 'objective_calls': step['objective_calls'],
               'metrics': measured, 'gates': gate_result(measured, 21, p), 'step': step, 'backend_audit': audit, 'scope': 'New final-tranche observation; previous history is retained separately'}
        # Every accepted state is an immutable full optimizer checkpoint. An
        # interrupted write is never mistaken for the committed pointer.
        relative = 'states/a%05d-i%05d.npz' % (attempt, state['iteration'])
        need(not (folder/relative).exists(), 'Refusing overwrite of an existing accepted-state checkpoint')
        checkpoint(folder/relative, state, engine, identity)
        control['history'].append(row)
        control.update(checkpoint=relative, committed_attempts=attempt)
        control_save(folder, control)
        phase.update(iteration=int(state['iteration']), relative_force_l2=measured['relative_force_l2'], acceleration_max=measured['acceleration_max'])
        log('Q21 final-tranche observation', iteration=int(state['iteration']), new_attempt=attempt, force=measured['relative_force_l2'], acceleration=measured['acceleration_max'], gates=row['gates'])
    endpoint = folder/'endpoint.npz'
    checkpoint(endpoint, state, engine, identity)
    new_rows = [row for row in control['history'] if row['iteration'] > origin]
    result = {'recorded_at': stamp(), 'status': 'measured_pending_review', 'reason': reason, 'identity': canonical(identity), 'source_iteration': origin,
              'final_iteration': int(state['iteration']), 'new_attempts_charged': ledger_count(folder), 'accepted_new_steps': int(state['iteration'])-origin,
              'maximum_new_attempts': ceiling, 'history': control['history'], 'new_history': new_rows, 'final': control['history'][-1], 'decisions': control['decisions'],
              'committed_objective_calls_new_steps': sum(row['objective_calls'] for row in new_rows), 'objective_call_scope': 'Interrupted/uncommitted calls may be unknown; their optimizer attempts remain charged',
              'optimizer_memory_retained': True, 'grid_unchanged': True, 'box_unchanged': True, 'gates_unchanged': True, 'physical_time_steps': 0,
              'followup': 'No automatic further same-grid tranche. Assess joint progress and Q22 recovery before any separate mesh/preparation decision.'}
    save(folder/'record.json', result)
    save(folder/'DONE.json', {'recorded_at': stamp(), 'identity': canonical(identity), 'record_sha256': sha(folder/'record.json'), 'endpoint_sha256': sha(endpoint)})
    del state, engine
    gc.collect()
    return result
