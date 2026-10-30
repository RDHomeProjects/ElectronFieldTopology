"""Bounded S2 evolution study, comparisons and evidence; Apache-2.0."""
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
from .fields import hopfion
from .evolution import FourierMaxwell,grid,cube_diagnostics
from .benchmark import digest,git


def validate(c):
    if c['model_id']!='B0-H11-PSATD':raise ValueError('unsupported model')
    if not np.isfinite(c['duration']) or not 0<c['duration']<=1:raise ValueError('duration must be in (0,1]')
    if not np.isfinite(c['roi_half_extent']) or not .5<=c['roi_half_extent']<=2:raise ValueError('invalid ROI')
    for group in ['spatial','domain','time_flux']:
        g=c[group]
        ns=g.get('grids',[g.get('grid')])
        if not 1<=len(ns)<=4 or any(not isinstance(n,int) or n%2==0 or not 17<=n<=97 for n in ns):raise ValueError('odd grids 17..97 required')
        if group=='domain':
            if not np.isfinite(g['spacing']) or not .15<=g['spacing']<=.4:raise ValueError('invalid spacing')
            extents=[g['spacing']*n/2 for n in ns]
        else:
            extents=[g['half_extent']]
        if any(not np.isfinite(v) or not 3<=v<=12 or v<=c['roi_half_extent']+c['duration'] for v in extents):raise ValueError('insufficient domain margin')
        intervals=g.get('intervals',[g.get('flux_intervals')])
        if not 1<=len(intervals)<=4 or any(not isinstance(v,int) or not 4<=v<=64 for v in intervals):raise ValueError('invalid output intervals')
    intervals=c['time_flux']['intervals']
    if len(intervals)!=3 or intervals[1]!=2*intervals[0] or intervals[2]!=2*intervals[1]:raise ValueError('time flux study requires three doubled interval counts')
    if not 3<=len(c['subdivision'])<=6 or any(not isinstance(v,int) or not 1<=v<=32 for v in c['subdivision']):raise ValueError('invalid subdivision')


def case(n,half_extent,duration,intervals,roi):
    points,dx=grid(n,half_extent)
    e0,b0=hopfion(points,0)
    solver=FourierMaxwell(e0,b0,dx)
    initial_energy=solver.energy()
    half_cells=int(np.floor(roi/dx+0.5+1e-10))
    center=n//2
    sl=slice(center-half_cells,center+half_cells+1)
    rows=[]
    max_div=0.
    for i in range(intervals+1):
        if i:solver.advance(duration/intervals)
        e,b=solver.fields()
        # Analytical oracle is outside the propagator and used only for comparison.
        er,br=hopfion(points[sl,sl,sl],i*duration/intervals)
        denom=np.sum(er*er+br*br)
        error=np.sum((e[sl,sl,sl]-er)**2+(b[sl,sl,sl]-br)**2)
        diagnostics=cube_diagnostics(e,b,dx,half_cells)
        rows.append({'time':i*duration/intervals,**diagnostics,
                     'relative_l2_error':float(np.sqrt(error/denom)),
                     'periodic_total_energy':solver.energy(),
                     'periodic_momentum':(dx**3*np.sum(np.cross(e,b),axis=(0,1,2))).tolist()})
        if i in [0,intervals]:max_div=max(max_div,solver.divergence_max())
    times=np.array([r['time'] for r in rows])
    flux=np.array([r['outward_flux'] for r in rows])
    transported=float(np.trapezoid(flux,x=times))
    change=rows[-1]['energy']-rows[0]['energy']
    balance=change+transported
    return {'grid':n,'half_extent':half_extent,'dx':dx,'duration':duration,
        'flux_intervals':intervals,'roi_actual_half_extent':half_cells*dx,
        'initial_transverse_projection_relative_l2_global':solver.initial_projection_relative_l2,
        'initial_core_relative_l2_error':rows[0]['relative_l2_error'],
        'final_core_relative_l2_error':rows[-1]['relative_l2_error'],
        'max_endpoint_divergence':max_div,
        'max_relative_periodic_momentum_drift':max(float(np.linalg.norm(np.array(r['periodic_momentum'])-rows[0]['periodic_momentum']))/initial_energy for r in rows),
        'max_relative_periodic_energy_drift':max(abs(r['periodic_total_energy']/initial_energy-1) for r in rows),
        'roi_energy_change':change,'integrated_outward_flux':transported,
        'balance_defect':balance,'normalised_balance_defect':abs(balance)/rows[0]['energy'],
        'balance_defect_relative_to_energy_change':abs(balance)/abs(change) if change else None,
        'samples':rows}


def subdivision(c):
    n=c['time_flux']['grid'];half=c['time_flux']['half_extent']
    p,dx=grid(n,half);e,b=hopfion(p)
    reference=FourierMaxwell(e,b,dx);reference.advance(c['duration'])
    norm=np.sum(np.abs(reference.ehat)**2+np.abs(reference.bhat)**2)
    result=[]
    for count in c['subdivision']:
        s=FourierMaxwell(e,b,dx)
        for _ in range(count):s.advance(c['duration']/count)
        err=np.sum(np.abs(s.ehat-reference.ehat)**2+np.abs(s.bhat-reference.bhat)**2)
        result.append({'steps':count,'dt':c['duration']/count,
                       'relative_l2_difference_to_one_step':float(np.sqrt(err/norm))})
    return result


