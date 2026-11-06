"""S5-B-009 unchanged D4 objective; explicit optimizer settling controller. Apache-2.0.

The CG iteration below is copied from sf_readmission.relax at commit5bf6ae24.
Only observation, checkpoint identity, stopping and work allocation differ.
"""
import json
import os
from pathlib import Path
import time
import numpy as np
from scipy.fft import dstn,idstn
from .sf_readmission import static_value_gradient,cone,stationarity,admitted,checkpoint
from .sf_time import Grid
from .sf_time_run import MODEL,SCHEME,canonical_sha,initialize,state_sha
from .sf_dynamics_admission import sha
from .sf_checkpoints import timestamp,atomic_json
from .skyrme import K,NORTH,rational_field
from .sf_tail_domain import compare_fields
from .sf_q1_metrics import measure
FILES=['sf_q1_metrics.py','sf_q1_settling.py','sf_q1_campaign.py','sf_q1_local.py','sf_tail_domain.py','sf_readmission.py','sf_time.py','sf_time_run.py','sf_dynamics.py','skyrme.py','sf_checkpoints.py','sf_dynamics_admission.py','sf_motion_diagnostics.py','sf_motion_metrics.py','sf_time_initial.py','sf_time_controls.py']
class TopologyFailure(ValueError):pass

def code_hashes():return {name:sha(Path(__file__).with_name(name)) for name in FILES}
def seed(folder,n,g,config):
    folder.mkdir(parents=True,exist_ok=True);cs=canonical_sha(config);code=canonical_sha(code_hashes())
    atomic_json(folder/'config.json',config)
    atomic_json(folder/'manifest.json',{'started_at':timestamp(),'config_sha256':cs,'code_sha256':code,'code_hashes':code_hashes(),'model':MODEL,'scheme':SCHEME,'config':config})
    for name in ['initial.npz','latest.npz']:checkpoint(folder/name,n,g,1,cs,0,0,code)
    atomic_json(folder/'history.json',[{'recorded_at':timestamp(),'iteration':0,'pass_index':0,**stationarity(n,g)}])
def checked(folder,config):
    meta=json.loads((folder/'manifest.json').read_text());cs=canonical_sha(config);codes=canonical_sha(code_hashes())
    if meta['config_sha256']!=cs or meta['code_sha256']!=codes:raise ValueError('Checkpoint manifest identity differs')
    g=Grid((config['nodes'],)*3,(config['length'],)*3,'fixed')
    with np.load(folder/'latest.npz',allow_pickle=False) as d:
        n=d['field'].copy();v=d['field_rate']
        if n.shape!=g.shape+(3,) or n.dtype!=np.float64 or not np.isfinite(n).all():raise ValueError('Invalid field')
        if str(d['model_id'])!=MODEL or str(d['scheme'])!=SCHEME or int(d['expected_q'])!=1 or float(d['h'])!=g.spacing[0]:raise ValueError('Checkpoint model/grid differs')
        if str(d['config_sha256'])!=cs or str(d['code_sha256'])!=codes:raise ValueError('Checkpoint embedded identity differs')
        if v.shape!=n.shape or v.dtype!=np.float64:raise ValueError('Checkpoint rate shape/precision differs')
        if np.max(abs(v))!=0 or np.max(abs(n[g.fixed_mask()]-NORTH))!=0 or np.max(abs(np.sum(n*n,axis=-1)-1))>=1e-10:raise ValueError('Checkpoint constraints differ')
    return n,g

def small(value,limit):return isinstance(value,(int,float)) and np.isfinite(value) and value<=limit

def stable_intervals(rows,study):
    k=study['stable_intervals'];rows=[r for r in rows if r['regular_observation']]
    if len(rows)<k+1:return False
    rows=rows[-(k+1):]
    return all(b['iteration']-a['iteration']==study['observe_every'] and
        small(b.get('tail_fraction_change'),study['tail_fraction_change']) and
        small(b.get('shell_energy_change'),study['shell_energy_change']) and
        small(b.get('core_field_relative_change'),study['core_field_relative_change']) and
        small(b.get('hamiltonian_relative_change'),study['hamiltonian_relative_change'])
        for a,b in zip(rows,rows[1:]))

def settled(out,metrics,config,study,iteration):
    p=out/'observations.json';rows=json.loads(p.read_text()) if p.exists() else []
    return bool(rows) and rows[-1]['iteration']==iteration and rows[-1]['regular_observation'] and admitted(metrics,config['q'],config) and stable_intervals(rows,study)

