"""Passive Lorentz transforms in c=1, eta=(-,+,+,+); Apache-2.0.

Events are (t,x,y,z). F contravariant has F[0,i]=E_i and F[i,j]=eps_ijk B_k.
Vector field transformation is independent of the tensor-path test reference.
"""
import numpy as np
from .fields import hopfion


def velocity_vector(velocity):
    if np.iscomplexobj(velocity):
        raise ValueError('velocity must be real')
    v=np.asarray(velocity,dtype=float)
    if v.shape!=(3,) or not np.isfinite(v).all() or np.dot(v,v)>=1:
        raise ValueError('finite velocity shape (3,) with norm <1 required')
    return v


def lorentz_matrix(velocity):
    """Passive x'=Lambda(v)x, with t'=gamma(t-v dot x)."""
    v=velocity_vector(velocity)
    gamma=1/np.sqrt(1-np.dot(v,v))
    matrix=np.eye(4)
    matrix[0,0]=gamma
    matrix[0,1:]=matrix[1:,0]=-gamma*v
    matrix[1:,1:]+=gamma**2/(gamma+1)*np.outer(v,v)
    return matrix


def transform_events(events, matrix):
    events=np.asarray(events,dtype=float)
    matrix=np.asarray(matrix,dtype=float)
    if events.shape[-1:]!=(4,) or matrix.shape!=(4,4) or not np.isfinite(events).all() or not np.isfinite(matrix).all():
        raise ValueError('finite events (...,4) and matrix (4,4) required')
    return np.einsum('ij,...j->...i',matrix,events)


def field_tensor(electric,magnetic):
    e,b=np.broadcast_arrays(np.asarray(electric,dtype=float),np.asarray(magnetic,dtype=float))
    if e.shape[-1:]!=(3,) or not np.isfinite(e).all() or not np.isfinite(b).all():
        raise ValueError('finite fields (...,3) required')
    tensor=np.zeros(e.shape[:-1]+(4,4))
    tensor[...,0,1:]=e;tensor[...,1:,0]=-e
    for i,j,k in [(1,2,2),(2,3,0),(3,1,1)]:
        tensor[...,i,j]=b[...,k];tensor[...,j,i]=-b[...,k]
    return tensor


def fields_from_tensor(tensor):
    f=np.asarray(tensor,dtype=float)
    if f.shape[-2:]!=(4,4) or not np.isfinite(f).all():
        raise ValueError('finite tensor (...,4,4) required')
    return f[...,0,1:],np.stack((f[...,2,3],f[...,3,1],f[...,1,2]),axis=-1)


def transform_fields(electric,magnetic,velocity):
    """Fields at the same event, expressed in the moving observer's frame."""
    v=velocity_vector(velocity)
    e,b=np.broadcast_arrays(np.asarray(electric,dtype=float),np.asarray(magnetic,dtype=float))
    if e.shape[-1:]!=(3,) or not np.isfinite(e).all() or not np.isfinite(b).all():
        raise ValueError('finite fields (...,3) required')
    gamma=1/np.sqrt(1-np.dot(v,v));factor=gamma**2/(gamma+1)
    return (gamma*(e+np.cross(v,b))-factor*np.sum(e*v,axis=-1)[...,None]*v,
            gamma*(b-np.cross(v,e))-factor*np.sum(b*v,axis=-1)[...,None]*v)


def boosted_hopfion(points,time,velocity):
    """Evaluate at target (primed) coordinates, using inverse event mapping."""
    points=np.asarray(points,dtype=float)
    if points.shape[-1:]!=(3,):raise ValueError('points (...,3) required')
    if np.iscomplexobj(time):raise ValueError('time must be real')
    time=np.asarray(time,dtype=float)
    shape=np.broadcast_shapes(points.shape[:-1],time.shape)
    events=np.concatenate((np.broadcast_to(time,shape)[...,None],np.broadcast_to(points,shape+(3,))),axis=-1)
    v=velocity_vector(velocity)
    source=transform_events(events,lorentz_matrix(-v))
    e,b=hopfion(source[...,1:],source[...,0])
    return transform_fields(e,b,v)
