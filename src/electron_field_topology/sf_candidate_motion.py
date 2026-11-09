"""Checkpointed candidate motion and read-only matched-field comparisons. Apache-2.0.

The numerical step/action/readmission kernels are imported unchanged. All original
criteria are retained; observation, segmentation and early decisions are explicit.
"""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from .sf_checkpoints import timestamp,atomic_json
from .sf_higher_q_sources import need,sha,event
from .sf_time import Grid
from .sf_time_run import canonical_sha,state_sha,save_checkpoint,validate
from .sf_temporal_run import run as evolve,evolution_hashes
from .sf_temporal import retained_history,coast_reference
from .sf_focused_motion import lab_grid,readmit
from .sf_motion_metrics import evaluate,translated_reference
from .sf_reconstruction import phase_comparison,sample_cubic
from .sf_temporal_metrics import tail_band,observed_order
from .skyrme import NORTH
TERMINAL={'screen_pass','screen_failed','admission_rejected','boundary_reserve_stop','numerical_failure'}

def local_path(out,name):
    """Read native absolute provenance under an unchanged record ID after restore."""
    out=Path(out).resolve();p=Path(name);need('..' not in p.parts,'Unsafe archived path')
    if p.is_absolute():
        if p.is_relative_to(out):need(p.resolve().is_relative_to(out),'Run path escapes through a symlink');return p
        need(p.parts.count(out.name)==1,'Unrecognized archived path');p=Path(*p.parts[p.parts.index(out.name)+1:])
    need('..' not in p.parts and not p.is_absolute() and (out/p).resolve().is_relative_to(out),'Unsafe run-relative path');return out/p

def rest_state(out,r):
    path=out/r['checkpoint'];need(sha(path)==r['checkpoint_sha256'],'Sealed stationary field changed')
    with np.load(path,allow_pickle=False) as z:n=z['field'].copy()
    return n,Grid((r['nodes'],)*3,(r['length'],)*3,'fixed')

def admission(rest,rg,beta,axis,duration,c):
    g=lab_grid(rg,beta,axis);n,v,p=readmit(rest,rg,g,beta,axis,'cubic');nf,vf=coast_reference(rest,rg,g,beta,axis,duration)
    old=translated_reference(rest,rg.spacing[0],g,beta,axis,0.)
    floor=float(np.linalg.norm(n-old)/max(np.linalg.norm(old-NORTH),1e-30))
    start=tail_band(n,v,g,c['shell_width']);guard=tail_band(n,v,g,c['expanded_guard_width']);end=tail_band(nf,vf,g,c['shell_width'])
    passed=p['passed'] and floor<=c['limits']['shape_relative'] and all(row['fraction'] is not None and row['fraction']<=limit for row,limit in [(start,c['initial_tail_reserve']),(guard,c['expanded_guard_limit']),(end,c['initial_tail_reserve'])])
    return n,v,g,{'recorded_at':timestamp(),'passed':bool(passed),'projection':p,'initial_legacy_shape_floor':floor,'initial_tail':start,'expanded_guard':guard,'predicted_coasting_tail':end,'duration':duration,'beta':beta,'axis':axis,'lab_grid':list(g.shape),'lab_lengths':list(g.lengths)}

def decision(assessment,t,beta,c):
    failed=[k for k,v in assessment['legacy_motion']['checks'].items() if not v]
    stop=[k for k in failed if k!='speed' or not beta or t>=c['speed_stop_from_time']-1e-12]
    if not assessment['tail_pass_all_observations']:stop.append('tail_at_previous_observation')
    return {'recorded_at':timestamp(),'failed_original_checks':failed,'stop_checks':stop,'stop':bool(stop),'speed_stop_eligible':not beta or t>=c['speed_stop_from_time']-1e-12}

