"""Bounded S3-D helicity, closure and linking verification; Apache-2.0."""
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
from .evolution import FourierMaxwell,grid
from .fields import hopfion
from .helicity import bateman_potentials,coulomb_potential,periodic_helicities,remove_mean
from .linking import gauss_link,trace_closed_line
from .localisation import all_space_rule
from .perturbations import seeded_gaussian,null_scores


def validate(c):
    expected={'model_id':'B0-H11-Topology','modal_grid':17,'modes':[-2,-1,1,2],
        'times':[0,.25,.5,.75],'domain_grids':[41,61,81],'spacing':.2,
        'exchange_intervals':[8,16,32],'link_segments':[64,128,256],
        'trace_tolerances':[1e-8,1e-10,1e-12],'trace_max_steps':[.1,.05,.025],
        'trace_seeds':[[1,0,0],[.5,0,0]],'trace_max_arclength':40,
        'analytical_orders':[24,40,64],'analytical_times':[0,.75]}
    if any(c[k]!=v for k,v in expected.items()):raise ValueError('only the declared bounded standard configuration is supported')


def modal_case(q,c):
    p,dx=grid(c['modal_grid'],np.pi);b0=np.zeros_like(p);b0[...,0]=np.sin(q*p[...,2]);b0[...,1]=np.cos(q*p[...,2])
    solver=FourierMaxwell(np.zeros_like(p),b0,dx,project=False);volume=(2*np.pi)**3;rows=[]
    for t in c['times']:
        if t!=solver.time:solver.advance(t-solver.time)
        e,b=solver.fields();h=periodic_helicities(e,b,dx)
        expected=[volume*np.cos(q*t)**2/q,volume*np.sin(q*t)**2/q]
        rows.append({'time':t,**h,'expected_magnetic_helicity':expected[0],'expected_electric_helicity':expected[1],
            'normalised_modal_error':float(max(abs(h['magnetic_helicity']-expected[0]),abs(h['electric_helicity']-expected[1]))/volume),
            'combined_null_score':null_scores(e,b)['combined_null_score']})
    return {'mode':q,'energy':solver.energy(),'volume':volume,'samples':rows}


def gauge_control(e,b,p,dx):
    a,_=coulomb_potential(b,dx);cc,_=coulomb_potential(e,dx);x,y,z=np.moveaxis(p,-1,0)
    # Physical periods of this grid, not an assumed 2pi domain.
    k=2*np.pi/(p.shape[0]*dx)
    grad=np.stack([k*np.cos(k*x),-.6*k*np.sin(k*(2*y-z)),.3*k*np.sin(k*(2*y-z))],axis=-1)
    energy=dx**3*np.sum(e*e+b*b)/2
    return float(max(abs(dx**3*np.sum((a+grad+np.array([.2,-.1,.3]))*b)-dx**3*np.sum(a*b)),
                     abs(dx**3*np.sum((cc-.7*grad)*e)-dx**3*np.sum(cc*e)))/energy)


def periodic_initial(n,c,generic=False):
    dx=c['spacing'];p,_=grid(n,n*dx/2);e,b=hopfion(p);projected=FourierMaxwell(e,b,dx);e,b=projected.fields()
    original_energy=projected.energy();e,me=remove_mean(e);b,mb=remove_mean(b)
    volume=(n*dx)**3;removed_energy=float(volume*(np.dot(me,me)+np.dot(mb,mb))/2)
    if generic:
        de,db,_=seeded_gaussian(p,dx,11,.8);factor=.1*np.sqrt(np.sum(e*e+b*b)/np.sum(de*de+db*db));e=e+factor*de;b=b+factor*db
    return p,e,b,{'base_projection_relative_l2':projected.initial_projection_relative_l2,
        'removed_mean_e':me.tolist(),'removed_mean_b':mb.tolist(),'removed_mean_energy':removed_energy,
        'removed_mean_energy_fraction':removed_energy/original_energy,'mean_removal_explicit':True}


def periodic_case(n,c):
    p,e,b,means=periodic_initial(n,c);dx=c['spacing'];gauge=gauge_control(e,b,p,dx)
    solver=FourierMaxwell(e,b,dx,project=False);energy=solver.energy();rows=[]
    for t in c['times']:
        if t!=solver.time:solver.advance(t-solver.time)
        en,bn=solver.fields();rows.append({'time':t,**periodic_helicities(en,bn,dx)})
    return {'grid':n,'half_extent':n*dx/2,**means,'initial_energy':energy,
        'gauge_helicity_error_over_energy':gauge,'samples':rows,
        'optical_drift_over_initial_energy':float(max(abs(r['optical_helicity']-rows[0]['optical_helicity']) for r in rows)/energy)}


