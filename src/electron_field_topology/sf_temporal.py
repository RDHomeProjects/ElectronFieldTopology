"""S5-B-006 combined endpoint audit, boundary admission and temporal convergence. Apache-2.0."""
import argparse,fcntl,json,platform,signal,subprocess,sys,threading,time,zipfile
from pathlib import Path
import numpy as np
import scipy
from .sf_motion_diagnostics import ROOT,atomic_json,event,sha
from .sf_checkpoints import timestamp
from .sf_time import Grid,retract,diagnostics
from .sf_time_run import MODEL,SCHEME,canonical_sha,state_sha,save_checkpoint,validate as validate_physics
from .sf_readmission import relax,admitted
from .sf_tail_domain import exact_extension,seed_continuation,checked_field,compact_evidence
from .sf_q1_metrics import measure
from .sf_focused_motion import lab_grid,readmit,boundary_controls,history,comoving
from .sf_reconstruction import sample_cubic,phase_comparison
from .sf_motion_metrics import evaluate
from .sf_boost_study import rate_metrics
from .sf_temporal_metrics import tail_band,endpoint_audit,geodesic_control,field_differences,observed_order
from .sf_temporal_run import run as evolve,evolution_hashes
from .skyrme import NORTH
CONFIG=ROOT/'experiments/configs/s5-b/006-focused-motion-convergence/temporal-audit.json'
FILES=['sf_temporal.py','sf_temporal_run.py','sf_temporal_metrics.py','sf_temporal_local.py','sf_focused_motion.py','sf_reconstruction.py','sf_readmission.py','sf_tail_domain.py','sf_q1_metrics.py','sf_q1_settling.py','sf_time.py','sf_time_run.py','sf_time_initial.py','sf_time_controls.py','sf_dynamics.py','sf_checkpoints.py','sf_motion_metrics.py','sf_motion_diagnostics.py','sf_boost_study.py','skyrme.py','sf_preview.py','sf_dynamics_admission.py','sf_motion_local.py']
STOP=False
SCOPE='Combined reporting audit and three-dt neutral T=1 motion comparison at admitted finite boxes. No physical-mesh/domain independence, long-time isolation, charge, quantum spin or electron acceptance.'
TERMINAL_CASES={'complete','boundary_reserve_stop','numerical_failure'}

def need(x,message):
    if not x:raise ValueError(message)

def validate(c):
    need(c['format']=='EFT-admitted-temporal-v1' and c['beta']==.3 and c['duration']==1. and c['time_steps']==[.01,.005,.0025],'Declared speed/window/three time steps required')
    need(c['models']==[{'id':'q1-x','q':1,'axis':0,'source':'q1','domains':[{'nodes':153,'length':24.32},{'nodes':167,'length':26.56}]},{'id':'q2-z','q':2,'axis':2,'source':'q2','domains':[{'nodes':127,'length':20.16},{'nodes':139,'length':22.08}]}],'Declared two-model/domain ladder required')
    need(c['tail_fraction_limit']==.001 and c['spacing']==.16 and c['shell_width']==2. and c['initial_tail_reserve']==.00075 and c['runtime_tail_reserve']==.0009 and c['expanded_guard_width']==3. and c['expanded_guard_limit']==.001,'Original shell and stricter admission reserves required')
    need(c['comparison_times']==[.25,.5,.75,1.], 'Declared matched comparison times required')
    need(c['diagnostic_time']==.05 and c['checkpoint_time']==.25 and c['common_nodes']==73 and c['fixed_comoving_half_width']==4.,'Matched observation times and fixed analysis region required')
    expected=json.loads((ROOT/'experiments/configs/sf-motion/lowq-motion.json').read_text())['limits'];need(c['limits']==expected and c['limits']['tail_fraction']==.001,'Original motion gates required unchanged')
    need(c['readmission']=={'relative_force_l2':1e-4,'acceleration_max':1e-3,'charge_relative_error':.05,'iterations_per_pass':200,'checkpoint_every':25,'stagnation_relative_energy':1e-10} and c['readmission_passes']==6,'Established preparation targets and declared work allocation required')
    for m in c['models']:
        for d in m['domains']:need(abs(d['length']/(d['nodes']-1)-.16)<1e-14,'Matched physical spacing required')