def trajectory(out,key,r,beta,axis,dt,duration,milestones,observation_time,d,c,save,check_stop):
    folder=out/'cases'/key;folder.mkdir(parents=True,exist_ok=True);row=d['cases'].get(key)
    if row and row['status']=='admitted' and 'physical' not in row:row=None
    if row and row['status'] in TERMINAL:
        if row.get('final_checkpoint'):need(sha(out/row['final_checkpoint'])==row['final_checkpoint_sha256'],'Completed moving state changed')
        return row
    rest,rg=rest_state(out,r)
    if row is None:
        n,v,g,adm=admission(rest,rg,beta,axis,duration,c)
        row={'recorded_at':timestamp(),'id':key,'rest_id':r['id'],'seed_id':r['seed_id'],'q':r['q'],'beta':beta,'axis':axis,'dt':dt,'duration':duration,'status':'admitted' if adm['passed'] else 'admission_rejected','admission':adm,'attempts':[],'milestones':{}};d['cases'][key]=row;save()
        if not adm['passed']:return row
        initial={'kind':'s5-b-010-authenticated-cubic-external','expected_q':r['q'],'beta':beta,'axis':axis,'rest_sha256':r['checkpoint_sha256'],'study_config_sha256':d['config_sha256'],'campaign_code_sha256':canonical_sha(d['source_sha256']),'admitted_state_sha256':state_sha(n,v)}
        physical={'case_id':key,'grid':list(g.shape),'lengths':list(g.lengths),'boundary':'fixed','dt':dt,'steps':round(duration/dt),'diagnostic_every':round(observation_time/dt),'checkpoint_every':round(c['snapshot_time']/dt),'initial':initial};validate(physical)
        save_checkpoint(folder/'admitted.npz',n,v,0,dt,canonical_sha(physical),canonical_sha(evolution_hashes()))
        row.update(physical=physical,status='working',initial_state_sha256=state_sha(n,v),initial_checkpoint_sha256=sha(folder/'admitted.npz'));save()
    else:g=Grid(tuple(row['physical']['grid']),tuple(row['physical']['lengths']),'fixed')
    need(sha(folder/'admitted.npz')==row['initial_checkpoint_sha256'],'Initial moving state changed')
    resume=folder/'admitted.npz';latest_step=0
    for old in row['attempts']:
        p=local_path(out,old)/'latest.npz'
        if p.exists():
            with np.load(p,allow_pickle=False) as z:s=int(z['step'])
            if s>=latest_step:resume=p;latest_step=s
    for target in milestones:
        check_stop()
        if f'{target:g}' in row['milestones']:continue
        resume=folder/'admitted.npz';step=0
        for old in row['attempts']:
            p=local_path(out,old)/'latest.npz'
            if p.exists():
                with np.load(p,allow_pickle=False) as z:s=int(z['step'])
                if s>=step:resume=p;step=s
        if row.get('sealed_resume_path') and local_path(out,row['sealed_resume_path'])==resume:need(sha(resume)==row['sealed_resume_sha256'],'Sealed resume checkpoint changed')
        elif resume!=folder/'admitted.npz':
            row.setdefault('recovery',[]).append({'recorded_at':timestamp(),'kind':'unsealed-atomic-motion-checkpoint','path':resume.relative_to(out).as_posix(),'sha256':sha(resume),'scope':'Embedded model/config/code/CRC/constraint checks are performed by the unchanged resume bridge; no prior external SHA seal claimed.'});save()
        end=round(target/dt)
        if step<end:
            ap=folder/f'attempt-{len(row["attempts"]):03d}';row['attempts'].append(str(ap.resolve()));row['target_time']=target;save();event('START candidate motion segment',case_id=key,from_step=step,to_step=end)
            result=evolve(row['physical'],ap,{'export':{'enabled':False}},resume=resume,stop_after=end,monitor={'enabled':True,'shell_width':c['shell_width'],'warning_fraction':c['runtime_tail_reserve'],'tail_fraction_limit':c['limits']['tail_fraction'],'snapshot_every_time':c['snapshot_time']})
            resume=ap/'latest.npz';row.update(result=result,sealed_resume_path=str(resume.resolve()),sealed_resume_sha256=sha(resume));save()
            if result['status']=='interrupted':raise KeyboardInterrupt
            if result['status'] not in {'complete','checkpointed'}:row['status']=result['status'];break
        with np.load(resume,allow_pickle=False) as z:n=z['field'].copy();v=z['field_rate'].copy();step=int(z['step'])
        hist=retained_history([local_path(out,p) for p in row['attempts']]);need(hist and hist[0]['step']==0,'Global t0 diagnostic missing');atomic_json(folder/'history-combined.json',hist)
        legacy=evaluate(hist,n,v,g,rest,rg.spacing[0],beta,axis,r['q'],c['shell_width'],c['limits']);ref,_=coast_reference(rest,rg,g,beta,axis,step*dt)
        assessment={'recorded_at':timestamp(),'legacy_motion':legacy,'projected_cubic_reference_raw':phase_comparison(n,ref),'maximum_observed_tail_fraction':max(x['boundary_tail']['fraction'] for x in hist),'tail_pass_all_observations':all(x['original_tail_pass'] for x in hist)}
        policy=decision(assessment,step*dt,beta,c);row['milestones'][f'{target:g}']={'assessment':assessment,'decision':policy,'checkpoint':resume.relative_to(out).as_posix(),'checkpoint_sha256':sha(resume),'state_sha256':state_sha(n,v)};row['assessment']=assessment;save()
        if policy['stop']:row.update(status='screen_failed',stop_reason=', '.join(policy['stop_checks']));break
    else:row['status']='screen_pass' if row['assessment']['legacy_motion']['bounded_case_gates_pass'] and row['assessment']['tail_pass_all_observations'] else 'screen_failed'
    row.update(final_checkpoint=resume.relative_to(out).as_posix(),final_checkpoint_sha256=sha(resume))
    with np.load(resume,allow_pickle=False) as z:
        n=z['field'].copy();v=z['field_rate'].copy();row.update(final_time=float(z['time']),final_state_sha256=state_sha(n,v))
    if row['final_time']>0 and abs(row.get('assessment',{}).get('legacy_motion',{}).get('time',-1)-row['final_time'])>1e-12:
        hist=retained_history([local_path(out,p) for p in row['attempts']]);atomic_json(folder/'history-combined.json',hist);legacy=evaluate(hist,n,v,g,rest,rg.spacing[0],beta,axis,r['q'],c['shell_width'],c['limits']);ref,_=coast_reference(rest,rg,g,beta,axis,row['final_time'])
        row['assessment']={'recorded_at':timestamp(),'legacy_motion':legacy,'projected_cubic_reference_raw':phase_comparison(n,ref),'maximum_observed_tail_fraction':max(x['boundary_tail']['fraction'] for x in hist),'tail_pass_all_observations':all(x['original_tail_pass'] for x in hist)}
    atomic_json(folder/'assessment.json',row);save();event('FINISHED candidate motion',case_id=key,status=row['status'],time=row['final_time']);return row

