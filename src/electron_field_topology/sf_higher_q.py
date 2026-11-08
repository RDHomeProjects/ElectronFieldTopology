"""S5-B-007 staged coarse Q17/Q19 motion screen. Apache-2.0.

Calls unchanged stationary readmission and D4/projected-RK4 kernels. Coarse screening
is distinct from spatial/domain convergence and records all original motion gates.
"""
import argparse,csv,fcntl,json,platform,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
import numpy as np
import scipy
from .sf_higher_q_sources import ROOT,need,sha,event,load,recover,validate_field,authenticate
from .sf_checkpoints import timestamp,atomic_json
from .sf_time import Grid
from .sf_time_run import canonical_sha,state_sha,save_checkpoint,validate as validate_physics
from .sf_readmission import relax,stationarity,admitted
from .sf_tail_domain import exact_extension,seed_continuation,checked_field,compact_evidence
from .sf_focused_motion import lab_grid,readmit,boundary_controls
from .sf_temporal import coast_reference,retained_history,own_comoving,FILES as BASE_FILES
from .sf_temporal_run import run as evolve,evolution_hashes
from .sf_temporal_metrics import tail_band,geodesic_control,field_differences
from .sf_motion_metrics import evaluate,translated_reference
from .sf_reconstruction import sample_cubic,phase_comparison
from .skyrme import NORTH
CONFIG=ROOT/'experiments/configs/s5-b/007-higher-q-motion/coarse-screen.json'
FILES=sorted(set(BASE_FILES+['sf_higher_q.py','sf_higher_q_sources.py','sf_higher_q_local.py']))
STOP=False
SCOPE='Exploratory coarse Q17/Q19 neutral motion screen; Q1 parked, Q2 convergence open. Screen results select follow-up work; physical-resolution/domain and long-time qualification remain separate.'
TERMINAL_REST={'admitted','coarse_topology_unresolved','preparation_unresolved','boundary_admission_rejected'}
TERMINAL_CASE={'screen_pass','screen_failed','boundary_reserve_stop','numerical_failure'}

def validate(c):
    need(c['format']=='EFT-higher-q-screen-v1','Unknown screen format')
    need(c['models']==[{'id':'q17','q':17,'axis':2,'source':'q17'},{'id':'q19','q':19,'axis':2,'source':'q19'}],'Only the declared Q17/Q19 screen is allowed')
    need(c['coarse_rest']=={'nodes':97,'length':23.04,'spacing':.24,'source_stride':2},'Coarse physical grid changed; use a new study specification')
    need(c['reference_rest']=={'nodes':127,'length':20.16,'spacing':.16},'Existing Q2 reference grid required')
    need(c['beta']==.3 and c['duration']==.2 and c['time_step']==.01 and c['confirmation_dt']==.005,'Declared short screen and optional half-dt confirmation required')
    need(c['milestones']==[.05,.1,.2] and c['diagnostic_time']==.01 and c['snapshot_time']==.05 and c['speed_stop_from_time']==.1,'Declared early-stop and sampling times required')
    need(c['shell_width']==2. and c['initial_tail_reserve']==.00075 and c['expanded_guard_width']==3. and c['expanded_guard_limit']==.001 and c['runtime_tail_reserve']==.0009,'Original shell and additional safety reserves required')
    expected=load(ROOT/'experiments/configs/sf-motion/lowq-motion.json')['limits'];need(c['limits']==expected,'Original motion criteria changed')
    need(c['readmission']=={'relative_force_l2':1e-4,'acceleration_max':1e-3,'charge_relative_error':.05,'iterations_per_pass':50,'checkpoint_every':25,'stagnation_relative_energy':1e-10} and c['maximum_readmission_calls']==4,'Declared bounded preparation work/targets required')
    need(c['temporal_screen_limits']=={'field_relative_l2':1e-4,'rate_relative_l2':1e-3},'Declared two-dt screening consistency limits required')
    need(set(c['sources'])=={'q2','q17','q19'},'Reference and both original higher-Q sources required')
    for key,s in c['sources'].items():
        need(s['key']==key and s['q']==int(key[1:]),'Source label differs');authenticate(s)
    for dt in [c['time_step'],c['confirmation_dt']]:
        need(all(abs(round(t/dt)*dt-t)<1e-12 for t in c['milestones']+[c['diagnostic_time'],c['snapshot_time']]),'Nonintegral physical observation time')
    return c