def source_inventory(source,c):
    validate(c);mapping=json.loads(Path(source).read_text());files={};records={}
    for key,s in c['sources'].items():
        folder=Path(mapping[key]).expanduser().resolve();path=folder/s['checkpoint'];reference=ROOT/s['published_run']
        need(sha(reference/'evidence.zip')==s['evidence_sha256'],'Published source compact archive differs: '+key)
        campaign=json.loads((reference/'campaign.json').read_text());row=campaign['cases'][s['case_id']]
        need(sha(path)==s['checkpoint_sha256']==row['final_checkpoint_sha256'],'Source checkpoint SHA differs: '+key)
        with zipfile.ZipFile(reference/'evidence.zip') as z:manifest=json.loads(z.read('readmission/'+s['case_id']+'/manifest.json'))
        for name,digest in manifest['code_hashes'].items():need(sha(Path(__file__).with_name(name))==digest,'Source numerical kernel differs: '+name)
        with np.load(path,allow_pickle=False) as d:
            n=d['field'];v=d['field_rate'];g=Grid((s['nodes'],)*3,(s['length'],)*3,'fixed')
            need(n.dtype==v.dtype==np.float64 and n.shape==v.shape==g.shape+(3,) and np.isfinite(n).all(),'Invalid source geometry/precision')
            need(float(d['h'])==g.spacing[0] and str(d['model_id'])==MODEL and str(d['scheme'])==SCHEME and int(d['expected_q'])==s['q'],'Source model/grid differs')
            need(str(d['config_sha256'])==canonical_sha(row['relax_config']) and str(d['code_sha256'])==manifest['code_sha256'],'Source provenance differs')
            need(np.max(abs(v))==0 and np.max(abs(np.sum(n*n,axis=-1)-1))<1e-10 and np.max(abs(n[g.fixed_mask()]-NORTH))==0,'Source constraints differ')
            need(state_sha(n,v)==row['final']['state_sha256'],'Source state differs')
        files[key]={'path':str(path),'sha256':s['checkpoint_sha256']};records[key]={'native_status':row['status'],'published_run':s['published_run'],'geometry':[s['nodes'],s['length']]}
    return {'recorded_at':timestamp(),'files':files,'input_fingerprint':canonical_sha({k:v['sha256'] for k,v in files.items()}),'source_records':records},mapping

def load_source(inv,key):
    path=Path(inv['files'][key]['path']);need(sha(path)==inv['files'][key]['sha256'],'Source changed')
    with np.load(path,allow_pickle=False) as d:return d['field'].copy()

def audit_sources(inv,c):
    source=c['sources']['q1'];folder=ROOT/source['published_run']
    with zipfile.ZipFile(folder/'evidence.zip') as z:
        campaign=json.loads(z.read('campaign.json'));policy=json.loads(z.read('plan.json'));rows=[]
        for key,r in campaign['cases'].items():
            obs=json.loads(z.read('readmission/'+key+'/observations.json'));a=endpoint_audit(r['final']['stationarity'],obs,policy['readmission'],policy,r['status'],r['result']['reason']);a['case_id']=key;rows.append(a)
    geo=geodesic_control();fixed=boundary_controls()
    need(geo['passed'] and fixed['passed'],'Analytical temporal or fixed-layer controls failed')
    return {'recorded_at':timestamp(),'historical_endpoint_audit':rows,'geodesic_control':geo,'fixed_layer_control':fixed,'passed':True,'scope':'Audit reports endpoint/window/regular-certificate separately; no source labels changed. Source records remain read-only.'}

def coast_reference(rest,rg,g,beta,axis,t):
    points=g.points();points[...,axis]=(points[...,axis]-beta*t)/np.sqrt(1-beta*beta)
    n,d=sample_cubic(rest,rg,points,axis);return retract(n,-beta/np.sqrt(1-beta*beta)*d,g)

