"""Full-grid motion diagnostics, independent of display sampling."""
import numpy as np
from scipy.fft import fftn,ifftn,fftfreq
from .sf_time import gradients,densities
from .sf_time_initial import sample_static
from .skyrme import NORTH
from .sf_readmission import cone


def hopf(n,grid):
    d=gradients(n-NORTH,grid)
    b=np.stack([np.sum(n*np.cross(d[...,1,:],d[...,2,:]),axis=-1),
                np.sum(n*np.cross(d[...,2,:],d[...,0,:]),axis=-1),
                np.sum(n*np.cross(d[...,0,:],d[...,1,:]),axis=-1)],axis=-1)
    axes=[2*np.pi*fftfreq(s,h) for s,h in zip(grid.shape,grid.spacing)]
    k=np.stack(np.meshgrid(*axes,indexing='ij'),axis=-1);k2=np.sum(k*k,axis=-1);k2[0,0,0]=1
    bh=fftn(b,axes=(0,1,2));ah=1j*np.cross(k,bh)/k2[...,None];ah[0,0,0]=0
    a=ifftn(ah,axes=(0,1,2)).real
    return {'hopf_integral':float(np.sum(a*b)*np.prod(grid.spacing)/(16*np.pi**2)),
            'minimum_corner_cone':cone(n),'mean_topological_b':np.mean(b,axis=(0,1,2)).tolist(),
            'topology_scope':'Anisotropic-grid Coulomb quadrature, periodic auxiliary inversion of a fixed-box field; not an exact integer certificate.'}


def spatial_metrics(n,v,grid,margin):
    data=densities(n,v,grid);e=data['energy_density'];total=float(np.sum(e));points=grid.points()
    centre=np.sum(points*e[...,None],axis=(0,1,2))/max(total,1e-30)
    r=np.linalg.norm(points-centre,axis=-1);order=np.argsort(r.ravel());sums=np.cumsum(e.ravel()[order])
    r99=float(r.ravel()[order[min(np.searchsorted(sums,.99*total),len(order)-1)]])
    shell=np.any(abs(points)>=np.array(grid.lengths)/2-margin,axis=-1)
    return {'continuum_energy':float(total*np.prod(grid.spacing)),'centroid':centre.tolist(),
            'radius_99':r99,'boundary_shell_width':margin,
            'boundary_shell_energy_fraction':float(np.sum(e[shell])/max(total,1e-30)),
            'initial_light_cone_clearance':float(min(np.array(grid.lengths)/2-abs(centre))-r99),**hopf(n,grid)}


def translated_reference(rest,h,grid,beta,axis,t):
    p=grid.points();p[...,axis]=(p[...,axis]-beta*t)/np.sqrt(1-beta*beta)
    return sample_static(rest,h,p,axis)[0]


def evaluate(history,n,v,grid,rest,h,beta,axis,q,margin,limits):
    rows=sorted(history,key=lambda x:x['step']);initial=rows[0];last=rows[-1];times=np.array([r['time'] for r in rows])
    centres=np.array([r['centroid'] for r in rows]);duration=float(times[-1]-times[0])
    slope=np.linalg.lstsq(np.stack([times-times[0],np.ones(len(times))],axis=-1),centres,rcond=None)[0][0] if duration else np.zeros(3)
    target=np.zeros(3);target[axis]=beta
    reference=translated_reference(rest,h,grid,beta,axis,last['time'])
    shape_error=float(np.linalg.norm(n-reference)/max(np.linalg.norm(reference-NORTH),1e-30))
    e0=initial['energy'];p0=np.array(initial['momentum']);final=spatial_metrics(n,v,grid,margin)
    energy_drift=max(abs(r['energy']-e0)/max(abs(e0),1e-30) for r in rows)
    momentum_drift=max(float(np.linalg.norm(np.array(r['momentum'])-p0)/max(abs(e0),1e-30)) for r in rows)
    speed_error=float(np.linalg.norm(slope-target));relative_speed_error=speed_error/abs(beta) if beta else None
    topo_error=abs(abs(final['hopf_integral'])-q)/q
    # Rest and moving gates differ: zero speed uses absolute model-unit drift.
    checks={'energy':energy_drift<=limits['energy_relative'],'momentum':momentum_drift<=limits['momentum_scaled'],
            'constraints':max(max(r['unit_error'],r['tangency_error']) for r in rows)<1e-10,
            'shape':shape_error<=limits['shape_relative'],
            'speed':(relative_speed_error<=limits['speed_relative'] if beta else speed_error<=limits['rest_speed_absolute']),
            'topology':topo_error<=limits['charge_relative_error'] and final['minimum_corner_cone']>0,
            'tail':final['boundary_shell_energy_fraction']<=limits['tail_fraction']}
    return {'time':float(last['time']),'fitted_centroid_velocity':slope.tolist(),'expected_velocity':target.tolist(),
            'speed_absolute_error':speed_error,'speed_relative_error':relative_speed_error,
            'translated_static_field_relative_l2':shape_error,'max_energy_relative_drift':energy_drift,
            'max_momentum_drift_over_initial_energy':momentum_drift,'final':final,'checks':checks,
            'bounded_case_gates_pass':all(checks.values()),
            'scope':'Bounded fixed-box motion diagnostics. Case pass is insufficient without temporal, spatial and domain convergence.'}