def coarse_field(original,source,domain):
    """Exact every-second-node sampling on unchanged coordinates, then north extension."""
    need(original.shape==(source['nodes'],)*3+(3,) and source['nodes']==129 and source['length']==15.36,'Declared archived129 source required')
    small=original[::domain['source_stride'],::domain['source_stride'],::domain['source_stride']].copy()
    need(abs(source['length']/(len(small)-1)-domain['spacing'])<1e-14,'Decimation changes physical coordinates')
    return exact_extension(small,domain['nodes'])

def load_rest(out,row):
    p=out/row['checkpoint'];need(sha(p)==row['checkpoint_sha256'],'Prepared rest checkpoint changed')
    with np.load(p,allow_pickle=False) as d:n=d['field'].copy()
    g=Grid((row['nodes'],)*3,(row['length'],)*3,'fixed')
    return n,g

def rest_metrics(n,g,c):
    return {'recorded_at':timestamp(),'stationarity':stationarity(n,g),'tail':tail_band(n,np.zeros_like(n),g,c['shell_width']),'state_sha256':state_sha(n,np.zeros_like(n))}

def prepare(out,model,d,c,save):
    key=model['id'];row=d['rest'].get(key);folder=out/'rest'/key
    if row and row['status']=='initializing':row=None
    if row and row['status'] in TERMINAL_REST:load_rest(out,row);return row
    spec=c['sources'][model['source']];original,source_info=validate_field(out/'sources'/(model['source']+'.npz'),spec)
    if row is None:
        domain=c['reference_rest'] if key=='q2' else c['coarse_rest'];g=Grid((domain['nodes'],)*3,(domain['length'],)*3,'fixed')
        n=original if key=='q2' else coarse_field(original,spec,domain)
        cfg={**c['readmission'],'nodes':domain['nodes'],'length':domain['length'],'q':model['q'],'external_initial':{'source_sha256':spec['sha256'],'method':'retained-exact-D4-rest' if key=='q2' else 'exact-stride-two-and-centred-north-extension','screen_config_sha256':canonical_sha(c)}}
        row={'id':key,'q':model['q'],'nodes':domain['nodes'],'length':domain['length'],'status':'initializing','source':source_info,'config':cfg,'optimizer_calls_allocated':0};d['rest'][key]=row;save()
        seed_continuation(folder,n,g,model['q'],cfg);row['initial']=rest_metrics(n,g,c);row['initial_checkpoint_sha256']=sha(folder/'initial.npz');row['checkpoint']='rest/'+key+'/latest.npz';row['checkpoint_sha256']=sha(folder/'latest.npz');row['status']='preparing';save()
    need(sha(folder/'initial.npz')==row['initial_checkpoint_sha256'],'Initial coarse/reference rest changed')
    actual=sha(folder/'latest.npz')
    n,g=checked_field(folder,row['config'])
    if actual!=row['checkpoint_sha256']:
        row.setdefault('recovery',[]).append({'recorded_at':timestamp(),'kind':'unsealed-atomic-optimizer-checkpoint','sha256':actual,'scope':'Embedded code/config/model/CRC/constraints checked; no previous external SHA seal for this endpoint.'});row['checkpoint_sha256']=actual;save()
    m=stationarity(n,g)
    topo=lambda x:abs(abs(x['hopf_integral'])-model['q'])/model['q']<=c['readmission']['charge_relative_error'] and x['minimum_corner_cone']>0 and x['unit_error']<1e-10
    if not topo(m):row.update(status='coarse_topology_unresolved',reason='Coarse representation does not meet original topology/constraint admission; no moving run and no physical rejection of this Q.')
    elif key=='q2' and not admitted(m,2,c['readmission']):row.update(status='preparation_unresolved',reason='Retained Q2 reference no longer meets measured preparation targets; higher-Q screen blocked.')
    else:
        while not admitted(m,model['q'],c['readmission']) and row['optimizer_calls_allocated']<c['maximum_readmission_calls']:
            check_stop(out);row['optimizer_calls_allocated']+=1;save();event('START bounded coarse readmission',model=key,call=row['optimizer_calls_allocated'],maximum_calls=c['maximum_readmission_calls'])
            result=relax(row['config'],folder,pass_limit=1);row['optimizer_result']=result;row['checkpoint_sha256']=sha(folder/'latest.npz');n,g=checked_field(folder,row['config']);m=stationarity(n,g);row['latest']=rest_metrics(n,g,c);save()
            if result['status']=='interrupted' or STOP:raise KeyboardInterrupt
            if result['status'] not in {'checkpointed','stationary'}:break
        row['status']='rest_stationary' if admitted(m,model['q'],c['readmission']) else 'preparation_unresolved'
        if row['status']!='rest_stationary':row['reason']='Bounded readmission unresolved; retain native optimizer status and refine/extend preparation only in a new follow-up.'
    row['final']=rest_metrics(n,g,c);row['checkpoint_sha256']=sha(folder/'latest.npz');save()
    if row['status']!='rest_stationary':return row
    lab=lab_grid(g,c['beta'],model['axis']);n0,v0,projection=readmit(n,g,lab,c['beta'],model['axis'],'cubic');nf,vf=coast_reference(n,g,lab,c['beta'],model['axis'],c['duration']);oldref=translated_reference(n,g.spacing[0],lab,c['beta'],model['axis'],0)
    admission={'recorded_at':timestamp(),'projection':projection,'initial_tail':tail_band(n0,v0,lab,c['shell_width']),'expanded_guard':tail_band(n0,v0,lab,c['expanded_guard_width']),'predicted_coasting_tail':tail_band(nf,vf,lab,c['shell_width']),'initial_legacy_shape_floor':float(np.linalg.norm(n0-oldref)/max(np.linalg.norm(oldref-NORTH),1e-30)),'lab_grid':list(lab.shape),'lab_lengths':list(lab.lengths)}
    ok=projection['passed'] and admission['initial_legacy_shape_floor']<=c['limits']['shape_relative'] and all(admission[name]['fraction'] is not None and admission[name]['fraction']<=limit for name,limit in [('initial_tail',c['initial_tail_reserve']),('expanded_guard',c['expanded_guard_limit']),('predicted_coasting_tail',c['initial_tail_reserve'])])
    row['admission']=admission
    row['status']='admitted' if ok else 'boundary_admission_rejected'
    if not ok:row.update(status='boundary_admission_rejected',reason='Initial/coasting/width3 reserve, fixed-layer projection or historical-reference floor failed; no automatic box ladder or finer computation.')
    save();return row

