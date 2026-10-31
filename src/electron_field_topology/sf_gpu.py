"""Experimental float64 CuPy backend for the unchanged SF-J2015 functional.

Model/gradient derivation: docs/models/SF-J2015-static.md. Apache-2.0.
CPU tests can exercise array routines with NumPy; that is not GPU execution.
"""
from pathlib import Path
import numpy as np
from .skyrme import K


def cupy_module():
    try:
        import cupy as cp
    except ImportError as error:
        raise RuntimeError("GPU extra required: uv sync --frozen --extra gpu --python 3.12.14") from error
    if cp.cuda.runtime.getDeviceCount() < 1:
        raise RuntimeError("No CUDA GPU is accessible; no CPU fallback is used")
    return cp


def quadrature():
    """Exactly the shape weights used by the native 2x2x2 Gauss cell rule."""
    shape = np.empty((8, 8)); der = np.empty((8, 8, 3))
    gauss = [.5-.5/np.sqrt(3.), .5+.5/np.sqrt(3.)]
    for q in range(8):
        for a in range(8):
            f = [gauss[(q >> (2-i)) & 1] if (a >> (2-i)) & 1
                 else 1-gauss[(q >> (2-i)) & 1] for i in range(3)]
            shape[q, a] = f[0]*f[1]*f[2]
            for i in range(3):
                der[q, a, i] = (1. if (a >> (2-i)) & 1 else -1.) * f[(i+1) % 3]*f[(i+2) % 3]
    return shape, der  # Derivatives divided by h when uploaded.


