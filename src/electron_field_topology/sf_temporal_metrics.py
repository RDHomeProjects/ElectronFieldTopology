"""Independent reporting layers for endpoint audit and fixed-region temporal comparisons. Apache-2.0."""
import numpy as np
from .sf_checkpoints import timestamp
from .sf_time import Grid,densities,step
from .sf_readmission import admitted
from .sf_tail_domain import centred_slice
from .skyrme import NORTH

def tail_band(n,v,grid,width):
    e=densities(n,v,grid)['energy_density'];points=grid.points();mask=np.any(abs(points)>=np.asarray(grid.lengths)/2-width,axis=-1)
    total=float(np.sum(e)*np.prod(grid.spacing));shell=float(np.sum(e[mask])*np.prod(grid.spacing))
    return {'width':width,'energy':shell,'total_continuum_energy':total,'fraction':shell/total if total>0 else None}

def endpoint_audit(metrics,observations,stationary_policy,window_policy,native_status,reason):
    rows=[r for r in observations if r['regular_observation']];count=window_policy['stable_intervals'];last=rows[-count-1:]
    stable=len(last)==count+1 and all(b['iteration']-a['iteration']==window_policy['observe_every'] and all(isinstance(b.get(k),(float,int)) and np.isfinite(b[k]) and b[k]<=window_policy[k] for k in ['tail_fraction_change','shell_energy_change','core_field_relative_change','hamiltonian_relative_change']) for a,b in zip(last,last[1:]))
    endpoint=admitted(metrics,1,stationary_policy);regular=bool(observations) and observations[-1]['regular_observation']
    return {'recorded_at':timestamp(),'native_status_preserved':native_status,'native_reason_preserved':reason,'strict_endpoint_stationarity_pass':endpoint,'preceding_regular_window_stable':bool(stable),'final_observation_regular':bool(regular),'historical_regular_certificate_pass':bool(endpoint and stable and regular),'scope':'Separates the measured endpoint, preceding window and historical sampling certificate; never overwrites native labels or authorizes motion.'}

def geodesic_control():
    # Independent closed form: a uniform great-circle geodesic, no spatial truncation.
    g=Grid((1,1,1),(2.,2.,2.),'periodic');omega=.7;duration=.8;rows=[]
    for dt in [.2,.1,.05]:
        n=np.broadcast_to([0.,0.,1.],g.shape+(3,)).copy();v=np.broadcast_to([omega,0.,0.],n.shape).copy()
        for k in range(round(duration/dt)):n,v,_=step(n,v,g,dt,k*dt)
        expected_n=np.array([np.sin(omega*duration),0.,np.cos(omega*duration)]);expected_v=omega*np.array([np.cos(omega*duration),0.,-np.sin(omega*duration)])
        error=float(np.sqrt(np.mean((n-expected_n)**2+(v-expected_v)**2)))
        rows.append({'dt':dt,'error':error,'unit_error':float(np.max(abs(np.sum(n*n,axis=-1)-1))),'tangency_error':float(np.max(abs(np.sum(n*v,axis=-1))))})
    orders=[float(np.log2(a['error']/b['error'])) for a,b in zip(rows,rows[1:])]
    return {'recorded_at':timestamp(),'rows':rows,'orders':orders,'passed':min(orders)>3.9 and max(max(r['unit_error'],r['tangency_error']) for r in rows)<1e-10,'scope':'Closed-form temporal instrument control only, not soliton acceptance.'}

def field_differences(na,va,nb,vb,count):
    aa=na[centred_slice(len(na),count)] if na.shape[0]==na.shape[1]==na.shape[2] else centred_cube(na,count)
    ab=nb[centred_slice(len(nb),count)] if nb.shape[0]==nb.shape[1]==nb.shape[2] else centred_cube(nb,count)
    av=centred_cube(va,count);bv=centred_cube(vb,count)
    return {'field_relative_l2':float(np.linalg.norm(aa-ab)/max(np.linalg.norm(ab-NORTH),1e-30)),
            'rate_relative_l2':float(np.linalg.norm(av-bv)/max(np.linalg.norm(bv),1e-30)),
            'combined_absolute_rms':float(np.sqrt(np.mean((aa-ab)**2+(av-bv)**2)))}

def centred_cube(a,count):
    if count%2!=1 or any(n<count or n%2!=1 for n in a.shape[:3]):raise ValueError('Odd equal-centre common cube required')
    return a[tuple(slice((n-count)//2,(n+count)//2) for n in a.shape[:3])]

def observed_order(coarse_medium,medium_fine,floor=1e-12):
    if not np.isfinite(coarse_medium+medium_fine) or coarse_medium<=floor or medium_fine<=floor:return {'order':None,'reason':'difference at/below declared numerical reporting floor'}
    return {'order':float(np.log2(coarse_medium/medium_fine)),'reason':'descriptive three-step estimate at fixed physical grid and common time'}