def prepare_domain(out,model,domain,r,c,inv,save):
    folder=out/'rest'/r['id'];cfg=r['relax_config']
    if r['status'] in {'admitted','admission_rejected'}:
        need(sha(folder/'latest.npz')==r['rest_checkpoint_sha256'],'Sealed rest state changed');return r
    if 'initial_checkpoint_sha256' not in r:
        original=load_source(inv,model['source']);n=exact_extension(original,domain['nodes']);g=Grid((domain['nodes'],)*3,(domain['length'],)*3,'fixed');seed_continuation(folder,n,g,model['q'],cfg)
        r['initial_checkpoint_sha256']=sha(folder/'initial.npz');r['initial']=measure(n,g,model['q'],c);save()
    need(sha(folder/'initial.npz')==r['initial_checkpoint_sha256'],'Initial preparation state changed')
    if r.get('resume_checkpoint_sha256'):need(sha(folder/'latest.npz')==r['resume_checkpoint_sha256'],'Stopped rest checkpoint changed')
    checked_field(folder,cfg);r.pop('resume_checkpoint_sha256',None);save()
    while r.get('passes_called',0)<c['readmission_passes']:
        if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt
        result=relax(cfg,folder,pass_limit=1);r['passes_called']=r.get('passes_called',0)+(result['status']!='interrupted');r['rest_result']=result
        n,g=checked_field(folder,cfg);r['resume_checkpoint_sha256']=sha(folder/'latest.npz');save()
        if result['status']=='interrupted':raise KeyboardInterrupt
        if result['status']!='checkpointed':break
        r.pop('resume_checkpoint_sha256',None);save()
    n,g=checked_field(folder,cfg);r['rest_checkpoint_sha256']=sha(folder/'latest.npz');r['rest_final']=measure(n,g,model['q'],c)
    if not admitted(r['rest_final']['stationarity'],model['q'],c['readmission']):r.update(status='admission_rejected',reason='rest stationarity/topology unqualified');save();return r
    lab=lab_grid(g,c['beta'],model['axis']);n0,v0,projection=readmit(n,g,lab,c['beta'],model['axis'],'cubic')
    start=tail_band(n0,v0,lab,c['shell_width']);guard=tail_band(n0,v0,lab,c['expanded_guard_width'])
    nf,vf=coast_reference(n,g,lab,c['beta'],model['axis'],c['duration']);end=tail_band(nf,vf,lab,c['shell_width'])
    initial_metrics=diagnostics(n0,v0,lab)
    r['admission']={'recorded_at':timestamp(),'projection':projection,'initial_tail':start,'expanded_guard':guard,'predicted_coasting_final_tail':end,'lab_grid':list(lab.shape),'lab_lengths':list(lab.lengths),'initial_observables':initial_metrics,
       'raw_transport_baseline':rate_metrics(n0,v0,lab,c['beta'],model['axis'],c['shell_width']),
       'scope':'Stricter buffer/coasting admission predicts boundary clearance; it does not guarantee nonlinear evolution or isolation.'}
    ok=projection['passed'] and all(x['fraction'] is not None and x['fraction']<=limit for x,limit in [(start,c['initial_tail_reserve']),(guard,c['expanded_guard_limit']),(end,c['initial_tail_reserve'])])
    r.update(status='admitted' if ok else 'admission_rejected',reason=None if ok else 'initial/coasting/expanded boundary reserve not met');save();return r

def retained_history(attempts):
    # Prefer later complete attempt rows at the same physical step. Drop orphaned rows after its sealed latest checkpoint.
    merged={}
    for folder in attempts:
        folder=Path(folder);p=folder/'latest.npz'
        if not p.exists():continue
        with np.load(p,allow_pickle=False) as d:cap=int(d['step'])
        for row in json.loads((folder/'history.json').read_text()) if (folder/'history.json').exists() else []:
            if row['step']<=cap:merged[row['step']]=row
    return [merged[k] for k in sorted(merged)]

def own_comoving(final,initial,g,beta,axis,t,half):
    a=np.linspace(-half,half,33);points=np.stack(np.meshgrid(a,a,a,indexing='ij'),axis=-1);points[...,axis]*=np.sqrt(1-beta*beta);shift=points.copy();shift[...,axis]+=beta*t
    old=sample_cubic(initial,g,points,axis)[0];new=sample_cubic(final,g,shift,axis)[0]
    return {'fixed_rest_cube_side':2*half,'sampling_nodes':33,'comparison':phase_comparison(new,old),'scope':'Fixed physical comoving sample cube and same sampling operator at t0/t; no spatial registration or shrinking region.'}

