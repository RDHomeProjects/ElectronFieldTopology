"""S5-B-005 read-only initialization/registration study. Apache-2.0.

No trajectory generation, action change, renderer input or automatic gate release.
"""
import argparse
import csv
import fcntl
import json
from pathlib import Path
import platform
import signal
import subprocess
import time
import zipfile
import numpy as np
import scipy

from .sf_checkpoints import timestamp
from .sf_motion_diagnostics import (ROOT, atomic_json, event, compact, inventory,
    load_rest, load_state, attempt_path, sha)
from .sf_reconstruction import sample_cubic, boosted_cubic, phase_comparison
from .sf_time_initial import sample_static, boosted_static
from .sf_time import Grid, derivative
from .sf_time_run import canonical_sha, state_sha
from .skyrme import NORTH

CONFIG=ROOT/'experiments/configs/s5-b/005-boost-initialization/study.json'
SCOPE=('Retained-field reconstruction and restricted registration only. New cubic '
       'initial data have not been evolved. No isolated-motion, charge, spin or electron acceptance.')
SOURCES=['sf_boost_study.py','sf_reconstruction.py','sf_boost_local.py',
         'sf_motion_diagnostics.py','sf_time.py','sf_time_initial.py','sf_time_run.py',
         'sf_motion_metrics.py','sf_checkpoints.py','sf_dynamics_admission.py','skyrme.py']


def diagnostic_config(config):
    if (config['format']!='EFT-boost-study-v1' or type(config['sampling_nodes']) is not int
            or config['sampling_nodes']<5 or type(config['chunk_points']) is not int
            or config['chunk_points']<1 or not np.isfinite(config['case_dt']) or config['case_dt']<=0
            or config['control_nodes']!=[17,33,65]
            or any(not np.isfinite(v) or v<=0 for v in config['control_limits'].values())):
        raise ValueError('Explicit valid boost-study configuration required')
    return {'format':'EFT-motion-diagnostics-v1','evidence_sha256':config['evidence_sha256'],
            'case_ids':[], 'comparison_grids':[config['sampling_nodes']],
            'shell_width':config['shell_width'],'replay_rtol':1e-9,'replay_atol':1e-11}


def analytical(points, axis):
    """Independent theta/phi formula and exact coordinate derivative; not a solver."""
    x,y,z=np.moveaxis(points,-1,0)
    theta=.19*np.sin(.7*x)+.13*np.cos(.6*y)+.11*np.sin(.5*z)
    phi=.17*np.sin(.4*y)+.09*np.cos(.3*z)
    dt=[.133*np.cos(.7*x),-.078*np.sin(.6*y),.055*np.cos(.5*z)][axis]
    dp=[np.zeros_like(x),.068*np.cos(.4*y),-.027*np.sin(.3*z)][axis]
    n=np.stack((np.sin(theta)*np.cos(phi),np.sin(theta)*np.sin(phi),np.cos(theta)),axis=-1)
    nt=np.stack((np.cos(theta)*np.cos(phi),np.cos(theta)*np.sin(phi),-np.sin(theta)),axis=-1)
    np_=np.stack((-np.sin(theta)*np.sin(phi),np.sin(theta)*np.cos(phi),np.zeros_like(x)),axis=-1)
    return n,dt[...,None]*nt+dp[...,None]*np_


