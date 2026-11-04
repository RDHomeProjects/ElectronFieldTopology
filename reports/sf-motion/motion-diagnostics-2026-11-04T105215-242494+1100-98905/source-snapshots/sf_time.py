"""Constrained nonlinear neutral SF physical-time reference. Apache-2.0.

Fourth-order skew spatial derivative of an explicit discrete action, projected RK4.
No relaxation, artificial damping, smoothing or renderer dependencies.
Equation/discretization map: docs/models/SF-physical-time.md.
"""
from dataclasses import dataclass
import numpy as np
from .sf_dynamics import currents, lagrangian
from .skyrme import K, NORTH


@dataclass(frozen=True)
class Grid:
    shape: tuple
    lengths: tuple
    boundary: str = 'periodic'

    def __post_init__(self):
        if (len(self.shape) != 3 or len(self.lengths) != 3
                or any(type(n) is not int or (n != 1 and n < 5) for n in self.shape)
                or any(not np.isfinite(l) or l <= 0 for l in self.lengths)
                or self.boundary not in ('periodic', 'fixed')):
            raise ValueError('Three positive lengths, valid node counts and explicit boundary required')
        if self.boundary == 'fixed' and any(n != 1 and n < 9 for n in self.shape):
            raise ValueError('Fixed faces need at least 9 nodes on each active axis')

    @property
    def spacing(self):
        return tuple(l/(n if self.boundary == 'periodic' or n == 1 else n-1)
                     for n, l in zip(self.shape, self.lengths))

    def points(self):
        axes = [-l/2+np.arange(n)*h for n, l, h in zip(self.shape, self.lengths, self.spacing)]
        return np.stack(np.meshgrid(*axes, indexing='ij'), axis=-1)

    def fixed_mask(self):
        mask = np.zeros(self.shape, dtype=bool)
        if self.boundary == 'fixed':
            for axis,n in enumerate(self.shape):
                if n != 1:
                    sl = [slice(None)]*3;sl[axis] = [0,1,n-2,n-1];mask[tuple(sl)] = True
        return mask


def derivative(a, h, axis, boundary='periodic'):
    """Skew-adjoint D4; fixed mode is its constant-zero-exterior restriction."""
    if a.shape[axis] == 1: return np.zeros_like(a)
    if boundary == 'periodic':
        return (np.roll(a,2,axis)-8*np.roll(a,1,axis)+8*np.roll(a,-1,axis)-np.roll(a,-2,axis))/(12*h)
    if boundary != 'fixed': raise ValueError('Unknown boundary')
    pad = [(0,0)]*a.ndim;pad[axis] = (2,2);p = np.pad(a,pad)
    def at(offset):
        sl = [slice(None)]*a.ndim;sl[axis] = slice(2+offset,2+offset+a.shape[axis]);return p[tuple(sl)]
    return (at(-2)-8*at(-1)+8*at(1)-at(2))/(12*h)


def gradients(a, grid):
    return np.stack([derivative(a,h,i,grid.boundary) for i,h in enumerate(grid.spacing)],axis=-2)


def sigma_terms(n,grid):
    """Positive fourth-order sigma action and its exact nodal force.

    E2=sum |D+u|^2+h^2/12 |D2u|^2. Its force is the standard fourth-order
    Laplacian. Unlike D4^T D4 it has no spurious zero at the Nyquist mode.
    """
    u=n-NORTH;density=np.zeros(n.shape[:-1]);force=np.zeros_like(n)
    for axis,(h,count) in enumerate(zip(grid.spacing,grid.shape)):
        if count==1:continue
        if grid.boundary=='periodic':
            def at(offset):return np.roll(u,-offset,axis)
        else:
            pad=[(0,0)]*u.ndim;pad[axis]=(2,2);p=np.pad(u,pad)
            def at(offset):
                sl=[slice(None)]*u.ndim;sl[axis]=slice(2+offset,2+offset+count);return p[tuple(sl)]
        ahead=at(1);behind=at(-1);d2=(ahead-2*u+behind)/h**2
        density+=.5*np.sum(((ahead-u)/h)**2+((u-behind)/h)**2,axis=-1)+h*h/12*np.sum(d2*d2,axis=-1)
        force+=(-at(2)+16*ahead-30*u+16*behind-at(-2))/(12*h*h)
    return density,force


def retract(n, v, grid):
    """Explicit sphere/tangent projection, including fixed north faces."""
    if (n.shape != grid.shape+(3,) or v.shape != n.shape
            or not np.isfinite(n).all() or not np.isfinite(v).all()):
        raise ValueError('Finite n/v with declared shape required')
    size = np.linalg.norm(n,axis=-1,keepdims=True)
    if np.min(size) < 1e-12: raise ValueError('Field normalization singularity')
    nn = n/size;vv = v-nn*np.sum(nn*v,axis=-1,keepdims=True)
    if grid.boundary == 'fixed':
        mask = grid.fixed_mask();nn[mask] = NORTH;vv[mask] = 0
    return nn,vv


