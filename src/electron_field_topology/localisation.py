"""Energy moments on declared slices; classical observables, Apache-2.0."""
import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.optimize import minimize
from .diagnostics import energy_flow, sphere_rule


def stress_energy(electric, magnetic):
    """Contravariant symmetric T, eta=(-+++), c=epsilon_0=mu_0=1."""
    e,b=np.broadcast_arrays(np.asarray(electric,dtype=float),np.asarray(magnetic,dtype=float))
    if e.shape[-1:]!=(3,) or not np.isfinite(e).all() or not np.isfinite(b).all():
        raise ValueError('finite vector fields required')
    u,s=energy_flow(e,b)
    tensor=np.zeros(e.shape[:-1]+(4,4))
    tensor[...,0,0]=u;tensor[...,0,1:]=s;tensor[...,1:,0]=s
    tensor[...,1:,1:]=u[...,None,None]*np.eye(3)-e[..., :,None]*e[...,None,:]-b[..., :,None]*b[...,None,:]
    return tensor


def energy_moments(points,weights,electric,magnetic,origin=(0,0,0)):
    """Positive-weight moments; origin affects angular momentum only.

    Centroid/covariance always use the supplied coordinates. This function does
    not assume the fields solve Maxwell equations or that weights cover R^3.
    """
    p=np.asarray(points,dtype=float);w=np.asarray(weights,dtype=float)
    e=np.asarray(electric,dtype=float);b=np.asarray(magnetic,dtype=float)
    a=np.asarray(origin,dtype=float)
    if p.shape[-1:]!=(3,) or e.shape!=p.shape or b.shape!=p.shape or w.shape!=p.shape[:-1] or a.shape!=(3,):
        raise ValueError('matching points/fields (...,3), weights (...) and origin (3,) required')
    if not all(np.isfinite(x).all() for x in [p,w,e,b,a]) or np.any(w<0):
        raise ValueError('finite data and nonnegative weights required')
    p=p.reshape(-1,3);w=w.reshape(-1);e=e.reshape(-1,3);b=b.reshape(-1,3)
    u,s=energy_flow(e,b);wu=w*u;energy=np.sum(wu)
    if energy<=0:raise ValueError('positive total energy required')
    centroid=np.sum(wu[:,None]*p,axis=0)/energy
    centered=p-centroid
    covariance=np.einsum('n,ni,nj->ij',wu,centered,centered)/energy
    return {'energy':float(energy),'momentum':np.sum(w[:,None]*s,axis=0).tolist(),
        'centroid':centroid.tolist(),'covariance':covariance.tolist(),
        'central_rms_squared':float(np.trace(covariance)),
        'raw_r_squared_mean':float(np.sum(wu*np.sum(p*p,axis=-1))/energy),
        'r_dot_flow_integral':float(np.sum(w*np.sum(p*s,axis=-1))),
        'angular_momentum_about_origin':np.sum(w[:,None]*np.cross(p-a,s),axis=0).tolist(),
        'angular_momentum_about_centroid':np.sum(w[:,None]*np.cross(centered,s),axis=0).tolist(),
        'angular_origin':a.tolist()}


def all_space_rule(order,radial_order=None):
    """Radial r=s/(1-s), angular Gauss mu / periodic phi; no outer cutoff."""
    if not isinstance(order,int) or order<2:raise ValueError('integer order >=2 required')
    radial_order=order if radial_order is None else radial_order
    if not isinstance(radial_order,int) or radial_order<2:raise ValueError('integer radial order >=2 required')
    normals,angular,_=sphere_rule(1,order,volume=False)
    x,w=leggauss(radial_order);s=(x+1)/2;r=s/(1-s)
    radial=w/2*r*r/(1-s)**2
    return r[:,None,None,None]*normals,radial[:,None,None]*angular


def integrate_moments(field,time,order,radius=None,center=(0,0,0),origin=(0,0,0),radial_order=None):
    if radius is None:
        if np.any(np.asarray(center)!=0):raise ValueError('all-space rule uses coordinate origin')
        p,w=all_space_rule(order,radial_order)
    else:p,w=sphere_rule(radius,order,center)
    return energy_moments(p,w,*field(p,time),origin=origin)


def density_peak(field,time,half_extent,grid_count):
    """Bounded grid + four local starts; a candidate, no global certificate."""
    if not np.isfinite(half_extent) or half_extent<=0 or not isinstance(grid_count,int) or not 5<=grid_count<=65:
        raise ValueError('positive extent and grid count 5..65 required')
    x=np.linspace(-half_extent,half_extent,grid_count)
    points=np.stack(np.meshgrid(x,x,x,indexing='ij'),axis=-1).reshape(-1,3)
    u,_=energy_flow(*field(points,time))
    candidates=np.argsort(u)[-4:]
    def objective(p):return -float(energy_flow(*field(p,time))[0])
    results=[minimize(objective,points[i],method='L-BFGS-B',bounds=[(-half_extent,half_extent)]*3,
                      options={'ftol':1e-14,'gtol':1e-9,'maxiter':200}) for i in candidates]
    best=min(results,key=lambda r:r.fun)
    return {'grid_count':grid_count,'half_extent':half_extent,'position':best.x.tolist(),
        'energy_density':float(-best.fun),'selected_optimizer_success':bool(best.success),
        'all_optimizer_success':[bool(r.success) for r in results],
        'distance_to_search_boundary':float(half_extent-np.max(np.abs(best.x))),
        'method':'bounded Cartesian grid plus four L-BFGS-B starts; candidate maximum'}