def acceptance(metrics):
    spatial=metrics['spatial']
    domain=metrics['domain']
    allcases=spatial+domain+metrics['time_flux']
    temporal=metrics['time_flux']
    diff0=abs(temporal[0]['integrated_outward_flux']-temporal[1]['integrated_outward_flux'])
    diff1=abs(temporal[1]['integrated_outward_flux']-temporal[2]['integrated_outward_flux'])
    return {
        'flux_time_quadrature_second_order':3.5 < diff0/diff1 < 4.5,
        'periodic_momentum_drift_below_1e-12':max(r['max_relative_periodic_momentum_drift'] for r in allcases)<1e-12,
        'spatial_error_reduces':spatial[-1]['final_core_relative_l2_error']<spatial[0]['final_core_relative_l2_error'],
        'domain_error_reduces':domain[-1]['final_core_relative_l2_error']<domain[0]['final_core_relative_l2_error'],
        'finest_core_error_below_0.005':spatial[-1]['final_core_relative_l2_error']<.005,
        'finest_balance_below_0.01':spatial[-1]['normalised_balance_defect']<.01,
        'balance_improves_spatially':spatial[-1]['normalised_balance_defect']<spatial[0]['normalised_balance_defect'],
        'periodic_energy_drift_below_1e-12':max(r['max_relative_periodic_energy_drift'] for r in allcases)<1e-12,
        'endpoint_divergence_below_1e-10':max(r['max_endpoint_divergence'] for r in allcases)<1e-10,
        'time_subdivision_difference_below_1e-12':max(r['relative_l2_difference_to_one_step'] for r in metrics['subdivision'])<1e-12,
    }


def plot(metrics,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='eft-s2'
    fig,axs=plt.subplots(1,3,figsize=(12,3.6),constrained_layout=True)
    s=metrics['spatial'];d=metrics['domain']
    axs[0].loglog([r['dx'] for r in s],[r['final_core_relative_l2_error'] for r in s],'o-')
    axs[0].set(xlabel='Grid spacing',ylabel='Core relative field L2 error',title='Spatial refinement')
    axs[1].semilogy([r['half_extent'] for r in d],[r['final_core_relative_l2_error'] for r in d],'o-')
    axs[1].set(xlabel='Periodic half extent',ylabel='Core relative field L2 error',title='Domain enlargement, fixed dx')
    r=s[-1];times=[x['time'] for x in r['samples']];u=np.array([x['energy'] for x in r['samples']]);flux=np.array([x['outward_flux'] for x in r['samples']]);times=np.array(times)
    integral=np.r_[0,np.cumsum((flux[1:]+flux[:-1])*np.diff(times)/2)]
    axs[2].plot(times,u-u[0],label='Interior energy change')
    axs[2].plot(times,-integral,'--',label='Negative outward flux integral')
    axs[2].set(xlabel='Time',ylabel='Dimensionless energy',title='Interior Poynting balance')
    axs[2].legend(fontsize=8)
    fig.savefig(out/'convergence.svg',metadata={'Date':None});plt.close(fig)


def run(config_path,output):
    start=time.perf_counter();path=Path(config_path).resolve();c=json.loads(path.read_text());validate(c)
    out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('new or empty output required')
    out.mkdir(parents=True,exist_ok=True)
    common=(c['duration'],c['roi_half_extent'])
    def compute(n,L,intervals):
        r=case(n,L,common[0],intervals,common[1]);print(f'n={n} L={L:g} samples={intervals}: core_error={r["final_core_relative_l2_error"]:.6g} balance={r["normalised_balance_defect"]:.6g}',flush=True);return r
    g=c['spatial'];spatial=[compute(n,g['half_extent'],g['flux_intervals']) for n in g['grids']]
    g=c['domain'];domain=[compute(n,n*g['spacing']/2,g['flux_intervals']) for n in g['grids']]
    g=c['time_flux'];temporal=[compute(g['grid'],g['half_extent'],i) for i in g['intervals']]
    metrics={'experiment_id':c['experiment_id'],'spatial':spatial,'domain':domain,'time_flux':temporal,'subdivision':subdivision(c),
             'scope':'Periodic source-free PSATD initial-value solution, transverse-projected samples; interior comparison only. No isolated confinement claim.'}
    metrics['acceptance']=acceptance(metrics)
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n');(out/'config.json').write_bytes(path.read_bytes());plot(metrics,out)
    root=Path(__file__).resolve().parents[2]
    sources=[root/'pyproject.toml',root/'uv.lock',*sorted((root/'src').rglob('*.py'))]
    manifest={'experiment_id':c['experiment_id'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'repository':'https://github.com/RDHomeProjects/ElectronFieldTopology','commit':git(root,'rev-parse','HEAD'),
        'dirty_tree':bool(git(root,'status','--porcelain')),'source_sha256':{str(p.relative_to(root)):digest(p) for p in sources},
        'config_sha256':digest(path),'dependency_lock_sha256':digest(root/'uv.lock'),'configuration':c,
        'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'cpu_count':os.cpu_count(),
        'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib']},
        'precision':'float64 / complex128','thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
        'command':sys.argv,'boundaries':'periodic cube, no PML; interior cube diagnostics; initial transverse projection measured per case',
        'units':'c=epsilon_0=mu_0=l0=1, dimensionless fields','elapsed_seconds':time.perf_counter()-start,
        'artifacts_sha256':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'acceptance':metrics['acceptance'],'elapsed_seconds':manifest['elapsed_seconds']}))
    return all(metrics['acceptance'].values())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if not run(a.config,a.output):raise SystemExit('Verification acceptance failed; retain metrics for investigation.')


if __name__=='__main__':main()
