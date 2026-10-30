"""Bounded S4-A catalogue, independent references and graphics; Apache-2.0."""
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
from .candidates import candidate,coordinates,potentials,reference,catalogue,core_curve,core_level,trace_core
from .diagnostics import energy_flow,maxwell_residuals
from .fields import hopfion
from .linking import gauss_link
from .localisation import all_space_rule
from .perturbations import null_scores


def validate(c):
    required={'model_id':'B0-Bateman-PQ','pairs':[[1,1],[2,1],[2,3],[3,2]],'times':[0,.75],
        'orders':[24,40,64],'difference_steps':[.04,.02,.01],'segments':[128,256,512],
        'trace_tolerance':1e-9,'trace_max_step':.15,'trace_max_arclength':80,'trace_refinement_tolerance':1e-11,
        'trace_seed_phase':.17,'slice_grid':161,'slice_half_extent':4,'seed':31415,
        'requests':[[1,1],[2,1],[2,3],[3,2],[0,1],[-1,2],[1.5,2],[2,2],[4,5],[True,1]]}
    if any(c[k]!=v for k,v in required.items()):raise ValueError('only the declared bounded catalogue is supported')


def integrals(p,q,t,order):
    x,w=all_space_rule(order,2*order);e,b=candidate(x,t,p,q);u,s=energy_flow(e,b);a,cc=potentials(x,t,p,q)
    values={'energy':float(np.sum(w*u)),'momentum':np.sum(w[...,None]*s,axis=(0,1,2)).tolist(),
        'magnetic_helicity':float(np.sum(w*np.sum(a*b,axis=-1))),'electric_helicity':float(np.sum(w*np.sum(cc*e,axis=-1)))}
    ref=reference(p,q);err=max(abs(values[k]-ref[k])/abs(ref[k]) for k in ['energy','magnetic_helicity','electric_helicity'])
    err=max(err,float(np.linalg.norm(np.array(values['momentum'])-ref['momentum'])/ref['energy']))
    return {'time':t,'angular_order':order,'radial_order':2*order,**values,'reference':ref,'max_reference_error':err}


def local_checks(p,q,c,points):
    rows=[]
    for t in c['times']:
        e,b=candidate(points,t,p,q);denom=np.sqrt(np.mean(e*e+b*b));res=[]
        for h in c['difference_steps']:
            r=maxwell_residuals(points,t,h,field=lambda x,t:candidate(x,t,p,q))
            combined=np.mean(r['div_e']**2)+np.mean(r['div_b']**2)+np.mean(np.sum(r['faraday']**2,axis=-1))+np.mean(np.sum(r['ampere']**2,axis=-1))
            res.append({'step':h,'combined_normalised_rms':float(np.sqrt(combined)/denom),
                **{k:float(np.sqrt(np.mean(v*v))/denom) for k,v in r.items()}})
        rows.append({'time':t,'null_scores':null_scores(e,b),'maxwell':res})
    return rows


def core_checks(p,q,t,n):
    theta=np.linspace(0,2*np.pi,n+1);curves=[];checks=[]
    for sign in [1,-1]:
        x,derivative=core_curve(theta,t,p,q,sign);b=candidate(x,t,p,q)[1]
        cross=np.linalg.norm(np.cross(derivative,b),axis=-1)/(np.linalg.norm(derivative,axis=-1)*np.linalg.norm(b,axis=-1))
        value,mag=core_level(x,t,p,q);alpha,beta=coordinates(x,t)
        # The advected Bateman coordinates should equal the initial coordinates.
        initial,_=core_curve(theta,0,p,q,sign);ai,bi=coordinates(initial,0)
        checks.append({'sign':sign,'max_tangent_sine_error':float(np.max(cross)),
            'max_core_level_relative_error':float(np.max(np.abs(value-sign*mag))/mag),
            'max_transport_coordinate_error':float(max(np.max(np.abs(alpha-ai)),np.max(np.abs(beta-bi))))})
        curves.append(x)
    link=gauss_link(*curves)
    return {'time':t,'segments':n,'cores':checks,'link':link,'winding_product_reference':p*q,
            'relative_link_error':abs(abs(link['linking_integral'])/(p*q)-1)}


