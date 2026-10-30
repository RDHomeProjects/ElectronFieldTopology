"""Bounded S3-C linear perturbation and literature comparison; Apache-2.0."""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
import numpy as np
from .benchmark import digest,git
from .evolution import FourierMaxwell,grid,cube_diagnostics
from .fields import hopfion
from .perturbations import (duality,null_scores,invariant_change,seeded_gaussian,
                            fourier_cube,cube_energy)


def validate(c):
    if c['model_id']!='B0-H11-Perturbations':raise ValueError('unsupported model')
    if c['times']!=[0,.25,.5,.75]:raise ValueError('standard four times required')
    if c['seeds']!=[11,29,47] or c['amplitudes']!=[.01,.05,.1]:raise ValueError('standard bounded trials required')
    if c['gaussian_width']!=.8 or c['roi_half_extent']!=1.2 or c['observation_grid']!=17:raise ValueError('standard observation geometry required')
    if c['reference']!={'grid':61,'half_extent':6.1}:raise ValueError('standard reference required')
    for key in ['spatial','domain']:
        ns=c[key]['grids']
        if len(ns)!=3 or any(not isinstance(n,int) or n%2!=1 or not 25<=n<=81 for n in ns) or not ns[0]<ns[1]<ns[2]:raise ValueError('three increasing odd grids25..81 required')
    if c['spatial']['half_extent']!=6.1 or c['domain']['spacing']!=.2:raise ValueError('standard convergence geometry required')
    if c['flux_intervals']!=[8,16,32]:raise ValueError('standard flux intervals required')


def squared_norm(e,b):return float(np.sum(e*e+b*b))


def calibration(c):
    g=c['reference'];p,dx=grid(g['grid'],g['half_extent']);e,b=hopfion(p)
    base=FourierMaxwell(e,b,dx);eb,bb=base.fields();norm=squared_norm(eb,bb);rows=[]
    for seed in c['seeds']:
        de,db,parameters=seeded_gaussian(p,dx,seed,c['gaussian_width'])
        rows.append({'seed':seed,'parameters':parameters,'physical_scale_per_unit_epsilon':float(np.sqrt(norm/squared_norm(de,db)))})
    return rows


def initial(n,L,kind,epsilon,seed,c,calibrations):
    p,dx=grid(n,L);e,b=hopfion(p);base=FourierMaxwell(e,b,dx);eb,bb=base.fields()
    if kind=='amplitude':de,db=epsilon*eb,epsilon*bb;parameters={'multiplier':1+epsilon}
    elif kind=='duality':
        angle=2*np.arcsin(epsilon/2);et,bt=duality(eb,bb,angle);de,db=et-eb,bt-bb;parameters={'angle':float(angle)}
    elif kind=='curl':
        de,db,parameters=seeded_gaussian(p,dx,seed,c['gaussian_width'])
        scale=next(r['physical_scale_per_unit_epsilon'] for r in calibrations if r['seed']==seed)
        de=de*(epsilon*scale);db=db*(epsilon*scale);parameters={**parameters,'physical_scale_per_unit_epsilon':scale}
    else:raise ValueError('unsupported perturbation')
    return p,dx,base,eb,bb,de,db,parameters