def run_case(out,model,domain_row,dt,ledger,c,inv,save):
    key=f'{domain_row["id"]}-dt{dt:g}';folder=out/'cases'/key;folder.mkdir(parents=True,exist_ok=True)
    row=ledger['cases'].get(key);rest,rg=checked_field(out/'rest'/domain_row['id'],domain_row['relax_config']);g=lab_grid(rg,c['beta'],model['axis'])
    if row and row['status'] in TERMINAL_CASES:
        need(sha(Path(row['final_checkpoint']))==row['final_checkpoint_sha256'],'Completed trajectory changed');return row
    if row is None:
        n,v,adm=readmit(rest,rg,g,c['beta'],model['axis'],'cubic');need(adm['passed'],'Projection changed after admission')
        initial={'kind':'s5-b-006-audited-cubic-external','expected_q':model['q'],'beta':c['beta'],'axis':model['axis'],'rest_sha256':domain_row['rest_checkpoint_sha256'],'study_config_sha256':ledger['config_sha256'],'external_source_sha256':canonical_sha(ledger['source_sha256']),'admitted_state_sha256':state_sha(n,v)}
        physical={'case_id':key,'grid':list(g.shape),'lengths':list(g.lengths),'boundary':'fixed','dt':dt,'steps':round(c['duration']/dt),'diagnostic_every':round(c['diagnostic_time']/dt),'checkpoint_every':round(c['checkpoint_time']/dt),'initial':initial};validate_physics(physical)
        save_checkpoint(folder/'admitted.npz',n,v,0,dt,canonical_sha(physical),canonical_sha(evolution_hashes()))
        row={'id':key,'model':model['id'],'domain_id':domain_row['id'],'dt':dt,'physical':physical,'status':'working','attempts':[],'initial_checkpoint_sha256':sha(folder/'admitted.npz'),'initial_state_sha256':state_sha(n,v)};ledger['cases'][key]=row;save()
    need(sha(folder/'admitted.npz')==row['initial_checkpoint_sha256'],'Admitted initial checkpoint changed')
    resume=folder/'admitted.npz';last_step=0
    for ap in row['attempts']:
        p=Path(ap)/'latest.npz'
        if p.exists():
            with np.load(p,allow_pickle=False) as d:idx=int(d['step'])
            if idx>=last_step:resume=p;last_step=idx
    if rsha:=row.get('resume_checkpoint_sha256'):
        if str(resume)==row.get('resume_checkpoint_path'):need(sha(resume)==rsha,'Sealed trajectory resume checkpoint changed')
    row.pop('resume_checkpoint_sha256',None);row['status']='working';save()
    if last_step<row['physical']['steps']:
        ap=folder/f'attempt-{len(row["attempts"]):03d}';row['attempts'].append(str(ap));save()
        event('START matched-time trajectory',case_id=key,from_step=last_step,total_steps=row['physical']['steps'])
        result=evolve(row['physical'],ap,{'export':{'enabled':False}},resume=resume,monitor={'enabled':True,'shell_width':c['shell_width'],'warning_fraction':c['runtime_tail_reserve'],'tail_fraction_limit':c['limits']['tail_fraction'],'snapshot_every_time':c['checkpoint_time']})
        resume=ap/'latest.npz';row.update(result=result,resume_checkpoint_path=str(resume),resume_checkpoint_sha256=sha(resume));save()
        if result['status']=='interrupted' or STOP:raise KeyboardInterrupt
        end_status=result['status']
    else:end_status='complete'
    with np.load(resume,allow_pickle=False) as d:n=d['field'].copy();v=d['field_rate'].copy();final_step=int(d['step'])
    hist=retained_history(row['attempts']);need(hist and hist[0]['step']==0,'Global initial diagnostic record missing')
    atomic_json(folder/'history-combined.json',hist)
    with np.load(folder/'admitted.npz',allow_pickle=False) as d:initial=d['field'].copy()
    t=final_step*dt
    if final_step>0:
        legacy=evaluate(hist,n,v,g,rest,rg.spacing[0],c['beta'],model['axis'],model['q'],c['shell_width'],c['limits'])
        legacy['reference_label']='Historical projected-evolution versus translated TRILINEAR rest reference; retained original shape gate'
        reference,_=coast_reference(rest,rg,g,c['beta'],model['axis'],t)
        row['assessment']={'recorded_at':timestamp(),'legacy_motion':legacy,'projected_cubic_coast_reference':phase_comparison(n,reference),'own_admitted_comoving':own_comoving(n,initial,g,c['beta'],model['axis'],t,c['fixed_comoving_half_width']),
          'max_observed_tail_fraction':max(r.get('boundary_tail',{}).get('fraction') or 0. for r in hist),'tail_monitor_time_spacing':c['diagnostic_time'],'original_tail_pass_at_all_recorded_times':all(r.get('original_tail_pass',False) for r in hist),'boundary_reserve_clear_at_all_recorded_times':all(r.get('tail_warning_clear',False) for r in hist)}
    row.update(status=end_status,final_time=t,final_checkpoint=str(resume),final_checkpoint_sha256=sha(resume),final_state_sha256=state_sha(n,v))
    atomic_json(folder/'assessment.json',row);save();event('FINISHED trajectory',case_id=key,status=row['status'],time=t,maximum_observed_tail=row.get('assessment',{}).get('max_observed_tail_fraction'));return row

