"""Diagnostics for analytical fields; Apache-2.0."""
import numpy as np
from numpy.polynomial.legendre import leggauss
from .fields import hopfion


def energy_flow(e, b):
    return (np.sum(e*e, axis=-1) + np.sum(b*b, axis=-1))/2, np.cross(e, b)


def sphere_rule(radius, order, center=(0, 0, 0), volume=True):
    """Gauss-Legendre r/mu, periodic trapezoid phi; no evolution boundary."""
    if radius <= 0 or order < 2:
        raise ValueError("positive radius and quadrature order >=2 required")
    mu, wm = leggauss(order)
    phi = 2*np.pi*np.arange(2*order)/(2*order)
    normals = np.stack(np.broadcast_arrays(
        np.sqrt(1-mu[:, None]**2)*np.cos(phi),
        np.sqrt(1-mu[:, None]**2)*np.sin(phi), mu[:, None]), axis=-1)
    angular = np.broadcast_to(wm[:, None]*(np.pi/order), normals.shape[:-1])
    if not volume:
        return center + radius*normals, radius**2*angular, normals
    r, wr = leggauss(order)
    r, wr = radius*(r+1)/2, radius*wr/2
    points = np.asarray(center) + r[:, None, None, None]*normals
    weights = (wr*r*r)[:, None, None]*angular
    return points, weights


def sphere_integrals(radius, order, time=0.0, center=(0, 0, 0)):
    points, weights = sphere_rule(radius, order, center)
    e, b = hopfion(points, time)
    u, flow = energy_flow(e, b)
    axes = tuple(range(weights.ndim))
    energy = np.sum(weights*u)
    momentum = np.sum(weights[..., None]*flow, axis=axes)
    angular = np.sum(weights[..., None]*np.cross(points, flow), axis=axes)
    centroid = np.sum(weights[..., None]*points*u[..., None], axis=axes)/energy
    return {"energy": float(energy), "momentum": momentum.tolist(),
            "angular_momentum_about_origin": angular.tolist(),
            "centroid": centroid.tolist()}


def sphere_flux(radius, order, time=0.0, center=(0, 0, 0)):
    points, weights, normal = sphere_rule(radius, order, center, volume=False)
    e, _ = hopfion(points, time)
    integrand = np.sum(e*normal, axis=-1)
    return {"electric_flux": float(np.sum(weights*integrand)),
            "absolute_flux_integral": float(np.sum(weights*np.abs(integrand)))}


def maxwell_residuals(points, time, step):
    """Second-order centred differences at fixed points, including time."""
    if step <= 0:
        raise ValueError("step must be positive")
    derivatives = []
    for axis in range(3):
        shift = np.eye(3)[axis]*step
        ep, bp = hopfion(points+shift, time)
        em, bm = hopfion(points-shift, time)
        derivatives.append(((ep-em)/(2*step), (bp-bm)/(2*step)))
    ep, bp = hopfion(points, time+step)
    em, bm = hopfion(points, time-step)
    de, db = (ep-em)/(2*step), (bp-bm)/(2*step)
    je = np.stack([d[0] for d in derivatives], axis=-1)
    jb = np.stack([d[1] for d in derivatives], axis=-1)
    def curl(j):
        return np.stack((j[..., 2, 1]-j[..., 1, 2], j[..., 0, 2]-j[..., 2, 0],
                         j[..., 1, 0]-j[..., 0, 1]), axis=-1)
    return {"div_e": np.trace(je, axis1=-2, axis2=-1),
            "div_b": np.trace(jb, axis1=-2, axis2=-1),
            "faraday": db+curl(je), "ampere": de-curl(jb)}
