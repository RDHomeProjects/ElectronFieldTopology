"""Bounded off-core magnetic tracing with explicit nodal and closure outcomes."""
import numpy as np
from scipy.integrate import solve_ivp
from .fields import hopfion
from .candidates import candidate, exponents


class _EvaluationBudget(RuntimeError):
    pass


def transport_velocity(points, time=0.):
    e, b = hopfion(points, time)
    return np.cross(e, b)/(.5*np.sum(e*e+b*b, axis=-1))[..., None]


def field_ratio(points, time, p, q):
    e0, b0 = hopfion(points, time)
    magnetic = candidate(points, time, p, q)[1]
    return np.linalg.norm(magnetic, axis=-1)/np.sqrt(np.sum(e0*e0+b0*b0, axis=-1))


def trace_line(field, seed, *, ratio=None, tolerance=1e-9, max_step=.15,
               max_arclength=40., samples=256, near_zero=1e-8, radius=12., max_evaluations=20000,
               section_normal=None):
    seed = np.asarray(seed, dtype=float)
    numbers = [tolerance, max_step, max_arclength, near_zero, radius]
    if (seed.shape != (3,) or not np.isfinite(seed).all() or not np.isfinite(numbers).all()
            or not 1e-12 <= tolerance <= 1e-6 or not 0 < max_step <= .2
            or not 1 <= max_arclength <= 80 or not 0 < near_zero < .01 or not 1 <= radius <= 24
            or isinstance(samples, bool) or not isinstance(samples, int) or not 32 <= samples <= 512
            or isinstance(max_evaluations, bool) or not isinstance(max_evaluations, int) or not 10 <= max_evaluations <= 30000):
        raise ValueError('invalid bounded off-core trace settings')
    normal = None if section_normal is None else np.array(section_normal, dtype=float, copy=True)
    if normal is not None:
        if normal.shape != (3,) or not np.isfinite(normal).all() or np.linalg.norm(normal) == 0:
            raise ValueError('finite nonzero section normal required')
        normal /= np.linalg.norm(normal)
    calls = 0; minimum_ratio = np.inf
    def magnitude(x):
        return float(ratio(x) if ratio is not None else np.linalg.norm(field(x)))
    def direction(x):
        v = np.asarray(field(x), dtype=float)
        if v.shape != (3,) or not np.isfinite(v).all() or not np.any(v):
            raise ValueError('zero or invalid field direction')
        scaled = v/np.max(abs(v)); return scaled/np.linalg.norm(scaled)
    value = magnitude(seed)
    meta = {'seed': seed.tolist(), 'closed': False, 'status': 'unresolved_budget', 'section_returns': [],
            'accepted_return': None, 'endpoint_correction': 0., 'function_evaluations': 0,
            'max_arclength': max_arclength, 'tolerance': tolerance, 'max_step': max_step,
            'near_zero_floor': near_zero, 'observation_radius': radius,
            'evaluated_arclength': 0.,
            'minimum_field_ratio': value if np.isfinite(value) else None}
    if not np.isfinite(value):
        meta['status'] = 'invalid_field'; return seed[None, :], meta
    if value < near_zero:
        meta['status'] = 'near_zero_guard'; return seed[None, :], meta
    if np.linalg.norm(seed) >= radius:
        meta['status'] = 'observation_radius'; return seed[None, :], meta
    try: initial = direction(seed)
    except ValueError:
        meta['status'] = 'invalid_field'; return seed[None, :], meta
    if normal is None: normal = initial.copy()
    if abs(np.dot(normal, initial)) < 1e-8:
        raise ValueError('section must be transverse at the seed')
    if np.dot(normal, initial) < 0: normal *= -1
    meta['section_normal'] = normal.tolist()
    def rhs(s, x):
        nonlocal calls, minimum_ratio
        calls += 1
        if calls > max_evaluations: raise _EvaluationBudget('evaluation budget exhausted')
        minimum_ratio = min(minimum_ratio, magnitude(x))
        return direction(x)
    def section(s, x): return float(np.dot(x-seed, normal))
    section.direction = 1
    def zero(s, x): return magnitude(x)-near_zero
    zero.terminal = True; zero.direction = -1
    def escape(s, x): return radius-np.linalg.norm(x)
    escape.terminal = True; escape.direction = -1
    try:
        first = solve_ivp(rhs, (0, .05), seed, method='DOP853', rtol=tolerance,
                          atol=tolerance*.1, max_step=min(max_step, .05), dense_output=True, events=[zero, escape])
        if not first.success:
            meta['status'] = 'solver_failure'; points = first.y.T
            meta['evaluated_arclength'] = float(first.t[-1])
        elif first.status == 1:
            meta['status'] = 'near_zero_guard' if len(first.t_events[0]) else 'observation_radius'
            points = first.y.T
            meta['evaluated_arclength'] = float(first.t[-1])
        else:
            rest = solve_ivp(rhs, (.05, max_arclength), first.y[:, -1], method='DOP853', rtol=tolerance,
                             atol=tolerance*.1, max_step=max_step, dense_output=True, events=[section, zero, escape])
            for length, x in zip(rest.t_events[0], rest.y_events[0]):
                row = {'arclength': float(length), 'closure_gap': float(np.linalg.norm(x-seed)),
                       'tangent_mismatch': float(np.linalg.norm(direction(x)-initial)), 'position': x.tolist()}
                meta['section_returns'].append(row)
                if length > .5 and row['closure_gap'] < 1e-6 and row['tangent_mismatch'] < 1e-6 and meta['accepted_return'] is None:
                    meta['accepted_return'] = row
            accepted = meta['accepted_return']
            meta['evaluated_arclength'] = float(rest.t[-1])
            meta['closed'] = bool(first.success and rest.success and accepted is not None)
            if meta['closed']: meta['status'] = 'closed_candidate'
            elif len(rest.t_events[1]): meta['status'] = 'near_zero_guard'
            elif len(rest.t_events[2]): meta['status'] = 'observation_radius'
            elif not first.success or not rest.success: meta['status'] = 'solver_failure'
            length = accepted['arclength'] if meta['closed'] else float(rest.t[-1])
            grid = np.linspace(0, length, samples+1); early = grid <= .05
            points = np.empty((samples+1, 3)); points[early] = first.sol(grid[early]).T
            points[~early] = rest.sol(grid[~early]).T
            if meta['closed']:
                meta['endpoint_correction'] = float(np.linalg.norm(points[-1]-seed)); points[-1] = seed
    except (ValueError, _EvaluationBudget) as error:
        # A failed/over-budget solve supplies no certified partial interpolant.
        meta['status'] = 'evaluation_budget' if isinstance(error, _EvaluationBudget) else 'invalid_field'
        meta['reason'] = str(error); points = seed[None, :]
    meta['function_evaluations'] = min(calls, max_evaluations)
    meta['minimum_field_ratio'] = float(minimum_ratio if np.isfinite(minimum_ratio) else value)
    return points, meta