def observe(out,n,g,iteration,study,config,force=False):
    p=out/'observations.json';rows=json.loads(p.read_text()) if p.exists() else []
    # An atomic field checkpoint can precede a hard kill; discard no newer immutable observation.
    if rows and rows[-1]['iteration']>iteration:raise ValueError('Observation is newer than restart checkpoint')
    if rows and rows[-1]['iteration']==iteration:return
    regular=iteration%study['observe_every']==0
    if not regular and not force:return
    measurement=measure(n,g,config['q'],study)
    row={'recorded_at':timestamp(),'iteration':iteration,'regular_observation':regular,**measurement}
    previous=next((r for r in reversed(rows) if r['regular_observation']),None)
    if previous:
        path=out/previous['snapshot'];
        if sha(path)!=previous['checkpoint_sha256']:raise ValueError('Retained observation checkpoint changed')
        with np.load(path,allow_pickle=False) as d:old=d['field'].copy()
        comp=compare_fields(old,g,n,g,study['common_nodes']);row['previous_core_comparison']=comp
        row['tail_fraction_change']=abs(row['shell_fraction']-previous['shell_fraction']) if row['shell_fraction'] is not None and previous['shell_fraction'] is not None else None
        row['shell_energy_change']=abs(row['shell_energy']-previous['shell_energy'])
        row['core_field_relative_change']=comp['field_relative_l2'] if comp['field_relative_l2'] is not None else None
        row['hamiltonian_relative_change']=abs(row['discrete_hamiltonian']-previous['discrete_hamiltonian'])/max(abs(previous['discrete_hamiltonian']),1e-30)
    snap=out/'observations'/f'iteration-{iteration:06d}.npz';snap.parent.mkdir(exist_ok=True)
    if snap.exists():
        with np.load(snap,allow_pickle=False) as d:
            if not np.array_equal(d['field'],n):raise ValueError('Existing immutable observation differs')
    else:checkpoint(snap,n,g,config['q'],canonical_sha(config),iteration,0,canonical_sha(code_hashes()))
    row.update(snapshot=snap.relative_to(out).as_posix(),checkpoint_sha256=sha(snap))
    rows.append(row);atomic_json(p,rows)
    print(json.dumps({'message':'Tail/core settling observation','recorded_at':timestamp(),'case':out.name,'iteration':iteration,'tail_fraction':row['shell_fraction'],'three_intervals_stable':stable_intervals(rows,study)}),flush=True)

