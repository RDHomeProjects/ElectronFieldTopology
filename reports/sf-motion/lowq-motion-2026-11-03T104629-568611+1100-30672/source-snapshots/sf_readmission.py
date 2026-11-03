"""Stationary readmission to the physical-time lattice action, never physical time."""
import json
import os
from pathlib import Path
import time
import numpy as np
from scipy.fft import dstn,idstn
from .sf_time import Grid,gradients,sigma_terms,derivative,acceleration,densities
from .sf_dynamics import currents
from .sf_checkpoints import timestamp,atomic_json
from .sf_dynamics_admission import sha
from .sf_time_run import MODEL,SCHEME,canonical_sha,initialize
from .skyrme import K,NORTH,rational_field,diagnostics as topology


def static_value_gradient(n,grid):
    """Exact Euclidean derivative of the same nodal static Hamiltonian."""
    d=gradients(n-NORTH,grid);sigma,force=sigma_terms(n,grid)
    _,q=currents(d,np.zeros_like(n))
    for i,h in enumerate(grid.spacing):force+=derivative(-.5*q[...,i,:]-d[...,i,:],h,i,grid.boundary)
    e4=sum(np.sum(np.cross(d[...,i,:],d[...,j,:])**2,axis=-1) for i,j in [(0,1),(0,2),(1,2)])
    return float(K*np.sum(sigma+e4)*np.prod(grid.spacing)),-2*K*np.prod(grid.spacing)*force


def cone(n):
    """Minimum dot of each cell corner with its normalized corner sum."""
    shape=tuple(s-1 for s in n.shape[:3]);total=np.zeros(shape+(3,));pieces=[]
    for a in np.ndindex(2,2,2):
        p=n[tuple(slice(bit,bit+size) for bit,size in zip(a,shape))];pieces.append(p);total+=p
    size=np.linalg.norm(total,axis=-1,keepdims=True)
    if np.min(size)<1e-12:return -1.
    centre=total/size
    return min(float(np.min(np.sum(p*centre,axis=-1))) for p in pieces)


def stationarity(n,grid):
    energy,g=static_value_gradient(n,grid);g-=n*np.sum(n*g,axis=-1,keepdims=True);g[grid.fixed_mask()]=0
    f=-g/(2*K*np.prod(grid.spacing));sigma=sigma_terms(n,grid)[1]
    a=acceleration(n,np.zeros_like(n),grid)[1]
    return {'energy':energy,'relative_force_l2':float(np.linalg.norm(f)/max(np.linalg.norm(sigma),1e-30)),
            'acceleration_max':float(np.max(np.linalg.norm(a,axis=-1))),
            'acceleration_rms':float(np.sqrt(np.mean(a*a))),
            'minimum_corner_cone':cone(n),**topology(n,grid.spacing[0])}


def checkpoint(path,n,grid,q,config_sha,iteration,pass_index,code_sha):
    path=Path(path);tmp=path.with_suffix('.tmp');stamp=timestamp()
    with tmp.open('wb') as f:
        np.savez_compressed(f,field=n,field_rate=np.zeros_like(n),h=grid.spacing[0],expected_q=q,
            model_id=MODEL,scheme=SCHEME,config_sha256=config_sha,code_sha256=code_sha,
            iteration=iteration,pass_index=pass_index,written_utc=stamp['utc'],written_melbourne=stamp['melbourne'])
        f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def admitted(metrics,q,cfg):
    return (metrics['relative_force_l2']<=cfg['relative_force_l2']
            and metrics['acceleration_max']<=cfg['acceleration_max']
            and abs(abs(metrics['hopf_integral'])-q)/q<=cfg['charge_relative_error']
            and metrics['minimum_corner_cone']>0 and metrics['unit_error']<1e-10)