def snapshot_for(row,t):
    # Each accepted attempt retains quarter-time states, authenticated separately.
    for ap in reversed(row['attempts']):
        p=Path(ap)/'snapshots.json'
        for r in json.loads(p.read_text()) if p.exists() else []:
            if abs(r['time']-t)<1e-12:
                need(sha(Path(r['path']))==r['sha256'],'Sealed comparison snapshot changed');return Path(r['path'])
    raise ValueError('Missing matched-time full state: '+row['id']+' t='+str(t))

def temporal_pairs(ledger,c):
    result=[]
    for model in c['models']:
        chosen=ledger['selected_domains'].get(model['id'])
        if not chosen:continue
        rows=[ledger['cases'][f'{chosen}-dt{dt:g}'] for dt in c['time_steps']]
        need(len({r['initial_state_sha256'] for r in rows})==1,'Time-step initial fields differ')
        for t in c['comparison_times']:
            arrays=[]
            for row in rows:
                with np.load(snapshot_for(row,t),allow_pickle=False) as d:arrays.append((d['field'].copy(),d['field_rate'].copy()))
            d01=field_differences(*arrays[0],*arrays[1],c['common_nodes']);d12=field_differences(*arrays[1],*arrays[2],c['common_nodes']);d02=field_differences(*arrays[0],*arrays[2],c['common_nodes'])
            result.append({'recorded_at':timestamp(),'model':model['id'],'domain_id':chosen,'time':t,'common_nodes':c['common_nodes'],'coarse_medium':d01,'medium_fine':d12,'coarse_fine':d02,'field_order':observed_order(d01['field_relative_l2'],d12['field_relative_l2']),'rate_order':observed_order(d01['rate_relative_l2'],d12['rate_relative_l2']),'scope':'Descriptive temporal refinement on one physical grid/domain; no physical-mesh or isolation certificate.'})
    return {'recorded_at':timestamp(),'rows':result}