def controls(config):
    """Three actual sample meshes, independent values/jets and event differences."""
    rows=[];rng=np.random.default_rng(5005)
    fractions=rng.uniform(-.2,.2,(240,3))
    for size in config['control_nodes']:
        g=Grid((size,)*3,(8.,)*3,'fixed');n=analytical(g.points(),0)[0];h=g.spacing[0]
        for kind in ['nodes','shifted']:
            cells=np.round(fractions*(size-1)).astype(int)
            points=(cells+(0 if kind=='nodes' else np.array([.23,.37,.41])))*h
            for axis in range(3):
                truth,jet=analytical(points,axis)
                old,do=sample_static(n,h,points,axis);new,dn=sample_cubic(n,g,points,axis)
                rows.append({'nodes':size,'sampling':kind,'axis':axis,
                  'old_value_max':float(np.max(np.linalg.norm(old-truth,axis=-1))),
                  'new_value_max':float(np.max(np.linalg.norm(new-truth,axis=-1))),
                  'old_derivative_rms':float(np.sqrt(np.mean((do-jet)**2))),
                  'new_derivative_rms':float(np.sqrt(np.mean((dn-jet)**2))),
                  'unit_max':float(np.max(abs(np.sum(new*new,axis=-1)-1))),
                  'tangency_max':float(np.max(abs(np.sum(new*dn,axis=-1))))})
    orders=[]
    for axis in range(3):
        for metric,kind in [('new_value_max','shifted'),('new_derivative_rms','shifted'),('new_derivative_rms','nodes')]:
            series=[next(r[metric] for r in rows if r['nodes']==n and r['sampling']==kind and r['axis']==axis) for n in config['control_nodes']]
            orders.append({'axis':axis,'metric':metric,'sampling':kind,'errors':series,
                           'orders':[float(np.log2(a/b)) for a,b in zip(series,series[1:])]})
    # Constant-north extensions with compact C5 theta, independent of the sampler.
    g=Grid((33,)*3,(8.,)*3,'fixed');p=g.points();r=np.maximum(1-np.sum(p*p,axis=-1)/4,0)
    theta=.2*r**6;field=np.stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1)
    boundary=[];continuity=[];events=[]
    for axis in range(3):
        q=np.zeros((6,3));q[:,axis]=[-4.1,-4.,-4.+1e-7,4.-1e-7,4.,4.1]
        n,d=sample_cubic(field,g,q,axis)
        boundary.append(float(max(np.max(abs(n-NORTH)),np.max(abs(d)))))
        q=rng.uniform(-1.,1.,(40,3));q[:,axis]=0
        a=q.copy();b=q.copy();a[:,axis]-=1e-8;b[:,axis]+=1e-8
        na,da=sample_cubic(field,g,a,axis);nb,db=sample_cubic(field,g,b,axis)
        continuity.append(float(np.max(abs(da-db))))
        beta=.3;gamma=1/np.sqrt(1-beta*beta);q=rng.uniform(-1.,1.,(50,3))
        rp=q.copy();rp[:,axis]*=gamma;nn,d=sample_cubic(field,g,rp,axis)
        eps=1e-6;pp=rp.copy();pm=rp.copy();pp[:,axis]-=gamma*beta*eps;pm[:,axis]+=gamma*beta*eps
        vp=(sample_cubic(field,g,pp,axis)[0]-sample_cubic(field,g,pm,axis)[0])/(2*eps)
        events.append(float(np.max(abs(vp+gamma*beta*d))))
    checks={'node_values':max(r['new_value_max'] for r in rows if r['sampling']=='nodes')<2e-14,
            'offnode_value_order':all(min(r['orders'])>config['control_limits']['value_order'] for r in orders if r['metric']=='new_value_max'),
            'derivative_order':all(min(r['orders'])>config['control_limits']['derivative_order'] for r in orders if r['metric']=='new_derivative_rms'),
            'constraints':max(max(r['unit_max'],r['tangency_max']) for r in rows)<2e-13,
            'north_extension':max(boundary)<1e-13,'cell_derivative_continuity':max(continuity)<1e-7,
            'event_derivative':max(events)<1e-8}
    return {'recorded_at':timestamp(),'rows':rows,'orders':orders,'boundary_max':boundary,
            'derivative_jump_at_epsilon':continuity,'event_derivative_max':events,
            'checks':checks,'passed':all(checks.values()),
            'scope':'Reconstruction controls; three input meshes are not soliton evolution convergence.'}