def exchange_case(intervals,c,modal=False):
    if modal:
        p,dx=grid(c['modal_grid'],np.pi);e=np.zeros_like(p);b=e.copy();b[...,0]=np.sin(p[...,2]);b[...,1]=np.cos(p[...,2])
    else:p,e,b,_=periodic_initial(41,c,True);dx=c['spacing']
    solver=FourierMaxwell(e,b,dx,project=False);energy=solver.energy();rows=[];duration=c['times'][-1]
    for i in range(intervals+1):
        if i:solver.advance(duration/intervals)
        rows.append({'time':i*duration/intervals,**periodic_helicities(*solver.fields(),dx)})
    integrated=float(np.trapezoid([r['integral_e_dot_b'] for r in rows],x=[r['time'] for r in rows]))
    defect_m=rows[-1]['magnetic_helicity']-rows[0]['magnetic_helicity']+2*integrated
    defect_e=rows[-1]['electric_helicity']-rows[0]['electric_helicity']-2*integrated
    return {'intervals':intervals,'kind':'Beltrami' if modal else 'mean-removed Hopfion plus curl',
        'initial_energy':energy,'integrated_e_dot_b':integrated,'magnetic_exchange_defect':defect_m,
        'electric_exchange_defect':defect_e,'normalised_exchange_defect':max(abs(defect_m),abs(defect_e))/energy,
        'optical_drift_over_initial_energy':float(max(abs(r['optical_helicity']-rows[0]['optical_helicity']) for r in rows)/energy),'samples':rows}


def analytical_case(order,time):
    p,w=all_space_rule(order,2*order);e,b=hopfion(p,time);a,cc=bateman_potentials(p,time)
    hm=float(np.sum(w*np.sum(a*b,axis=-1)));he=float(np.sum(w*np.sum(cc*e,axis=-1)))
    return {'angular_order':order,'radial_order':2*order,'time':time,'magnetic_helicity':hm,'electric_helicity':he,
            'reference_each':np.pi**2,'max_relative_error':float(max(abs(hm/np.pi**2-1),abs(he/np.pi**2-1)))}


def potential_curl_controls():
    points=np.random.default_rng(19).uniform(-1,1,(32,3));time=.3;e,b=hopfion(points,time);denom=np.sqrt(np.mean(e*e+b*b));rows=[]
    for h in [.04,.02,.01]:
        derivatives=[]
        for axis in range(3):
            shift=np.eye(3)[axis]*h;ap,cp=bateman_potentials(points+shift,time);am,cm=bateman_potentials(points-shift,time)
            derivatives.append(((ap-am)/(2*h),(cp-cm)/(2*h)))
        def curl(j):return np.stack([j[...,2,1]-j[...,1,2],j[...,0,2]-j[...,2,0],j[...,1,0]-j[...,0,1]],axis=-1)
        ja=np.stack([d[0] for d in derivatives],axis=-1);jc=np.stack([d[1] for d in derivatives],axis=-1)
        rows.append({'step':h,'curl_a_relative_rms_error':float(np.sqrt(np.mean((curl(ja)-b)**2))/denom),
            'curl_c_relative_rms_error':float(np.sqrt(np.mean((curl(jc)-e)**2))/denom)})
    return rows


def circles(n,shift=1):
    t=np.linspace(0,2*np.pi,n+1)
    return np.stack([np.cos(t),np.sin(t),np.zeros_like(t)],axis=-1),np.stack([shift+np.cos(t),np.zeros_like(t),np.sin(t)],axis=-1)


def rejections(c):
    p,dx=grid(17,np.pi);uniform=np.zeros_like(p);uniform[...,2]=1;longitudinal=np.zeros_like(p);longitudinal[...,0]=np.sin(p[...,0])
    flags={}
    for name,field in [('mean',uniform),('longitudinal',longitudinal)]:
        try:coulomb_potential(field,dx);flags[name+'_rejected']=False
        except ValueError:flags[name+'_rejected']=True
    points,meta=trace_closed_line(lambda p:np.array([1.,0,0]),[0,0,0],samples=64,max_arclength=4)
    try:gauss_link(points,circles(64)[0]);rejected=False
    except ValueError:rejected=True
    return {**flags,'uniform_open_trace':meta,'open_trace_linking_rejected':rejected}