def trial(n,L,kind,epsilon,seed,c,calibrations,observe=False):
    p,dx,base,eb,bb,de,db,parameters=initial(n,L,kind,epsilon,seed,c,calibrations)
    combined=FourierMaxwell(eb+de,bb+db,dx,project=False);delta=FourierMaxwell(de,db,dx,project=False)
    delta_norm=squared_norm(de,db);initial_delta_energy=delta.energy();initial_base_energy=base.energy()
    half=int(np.floor(c['roi_half_extent']/dx+.5+1e-10));center=n//2;sl=slice(center-half,center+half+1)
    def core(a):return a[sl,sl,sl]
    base_core_initial=cube_diagnostics(eb,bb,dx,half)['energy'];rows=[]
    axis=np.linspace(-c['roi_half_extent'],c['roi_half_extent'],c['observation_grid'])
    observation_initial=cube_energy(fourier_cube(base.ehat,dx,axis),fourier_cube(base.bhat,dx,axis),axis) if observe else None
    for t in c['times']:
        dt=t-base.time
        if dt:
            for solver in [base,combined,delta]:solver.advance(dt)
        be,bb=base.fields();ce,cb=combined.fields();se,sb=delta.fields();diff_e,diff_b=ce-be,cb-bb
        roi_delta=cube_diagnostics(se,sb,dx,half);roi_base=cube_diagnostics(be,bb,dx,half);roi_total=cube_diagnostics(ce,cb,dx,half)
        base_null=null_scores(core(be),core(bb));perturbed_null=null_scores(core(ce),core(cb))
        rows.append({'time':t,'superposition_relative_field_error':float(np.sqrt(squared_norm(diff_e-se,diff_b-sb)/delta_norm)),
            'difference_energy_from_subtraction':dx**3*squared_norm(diff_e,diff_b)/2,
            'standalone_delta_energy':delta.energy(),
            'relative_difference_energy_drift':float(abs(dx**3*squared_norm(diff_e,diff_b)/(2*initial_delta_energy)-1)),
            'divergence_max':max(s.divergence_max() for s in [base,combined,delta]),
            'base_core_null_scores':base_null,'perturbed_core_null_scores':perturbed_null,
            'invariant_change_over_base_core_u_rms':invariant_change(core(ce),core(cb),core(be),core(bb)),
            'periodic_control_null_score_difference':abs(base_null['combined_null_score']-perturbed_null['combined_null_score']),
            'delta_core_energy':roi_delta['energy'],'delta_core_fraction_of_global_initial_delta_energy':roi_delta['energy']/initial_delta_energy,
            'delta_outward_flux':roi_delta['outward_flux'],
            'total_minus_base_core_energy':roi_total['energy']-roi_base['energy'],
            'response_over_initial_base_core_energy':(roi_total['energy']-roi_base['energy'])/base_core_initial})
    fixed=None
    if observe:
        br=cube_energy(fourier_cube(base.ehat,dx,axis),fourier_cube(base.bhat,dx,axis),axis)
        cr=cube_energy(fourier_cube(combined.ehat,dx,axis),fourier_cube(combined.bhat,dx,axis),axis)
        fixed={'half_extent':c['roi_half_extent'],'grid':c['observation_grid'],
               'initial_base_energy':observation_initial,'final_base_energy':br,'final_combined_energy':cr,
               'response_over_initial_base_energy':(cr-br)/observation_initial}
    result={'kind':kind,'epsilon_target_on_reference_grid':epsilon,'seed':seed,'parameters':parameters,
        'grid':n,'half_extent':L,'spacing':dx,'native_roi_half_extent':half*dx,
        'base_initial_projection_relative_l2':base.initial_projection_relative_l2,
        'initial_relative_delta_field_norm':float(np.sqrt(delta_norm/(2*initial_base_energy/dx**3))),
        'initial_delta_energy':initial_delta_energy,'initial_base_energy':initial_base_energy,
        'fixed_physical_cube_observation':fixed,'samples':rows}
    print(f'{kind} seed={seed} eps={epsilon:g} n={n} L={L:g}: drift={max(r["relative_difference_energy_drift"] for r in rows):.3g}',flush=True)
    return result


def analytic_controls(c):
    p,_=grid(17,2);rows=[]
    for t in c['times']:
        e,b=hopfion(p,t)
        for kind in ['amplitude','duality']:
            if kind=='amplitude':et,bt=1.1*e,1.1*b
            else:et,bt=duality(e,b,2*np.arcsin(.05))
            rows.append({'kind':kind,'time':t,**null_scores(et,bt)})
    return rows


