"""Measured physical-time control suite, no renderer and no large soliton claim."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from electron_field_topology.sf_time import Grid,step,acceleration,diagnostics,densities
from electron_field_topology.sf_time_controls import wave,manufactured,manufactured_force,pulse
from electron_field_topology.sf_time_run import initialize
from electron_field_topology.sf_checkpoints import atomic_json,timestamp
from electron_field_topology.sf_dynamics_admission import sha


def order(errors,ratios):return [float(np.log(errors[i]/errors[i+1])/np.log(ratios[i])) for i in range(len(ratios))]


def verify():
    started=timestamp();clock=time.monotonic();results={}
    modes=[{'amplitude':.35,'wave_numbers':[1,0,0]}];cases=[]
    for n in [16,32,64]:
        g=Grid((n,1,1),(2*np.pi,1.,1.));u,v=wave(g.points(),0,g.lengths,modes);d0=diagnostics(u,v,g);dt=1/(2*n)
        for k in range(2*n):u,v,_=step(u,v,g,dt,k*dt)
        d1=diagnostics(u,v,g)
        cases.append({'n':n,'dt':dt,'time':1.,'reference_rms_error':float(np.sqrt(np.mean((u-wave(g.points(),1,g.lengths,modes)[0])**2))),
             'energy_relative_drift':abs(d1['energy']/d0['energy']-1),
             'momentum_scaled_drift':float(np.linalg.norm(np.array(d1['momentum'])-d0['momentum'])/d0['energy']),
             'unit_error':d1['unit_error'],'tangency_error':d1['tangency_error']})
    results['wave_convergence']={'cases':cases,'orders':order([x['reference_rms_error'] for x in cases],[2,2])}
    cases=[]
    for dt in [.1,.05,.025]:
        g=Grid((1,1,1),(1.,)*3);u=np.array([[[[0.,0.,1.]]]]);v=np.array([[[[1.,0.,0.]]]])
        for k in range(round(1/dt)):u,v,_=step(u,v,g,dt,k*dt)
        cases.append({'dt':dt,'time':1.,'field_error':float(np.linalg.norm(u.ravel()-[np.sin(1),0,np.cos(1)]))})
    results['temporal_geodesic']={'cases':cases,'orders':order([x['field_error'] for x in cases],[2,2])}
    cases=[]
    for n in [8,16,32]:
        g=Grid((n,n,n),(2*np.pi,)*3);u,v,exact=manufactured(g.points(),.17,True)
        a=acceleration(u,v,g,manufactured_force,.17)[1]
        cases.append({'n':n,'acceleration_rms_error':float(np.sqrt(np.mean((a-exact)**2)))})
    results['manufactured_spatial_rhs']={'cases':cases,'orders':order([x['acceleration_rms_error'] for x in cases],[2,2])}
    cases=[]
    for n in [8,12,16]:
        g=Grid((n,n,n),(2*np.pi,)*3);u,v=manufactured(g.points(),0)
        for k in range(10):u,v,_=step(u,v,g,.01,k*.01,manufactured_force)
        cases.append({'n':n,'dt':.01,'time':.1,'field_rms_error':float(np.sqrt(np.mean((u-manufactured(g.points(),.1)[0])**2)))})
    results['manufactured_evolution']={'cases':cases,'orders':order([x['field_rms_error'] for x in cases],[1.5,4/3])}
    cv=[]
    for n,dt in [(97,.005),(193,.0025),(385,.00125)]:
        g=Grid((n,1,1),(16.,1.,1.),'fixed');u,v=pulse(g.points(),0,centre=-2.,radius=2.)
        a=(n-1)//4;b=(n-1)//2;h=g.spacing[0];flux=np.zeros(2);last=None
        for k in range(round(1.5/dt)+1):
            data=densities(u,v,g);e=data['energy_density'][:,0,0];s=data['energy_flux'][:,0,0,0];stress=data['stress'][:,0,0,0,0]
            quantities=np.array([np.trapezoid(e[a:b+1],dx=h),np.trapezoid(s[a:b+1],dx=h)])
            rate=np.array([s[b]-s[a],stress[b]-stress[a]])
            if k==0:initial=quantities.copy()
            else:flux+=.5*dt*(rate+last)
            last=rate
            if k<round(1.5/dt):u,v,_=step(u,v,g,dt,k*dt)
        defects=abs(quantities-initial+flux)/initial[0]
        cv.append({'n':n,'h':h,'dt':dt,'time':1.5,'energy_flux_balance_relative_defect':float(defects[0]),
                   'momentum_flux_balance_scaled_defect':float(defects[1]),
                   'scope':'Continuum stress/energy on x in [-4,0], before fixed-wall return; trapezoidal space/time flux quadrature.'})
    results['interior_flux_balance']=cv
    reflections=[]
    for dt in [.01,.005]:
        g=Grid((129,1,1),(8.,1.,1.),'fixed');u,v=pulse(g.points(),0,centre=1.7,radius=.8);d0=diagnostics(u,v,g)
        for k in range(round(4/dt)):u,v,_=step(u,v,g,dt,k*dt)
        d1=diagnostics(u,v,g)
        reflections.append({'n':129,'dt':dt,'time':4.,'energy_relative_drift':abs(d1['energy']/d0['energy']-1),
                'initial_momentum_over_energy':d0['momentum'][0]/d0['energy'],'final_momentum_over_initial_energy':d1['momentum'][0]/d0['energy'],
                'scope':'Reflecting-wall diagnostic; wall impulse changes momentum. This is not an absorbing boundary.'})
    results['fixed_wall_reflection']=reflections
    seeds=[]
    for q in [1,2]:
        g=Grid((17,17,17),(8.,)*3,'fixed');cfg={'initial':{'kind':'rational','q':q,'scale':1.,'cutoff':2.8}}
        u,v,meta=initialize(cfg,g);d0=diagnostics(u,v,g)
        for k in range(2):u,v,_=step(u,v,g,.001,k*.001)
        d1=diagnostics(u,v,g);seeds.append({'intended_q':q,'initial':d0,'final':d1,'time':.002,'dt':.001,
            'energy_relative_drift':abs(d1['energy']/d0['energy']-1),'scope':meta['scope']+' No independent topology/stability acceptance.'})
    results['low_q_seed_smoke']=seeds
    checks={
      'wave_spatial_time_order_gt_3_5':min(results['wave_convergence']['orders'])>3.5,
      'temporal_order_gt_3_9':min(results['temporal_geodesic']['orders'])>3.9,
      'nonlinear_rhs_order_gt_3_5':min(results['manufactured_spatial_rhs']['orders'])>3.5,
      'forced_evolution_order_gt_3_4':min(results['manufactured_evolution']['orders'])>3.4,
      'wave_conservation_below_1e_3':all(x['energy_relative_drift']<1e-3 and x['momentum_scaled_drift']<1e-3 for x in results['wave_convergence']['cases']),
      'unit_tangency_below_1e_10':all(x['unit_error']<1e-10 and x['tangency_error']<1e-10 for x in results['wave_convergence']['cases']),
      'finest_interior_energy_momentum_balance_below_1e_3':max(cv[-1]['energy_flux_balance_relative_defect'],cv[-1]['momentum_flux_balance_scaled_defect'])<1e-3,
      'refined_wall_energy_below_1e_6':reflections[-1]['energy_relative_drift']<1e-6,
      'fixed_wall_reverses_pulse_momentum':reflections[-1]['final_momentum_over_initial_energy']<-.95}
    return {'started_at':started,'finished_at':timestamp(),'wall_seconds':time.monotonic()-clock,'checks':checks,'passed':all(checks.values()),
            'results':results,'source_sha256':{name:sha(Path(__file__).resolve().parents[1]/'src/electron_field_topology'/name)
                for name in ['sf_time.py','sf_time_controls.py','sf_time_initial.py','sf_dynamics.py']},
            'scope':'Actual physical-time numerical controls. No stationary Q1/Q2 or high-Q free-flight/stability acceptance; no charged or electron claim.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=verify();a.output.parent.mkdir(parents=True,exist_ok=True);atomic_json(a.output,result)
    print(json.dumps({k:result[k] for k in ['started_at','finished_at','wall_seconds','checks','passed']},indent=2))
    raise SystemExit(0 if result['passed'] else 1)
