"""Opt-in C1 normalized tensor Hermite reconstruction. Apache-2.0.

This diagnostic candidate does not replace the historical trilinear initializer.
Equation/derivative map: docs/models/SF-boost-reconstruction.md.
"""
from itertools import product
import numpy as np
from .skyrme import NORTH


def weights(t):
    """Cubic Hermite interpolant with centered nodal slopes (Catmull--Rom)."""
    return (np.stack((-.5*t+t*t-.5*t**3, 1-2.5*t*t+1.5*t**3,
                      .5*t+2*t*t-1.5*t**3, -.5*t*t+.5*t**3), axis=-1),
            np.stack((-.5+2*t-1.5*t*t, -5*t+4.5*t*t,
                      .5+4*t-4.5*t*t, -t+1.5*t*t), axis=-1))


def sample_cubic(field, grid, points, axis=0, chunk=16384):
    """Return unit field and analytic partial_axis, with constant north exterior.

    Fixed-grid samples only. C1 across exterior faces requires two north layers;
    callers report/check those layers rather than silently tapering the input.
    Overshooting cubics are normalized analytically; unresolved zeros are rejected.
    """
    if (grid.boundary != 'fixed' or field.shape != grid.shape+(3,)
            or field.dtype != np.float64 or min(grid.shape) < 4
            or not np.isfinite(field).all()):
        raise ValueError('Finite float64 three-dimensional fixed-grid field required')
    points=np.asarray(points,dtype=np.float64)
    if points.shape[-1:] != (3,) or not np.isfinite(points).all():
        raise ValueError('Finite points with three coordinates required')
    if type(axis) is not int or axis not in (0,1,2) or type(chunk) is not int or chunk<1:
        raise ValueError('One derivative axis and positive chunk size required')
    shape=points.shape;flat=points.reshape(-1,3)
    values=np.empty_like(flat);derivs=np.empty_like(flat)
    counts=np.array(grid.shape);h=np.array(grid.spacing);half=np.array(grid.lengths)/2
    for start in range(0,len(flat),chunk):
        p=flat[start:start+chunk];index=(p+half)/h
        outside=np.any((p < -half)|(p > half),axis=-1)
        clipped=np.clip(index,0,counts-1);base=np.minimum(np.floor(clipped).astype(int),counts-2)
        w,dw=weights(clipped-base)
        raw=np.zeros_like(p);dr=np.zeros_like(p)
        for corner in product(range(4),repeat=3):
            pos=base+np.array(corner)-1;valid=np.all((pos>=0)&(pos<counts),axis=-1)
            pos=np.clip(pos,0,counts-1)
            part=field[pos[:,0],pos[:,1],pos[:,2]].copy();part[~valid]=NORTH
            factors=[w[:,i,corner[i]] for i in range(3)]
            raw+=np.prod(factors,axis=0)[:,None]*part
            factors[axis]=dw[:,axis,corner[axis]]/h[axis]
            dr+=np.prod(factors,axis=0)[:,None]*part
        size=np.linalg.norm(raw,axis=-1,keepdims=True)
        if np.any(size<1e-8):raise ValueError('Unresolved zero in cubic interpolant')
        n=raw/size;d=(dr-n*np.sum(n*dr,axis=-1,keepdims=True))/size
        n[outside]=NORTH;d[outside]=0
        values[start:start+len(p)]=n;derivs[start:start+len(p)]=d
    return values.reshape(shape),derivs.reshape(shape)


def boosted_cubic(field, rest_grid, lab_grid, beta, axis, chunk=16384):
    if type(axis) is not int or axis not in (0,1,2) or not np.isfinite(beta) or abs(beta)>=1:
        raise ValueError('Finite subluminal beta required')
    gamma=1/np.sqrt(1-beta*beta);points=lab_grid.points();points[...,axis]*=gamma
    n,d=sample_cubic(field,rest_grid,points,axis,chunk)
    return n,-gamma*beta*d


def phase_comparison(observed, reference):
    """Raw and best global SO(2)-about-north errors; no spatial/orientation fit."""
    if observed.shape!=reference.shape or observed.shape[-1]!=3:
        raise ValueError('Matching internal vector arrays required')
    scale=max(float(np.linalg.norm(reference-NORTH)),1e-30)
    a=reference[...,0]+1j*reference[...,1];b=observed[...,0]+1j*observed[...,1]
    overlap=np.sum(np.conj(a)*b)
    angle=float(np.angle(overlap)) if abs(overlap)>1e-30 else 0.
    rotated=reference.copy();z=a*np.exp(1j*angle)
    rotated[...,0]=z.real;rotated[...,1]=z.imag
    return {'raw_relative_l2':float(np.linalg.norm(observed-reference)/scale),
            'phase_registered_relative_l2':float(np.linalg.norm(observed-rotated)/scale),
            'global_internal_phase_radians':angle,
            'phase_identifiable':bool(abs(overlap)>1e-30),
            'absolute_rms':float(np.sqrt(np.mean((observed-reference)**2)))}
