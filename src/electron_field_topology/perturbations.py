"""Classified real Maxwell perturbations and diagnostics; Apache-2.0."""
import numpy as np
from scipy.fft import fftn,ifftn,fftfreq
from .diagnostics import energy_flow


def duality(e,b,angle):
    """F'=exp(i angle)F for F=E+iB; constant real angle."""
    if not np.isscalar(angle) or not np.isreal(angle) or not np.isfinite(angle):
        raise ValueError('finite real angle required')
    return np.cos(angle)*e-np.sin(angle)*b,np.sin(angle)*e+np.cos(angle)*b


def invariants(e,b):
    return np.sum(e*b,axis=-1),np.sum(e*e-b*b,axis=-1)/2


def null_scores(e,b):
    """RMS invariants / RMS positive energy; never divide pointwise by tails."""
    u,_=energy_flow(e,b);a,c=invariants(e,b);denom=np.mean(u*u)
    if denom<=0:raise ValueError('nonzero field required')
    return {'e_dot_b_rms_over_u_rms':float(np.sqrt(np.mean(a*a)/denom)),
            'half_e2_minus_b2_rms_over_u_rms':float(np.sqrt(np.mean(c*c)/denom)),
            'combined_null_score':float(np.sqrt(np.mean(a*a+c*c)/denom))}


def invariant_change(e,b,base_e,base_b):
    a,c=invariants(e,b);ar,cr=invariants(base_e,base_b);u,_=energy_flow(base_e,base_b)
    return float(np.sqrt(np.mean((a-ar)**2+(c-cr)**2)/np.mean(u*u)))


def seeded_gaussian(points,spacing,seed,width,mode='curl'):
    """Spectral curl of g*a, or inadmissible gradient negative control.

    g is a product of three-image Gaussian sums; the FFT representation is
    periodic. Random center/orientation depend only on the declared seed.
    """
    p=np.asarray(points)
    if p.ndim!=4 or p.shape[-1]!=3 or len(set(p.shape[:3]))!=1 or p.shape[0]%2!=1:
        raise ValueError('odd cubic vector grid required')
    if not np.isfinite(spacing) or spacing<=0 or not np.isfinite(width) or width<=0 or mode not in ['curl','gradient']:
        raise ValueError('positive spacing/width and curl or gradient required')
    rng=np.random.default_rng(seed);center=rng.uniform(-.5,.5,3);axis=rng.normal(size=3);axis/=np.linalg.norm(axis)
    n=p.shape[0];period=n*spacing;g=np.ones(p.shape[:-1])
    for j in range(3):
        g*=sum(np.exp(-(p[...,j]-center[j]+image*period)**2/(2*width**2)) for image in [-1,0,1])
    kaxis=2*np.pi*fftfreq(n,d=spacing);k=np.stack(np.meshgrid(kaxis,kaxis,kaxis,indexing='ij'),axis=-1)
    if mode=='curl':hat=1j*np.cross(k,fftn(g[...,None]*axis,axes=(0,1,2)))
    else:hat=1j*k*fftn(g,axes=(0,1,2))[...,None]
    e=ifftn(hat,axes=(0,1,2)).real
    return e,np.zeros_like(e),{'seed':seed,'width':width,'center':center.tolist(),'axis':axis.tolist(),'mode':mode,'images_per_axis':3}


def fourier_cube(spectrum,spacing,axis):
    """Evaluate the nodal trigonometric interpolant on a fixed physical cube.

    FFT indices start at the grid's -floor(N/2)*dx coordinate. This origin
    offset must enter the phases; no spatial interpolation of intensities.
    """
    n=spectrum.shape[0];x=np.asarray(axis,dtype=float)
    if spectrum.shape!=(n,n,n,3) or x.ndim!=1 or not np.isfinite(x).all() or spacing<=0:
        raise ValueError('cubic vector spectrum, positive spacing and finite axis required')
    k=2*np.pi*fftfreq(n,d=spacing)
    phase=np.exp(1j*(x[:,None]+(n//2)*spacing)*k[None,:])/n
    a=np.einsum('pi,ijkv->pjkv',phase,spectrum,optimize=True)
    a=np.einsum('qj,pjkv->pqkv',phase,a,optimize=True)
    return np.einsum('rk,pqkv->pqrv',phase,a,optimize=True).real


def cube_energy(e,b,axis):
    u,_=energy_flow(e,b)
    for _ in range(3):u=np.trapezoid(u,x=axis,axis=0)
    return float(u)