def decide(metrics,t,c):
    """Original flags never change; short first milestone defers speed-stop only."""
    failed=[k for k,v in metrics['legacy_motion']['checks'].items() if not v]
    stop=[k for k in failed if k!='speed' or t>=c['speed_stop_from_time']-1e-12]
    if not metrics['tail_pass_all_observations']:stop.append('tail_at_previous_observation')
    return {'recorded_at':timestamp(),'failed_original_checks':failed,'stop_checks':stop,'stop':bool(stop),'speed_stop_eligible':t>=c['speed_stop_from_time']-1e-12}

def check_stop(out):
    if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt

def assess(hist,n,v,g,rest,rg,model,c):
    t=hist[-1]['time'];legacy=evaluate(hist,n,v,g,rest,rg.spacing[0],c['beta'],model['axis'],model['q'],c['shell_width'],c['limits']);ref,_=coast_reference(rest,rg,g,c['beta'],model['axis'],t)
    return {'recorded_at':timestamp(),'legacy_motion':legacy,'projected_cubic_reference_raw':phase_comparison(n,ref),'own_admitted_fixed_comoving':None,'maximum_observed_tail_fraction':max(x['boundary_tail']['fraction'] for x in hist),'tail_pass_all_observations':all(x['original_tail_pass'] for x in hist),'scope':'Original trilinear shape/speed/etc flags retained; projected cubic raw reference is additional. Short coarse screen only.'}