def study(c):
    modal=[modal_case(q,c) for q in c['modes']];domains=[periodic_case(n,c) for n in c['domain_grids']]
    # Opposite helicities cancel while the magnetic field remains nonzero.
    p,dx=grid(17,np.pi);b=np.zeros_like(p);b[...,1]=2*np.cos(p[...,2]);cancellation=periodic_helicities(np.zeros_like(p),b,dx);cancellation_energy=float(dx**3*np.sum(b*b)/2)
    known=[];traced=[];finest_curves=None
    for n,tol,step in zip(c['link_segments'],c['trace_tolerances'],c['trace_max_steps']):
        a,b=circles(n);_,separate=circles(n,3)
        known.append({'segments':n,'linked':gauss_link(a,b),'reversed':gauss_link(a,b[::-1]),'unlinked':gauss_link(a,separate)})
        curves=[];metas=[]
        for seed in c['trace_seeds']:
            curve,meta=trace_closed_line(lambda p:hopfion(p,0)[1],seed,samples=n,tolerance=tol,max_step=step,max_arclength=c['trace_max_arclength'])
            curves.append(curve);metas.append(meta)
        link=gauss_link(*curves) if all(x['closed'] for x in metas) else None
        traced.append({'segments':n,'traces':metas,'link':link})
        finest_curves=curves
        print(f'segments={n}: traced closure={[x["closure_gap_before_correction"] for x in metas]}, link={None if link is None else link["linking_integral"]}',flush=True)
    m={'experiment_id':c['experiment_id'],'modal_controls':modal,'periodic_fluctuation_domains':domains,
        'opposite_helicity_cancellation':{**cancellation,'nonzero_energy':cancellation_energy},
        'modal_exchange':[exchange_case(n,c,True) for n in c['exchange_intervals']],
        'generic_exchange':[exchange_case(n,c) for n in c['exchange_intervals']],
        'unbounded_analytical_helicities':[{'order':o,'samples':[analytical_case(o,t) for t in c['analytical_times']]} for o in c['analytical_orders']],
        'potential_curl_controls':potential_curl_controls(),'known_curve_controls':known,'traced_hopfion_pair':traced,'negative_controls':rejections(c),
        'scope':'Helicity instruments on declared domains and selected analytical closed-fiber pair. No entire-fibration certification, perturbation topology or self-confinement inference.'}
    m['acceptance']=acceptance(m)
    return m,{'time':0,'field':'unbounded analytical Hopfion B','curves':[p.tolist() for p in finest_curves]}


def acceptance(m):
    modal_rows=[r for case in m['modal_controls'] for r in case['samples']]
    periodic_rows=modal_rows+[r for case in m['periodic_fluctuation_domains'] for r in case['samples']]
    checks=[r[k][v] for r in periodic_rows for k in ['magnetic_potential_checks','electric_potential_checks'] for v in ['relative_curl_reconstruction_error','relative_coulomb_divergence']]
    f=m['modal_exchange'];ratio=abs((f[0]['integrated_e_dot_b']-f[1]['integrated_e_dot_b'])/(f[1]['integrated_e_dot_b']-f[2]['integrated_e_dot_b']))
    a=m['unbounded_analytical_helicities'];increments=[abs(x[k]-y[k])/np.pi**2 for x,y in zip(a[-1]['samples'],a[-2]['samples']) for k in ['magnetic_helicity','electric_helicity']]
    curls=m['potential_curl_controls'];curlratios=[curls[i][key]/curls[i+1][key] for i in [0,1] for key in ['curl_a_relative_rms_error','curl_c_relative_rms_error']]
    k=m['known_curve_controls'];t=m['traced_hopfion_pair'];finest_trace=t[-1];valid=all(r['closed'] for case in t for r in case['traces'])
    linkerr=max(abs(k[-1]['linked']['linking_integral']+1),abs(k[-1]['reversed']['linking_integral']-1),abs(k[-1]['unlinked']['linking_integral']))
    known_increment=max(abs(k[-1][key]['linking_integral']-k[-2][key]['linking_integral']) for key in ['linked','reversed','unlinked'])
    return {'modal_helicity_error_below_1e-11':max(r['normalised_modal_error'] for r in modal_rows)<1e-11,
        'potential_reconstruction_coulomb_below_1e-11':max(checks)<1e-11,
        'periodic_gauge_invariance_below_1e-11':max(r['gauge_helicity_error_over_energy'] for r in m['periodic_fluctuation_domains'])<1e-11,
        'periodic_optical_drift_below_1e-11':max([r['optical_drift_over_initial_energy'] for r in m['periodic_fluctuation_domains']]+[r['optical_drift_over_initial_energy'] for r in m['generic_exchange']])<1e-11,
        'generic_exchange_balance_below_1e-4':m['generic_exchange'][-1]['normalised_exchange_defect']<1e-4,
        'modal_exchange_time_second_order':3.5<ratio<4.5,
        'mean_longitudinal_and_open_controls_rejected':m['negative_controls']['mean_rejected'] and m['negative_controls']['longitudinal_rejected'] and m['negative_controls']['open_trace_linking_rejected'] and not m['negative_controls']['uniform_open_trace']['closed'],
        'unbounded_helicities_error_and_increment_below_1e-6':max([r['max_relative_error'] for r in a[-1]['samples']]+increments)<1e-6,
        'bateman_potential_curl_second_order':all(3.5<x<4.5 for x in curlratios) and max(curls[-1]['curl_a_relative_rms_error'],curls[-1]['curl_c_relative_rms_error'])<.01,
        'known_signed_links_error_and_increment_below_5e-4':max(linkerr,known_increment)<5e-4,
        'traces_close_without_large_endpoint_correction':valid and max(r['closure_gap_before_correction'] for r in finest_trace['traces'])<1e-6 and max(r['tangent_mismatch'] for r in finest_trace['traces'])<1e-6,
        'selected_fiber_link_error_and_increment_below_5e-4':bool(valid and abs(abs(finest_trace['link']['linking_integral'])-1)<5e-4 and abs(finest_trace['link']['linking_integral']-t[-2]['link']['linking_integral'])<5e-4),
        'opposite_helicity_cancellation_below_1e-11':abs(m['opposite_helicity_cancellation']['magnetic_helicity'])/m['opposite_helicity_cancellation']['nonzero_energy']<1e-11}


