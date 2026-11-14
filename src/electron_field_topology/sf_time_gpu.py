"""Float64 array port of the established D4 action and projected RK4.

Model/equation source: docs/models/SF-physical-time.md. Apache-2.0.
ArrayTime(numpy) is a host test double, never CUDA execution evidence.
CUDATime explicitly requires CuPy and an accessible device; no fallback.
"""
import numpy as np
from .skyrme import K


class ArrayTime:
    def __init__(self, xp):
        self.xp = xp
        self.north = xp.asarray([0., 0., 1.], dtype=xp.float64)
        self._masks = {}
        self._points = {}
        self.execution_kind = 'numpy-test-double' if xp is np else 'cuda-cupy-float64'

    def fixed_mask(self, grid):
        if grid not in self._masks:
            self._masks[grid] = self.xp.asarray(grid.fixed_mask())
        return self._masks[grid]

    def points(self, grid):
        if grid not in self._points:
            xp = self.xp
            axes = [-l/2 + xp.arange(n)*h for n,l,h in zip(grid.shape,grid.lengths,grid.spacing)]
            self._points[grid] = xp.stack(xp.meshgrid(*axes,indexing='ij'),axis=-1)
        return self._points[grid]

    def force(self, forcing, grid, t):
        # The independently derived manufactured test source remains on the CPU.
        return self.xp.asarray(forcing(grid.points(),t),dtype=self.xp.float64)

    def upload(self, n, v):
        if n.dtype != np.float64 or v.dtype != np.float64:
            raise ValueError('Float64 states required; no implicit precision reduction')
        return self.xp.asarray(n).copy(), self.xp.asarray(v).copy()

    def host(self, a):
        return np.array(a,copy=True) if self.xp is np else self.xp.asnumpy(a)

    def synchronize(self):
        if self.xp is not np:
            self.xp.cuda.get_current_stream().synchronize()

    def solve(self, mass, rhs):
        return self.xp.linalg.solve(mass, rhs)

    def tail_band(self, n, v, grid, width):
        xp = self.xp
        e = self.densities(n, v, grid, include_stress=False)['energy_density']
        mask = xp.any(abs(self.points(grid)) >= xp.asarray(grid.lengths)/2-width, axis=-1)
        total = float(xp.sum(e)*np.prod(grid.spacing))
        shell = float(xp.sum(e[mask])*np.prod(grid.spacing))
        return {'width':width, 'energy':shell, 'total_continuum_energy':total,
                'fraction':shell/total if total>0 else None}

    def reference_error(self, n, expected):
        return float(self.xp.sqrt(self.xp.mean((n-self.xp.asarray(expected))**2)))

    def static_value_gradient(self, n, grid):
        xp = self.xp
        d = self.gradients(n-self.north,grid)
        sigma,force = self.sigma_terms(n,grid)
        _,q = self.currents(d,xp.zeros_like(n))
        for i,h in enumerate(grid.spacing):
            force += self.derivative(-.5*q[...,i,:]-d[...,i,:],h,i,grid.boundary)
        e4 = sum(xp.sum(xp.cross(d[...,i,:],d[...,j,:])**2,axis=-1)
                 for i,j in [(0,1),(0,2),(1,2)])
        volume = np.prod(grid.spacing)
        return float(K*xp.sum(sigma+e4)*volume),-2*K*volume*force

    def derivative(self, a, h, axis, boundary='periodic'):
        """Skew-adjoint D4; fixed mode is its constant-zero-exterior restriction."""
        xp = self.xp
        if a.shape[axis] == 1:
            return xp.zeros_like(a)
        if boundary == 'periodic':
            return (xp.roll(a, 2, axis) - 8 * xp.roll(a, 1, axis) + 8 * xp.roll(a, -1, axis) - xp.roll(a, -2, axis)) / (12 * h)
        if boundary != 'fixed':
            raise ValueError('Unknown boundary')
        pad = [(0, 0)] * a.ndim
        pad[axis] = (2, 2)
        p = xp.pad(a, pad)

        def at(offset):
            sl = [slice(None)] * a.ndim
            sl[axis] = slice(2 + offset, 2 + offset + a.shape[axis])
            return p[tuple(sl)]
        return (at(-2) - 8 * at(-1) + 8 * at(1) - at(2)) / (12 * h)

    def gradients(self, a, grid):
        xp = self.xp
        return xp.stack([self.derivative(a, h, i, grid.boundary) for i, h in enumerate(grid.spacing)], axis=-2)

    def sigma_terms(self, n, grid):
        """Positive fourth-order sigma action and its exact nodal force.

        E2=sum |D+u|^2+h^2/12 |D2u|^2. Its force is the standard fourth-order
        Laplacian. Unlike D4^T D4 it has no spurious zero at the Nyquist mode.
        """
        xp = self.xp
        u = n - self.north
        density = xp.zeros(n.shape[:-1])
        force = xp.zeros_like(n)
        for axis, (h, count) in enumerate(zip(grid.spacing, grid.shape)):
            if count == 1:
                continue
            if grid.boundary == 'periodic':

                def at(offset):
                    return xp.roll(u, -offset, axis)
            else:
                pad = [(0, 0)] * u.ndim
                pad[axis] = (2, 2)
                p = xp.pad(u, pad)

                def at(offset):
                    sl = [slice(None)] * u.ndim
                    sl[axis] = slice(2 + offset, 2 + offset + count)
                    return p[tuple(sl)]
            ahead = at(1)
            behind = at(-1)
            d2 = (ahead - 2 * u + behind) / h ** 2
            density += 0.5 * xp.sum(((ahead - u) / h) ** 2 + ((u - behind) / h) ** 2, axis=-1) + h * h / 12 * xp.sum(d2 * d2, axis=-1)
            force += (-at(2) + 16 * ahead - 30 * u + 16 * behind - at(-2)) / (12 * h * h)
        return (density, force)

    def retract(self, n, v, grid):
        """Explicit sphere/tangent projection, including fixed north faces."""
        xp = self.xp
        if n.shape != grid.shape + (3,) or v.shape != n.shape or (not xp.isfinite(n).all()) or (not xp.isfinite(v).all()):
            raise ValueError('Finite n/v with declared shape required')
        size = xp.linalg.norm(n, axis=-1, keepdims=True)
        if xp.min(size) < 1e-12:
            raise ValueError('Field normalization singularity')
        nn = n / size
        vv = v - nn * xp.sum(nn * v, axis=-1, keepdims=True)
        if grid.boundary == 'fixed':
            mask = self.fixed_mask(grid)
            nn[mask] = self.north
            vv[mask] = 0
        return (nn, vv)

    def jets(self, n, v, grid):
        xp = self.xp
        d = self.gradients(n - self.north, grid)
        return (d, self.gradients(v, grid))

    def acceleration(self, n, v, grid, forcing=None, t=0.0):
        """Solve M a = div B - Mdot v + f + lambda*n with n.a=-v.v."""
        xp = self.xp
        n, v = self.retract(n, v, grid)
        d, dv = self.jets(n, v, grid)
        gram = xp.einsum('...ia,...ib->...ab', d, d)
        trace = xp.sum(d * d, axis=(-2, -1))
        mass = (1 + trace)[..., None, None] * xp.eye(3) - gram
        mass_dot = (2 * xp.sum(d * dv, axis=(-2, -1)))[..., None, None] * xp.eye(3)
        mass_dot -= xp.einsum('...ia,...ib->...ab', dv, d) + xp.einsum('...ia,...ib->...ab', d, dv)
        _, q = self.currents(d, v)
        rhs = self.sigma_terms(n, grid)[1]
        rhs += sum((self.derivative(-0.5 * q[..., i, :] - d[..., i, :], h, i, grid.boundary) for i, h in enumerate(grid.spacing)))
        rhs -= xp.einsum('...ab,...b->...a', mass_dot, v)
        if forcing is not None:
            rhs += self.force(forcing, grid, t)
        solved = self.solve(mass, xp.stack((rhs, n), axis=-1))
        a0 = solved[..., 0]
        normal = solved[..., 1]
        lam = (-xp.sum(v * v, axis=-1) - xp.sum(n * a0, axis=-1)) / xp.sum(n * normal, axis=-1)
        a = a0 + lam[..., None] * normal
        if grid.boundary == 'fixed':
            a[self.fixed_mask(grid)] = 0
        return (v, a)

    def step(self, n, v, grid, dt, t=0.0, forcing=None):
        """Classical RK4 of a smooth constraint extension; retract accepted endpoint."""
        xp = self.xp
        if not xp.isfinite(dt) or dt <= 0:
            raise ValueError('Positive dt required')
        k1 = self.acceleration(n, v, grid, forcing, t)
        k2 = self.acceleration(n + dt * 0.5 * k1[0], v + dt * 0.5 * k1[1], grid, forcing, t + dt * 0.5)
        k3 = self.acceleration(n + dt * 0.5 * k2[0], v + dt * 0.5 * k2[1], grid, forcing, t + dt * 0.5)
        k4 = self.acceleration(n + dt * k3[0], v + dt * k3[1], grid, forcing, t + dt)
        raw_n = n + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        raw_v = v + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        nn, vv = self.retract(raw_n, raw_v, grid)
        return (nn, vv, {'n_projection_max': float(xp.max(xp.linalg.norm(nn - raw_n, axis=-1))), 'v_projection_max': float(xp.max(xp.linalg.norm(vv - raw_v, axis=-1)))})

    def densities(self, n, v, grid, include_stress=True):
        """Densities of the same discrete action, no cell-energy substitution."""
        xp = self.xp
        d = self.gradients(n - self.north, grid)
        p, q = self.currents(d, v, spatial=include_stress)
        ell = self.lagrangian(d, v)
        e = K * (xp.sum(p * v, axis=-1) - ell)
        hamiltonian = e + K * (self.sigma_terms(n, grid)[0] - xp.sum(d * d, axis=(-2, -1)))
        momentum = -K * xp.sum(p[..., None, :] * d, axis=-1)
        result = {'energy_density': e, 'hamiltonian_density': hamiltonian, 'energy_flux': momentum, 'field': n, 'field_rate': v}
        if include_stress:
            stress = -K * xp.einsum('...ia,...ja->...ij', q, d)
            for i in range(3):
                stress[..., i, i] += K * ell
            result['stress'] = stress
        return result

    def diagnostics(self, n, v, grid, forcing=None, t=0.0):
        xp = self.xp
        data = self.densities(n, v, grid, include_stress=False)
        dv = np.prod(grid.spacing)
        e = float(xp.sum(data['hamiltonian_density']) * dv)
        ce = float(xp.sum(data['energy_density']) * dv)
        points = self.points(grid)
        centroid = xp.sum(points * data['energy_density'][..., None], axis=(0, 1, 2)) * dv / ce if ce else xp.zeros(3)
        rms = float(xp.sqrt(max(0, float(xp.sum(xp.sum((points - centroid) ** 2, axis=-1) * data['energy_density']) * dv / ce)))) if ce else 0.0
        power = 0.0
        force = xp.zeros(3)
        if forcing is not None:
            f = self.force(forcing, grid, t)
            power = float(2 * K * xp.sum(f * v) * dv)
            force = -2 * K * xp.sum(f[..., None, :] * self.gradients(n - self.north, grid), axis=(0, 1, 2, 4)) * dv
        return {'energy': e, 'continuum_energy': ce, 'momentum': (xp.sum(data['energy_flux'], axis=(0, 1, 2)) * dv).tolist(), 'unit_error': float(xp.max(abs(xp.linalg.norm(n, axis=-1) - 1))), 'tangency_error': float(xp.max(abs(xp.sum(n * v, axis=-1)))), 'centroid': centroid.tolist(), 'rms_radius': rms, 'source_power': power, 'source_force': force.tolist(), 'boundary': 'periodic' if grid.boundary == 'periodic' else 'fixed_reflecting'}

    def currents(self, d, velocity, spatial=True):
        """Return (p,q_i)/K = derivatives of L/K with respect to time/spatial jets."""
        xp = self.xp
        d = xp.asarray(d, dtype=float)
        velocity = xp.asarray(velocity, dtype=float)
        vv = xp.sum(velocity * velocity, axis=-1)
        norms = xp.sum(d * d, axis=-1)
        vd = xp.sum(d * velocity[..., None, :], axis=-1)
        p = 2 * (velocity * (1 + xp.sum(norms, axis=-1))[..., None] - xp.sum(vd[..., None] * d, axis=-2))
        if not spatial:
            return p,None
        q = -2 * d + 2 * (vv[..., None, None] * d - vd[..., None] * velocity[..., None, :])
        for i in range(3):
            for j in range(3):
                if i != j:
                    dot = xp.sum(d[..., i, :] * d[..., j, :], axis=-1)
                    q[..., i, :] -= 2 * (norms[..., j, None] * d[..., i, :] - dot[..., None] * d[..., j, :])
        return (p, q)

    def lagrangian(self, d, velocity):
        """L/K for spatial jets (...,3,3), time jet (...,3); signature +---."""
        xp = self.xp
        d = xp.asarray(d, dtype=float)
        velocity = xp.asarray(velocity, dtype=float)
        e2 = xp.sum(d * d, axis=(-2, -1))
        e4 = sum((xp.sum(xp.cross(d[..., i, :], d[..., j, :]) ** 2, axis=-1) for i, j in ((0, 1), (0, 2), (1, 2))))
        kinetic = xp.sum(velocity * velocity, axis=-1)
        kinetic += xp.sum(xp.cross(velocity[..., None, :], d) ** 2, axis=(-2, -1))
        return kinetic - e2 - e4

