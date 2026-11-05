"""S5-B-006 fixed-layer readmission and focused physical-time campaign. Apache-2.0.

The continuum action, D4 spatial scheme, RK4 and original importer are unchanged.
Custom projected data enter the existing runner through its authenticated step-zero
continuation interface; all external initialization code is bound into physics.
"""
import argparse
import fcntl
import json
from pathlib import Path
import platform
import signal
import threading
import time
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
from .sf_checkpoints import timestamp
from .sf_motion_diagnostics import (ROOT,atomic_json,event,compact,load_rest,load_state,
    attempt_path,field_difference,sha)
from .sf_reconstruction import boosted_cubic,sample_cubic,phase_comparison
from .sf_boost_study import controls as interpolation_controls, rate_metrics
from .sf_time_initial import boosted_static
from .sf_time import Grid,retract,diagnostics
from .sf_time_run import (run as evolve,save_checkpoint,validate,MODEL,SCHEME,canonical_sha,state_sha)
from .sf_motion_metrics import evaluate,spatial_metrics
from .skyrme import NORTH

CONFIG=ROOT/'experiments/configs/s5-b/006-focused-motion-convergence/overnight.json'
PROFILE=ROOT/'experiments/configs/s5-b/006-focused-motion-convergence/preview.json'
FILES=['sf_focused_motion.py','sf_reconstruction.py','sf_time.py','sf_time_controls.py',
       'sf_time_initial.py','sf_dynamics.py','sf_time_run.py','skyrme.py',
       'sf_motion_diagnostics.py','sf_motion_metrics.py','sf_checkpoints.py','sf_boost_study.py']
OLD_TIME=['sf_time.py','sf_time_controls.py','sf_time_initial.py','sf_dynamics.py','sf_time_run.py','skyrme.py']
SCOPE='Focused fixed-reflecting-box method comparison; no mesh/domain convergence, isolated stability, charge, quantum spin or electron acceptance.'
STOP=False


def stop_requested(*_):
    global STOP
    STOP=True
    raise KeyboardInterrupt


def need(ok,message):
    if not ok:raise ValueError(message)


def source_records(source,config):
    dc={'format':'EFT-motion-diagnostics-v1','evidence_sha256':config['source_evidence_sha256'],
        'case_ids':[],'comparison_grids':[41],'shell_width':config['shell_width'],'replay_rtol':1e-9,'replay_atol':1e-11}
    c,p,_,_,m=compact(source,dc)
    return c,p,m


def validate_plan(config):
    need(config['format']=='EFT-focused-motion-v1','Unknown focused-motion format')
    need(config['methods']==['trilinear','cubic'] and config['axes']==[0,2],'Matched x/z old/cubic pairs required')
    need(config['beta']==.3 and config['dt']>0 and np.isfinite(config['dt']),'Declared beta=.3 and finite dt required')
    times=config['milestone_times']
    need(times and times==sorted(set(times)) and all(t>0 and abs(round(t/config['dt'])*config['dt']-t)<1e-12 for t in times),'Positive increasing integer-step milestones required')
    need(config['diagnostic_every']>0 and config['checkpoint_every']>0,'Positive recording intervals required')


def lab_grid(rest,beta,axis):
    n=rest.shape[0];shape=list(rest.shape);gamma=1/np.sqrt(1-beta*beta)
    shape[axis]=2*int(np.ceil((n-1)*gamma/2))+1
    return Grid(tuple(shape),rest.lengths,'fixed')