def plot(m,curves,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='eft-s3d';fig=plt.figure(figsize=(11,3.8),constrained_layout=True)
    ax=fig.add_subplot(131,projection='3d')
    for i,p in enumerate(curves['curves']):
        p=np.array(p);ax.plot(*p.T,label=f'B fiber {i+1}')
    ax.set(xlabel='x',ylabel='y',zlabel='z',title='Selected traced Hopfion pair');ax.legend(fontsize=7)
    ax=fig.add_subplot(132);r=next(c for c in m['modal_controls'] if c['mode']==1)['samples']
    for key,label in [('magnetic_helicity','Magnetic'),('electric_helicity','Electric'),('optical_helicity','Optical')]:ax.plot([x['time'] for x in r],[x[key]/(2*np.pi)**3 for x in r],'o-',label=label)
    ax.set(xlabel='Time',ylabel='Helicity / volume',title='Independent Beltrami exchange');ax.legend(fontsize=7)
    ax=fig.add_subplot(133);r=m['traced_hopfion_pair'];ax.loglog([x['segments'] for x in r],[abs(abs(x['link']['linking_integral'])-1) if x['link'] else 1 for x in r],'o-',label='Traced pair')
    k=m['known_curve_controls'];ax.loglog([x['segments'] for x in k],[abs(x['linked']['linking_integral']+1) for x in k],'s--',label='Known linked circles')
    ax.set(xlabel='Polygon segments per curve',ylabel='Absolute link error',title='Gauss-link refinement');ax.legend(fontsize=7)
    fig.savefig(out/'topology.svg',metadata={'Date':None});plt.close(fig)


def run(config_path,output):
    start=time.perf_counter();path=Path(config_path).resolve();c=json.loads(path.read_text());validate(c);out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('new or empty output required')
    out.mkdir(parents=True,exist_ok=True);m,curves=study(c)
    for name,data in [('metrics.json',m),('trace-curves.json',curves)]: (out/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    (out/'config.json').write_bytes(path.read_bytes());plot(m,curves,out)
    root=Path(__file__).resolve().parents[2];sources=[root/'pyproject.toml',root/'uv.lock',*sorted((root/'src').rglob('*.py'))]
    manifest={'experiment_id':c['experiment_id'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'repository':'https://github.com/RDHomeProjects/ElectronFieldTopology','commit':git(root,'rev-parse','HEAD'),
        'dirty_tree':bool(git(root,'status','--porcelain')),'source_sha256':{str(p.relative_to(root)):digest(p) for p in sources},
        'config_sha256':digest(path),'dependency_lock_sha256':digest(root/'uv.lock'),'configuration':c,
        'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'cpu_count':os.cpu_count(),
        'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib']},
        'precision':'float64 / complex128','thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
        'command':sys.argv,'domains':'periodic zero-mean fluctuations for Coulomb helicity; unbounded analytical fields for Bateman helicity and selected curve tracing',
        'units':'c=epsilon_0=mu_0=l0=1, arbitrary dimensionless amplitude','elapsed_seconds':time.perf_counter()-start,
        'artifacts_sha256':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'acceptance':m['acceptance'],'elapsed_seconds':manifest['elapsed_seconds']}));return all(m['acceptance'].values())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if not run(a.config,a.output):raise SystemExit('Verification acceptance failed; retain metrics for investigation.')


if __name__=='__main__':main()