def trajectory(out,model,rest_row,dt,d,c,save,reference=False):
    key=model['id']+f'-dt{dt:g}';folder=out/'cases'/key;folder.mkdir(parents=True,exist_ok=True);r=d['cases'].get(key)
    if r and r['status'] in TERMINAL_CASE:
        need(sha(out/r['final_checkpoint'])==r['final_checkpoint_sha256'],'Completed moving state changed');return r
    rest,rg=load_rest(out,rest_row);g=lab_grid(rg,c['beta'],model['axis'])
    if r is None:
        n,v,adm=readmit(rest,rg,g,c['beta'],model['axis'],'cubic');need(adm['passed'],'Initial projection differs')
        initial={'kind':'s5-b-007-external-cubic-screen','expected_q':model['q'],'beta':c['beta'],'axis':model['axis'],'rest_sha256':rest_row['checkpoint_sha256'],'study_config_sha256':d['config_sha256'],'campaign_code_sha256':canonical_sha(d['source_sha256']),'admitted_state_sha256':state_sha(n,v)}
        physical={'case_id':key,'grid':list(g.shape),'lengths':list(g.lengths),'boundary':'fixed','dt':dt,'steps':round(c['duration']/dt),'diagnostic_every':round(c['diagnostic_time']/dt),'checkpoint_every':round(c['snapshot_time']/dt),'initial':initial};validate_physics(physical)
        save_checkpoint(folder/'admitted.npz',n,v,0,dt,canonical_sha(physical),canonical_sha(evolution_hashes()))
        r={'id':key,'model':model['id'],'q':model['q'],'axis':model['axis'],'reference':reference,'dt':dt,'status':'working','physical':physical,'attempts':[],'milestones':{},'initial_state_sha256':state_sha(n,v),'initial_checkpoint_sha256':sha(folder/'admitted.npz')};d['cases'][key]=r;save()
    need(sha(folder/'admitted.npz')==r['initial_checkpoint_sha256'],'Moving initial checkpoint changed')
    for target in c['milestones']:
        check_stop(out)
        if f'{target:g}' in r['milestones']:continue
        resume=folder/'admitted.npz';step=0
        for ap in r['attempts']:
            p=Path(ap)/'latest.npz'
            if p.exists():
                with np.load(p,allow_pickle=False) as z:s=int(z['step'])
                if s>=step:resume=p;step=s
        if r.get('sealed_resume_path')==str(resume):need(sha(resume)==r['sealed_resume_sha256'],'Sealed moving resume changed')
        end=round(target/dt)
        if step<end:
            ap=folder/f'attempt-{len(r["attempts"]):03d}';r['attempts'].append(str(ap.resolve()));r['target_time']=target;save();event('START short motion segment',case_id=key,from_step=step,to_step=end)
            result=evolve(r['physical'],ap,{'export':{'enabled':False}},resume=resume,stop_after=end,monitor={'enabled':True,'shell_width':c['shell_width'],'warning_fraction':c['runtime_tail_reserve'],'tail_fraction_limit':c['limits']['tail_fraction'],'snapshot_every_time':c['snapshot_time']})
            resume=ap/'latest.npz';r['result']=result;r['sealed_resume_path']=str(resume.resolve());r['sealed_resume_sha256']=sha(resume);save()
            if result['status']=='interrupted' or STOP:raise KeyboardInterrupt
            if result['status'] not in {'complete','checkpointed'}:
                r['status']=result['status'];break
        with np.load(resume,allow_pickle=False) as z:n=z['field'].copy();v=z['field_rate'].copy();step=int(z['step'])
        hist=retained_history(r['attempts']);need(hist and hist[0]['step']==0,'Global initial observation missing');atomic_json(folder/'history-combined.json',hist)
        a=assess(hist,n,v,g,rest,rg,model,c);policy=decide(a,step*dt,c);r['milestones'][f'{target:g}']={'assessment':a,'decision':policy,'checkpoint':resume.relative_to(out).as_posix(),'checkpoint_sha256':sha(resume),'state_sha256':state_sha(n,v)};r['assessment']=a;save()
        if policy['stop']:r.update(status='screen_failed',stop_reason='original gates: '+', '.join(policy['stop_checks']));break
    else:r['status']='screen_pass' if r['assessment']['legacy_motion']['bounded_case_gates_pass'] and r['assessment']['tail_pass_all_observations'] else 'screen_failed'
    r['final_checkpoint']=resume.relative_to(out).as_posix();r['final_checkpoint_sha256']=sha(resume)
    with np.load(resume,allow_pickle=False) as z:r['final_time']=float(z['time']);r['final_state_sha256']=state_sha(z['field'],z['field_rate'])
    atomic_json(folder/'assessment.json',r);save();event('FINISHED coarse motion case',case_id=key,status=r['status'],time=r['final_time']);return r