def at(out,row,t):
    if abs(t)<1e-12:p=out/'cases'/row['id']/'admitted.npz';expected=row['initial_checkpoint_sha256']
    else:
        found=[]
        for old in row['attempts']:
            path=local_path(out,old)/'snapshots.json'
            for snap in json.loads(path.read_text()) if path.exists() else []:
                if abs(snap['time']-t)<1e-12:found.append(snap)
        if found:p=local_path(out,found[-1]['path']);expected=found[-1]['sha256']
        else:
            need(abs(t-row.get('final_time',-1))<1e-12 and row.get('final_checkpoint'),'No retained matched-time state '+row['id']);p=out/row['final_checkpoint'];expected=row['final_checkpoint_sha256']
    need(sha(p)==expected,'Matched-time checkpoint changed')
    with np.load(p,allow_pickle=False) as z:need(abs(float(z['time'])-t)<1e-12,'Comparison time differs');return z['field'].copy(),z['field_rate'].copy()

def difference(n,v,m,w):
    return {'field_relative_l2':float(np.linalg.norm(n-m)/max(np.linalg.norm(m-NORTH),1e-30)),'rate_relative_l2':float(np.linalg.norm(v-w)/max(np.linalg.norm(w),1e-30)) if np.linalg.norm(w)>1e-20 else None,'rate_absolute_rms':float(np.sqrt(np.mean((v-w)**2)))}

def common_samples(n,v,g,c):
    a=np.linspace(-c['comparison_half_width'],c['comparison_half_width'],c['comparison_nodes']);points=np.stack(np.meshgrid(a,a,a,indexing='ij'),axis=-1)
    need(c['comparison_half_width']<min(g.lengths)/2,'Common analysis cube extends beyond source')
    field=sample_cubic(n,g,points,2)[0];coords=np.moveaxis((points+np.asarray(g.lengths)/2)/np.asarray(g.spacing),-1,0)
    rate=np.stack([map_coordinates(v[...,i],coords,order=3,mode='constant',cval=0.,prefilter=True) for i in range(3)],axis=-1)
    return field,rate

def temporal_comparison(out,rows,c):
    available=[r for r in rows if r and r.get('final_time',0)>0]
    if len(available)!=3:return {'recorded_at':timestamp(),'status':'incomplete','reason':'All three time-step cases need reached matched endpoints; original failures remain.'}
    need(len({r['initial_state_sha256'] for r in available})==1,'Temporal initial fields/rates differ');values=[]
    for t in c['detail_milestones']:
        if not all(r['final_time']>=t-1e-12 for r in rows):continue
        arrays=[at(out,r,t) for r in rows];ab=difference(*arrays[0],*arrays[1]);bc=difference(*arrays[1],*arrays[2])
        values.append({'time':t,'coarse_medium':ab,'medium_fine':bc,'field_order':observed_order(ab['field_relative_l2'],bc['field_relative_l2']),'rate_order':observed_order(ab['rate_relative_l2'],bc['rate_relative_l2'])})
    full=bool(values and abs(values[-1]['time']-c['detail_duration'])<1e-12)
    return {'recorded_at':timestamp(),'status':'measured' if full else 'partial_matched_windows' if values else 'incomplete','requested_time':c['detail_duration'],'full_window_completed':full,'case_ids':[r['id'] for r in rows],'matched_windows':values,'scope':'Same-grid three-dt full field/rate comparison at reached common windows. Partial windows do not complete the requested T0.5 comparison; order may be unresolved near roundoff and is not spatial convergence or stability.'}
