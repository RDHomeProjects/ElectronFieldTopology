"""Neutral SF continuum action and finite-cell admission diagnostics. Apache-2.0.

This module does not evolve physical time. See docs/models/SF-relativistic.md.
"""
from itertools import product
import numpy as np
from .skyrme import K, NORTH


def lagrangian(d, velocity):
    """L/K for spatial jets (...,3,3), time jet (...,3); signature +---."""
    d = np.asarray(d, dtype=float)
    velocity = np.asarray(velocity, dtype=float)
    e2 = np.sum(d*d, axis=(-2, -1))
    e4 = sum(np.sum(np.cross(d[..., i, :], d[..., j, :])**2, axis=-1)
             for i, j in ((0, 1), (0, 2), (1, 2)))
    kinetic = np.sum(velocity*velocity, axis=-1)
    kinetic += np.sum(np.cross(velocity[..., None, :], d)**2, axis=(-2, -1))
    return kinetic-e2-e4


def currents(d, velocity):
    """Return (p,q_i)/K = derivatives of L/K with respect to time/spatial jets."""
    d = np.asarray(d, dtype=float)
    velocity = np.asarray(velocity, dtype=float)
    vv = np.sum(velocity*velocity, axis=-1)
    norms = np.sum(d*d, axis=-1)
    vd = np.sum(d*velocity[..., None, :], axis=-1)
    p = 2*(velocity*(1+np.sum(norms, axis=-1))[..., None]
           - np.sum(vd[..., None]*d, axis=-2))
    q = -2*d+2*(vv[..., None, None]*d-vd[..., None]*velocity[..., None, :])
    for i in range(3):
        for j in range(3):
            if i != j:
                dot = np.sum(d[..., i, :]*d[..., j, :], axis=-1)
                q[..., i, :] -= 2*(norms[..., j, None]*d[..., i, :]
                                     - dot[..., None]*d[..., j, :])
    return p, q


def stress_energy(d, velocity):
    """Contravariant T^{mu nu}/K, explicit canonical derivative (symmetric here)."""
    p, q = currents(d, velocity)
    ell = lagrangian(d, velocity)
    t = np.empty(np.shape(ell)+(4, 4))
    t[..., 0, 0] = np.sum(p*velocity, axis=-1)-ell
    t[..., 0, 1:] = -np.sum(p[..., None, :]*d, axis=-1)
    t[..., 1:, 0] = np.sum(q*velocity[..., None, :], axis=-1)
    t[..., 1:, 1:] = -np.einsum('...ia,...ja->...ij', q, d)
    for i in range(3):
        t[..., i+1, i+1] += ell
    return t


def boost_jet(d, beta, axis):
    """t=0 jet of n0(gamma*(x_axis-beta*t), other x); no evolution."""
    if axis not in (0, 1, 2) or not np.isfinite(beta) or abs(beta) >= 1:
        raise ValueError('A coordinate axis and finite |beta|<1 are required')
    gamma = 1/np.sqrt(1-beta*beta)
    boosted = np.array(d, copy=True)
    boosted[..., axis, :] *= gamma
    return boosted, -gamma*beta*d[..., axis, :]


def boost_integrals(energy, stress, speeds):
    """Tensor transform integrated over the Lorentz-contracted rest box.

    E=gamma*(E0+beta^2*Saa), Pa=gamma*beta*(E0+Saa), Pb=beta*Sab.
    Particle four-momentum requires the integrated rest stresses to vanish.
    """
    rows = []
    for axis in range(3):
        for beta in speeds:
            if not np.isfinite(beta) or not 0 <= beta < 1:
                raise ValueError('Finite 0<=beta<1 required')
            gamma = 1/np.sqrt(1-beta*beta)
            e = gamma*(energy+beta*beta*stress[axis, axis])
            p = beta*np.array(stress[axis], copy=True)
            p[axis] = gamma*beta*(energy+stress[axis, axis])
            rows.append({'axis': axis, 'beta': beta, 'gamma': float(gamma),
                         'energy': float(e), 'momentum': p.tolist(),
                         'energy_particle_relative_defect': float(e/(gamma*energy)-1),
                         'momentum_particle_scaled_defect': float(np.linalg.norm(
                             p-gamma*beta*energy*np.eye(3)[axis])/(gamma*energy)),
                         'mass_squared_over_rest_energy_squared': float((e*e-p@p)/energy**2)})
    return rows


