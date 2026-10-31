"""Bounded one-control-at-a-time return-map diagnosis; no new physical dynamics."""
import argparse
from collections import Counter
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
from .candidates import core_curve
from .offcore import trace_candidate,trace_line
from .return_map import section_coordinates,compare_returns,torus_field,torus_check

EXPECTED={'experiment_id':'S4-C-returnmap-v1','model_id':'B0-Bateman-PQ','pairs':[[2,1],[2,3],[3,2]],
          'time':0,'phase':.17,'primary_offset':[.15,0,0],'replication_offset':[0,0,.2],
          'baseline':{'tolerance':1e-11,'max_step':.075,'max_arclength':80,'samples':128,'near_zero':1e-8,'radius':12,'max_evaluations':20000},
          'variations':{'max_arclength':[20,40],'tolerance':[1e-9,1e-10],'max_step':[.15,.0375],'near_zero':[1e-6,1e-10],'radius':[6,24]},
          'return_comparison_limit':1e-5}


def validate(c):
    if json.dumps(c,sort_keys=True)!=json.dumps(EXPECTED,sort_keys=True):
        raise ValueError('only the predeclared bounded S4-C diagnosis is supported')


def settings(c):
    result=[('baseline',None,None,dict(c['baseline']))]
    for key,values in c['variations'].items():
        for value in values:result.append((f'{key}={value:g}',key,value,{**c['baseline'],key:value}))
    return result


def study(c):
    validate(c); cases=[];replications=[];controls=[]
    for p,q in c['pairs']:
        origin=core_curve(c['phase'],0,p,q,1)[0];seed=origin+c['primary_offset'];family=[]
        for label,key,value,config in settings(c):
            _,meta=trace_candidate(seed,0,p,q,**config)
            row={'pair':[p,q],'label':label,'changed_control':key,'changed_value':value,'settings':config,
                 'trace':meta,'return_map':section_coordinates(meta)}
            family.append(row)
            print(f'({p},{q}) {label}: {meta["status"]}, returns={len(meta["section_returns"])}',flush=True)
        reference=family[0]['trace']
        for row in family:row['prefix_comparison']=compare_returns(reference,row['trace'],c['return_comparison_limit'])
        cases.extend(family)
        seed=origin+c['replication_offset'];_,meta=trace_candidate(seed,0,p,q,**c['baseline'])
        replications.append({'pair':[p,q],'trace':meta,'return_map':section_coordinates(meta)})
    for p,q,offset,label in [(1,1,c['primary_offset'],'offcore_hopfion'),(2,3,[0,0,0],'trefoil_core')]:
        seed=core_curve(c['phase'],0,p,q,1)[0]+offset
        _,meta=trace_candidate(seed,0,p,q,**c['baseline'])
        controls.append({'label':label,'trace':meta,'return_map':section_coordinates(meta)})
    torus=[];phi0=.3;seed=np.array([2+.5*np.cos(phi0),0,.5*np.sin(phi0)])
    for omega in [.5,float(np.sqrt(2))]:
        points,meta=trace_line(torus_field(omega),seed,**{**c['baseline'],'section_normal':[0,1,0]})
        torus.append({'omega':omega,'trace':meta,'return_map':section_coordinates(meta),
                      'analytic_check':torus_check(points,meta,omega,phi0)})
    # Instrument acceptance is independent of whether physical probes close or change under a control.
    maps=[r['return_map'] for r in cases+replications+controls+torus]
    traces=[r['trace'] for r in cases+replications+controls+torus]
    plane=max([abs(e['plane_residual']) for m in maps for e in m['returns']]+[0.])
    checks={'exactly_33_diagnostic_and_3_replication_runs':len(cases)==33 and len(replications)==3,
        'one_control_changes_per_variant':all(sum(r['settings'][k]!=c['baseline'][k] for k in c['baseline'])==1 for r in cases if r['changed_control']),
        'closed_Maxwell_controls_close':all(r['trace']['closed'] for r in controls),
        'manufactured_periodic_control_closes':torus[0]['trace']['closed'],
        'manufactured_irrational_control_not_falsely_closed':not torus[1]['trace']['closed'],
        'manufactured_return_angles_below_1e-6':all(r['analytic_check']['return_count']>=3 and r['analytic_check']['max_wrapped_angle_error']<1e-6 for r in torus),
        'manufactured_torus_residual_below_1e-7':all(r['analytic_check']['max_torus_equation_error']<1e-7 for r in torus),
        'section_plane_residual_below_1e-9':plane<1e-9,
        'every_return_position_retained':all(len(r['return_map']['returns'])==len(r['trace']['section_returns']) for r in cases+replications+controls+torus),
        'unresolved_endpoints_not_corrected':all(r['endpoint_correction']==0 for r in traces if not r['closed'])}
    return {'experiment_id':c['experiment_id'],'diagnostic_cases':cases,'replications':replications,'closed_controls':controls,
        'manufactured_torus_controls':torus,'status_counts':dict(Counter(r['trace']['status'] for r in cases)),
        'comparison_counts':dict(Counter(r['prefix_comparison']['comparison'] for r in cases)),
        'max_section_plane_residual':plane,'acceptance':checks,
        'Maxwell_angular_interpretation':'not_assigned: no invariant surface or angular coordinate certified',
        'scope':'three selected Maxwell snapshot seeds and three replications; no complete orbit classification or new dynamics'}


