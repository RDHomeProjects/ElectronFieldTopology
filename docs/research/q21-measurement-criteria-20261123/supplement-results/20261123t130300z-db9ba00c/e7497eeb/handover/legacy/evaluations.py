"""Measured operator checks and a memory-only paired experiment."""
import gc
import hashlib
import numpy as np
from common import need, stamp

def array_sha(a):
    return hashlib.sha256(memoryview(np.ascontiguousarray(a)).cast('B')).hexdigest()

def state_digest(s):
    return {key: array_sha(s[key]) if s[key] is not None else None for key in ['n', 'old_g', 'old_z', 'direction']} | {'alpha': float(s['alpha']), 'iteration': int(s['iteration'])}

def split_state(s, reset=False):
    result = {k: v.copy() if isinstance(v, np.ndarray) else v for k, v in s.items()}
    if reset:
        for key in ['old_g', 'old_z', 'direction']:
            result[key] = None
    return result

def gate_result(m, q, p):
    finite = all(np.isfinite(m[k]) for k in ['relative_force_l2', 'acceleration_max', 'hopf_integral', 'minimum_corner_cone', 'unit_error', 'tail_fraction', 'guard_fraction'])
    representation = bool(finite and abs(abs(m['hopf_integral']) - q) / q <= p['charge_relative_error'] and m['minimum_corner_cone'] > 0 and m['unit_error'] < p['unit_limit'])
    stationary = bool(representation and m['relative_force_l2'] <= p['force_limit'] and m['acceleration_max'] <= p['acceleration_limit'])
    boundary = bool(finite and m['tail_fraction'] <= p['initial_tail_limit'] and m['guard_fraction'] <= p['tail_guard_limit'])
    return {'representation': representation, 'strict_stationary': stationary, 'boundary_admitted': boundary, 'all_readiness_gates': stationary and boundary}

def metrics(n, grid, p):
    from electron_field_topology.sf_readmission import stationarity
    from electron_field_topology.sf_time import densities
    m = stationarity(n, grid)
    density = densities(n, np.zeros_like(n), grid)['energy_density']
    axes = [-length / 2 + np.arange(count) * spacing for count, length, spacing in zip(grid.shape, grid.lengths, grid.spacing)]
    distance = np.minimum.reduce(np.broadcast_arrays(*[(grid.lengths[i] / 2 - np.abs(axis)).reshape(tuple(len(axis) if j == i else 1 for j in range(3))) for i, axis in enumerate(axes)]))
    for key, width in [('tail_fraction', p['shell_width']), ('guard_fraction', p['guard_width'])]:
        m[key] = float(np.sum(density[distance <= width]) / np.sum(density))
    return m

def derivative_check(n, grid, settings):
    from electron_field_topology.sf_readmission import static_value_gradient
    before = array_sha(n)
    value, raw = static_value_gradient(n, grid)
    projected = raw - n * np.sum(n * raw, axis=-1, keepdims=True)
    projected[grid.fixed_mask()] = 0
    axes = [-length / 2 + np.arange(count) * spacing for count, length, spacing in zip(grid.shape, grid.lengths, grid.spacing)]
    x, y, z = np.meshgrid(*axes, indexing='ij', sparse=True)
    direction = np.empty_like(n)
    direction[..., 0] = np.sin(.7 * x + .4 * y) * np.cos(.3 * z)
    direction[..., 1] = np.cos(.5 * y - .2 * z) * np.sin(.6 * x)
    direction[..., 2] = np.sin(.4 * z + .3 * x) * np.cos(.2 * y)
    direction *= np.exp(-(x*x + y*y + z*z) / 25)[..., None]
    direction -= n * np.sum(n * direction, axis=-1, keepdims=True)
    direction[grid.fixed_mask()] = 0
    rows = []
    for name, vector in [('negative_projected_gradient', -projected), ('deterministic_smooth_tangent', direction)]:
        vector = vector / max(float(np.max(np.linalg.norm(vector, axis=-1))), 1e-30)
        predicted = float(np.sum(raw * vector))
        differences = []
        for epsilon in settings['epsilons']:
            values = []
            for sign in [-1, 1]:
                trial = n + sign * epsilon * vector
                trial /= np.linalg.norm(trial, axis=-1, keepdims=True)
                trial[grid.fixed_mask()] = n[grid.fixed_mask()]
                values.append(static_value_gradient(trial, grid)[0])
            measured = (values[1] - values[0]) / (2 * epsilon)
            tolerance = settings['atol'] + settings['rtol'] * abs(predicted)
            differences.append({'epsilon': epsilon, 'predicted': predicted, 'centered_difference': measured, 'absolute_error': abs(measured - predicted), 'tolerance': tolerance, 'passed': bool(abs(measured - predicted) <= tolerance)})
        rows.append({'direction': name, 'differences': differences, 'passed': all(r['passed'] for r in differences[-2:])})
    need(array_sha(n) == before, 'Directional derivative check mutated source field')
    return {'recorded_at': stamp(), 'passed': all(r['passed'] for r in rows), 'energy': value, 'rows': rows, 'energy_gradient_calls': 13,
            'optimizer_attempts': 0, 'physical_time_steps': 0, 'scope': 'Centered constrained retractions on the exact Q21 endpoint; no accepted optimization updates'}