def longitudinal_control(c):
    g=c['reference'];p,dx=grid(g['grid'],g['half_extent'])
    e,b,params=seeded_gaussian(p,dx,c['seeds'][0],c['gaussian_width'],mode='gradient')
    raw=FourierMaxwell(e,b,dx,project=False);projected=FourierMaxwell(e,b,dx)
    return {'parameters':params,'raw_divergence_max':raw.divergence_max(),
            'projection_removed_relative_field_norm':projected.initial_projection_relative_l2,
            'remaining_energy_fraction':projected.energy()/raw.energy(),
            'projected_divergence_max':projected.divergence_max(),'accepted_for_vacuum_evolution':False}


def flux_case(intervals,c,calibrations):
    g=c['reference'];n=g['grid'];L=g['half_extent'];seed=c['seeds'][0]
    p,dx,_,_,_,de,db,_=initial(n,L,'curl',.1,seed,c,calibrations)
    solver=FourierMaxwell(de,db,dx,project=False);half=int(round(c['roi_half_extent']/dx));rows=[]
    duration=c['times'][-1]
    for i in range(intervals+1):
        if i:solver.advance(duration/intervals)
        rows.append({'time':i*duration/intervals,**cube_diagnostics(*solver.fields(),dx,half)})
    flux=float(np.trapezoid([r['outward_flux'] for r in rows],x=[r['time'] for r in rows]));change=rows[-1]['energy']-rows[0]['energy']
    return {'intervals':intervals,'samples':rows,'energy_change':change,'integrated_outward_flux':flux,
        'balance_defect':change+flux,'normalised_balance_defect':abs(change+flux)/rows[0]['energy']}


def study(c):
    scales=calibration(c);g=c['reference'];main=[]
    for seed in c['seeds']:
        for eps in c['amplitudes']:main.append(trial(g['grid'],g['half_extent'],'curl',eps,seed,c,scales))
    for kind in ['amplitude','duality']:main.append(trial(g['grid'],g['half_extent'],kind,.1,None,c,scales))
    spatial=[trial(n,c['spatial']['half_extent'],'curl',.1,c['seeds'][0],c,scales,observe=True) for n in c['spatial']['grids']]
    domain=[trial(n,n*c['domain']['spacing']/2,'curl',.1,c['seeds'][0],c,scales,observe=True) for n in c['domain']['grids']]
    m={'experiment_id':c['experiment_id'],'calibration':scales,'main_trials':main,
        'analytic_null_controls':analytic_controls(c),'longitudinal_negative_control':longitudinal_control(c),
        'spatial':spatial,'domain':domain,'flux_time_quadrature':[flux_case(n,c,scales) for n in c['flux_intervals']],
        'scope':'Short-time periodic linear Maxwell differences. Generic constraints do not imply null-family membership or topology preservation. No self-binding or isolated stability claim.'}
    m['acceptance']=acceptance(m);return m


def acceptance(m):
    trials=m['main_trials']+m['spatial']+m['domain'];rows=[r for t in trials for r in t['samples']]
    generic=[t for t in m['main_trials'] if t['kind']=='curl'];controls=[t for t in m['main_trials'] if t['kind']!='curl']
    scaling=[abs(t['initial_delta_energy']/(t['epsilon_target_on_reference_grid']**2*t['initial_base_energy'])-1) for t in generic]
    increments={k:abs(m[k][-1]['fixed_physical_cube_observation']['response_over_initial_base_energy']-m[k][-2]['fixed_physical_cube_observation']['response_over_initial_base_energy']) for k in ['spatial','domain']}
    f=m['flux_time_quadrature'];ratio=abs((f[0]['integrated_outward_flux']-f[1]['integrated_outward_flux'])/(f[1]['integrated_outward_flux']-f[2]['integrated_outward_flux']))
    return {'divergence_below_1e-10':max(r['divergence_max'] for r in rows)<1e-10,
        'superposition_error_below_1e-11':max(r['superposition_relative_field_error'] for r in rows)<1e-11,
        'difference_energy_drift_below_1e-11':max(r['relative_difference_energy_drift'] for r in rows)<1e-11,
        'reference_perturbation_norm_below_1e-12':max(abs(t['initial_relative_delta_field_norm']-t['epsilon_target_on_reference_grid']) for t in m['main_trials'])<1e-12,
        'analytic_controls_null_below_1e-12':max(r['combined_null_score'] for r in m['analytic_null_controls'])<1e-12,
        'periodic_control_score_tracks_base_below_1e-12':max(r['periodic_control_null_score_difference'] for t in controls for r in t['samples'])<1e-12,
        'generic_invariant_change_above_1e-5':min(t['samples'][0]['invariant_change_over_base_core_u_rms'] for t in generic)>1e-5,
        'longitudinal_negative_control_detected':m['longitudinal_negative_control']['raw_divergence_max']>.01 and m['longitudinal_negative_control']['projection_removed_relative_field_norm']>.999,
        'difference_energy_quadratic_scaling_below_1e-11':max(scaling)<1e-11,
        'spatial_finest_response_increment_below_0.005':increments['spatial']<.005,
        'domain_finest_response_increment_below_0.005':increments['domain']<.005,
        'delta_poynting_balance_below_0.02':f[-1]['normalised_balance_defect']<.02,
        'flux_time_quadrature_second_order':3.5<ratio<4.5}