def rate_metrics(n,v,grid,beta,axis,margin):
    dn=derivative(n-NORTH,grid.spacing[axis],axis,'fixed')
    target=-beta*(dn-n*np.sum(n*dn,axis=-1,keepdims=True));target[grid.fixed_mask()]=0
    points=grid.points();core=np.all(abs(points)<=np.array(grid.lengths)/2-margin,axis=-1)
    result={}
    for name,mask in [('full',np.ones(grid.shape,dtype=bool)),('core',core)]:
        if not np.any(mask):raise ValueError('Declared core contains no grid points')
        delta=v[mask]-target[mask];scale=max(float(np.linalg.norm(v[mask])),float(np.linalg.norm(target[mask])),1e-30)
        result[name]={'rate_relative_l2':float(np.linalg.norm(delta)/scale) if beta else None,
                      'rate_absolute_rms':float(np.sqrt(np.mean(delta*delta))),
                      'points':int(mask.sum())}
    result['unit_error']=float(np.max(abs(np.sum(n*n,axis=-1)-1)))
    result['tangency_error']=float(np.max(abs(np.sum(n*v,axis=-1))))
    result['fixed_face_field_deviation']=float(np.max(abs(n[grid.fixed_mask()]-NORTH)))
    result['fixed_face_rate_max']=float(np.max(abs(v[grid.fixed_mask()])))
    result['scope']='D4 transport consistency only; analytic interpolant velocity is never replaced by a fitted D4 velocity.'
    return result


def case_record(source,case,campaign,manifests,config):
    rest,rg=load_rest(source,case['seed_id'],campaign)
    ni,vi,grid=load_state(source,case,manifests,'initial')
    beta=case['beta'];axis=case['axis'];gamma=1/np.sqrt(1-beta*beta)
    old_n,old_v=boosted_static(rest,rg.spacing[0],grid,beta,axis) if beta else (rest.copy(),np.zeros_like(rest))
    if state_sha(ni,vi)!=state_sha(old_n,old_v):raise ValueError('Retained initial state is not the original bit-exact reconstruction')
    new_n,new_v=boosted_cubic(rest,rg,grid,beta,axis,config['chunk_points'])
    initial={'old_replay_bit_exact':True,'new_vs_old':phase_comparison(new_n,ni),
             'rate_change_rms':float(np.sqrt(np.mean((new_v-vi)**2))),
             'old_transport':rate_metrics(ni,vi,grid,beta,axis,config['shell_width']),
             'new_transport':rate_metrics(new_n,new_v,grid,beta,axis,config['shell_width']),
             'candidate_state_sha256':state_sha(new_n,new_v)}
    del old_n,old_v,new_n,new_v,rest
    nf,vf,_=load_state(source,case,manifests,'final');del vf
    duration=case['physical']['dt']*case['physical']['steps']
    # One fixed central rest-coordinate cube shared by t=0 and t=T. No centroid fit.
    halves=np.minimum(np.array(rg.lengths)/2-config['shell_width'],np.array(grid.lengths)/2-config['shell_width'])
    halves[axis]=min(halves[axis],gamma*(grid.lengths[axis]/2-abs(beta*duration)-config['shell_width']))
    half=float(np.min(halves))
    if half<=0:raise ValueError('No common comoving region at this observation time')
    a=np.linspace(-half,half,config['sampling_nodes']);xi=np.stack(np.meshgrid(a,a,a,indexing='ij'),axis=-1)
    x0=xi.copy();x0[...,axis]/=gamma;xt=x0.copy();xt[...,axis]+=beta*duration
    init_sample=sample_cubic(ni,grid,x0,axis,config['chunk_points'])[0]
    final_sample=sample_cubic(nf,grid,xt,axis,config['chunk_points'])[0]
    rest,rg=load_rest(source,case['seed_id'],campaign)
    references={'historical_trilinear':sample_static(rest,rg.spacing[0],xi,axis)[0],
                'candidate_cubic':sample_cubic(rest,rg,xi,axis,config['chunk_points'])[0]}
    comparisons={k:{'initial_reference':phase_comparison(init_sample,r),
                    'final_reference':phase_comparison(final_sample,r)} for k,r in references.items()}
    return {'recorded_at':timestamp(),'case_id':case['id'],'seed_id':case['seed_id'],'q':case['q'],
            'beta':beta,'axis':axis,'dt':case['physical']['dt'],'time':duration,'initial':initial,
            'comoving':{'cube_side':2*half,'sampling_nodes':config['sampling_nodes'],
                        'map':'x_a=xi_a/gamma+beta*t; transverse coordinates unchanged',
                        'reference_comparisons':comparisons,
                        'evolved_vs_own_initial':phase_comparison(final_sample,init_sample),
                        'reference_change':phase_comparison(references['candidate_cubic'],references['historical_trilinear'])},
            'original_case_checks':case['assessment']['checks'],
            'scope':SCOPE+' Comoving comparisons use the same cubic sampling operator on both retained snapshots; sampling error remains.'}


