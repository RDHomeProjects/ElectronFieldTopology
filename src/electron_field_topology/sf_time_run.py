"""Physical-time run driver. Optional preview export has no numerical controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import numpy as np
from .sf_checkpoints import atomic_json,timestamp
from .sf_dynamics_admission import sha
from .sf_time import Grid,step,diagnostics,densities,retract
from .sf_time_controls import wave,pulse,manufactured,manufactured_force
from .sf_time_initial import boosted_static
from .sf_preview import PreviewWriter,export_settings
from .skyrme import NORTH,coordinates,rational_field,set_boundary

MODEL='SF-relativistic-neutral-v1'
SCHEME='D4-action-projected-RK4-v1'
ROOT=Path(__file__).resolve().parents[2]


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def state_sha(n,v):
    h=hashlib.sha256()
    for a in (n,v):h.update(memoryview(np.ascontiguousarray(a,dtype='<f8')))
    return h.hexdigest()


def validate(config):
    allowed={'case_id','grid','lengths','boundary','dt','steps','diagnostic_every','checkpoint_every','initial'}
    if set(config)-allowed:raise ValueError('Unknown physical configuration keys')
    g=Grid(tuple(config['grid']),tuple(config['lengths']),config['boundary'])
    if (not isinstance(config['case_id'],str) or type(config['steps']) is not int or config['steps']<1
            or not np.isfinite(config['dt']) or config['dt']<=0
            or any(type(config[k]) is not int or config[k]<1 for k in ('diagnostic_every','checkpoint_every'))):
        raise ValueError('Explicit positive time/step/recording parameters required')
    active=[h for h,n in zip(g.spacing,g.shape) if n>1]
    if active and config['dt']/min(active)>.2:raise ValueError('Reference dt/h must not exceed predeclared .2')
    return g


def reference(config,grid,t):
    initial=config['initial'];kind=initial['kind'];points=grid.points()
    if kind=='wave':return wave(points,t,grid.lengths,initial['modes'],initial.get('offset',0.))
    if kind=='pulse':return pulse(points,t,**{k:v for k,v in initial.items() if k!='kind'})
    if kind=='manufactured':return manufactured(points,t)
    if kind=='geodesic':
        theta=initial.get('omega',1.)*t;omega=initial.get('omega',1.)
        n=np.broadcast_to([np.sin(theta),0.,np.cos(theta)],grid.shape+(3,)).copy()
        v=np.broadcast_to([omega*np.cos(theta),0.,-omega*np.sin(theta)],n.shape).copy();return n,v
    return None


def initialize(config,grid):
    initial=config['initial'];kind=initial['kind'];known=reference(config,grid,0.)
    provenance={'kind':kind}
    if known is not None:n,v=known
    elif kind=='vacuum':n=np.broadcast_to(NORTH,grid.shape+(3,)).copy();v=np.zeros_like(n)
    elif kind=='rational':
        if (len(set(grid.shape))!=1 or len(set(grid.spacing))!=1 or grid.boundary!='fixed'
                or initial['q'] not in (1,2)):
            raise ValueError('Fresh low-Q controls require a cubic fixed box and Q1/Q2')
        n=set_boundary(rational_field(grid.points(),alpha=initial['q'],beta=1,
                    scale=initial.get('scale',1.),cutoff=initial['cutoff']));v=np.zeros_like(n)
        provenance['scope']='Fresh unrelaxed low-Q seed; not a stationary soliton.'
    elif kind in ('checkpoint','boosted_checkpoint','lattice_checkpoint','boosted_lattice_checkpoint'):
        path=Path(initial['path']).expanduser();digest=sha(path)
        if digest!=initial['sha256']:raise ValueError('Static input checkpoint SHA-256 mismatch')
        with np.load(path,allow_pickle=False) as data:
            n=data['field'].copy()
            oldh=float(data['h'])
            if (n.dtype!=np.dtype('float64') or grid.boundary!='fixed'
                    or str(data['model_id'])!=(MODEL if 'lattice' in kind else 'SF-J2015-static')
                    or int(data['expected_q'])!=initial['expected_q']):
                raise ValueError('Static checkpoint model/grid/Q mismatch; no implicit resampling')
            if 'lattice' in kind:
                if str(data['scheme'])!=SCHEME or np.max(abs(data['field_rate']))!=0:
                    raise ValueError('Lattice rest import needs the exact scheme and zero velocity')
        if kind in ('checkpoint','lattice_checkpoint'):
            if n.shape!=grid.shape+(3,) or len(set(grid.spacing))!=1 or oldh!=grid.spacing[0]:
                raise ValueError('Rest checkpoint geometry mismatch; no implicit resampling')
            v=np.zeros_like(n)
        else:
            beta=initial['beta'];axis=initial['axis'];n,v=boosted_static(n,oldh,grid,beta,axis)
            provenance.update(beta=beta,axis=axis,
                resolution_scope='A finer lab grid and boundary/readmission checks are required before motion acceptance.',
                max_lab_parallel_spacing_for_same_rest_resolution=float(oldh*np.sqrt(1-beta*beta)))
        provenance.update(path=str(path.resolve()),sha256=digest,
                 scope='Rest snapshot imported into a different, explicitly tested time discretization; re-admission required.')
    else:raise ValueError('Unknown initial condition')
    if not np.isfinite(n).all() or np.max(abs(np.linalg.norm(n,axis=-1)-1))>1e-10:
        raise ValueError('Initial field is not a finite unit-vector field')
    if np.max(abs(np.sum(n*v,axis=-1)))>1e-10:raise ValueError('Initial velocity is not tangent')
    if grid.boundary=='fixed':
        mask=grid.fixed_mask()
        if np.max(abs(n[mask]-NORTH),initial=0)>1e-12 or np.max(abs(v[mask]),initial=0)>1e-12:
            raise ValueError('Initial data do not satisfy fixed faces')
    return n,v,provenance


def save_checkpoint(path,n,v,step_index,dt,physics_sha,code_sha):
    path=Path(path);temp=path.with_suffix('.tmp');written=timestamp()
    with temp.open('wb') as stream:
        np.savez_compressed(stream,field=n,field_rate=v,step=step_index,time=step_index*dt,
                model_id=MODEL,scheme=SCHEME,physics_sha256=physics_sha,code_sha256=code_sha,
                written_utc=written['utc'],written_melbourne=written['melbourne'])
        stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)


def run(config,output,profile=None,resume=None,stop_after=None):
    """stop_after is a checkpoint/recovery test/pass guard, never profile-controlled."""
    grid=validate(config);profile=profile or {'export':{'enabled':False}}
    export_settings(profile)
    if config['initial']['kind']=='manufactured' and (grid.boundary!='periodic' or grid.lengths!=(2*np.pi,)*3):
        raise ValueError('Manufactured source is a declared periodic 2pi test only')
    out=Path(output)
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new or empty run output directory')
    out.mkdir(parents=True,exist_ok=True);started=timestamp();clock=time.monotonic()
    physics_sha=canonical_sha(config)
    code_files=['sf_time.py','sf_time_controls.py','sf_time_initial.py','sf_dynamics.py','sf_time_run.py','skyrme.py']
    code_hashes={n:sha(Path(__file__).with_name(n)) for n in code_files};code_sha=canonical_sha(code_hashes)
    start_step=0
    if not resume:n,v,initial=initialize(config,grid)
    else:initial={'kind':config['initial']['kind'],'scope':'Exact physical-time checkpoint continuation; original static input not reread.'}
    if resume:
        with np.load(resume,allow_pickle=False) as checkpoint:
            if (str(checkpoint['model_id'])!=MODEL or str(checkpoint['scheme'])!=SCHEME
                    or str(checkpoint['physics_sha256'])!=physics_sha or str(checkpoint['code_sha256'])!=code_sha):
                raise ValueError('Resume model, numerical source or physical config mismatch')
            n=checkpoint['field'].copy();v=checkpoint['field_rate'].copy();start_step=int(checkpoint['step'])
            if n.dtype!=np.dtype('float64') or v.dtype!=np.dtype('float64') or n.shape!=grid.shape+(3,) or v.shape!=n.shape:
                raise ValueError('Resume field precision/geometry mismatch')
            if float(checkpoint['time'])!=start_step*config['dt'] or not 0<=start_step<=config['steps']:
                raise ValueError('Resume time/step mismatch')
        if (not np.isfinite(n).all() or not np.isfinite(v).all()
                or np.max(abs(np.linalg.norm(n,axis=-1)-1))>1e-10
                or np.max(abs(np.sum(n*v,axis=-1)))>1e-10):raise ValueError('Invalid resume constraints')
        if grid.boundary=='fixed' and (np.max(abs(n[grid.fixed_mask()]-NORTH),initial=0)>1e-12
                                      or np.max(abs(v[grid.fixed_mask()]),initial=0)>1e-12):
            raise ValueError('Resume fixed faces differ')
        initial.update(resume=str(Path(resume).resolve()),resume_sha256=sha(resume),start_step=start_step)
    forcing=manufactured_force if config['initial']['kind']=='manufactured' else None
    try:
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    except (OSError,subprocess.CalledProcessError):commit=None;dirty=None
    manifest={'started_at':started,'model_id':MODEL,'scheme':SCHEME,'physics':config,'physics_sha256':physics_sha,
              'physics_source_sha256':code_hashes,'code_sha256':code_sha,'git_commit':commit,'git_worktree_dirty':dirty,
              'preview_profile_sha256':canonical_sha(profile),'preview_profile':profile,'initial':initial,
              'preview_source_sha256':sha(Path(__file__).with_name('sf_preview.py')),
              'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),
              'scope':'Neutral physical-time reference; no charged model, full soliton stability or electron claim.'}
    atomic_json(out/'manifest.json',manifest);atomic_json(out/'physics.json',config)
    writer=PreviewWriter(out/'preview',profile,grid,config['case_id'],
                         {k:manifest[k] for k in ('started_at','model_id','scheme','physics_sha256','git_commit')})
    dt=config['dt'];history=[];source_work=0.;source_impulse=np.zeros(3);projection={'n_projection_max':0.,'v_projection_max':0.}
    metrics=diagnostics(n,v,grid,forcing,start_step*dt);initial_metrics=metrics.copy();last_metrics=metrics
    def record(index,metrics):
        row={'recorded_at':timestamp(),'step':index,'time':index*dt,**metrics,
             'source_work_since_start':source_work,'source_impulse_since_start':source_impulse.tolist(),
             'energy_balance_defect':metrics['energy']-initial_metrics['energy']-source_work,**projection}
        known=reference(config,grid,index*dt)
        if known is not None:row['reference_rms_error']=float(np.sqrt(np.mean((n-known[0])**2)))
        history.append(row);atomic_json(out/'history.json',history)
        return row
    row=record(start_step,metrics);writer.write(start_step,start_step*dt,densities(n,v,grid),row,initial=True)
    save_checkpoint(out/'initial.npz',n,v,start_step,dt,physics_sha,code_sha)
    save_checkpoint(out/'latest.npz',n,v,start_step,dt,physics_sha,code_sha)
    final_step=start_step;status='complete'
    try:
        end_step=min(config['steps'],stop_after) if stop_after is not None else config['steps']
        for index in range(start_step+1,end_step+1):
            n,v,projection=step(n,v,grid,dt,(index-1)*dt,forcing);final_step=index
            metrics=diagnostics(n,v,grid,forcing,index*dt)
            source_work+=.5*dt*(last_metrics['source_power']+metrics['source_power'])
            source_impulse+=.5*dt*(np.array(last_metrics['source_force'])+metrics['source_force']);last_metrics=metrics
            final=index==end_step
            if index%config['diagnostic_every']==0 or final:row=record(index,metrics)
            else:row={'recorded_at':timestamp(),'step':index,'time':index*dt,**metrics}
            if writer.due(index,final):writer.write(index,index*dt,densities(n,v,grid),row,final=final)
            if index%config['checkpoint_every']==0 or final:
                save_checkpoint(out/'latest.npz',n,v,index,dt,physics_sha,code_sha)
            if index%20==0 or final:
                print(json.dumps({'recorded_at':timestamp(),'step':index,'steps':config['steps'],
                                  'energy':metrics['energy'],'unit_error':metrics['unit_error']}),flush=True)
        if final_step<config['steps']:status='checkpointed'
    except (ValueError,KeyboardInterrupt,FloatingPointError) as error:
        status='interrupted' if isinstance(error,KeyboardInterrupt) else 'numerical_failure'
        atomic_json(out/'failure.json',{'recorded_at':timestamp(),'status':status,'error':str(error)})
        # latest.npz is the last independently complete checkpoint, never a partial RK stage.
    writer.finish(status)
    if status in ('complete','checkpointed'):
        save_checkpoint(out/'final.npz',n,v,final_step,dt,physics_sha,code_sha)
    scale=max(abs(initial_metrics['energy']),1e-30)
    result={'started_at':started,'finished_at':timestamp(),'status':status,'step':final_step,'time':final_step*dt,
            'physics_sha256':physics_sha,'state_sha256':state_sha(n,v),'initial':initial_metrics,'final':metrics,
            'max_energy_balance_relative_defect':max(abs(r['energy_balance_defect'])/scale for r in history),
            'max_unit_error':max(r['unit_error'] for r in history),'max_tangency_error':max(r['tangency_error'] for r in history),
            'wall_seconds':time.monotonic()-clock,'preview_frames':len(writer.frames),
            'scope':manifest['scope']}
    atomic_json(out/'result.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True)
    p.add_argument('--profile',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--resume',type=Path)
    a=p.parse_args();config=json.loads(a.config.read_text());profile=json.loads(a.profile.read_text()) if a.profile else None
    result=run(config,a.output,profile,a.resume);print(json.dumps(result,indent=2))
    return 0 if result['status']=='complete' else 2


if __name__=='__main__':raise SystemExit(main())
