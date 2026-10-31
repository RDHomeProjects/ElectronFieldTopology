"""Finite return-section diagnostics and explicitly manufactured torus controls."""
import numpy as np


def section_coordinates(meta):
    """Return seed-centred plane coordinates; no invariant torus is assumed."""
    normal = meta.get('section_normal')
    if normal is None:
        return {'basis': None, 'returns': [], 'angular_interpretation': 'not_assigned'}
    n = np.asarray(normal, dtype=float); n /= np.linalg.norm(n)
    u = np.cross(n, np.eye(3)[np.argmin(abs(n))]); u /= np.linalg.norm(u)
    v = np.cross(n, u); seed = np.asarray(meta['seed']); rows = []
    for row in meta['section_returns']:
        delta = np.asarray(row['position'])-seed
        rows.append({**row, 'plane_coordinates': [float(delta@u), float(delta@v)],
                     'plane_residual': float(delta@n)})
    return {'basis': [u.tolist(), v.tolist()], 'returns': rows,
            'angular_interpretation': 'not_assigned'}


def compare_returns(reference, trial, limit=1e-5):
    """Compare the common prefix; shorter observation budgets are allowed to have fewer events."""
    a, b = reference['section_returns'], trial['section_returns']; n = min(len(a),len(b))
    if not n:
        return {'common_returns': 0, 'comparison': 'insufficient_returns', 'repeatable': None}
    position = max(float(np.linalg.norm(np.asarray(x['position'])-y['position'])) for x,y in zip(a[:n],b[:n]))
    length = max(abs(x['arclength']-y['arclength']) for x,y in zip(a[:n],b[:n]))
    # A changed count within the shared observation interval is a sensitivity signal.
    end = min(reference['evaluated_arclength'],trial['evaluated_arclength'])-1e-5
    counts = [sum(x['arclength'] <= end for x in r) for r in [a,b]]
    repeatable = position < limit and length < limit and counts[0] == counts[1]
    return {'common_returns': n, 'max_position_difference': position, 'max_arclength_difference': length,
            'shared_interval_counts': counts, 'repeatable': bool(repeatable),
            'comparison': 'repeatable_prefix' if repeatable else 'control_sensitive'}


def torus_field(omega, major=2.):
    """Manufactured dtheta/dtau=1, dphi/dtau=omega on (rho-major)^2+z^2=r^2.

    The Cartesian expression is obtained by differentiating the explicit torus
    embedding. It is a numerical control, not an electromagnetic model.
    """
    if not np.isfinite(omega) or not np.isfinite(major) or major <= 0:
        raise ValueError('finite torus frequency and positive major radius required')
    def field(point):
        x,y,z = np.asarray(point,dtype=float); rho = np.hypot(x,y)
        if rho < 1e-12: raise ValueError('torus control excludes its cylindrical axis')
        return np.array([-y-omega*z*x/rho, x-omega*z*y/rho, omega*(rho-major)])
    return field


def torus_check(points, meta, omega, phi0=.3, major=2., minor=.5):
    rows = meta['section_returns']; errors = []
    for i,row in enumerate(rows,1):
        x,y,z = row['position']; phi = np.arctan2(z,np.hypot(x,y)-major)
        expected = phi0+2*np.pi*omega*i
        errors.append(float(abs(np.angle(np.exp(1j*(phi-expected))))))
    checked = np.vstack([points, np.array([row['position'] for row in rows]).reshape(-1,3)])
    rho = np.hypot(checked[:,0],checked[:,1])
    residual = float(np.max(abs((rho-major)**2+checked[:,2]**2-minor**2)))
    kind = ('periodic' if omega == .5 else 'irrational_linear_torus_flow_analytic_target'
            if omega == float(np.sqrt(2)) else 'frequency_not_classified')
    return {'return_count':len(rows), 'max_wrapped_angle_error':max(errors) if errors else None,
            'max_torus_equation_error':residual,
            'known_control_type':kind,
            'scope':'analytic manufactured control only; no Maxwell rotation number assigned'}