def readmit(rest,rg,grid,beta,axis,method):
    need(method in {'trilinear','cubic'},'Unknown reconstruction method')
    raw_n,raw_v=(boosted_static(rest,rg.spacing[0],grid,beta,axis) if method=='trilinear'
                 else boosted_cubic(rest,rg,grid,beta,axis))
    n,v=retract(raw_n,raw_v,grid);fixed=grid.fixed_mask();free=~fixed
    dn=n-raw_n;dv=v-raw_v
    report={'recorded_at':timestamp(),'method':method,'beta':beta,'axis':axis,
       'raw_state_sha256':state_sha(raw_n,raw_v),'admitted_state_sha256':state_sha(n,v),
       'raw_fixed_field_max':float(abs(raw_n[fixed]-NORTH).max()),'raw_fixed_rate_max':float(abs(raw_v[fixed]).max()),
       'field_correction_max':float(abs(dn).max()),'rate_correction_max':float(abs(dv).max()),
       'field_correction_rms':float(np.sqrt(np.mean(dn*dn))),'rate_correction_rms':float(np.sqrt(np.mean(dv*dv))),
       'free_field_correction_max':float(abs(dn[free]).max()),'free_rate_correction_max':float(abs(dv[free]).max()),
       'fixed_field_max':float(abs(n[fixed]-NORTH).max()),'fixed_rate_max':float(abs(v[fixed]).max()),
       'unit_max':float(abs(np.sum(n*n,axis=-1)-1).max()),'tangency_max':float(abs(np.sum(n*v,axis=-1)).max())}
    report['passed']=(report['fixed_field_max']==0 and report['fixed_rate_max']==0
       and report['unit_max']<1e-10 and report['tangency_max']<1e-10
       and report['free_field_correction_max']<1e-12 and report['free_rate_correction_max']<1e-12)
    return n,v,report


def boundary_controls():
    rest_grid=Grid((81,)*3,(16.,)*3,'fixed');rows=[]
    for axis in [0,2]:
        field=np.broadcast_to(NORTH,rest_grid.shape+(3,)).copy();pos=[40]*3;pos[axis]=2
        field[tuple(pos)]=[np.sin(.1),0,np.cos(.1)]
        for beta in [.1,.3]:
            lab=lab_grid(rest_grid,beta,axis)
            for method in ['trilinear','cubic']:
                n,v,r=readmit(field,rest_grid,lab,beta,axis,method)
                rows.append(r)
    # Independent time-event test on free nodes, and exact zero rates at held nodes.
    g=Grid((17,)*3,(8.,)*3,'fixed');x=g.points();theta=.1*np.maximum(1-np.sum(x*x,axis=-1)/4,0)**6
    field=np.stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1)
    event_errors=[]
    for axis in [0,2]:
        lab=lab_grid(g,.1,axis);gamma=1/np.sqrt(.99);eps=1e-6;p=lab.points();p[...,axis]*=gamma
        n,v,r=readmit(field,g,lab,.1,axis,'cubic')
        plus=p.copy();minus=p.copy();plus[...,axis]-=gamma*.1*eps;minus[...,axis]+=gamma*.1*eps
        a=sample_cubic(field,g,plus,axis)[0];b=sample_cubic(field,g,minus,axis)[0]
        a[lab.fixed_mask()]=NORTH;b[lab.fixed_mask()]=NORTH
        event_errors.append(float(abs((a-b)/(2*eps)-v).max()))
    return {'recorded_at':timestamp(),'rows':rows,'free_node_event_errors':event_errors,
        'passed':all(r['passed'] for r in rows) and max(event_errors)<1e-8
           and any(r['raw_fixed_field_max']>1e-4 for r in rows if r['method']=='cubic' and r['beta']==.1),
        'scope':'Manufactured thin-layer projection and chain-rule controls; no trajectory.'}


def inventory(source,config):
    validate_plan(config);c,p,m=source_records(source,config);files={}
    for sid in config['admission_seeds']:
        load_rest(source,sid,c)
        rel=f'readmission/{sid}/latest.npz';files[rel]=sha(Path(source)/rel)
    timings=[]
    for sid in config['seeds']:
        for axis in config['axes']:
            key=f'{sid}-b0.3-a{axis}-dt0.01';row=c['cases'][key]
            need(row['status']=='complete','Required original reference case is not complete: '+key)
            for which in ['initial','final']:
                load_state(source,row,m,which)
                rel=(attempt_path(source,row)/f'{which}.npz').relative_to(source).as_posix();files[rel]=sha(Path(source)/rel)
            old_duration=row['physical']['steps']*row['physical']['dt']
            timings.append(row['result']['wall_seconds']*2*config['milestone_times'][-1]/old_duration*(.01/config['dt']))
    return {'recorded_at':timestamp(),'source_evidence_sha256':config['source_evidence_sha256'],
       'files':files,'input_fingerprint':canonical_sha(files),'estimated_wall_seconds_from_previous':sum(timings),
       'estimate_scope':'Prior matching old-initializer CPU runs scaled by method count, window and dt; load/thermal/checkpoint overhead varies.'}