def temporal_compare(out,model,d,c):
    a=d['cases'][model['id']+f'-dt{c["time_step"]:g}'];b=d['cases'][model['id']+f'-dt{c["confirmation_dt"]:g}'];need(a['initial_state_sha256']==b['initial_state_sha256'],'Confirmation initial field/rate differs')
    with np.load(out/a['final_checkpoint'],allow_pickle=False) as x,np.load(out/b['final_checkpoint'],allow_pickle=False) as y:
        need(float(x['time'])==float(y['time'])==c['duration'],'Confirmation times differ');x1,xv=x['field'],x['field_rate'];y1,yv=y['field'],y['field_rate'];field=float(np.linalg.norm(x1-y1)/max(np.linalg.norm(y1-NORTH),1e-30));rate=float(np.linalg.norm(xv-yv)/max(np.linalg.norm(yv),1e-30))
    limits=c['temporal_screen_limits'];return {'recorded_at':timestamp(),'time':c['duration'],'region':'whole lab grid','field_relative_l2':field,'rate_relative_l2':rate,'screen_consistent':field<=limits['field_relative_l2'] and rate<=limits['rate_relative_l2'],'limits':limits,'scope':'Two-dt consistency screen with predeclared thresholds; no convergence order or spatial-convergence claim.'}

def followup(out,d,c):
    rows=[]
    for model in c['models']:
        key=model['id'];rest=d['rest'].get(key);case=d['cases'].get(key+f'-dt{c["time_step"]:g}');confirm=d['cases'].get(key+f'-dt{c["confirmation_dt"]:g}')
        passed=bool(case and confirm and case['status']==confirm['status']=='screen_pass' and d.get('temporal',{}).get(key,{}).get('screen_consistent'))
        rows.append({'model':key,'disposition':'promising_coarse_followup' if passed else 'review_coarse_failure_or_preparation','original129_source_sha256':c['sources'][key]['sha256'],'coarse_rest':({'checkpoint':rest.get('checkpoint'),'sha256':rest.get('checkpoint_sha256'),'state_sha256':rest.get('final',{}).get('state_sha256')} if rest else None),'motion_parent':({'checkpoint':case.get('final_checkpoint'),'sha256':case.get('final_checkpoint_sha256')} if case else None),'recommended_action':'Use admitted coarse rest as a warm start for new finer rest grids, freshly readmit and rerun matched motion from t0; include an original129-source-start control to expose basin inheritance.' if passed else 'Keep the failure. Diagnose resolution/preparation versus dynamics; use the original129 field for a finer representation if coarse topology or preparation failed. No automatic expensive rerun.','followup_options':c['followup']})
    atomic_json(out/'followup.json',{'recorded_at':timestamp(),'parent_run':out.name,'parent_config_sha256':d['config_sha256'],'candidates':rows,'q1':'parked; original1.563660% speed failure retained','q2':'Reference control does not close its physical-mesh/domain work. Return to low-Q methods if control fails or both higher-Q screens are unresolved.','automatic_fine_work_started':False})

