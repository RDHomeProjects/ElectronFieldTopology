"""Fresh Q3/Q4/Q7 maps for D4 preparation, not imported relaxed cell fields.

Sutcliffe arXiv:0705.1468v1, Eqs.3.1-3.4; source map in SF-candidate-survey.md.
The radial cutoff, shear and small target rotation are declared initialization
choices. They neither change the action nor constrain subsequent relaxation.
Apache-2.0.
"""
import numpy as np
from .skyrme import NORTH

def degree(seed):
    if seed['family']=='axial':return seed['alpha']*seed['beta']
    if seed['family']=='trefoil32':return 2*seed['alpha']+3*seed['beta']
    raise ValueError('Unknown seed family')

def field(points,seed):
    """Nonsingular homogeneous construction; no reference to a target energy."""
    if degree(seed)!=seed['q']:raise ValueError('Seed polynomial charge differs from Q label')
    x=np.asarray(points,dtype=np.float64).copy();scale=float(seed['scale']);cutoff=float(seed['cutoff'])
    if not 0<scale<cutoff:raise ValueError('Invalid declared seed profile')
    # A global invertible shear: x -> x-b exp[-(y²+z²)/scale²], determinant exactly1.
    x[...,0]-=seed['bend']*np.exp(-(x[...,1]**2+x[...,2]**2)/scale**2)
    r=np.linalg.norm(x,axis=-1);f=2*np.arctan2(scale,r)
    t=np.clip((r-.7*cutoff)/(.3*cutoff),0,1);f*=1-(10*t**3-15*t**4+6*t**5)
    sr=np.divide(np.sin(f),r,out=np.full_like(r,2/scale),where=r>1e-14)
    z1=(x[...,0]+1j*x[...,1])*sr;z0=np.cos(f)+1j*x[...,2]*sr
    if seed['family']=='axial':p=z1**seed['alpha'];q=z0**seed['beta']
    else:p=z1**seed['alpha']*z0**seed['beta'];q=z1**3+z0**2
    p*=seed['amplitude'];den=abs(p)**2+abs(q)**2
    if np.min(den)<1e-28:raise ValueError('Unresolved homogeneous common zero')
    pq=p*np.conj(q);n=np.stack([2*pq.real,2*pq.imag,abs(q)**2-abs(p)**2],axis=-1)/den[...,None]
    # Smooth pointwise SO(3) rotation, continuously connected to the identity.
    # It vanishes exactly in north vacuum, so does not create an exterior tail.
    omega=seed['perturbation']*(1-n[...,2])[...,None]*np.stack([np.sin(.7*x[...,0]+.3*x[...,1]),np.sin(.5*x[...,1]-.4*x[...,2]),np.sin(.3*x[...,2]+.2*x[...,0])],axis=-1)
    theta=np.linalg.norm(omega,axis=-1);cross=np.cross(omega,n)
    n=n+np.sinc(theta/np.pi)[...,None]*cross+(.5*np.sinc(theta/(2*np.pi))**2)[...,None]*np.cross(omega,cross)
    n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return n

def sampled(grid,seed):
    n=field(grid.points(),seed)
    if np.max(abs(n[grid.fixed_mask()]-NORTH))>1e-12:raise ValueError('Seed support reaches held layers; use a declared larger box')
    n[grid.fixed_mask()]=NORTH
    return n

def candidates():
    def s(id,q,family,a,b,scale,bend,amplitude=1.):
        return dict(id=id,q=q,family=family,alpha=a,beta=b,scale=scale,cutoff=8.8,bend=bend,amplitude=amplitude,perturbation=.005)
    return [s('q3-axial',3,'axial',3,1,2.8,0.),s('q3-bent',3,'axial',3,1,2.8,.65),
            s('q4-axial41',4,'axial',4,1,3.2,.2),s('q4-axial22',4,'axial',2,2,3.2,.2),
            s('q7-axial',7,'axial',7,1,4.,.25),s('q7-trefoil',7,'trefoil32',2,1,3.8,.25,2.)]