def perturbation(u, h, mode):
    """Four fixed smooth tangent nodal directions, compact at the fixed faces."""
    if mode not in range(4):
        raise ValueError('Reviewed direction 0..3 required')
    n = len(u)
    z = np.linspace(-1, 1, n)
    x, y, z = np.meshgrid(z, z, z, indexing='ij', sparse=True)
    envelope = (1-x*x)**3*(1-y*y)**3*(1-z*z)**3
    w = np.zeros_like(u)
    if mode < 3:
        w[..., mode] = envelope*np.cos(np.pi*(x+2*y+3*z)/4)
    else:
        w[..., 0] = envelope*np.sin(np.pi*y)
        w[..., 1] = envelope*np.sin(np.pi*z)
        w[..., 2] = envelope*np.sin(np.pi*x)
    w -= u*np.sum(w*u, axis=-1, keepdims=True)
    for axis in range(3):
        sl = [slice(None)]*4; sl[axis] = [0, 1, n-2, n-1]
        w[tuple(sl)] = 0
    maximum = float(np.max(np.linalg.norm(w, axis=-1)))
    if maximum == 0:
        return w
    return w/maximum


def sphere_step(u, w, epsilon):
    r = np.linalg.norm(w, axis=-1, keepdims=True)
    return np.cos(epsilon*r)*u+epsilon*np.sinc(epsilon*r/np.pi)*w