class GPUEnergy:
    def __init__(self, n, h, block_size=128):
        if isinstance(n, bool) or not isinstance(n, int) or not 9 <= n <= 301 or n % 2 != 1:
            raise ValueError("Odd grid 9..301 required")
        if not np.isfinite(h) or h <= 0 or block_size not in (64, 128, 256):
            raise ValueError("Positive spacing and supported block size required")
        self.cp = cp = cupy_module()
        self.n, self.h, self.block_size = n, h, block_size
        shape, der = quadrature()
        self.shape = cp.asarray(shape); self.der = cp.asarray(der/h)
        self.grad = cp.empty((n, n, n, 3), dtype=cp.float64)
        self.metrics = cp.empty((4, (n-1)**3), dtype=cp.float64)
        self.kernel = cp.RawKernel(Path(__file__).with_name("sf_energy_gpu.cu").read_text(),
                                   "sf_cell_color", options=("--std=c++11", "--fmad=false"))

    def evaluate(self, u):
        cp = self.cp
        u = cp.ascontiguousarray(u, dtype=cp.float64)
        if u.shape != (self.n, self.n, self.n, 3) or not bool(cp.isfinite(u).all()):
            raise ValueError("Field shape/finite values")
        self.grad.fill(0)
        count = ((self.n-1)//2)**3
        for color in range(8):
            self.kernel(((count+self.block_size-1)//self.block_size,), (self.block_size,),
                        (np.int32(self.n), np.float64(self.h), u, self.grad, self.metrics,
                         self.shape, self.der, np.int32(color)))
        minima = cp.asnumpy(cp.min(self.metrics[2:], axis=1))
        self.minimum_interpolant_norm, self.minimum_corner_cone = map(float, minima)
        if self.minimum_interpolant_norm < 1e-8:
            raise ValueError("Unresolved normalized interpolant")
        factor = K*self.h**3
        return cp.sum(self.metrics[:2], axis=1)*factor, self.grad.copy()*factor


def dst1n(a, xp):
    """Orthonormal DST-I on axes 0,1,2, via odd FFT extensions.

    For length m: -Im FFT([0,a,0,-reverse(a)])[1:m+1]/sqrt(2(m+1)).
    The transform is self-inverse; CPU tests compare against SciPy/direct sine.
    """
    for axis in range(3):
        m = a.shape[axis]
        shape = list(a.shape); shape[axis] = 1
        zero = xp.zeros(shape, dtype=xp.float64)
        odd = xp.concatenate((zero, a, zero, -xp.flip(a, axis=axis)), axis=axis)
        spectrum = xp.fft.fft(odd, axis=axis)
        sl = [slice(None)]*a.ndim; sl[axis] = slice(1, m+1)
        a = xp.ascontiguousarray(-spectrum.imag[tuple(sl)]/np.sqrt(2*(m+1)))
    return a


def normalize_array(v, xp):
    v = xp.asarray(v, dtype=xp.float64)
    r = xp.linalg.norm(v, axis=-1, keepdims=True)
    if not bool(xp.isfinite(v).all()) or float(xp.min(r)) < 1e-12:
        raise ValueError("Finite nonzero field required")
    return v/r


def minimize_array(engine, initial, maxiter, callback, expired, xp, length=.5, strict_continuity=False):
    """Port of sf_minimize.minimize_static: identical controls and stop rules."""
    u = initial.copy(); n = len(u); h = engine.h; m = n-4
    k = xp.arange(1, m+1)
    lam = 4*xp.sin(np.pi*k/(2*(m+1)))**2/h**2
    divisor = 1+length**2*(lam[:, None, None]+lam[None, :, None]+lam[None, None, :])
    def projected(a):
        a -= u*xp.sum(a*u, axis=-1, keepdims=True)
        for ax in range(3):
            sl = [slice(None)]*4; sl[ax] = [0, 1, n-2, n-1]; a[tuple(sl)] = 0
        return a
    parts, g = engine.evaluate(u); energy = float(sum(parts))
    old_g = old_z = direction = None; alpha = .01; evaluations = 1
    for iteration in range(1, maxiter+1):
        if expired():
            return u, {"status": "time_budget", "iterations": iteration-1, "evaluations": evaluations}
        accepted_margin = engine.minimum_corner_cone
        g = projected(g/(K*h**3))
        z = xp.zeros_like(g)
        z[2:-2, 2:-2, 2:-2] = dst1n(dst1n(g[2:-2, 2:-2, 2:-2], xp)/divisor[..., None], xp)
        z = projected(z)
        beta = 0. if old_g is None else max(0., float(xp.sum(g*(z-old_z))) /
                                          max(float(xp.sum(old_g*old_z)), 1e-30))
        direction = -z if direction is None else -z+beta*projected(direction)
        dot = float(xp.sum(g*direction))*K*h**3
        if dot >= 0:
            direction = -z; dot = -float(xp.sum(g*z))*K*h**3
        maximum = float(xp.max(xp.linalg.norm(direction, axis=-1)))
        alpha = min(alpha*1.5, .1/max(maximum, 1e-30))
        accepted = False
        for _ in range(20):
            if strict_continuity and expired():
                return u, {"status": "time_budget", "iterations": iteration-1, "evaluations": evaluations}
            trial = normalize_array(u+alpha*direction, xp)
            margin = accepted_margin if strict_continuity else engine.minimum_corner_cone
            if float(xp.max(xp.linalg.norm(trial-u, axis=-1))) > min(.2, .5*margin):
                alpha *= .5; continue
            p, gg = engine.evaluate(trial); evaluations += 1; e = float(sum(p))
            if engine.minimum_corner_cone > 0 and e <= energy+1e-4*alpha*dot:
                accepted = True; break
            alpha *= .5
        if not accepted:
            return u, {"status": "line_search_limit", "iterations": iteration-1, "evaluations": evaluations}
        old_g = g.copy(); old_z = z.copy(); u = trial; g = gg; energy = e
        callback(u, iteration)
        if float(xp.sqrt(xp.mean(old_g[2:-2, 2:-2, 2:-2]**2))) < 1e-3:
            return u, {"status": "gradient_stationary", "iterations": iteration, "evaluations": evaluations}
    return u, {"status": "iteration_budget", "iterations": maxiter, "evaluations": evaluations}


def diagnostics_array(u, h, xp):
    """Same fourth-order differences and periodic Hopf integral as skyrme.py."""
    north = xp.asarray([0., 0., 1.])
    def derivative(v, axis):
        pad = [(0, 0)]*v.ndim; pad[axis] = (2, 2); padded = xp.pad(v, pad)
        def at(o):
            sl = [slice(None)]*v.ndim; sl[axis] = slice(2+o, 2+o+v.shape[axis])
            return padded[tuple(sl)]
        return (at(-2)-8*at(-1)+8*at(1)-at(2))/(12*h)
    d = [derivative(u-north, i) for i in range(3)]
    b = xp.stack([xp.sum(u*xp.cross(d[1], d[2]), axis=-1),
                  xp.sum(u*xp.cross(d[2], d[0]), axis=-1),
                  xp.sum(u*xp.cross(d[0], d[1]), axis=-1)], axis=-1)
    wave = 2*np.pi*xp.fft.fftfreq(len(u), h)
    k = xp.stack(xp.meshgrid(wave, wave, wave, indexing="ij"), axis=-1)
    k2 = xp.sum(k*k, axis=-1); k2[0, 0, 0] = 1.
    bh = xp.fft.fftn(b, axes=(0, 1, 2)); ah = 1j*xp.cross(k, bh)/k2[..., None]; ah[0, 0, 0] = 0
    a = xp.fft.ifftn(ah, axes=(0, 1, 2)).real
    angle = max(float(xp.max(xp.arccos(xp.clip(xp.sum(
        xp.take(u, xp.arange(len(u)-1), axis=i)*xp.take(u, xp.arange(1, len(u)), axis=i),
        axis=-1), -1, 1)))) for i in range(3))
    mean = xp.mean(b, axis=(0, 1, 2))
    return {"hopf_integral": float(xp.sum(a*b)*h**3/(16*np.pi**2)),
            "unit_error": float(xp.max(abs(xp.linalg.norm(u, axis=-1)-1))),
            "max_neighbour_angle": angle,
            "mean_topological_b": [float(x) for x in mean],
            "scope": "finite-grid Coulomb-gauge integral, not an exact integer certificate"}