class CUDATime(ArrayTime):
    def __init__(self):
        try:
            import cupy as cp
        except ImportError as error:
            raise RuntimeError('Install the frozen gpu extra; CUDA execution has no CPU fallback') from error
        if cp.cuda.runtime.getDeviceCount() < 1:
            raise RuntimeError('No accessible CUDA device; no CPU fallback')
        super().__init__(cp)

    def solve(self, mass, rhs):
        # Bound cuSOLVER workspace rather than asking for millions of systems
        # in a single call. Each solve is the same independent 3x3/2-RHS problem.
        import cupyx
        cp = self.xp
        flat = mass.reshape(-1,3,3)
        values = rhs.reshape(-1,3,2)
        answer = cp.empty_like(values)
        with cupyx.errstate(linalg='raise'):
            for start in range(0,len(flat),65536):
                answer[start:start+65536] = cp.linalg.solve(flat[start:start+65536],values[start:start+65536])
        return answer.reshape(rhs.shape)

    def identity(self):
        cp = self.xp
        device = cp.cuda.Device()
        info = cp.cuda.runtime.getDeviceProperties(device.id)
        name = info['name']
        return {'execution_backend': self.execution_kind, 'device_id': device.id,
                'device_name': name.decode() if isinstance(name,bytes) else name,
                'compute_capability': device.compute_capability,
                'cupy': cp.__version__, 'cuda_runtime': cp.cuda.runtime.runtimeGetVersion(),
                'cuda_driver': cp.cuda.runtime.driverGetVersion(), 'precision': 'float64'}