def prepare_case(source,case,campaign,config,inv,code):
    rest,rg=load_rest(source,case['seed_id'],campaign);g=lab_grid(rg,config['beta'],case['axis'])
    n,v,admission=readmit(rest,rg,g,config['beta'],case['axis'],case['method'])
    need(admission['passed'],'Fixed-layer/constraint admission failed: '+case['id'])
    old_key=f'{case["seed_id"]}-b0.3-a{case["axis"]}-dt0.01'
    old_n,old_v,_=load_state(source,campaign['cases'][old_key],config['_manifests'],'initial')
    raw_n,raw_v=boosted_static(rest,rg.spacing[0],g,.3,case['axis'])
    need(state_sha(raw_n,raw_v)==state_sha(old_n,old_v),'Original initializer failed bit-exact replay')
    initial={'kind':'s5-b-006-external-projected','method':case['method'],'expected_q':case['q'],
       'rest_sha256':campaign['seeds'][case['seed_id']]['field_sha256'],'beta':config['beta'],'axis':case['axis'],
       'external_source_sha256':code,'admitted_state_sha256':state_sha(n,v),'input_fingerprint':inv['input_fingerprint']}
    physical={'case_id':case['id'],'grid':list(g.shape),'lengths':list(g.lengths),'boundary':'fixed',
       'dt':config['dt'],'steps':round(config['milestone_times'][-1]/config['dt']),
       'diagnostic_every':config['diagnostic_every'],'checkpoint_every':config['checkpoint_every'],'initial':initial}
    validate(physical)
    admission.update(original_raw_replay_bit_exact=True,
       source_rest_status=campaign['seeds'][case['seed_id']]['status'],
       raw_transport=rate_metrics(raw_n,raw_v,g,.3,case['axis'],config['shell_width']),
       admitted_transport=rate_metrics(n,v,g,.3,case['axis'],config['shell_width']),
       initial_observables=diagnostics(n,v,g),initial_spatial=spatial_metrics(n,v,g,config['shell_width']))
    return n,v,g,physical,admission


def history(attempts,through):
    merged={}
    for i,folder in enumerate(attempts):
        folder=Path(folder);cap=through
        for later in attempts[i+1:]:
            if (Path(later)/'initial.npz').exists():
                with np.load(Path(later)/'initial.npz',allow_pickle=False) as d:cap=min(cap,int(d['step']))
                break
        if (folder/'history.json').exists():
            for row in json.loads((folder/'history.json').read_text()):
                if row['step']<=cap:merged[row['step']]=row
    return [merged[k] for k in sorted(merged)]


def comoving(n,initial,grid,beta,axis,t,margin):
    gamma=1/np.sqrt(1-beta*beta);half=min(grid.lengths)/2-margin-abs(beta*t)
    if half<=0:return {'available':False,'reason':'No common comoving core'}
    a=np.linspace(-half,half,33);xi=np.stack(np.meshgrid(a,a,a,indexing='ij'),axis=-1)
    x0=xi.copy();x0[...,axis]/=gamma;xt=x0.copy();xt[...,axis]+=beta*t
    start=sample_cubic(initial,grid,x0,axis)[0];final=sample_cubic(n,grid,xt,axis)[0]
    return {'available':True,'cube_side':2*half,'sampling_nodes':33,'comparison':phase_comparison(final,start),
       'scope':'Same known-comoving sampling operator at t=0/t; no spatial fit. Region shrinks with observation time; compare methods at matched times only.'}