def write_outputs(out,ledger):
    stamp=timestamp();rows=list(ledger['cases'].values())
    lines=['# S5-B-005: boost initialization and field registration','',
           f"UTC: {stamp['utc']}; Melbourne: {stamp['melbourne']}.",'',
           f"Status: **{ledger['status']}**. Cases: {len(rows)}/{ledger['expected_cases']}.",
           f"Independent reconstruction controls passed: {ledger.get('controls',{}).get('passed')}.",'',
           '|Case|Old rate mismatch|Cubic rate mismatch|Raw comoving change|Phase-registered change|',
           '|---|---:|---:|---:|---:|']
    columns=['recorded_utc','recorded_melbourne','case_id','beta','axis','old_rate_relative','new_rate_relative','comoving_raw','comoving_phase_registered']
    with (out/'case-metrics.csv').open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n');w.writeheader()
        for r in rows:
            old=r['initial']['old_transport']['full']['rate_relative_l2'];new=r['initial']['new_transport']['full']['rate_relative_l2']
            obs=r['comoving']['evolved_vs_own_initial']
            lines.append(f"|{r['case_id']}|{old}|{new}|{obs['raw_relative_l2']:.8g}|{obs['phase_registered_relative_l2']:.8g}|")
            w.writerow({'recorded_utc':r['recorded_at']['utc'],'recorded_melbourne':r['recorded_at']['melbourne'],
                'case_id':r['case_id'],'beta':r['beta'],'axis':r['axis'],'old_rate_relative':old,'new_rate_relative':new,
                'comoving_raw':obs['raw_relative_l2'],'comoving_phase_registered':obs['phase_registered_relative_l2']})
    lines+=['',SCOPE,'Original failed gates are retained. Any candidate promotion needs scientific review; no new motion result is implied.','']
    (out/'SUMMARY.md').write_text('\n'.join(lines))


def evidence(out):
    files=sorted(p for p in out.rglob('*') if p.is_file() and p.suffix in {'.json','.md','.csv'}
                 and p.name not in {'evidence-hashes.json','launch.json','stop-request.json','exit.json'})
    atomic_json(out/'evidence-hashes.json',{'recorded_at':timestamp(),'sha256':{p.relative_to(out).as_posix():sha(p) for p in files}})
    with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[out/'evidence-hashes.json']:z.write(p,p.relative_to(out).as_posix())


def selected_inputs(source,config):
    dc=diagnostic_config(config);campaign,plan,pairs,selected,manifests=compact(source,dc)
    selected=[k for k in selected if campaign['cases'][k]['physical']['dt']==config['case_dt']]
    if not selected:raise ValueError('No complete cases match the declared source timestep')
    dc['case_ids']=selected;inv=inventory(source,dc)
    if len(selected)!=config['expected_cases'] or len(inv['selected_seeds'])!=config['expected_seeds']:
        raise ValueError('Selected case/seed coverage differs from the predeclared study')
    return campaign,manifests,selected,inv