def relax(config,output,pass_limit=None):
    """Restartable projected Sobolev conjugate-gradient batches; pass_limit exists only for preparation tests.

    No wall-time/overall pass cap. Stop on measured admission, topology failure,
    line-search failure, or three stagnant complete passes; preserve unresolved cases.
    Restart discards conjugate-gradient memory, never changes the energy or thresholds.
    """
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    cfgsha=canonical_sha(config);grid=Grid((config['nodes'],)*3,(config['length'],)*3,'fixed');q=config['q']
    codes={name:sha(Path(__file__).with_name(name)) for name in ['sf_readmission.py','sf_time.py','sf_dynamics.py','skyrme.py']}
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
    first=history[0];status='working';reason=None;passes_here=0
    while True:
        metrics=stationarity(n,grid)
        if (abs(abs(metrics['hopf_integral'])-q)/q>config['charge_relative_error']
                or metrics['minimum_corner_cone']<=0):status='topology_unresolved';break
        if admitted(metrics,q,config):status='stationary';break
        if pass_limit is not None and passes_here>=pass_limit:status='checkpointed';break
        before=metrics['energy'];within=0;calls=0;old_g=None;old_z=None;direction=None;alpha=1.;message='iteration batch complete'
        interior=tuple(slice(2,-2) for _ in range(3))
        axes=[4*np.sin(np.pi*np.arange(1,count-3)/(2*(count-3)))**2/h**2 for count,h in zip(grid.shape,grid.spacing)]
        symbol=.25+sum(np.reshape(a,tuple(len(a) if i==j else 1 for i in range(3))) for j,a in enumerate(axes))
        def tangent(a):
            a=a-n*np.sum(n*a,axis=-1,keepdims=True);a[grid.fixed_mask()]=0;return a
        try:
            for _ in range(config['iterations_per_pass']):
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
                if within%config['checkpoint_every']==0:
                    row={'recorded_at':timestamp(),'iteration':iteration,'pass_index':completed,**stationarity(n,grid)}
                    history.append(row);atomic_json(out/'history.json',history)
                    checkpoint(out/'latest.npz',n,grid,q,cfgsha,iteration,completed,codesha)
                    print(json.dumps({'readmission':out.name,**row}),flush=True)
                    if abs(abs(row['hopf_integral'])-q)/q>config['charge_relative_error'] or row['minimum_corner_cone']<=0:
                        raise ValueError('Readmission topology diagnostic failed')
                    if admitted(row,q,config):message='measured stationary gates reached';break
        except (KeyboardInterrupt,ValueError) as error:
            status='interrupted' if isinstance(error,KeyboardInterrupt) else 'topology_unresolved';reason=str(error);break
        completed+=1;passes_here+=1
        row={'recorded_at':timestamp(),'iteration':iteration,'pass_index':completed,'optimizer_message':message,
             'objective_calls':calls,**stationarity(n,grid)}
        history.append(row);atomic_json(out/'history.json',history)
        checkpoint(out/'latest.npz',n,grid,q,cfgsha,iteration,completed,codesha)
        # No hidden time cap: numerical stagnation is an unresolved result.
        ends=[r for r in history if 'optimizer_message' in r]
        if not admitted(row,q,config) and ((within==0) or (len(ends)>=3 and
                all(abs(ends[i]['energy']-ends[i-1]['energy'])/ends[i-1]['energy']<config['stagnation_relative_energy']
                    for i in range(len(ends)-2,len(ends))))):
            status='stationarity_unresolved';reason=message;break
    metrics=stationarity(n,grid)
    checkpoint(out/'latest.npz',n,grid,q,cfgsha,iteration,completed,codesha)
    result={'started_at':started,'finished_at':timestamp(),'status':status,'reason':reason,'q_label':q,
            'initial':first,'final':metrics,'iterations':iteration,'passes':completed,
            'wall_seconds':time.monotonic()-clock,'field_sha256':sha(out/'latest.npz'),
            'scope':'Finite lattice stationarity and approximate Hopf quadrature only; no integer certificate or stability proof.'}
    atomic_json(out/'result.json',result);return result