def study(c):
    points=np.random.default_rng(c['seed']).uniform(-1.3,1.3,(80,3));rows=[];saved=[]
    ledger=catalogue(c['requests'])
    for p,q in c['pairs']:
        numeric=[{'order':o,'samples':[integrals(p,q,t,o) for t in c['times']]} for o in c['orders']]
        checks=[core_checks(p,q,t,n) for t in c['times'] for n in c['segments']]
        traces=[]
        for t in c['times']:
            for sign in [1,-1]:
                curve,meta=trace_core(p,q,t,sign,phase=c['trace_seed_phase'],tolerance=c['trace_tolerance'],max_step=c['trace_max_step'],max_arclength=c['trace_max_arclength'],samples=128)
                traces.append(meta);saved.append({'pair':[p,q],'time':t,'sign':sign,'points':curve.tolist(),'closed':meta['closed']})
        refinement=[]
        if [p,q]==[2,3]:
            for t in c['times']:
                _,meta=trace_core(p,q,t,1,phase=c['trace_seed_phase'],tolerance=c['trace_refinement_tolerance'],max_step=c['trace_max_step']/2,max_arclength=c['trace_max_arclength'],samples=128)
                refinement.append(meta)
        rows.append({'pair':[p,q],'reference':reference(p,q),'local_checks':local_checks(p,q,c,points),
            'all_space':numeric,'parameterised_core_checks':checks,'independent_traces':traces,'trefoil_refinement':refinement})
        print(f'pair=({p},{q}): integral error={max(x["max_reference_error"] for x in numeric[-1]["samples"]):.3g}, traces closed={sum(x["closed"] for x in traces)}/{len(traces)}',flush=True)
    e,b=candidate(points,.3,1,1);er,br=hopfion(points,.3)
    baseline=float(np.sqrt(np.sum((e-er)**2+(b-br)**2)/np.sum(er*er+br*br)))
    _,guard=trace_core(2,3,0,1,phase=.8,tolerance=c['trace_tolerance'],max_step=c['trace_max_step'],max_arclength=30,samples=64)
    m={'return_section_guard':guard,'experiment_id':c['experiment_id'],'catalogue_ledger':ledger,'candidates':rows,'baseline_relative_field_error':baseline,
        'scope':'Four fixed unbounded null Maxwell monomial candidates. Published parameterised cores and independent seed traces at two times; no arbitrary-line knot certificate, optimiser or electron claim.'}
    m['acceptance']=acceptance(m,c)
    return m,{'traces':saved,'coordinate_units':'dimensionless','note':'Independent ODE samples; only closure-qualified endpoints corrected, correction recorded in metrics.'}


def acceptance(m,c):
    rows=m['candidates'];local=[r for x in rows for r in x['local_checks']];fine=[r for x in rows for r in x['all_space'][-1]['samples']]
    ratios=[r['maxwell'][i]['combined_normalised_rms']/r['maxwell'][i+1]['combined_normalised_rms'] for r in local for i in [0,1]]
    increments=[]
    for x in rows:
        for a,b in zip(x['all_space'][-1]['samples'],x['all_space'][-2]['samples']):
            increments += [abs(a[k]-b[k])/abs(a['reference'][k]) for k in ['energy','magnetic_helicity','electric_helicity']]
            increments.append(float(np.linalg.norm(np.array(a['momentum'])-b['momentum'])/a['reference']['energy']))
    cores=[r for x in rows for case in x['parameterised_core_checks'] for r in case['cores']]
    traces=[r for x in rows for r in x['independent_traces']+x['trefoil_refinement']]
    link_increments=[]
    for x in rows:
        for t in c['times']:
            checks=[r for r in x['parameterised_core_checks'] if r['time']==t]
            link_increments.append(abs(abs(checks[-1]['link']['linking_integral'])-abs(checks[-2]['link']['linking_integral']))/checks[-1]['winding_product_reference'])
    return {'baseline_agreement_below_1e-12':m['baseline_relative_field_error']<1e-12,
        'null_scores_below_1e-12':max(r['null_scores']['combined_null_score'] for r in local)<1e-12,
        'maxwell_residuals_second_order':all(3.5<r<4.5 for r in ratios),
        'maxwell_finest_below_0.01':max(r['maxwell'][-1]['combined_normalised_rms'] for r in local)<.01,
        'integral_reference_and_increment_below_1e-5':max([r['max_reference_error'] for r in fine]+increments)<1e-5,
        'analytic_core_tangent_below_1e-10':max(r['max_tangent_sine_error'] for r in cores)<1e-10,
        'core_level_and_transport_below_1e-10':max(max(r['max_core_level_relative_error'],r['max_transport_coordinate_error']) for r in cores)<1e-10,
        'independent_traces_close':all(r['closed'] and r['accepted_return']['closure_gap']<1e-6 and r['accepted_return']['tangent_mismatch']<1e-6 for r in traces),
        'traced_core_level_below_1e-5':max(r['max_core_level_relative_error'] for r in traces)<1e-5,
        'selected_core_link_error_and_increment_below_0.005':max([r['relative_link_error'] for x in rows for r in x['parameterised_core_checks'] if r['segments']==c['segments'][-1]]+link_increments)<.005,
        'section_guard_skips_nonclosing_return':bool(m['return_section_guard']['closed'] and m['return_section_guard']['section_returns'][0]['closure_gap']>1e-3 and m['return_section_guard']['accepted_return']['closure_gap']<1e-6),
        'ledger_retains_invalid_and_deferred':{r['status'] for r in m['catalogue_ledger']}=={'admitted','invalid_parameters','deferred_budget','deferred_link_family'}}


