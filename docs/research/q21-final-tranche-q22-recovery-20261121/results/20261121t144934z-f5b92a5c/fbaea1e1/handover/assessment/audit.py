"""Independent compact audit; no field evaluation or optimizer execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import zipfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = 'b674cee9dca4af58fa4bf1e949aaf76db815fe14fdb43b4b51fbc43b8e2c42b9'

def stamp():
    now = datetime.now(timezone.utc)
    return {'utc': now.isoformat(), 'melbourne': now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())

def checked(z):
    names = z.namelist()
    assert len(names) == len(set(names)) and z.testzip() is None
    result = {}
    for row in z.read('SHA256SUMS').decode().splitlines():
        sha, name = row.split('  ', 1)
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and name not in result
        assert digest(z.read(name)) == sha, name
        result[name] = sha
    assert set(result) == set(names) - {'SHA256SUMS'}
    return result

def close(a, b):
    return math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-12)

def solve(matrix, rhs):
    rows = [list(row) + [value] for row, value in zip(matrix, rhs)]
    for i in range(len(rows)):
        pivot = max(range(i, len(rows)), key=lambda j: abs(rows[j][i]))
        rows[i], rows[pivot] = rows[pivot], rows[i]
        scale = rows[i][i]
        rows[i] = [v / scale for v in rows[i]]
        for j in range(len(rows)):
            if j != i:
                factor = rows[j][i]
                rows[j] = [v - factor * u for v, u in zip(rows[j], rows[i])]
    return [row[-1] for row in rows]

def fit(xs, ys, degree):
    matrix = [[sum(x**(i+j) for x in xs) for j in range(degree+1)] for i in range(degree+1)]
    rhs = [sum(y*x**i for x, y in zip(xs, ys)) for i in range(degree+1)]
    return solve(matrix, rhs)[::-1]

def polynomial(coeff, x):
    value = 0.
    for c in coeff:
        value = value * x + c
    return value

def gates(m, q, p):
    finite = all(math.isfinite(m[k]) for k in ['relative_force_l2', 'acceleration_max', 'hopf_integral', 'minimum_corner_cone', 'unit_error', 'tail_fraction', 'guard_fraction'])
    representation = finite and abs(abs(m['hopf_integral'])-q)/q <= p['charge_relative_error'] and m['minimum_corner_cone'] > 0 and m['unit_error'] < p['unit_limit']
    strict = representation and m['relative_force_l2'] <= p['force_limit'] and m['acceleration_max'] <= p['acceleration_limit']
    boundary = finite and m['tail_fraction'] <= p['initial_tail_limit'] and m['guard_fraction'] <= p['tail_guard_limit']
    return {'representation': representation, 'strict_stationary': strict, 'boundary_admitted': boundary, 'all_readiness_gates': strict and boundary}

def future_crossings(model, gate, origin, current):
    c = model['coefficients_highest_power_first'][:]
    c[-1] -= math.log(gate) if model['model'] == 'exponential' else gate
    if len(c) == 2:
        roots = [-c[1] / c[0]] if c[0] else []
    else:
        discriminant = c[1]**2 - 4*c[0]*c[2]
        roots = [(-c[1]+sign*math.sqrt(discriminant))/(2*c[0]) for sign in [-1, 1]] if discriminant >= 0 and c[0] else []
    return [origin + root for root in roots if root + origin > current]

def run(source):
    assert digest(source.read_bytes()) == SOURCE_SHA
    with zipfile.ZipFile(source) as z:
        hashes = checked(z)
        read = lambda name: json.loads(z.read(name))
        record, identity, plan = read('record.json'), read('identity.json'), read('handover/PLAN.json')
        assert record['status'] == 'complete_pending_review' and record['error'] is None
        assert record['identity'] == identity
        assert digest(z.read('handover/SHA256SUMS')) == identity['package_sha256']
        assert hashes['handover/PLAN.json'] == identity['plan_sha256']
        frozen = {}
        for row in z.read('handover/SHA256SUMS').decode().splitlines():
            sha, name = row.split('  ', 1)
            assert digest(z.read('handover/' + name)) == sha, name
            frozen[name] = sha
        assert len(frozen) == 42
        assert canonical(read('handover/SOURCES.json')) == identity['source_identity']
        with zipfile.ZipFile(io.BytesIO(z.read('handover/assessment/data/diagnostic-evidence.zip'))) as previous:
            prior_hashes = checked(previous)
            prior = json.loads(previous.read('cases/q21-axial-7-3-endpoint/record.json'))
        p = plan['registered_gates']
        assert record['q2']['gates'] == gates(record['q2']['metrics'], 2, p)
        assert record['q2']['gates']['all_readiness_gates']
        backend = read('BACKEND.json')
        assert backend['selected_backend'] == backend['source_backend'] == 'cuda' and not backend['backend_transfer']
        assert backend['same_backend_for_both_arms'] and backend['initial_energy_gradient_audit']['passed']
        derivative = read('DIRECTIONAL-DERIVATIVES.json')
        assert read('DERIVATIVE-SEAL.json')['sha256'] == hashes['DIRECTIONAL-DERIVATIVES.json']
        assert derivative['passed'] and derivative['optimizer_attempts'] == derivative['physical_time_steps'] == 0
        for direction in derivative['rows']:
            for item in direction['differences']:
                assert close(item['absolute_error'], abs(item['centered_difference'] - item['predicted']))
                assert close(item['tolerance'], plan['directional_derivatives']['atol'] + plan['directional_derivatives']['rtol'] * abs(item['predicted']))
                assert item['passed'] == (item['absolute_error'] <= item['tolerance'])
            assert direction['passed'] == all(row['passed'] for row in direction['differences'][-2:])
        inventory = {row['path']: row for row in read('FIELD-MANIFEST.json')['fields']}
        assert len(inventory) == 6
        stats, fit_checks, arms = [], [], {}
        total_attempts = 0
        for name in ['exact', 'memory-reset']:
            prefix = 'q21/' + name + '/'
            arm = read(prefix + 'record.json')
            assert arm == record['arms'][name]
            done = read(prefix + 'DONE.json')
            assert done['record_sha256'] == hashes[prefix + 'record.json'] and done['identity'] == arm['identity']
            assert done['endpoint_sha256'] == inventory[prefix + 'endpoint.npz']['sha256']
            for label in ['endpoint', 'state-0', 'state-1']:
                seal = read(prefix + label + '.seal.json')
                assert seal['sha256'] == inventory[prefix + label + '.npz']['sha256'] and seal['identity_sha256'] == arm['identity']
            intervention = read(prefix + 'INTERVENTION.json')
            before, after = intervention['before'], intervention['after']
            assert before['n'] == prior['field_array_sha256_after']
            assert before['n'] == after['n'] and before['alpha'] == after['alpha'] and before['iteration'] == after['iteration'] == 295
            if name == 'exact':
                assert before == after
            else:
                assert all(after[k] is None and before[k] is not None for k in ['old_g', 'old_z', 'direction'])
            ledger, control = read(prefix + 'attempt-ledger.json'), read(prefix + 'control.json')
            assert len(ledger) == arm['attempts_charged'] == arm['accepted_steps'] == 20
            assert all(row['attempt'] == i+1 and row['charged_before_execution'] and not row.get('interrupted_or_uncommitted') for i, row in enumerate(ledger))
            h = arm['history']
            assert len(h) == 21 and [row['iteration'] for row in h] == list(range(295, 316))
            assert control['history'] == h and control['history_sha256'] == canonical(h) and control['committed_attempts'] == 20
            assert arm['final'] == h[-1]
            assert sum(row['objective_calls'] for row in h) == arm['objective_calls_committed'] == 54
            for index, row in enumerate(h):
                assert row['gates'] == gates(row['metrics'], 21, p)
                assert row['gates']['representation'] and not row['gates']['strict_stationary'] and not row['gates']['boundary_admitted']
                if index:
                    assert row['backend_audit']['passed'] and row['metrics']['energy'] <= h[index-1]['metrics']['energy']
            initial, final = h[0]['metrics'], h[-1]['metrics']
            assert all(close(initial[key], prior['reference_metrics'][key]) for key in ['energy', 'relative_force_l2', 'acceleration_max', 'tail_fraction', 'guard_fraction'])
            changes = {key: 100 * (final[key]/initial[key]-1) for key in ['energy', 'relative_force_l2', 'acceleration_max', 'tail_fraction', 'guard_fraction']}
            joint = lambda row: max(row['metrics']['relative_force_l2']/p['force_limit'], row['metrics']['acceleration_max']/p['acceleration_limit'])
            best = min(h, key=joint)
            stats.append({'arm': name, 'initial': initial, 'final': final, 'changes_percent': changes,
                          'best_joint_iteration': best['iteration'], 'best_joint_gate_multiple': joint(best),
                          'final_force_gate_multiple': final['relative_force_l2']/p['force_limit'], 'final_acceleration_gate_multiple': final['acceleration_max']/p['acceleration_limit'],
                          'final_tail_gate_multiple': final['tail_fraction']/p['initial_tail_limit'], 'final_guard_gate_multiple': final['guard_fraction']/p['tail_guard_limit']})
            for key, description in arm['fits'].items():
                xs = [row['iteration']-295 for row in h]
                values = [row['metrics'][key] for row in h]
                gate = p['force_limit'] if key == 'relative_force_l2' else p['acceleration_limit']
                for model in description['models']:
                    degree = 2 if model['model'] == 'quadratic' else 1
                    ys = list(map(math.log, values)) if model['model'] == 'exponential' else values
                    coefficients = fit(xs, ys, degree)
                    assert all(close(a, b) for a, b in zip(coefficients, model['coefficients_highest_power_first']))
                    training = fit(xs[:-3], ys[:-3], degree)
                    predictions = [polynomial(training, x) for x in xs[-3:]]
                    if model['model'] == 'exponential':
                        predictions = list(map(math.exp, predictions))
                    error = math.sqrt(sum((a-b)**2 for a, b in zip(predictions, values[-3:]))/3) / (sum(map(abs, values[-3:]))/3)
                    assert close(error, model['holdout_relative_rmse'])
                    fit_checks.append({'arm': name, 'quantity': key, 'model': model['model'], 'holdout_relative_rmse': error,
                                       'passes_original_holdout_limit': error <= p['validation_relative_limit'],
                                       'formal_future_gate_crossings': future_crossings(model, gate, 295, 315), 'forecast_is_admission': False})
            total_attempts += len(ledger)
            arms[name] = arm
        assert total_attempts == record['charged_q21_attempts'] == identity['maximum_q21_attempts'] == 40
        assert record['physical_time_steps'] == 0
        paired = read('PAIRED-COMPARISON.json')
        assert paired == record['comparison'] and paired['matched_iterations'] == list(range(295, 316))
        for index, row in enumerate(paired['paired']):
            exact, reset = arms['exact']['history'][index]['metrics'], arms['memory-reset']['history'][index]['metrics']
            assert row['exact'] == exact and row['memory_reset'] == reset
            assert row['joint_reset_better'] == (reset['relative_force_l2'] < exact['relative_force_l2'] and reset['acceleration_max'] < exact['acceleration_max'])
        q22 = read('Q22-INVENTORY.json')
        assert record['q22'] == q22 and q22['status'] == 'deferred_missing_exact_historical_field'
        assert len(q22['checked']) == 1 and q22['checked'][0]['status'] == 'absent'
        assert not any(name.startswith('q22/') for name in z.namelist())
        samples = [json.loads(line) for line in z.read('telemetry.jsonl').decode().splitlines()]
        telemetry = {'samples': len(samples), 'peak_cgroup_gib': max(s['cgroup']['memory.peak'] for s in samples)/2**30,
                     'minimum_available_host_gib': min(s['host']['available_gib'] for s in samples), 'oom_kill_events': max(s['cgroup']['memory.events']['oom_kill'] for s in samples),
                     'memory_high_events': max(s['cgroup']['memory.events']['high'] for s in samples), 'maximum_host_full_pressure_avg10': max(s['pressure']['full']['avg10'] for s in samples)}
        return {'recorded_at': stamp(), 'status': 'pass', 'source_sha256': SOURCE_SHA, 'run_id': identity['run_id'], 'crc_pass': True,
                'compact_payload_hashes_verified': len(hashes), 'frozen_handover_payloads_verified': len(frozen), 'prior_diagnosis_payloads_verified': len(prior_hashes),
                'control_and_gate_reconstruction': 'pass', 'source_intervention_identity': 'pass', 'budget_and_committed_history': 'pass',
                'measured_arm_observations': 42, 'charged_q21_attempts': total_attempts, 'q22_evaluation_performed': False,
                'new_field_evaluation_here': False, 'new_optimizer_attempts_here': 0, 'physical_time_steps': 0,
                'arm_summary': stats, 'fits_independently_refitted': fit_checks,
                'reset_jointly_better_paired_observations_excluding_start': sum(row['joint_reset_better'] for row in paired['paired'][1:]),
                'telemetry': telemetry, 'scope': 'Independent compact hash, identity, intervention, gate, ledger and fit audit; full NPZ arrays remain on the workstation and were not reread here.'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT/'data/completed-evidence.zip')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = run(args.source)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ['recorded_at', 'status', 'compact_payload_hashes_verified', 'frozen_handover_payloads_verified', 'measured_arm_observations', 'charged_q21_attempts', 'q22_evaluation_performed']}))

if __name__ == '__main__':
    main()
