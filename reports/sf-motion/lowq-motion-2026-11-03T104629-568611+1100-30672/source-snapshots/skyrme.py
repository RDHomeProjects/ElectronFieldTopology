"""Jennings (2015) static unit-vector energy; no physical-time dynamics.

Source and discrete-adjoint derivation: docs/models/SF-J2015-static.md.
"""
import ctypes
from pathlib import Path
import subprocess
import numpy as np
from scipy.fft import fftn, ifftn, fftfreq

K=1/(32*np.pi**2*np.sqrt(2))
NORTH=np.array([0.,0.,1.])


def normalize(v):
    v=np.asarray(v,dtype=float)
    r=np.linalg.norm(v,axis=-1,keepdims=True)
    if not np.isfinite(v).all() or np.min(r)<1e-12:raise ValueError('finite nonzero field required')
    return v/r


def derivative(u,h,axis):
    """Fourth-order centred derivative, constant-zero extension of input."""
    pad=[(0,0)]*u.ndim;pad[axis]=(2,2);v=np.pad(u,pad)
    def at(o):
        sl=[slice(None)]*u.ndim;sl[axis]=slice(2+o,2+o+u.shape[axis]);return v[tuple(sl)]
    return (at(-2)-8*at(-1)+8*at(1)-at(2))/(12*h)


def numpy_energy(u,h):
    """Independent array implementation, including exact discrete transpose."""
    d=[]
    for axis in range(3):
        v=u-NORTH;pad=[(0,0)]*4;pad[axis]=(0,1)
        v=np.pad(v,pad);d.append(np.diff(v,axis=axis)/h)
    d=np.array(d)
    e2=float(np.sum(d*d));e4=0.;p=2*d.copy()
    for i,j in [(0,1),(0,2),(1,2)]:
        c=np.cross(d[i],d[j]);e4+=float(np.sum(c*c))
        p[i]+=2*np.cross(d[j],c);p[j]+=2*np.cross(c,d[i])
    g=np.zeros_like(u)
    for axis in range(3):
        pad=[(0,0)]*4;pad[axis]=(1,0);v=np.pad(p[axis],pad)
        g-=np.diff(v,axis=axis)/h
    return np.array([e2,e4])*K*h**3,g*K*h**3


def numpy_cell_energy(u,h):
    """Independent normalized-trilinear Gauss integration (energy only)."""
    from itertools import product
    gauss=[.5-.5/np.sqrt(3),.5+.5/np.sqrt(3)];corners=list(product([0,1],repeat=3))
    e=np.zeros(2)
    for q in product(gauss,repeat=3):
        value=np.zeros((len(u)-1,)*3+(3,));dv=np.zeros((3,)+value.shape)
        for a in corners:
            piece=u[tuple(slice(bit,bit+len(u)-1) for bit in a)]
            weights=[q[i] if a[i] else 1-q[i] for i in range(3)]
            value+=np.prod(weights)*piece
            for axis in range(3):
                weight=(1 if a[axis] else -1)*np.prod([weights[i] for i in range(3) if i!=axis])/h
                dv[axis]+=weight*piece
        norm=np.linalg.norm(value,axis=-1,keepdims=True)
        if np.min(norm)<1e-8:raise ValueError('unresolved normalized interpolant')
        nn=value/norm
        d=(dv-nn*np.sum(dv*nn,axis=-1,keepdims=True))/norm
        e[0]+=np.sum(d*d)/8
        e[1]+=sum(np.sum(np.cross(d[i],d[j])**2) for i,j in [(0,1),(0,2),(1,2)])/8
    return e*K*h**3


class Energy:
    """Explicitly compiled optional C accelerator; identical lattice functional."""
    def __init__(self,n,h,build,method='cell'):
        if isinstance(n,bool) or n<9 or n>301 or n%2!=1 or not np.isfinite(h) or h<=0:
            raise ValueError('odd bounded grid and positive spacing required')
        self.n=n;self.h=h
        build=Path(build);build.mkdir(parents=True,exist_ok=True)
        source=Path(__file__).with_name('sf_energy.c');lib=build/'sf_energy.so'
        if not lib.exists() or lib.stat().st_mtime<source.stat().st_mtime:
            subprocess.run(['gcc','-O3','-std=c99','-shared','-fPIC','-fopenmp',str(source),'-o',str(lib),'-lm'],check=True)
        self.lib=ctypes.CDLL(str(lib.resolve()));ptr=ctypes.POINTER(ctypes.c_double)
        if method not in ['forward','cell']:raise ValueError('declared energy discretisation required')
        self.function=self.lib.sf_cell if method=='cell' else self.lib.sf_energy
        self.function.argtypes=[ctypes.c_int,ctypes.c_double,ptr,ptr,ptr,ptr];self.function.restype=None
        self.flux=np.empty((n,n,n,3,3));self.grad=np.empty((n,n,n,3));self.parts=np.zeros(4)
        self.reference=None;self.reference_margin=1.
    def evaluate(self,u):
        u=np.ascontiguousarray(u,dtype=np.float64)
        if u.shape!=(self.n,self.n,self.n,3) or not np.isfinite(u).all():raise ValueError('field shape/finite values')
        def ptr(a):return a.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        self.function(self.n,self.h,ptr(u),ptr(self.flux),ptr(self.grad),ptr(self.parts))
        self.minimum_interpolant_norm=float(self.parts[2])
        self.minimum_corner_cone=float(self.parts[3])
        if self.minimum_interpolant_norm<1e-8:raise ValueError('unresolved normalized interpolant')
        return self.parts[:2].copy()*K*self.h**3,self.grad.copy()*K*self.h**3
    def objective(self,raw):
        v=raw.reshape(self.n,self.n,self.n,3);r=np.linalg.norm(v,axis=-1,keepdims=True)
        if np.min(r)<1e-12:raise ValueError('normalization singularity')
        u=v/r
        if self.reference is not None:
            delta=float(np.max(np.linalg.norm(u-self.reference,axis=-1)))
            if delta>min(.2,.5*self.reference_margin):return np.inf,np.zeros_like(raw)
        parts,g=self.evaluate(u)
        if self.minimum_corner_cone<=0:return np.inf,np.zeros_like(raw)
        g=(g-u*np.sum(g*u,axis=-1,keepdims=True))/r
        for axis in range(3):
            sl=[slice(None)]*4;sl[axis]=[0,1,self.n-2,self.n-1];g[tuple(sl)]=0
        return float(sum(parts)),g.ravel()


