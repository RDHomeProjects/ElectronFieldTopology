"""Read-only compact-evidence checks, policy replay and terminal curve refits."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
from zoneinfo import ZoneInfo
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = 'cc17e740f2217cb072420c715d22a11cf1cf15b1d81e9c585251a89869edd643'

def stamp():
    t = datetime.now(timezone.utc)
    return {'utc': t.isoformat(), 'melbourne': t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())

def checked(z, manifest='SHA256SUMS', prefix=''):
    assert len(z.namelist()) == len(set(z.namelist())) and z.testzip() is None
    hashes = {}
    for line in z.read(prefix + manifest).decode().splitlines():
        digest, name = line.split('  ', 1)
        p = PurePosixPath(name)
        assert not p.is_absolute() and '..' not in p.parts and name not in hashes
        assert sha(z.read(prefix + name)) == digest, name
        hashes[name] = digest
    assert {prefix + n for n in hashes} == set(z.namelist()) - {prefix + manifest}
    return hashes

def run():
    path = ROOT / 'data/completed-evidence.zip'
    assert sha(path.read_bytes()) == SOURCE_SHA
    summaries, replay, refits = [], [], []
    max_error_difference = 0.
    with zipfile.ZipFile(path) as z:
        hashes = checked(z)
        record = json.loads(z.read('record.json'))
        p = record['plan']
        fields = json.loads(z.read('field-manifest.json'))['fields']
        byfield = {r['path']: r for r in fields}
        selection = json.loads(z.read('handover/SELECTION.json'))['branches']
        missing = []
        with zipfile.ZipFile(ROOT / 'data/delivered-handover.zip') as delivered:
            prefix = 'ElectronFieldTopology-policy-v2-continuation-20261120/'
            delivered_hashes = checked(delivered, prefix=prefix)
            assert sha(delivered.read(prefix + 'SHA256SUMS')) == record['identity']['package_sha256']
            for name, digest in delivered_hashes.items():
                target = 'handover/' + name
                if target in z.namelist():
                    assert sha(z.read(target)) == digest
                else:
                    missing.append(name)
        nested = z.read('handover/assessment/data/source-evidence.zip')
        assert sha(nested) == record['identity']['audit_archive_sha256']
        with zipfile.ZipFile(io.BytesIO(nested)) as original:
            old_hashes = checked(original)
            old_identity = json.loads(original.read('identity.json'))
            assert canonical(old_identity) == record['identity']['original_source_identity']
            for name, digest in old_identity['complete_numerical_source_sha256'].items():
                assert sha(original.read('numerical-source/' + name)) == digest
            with tempfile.TemporaryDirectory() as td:
                module_path = Path(td) / 'fits.py'
                module_path.write_bytes(z.read('handover/science/fits.py'))
                spec = importlib.util.spec_from_file_location('delivered_policy_v2', module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for result in record['branches']:
                    seed = result['seed']['id']
                    folder = 'continuation/' + seed + '/'
                    get = lambda name: json.loads(z.read(folder + name))
                    migration, history, decisions = get('MIGRATION.json'), get('history.json'), get('decisions.json')
                    old_history = json.loads(original.read('broad/' + seed + '/optimizer/history.json'))
                    assert history[:len(old_history)] == old_history
                    pointer = get('latest.json')
                    assert pointer['history_sha256'] == canonical(history)
                    assert get('state-' + str(pointer['slot']) + '.seal.json')['sha256'] == byfield[folder + 'state-' + str(pointer['slot']) + '.npz']['sha256']
                    assert get('result.seal.json')['sha256'] == sha(z.read(folder + 'result.json'))
                    assert result['checkpoint_sha256'] == byfield[folder + 'endpoint.npz']['sha256']
                    assert migration['source_sha256'] == byfield[folder + 'parent-state.npz']['sha256']
                    s = next(s for s in selection if s['id'] == seed)
                    count, epoch = s['prior_plateau_count'], s['prior_plateau_epoch']
                    for saved in decisions:
                        prefix_history = [h for h in history if h['iteration'] <= saved['iteration']]
                        fit_function = module.models
                        try:
                            module.models = lambda rows, key, plan: saved['models'][key]
                            choice = module.decide(prefix_history, p, saved['remaining_attempts'], count, plateau_epoch=epoch)
                        finally:
                            module.models = fit_function
                        assert all(saved[k] == value for k, value in choice.items()), (seed, saved['iteration'])
                        assert saved['remaining_attempts'] == 500 - prefix_history[-1]['attempts']
                        count, epoch = choice.get('plateau_count', 0), choice['plateau_epoch']
                        replay.append({'seed': seed, **saved})
                    terminal = decisions[-1]
                    rows = [h for h in history if h['iteration'] >= terminal['fit_epoch_start']][-p['fit_window']:]
                    for key in ['relative_force_l2', 'acceleration_max', 'energy']:
                        fit = module.models(rows, key, p)
                        old = terminal['models'][key]
                        assert [m['model'] for m in fit['accepted']] == [m['model'] for m in old['accepted']]
                        for first, second in zip(fit['accepted'], old['accepted']):
                            max_error_difference = max(max_error_difference, abs(first['held_out_relative_error'] - second['held_out_relative_error']))
                        refits.append({'seed': seed, 'metric': key, 'window_iterations': [r['iteration'] for r in rows], 'refit': fit, 'accepted_model_order_matches': True})
                    assert terminal['plateau_count'] == 3 and terminal['progress_evidence_sufficient'] and terminal['action'] == 'stop'
                    initial, last = migration['original_metrics'], history[-1]
                    new = history[len(old_history):]
                    assert all(h['backend_audit']['passed'] for h in new)
                    assert all(b['energy'] <= a['energy'] + 1e-11 for a, b in zip(history, history[1:]))
                    assert all(abs(abs(h['hopf_integral']) - result['q']) / result['q'] <= p['charge_relative_error'] and h['unit_error'] < p['unit_limit'] and h['minimum_corner_cone'] > 0 for h in new)
                    best = min([h for h in history if h['iteration'] >= initial['iteration']], key=lambda h: max(h['relative_force_l2'] / p['force_limit'], h['acceleration_max'] / p['acceleration_limit']))
                    summaries.append({'seed': seed, 'q': result['q'], 'nodes': result['nodes'], 'initial_iteration': initial['iteration'], 'final_iteration': last['iteration'],
                                      'additional_attempts': result['additional_attempts'], 'unused_to_500': 500 - result['attempts'],
                                      'initial': initial, 'final': last,
                                      'gate_multiples': {key: last[key] / p[gate] for key, gate in [('relative_force_l2', 'force_limit'), ('acceleration_max', 'acceleration_limit'), ('tail_fraction', 'initial_tail_limit'), ('guard_fraction', 'tail_guard_limit')]},
                                      'change_percent': {key: 100 * (last[key] / initial[key] - 1) for key in ['relative_force_l2', 'acceleration_max', 'energy', 'tail_fraction']},
                                      'best_observed_iteration': best['iteration'], 'best_observed_joint_gate_multiple': max(best['relative_force_l2'] / p['force_limit'], best['acceleration_max'] / p['acceleration_limit']),
                                      'stop_reason': terminal['reason'], 'stop_distinct_observations': terminal['distinct_epoch_observations'],
                                      'terminal_force_fit_validated': bool(terminal['models']['relative_force_l2']['accepted']),
                                      'new_observations': len(new)})
        assert record['additional_attempts'] == sum(s['additional_attempts'] for s in summaries) == 225
        assert record['campaign_total_attempts_including_original'] == 5950
        next_stage = json.loads(z.read('NEXT-STAGE.json'))
        assert len(next_stage['all_34_dispositions']) == 34 and not next_stage['stationary_parent_ids_for_review']
    return {'recorded_at': stamp(), 'source_sha256': SOURCE_SHA, 'compact_payloads_verified': len(hashes), 'zip_crc_pass': True,
            'full_fields_declared': len(fields), 'full_field_contents_verified_here': False,
            'delivered_package_payloads_verified': len(delivered_hashes), 'delivered_package_members_omitted_from_result_zip': missing,
            'nested_original_payloads_verified': len(old_hashes), 'numerical_source_copies_verified': len(old_identity['complete_numerical_source_sha256']),
            'decisions_replayed': len(replay), 'terminal_metric_windows_refitted': len(refits), 'accepted_model_order_matches': True,
            'maximum_refit_heldout_error_difference': max_error_difference, 'terminal_branches': 6, 'stationary_passes': 0, 'boundary_passes': 0,
            'additional_attempts': 225, 'additional_unused': 1513, 'campaign_total_attempts': 5950, 'new_solver_steps_here': 0,
            'summaries': summaries, 'replay': replay, 'refits': refits}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in ['recorded_at', 'compact_payloads_verified', 'decisions_replayed', 'terminal_metric_windows_refitted', 'stationary_passes', 'boundary_passes', 'additional_attempts', 'new_solver_steps_here']}))
