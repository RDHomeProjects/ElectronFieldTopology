"""Explicit periodic Coulomb and unbounded Bateman potentials; Apache-2.0."""
import numpy as np
from scipy.fft import fftn,ifftn,fftfreq


def wavevectors(n,spacing):
    if not isinstance(n,int) or n<5 or n%2!=1 or not np.isfinite(spacing) or spacing<=0:
        raise ValueError('odd n>=5 and positive finite spacing required')
    axis=2*np.pi*fftfreq(n,d=spacing)
    return np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1)


def real_grid(field):
    f=np.asarray(field)
    if f.ndim!=4 or f.shape[-1]!=3 or len(set(f.shape[:3]))!=1 or not np.isrealobj(f) or not np.isfinite(f).all():
        raise ValueError('finite real cubic vector grid required')
    return f


def remove_mean(field):
    """Explicit operation: caller must retain the returned removed mean."""
    f=real_grid(field);mean=np.mean(f,axis=(0,1,2))
    return f-mean,mean


def coulomb_potential(field,spacing):
    """Reject mean/divergence; return zero-mean periodic A with curl A=field."""
    f=real_grid(field);n=f.shape[0];k=wavevectors(n,spacing);hat=fftn(f,axes=(0,1,2));k2=np.sum(k*k,axis=-1)
    rms=float(np.sqrt(np.mean(np.sum(f*f,axis=-1))));mean=np.mean(f,axis=(0,1,2))
    mean_relative=float(np.linalg.norm(mean)/rms) if rms else 0.
    norm=float(np.sum(np.abs(hat)**2));dot=np.sum(k*hat,axis=-1)
    divergence_relative=float(np.sqrt(np.sum(np.abs(dot)**2)/norm)) if norm else 0.
    if mean_relative>1e-12:raise ValueError('nonzero mean has no periodic curl potential; remove and report it explicitly')
    if divergence_relative>1e-10:raise ValueError('longitudinal input rejected; no hidden projection')
    ahat=np.divide(1j*np.cross(k,hat),k2[...,None],out=np.zeros_like(hat),where=k2[...,None]!=0)
    ahat[0,0,0]=0
    recovered=1j*np.cross(k,ahat)
    reconstruction=float(np.sqrt(np.sum(np.abs(recovered-hat)**2)/norm)) if norm else 0.
    arnorm=float(np.sum(np.abs(ahat)**2))
    coulomb=float(np.sqrt(np.sum(np.abs(np.sum(k*ahat,axis=-1))**2)/arnorm)) if arnorm else 0.
    return ifftn(ahat,axes=(0,1,2)).real,{'relative_mean':mean_relative,
        'relative_divergence':divergence_relative,'relative_curl_reconstruction_error':reconstruction,
        'relative_coulomb_divergence':coulomb}


def periodic_helicities(e,b,spacing):
    a,ad=coulomb_potential(b,spacing);c,cd=coulomb_potential(e,spacing)
    hm=float(spacing**3*np.sum(a*b));he=float(spacing**3*np.sum(c*e))
    return {'magnetic_helicity':hm,'electric_helicity':he,'optical_helicity':(hm+he)/2,
        'integral_e_dot_b':float(spacing**3*np.sum(e*b)),'magnetic_potential_checks':ad,'electric_potential_checks':cd}


def bateman_potentials(points,time=0.):
    """V=alpha grad beta=C+iA; unbounded gauge, not generally Coulomb."""
    p=np.asarray(points,dtype=float)
    if p.shape[-1:]!=(3,) or not np.isfinite(p).all() or not np.isscalar(time) or not np.isreal(time) or not np.isfinite(time):
        raise ValueError('finite real points (...,3) and scalar time required')
    x,y,z=np.moveaxis(p,-1,0);r2=np.sum(p*p,axis=-1)
    d=r2-(time-1j)**2;alpha=(r2-time*time-1+2j*z)/d;num=2*(x-1j*y)
    grad_beta=(np.array([2,-2j,0])*d[...,None]-2*p*num[...,None])/d[...,None]**2
    v=alpha[...,None]*grad_beta
    return v.imag,v.real  # magnetic A, electric C