def jets(n, v, grid):
    d = gradients(n-NORTH,grid)
    return d,gradients(v,grid)


def acceleration(n, v, grid, forcing=None, t=0.):
    """Solve M a = div B - Mdot v + f + lambda*n with n.a=-v.v."""
    n,v = retract(n,v,grid)
    d,dv = jets(n,v,grid)
    gram = np.einsum('...ia,...ib->...ab',d,d)
    trace = np.sum(d*d,axis=(-2,-1))
    mass = (1+trace)[...,None,None]*np.eye(3)-gram
    mass_dot = (2*np.sum(d*dv,axis=(-2,-1)))[...,None,None]*np.eye(3)
    mass_dot -= np.einsum('...ia,...ib->...ab',dv,d)+np.einsum('...ia,...ib->...ab',d,dv)
    _,q = currents(d,v)
    rhs = sigma_terms(n,grid)[1]
    rhs += sum(derivative(-.5*q[...,i,:]-d[...,i,:],h,i,grid.boundary) for i,h in enumerate(grid.spacing))
    rhs -= np.einsum('...ab,...b->...a',mass_dot,v)
    if forcing is not None: rhs += forcing(grid.points(),t)
    solved = np.linalg.solve(mass,np.stack((rhs,n),axis=-1))
    a0 = solved[...,0];normal = solved[...,1]
    lam = (-np.sum(v*v,axis=-1)-np.sum(n*a0,axis=-1))/np.sum(n*normal,axis=-1)
    a = a0+lam[...,None]*normal
    if grid.boundary == 'fixed': a[grid.fixed_mask()] = 0
    return v,a


def step(n, v, grid, dt, t=0., forcing=None):
    """Classical RK4 of a smooth constraint extension; retract accepted endpoint."""
    if not np.isfinite(dt) or dt <= 0: raise ValueError('Positive dt required')
    k1 = acceleration(n,v,grid,forcing,t)
    k2 = acceleration(n+dt*.5*k1[0],v+dt*.5*k1[1],grid,forcing,t+dt*.5)
    k3 = acceleration(n+dt*.5*k2[0],v+dt*.5*k2[1],grid,forcing,t+dt*.5)
    k4 = acceleration(n+dt*k3[0],v+dt*k3[1],grid,forcing,t+dt)
    raw_n = n+dt/6*(k1[0]+2*k2[0]+2*k3[0]+k4[0])
    raw_v = v+dt/6*(k1[1]+2*k2[1]+2*k3[1]+k4[1])
    nn,vv = retract(raw_n,raw_v,grid)
    return nn,vv,{'n_projection_max':float(np.max(np.linalg.norm(nn-raw_n,axis=-1))),
                  'v_projection_max':float(np.max(np.linalg.norm(vv-raw_v,axis=-1)))}


def densities(n, v, grid):
    """Densities of the same discrete action, no cell-energy substitution."""
    d = gradients(n-NORTH,grid);p,q = currents(d,v);ell = lagrangian(d,v)
    e = K*(np.sum(p*v,axis=-1)-ell)
    hamiltonian = e+K*(sigma_terms(n,grid)[0]-np.sum(d*d,axis=(-2,-1)))
    momentum = -K*np.sum(p[...,None,:]*d,axis=-1)
    stress = -K*np.einsum('...ia,...ja->...ij',q,d)
    for i in range(3): stress[...,i,i] += K*ell
    return {'energy_density':e,'hamiltonian_density':hamiltonian,
            'energy_flux':momentum,'stress':stress,'field':n,'field_rate':v}


def diagnostics(n, v, grid, forcing=None, t=0.):
    data = densities(n,v,grid);dv = np.prod(grid.spacing);e = float(np.sum(data['hamiltonian_density'])*dv)
    ce=float(np.sum(data['energy_density'])*dv)
    points = grid.points();centroid = np.sum(points*data['energy_density'][...,None],axis=(0,1,2))*dv/ce if ce else np.zeros(3)
    rms = float(np.sqrt(max(0,float(np.sum(np.sum((points-centroid)**2,axis=-1)*data['energy_density'])*dv/ce)))) if ce else 0.
    power = 0.;force = np.zeros(3)
    if forcing is not None:
        f = forcing(points,t);power = float(2*K*np.sum(f*v)*dv)
        force = -2*K*np.sum(f[...,None,:]*gradients(n-NORTH,grid),axis=(0,1,2,4))*dv
    # Fixed outer layers have zero velocity. This is a reflecting boundary, not absorption.
    return {'energy':e,'continuum_energy':ce,'momentum':(np.sum(data['energy_flux'],axis=(0,1,2))*dv).tolist(),
            'unit_error':float(np.max(abs(np.linalg.norm(n,axis=-1)-1))),
            'tangency_error':float(np.max(abs(np.sum(n*v,axis=-1)))),
            'centroid':centroid.tolist(),'rms_radius':rms,'source_power':power,
            'source_force':force.tolist(),'boundary':'periodic' if grid.boundary=='periodic' else 'fixed_reflecting'}