def run(source,out,config):
    source=Path(source).resolve();out=Path(out).resolve()
    if out==source or out.is_relative_to(source):raise ValueError('Study output must be outside the retained input campaign')
    out.mkdir(parents=True,exist_ok=True)
    with (out/'.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Study output is already in use')
        campaign,manifests,selected,inv=selected_inputs(source,config)
        if not inv['ready']:
            atomic_json(out/'inventory-not-ready.json',inv);raise ValueError('Missing or changed retained inputs; see inventory-not-ready.json')
        code={n:sha(Path(__file__).with_name(n)) for n in SOURCES}
        identity={'config_sha256':canonical_sha(config),'input_fingerprint':inv['input_fingerprint'],'source_sha256':code}
        path=out/'study.json'
        if path.exists():
            ledger=json.loads(path.read_text())
            if any(ledger.get(k)!=v for k,v in identity.items()):raise ValueError('Study config/source/inputs changed; use a new output')
            for key,row in ledger['cases'].items():
                if json.loads((out/'cases'/f'{key}.json').read_text())!=row:
                    raise ValueError('Saved case record differs from its checkpoint ledger')
        else:
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            dirty=bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip())
            ledger={'started_at':timestamp(),'record_id':out.name,'source_campaign':str(source),
                    **identity,'expected_cases':len(selected),'cases':{}}
            atomic_json(out/'manifest.json',{'recorded_at':timestamp(),'study_id':'s5-b-005',**identity,
                'source_commit':commit,'tracked_worktree_dirty':dirty,'config':config,
                'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
                'platform':platform.platform(),'source_scope':SCOPE})
        atomic_json(out/'inventory.json',inv);atomic_json(out/'config.json',config)
        def checkpoint():
            ledger['updated_at']=timestamp();atomic_json(path,ledger);write_outputs(out,ledger)
        ledger['status']='working';ledger.pop('error',None);checkpoint()
        try:
            if 'controls' not in ledger:
                event('START independent reconstruction controls');ledger['controls']=controls(config)
                atomic_json(out/'controls.json',ledger['controls']);checkpoint()
            for key in selected:
                if (out/'stop-request.json').exists():raise KeyboardInterrupt
                if key in ledger['cases']:continue
                event('START initialization and registration',case_id=key)
                row=case_record(source,campaign['cases'][key],campaign,manifests,config)
                atomic_json(out/'cases'/f'{key}.json',row);ledger['cases'][key]=row;checkpoint()
                event('FINISHED case',case_id=key,completed=len(ledger['cases']),expected=len(selected))
            ledger['status']='complete_pending_review'
        except KeyboardInterrupt:ledger['status']='stopped_checkpoint_retained'
        except Exception as e:
            ledger['status']='error';ledger['error']=str(e);checkpoint();evidence(out);raise
        checkpoint();evidence(out);event('SUMMARY',status=ledger['status'],completed=len(ledger['cases']),output=str(out))
        return ledger


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,default=CONFIG)
    p.add_argument('--controls-only',action='store_true');p.add_argument('--preflight',action='store_true');a=p.parse_args()
    config=json.loads(a.config.read_text());diagnostic_config(config)
    if a.controls_only:
        result=controls(config);atomic_json(a.output,result)
        print(json.dumps({'recorded_at':result['recorded_at'],'passed':result['passed'],
                          'checks':result['checks'],'output':str(a.output)},indent=2))
        return 0 if result['passed'] else 2
    if a.source is None:raise ValueError('--source must name the retained completed low-Q campaign')
    if a.preflight:
        *_,inv=selected_inputs(a.source,config);atomic_json(a.output,inv)
        print(json.dumps({'recorded_at':timestamp(),'ready':inv['ready'],'cases':len(inv['selected_cases']),
            'seeds':len(inv['selected_seeds']),'missing_or_changed':inv['missing_or_changed']},indent=2));return 0 if inv['ready'] else 2
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
    start=time.monotonic();result=run(a.source,a.output,config)
    atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':result['status'],'wall_seconds':time.monotonic()-start,'scope':SCOPE})
    return 0 if result['status']=='complete_pending_review' else 2


if __name__=='__main__':raise SystemExit(main())