def fit_history(rows, key):
    """Chronological holdout; descriptive only, never a budget extension rule."""
    if len(rows) < 8:
        return {'status': 'insufficient_distinct_observations', 'count': len(rows)}
    x = np.array([r['iteration'] - rows[0]['iteration'] for r in rows], dtype=float)
    y = np.array([r['metrics'][key] for r in rows])
    candidates = []
    for kind, degree in [('linear', 1), ('quadratic', 2), ('exponential', 1)]:
        if kind == 'exponential' and np.any(y <= 0):
            continue
        target = np.log(y) if kind == 'exponential' else y
        c = np.polyfit(x[:-3], target[:-3], degree)
        predicted = np.polyval(c, x[-3:])
        if kind == 'exponential':
            predicted = np.exp(np.clip(predicted, -700, 700))
        error = float(np.sqrt(np.mean((predicted - y[-3:])**2)) / max(float(np.mean(abs(y[-3:]))), 1e-30))
        final = np.polyfit(x, target, degree)
        candidates.append({'model': kind, 'coefficients_highest_power_first': final.tolist(), 'holdout_relative_rmse': error, 'holdout_points': 3})
    return {'status': 'descriptive_fit_complete', 'x_origin_iteration': rows[0]['iteration'], 'models': candidates, 'admission_inferred': False, 'budget_extension': False}

def paired_summary(arms):
    histories = {name: record['history'] for name, record in arms.items()}
    common = sorted(set(r['iteration'] for r in histories['exact']) & set(r['iteration'] for r in histories['memory-reset']))
    paired = []
    for iteration in common:
        rows = {name: next(r for r in rows if r['iteration'] == iteration) for name, rows in histories.items()}
        paired.append({'iteration': iteration, 'exact': rows['exact']['metrics'], 'memory_reset': rows['memory-reset']['metrics'],
                       'joint_reset_better': rows['memory-reset']['metrics']['relative_force_l2'] < rows['exact']['metrics']['relative_force_l2'] and rows['memory-reset']['metrics']['acceleration_max'] < rows['exact']['metrics']['acceleration_max']})
    return {'recorded_at': stamp(), 'matched_iterations': common, 'paired': paired,
            'last_matched_joint_reset_improvement': paired[-1]['joint_reset_better'] if len(paired) > 1 else None,
            'scope': 'Matched measured iterations, including failures; energy descent alone is not joint stationarity'}

def q22_compare(path, spec, p, folder):
    from electron_field_topology.sf_time import Grid
    from electron_field_topology.skyrme import Energy, K
    with np.load(path, allow_pickle=False) as z:
        field = z['field'].copy()
        need(field.shape == (spec['nodes'],) * 3 + (3,) and field.dtype in [np.dtype('float32'), np.dtype('float64')] and np.isfinite(field).all(), 'Native historical Q22 shape/precision differs')
        need('h' in z and np.isclose(float(z['h']), spec['spacing'], rtol=0, atol=1e-14), 'Native historical Q22 spacing differs')
    original_dtype, source_array = str(field.dtype), array_sha(field)
    n = field.astype(np.float64)
    need(np.array_equal(n.astype(field.dtype), field), 'Promotion changed stored field values')
    del field
    before = array_sha(n)
    grid = Grid((spec['nodes'],) * 3, (spec['length'],) * 3, 'fixed')
    engine = Energy(spec['nodes'], spec['spacing'], folder / 'native-cell-build', 'cell')
    parts, gradient = engine.evaluate(n)
    tangent = gradient - n * np.sum(n * gradient, axis=-1, keepdims=True)
    residual = float(np.sqrt(np.mean(tangent[2:-2, 2:-2, 2:-2]**2)) / (K * spec['spacing']**3))
    cell = {'energy': float(sum(parts)), 'e2': float(parts[0]), 'e4': float(parts[1]), 'tangent_gradient_rms': residual,
            'cell_residual_threshold': .001, 'cell_residual_below_threshold': residual < .001,
            'minimum_corner_cone': engine.minimum_corner_cone, 'minimum_interpolant_norm': engine.minimum_interpolant_norm,
            'historical_reported_energy': spec['energy'], 'historical_reported_cpu_residual': spec['cpu_residual'],
            'energy_relative_difference_from_historical': abs(float(sum(parts)) - spec['energy']) / spec['energy'],
            'residual_relative_difference_from_historical': abs(residual - spec['cpu_residual']) / spec['cpu_residual']}
    del engine, gradient, tangent
    gc.collect()
    d4 = metrics(n, grid, p)
    need(array_sha(n) == before, 'Native operator comparison mutated field')
    return {'recorded_at': stamp(), 'status': 'evaluated_pending_review', 'source_path': str(path), 'source_sha256': spec['sha256'],
            'source_dtype': original_dtype, 'source_array_sha256': source_array, 'promoted_array_sha256_before': before, 'promoted_array_sha256_after': array_sha(n),
            'values_preserved_by_promotion': True, 'normalized': False, 'resampled': False, 'nodes': spec['nodes'], 'spacing': spec['spacing'], 'length': spec['length'],
            'cell': cell, 'd4': d4, 'd4_gates': gate_result(d4, 22, p), 'optimizer_steps': 0, 'physical_time_steps': 0,
            'scope': 'Same stored native field evaluated under cell and D4. Archived float32 quantization, when present, remains; promotion does not restore the original solver precision. Historical success is not revoked by an archival replay discrepancy.'}