def cell_integrals(u, h, slab=4, directions=(), progress=None):
    """Independent normalized-trilinear 2^3 Gauss quadrature, bounded slabs.

    Same static interpolation/quadrature as production; independently coded.
    Directions are nodal tangent velocities. No full-volume jet arrays retained.
    """
    u = np.asarray(u)
    n = len(u)
    if (u.shape != (n, n, n, 3) or n < 5 or not np.isfinite(h) or h <= 0
            or not np.isfinite(u).all() or slab < 1):
        raise ValueError('Finite cubic field, positive spacing and slab required')
    if np.max(abs(np.linalg.norm(u, axis=-1)-1)) > 1e-10:
        raise ValueError('Unit nodal field required; no implicit repair')
    if any(w.shape != u.shape for w in directions):
        raise ValueError('Nodal direction geometry mismatch')
    gauss = [.5-.5/np.sqrt(3), .5+.5/np.sqrt(3)]
    corners = list(product((0, 1), repeat=3))
    energy = np.zeros(2); stress = np.zeros((3, 3))
    moment = np.zeros(3); radius2 = 0.; outer = 0.
    norms = np.zeros(len(directions)); min_metric = np.inf; max_metric = 0.
    max_condition = 1.; minimum_cone = 1.; direct_e = 0.; direct_p = np.zeros(3)
    weight = K*h**3/8
    for start in range(0, n-1, slab):
        stop = min(start+slab, n-1)
        pieces = [u[start+a:stop+a, b:n-1+b, c:n-1+c] for a, b, c in corners]
        centre = sum(pieces)
        cn = np.linalg.norm(centre, axis=-1, keepdims=True)
        if np.min(cn) < 1e-12:
            raise ValueError('Unresolved interpolation cell')
        minimum_cone = min(minimum_cone, min(float(np.min(np.sum(p*centre/cn, axis=-1)))
                                           for p in pieces))
        if minimum_cone <= 0:
            raise ValueError('Field does not have resolved open-hemisphere cells')
        for point in product(gauss, repeat=3):
            shape = []; grad_shape = []
            for corner in corners:
                f = [point[i] if corner[i] else 1-point[i] for i in range(3)]
                shape.append(np.prod(f))
                grad_shape.append([(1 if corner[i] else -1)*f[(i+1)%3]*f[(i+2)%3]/h
                                   for i in range(3)])
            value = sum(s*p for s, p in zip(shape, pieces))
            r = np.linalg.norm(value, axis=-1, keepdims=True)
            nn = value/r
            d = np.stack([sum(g[i]*p for g, p in zip(grad_shape, pieces)) for i in range(3)], axis=-2)
            d = (d-nn[..., None, :]*np.sum(d*nn[..., None, :], axis=-1, keepdims=True))/r[..., None]
            e2 = np.sum(d*d, axis=(-2, -1))
            crosses = [np.sum(np.cross(d[..., i, :], d[..., j, :])**2, axis=-1)
                       for i, j in ((0, 1), (0, 2), (1, 2))]
            e4 = sum(crosses); density = e2+e4
            energy += weight*np.array([np.sum(e2), np.sum(e4)])
            # Derivative of V with respect to a_i, and rest Tij.
            _, q = currents(d, np.zeros_like(nn))
            tensor = -np.einsum('...ia,...ja->...ij', q, d)
            for i in range(3): tensor[..., i, i] -= density
            stress += weight*np.sum(tensor, axis=(0, 1, 2))
            # Tangent kinetic eigenvalues are 1+lambda_min/max of sum a_i a_i^T.
            gram = np.einsum('...ia,...ja->...ij', d, d)
            discriminant = np.maximum(0, 2*np.sum(gram*gram, axis=(-2, -1))-e2*e2)
            lo = 1+(e2-np.sqrt(discriminant))/2
            hi = 1+(e2+np.sqrt(discriminant))/2
            min_metric = min(min_metric, float(np.min(lo)))
            max_metric = max(max_metric, float(np.max(hi)))
            max_condition = max(max_condition, float(np.max(hi/lo)))
            coords = [(np.arange(start, stop)+point[0]-(n-1)/2)*h,
                      (np.arange(n-1)+point[1]-(n-1)/2)*h,
                      (np.arange(n-1)+point[2]-(n-1)/2)*h]
            xyz = np.meshgrid(*coords, indexing='ij', sparse=True)
            rr = sum(x*x for x in xyz)
            radius2 += weight*float(np.sum(rr*density))
            mask = np.zeros(density.shape, dtype=bool)
            for i, x in enumerate(xyz):
                moment[i] += weight*float(np.sum(x*density))
                mask |= abs(x) > .8*(n-1)*h/2
            outer += weight*float(np.sum(density[mask]))
            # Independent jet evaluation at beta=.6, x; compare integrated tensor rule.
            bd, velocity = boost_jet(d, .6, 0)
            p, _ = currents(bd, velocity)
            direct_e += weight/1.25*float(np.sum(np.sum(p*velocity, axis=-1)-lagrangian(bd, velocity)))
            direct_p += weight/1.25*np.sum(-np.sum(p[..., None, :]*bd, axis=-1), axis=(0, 1, 2))
            for k, w in enumerate(directions):
                wp = [w[start+a:stop+a, b:n-1+b, c:n-1+c] for a, b, c in corners]
                v = sum(s*p for s, p in zip(shape, wp))
                v = (v-nn*np.sum(nn*v, axis=-1, keepdims=True))/r
                norms[k] += 2*weight*float(np.sum(np.sum(v*v, axis=-1)
                    + np.sum(np.cross(v[..., None, :], d)**2, axis=(-2, -1))))
        if progress: progress(stop, n-1)
    total = float(sum(energy)); centroid = moment/total if total else np.zeros(3)
    return {'energy_parts': energy.tolist(), 'energy': total, 'integrated_stress': stress.tolist(),
            'stress_frobenius_over_energy': float(np.linalg.norm(stress)/total) if total else 0.,
            'trace_identity_error': float(np.trace(stress)-energy[1]+energy[0]),
            'kinetic_tangent_min': min_metric, 'kinetic_tangent_max': max_metric,
            'max_local_kinetic_condition': max_condition, 'minimum_corner_cone': minimum_cone,
            'centroid': centroid.tolist(),
            'rms_radius': float(np.sqrt(max(0, radius2/total-centroid@centroid))) if total else 0.,
            'outer_20_percent_energy_fraction': outer/total if total else 0.,
            'direction_kinetic_norms': norms.tolist(),
            'direct_boost_beta06_axis0': {'energy': direct_e, 'momentum': direct_p.tolist()}}