def plots(m,c,out,traces=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='eft-s4a'
    fig=plt.figure(figsize=(14,7),constrained_layout=True)
    theta=np.linspace(0,2*np.pi,513)
    for j,(p,q) in enumerate(c['pairs']):
        for i,t in enumerate(c['times']):
            ax=fig.add_subplot(2,4,4*i+j+1,projection='3d');cloud=[]
            for sign,color in [(1,'#d95f02'),(-1,'#1b65a7')]:
                x,_=core_curve(theta,t,p,q,sign);cloud.append(x);ax.plot(*x.T,color=color,lw=1.4,label='positive core' if sign==1 else 'negative core')
            limit=c['slice_half_extent'];ax.set(xlim=(-limit,limit),ylim=(-limit,limit),zlim=(-limit,limit));ax.set_box_aspect((1,1,1))
            ax.set(xlabel='x',ylabel='y',zlabel='z',title=f'(p,q)=({p},{q}), t={t:g}')
            ax.tick_params(labelsize=7)
            if i==0 and j==0:ax.legend(fontsize=7,loc='upper left')
    fig.suptitle('Published parameterised magnetic cores, verified against the field\nCommon [-4,4] window and equal coordinate units; ODE checks are reported separately',fontsize=12)
    fig.savefig(out/'core-gallery.svg',metadata={'Date':None});plt.close(fig)
    axis=np.linspace(-c['slice_half_extent'],c['slice_half_extent'],c['slice_grid']);x,z=np.meshgrid(axis,axis,indexing='xy');points=np.stack([x,np.zeros_like(x),z],axis=-1)
    fig,axs=plt.subplots(2,4,figsize=(13,6.6),constrained_layout=True);slices=[]
    for j,(p,q) in enumerate(c['pairs']):
        for i,t in enumerate(c['times']):
            u,_=energy_flow(*candidate(points,t,p,q));peak=float(np.max(u));image=axs[i,j].imshow(np.log10(np.maximum(u/peak,1e-12)),origin='lower',extent=[axis[0],axis[-1],axis[0],axis[-1]],vmin=-4,vmax=0,cmap='magma')
            axs[i,j].set(xlabel='x',ylabel='z',title=f'({p},{q}), t={t:g}; slice peak={peak:.3g}')
            slices.append({'pair':[p,q],'time':t,'sampled_slice_peak':peak,'plane':'y=0','normalisation':'own panel peak; not common absolute energy or total energy'})
    fig.colorbar(image,ax=axs,label=r'$\log_{10}(u/u_{\rm slice\ peak})$; display clipped below -4',shrink=.82)
    fig.suptitle('Energy-density slices in a fixed observation window\nEach panel uses its own sampled peak; colours are not absolute-energy comparisons',fontsize=12)
    fig.savefig(out/'energy-slices.svg',metadata={'Date':None});plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(12,3.7),constrained_layout=True)
    for row in m['candidates']:
        label=str(tuple(row['pair']));r=row['local_checks'][-1]['maxwell'];axs[0].loglog([s['step'] for s in r],[s['combined_normalised_rms'] for s in r],'o-',label=label)
        r=row['all_space'];axs[1].semilogy([s['order'] for s in r],[max(v['max_reference_error'] for v in s['samples']) for s in r],'o-',label=label)
        r=[x for x in row['parameterised_core_checks'] if x['time']==0];axs[2].loglog([x['segments'] for x in r],[x['relative_link_error'] for x in r],'o-',label=label)
    axs[0].set(xlabel='Difference step',ylabel='Normalised Maxwell RMS',title='Local equation verification at t=.75')
    axs[1].set(xlabel='Angular quadrature order',ylabel='Maximum reference error',title='Independent integral references')
    axs[2].set(xlabel='Segments per core',ylabel='Relative Gauss-link error',title='Selected core-pair convergence')
    for ax in axs:ax.legend(title='(p,q)',fontsize=7)
    fig.savefig(out/'validation.svg',metadata={'Date':None});plt.close(fig)
    if traces is not None:
        fig=plt.figure(figsize=(10,4.7),constrained_layout=True)
        for i,t in enumerate(c['times']):
            ax=fig.add_subplot(1,2,i+1,projection='3d');ref,_=core_curve(theta,t,2,3,1)
            actual=next(r for r in traces['traces'] if r['pair']==[2,3] and r['time']==t and r['sign']==1)
            actual=np.asarray(actual['points']);ax.plot(*ref.T,color='#555555',lw=1.6,label='Published positive core')
            ax.scatter(*actual.T,s=7,color='#d95f02',label='Independent B-field ODE samples',depthshade=False)
            ax.set(xlim=(-3,3),ylim=(-3,3),zlim=(-3,3),xlabel='x',ylabel='y',zlabel='z',title=f'Trefoil core (2,3), t={t:g}');ax.set_box_aspect((1,1,1));ax.legend(fontsize=7)
        fig.suptitle('Independent trace versus the parameterised reference\nCommon window and coordinate scaling; points are sampled uniformly in arclength',fontsize=11)
        fig.savefig(out/'trace-comparison.svg',metadata={'Date':None});plt.close(fig)
    return slices


