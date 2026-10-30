"""Source-free periodic Fourier Maxwell evolution (PSATD); Apache-2.0.

The engine knows nothing about Hopfions. Numpy forward FFT uses exp(-ikx).
All fields are collocated, c=1; odd grids avoid a real Nyquist ambiguity.
"""
import numpy as np
from scipy.fft import fftn, ifftn, fftfreq


class FourierMaxwell:
    def __init__(self, electric, magnetic, spacing, project=True):
        e, b = np.asarray(electric), np.asarray(magnetic)
        if e.shape != b.shape or e.ndim != 4 or e.shape[-1] != 3:
            raise ValueError('matching cubic vector grids required')
        n = e.shape[0]
        if e.shape[:3] != (n,n,n) or n < 5 or n % 2 == 0:
            raise ValueError('odd cubic grid with n>=5 required')
        if not np.isfinite(spacing) or spacing <= 0:
            raise ValueError('positive finite spacing required')
        if not np.isrealobj(e) or not np.isrealobj(b) or not np.isfinite(e).all() or not np.isfinite(b).all():
            raise ValueError('finite real initial fields required')
        self.spacing = float(spacing)
        self.n = n
        axis = 2*np.pi*fftfreq(n, d=spacing)
        self.k = np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1)
        self.k2 = np.sum(self.k*self.k,axis=-1)
        self.kmag = np.sqrt(self.k2)
        self.ehat = fftn(e, axes=(0,1,2))
        self.bhat = fftn(b, axes=(0,1,2))
        self.initial_projection_relative_l2 = 0.0
        if project:
            el, bl = self.longitudinal(self.ehat), self.longitudinal(self.bhat)
            norm = np.sum(np.abs(self.ehat)**2+np.abs(self.bhat)**2)
            self.initial_projection_relative_l2 = float(np.sqrt(np.sum(np.abs(el)**2+np.abs(bl)**2)/norm)) if norm else 0.0
            self.ehat -= el
            self.bhat -= bl
        self.time = 0.0

    def longitudinal(self, f):
        dot = np.sum(self.k*f,axis=-1)
        ratio = np.divide(dot,self.k2,out=np.zeros_like(dot),where=self.k2!=0)
        return self.k*ratio[...,None]

    def advance(self, dt):
        if not np.isscalar(dt) or not np.isreal(dt) or not np.isfinite(dt):
            raise ValueError('finite real dt required')
        c = np.cos(self.kmag*dt)[...,None]
        s = (dt*np.sinc(self.kmag*dt/np.pi))[...,None]
        e, b = self.ehat, self.bhat
        # Longitudinal components and the k=0 mean remain unchanged.
        self.ehat = c*e + 1j*s*np.cross(self.k,b) + (1-c)*self.longitudinal(e)
        self.bhat = c*b - 1j*s*np.cross(self.k,e) + (1-c)*self.longitudinal(b)
        self.time += dt

    def fields(self):
        return (ifftn(self.ehat,axes=(0,1,2)).real,
                ifftn(self.bhat,axes=(0,1,2)).real)

    def divergence_max(self):
        return max(float(np.max(np.abs(ifftn(1j*np.sum(self.k*f,axis=-1)))))
                   for f in (self.ehat,self.bhat))

    def energy(self):
        # Parseval with numpy/scipy's default FFT normalisation.
        return float(self.spacing**3/(2*self.n**3)*np.sum(np.abs(self.ehat)**2+np.abs(self.bhat)**2))


def grid(n, half_extent):
    if not isinstance(n,int) or n<5 or n%2==0 or not np.isfinite(half_extent) or half_extent<=0:
        raise ValueError('odd n>=5 and positive half extent required')
    dx = 2*half_extent/n
    axis = (np.arange(n)-n//2)*dx
    return np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1), dx


def cube_diagnostics(e, b, spacing, half_cells):
    """Nodal trapezoidal energy and six outward Poynting fluxes.

    Interior cube faces run through grid nodes, not the outer periodic seam.
    """
    n = e.shape[0]
    if not 1 <= half_cells < n//2:
        raise ValueError('cube must lie strictly inside periodic domain')
    c = n//2
    sl = slice(c-half_cells,c+half_cells+1)
    ee,bb = e[sl,sl,sl],b[sl,sl,sl]
    u = np.sum(ee*ee+bb*bb,axis=-1)/2
    flow = np.cross(ee,bb)
    def trap(a):
        while a.ndim:
            a = np.trapezoid(a,dx=spacing,axis=0)
        return float(a)
    faces=[]
    for ax in range(3):
        for index,sign in [(0,-1),(-1,1)]:
            faces.append(sign*trap(np.take(flow[...,ax],index,axis=ax)))
    return {'energy':trap(u),'outward_flux':sum(faces),'face_fluxes':faces,
            'half_extent':float(half_cells*spacing)}