def write_outputs(out,ledger):
    atomic_json(out/'campaign.json',ledger)
    lines=['# S5-B-006 focused overnight motion','',json.dumps(ledger['updated_at']), '',
       f"Status: **{ledger['status']}**; complete cases {sum(r['status']=='complete' for r in ledger['cases'].values())}/{ledger['expected_cases']}.",
       '', '|Case|Status|Milestones|', '|---|---|---|']
    for key,row in ledger['cases'].items():lines.append(f"|{key}|{row['status']}|{', '.join(row.get('milestones',{}))}|")
    lines+=['','|Case / time|Energy drift|Legacy shape error|Tail fraction|Failed scientific checks|','|---|---:|---:|---:|---|']
    for key,row in ledger['cases'].items():
        for t,m in row.get('milestones',{}).items():
            a=m['assessment'];failed=', '.join(k for k,v in a['checks'].items() if not v) or 'none (bounded case only)'
            lines.append(f"|{key} / {t}|{a['max_energy_relative_drift']:.5g}|{a['translated_static_field_relative_l2']:.5g}|{a['final']['boundary_shell_energy_fraction']:.5g}|{failed}|")
    lines+=['',SCOPE,'All raw/projection corrections and scientific failures remain recorded. Wall-sensitive long windows do not establish isolated motion.','']
    (out/'SUMMARY.md').write_text('\n'.join(lines))


def evidence(out):
    files=sorted(p for p in out.rglob('*') if p.is_file() and p.suffix in {'.json','.md','.csv'}
       and p.name not in {'launch.json','exit.json','stop-request.json','evidence-hashes.json','heartbeat.json'}
       and 'preview' not in p.parts)
    atomic_json(out/'evidence-hashes.json',{'recorded_at':timestamp(),'sha256':{p.relative_to(out).as_posix():sha(p) for p in files}})
    with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[out/'evidence-hashes.json']:z.write(p,p.relative_to(out).as_posix())


def preview_series(folder,attempts):
    target=folder/'preview';target.mkdir(exist_ok=True);frames={}
    for attempt in attempts:
        p=Path(attempt)/'preview/manifest.json'
        if p.exists():
            m=json.loads(p.read_text())
            for f in m['frames']:
                if 'vti' in f:frames[f['step']]=(f['time'],Path(attempt)/'preview'/f['vti'])
    import os
    root=ET.Element('VTKFile',type='Collection',version='0.1',byte_order='LittleEndian');collection=ET.SubElement(root,'Collection')
    for k,(t,p) in sorted(frames.items()):ET.SubElement(collection,'DataSet',timestep=str(t),group='',part='0',file=os.path.relpath(p,target))
    ET.ElementTree(root).write(target/'series.pvd',encoding='utf-8',xml_declaration=True)