def run(config_path,output):
    start=time.perf_counter();path=Path(config_path).resolve();c=json.loads(path.read_text());validate(c);out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('new or empty output required')
    out.mkdir(parents=True,exist_ok=True);m,traces=study(c);m['energy_slice_metadata']=plots(m,c,out,traces)
    for name,data in [('metrics.json',m),('trace-curves.json',traces)]: (out/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    (out/'config.json').write_bytes(path.read_bytes())
    root=Path(__file__).resolve().parents[2];sources=[root/'pyproject.toml',root/'uv.lock',*sorted((root/'src').rglob('*.py'))]
    manifest={'experiment_id':c['experiment_id'],'created_utc':datetime.now(timezone.utc).isoformat(),'repository':'https://github.com/RDHomeProjects/ElectronFieldTopology',
        'commit':git(root,'rev-parse','HEAD'),'dirty_tree':bool(git(root,'status','--porcelain')),
        'source_sha256':{str(p.relative_to(root)):digest(p) for p in sources},'config_sha256':digest(path),'dependency_lock_sha256':digest(root/'uv.lock'),'configuration':c,
        'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'cpu_count':os.cpu_count(),
        'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib']},'precision':'float64 / complex128',
        'thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},'command':sys.argv,
        'domain':'unbounded analytical fields and Bateman potentials; compactified integrals; fixed plotting observation windows',
        'units':'c=epsilon_0=mu_0=l0=1; raw pq multiplier, no fitted amplitude','elapsed_seconds':time.perf_counter()-start,
        'artifacts_sha256':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'acceptance':m['acceptance'],'elapsed_seconds':manifest['elapsed_seconds']}));return all(m['acceptance'].values())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    if not run(args.config,args.output):raise SystemExit('Acceptance failed; retain catalogue and inconclusive traces for investigation.')


if __name__=='__main__':main()