def relax_settling(config,output,study,pass_limit=None):
    """Original projected Sobolev-CG step, with explicit settling observations and work budget.

    Objective, gradient, projection, preconditioner and Armijo/cone updates are unchanged.
    Stopping additionally requires three separated tail/core observations. No physical time.
    """
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    cfgsha=canonical_sha(config);grid=Grid((config['nodes'],)*3,(config['length'],)*3,'fixed');q=config['q']
    codes=code_hashes()
    codesha=canonical_sha(codes);clock=time.monotonic();started=timestamp()
    atomic_json(out/'config.json',config)
    completed=0;iteration=0;history=[]
    if (out/'latest.npz').exists():
        old=json.loads((out/'manifest.json').read_text())
        if old['config_sha256']!=cfgsha or old['code_sha256']!=codesha:raise ValueError('Readmission source/config changed')
        with np.load(out/'latest.npz',allow_pickle=False) as f:
            n=f['field'].copy();iteration=int(f['iteration']);completed=int(f['pass_index'])
        history=json.loads((out/'history.json').read_text())
        history=[r for r in history if r['iteration']<=iteration]
    else:
        if config.get('source_checkpoint'):
            source=config['source_checkpoint']
            n,_,_=initialize({'initial':{'kind':'checkpoint','path':source['path'],'sha256':source['sha256'],'expected_q':q}},grid)
        else:
            n=rational_field(grid.points(),alpha=q,beta=1,scale=config['seed_scale'],cutoff=config['seed_cutoff'])
            n[grid.fixed_mask()]=NORTH
        metrics=stationarity(n,grid)
        history=[{'recorded_at':timestamp(),'iteration':0,'pass_index':0,**metrics}]
        atomic_json(out/'history.json',history)
        checkpoint(out/'initial.npz',n,grid,q,cfgsha,0,0,codesha)
        checkpoint(out/'latest.npz',n,grid,q,cfgsha,0,0,codesha)
    atomic_json(out/'manifest.json',{'started_at':started,'config_sha256':cfgsha,'code_sha256':codesha,
        'code_hashes':codes,'model':MODEL,'scheme':SCHEME,'config':config,
        'scope':'Dissipative readmission to the time lattice action; optimization iteration is not physical time.'})
    observe(out,n,grid,iteration,study,config)
    first=history[0];status='working';reason=None;passes_here=0
    while True:
        metrics=stationarity(n,grid)
        if (abs(abs(metrics['hopf_integral'])-q)/q>config['charge_relative_error']
                or metrics['minimum_corner_cone']<=0):status='topology_unresolved';break
        if settled(out,metrics,config,study,iteration):status='settled';break
        if iteration>=study['max_iterations_per_case']:status='settling_budget_exhausted';break
        if pass_limit is not None and passes_here>=pass_limit:status='checkpointed';break
        before=metrics['energy'];within=0;calls=0;old_g=None;old_z=None;direction=None;alpha=1.;message='iteration batch complete'
        interior=tuple(slice(2,-2) for _ in range(3))
        axes=[4*np.sin(np.pi*np.arange(1,count-3)/(2*(count-3)))**2/h**2 for count,h in zip(grid.shape,grid.spacing)]
        symbol=.25+sum(np.reshape(a,tuple(len(a) if i==j else 1 for i in range(3))) for j,a in enumerate(axes))
        def tangent(a):
            a=a-n*np.sum(n*a,axis=-1,keepdims=True);a[grid.fixed_mask()]=0;return a
        try:
            for _ in range(min(config['iterations_per_pass'],study['max_iterations_per_case']-iteration)):
                value,raw_gradient=static_value_gradient(n,grid);calls+=1
                g=tangent(raw_gradient/(2*K*np.prod(grid.spacing)))
                z=np.zeros_like(g);z[interior]=idstn(dstn(g[interior],axes=(0,1,2),type=1,norm='ortho')/symbol[...,None],axes=(0,1,2),type=1,norm='ortho');z=tangent(z)
                if old_g is None:direction=-z
                else:
                    transport_z=tangent(old_z)
                    coefficient=max(0.,min(1.,float(np.sum(g*(z-transport_z))/max(np.sum(old_g*old_z),1e-30))))
                    direction=-z+coefficient*tangent(direction)
                if np.sum(direction*g)>=0:direction=-z
                slope=float(2*K*np.prod(grid.spacing)*np.sum(g*direction))
                margin=cone(n);maximum=float(np.max(np.linalg.norm(direction,axis=-1)))
                trial_alpha=min(alpha*1.6,min(.15,.25*margin)/max(maximum,1e-30))
                accepted=False
                for line in range(45):
                    trial=n+trial_alpha*direction;trial/=np.linalg.norm(trial,axis=-1,keepdims=True);trial[grid.fixed_mask()]=NORTH
                    next_value,_=static_value_gradient(trial,grid);calls+=1
                    if np.isfinite(next_value) and next_value<=value+1e-4*trial_alpha*slope:
                        accepted=True;break
                    trial_alpha*=.5
                if not accepted or trial_alpha*maximum<1e-14:
                    message='Armijo search stalled';break
                old_g=g;old_z=z;n=trial;alpha=trial_alpha;iteration+=1;within+=1
                if iteration%config['checkpoint_every']==0:
                    row={'recorded_at':timestamp(),'iteration':iteration,'pass_index':completed,**stationarity(n,grid)}
                    history.append(row);atomic_json(out/'history.json',history)
                    checkpoint(out/'latest.npz',n,grid,q,cfgsha,iteration,completed,codesha)
                    print(json.dumps({'readmission':out.name,**row}),flush=True)
                    if abs(abs(row['hopf_integral'])-q)/q>config['charge_relative_error'] or row['minimum_corner_cone']<=0:
                        raise TopologyFailure('Readmission topology diagnostic failed')
                    observe(out,n,grid,iteration,study,config)
                    if settled(out,row,config,study,iteration):message='strict force and separated tail/core settling reached';break
        except (KeyboardInterrupt,TopologyFailure) as error:
            status='interrupted' if isinstance(error,KeyboardInterrupt) else 'topology_unresolved';reason=str(error);break
        completed+=1;passes_here+=1
        row={'recorded_at':timestamp(),'iteration':iteration,'pass_index':completed,'optimizer_message':message,
             'objective_calls':calls,**stationarity(n,grid)}
        history.append(row);atomic_json(out/'history.json',history)
        checkpoint(out/'latest.npz',n,grid,q,cfgsha,iteration,completed,codesha)
        observe(out,n,grid,iteration,study,config)
        # No hidden time cap: numerical stagnation is an unresolved result.
        ends=[r for r in history if 'optimizer_message' in r]
        if not settled(out,row,config,study,iteration) and ((within==0) or (len(ends)>=3 and
                all(abs(ends[i]['energy']-ends[i-1]['energy'])/ends[i-1]['energy']<config['stagnation_relative_energy']
                    for i in range(len(ends)-2,len(ends))))):
            status='stationarity_unresolved';reason=message;break
    metrics=stationarity(n,grid)
    checkpoint(out/'latest.npz',n,grid,q,cfgsha,iteration,completed,codesha)
    observe(out,n,grid,iteration,study,config,force=True)
    result={'started_at':started,'finished_at':timestamp(),'status':status,'reason':reason,'q_label':q,
            'initial':first,'final':metrics,'iterations':iteration,'passes':completed,
            'wall_seconds':time.monotonic()-clock,'field_sha256':sha(out/'latest.npz'),
            'scope':'Finite lattice stationarity and approximate Hopf quadrature only; no integer certificate or stability proof.'}
    atomic_json(out/'result.json',result);return result
