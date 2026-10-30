"""Bateman (1,1) Hopfion, Valverde et al. arXiv:2003.01896v1 Eqs. 1-5.

Apache-2.0. Coordinates and fields are dimensionless; c=epsilon_0=mu_0=1.
This evaluates an exact solution; it is not a numerical time integrator.
"""
import numpy as np


def hopfion(points, time=0.0):
    """Return E, B with shape (..., 3) for real points of shape (..., 3).

    p=q=1 and unit amplitude/length only. Time broadcasts with point leading axes.
    """
    points = np.asarray(points, dtype=float)
    if points.ndim < 1 or points.shape[-1] != 3:
        raise ValueError("points must have final dimension 3")
    if np.iscomplexobj(time):
        raise ValueError("time must be real")
    time = np.asarray(time, dtype=float)
    if not np.isfinite(points).all() or not np.isfinite(time).all():
        raise ValueError("points and time must be finite")
    shape = np.broadcast_shapes(points.shape[:-1], time.shape)
    points = np.broadcast_to(points, shape + (3,))
    time = np.broadcast_to(time, shape)
    x, y, z = np.moveaxis(points, -1, 0)
    r2 = np.sum(points * points, axis=-1)
    denominator = r2 - (time - 1j)**2
    alpha_numerator = r2 - time*time - 1 + 2j*z
    beta_numerator = 2*(x - 1j*y)
    grad_denominator = 2*points
    grad_alpha_numerator = grad_denominator.astype(complex)
    grad_alpha_numerator[..., 2] += 2j
    grad_beta_numerator = np.array([2, -2j, 0])
    grad_alpha = (grad_alpha_numerator * denominator[..., None]
                  - alpha_numerator[..., None] * grad_denominator) / denominator[..., None]**2
    grad_beta = (grad_beta_numerator * denominator[..., None]
                 - beta_numerator[..., None] * grad_denominator) / denominator[..., None]**2
    field = np.cross(grad_alpha, grad_beta)
    return field.real, field.imag
