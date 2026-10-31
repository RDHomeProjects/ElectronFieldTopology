"""Reproducible bounded S4-B sampling; failed closure remains a result."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
import numpy as np
from .benchmark import digest, git
from .candidates import core_curve, coordinates, candidate
from .offcore import trace_candidate, transport_velocity, initial_null_checks
from .knot_diagram import invariant_gate, diagram_link, VIEWS
from .linking import gauss_link

EXPECTED = {'experiment_id':'S4-B-offcore-v1', 'model_id':'B0-Bateman-PQ',
            'pairs':[[1,1],[2,1],[2,3],[3,2]], 'times':[0,.75],
            'offsets':[[0,0,0],[.15,0,0],[0,0,.2]], 'phase':.17, 'seed':31415,
            'tolerances':[1e-9,1e-11], 'max_steps':[.15,.075], 'arclength_budgets':[40,80],
            'segments':[128,256], 'near_zero_floor':1e-8, 'observation_radius':12, 'max_evaluations':20000}


def validate(config):
    if json.dumps(config, sort_keys=True) != json.dumps(EXPECTED, sort_keys=True):
        raise ValueError('only the predeclared bounded S4-B experiment is supported')


def study(config):
    validate(config); c = config; cases = []; curves = []; local = []
    points = np.random.default_rng(c['seed']).uniform(-1.1, 1.1, (32,3))
    for p,q in c['pairs']:
        local.append({'pair':[p,q], **initial_null_checks(points,p,q)})
        origin = core_curve(c['phase'],0,p,q,1)[0]
        for index, offset in enumerate(c['offsets']):
            seed0 = origin+offset
            for t in c['times']:
                seed = seed0+t*transport_velocity(seed0,0)
                levels = []; stored = []
                for resolution in range(2):
                    curve, meta = trace_candidate(seed,t,p,q,tolerance=c['tolerances'][resolution],
                        max_step=c['max_steps'][resolution],max_arclength=c['arclength_budgets'][resolution],
                        samples=c['segments'][resolution],near_zero=c['near_zero_floor'],
                        radius=c['observation_radius'],max_evaluations=c['max_evaluations'])
                    levels.append(meta); stored.append(curve)
                status = levels[-1]['status']; drift = None; length_error = None; invariants = []
                if all(row['closed'] for row in levels):
                    drift = float(np.max(np.linalg.norm(stored[0]-stored[1][::2],axis=-1)))
                    a,b = [row['accepted_return']['arclength'] for row in levels]
                    length_error = abs(a-b)/max(1.,abs(b))
                    status = 'closed_refined' if drift < 1e-5 and length_error < 1e-5 else 'inconclusive_refinement'
                elif levels[-1]['closed']: status = 'closure_only_at_extended_budget'
                if levels[-1]['closed']:
                    invariants = [invariant_gate(stored[-1][::stride]) for stride in [4,2,1]]
                topology_passed = bool(invariants and all(r['agreed'] for r in invariants)
                                       and len({r['determinant'] for r in invariants})==1)
                ai,bi = coordinates(seed0,0); at,bt = coordinates(seed,t)
                row = {'pair':[p,q],'time':t,'seed_index':index,'seed_kind':'core_control' if index==0 else 'off_core',
                    'initial_offset':offset,'status':status,'refinements':levels,'curve_refinement_max_distance':drift,
                    'accepted_length_relative_difference':length_error,'projection_invariants':invariants,
                    'topology_invariant_gate_passed':topology_passed,'knot_type':'not_identified',
                    'seed_transport_coordinate_error':float(max(abs(at-ai),abs(bt-bi)))}
                cases.append(row);curves.append({'pair':[p,q],'time':t,'seed_index':index,'status':status,
                    'closed':levels[-1]['closed'],'points':stored[-1].tolist()})
                print(f'({p},{q}) seed={index} t={t}: {status}; invariant={topology_passed}',flush=True)
    links = []
    for p,q in c['pairs']:
        for t in c['times']:
            samples = []
            for n in c['segments']:
                theta=np.linspace(0,2*np.pi,n+1)
                a=core_curve(theta,t,p,q,1)[0];b=core_curve(theta,t,p,q,-1)[0];a[-1]=a[0];b[-1]=b[0]
                gauss=gauss_link(a,b)['linking_integral'];diagrams=[]
                for view in VIEWS:
                    try:diagrams.append({'status':'regular',**diagram_link(a,b,view)})
                    except ValueError as error:diagrams.append({'status':'unresolved_projection','reason':str(error)})
                valid=[r['linking_number'] for r in diagrams if r['status']=='regular']
                passed=len(valid)>=2 and len(set(valid))==1 and abs(gauss-valid[0])<.02
                samples.append({'segments':n,'gauss':gauss,'diagrams':diagrams,'agreed_with_gauss':passed})
            links.append({'pair':[p,q],'time':t,'samples':samples})
    guards=[]
    for seed in [[0,0,0],[1e-10,0,0],[1,0,0]]:
        _,guard=trace_candidate(seed,0,2,3);guards.append(guard)
    velocity=transport_velocity(np.array([[0,0,0],[1,0,0],[1e-10,0,0]]),0)
    checks={'all_eight_core_controls_close_on_refinement':all(r['refinements'][-1]['closed'] for r in cases if r['seed_kind']=='core_control'),
        'closed_refined_polygons_pass_independent_invariants':all(r['topology_invariant_gate_passed'] for r in cases if r['status']=='closed_refined'),
        'closed_polygons_exist':any(r['status']=='closed_refined' for r in cases),
        'independent_diagram_links_agree_with_gauss':all(s['agreed_with_gauss'] for r in links for s in r['samples']),
        'initial_sample_null_below_1e-12':all(r['max_normalised_null']<1e-12 for r in local),
        'initial_sample_complex_curl_finest_below_0.002':all(r['complex_curl'][-1]['max_normalised_complex_curl']<.002 for r in local),
        'zero_and_near_zero_seeds_guarded':all(g['status']=='near_zero_guard' and g['function_evaluations']==0 for g in guards),
        'normalised_flow_extension_finite_unit':bool(np.isfinite(velocity).all() and np.max(abs(np.linalg.norm(velocity,axis=-1)-1))<1e-12),
        'advected_seed_coordinate_error_below_1e-12':all(r['seed_transport_coordinate_error']<1e-12 for r in cases),
        'unresolved_traces_not_artificially_closed':all(not r['refinements'][-1]['closed'] and r['refinements'][-1]['endpoint_correction']==0 for r in cases if r['status']=='unresolved_budget')}
    return {'experiment_id':c['experiment_id'],'cases':cases,'status_counts':dict(Counter(r['status'] for r in cases)),
        'initial_condition_samples':local,'independent_core_link_checks':links,'nodal_guard_controls':guards,
        'acceptance':checks,'scope':'Finite-budget traces of fixed unbounded analytical B fields, not isolated dynamics, a complete knot identifier or a confinement result.'},curves


def plots(metrics,curves,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='eft-s4b'
    fig=plt.figure(figsize=(12,4),layout='constrained')
    for j,pair in enumerate([[1,1],[2,1],[2,3],[3,2]]):
        ax=fig.add_subplot(1,4,j+1,projection='3d')
        for row in curves:
            if row['pair']!=pair or row['time']!=.75:continue
            x=np.asarray(row['points']);ax.plot(*x.T,lw=1,label=f"seed {row['seed_index']}: {'closure candidate' if row['closed'] else 'unresolved/guarded'}")
            ax.scatter(*x[0],s=13,color='black');ax.scatter(*x[-1],s=14,marker='x',color='red')
        ax.set(xlabel='x',ylabel='y',zlabel='z',title=str(tuple(pair)),xlim=(-4,4),ylim=(-4,4),zlim=(-4,4))
        ax.set_box_aspect((1,1,1));ax.legend(fontsize=5,loc='lower left')
    fig.suptitle('Independent B-field traces at t=.75; core control plus two off-core seeds\nEqual units, common display window; open endpoints are never joined',fontsize=11)
    fig.savefig(out/'offcore-traces.svg',metadata={'Date':None});fig.savefig(out/'offcore-traces.png',dpi=140);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
    counts=metrics['status_counts'];axs[0].bar(list(counts),list(counts.values()),color='#327e9c');axs[0].tick_params(axis='x',labelrotation=18,labelsize=8)
    axs[0].set(ylabel='Trace cases (24 total)',title='Retained closure/budget outcomes')
    for row in metrics['initial_condition_samples']:
        x=row['complex_curl'];axs[1].loglog([v['step'] for v in x],[v['max_normalised_complex_curl'] for v in x],'o-',label=str(tuple(row['pair'])))
    axs[1].set(xlabel='Spatial difference step',ylabel='Maximum sampled normalised |F dot curl F|',title='Initial-condition residual; not a global proof');axs[1].legend()
    fig.savefig(out/'offcore-validation.svg',metadata={'Date':None});fig.savefig(out/'offcore-validation.png',dpi=140);plt.close(fig)


def run(config,output):
    start=time.perf_counter();path=Path(config).resolve();c=json.loads(path.read_text());validate(c)
    out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('new/empty output directory required')
    out.mkdir(parents=True,exist_ok=True);m,curves=study(c);plots(m,curves,out)
    for name,data in [('metrics.json',m),('trace-curves.json',curves),('config.json',c)]:
        (out/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    root=Path(__file__).resolve().parents[2]
    manifest={'experiment_id':c['experiment_id'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'github_base_commit':'1652b0194902209c2a6c01ded8cc4baef4fd4874','local_code_commit':git(root,'rev-parse','HEAD'),
        'local_code_commit_note':'Local materialisation commit; source hashes below are authoritative for reproduction.',
        'dirty_tree':bool(git(root,'status','--porcelain')),'source_sha256':{str(p.relative_to(root)):digest(p) for p in sorted((root/'src').rglob('*.py'))},
        'config_sha256':digest(path),'dependency_lock_sha256':digest(root/'uv.lock'),'python':sys.version,'platform':platform.platform(),
        'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib']},
        'thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']},
        'elapsed_seconds':time.perf_counter()-start,'precision':'float64 / complex128; exact integer Fox cofactors',
        'domain':'unbounded analytical Maxwell fields; tracing-radius and length guards are observation budgets, not physical walls',
        'units':'c=epsilon_0=mu_0=l0=1, raw pq amplitude; F=E+iB',
        'artifacts_sha256':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'acceptance':m['acceptance'],'elapsed_seconds':manifest['elapsed_seconds']},indent=2))
    return all(m['acceptance'].values())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if not run(args.config,args.output):raise SystemExit('Instrument acceptance incomplete; retain all outcomes for investigation.')


if __name__=='__main__':main()
