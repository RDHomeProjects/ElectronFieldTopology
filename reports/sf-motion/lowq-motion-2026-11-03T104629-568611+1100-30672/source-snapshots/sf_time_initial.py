"""Event-consistent scalar-field boost of an authenticated static snapshot."""
from itertools import product
import numpy as np
from .skyrme import NORTH


def sample_static(field,h,points,axis):
    """Normalized trilinear n and its analytic partial_axis in rest coordinates."""
    if field.ndim!=4 or field.shape[-1]!=3 or len(set(field.shape[:3]))!=1:
        raise ValueError('Uniform cubic rest snapshot required')
    n=len(field);index=points/h+(n-1)/2
    outside=np.any((index<0)|(index>n-1),axis=-1)
    clipped=np.clip(index,0,n-1);base=np.minimum(np.floor(clipped).astype(int),n-2);f=clipped-base
    value=np.zeros_like(points);dv=np.zeros_like(points)
    for corner in product((0,1),repeat=3):
        weights=[f[...,i] if corner[i] else 1-f[...,i] for i in range(3)]
        piece=field[base[...,0]+corner[0],base[...,1]+corner[1],base[...,2]+corner[2]]
        value+=np.prod(weights,axis=0)[...,None]*piece
        other=[weights[i] for i in range(3) if i!=axis]
        dv+=((1 if corner[axis] else -1)*other[0]*other[1]/h)[...,None]*piece
    size=np.linalg.norm(value,axis=-1,keepdims=True)
    if np.min(size)<1e-8:raise ValueError('Boost samples an unresolved static interpolant')
    nn=value/size;deriv=(dv-nn*np.sum(nn*dv,axis=-1,keepdims=True))/size
    nn[outside]=NORTH;deriv[outside]=0
    return nn,deriv


def boosted_static(field,h,grid,beta,axis):
    if type(axis) is not int or axis not in (0,1,2) or not np.isfinite(beta) or abs(beta)>=1:
        raise ValueError('Finite |beta|<1 and one boost axis required')
    gamma=1/np.sqrt(1-beta*beta);points=grid.points();points[...,axis]*=gamma
    n,d=sample_static(field,h,points,axis)
    return n,-gamma*beta*d
