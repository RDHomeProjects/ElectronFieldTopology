"""Unchanged D4/RK4 driver bridge with observational tail reserve and snapshots. Apache-2.0.

Loop derived from sf_time_run.run at merge4e4ff506; numerical stepping is unchanged.
Only diagnostics, checkpoint identity/retention and boundary-reserve stopping differ.
"""
import json,platform,subprocess,time
from pathlib import Path
import numpy as np
from .sf_time_run import (ROOT,MODEL,SCHEME,canonical_sha,state_sha,validate,reference,initialize,save_checkpoint)
from .sf_time import step,diagnostics,densities
from .sf_time_controls import manufactured_force
from .sf_preview import PreviewWriter,export_settings
from .sf_checkpoints import atomic_json,timestamp
from .sf_dynamics_admission import sha
from .sf_temporal_metrics import tail_band
from .skyrme import NORTH
EVOLUTION_FILES=['sf_time.py','sf_time_controls.py','sf_time_initial.py','sf_dynamics.py','sf_time_run.py','skyrme.py','sf_temporal_run.py','sf_temporal_metrics.py']
def evolution_hashes():return {n:sha(Path(__file__).with_name(n)) for n in EVOLUTION_FILES}
class BoundaryReserveStop(ValueError):pass

def run(config,output,profile=None,resume=None,stop_after=None,monitor=None):
    """stop_after is a checkpoint/recovery test/pass guard, never profile-controlled."""
    monitor=monitor or {'enabled':True,'shell_width':2.,'warning_fraction':.0009,'tail_fraction_limit':.001,'snapshot_every_time':.25}
    grid=validate(config);profile=profile or {'export':{'enabled':False}}
    export_settings(profile)
    if config['initial']['kind']=='manufactured' and (grid.boundary!='periodic' or grid.lengths!=(2*np.pi,)*3):
        raise ValueError('Manufactured source is a declared periodic 2pi test only')
    out=Path(output)
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new or empty run output directory')
    out.mkdir(parents=True,exist_ok=True);started=timestamp();clock=time.monotonic()
    physics_sha=canonical_sha(config)
    code_hashes=evolution_hashes();code_sha=canonical_sha(code_hashes)
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
              'monitor_policy':monitor,'monitor_policy_sha256':canonical_sha(monitor),'preview_profile_sha256':canonical_sha(profile),'preview_profile':profile,'initial':initial,
              'preview_source_sha256':sha(Path(__file__).with_name('sf_preview.py')),
              'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),
              'scope':'Neutral physical-time reference; no charged model, full soliton stability or electron claim.'}
    atomic_json(out/'manifest.json',manifest);atomic_json(out/'physics.json',config)
    writer=PreviewWriter(out/'preview',profile,grid,config['case_id'],
                         {k:manifest[k] for k in ('started_at','model_id','scheme','physics_sha256','git_commit')})
    dt=config['dt'];history=[];source_work=0.;source_impulse=np.zeros(3);projection={'n_projection_max':0.,'v_projection_max':0.}
    snapshots=[]
    metrics=diagnostics(n,v,grid,forcing,start_step*dt);initial_metrics=metrics.copy();last_metrics=metrics
    def record(index,metrics):
        row={'recorded_at':timestamp(),'step':index,'time':index*dt,**metrics,
             'source_work_since_start':source_work,'source_impulse_since_start':source_impulse.tolist(),
             'energy_balance_defect':metrics['energy']-initial_metrics['energy']-source_work,**projection}
        known=reference(config,grid,index*dt)
        if known is not None:row['reference_rms_error']=float(np.sqrt(np.mean((n-known[0])**2)))
        if monitor['enabled']:
            row['boundary_tail']=tail_band(n,v,grid,monitor['shell_width'])
            row['original_tail_pass']=row['boundary_tail']['fraction'] is not None and row['boundary_tail']['fraction']<=monitor['tail_fraction_limit']
            row['tail_warning_clear']=row['boundary_tail']['fraction'] is not None and row['boundary_tail']['fraction']<=monitor['warning_fraction']
        history.append(row);atomic_json(out/'history.json',history)
        return row
    row=record(start_step,metrics);writer.write(start_step,start_step*dt,densities(n,v,grid),row,initial=True)
    save_checkpoint(out/'initial.npz',n,v,start_step,dt,physics_sha,code_sha)
    save_checkpoint(out/'latest.npz',n,v,start_step,dt,physics_sha,code_sha)
    final_step=start_step;status='complete'
    if monitor['enabled'] and row['boundary_tail']['fraction'] is not None and not row['tail_warning_clear']:raise ValueError('Initial tail lacks the declared safety reserve; admit the domain before evolution')
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
            snapshot_step=round(monitor['snapshot_every_time']/dt)
            if index%snapshot_step==0 or final:
                snap=out/'snapshots'/f'step-{index:06d}.npz';snap.parent.mkdir(exist_ok=True)
                save_checkpoint(snap,n,v,index,dt,physics_sha,code_sha)
                snapshots.append({'step':index,'time':index*dt,'path':str(snap.resolve()),'sha256':sha(snap),'state_sha256':state_sha(n,v)})
                atomic_json(out/'snapshots.json',snapshots)
            if monitor['enabled'] and 'boundary_tail' in row and row['boundary_tail']['fraction'] is not None and not row['tail_warning_clear']:
                save_checkpoint(out/'latest.npz',n,v,index,dt,physics_sha,code_sha)
                raise BoundaryReserveStop('Observed tail exhausted the predeclared0.09% safety band; original0.1% flag retained')
            if index%20==0 or final:
                print(json.dumps({'recorded_at':timestamp(),'step':index,'steps':config['steps'],
                                  'energy':metrics['energy'],'unit_error':metrics['unit_error']}),flush=True)
        if final_step<config['steps']:status='checkpointed'
    except (ValueError,KeyboardInterrupt,FloatingPointError) as error:
        status='boundary_reserve_stop' if isinstance(error,BoundaryReserveStop) else ('interrupted' if isinstance(error,KeyboardInterrupt) else 'numerical_failure')
        atomic_json(out/'failure.json',{'recorded_at':timestamp(),'status':status,'error':str(error)})
        # latest.npz is the last independently complete checkpoint, never a partial RK stage.
    writer.finish(status)
    if status in ('complete','checkpointed','boundary_reserve_stop'):
        save_checkpoint(out/'final.npz',n,v,final_step,dt,physics_sha,code_sha)
    scale=max(abs(initial_metrics['energy']),1e-30)
    result={'started_at':started,'finished_at':timestamp(),'status':status,'step':final_step,'time':final_step*dt,
            'physics_sha256':physics_sha,'state_sha256':state_sha(n,v),'initial':initial_metrics,'final':metrics,
            'max_energy_balance_relative_defect':max(abs(r['energy_balance_defect'])/scale for r in history),
            'max_unit_error':max(r['unit_error'] for r in history),'max_tangency_error':max(r['tangency_error'] for r in history),
            'retained_snapshots':snapshots,'max_observed_tail_fraction':max((r['boundary_tail']['fraction'] for r in history if r.get('boundary_tail',{}).get('fraction') is not None),default=None),'tail_monitor_scope':'Same physical observation times across dt; no between-sample maximum guarantee','monitor_policy':monitor,'wall_seconds':time.monotonic()-clock,'preview_frames':len(writer.frames),
            'scope':manifest['scope']}
    atomic_json(out/'result.json',result);return result
