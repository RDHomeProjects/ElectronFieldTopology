"""Unchanged tail diagnostic, with canonical fixed-coordinate profile planes. Apache-2.0."""
import numpy as np
from .sf_checkpoints import timestamp
from .sf_time import densities
from .sf_readmission import stationarity,admitted
from .sf_time_run import state_sha
from .sf_tail_domain import need,centred_slice,shell_mask
from .skyrme import NORTH

def fixed_coordinate_max(grid,spacing):
    need(all(abs(h-spacing)<1e-14 for h in grid.spacing),'Canonical analysis spacing differs')
    axes=[abs((np.arange(n)-(n-1)/2)*spacing) for n in grid.shape]
    return np.maximum(np.maximum(axes[0][:,None,None],axes[1][None,:,None]),axes[2][None,None,:])

def density_summary(e,grid,width,common_nodes,profile,coordinate_spacing):
    """Energy integrated over explicit fixed/moving laboratory regions."""
    need(e.shape==grid.shape and np.isfinite(e).all() and np.min(e)>=-1e-14,'Invalid continuum energy density')
    dv=float(np.prod(grid.spacing));total=float(np.sum(e)*dv);xyz=grid.points();shell=shell_mask(grid,width)
    energy=float(np.sum(e[shell])*dv);common=centred_slice(grid.shape[0],common_nodes);fixed_radius=fixed_coordinate_max(grid,coordinate_spacing)
    centroid=np.sum(xyz*e[...,None],axis=(0,1,2))*dv/total if total>0 else np.zeros(3)
    radii=np.linalg.norm(xyz-centroid,axis=-1);order=np.argsort(radii.ravel());cum=np.cumsum(e.ravel()[order])
    def radius(f):return float(radii.ravel()[order[min(int(np.searchsorted(cum,f*np.sum(e))),len(order)-1)]]) if total>0 else None
    return {'continuum_energy':total,'shell_energy':energy,'shell_fraction':energy/total if total>0 else None,
        'shell_width':width,'shell_inner_half_lengths':(np.asarray(grid.lengths)/2-width).tolist(),
        'common_cube_nodes':common_nodes,'common_cube_side':(common_nodes-1)*grid.spacing[0],
        'common_cube_energy':float(np.sum(e[common])*dv),'centroid':centroid.tolist(),'radius_95':radius(.95),'radius_99':radius(.99),
        'outside_original_inner_cube_energy':float(np.sum(e[fixed_radius>=6.])*dv),
        'outside_original_box_energy':float(np.sum(e[fixed_radius>8.])*dv),
        'fixed_region_profile':[{'cube_half_width':a,'energy_outside':float(np.sum(e[fixed_radius>=a])*dv)} for a in profile if a<=min(grid.lengths)/2]}

def measure(n,grid,q,c):
    v=np.zeros_like(n);m=stationarity(n,grid);d=densities(n,v,grid)
    s=density_summary(d['energy_density'],grid,c['shell_width'],c['common_nodes'],c['profile_half_widths'],c['spacing'])
    s.update(recorded_at=timestamp(),stationarity=m,discrete_hamiltonian=float(np.sum(d['hamiltonian_density'])*np.prod(grid.spacing)),
        integrated_stress=(np.sum(d['stress'],axis=(0,1,2))*np.prod(grid.spacing)).tolist(),
        fixed_field_max=float(np.max(abs(n[grid.fixed_mask()]-NORTH))),state_sha256=state_sha(n,v),
        tail_gate_pass=s['shell_fraction'] is not None and s['shell_fraction']<=c['tail_fraction_limit'],
        preparation_stationarity_pass=admitted(m,q,c['readmission']))
    return s