def output(out,d,c):
    d['updated_at']=timestamp();atomic_json(out/'campaign.json',d)
    lines=['# S5-B-007 coarse Q17/Q19 motion screen','',json.dumps(d['updated_at']),'',f"Status: **{d['status']}**. Q1 parked; Q2 control precedes higher-Q work.",'','| Case | State | Time | Original speed error | Shape error | Maximum tail |','|---|---|---:|---:|---:|---:|']
    csvrows=[]
    for key,r in d['cases'].items():
        a=r.get('assessment',{});m=a.get('legacy_motion',{});lines.append(f"| {key} | {r['status']} | {r.get('final_time',m.get('time',''))} | {m.get('speed_relative_error','')} | {m.get('translated_static_field_relative_l2','')} | {a.get('maximum_observed_tail_fraction','')} |")
        csvrows.append({'recorded_at_utc':d['updated_at']['utc'],'recorded_at_melbourne':d['updated_at']['melbourne'],'case_id':key,'status':r['status'],'time':r.get('final_time',m.get('time')),'speed_relative_error':m.get('speed_relative_error'),'shape_relative_l2':m.get('translated_static_field_relative_l2'),'maximum_tail_fraction':a.get('maximum_observed_tail_fraction'),'energy_drift':m.get('max_energy_relative_drift'),'momentum_drift':m.get('max_momentum_drift_over_initial_energy'),'original_checks':json.dumps(m.get('checks',{}),sort_keys=True)})
    lines+=['','| Rest candidate | State | Preparation calls used |','|---|---|---:|']
    for key,r in d['rest'].items():lines.append(f"| {key} | {r['status']} | {r['optimizer_calls_allocated']} |")
    lines+=['','Fractions are dimensionless: multiply by100 for percent. Original tail0.1%, shape/speed1%, energy/momentum0.1%, topology5% and constraints1e-10 remain. Early first-milestone speed failures are recorded but become stop-eligible at T0.1.',SCOPE,'Original sources, coarse rest fields and admitted/milestone/latest full float64 states are retained for a separate finer follow-up. No fine computation is started automatically. Full data require verified Release archival before cleanup.','']
    (out/'SUMMARY.md').write_text('\n'.join(lines))
    if csvrows:
        with (out/'case-metrics.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(csvrows[0]),lineterminator='\n');w.writeheader();w.writerows(csvrows)

def campaign(out,c,source_map=None):
    global STOP
    STOP=False;validate(c);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);lock=(out/'.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('Screen already running')
    codes={n:sha(Path(__file__).with_name(n)) for n in FILES};identity={'config_sha256':canonical_sha(c),'source_sha256':codes}
    if (out/'campaign.json').exists():
        d=load(out/'campaign.json');need(all(d[k]==v for k,v in identity.items()),'Screen config/source changed; preserve run and use a new record');need(not d['status'].startswith('complete'),'Completed screen is immutable')
    else:
        need(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip(),'Commit the handover preparation before computation')
        d={'record_id':out.name,'started_at':timestamp(),**identity,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'scope':SCOPE,'rest':{},'cases':{},'temporal':{},'environment':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform()},'q1_disposition':'parked; original speed failure preserved'}
    d.update(status='working');d.pop('error',None)
    def save():output(out,d,c)
    atomic_json(out/'plan.json',c);save()
    try:
        controls={'recorded_at':timestamp(),'geodesic':geodesic_control(),'fixed_layer':boundary_controls()};need(controls['geodesic']['passed'] and controls['fixed_layer']['passed'],'Independent analytic/fixed-layer controls failed');atomic_json(out/'controls.json',controls)
        mapping=load(source_map) if source_map else {};inventory={}
        for key,spec in c['sources'].items():
            check_stop(out);target=out/'sources'/(key+'.npz');target.parent.mkdir(exist_ok=True)
            if target.exists():need(sha(target)==spec['sha256'],'Retained original source changed')
            else:
                source=Path(mapping[key]).expanduser().resolve() if key in mapping else recover(spec,ROOT/'artifacts/cache/s5-b-007')
                validate_field(source,spec);shutil.copy2(source,target)
            _,inventory[key]=validate_field(target,spec)
        fingerprint=canonical_sha({k:v['sha256'] for k,v in inventory.items()})
        if 'input_fingerprint' in d:need(d['input_fingerprint']==fingerprint,'Screen original inputs changed')
        d['input_fingerprint']=fingerprint;atomic_json(out/'inventory.json',{'recorded_at':timestamp(),'files':inventory,'input_fingerprint':fingerprint});save()
        reference={'id':'q2','q':2,'axis':2,'source':'q2'};rr=prepare(out,reference,d,c,save)
        ref=trajectory(out,reference,rr,c['time_step'],d,c,save,True) if rr['status']=='admitted' else None
        if not ref or ref['status']!='screen_pass':
            d.update(status='complete_reference_blocked_pending_review',reason='Q2 reference failed preparation or a measured short-motion gate; no higher-Q optimization/trajectory attempted.');save();followup(out,d,c);compact_evidence(out);return d
        for model in c['models']:
            check_stop(out);rr=prepare(out,model,d,c,save)
            if rr['status']=='admitted':trajectory(out,model,rr,c['time_step'],d,c,save)
        # Both cheap screens precede any finer-time work.
        for model in c['models']:
            key=model['id'];r=d['cases'].get(key+f'-dt{c["time_step"]:g}')
            if not r or r['status']!='screen_pass':continue
            check_stop(out);r2=trajectory(out,model,d['rest'][key],c['confirmation_dt'],d,c,save)
            if r2['status']=='screen_pass':d['temporal'][key]=temporal_compare(out,model,d,c);save()
        d['status']='complete_pending_review';followup(out,d,c)
    except KeyboardInterrupt:d['status']='stopped_checkpoint_retained'
    except Exception as error:d.update(status='error',error=str(error));save();compact_evidence(out);raise
    save();compact_evidence(out);return d

def main():
    global STOP
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--output',type=Path,required=True);a.add_argument('--config',type=Path,default=CONFIG);a.add_argument('--source-map',type=Path);x=a.parse_args();start=time.monotonic();done=threading.Event();x.output.mkdir(parents=True,exist_ok=True)
    def stop(*_):
        global STOP
        STOP=True;raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    def heartbeat():
        while not done.wait(30):atomic_json(x.output/'heartbeat.json',{'recorded_at':timestamp(),'wall_seconds':time.monotonic()-start})
    threading.Thread(target=heartbeat,daemon=True).start()
    try:r=campaign(x.output,load(x.config),x.source_map);code=0 if r['status'].startswith('complete') else 2
    except Exception as error:atomic_json(x.output/'exit.json',{'recorded_at':timestamp(),'status':'error','error':str(error),'wall_seconds':time.monotonic()-start,'exit_code':1});raise
    finally:done.set()
    atomic_json(x.output/'exit.json',{'recorded_at':timestamp(),'status':r['status'],'wall_seconds':time.monotonic()-start,'exit_code':code});event('SUMMARY',status=r['status'],output=str(x.output));return code
if __name__=='__main__':sys.exit(main())