def plots(m,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='eft-s4c'
    fig,axs=plt.subplots(1,3,figsize=(12,3.8),layout='constrained')
    for ax,pair in zip(axs,[[2,1],[2,3],[3,2]]):
        rows=[r for r in m['diagnostic_cases'] if r['pair']==pair]
        for r in rows:
            xy=np.array([v['plane_coordinates'] for v in r['return_map']['returns']])
            if len(xy):ax.plot(xy[:,0],xy[:,1],'o-' if r['label']=='baseline' else '.',alpha=1 if r['label']=='baseline' else .4,
                              label=r['label'] if r['label']=='baseline' else None)
        ax.scatter(0,0,marker='x',color='black',label='seed');ax.set(xlabel='section coordinate 1',ylabel='section coordinate 2',title=str(tuple(pair)));ax.legend(fontsize=8)
    fig.suptitle('Finite Maxwell return sections; baseline plus independent control variations\nConnected markers show return order, not field-line segments or an invariant torus',fontsize=11)
    fig.savefig(out/'return-sections.svg',metadata={'Date':None});fig.savefig(out/'return-sections.png',dpi=140);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
    for ax,row in zip(axs,m['manufactured_torus_controls']):
        positions=np.array([r['position'] for r in row['trace']['section_returns']]);phi=np.arctan2(positions[:,2],np.hypot(positions[:,0],positions[:,1])-2)
        n=np.arange(1,len(phi)+1);expected=np.angle(np.exp(1j*(.3+2*np.pi*row['omega']*n)))
        ax.plot(n,expected,'o',label='analytic angle');ax.plot(n,phi,'x',label='numerical return')
        ax.set(xlabel='positive return index',ylabel='wrapped torus angle / rad',
               title='periodic target' if row['omega']==.5 else 'irrational-frequency analytic target');ax.legend()
    fig.suptitle('Manufactured torus controls only; these angles are not assigned to Maxwell traces',fontsize=11)
    fig.savefig(out/'torus-controls.svg',metadata={'Date':None});fig.savefig(out/'torus-controls.png',dpi=140);plt.close(fig)


def run(config,output):
    start=time.perf_counter();path=Path(config).resolve();c=json.loads(path.read_text());validate(c);out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('new/empty output required')
    out.mkdir(parents=True,exist_ok=True);m=study(c);plots(m,out)
    for name,data in [('metrics.json',m),('config.json',c)]: (out/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    root=Path(__file__).resolve().parents[2]
    manifest={'experiment_id':c['experiment_id'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'github_base_commit':'8696b4190bbc739eea366f061bfbee66a9c82662','local_code_commit':git(root,'rev-parse','HEAD'),
        'local_code_commit_note':'Local snapshot; source hashes bind the published implementation and retained outputs.',
        'dirty_tree':bool(git(root,'status','--porcelain')),'source_sha256':{str(p.relative_to(root)):digest(p) for p in sorted((root/'src').rglob('*.py'))},
        'config_sha256':digest(path),'dependency_lock_sha256':digest(root/'uv.lock'),'python':sys.version,'platform':platform.platform(),
        'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib']},
        'thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']},'elapsed_seconds':time.perf_counter()-start,
        'units':'B0 dimensionless conventions; torus controls are synthetic geometric flows, not physical units',
        'artifacts_sha256':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'acceptance':m['acceptance'],'status_counts':m['status_counts'],'comparison_counts':m['comparison_counts'],'elapsed_seconds':manifest['elapsed_seconds']},indent=2))
    return all(m['acceptance'].values())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if not run(a.config,a.output):raise SystemExit('Instrument acceptance incomplete; retain diagnostics for investigation.')


if __name__=='__main__':main()