def trace_candidate(seed, time, p, q, **settings):
    p, q = exponents(p, q)
    return trace_line(lambda x: candidate(x, time, p, q)[1], seed,
                      ratio=lambda x: field_ratio(x, time, p, q), **settings)


def initial_null_checks(points, p, q, steps=(.02, .01, .005)):
    """Sample Kedia 2018 Eq.(10); this is not a global analytic/smooth-flow certificate."""
    e, b = candidate(points, 0, p, q); f = e+1j*b
    norm = np.linalg.norm(f, axis=-1); usable = field_ratio(points, 0, p, q) >= 1e-8
    if not np.any(usable) or not steps or not all(np.isfinite(h) and h > 0 for h in steps):
        raise ValueError('nonzero sample points and finite positive difference steps required')
    results = []
    for h in steps:
        derivatives = []
        for axis in np.eye(3):
            ep, bp = candidate(points+h*axis, 0, p, q); em, bm = candidate(points-h*axis, 0, p, q)
            derivatives.append(((ep+1j*bp)-(em+1j*bm))/(2*h))
        curl = np.stack((derivatives[1][..., 2]-derivatives[2][..., 1],
                         derivatives[2][..., 0]-derivatives[0][..., 2],
                         derivatives[0][..., 1]-derivatives[1][..., 0]), axis=-1)
        denominator = norm*np.linalg.norm(curl, axis=-1)
        score = abs(np.sum(f*curl, axis=-1))/np.maximum(denominator, 1e-300)
        results.append({'step': h, 'max_normalised_complex_curl': float(np.max(score[usable]))})
    return {'max_normalised_null': float(np.max(abs(np.sum(f*f, axis=-1))[usable]/norm[usable]**2)),
            'sample_count': int(np.sum(usable)), 'excluded_near_zero': int(np.sum(~usable)), 'complex_curl': results}