def run(source,out,config,profile):
    global STOP
    STOP=False;source=Path(source).resolve();out=Path(out).resolve()
    need(not (out==source or out.is_relative_to(source)),'Output must be outside the source campaign')
    validate_plan(config);out.mkdir(parents=True,exist_ok=True)
    lock=(out/'.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('Focused campaign is already active')
    inv=inventory(source,config);campaign,source_plan,manifests=source_records(source,config)
    codes={name:sha(Path(__file__).with_name(name)) for name in FILES};code=canonical_sha(codes)
    identity={'config_sha256':canonical_sha(config),'input_fingerprint':inv['input_fingerprint'],'code_sha256':code}
    file=out/'campaign.json'
    if file.exists():
        ledger=json.loads(file.read_text());need(all(ledger[k]==v for k,v in identity.items()),'Inputs/config/code changed; preserve this run and use a new record')
        for row in ledger['cases'].values():
            for m in row['milestones'].values():need(sha(Path(m['checkpoint']))==m['checkpoint_sha256'],'A sealed milestone checkpoint changed')
    else:
        import subprocess
        ledger={'record_id':out.name,'started_at':timestamp(),**identity,'source_sha256':codes,'config':config,
          'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'source_worktree_dirty':bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip()),
          'expected_cases':len(config['seeds'])*4,'admissions':{},'cases':{},'scope':SCOPE}
    def checkpoint(status=None):
        ledger['updated_at']=timestamp()
        if status:ledger['status']=status
        write_outputs(out,ledger)
    checkpoint('working');atomic_json(out/'inventory.json',inv);atomic_json(out/'plan.json',config)
    try:
        if 'controls' not in ledger:
            base=json.loads((ROOT/'experiments/configs/s5-b/005-boost-initialization/study.json').read_text())
            ledger['controls']={'interpolation':interpolation_controls(base),'fixed_layers':boundary_controls()}
            atomic_json(out/'controls.json',ledger['controls'])
        need(ledger['controls']['interpolation']['passed'] and ledger['controls']['fixed_layers']['passed'],'Independent admission controls failed; no trajectory admitted')
        # Readmit all retained static grids at beta .1/.3, for both spatial axes/methods.
        for sid in config['admission_seeds']:
            for axis in config['axes']:
                for beta in [.1,.3]:
                    for method in config['methods']:
                        key=f'{sid}-b{beta:g}-a{axis}-{method}'
                        if key in ledger['admissions']:continue
                        if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt
                        rest,rg=load_rest(source,sid,campaign);g=lab_grid(rg,beta,axis)
                        _,_,r=readmit(rest,rg,g,beta,axis,method);r['seed_id']=sid
                        ledger['admissions'][key]=r;checkpoint()
                        need(r['passed'],'Retained-field fixed-layer admission failed: '+key)
        config_with_metadata={**config,'_manifests':manifests}
        for sid in config['seeds']:
            for axis in config['axes']:
                for method in config['methods']:
                    if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt
                    key=f'{sid}-a{axis}-{method}';folder=out/'cases'/key;folder.mkdir(parents=True,exist_ok=True)
                    row=ledger['cases'].get(key)
                    if row and row['status'] in {'complete','numerical_failure'}:continue
                    if row is None:
                        case={'id':key,'seed_id':sid,'q':campaign['seed_configs'][sid]['q'],'axis':axis,'method':method}
                        n,v,g,physics,adm=prepare_case(source,case,campaign,config_with_metadata,inv,code)
                        oldhash=canonical_sha({k:codes[k] for k in OLD_TIME})
                        save_checkpoint(folder/'admitted.npz',n,v,0,config['dt'],canonical_sha(physics),oldhash)
                        row={**case,'physics':physics,'admission':adm,'status':'working','attempts':[],'milestones':{},
                             'initial_checkpoint_sha256':sha(folder/'admitted.npz')}
                        ledger['cases'][key]=row;atomic_json(folder/'admission.json',adm);checkpoint()
                    physics=row['physics'];g=validate(physics)
                    # Recover from completed or uncleanly stopped attempts, always from a complete NPZ.
                    resume=folder/'admitted.npz';current_step=0
                    need(sha(resume)==row['initial_checkpoint_sha256'],'Initial checkpoint changed')
                    for ap in row['attempts']:
                        candidate=Path(ap)/'latest.npz'
                        if candidate.exists():
                            with np.load(candidate,allow_pickle=False) as d:idx=int(d['step'])
                            if idx>=current_step:resume=candidate;current_step=idx
                    if 'resume_checkpoint_sha256' in row and str(resume)==row.get('resume_checkpoint_path'):
                        need(sha(resume)==row['resume_checkpoint_sha256'],'Sealed resume checkpoint changed')
                    for target_time in config['milestone_times']:
                        target=round(target_time/config['dt'])
                        if str(target_time) in row['milestones']:continue
                        if current_step<target:
                            if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt
                            ap=folder/f'attempt-{len(row["attempts"]):03d}';row['attempts'].append(str(ap));checkpoint()
                            event('START trajectory segment',case_id=key,from_step=current_step,to_step=target,total_steps=physics['steps'])
                            result=evolve(physics,ap,profile,resume=resume,stop_after=target)
                            candidate=ap/'latest.npz'
                            if candidate.exists():
                                resume=candidate
                                with np.load(resume,allow_pickle=False) as d:current_step=int(d['step'])
                                row.update(resume_checkpoint_path=str(resume),resume_checkpoint_sha256=sha(resume))
                            checkpoint()
                            if result['status']=='numerical_failure':row['status']='numerical_failure';break
                            if result['status']=='interrupted' or STOP:raise KeyboardInterrupt
                            need(current_step==target,'Segment did not reach its declared milestone')
                        with np.load(resume,allow_pickle=False) as d:n=d['field'].copy();v=d['field_rate'].copy()
                        with np.load(folder/'admitted.npz',allow_pickle=False) as d:initial=d['field'].copy()
                        rest,rg=load_rest(source,sid,campaign)
                        hist=history(row['attempts'],target)
                        e0=hist[0]['energy']
                        for hrow in hist:
                            hrow['global_energy_relative_change']=(hrow['energy']-e0)/max(abs(e0),1e-30)
                            hrow['attempt_balance_scope']='Source work/balance fields restart per attempt; global drift uses original t=0 energy.'
                        atomic_json(folder/'history-combined.json',hist)
                        metric=evaluate(hist,n,v,g,rest,rg.spacing[0],.3,axis,row['q'],config['shell_width'],source_plan['limits'])
                        metric.update(recorded_at=timestamp(),comoving_own_initial=comoving(n,initial,g,.3,axis,target_time,config['shell_width']),
                            r99_cone_window_clear=target_time<row['admission']['initial_spatial']['initial_light_cone_clearance'],
                            r99_scope='99-percent-energy geometric indicator only; finite tails and reflecting walls remain.')
                        row['milestones'][str(target_time)]={'assessment':metric,'checkpoint':str(resume),'checkpoint_sha256':sha(resume),'state_sha256':state_sha(n,v)}
                        atomic_json(folder/f'milestone-{target:06d}.json',row['milestones'][str(target_time)])
                        preview_series(folder,row['attempts']);checkpoint()
                    if row['status']!='numerical_failure':row['status']='complete'
                    checkpoint()
        ledger['status']='complete_pending_review' if all(r['status']=='complete' for r in ledger['cases'].values()) else 'complete_with_failures_pending_review'
        # Direct full-state pair comparisons at identical physical times and grid.
        pairs={}
        for sid in config['seeds']:
            for axis in config['axes']:
                old=ledger['cases'][f'{sid}-a{axis}-trilinear'];new=ledger['cases'][f'{sid}-a{axis}-cubic']
                for t in config['milestone_times']:
                    if str(t) not in old['milestones'] or str(t) not in new['milestones']:continue
                    a=Path(old['milestones'][str(t)]['checkpoint']);b=Path(new['milestones'][str(t)]['checkpoint'])
                    with np.load(a,allow_pickle=False) as z:na=z['field'].copy();va=z['field_rate'].copy()
                    with np.load(b,allow_pickle=False) as z:nb=z['field'].copy();vb=z['field_rate'].copy()
                    pairs[f'{sid}-a{axis}-t{t:g}']={'recorded_at':timestamp(),**field_difference(na,va,nb,vb)}
        atomic_json(out/'method-pairs.json',pairs)
    except KeyboardInterrupt:ledger['status']='stopped_checkpoint_retained'
    except Exception as e:
        ledger['status']='error';ledger['error']=str(e);checkpoint();evidence(out);raise
    checkpoint();evidence(out);event('SUMMARY',status=ledger['status'],output=str(out),complete=sum(r['status']=='complete' for r in ledger['cases'].values()))
    return ledger


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,default=CONFIG);p.add_argument('--profile',type=Path,default=PROFILE);p.add_argument('--preflight',action='store_true')
    a=p.parse_args();cfg=json.loads(a.config.read_text())
    if a.preflight:
        result=inventory(a.source,cfg);atomic_json(a.output,result);print(json.dumps(result,indent=2));return 0
    signal.signal(signal.SIGTERM,stop_requested)
    start=time.monotonic();done=threading.Event()
    a.output.mkdir(parents=True,exist_ok=True)
    def heartbeat():
        while not done.wait(30):atomic_json(a.output/'heartbeat.json',{'recorded_at':timestamp(),'elapsed_wall_seconds':time.monotonic()-start})
    threading.Thread(target=heartbeat,daemon=True).start()
    try:result=run(a.source,a.output,cfg,json.loads(a.profile.read_text()))
    finally:done.set()
    atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':result['status'],'wall_seconds':time.monotonic()-start})
    return 0 if result['status']=='complete_pending_review' else 2


if __name__=='__main__':raise SystemExit(main())