def coordinates(n,h):
    x=(np.arange(n)-(n-1)/2)*h
    return np.stack(np.meshgrid(x,x,x,indexing='ij'),axis=-1)


def rational_field(points,kind='axial',alpha=1,beta=1,scale=1.,cutoff=None,amplitude=1.,eta=.5):
    """Eqs. 2.4–2.7/3.8 in homogeneous coordinates, with declared profile."""
    x=np.asarray(points,dtype=float);r=np.linalg.norm(x,axis=-1)
    f=2*np.arctan2(scale,r)
    if cutoff is not None:
        # Quintic taper on outer 30% of declared compact support.
        t=np.clip((r-.7*cutoff)/(.3*cutoff),0,1)
        f*=1-(10*t**3-15*t**4+6*t**5)
    sr=np.divide(np.sin(f),r,out=np.full_like(r,2/scale),where=r>1e-14)
    z1=(x[...,0]+1j*x[...,1])*sr;z0=np.cos(f)+1j*x[...,2]*sr
    if kind=='axial':p=z1**alpha;q=z0**beta
    elif kind in ['torus72','torus54','torus53','torus23']:
        a,b={'torus72':(7,2),'torus54':(5,4),'torus53':(5,3),'torus23':(2,3)}[kind]
        p=z1**alpha*z0**beta;q=z1**a+z0**b
    elif kind=='cable':
        p=z1**alpha*z0**beta
        q=z0**4-2*z1**3*z0**2-4*eta**2*z1**3*z0+z1**6-eta**4*z1**3
    else:raise ValueError('unknown declared rational family')
    p*=amplitude;den=abs(p)**2+abs(q)**2
    if np.min(den)<1e-28:raise ValueError('unresolved homogeneous common zero')
    pq=p*np.conj(q)
    return np.stack([2*pq.real,2*pq.imag,abs(q)**2-abs(p)**2],axis=-1)/den[...,None]


def set_boundary(u):
    u=u.copy()
    for axis in range(3):
        sl=[slice(None)]*4;sl[axis]=[0,1,len(u)-2,len(u)-1];u[tuple(sl)]=NORTH
    return u


def diagnostics(u,h):
    """Calibrated periodic-box Hopf quadrature; finite-grid, not integer certificate."""
    d=[derivative(u-NORTH,h,i) for i in range(3)]
    b=np.stack([np.sum(u*np.cross(d[1],d[2]),axis=-1),np.sum(u*np.cross(d[2],d[0]),axis=-1),np.sum(u*np.cross(d[0],d[1]),axis=-1)],axis=-1)
    wave=2*np.pi*fftfreq(len(u),h);k=np.stack(np.meshgrid(wave,wave,wave,indexing='ij'),axis=-1)
    k2=np.sum(k*k,axis=-1);k2[0,0,0]=1.
    bh=fftn(b,axes=(0,1,2));ah=1j*np.cross(k,bh)/k2[...,None];ah[0,0,0]=0
    a=ifftn(ah,axes=(0,1,2)).real
    q=float(np.sum(a*b)*h**3/(16*np.pi**2))
    angle=max(float(np.max(np.arccos(np.clip(np.sum(u.take(range(len(u)-1),axis=i)*u.take(range(1,len(u)),axis=i),axis=-1),-1,1)))) for i in range(3))
    return {'hopf_integral':q,'unit_error':float(np.max(abs(np.linalg.norm(u,axis=-1)-1))),
            'max_neighbour_angle':angle,'mean_topological_b':np.mean(b,axis=(0,1,2)).tolist(),
            'scope':'finite-grid Coulomb-gauge integral, not an exact integer certificate'}