def plot(m,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='eft-s3c';fig,axs=plt.subplots(1,3,figsize=(12,3.6),constrained_layout=True)
    trials=[t for t in m['main_trials'] if t['kind']=='curl' and t['epsilon_target_on_reference_grid']==.1]
    for t in trials:
        x=[r['time'] for r in t['samples']];axs[0].plot(x,[r['difference_energy_from_subtraction']/t['initial_delta_energy'] for r in t['samples']],'o-',label=str(t['seed']))
        axs[1].plot(x,[r['delta_core_fraction_of_global_initial_delta_energy'] for r in t['samples']],'o-',label=str(t['seed']))
        axs[2].plot(x,[r['perturbed_core_null_scores']['combined_null_score'] for r in t['samples']],'o-',label=str(t['seed']))
    axs[0].set(xlabel='Time',ylabel='Difference energy / initial value',title='Global periodic norm');axs[0].set_ylim(.98,1.02)
    axs[1].set(xlabel='Time',ylabel='Fraction of initial global difference energy',title='Interior difference energy')
    axs[2].set(xlabel='Time',ylabel='RMS null invariant score',title='Generic curl perturbations')
    for ax in axs:ax.legend(title='Seed',fontsize=7)
    fig.savefig(out/'perturbations.svg',metadata={'Date':None});plt.close(fig)


def run(config_path,output):
    start=time.perf_counter();path=Path(config_path).resolve();c=json.loads(path.read_text());validate(c);out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('new or empty output required')
    out.mkdir(parents=True,exist_ok=True);m=study(c)
    (out/'metrics.json').write_text(json.dumps(m,indent=2,allow_nan=False)+'\n');(out/'config.json').write_bytes(path.read_bytes());plot(m,out)
    root=Path(__file__).resolve().parents[2];sources=[root/'pyproject.toml',root/'uv.lock',*sorted((root/'src').rglob('*.py'))]
    manifest={'experiment_id':c['experiment_id'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'repository':'https://github.com/RDHomeProjects/ElectronFieldTopology','commit':git(root,'rev-parse','HEAD'),
        'dirty_tree':bool(git(root,'status','--porcelain')),'source_sha256':{str(p.relative_to(root)):digest(p) for p in sources},
        'config_sha256':digest(path),'dependency_lock_sha256':digest(root/'uv.lock'),'configuration':c,
        'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'cpu_count':os.cpu_count(),
        'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib']},
        'precision':'float64 / complex128','thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
        'command':sys.argv,'boundaries':'periodic cube; native interior cube and fixed physical Fourier observation cube; no absorption',
        'units':'c=epsilon_0=mu_0=l0=1, arbitrary dimensionless amplitude','elapsed_seconds':time.perf_counter()-start,
        'artifacts_sha256':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'acceptance':m['acceptance'],'elapsed_seconds':manifest['elapsed_seconds']}));return all(m['acceptance'].values())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if not run(a.config,a.output):raise SystemExit('Verification acceptance failed; retain metrics for investigation.')


if __name__=='__main__':main()