def output(out,d,c):
    d['updated_at']=timestamp();atomic_json(out/'campaign.json',d)
    lines=['# S5-B-006 combined audit and admitted temporal convergence','',json.dumps(d['updated_at']),'',f"Status: **{d['status']}**. Selected models: {len(d['selected_domains'])}/2. Recorded trajectory attempts: {len(d['cases'])}.",'','|Case|Status|Time reached|Maximum observed tail (%)|','|---|---|---:|---:|']
    for key,r in d['cases'].items():
        value=r.get('assessment',{}).get('max_observed_tail_fraction');lines.append(f"|{key}|{r['status']}|{r.get('final_time','')}|{100*value if value is not None else ''}|")
    lines+=['','Selected domains: '+json.dumps(d['selected_domains']), 'Admission/earlier-domain failures and safety stops remain recorded. No original threshold is weakened. All three dt cases in a selected family use the same domain and identical initial full state.',SCOPE,'Full fields and runnable handover require a verified Release archive before cleanup.','']
    (out/'SUMMARY.md').write_text('\n'.join(lines))
    import csv
    rows=[]
    for key,r in d['cases'].items():
        a=r.get('assessment',{});m=a.get('legacy_motion',{})
        rows.append({'recorded_at_utc':d['updated_at']['utc'],'recorded_at_melbourne':d['updated_at']['melbourne'],'case_id':key,'model':r['model'],'domain_id':r['domain_id'],'dt':r['dt'],'status':r['status'],'time':r.get('final_time'),'maximum_observed_tail_fraction':a.get('max_observed_tail_fraction'),'tail_pass':a.get('original_tail_pass_at_all_recorded_times'),'safety_reserve_clear':a.get('boundary_reserve_clear_at_all_recorded_times'),'legacy_shape_relative_l2':m.get('translated_static_field_relative_l2'),'speed_relative_error':m.get('speed_relative_error'),'energy_drift':m.get('max_energy_relative_drift'),'momentum_drift':m.get('max_momentum_drift_over_initial_energy')})
    if rows:
        with (out/'case-metrics.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def campaign(source,out,c):
    global STOP
    STOP=False;source=Path(source).resolve();out=Path(out).resolve();validate(c);out.mkdir(parents=True,exist_ok=True);lock=(out/'.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('Temporal campaign already running')
    inv,_=source_inventory(source,c)
    for r in inv['files'].values():need(not out.is_relative_to(Path(r['path']).parent),'Output must be separate from retained source root')
    codes={n:sha(Path(__file__).with_name(n)) for n in FILES};identity={'config_sha256':canonical_sha(c),'input_fingerprint':inv['input_fingerprint'],'source_sha256':codes}
    if (out/'campaign.json').exists():
        d=json.loads((out/'campaign.json').read_text());need(all(d[k]==v for k,v in identity.items()),'Inputs/config/source changed; preserve run and create a new record')
        need(not d['status'].startswith('complete'),'Completed run is immutable')
    else:
        need(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip(),'Commit preparation before native computation')
        d={'record_id':out.name,'started_at':timestamp(),**identity,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_worktree_dirty':False,'scope':SCOPE,'domains':{},'cases':{},'selected_domains':{},'environment':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform()}}
    d['status']='working';d.pop('error',None)
    def save():output(out,d,c)
    atomic_json(out/'plan.json',c);atomic_json(out/'inventory.json',inv);save()
    try:
        if 'audit' not in d:d['audit']=audit_sources(inv,c);atomic_json(out/'audit.json',d['audit']);save()
        for model in c['models']:
            if model['id'] in d['selected_domains']:continue
            for domain in model['domains']:
                if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt
                key=f'{model["id"]}-n{domain["nodes"]}-L{domain["length"]:g}';r=d['domains'].get(key)
                if r and r.get('family_status') in {'rejected','accepted'}:continue
                if r is None:
                    cfg={**c['readmission'],**domain,'q':model['q'],'external_initial':{'method':'exact-centred-north-extension','source_sha256':inv['files'][model['source']]['sha256'],'study_config_sha256':d['config_sha256']}}
                    r={'id':key,'model':model['id'],**domain,'status':'preparing','relax_config':cfg};d['domains'][key]=r;save()
                event('Preparing measured boundary admission',domain_id=key)
                prepare_domain(out,model,domain,r,c,inv,save)
                if r['status']!='admitted':r['family_status']='rejected';save();continue
                family_ok=True
                for dt in c['time_steps']:
                    if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt
                    row=run_case(out,model,r,dt,d,c,inv,save)
                    if row['status']!='complete' or not row['assessment']['boundary_reserve_clear_at_all_recorded_times']:
                        family_ok=False;r['family_status']='rejected';r['family_reason']='trajectory safety reserve exhausted or numerical failure; larger domain requires a fresh full three-dt family';save();break
                if family_ok:r['family_status']='accepted';d['selected_domains'][model['id']]=key;save();break
        d['status']='complete_pending_review' if len(d['selected_domains'])==2 else 'complete_admission_blocked_pending_review'
        atomic_json(out/'temporal-comparisons.json',temporal_pairs(d,c))
    except KeyboardInterrupt:d['status']='stopped_checkpoint_retained'
    except Exception as error:d['status']='error';d['error']=str(error);save();compact_evidence(out);raise
    for r in inv['files'].values():need(sha(Path(r['path']))==r['sha256'],'Original source field changed')
    save();compact_evidence(out);return d

def main():
    global STOP
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True,help='JSON map of the two retained run roots');p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,default=CONFIG);a=p.parse_args();c=json.loads(a.config.read_text());clock=time.monotonic();done=threading.Event();a.output.mkdir(parents=True,exist_ok=True)
    def stop(*_):
        global STOP
        STOP=True;raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    def heart():
        while not done.wait(30):atomic_json(a.output/'heartbeat.json',{'recorded_at':timestamp(),'wall_seconds':time.monotonic()-clock})
    threading.Thread(target=heart,daemon=True).start()
    try:r=campaign(a.source,a.output,c);code=0 if r['status'].startswith('complete') else 2
    except Exception as error:atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':'error','error':str(error),'wall_seconds':time.monotonic()-clock});raise
    finally:done.set()
    atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':r['status'],'wall_seconds':time.monotonic()-clock,'exit_code':code});event('SUMMARY',status=r['status'],output=str(a.output),selected_models=len(r['selected_domains']));return code
if __name__=='__main__':sys.exit(main())
