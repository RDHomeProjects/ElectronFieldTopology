"""S5-B-010 fresh Q3/Q4/Q7 survey and conditional detailed motion. Apache-2.0.

No numerical action, force, mass operator, optimizer or RK step is replaced.
This module owns the declared allocation, lineage, gates and retained records.
"""
import argparse,csv,fcntl,json,platform,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
import numpy as np
import scipy
from .sf_checkpoints import timestamp,atomic_json
from .sf_higher_q_sources import ROOT,need,sha,event,load,recover,validate_field,authenticate
from .sf_higher_q import FILES as BASE_FILES
from .sf_candidate_seeds import candidates,sampled
from .sf_candidate_motion import trajectory,rest_state,admission,at,difference,common_samples,temporal_comparison
from .sf_time import Grid
from .sf_time_run import canonical_sha,state_sha
from .sf_readmission import relax,stationarity,admitted,checkpoint
from .sf_tail_domain import checked_field,exact_extension,compact_evidence,READMISSION_FILES
from .sf_temporal_metrics import tail_band,geodesic_control
from .sf_focused_motion import boundary_controls
from .sf_reconstruction import sample_cubic
from .sf_topology import preimages,resample
from .knot_diagram import crossings,knot_determinant,diagram_link,VIEWS
from .skyrme import NORTH
CONFIG=ROOT/'experiments/configs/s5-b/010-intermediate-q-survey/study.json'
FILES=sorted(set(BASE_FILES+['sf_candidate_seeds.py','sf_candidate_motion.py','sf_candidate_survey.py','sf_candidate_local.py','sf_candidate_replay.py','sf_topology.py','knot_diagram.py']))
TERMINAL_REST={'stationary','representation_unresolved','preparation_unresolved','stationarity_unresolved','topology_unresolved'}
STOP=False

def validate(c):
    need(c['format']=='EFT-intermediate-q-survey-v1' and c['seeds']==candidates(),'Declared six fresh starts required')
    need(c['levels']==[{'id':'coarse','nodes':97,'length':23.04},{'id':'medium','nodes':121,'length':23.04},{'id':'fine','nodes':145,'length':23.04}] and c['domain']=={'id':'domain','nodes':169,'length':26.88},'Declared physical-mesh/domain matrix required')
    need(c['readmission']=={'relative_force_l2':1e-4,'acceleration_max':1e-3,'charge_relative_error':.05,'iterations_per_pass':200,'checkpoint_every':25,'stagnation_relative_energy':1e-10} and c['maximum_preparation_calls']==6,'Strict stationarity and explicit six200-iteration allocations required')
    need(c['medium_retry_if_no_coarse_stationary'] is True,'Declared one-level fresh representation/preparation retry required')
    need(c['beta']==.3 and c['screen_duration']==.2 and c['detail_duration']==.5 and c['screen_dt']==.01 and c['time_steps']==[.02,.01,.005],'Declared motion matrix required')
    need(c['screen_milestones']==[.1,.2] and c['detail_milestones']==[.1,.2,.5] and c['screen_diagnostic_time']==.01 and c['detail_diagnostic_time']==.02 and c['snapshot_time']==.1 and c['speed_stop_from_time']==.2,'Matched observations and early-stop ordering required')
    expected=load(ROOT/'experiments/configs/sf-motion/lowq-motion.json')['limits'];need(c['limits']==expected,'Original case criteria changed')
    need(c['shell_width']==2. and c['initial_tail_reserve']==.00075 and c['runtime_tail_reserve']==.0009 and c['expanded_guard_width']==3. and c['expanded_guard_limit']==.001,'Original boundary reserves required')
    need(c['comparison_half_width']==8. and c['comparison_nodes']==41 and c['curve_max_tetrahedra']==300000 and c['curve_polygon_nodes']==128 and c['curve_max_crossings']==40 and c['curve_max_components']==16,'Declared read-only diagnostic budgets required')
    need(c['curve_targets']==[[.000007,.000011,-1.],[.000013,-.000017,-1.]],'Both fixed near-south preimage targets required')
    need(c['reference_source']==load(ROOT/'experiments/configs/s5-b/007-higher-q-motion/coarse-screen.json')['sources']['q2'],'Authenticated retained Q2 control required');authenticate(c['reference_source'])
    for dt in c['time_steps']:need(all(abs(round(t/dt)*dt-t)<1e-12 for t in c['detail_milestones']+[c['detail_diagnostic_time'],c['snapshot_time']]),'Unmatched temporal samples')
    return c

def metrics(n,g,c):return {'recorded_at':timestamp(),'stationarity':stationarity(n,g),'tail':tail_band(n,np.zeros_like(n),g,c['shell_width']),'state_sha256':state_sha(n,np.zeros_like(n))}

def seed_rest(folder,n,g,q,cfg):
    folder.mkdir(parents=True,exist_ok=True);codes={s:sha(Path(__file__).with_name(s)) for s in READMISSION_FILES};code=canonical_sha(codes);cs=canonical_sha(cfg)
    if (folder/'manifest.json').exists():
        old=load(folder/'manifest.json');need(old['config_sha256']==cs and old['code_sha256']==code,'Unknown partial rest destination')
        if (folder/'history.json').exists():need(all(r['iteration']==0 for r in load(folder/'history.json')),'Unregistered optimizer progress exists; preserve for manual recovery')
    m=stationarity(n,g);atomic_json(folder/'config.json',cfg);atomic_json(folder/'manifest.json',{'started_at':timestamp(),'config_sha256':cs,'code_sha256':code,'code_hashes':codes,'config':cfg,'model':'SF-relativistic-neutral-v1','scheme':'D4-action-projected-RK4-v1','scope':'Declared fresh analytic or authenticated warm-start iteration-zero D4 preparation.'})
    checkpoint(folder/'initial.npz',n,g,q,cs,0,0,code);checkpoint(folder/'latest.npz',n,g,q,cs,0,0,code);atomic_json(folder/'history.json',[{'recorded_at':timestamp(),'iteration':0,'pass_index':0,**m}])

def prepare(out,key,seed,grid_spec,route,parent,d,c,save,check_stop,optimize=True):
    row=d['rest'].get(key);folder=out/'rest'/key
    if row and row['status'] in TERMINAL_REST:rest_state(out,row);return row
    g=Grid((grid_spec['nodes'],)*3,(grid_spec['length'],)*3,'fixed')
    if row is None:
        lineage={'route':route,'seed_sha256':canonical_sha(seed),'parent_rest_id':parent['id'] if parent else None,'parent_checkpoint_sha256':parent['checkpoint_sha256'] if parent else None}
        projection={'maximum_held_layer_correction':0.,'free_nodes_changed':False}
        if route=='fresh':n=sampled(g,seed)
        elif route=='retained-reference':
            with np.load(out/'sources/q2.npz',allow_pickle=False) as z:n=z['field'].copy()
        else:
            old,og=rest_state(out,parent)
            n=exact_extension(old,grid_spec['nodes']) if route=='same-spacing-extension' else sample_cubic(old,og,g.points(),2)[0]
            projection['maximum_held_layer_correction']=float(np.max(abs(n[g.fixed_mask()]-NORTH)));n[g.fixed_mask()]=NORTH
        lineage['initial_boundary_projection']=projection
        cfg={**c['readmission'],'nodes':grid_spec['nodes'],'length':grid_spec['length'],'q':seed['q'],'external_initial':{**lineage,'study_config_sha256':d['config_sha256']}}
        seed_rest(folder,n,g,seed['q'],cfg);initial=metrics(n,g,c)
        row={'recorded_at':timestamp(),'id':key,'seed_id':seed['id'],'q':seed['q'],'level':grid_spec['id'],'nodes':grid_spec['nodes'],'length':grid_spec['length'],'status':'preparing','lineage':lineage,'config':cfg,'calls_allocated':0,'initial':initial,'initial_checkpoint_sha256':sha(folder/'initial.npz'),'checkpoint':(folder/'latest.npz').relative_to(out).as_posix(),'checkpoint_sha256':sha(folder/'latest.npz')};d['rest'][key]=row;save()
    need(sha(folder/'initial.npz')==row['initial_checkpoint_sha256'],'Initial stationary field changed');n,g=checked_field(folder,row['config']);actual=sha(folder/'latest.npz')
    with np.load(folder/'latest.npz',allow_pickle=False) as z:need(z['field_rate'].dtype==np.float64 and z['field_rate'].shape==n.shape and int(z['iteration'])>=0 and int(z['pass_index'])>=0,'Invalid rest rate precision or native optimizer counters')
    if actual!=row['checkpoint_sha256']:
        row.setdefault('recovery',[]).append({'recorded_at':timestamp(),'kind':'unsealed-atomic-optimizer-checkpoint','sha256':actual,'scope':'Embedded source/config/model/geometry/CRC/constraints checked; no prior external checkpoint SHA seal claimed.'});row['checkpoint_sha256']=actual;save()
    m=stationarity(n,g)
    topo=lambda x:abs(abs(x['hopf_integral'])-seed['q'])/seed['q']<=c['readmission']['charge_relative_error'] and x['minimum_corner_cone']>0 and x['unit_error']<1e-10
    if not topo(m):row.update(status='representation_unresolved',reason='Initial/recovered field does not meet measured topology representation gates')
    else:
        while optimize and not admitted(m,seed['q'],c['readmission']) and row['calls_allocated']<c['maximum_preparation_calls']:
            check_stop();need(shutil.disk_usage(out).free>2*1024**3,'Less than2 GiB free; checkpoint retained. Free space or archive completed work before resuming.')
            row['calls_allocated']+=1;d['current_operation']={'kind':'preparation','rest_id':key,'call':row['calls_allocated']};save();event('START stationary batch',rest_id=key,call=row['calls_allocated'],max_calls=c['maximum_preparation_calls'])
            result=relax(row['config'],folder,pass_limit=1);row['native_result']=result;row['checkpoint_sha256']=sha(folder/'latest.npz');n,g=checked_field(folder,row['config']);m=stationarity(n,g);row['latest']=metrics(n,g,c);save()
            if result['status']=='interrupted':raise KeyboardInterrupt
            if result['status'] not in {'checkpointed','stationary'}:break
        if admitted(m,seed['q'],c['readmission']):row.update(status='stationary',reason=None)
        else:
            native=row.get('native_result',{});status=native.get('status');row.update(status=status if status in {'topology_unresolved','stationarity_unresolved'} else 'preparation_unresolved',reason=native.get('reason') or 'Declared preparation allocation exhausted or retained reference unqualified; no physical candidate rejection')
    row['final']=metrics(n,g,c);row['checkpoint_sha256']=sha(folder/'latest.npz');save();event('FINISHED stationary preparation',rest_id=key,status=row['status'],force=m['relative_force_l2'],acceleration=m['acceleration_max']);return row

def polygon_summary(curve,c):
    rows=[]
    for view in VIEWS:
        try:
            count=len(crossings(curve,normal=view))
            if count>c['curve_max_crossings']:rows.append({'normal':list(view),'status':'projection_budget','crossings':count});continue
            rows.append({'normal':list(view),'status':'regular',**knot_determinant(curve,view)})
        except ValueError as e:rows.append({'normal':list(view),'status':'unresolved','reason':str(e)})
    valid=[r['determinant'] for r in rows if r['status']=='regular'];agree=len(valid)>=2 and len(set(valid))==1
    return {'projections':rows,'agreed':agree,'determinant':valid[0] if agree else None,'knot_type':'not_identified','scope':'Budgeted finite polygon determinant; not a unique knot-name or continuum certificate.'}

def core_diagnostics(out,row,c,save):
    if row.get('core_diagnostics'):
        need(sha(out/row['core_diagnostics']['path'])==row['core_diagnostics']['sha256'],'Core diagnostic changed');return
    n,g=rest_state(out,row);records=[];folder=out/'core'/row['id'];folder.mkdir(parents=True,exist_ok=True)
    for i,target in enumerate(c['curve_targets']):
        try:
            data=preimages(n,g.spacing[0],target,c['curve_max_tetrahedra']);curves=data.pop('curves');polygons=[resample(curve,c['curve_polygon_nodes']) for curve in curves]
            path=folder/f'target-{i:02d}.npz';st=timestamp()
            with path.open('wb') as f:np.savez_compressed(f,**{f'curve_{j:03d}':curve for j,curve in enumerate(curves)},written_utc=st['utc'],written_melbourne=st['melbourne'])
            data.update(recorded_at=st,curve_file=path.relative_to(out).as_posix(),curve_sha256=sha(path),polygon_invariants=[polygon_summary(curve,c) for curve in polygons] if len(polygons)<=c['curve_max_components'] else [],links=[])
            if len(polygons)>c['curve_max_components']:data.update(invariant_status='component_budget_exceeded; every extracted curve retained');records.append(data);continue
            for a in range(len(polygons)):
                for b in range(a+1,len(polygons)):
                    for view in VIEWS:
                        try:data['links'].append({'components':[a,b],'normal':list(view),**diagram_link(polygons[a],polygons[b],view)})
                        except ValueError as e:data['links'].append({'components':[a,b],'normal':list(view),'status':'unresolved','reason':str(e)})
        except (ValueError,np.linalg.LinAlgError) as e:data={'recorded_at':timestamp(),'status':'unresolved','target':target,'reason':str(e)}
        records.append(data)
    path=folder/'diagnostics.json';atomic_json(path,{'recorded_at':timestamp(),'rest_id':row['id'],'rest_checkpoint_sha256':row['checkpoint_sha256'],'targets':records,'scope':'Finite piecewise-linear preimages and polygon determinants/linking at two fixed targets. No unique knot-name or continuum-isotopy certificate; do not infer a surviving trefoil from its seed label.'});row['core_diagnostics']={'path':path.relative_to(out).as_posix(),'sha256':sha(path)};save()

def select(rows,cases):
    pool=[r for r in rows if r['status']=='stationary']
    qualified=[r for r in pool if cases.get(r['id']+'-screen-dt0.01',{}).get('admission',{}).get('passed')]
    return min(qualified or pool,key=lambda r:(r['final']['stationarity']['energy'],r['seed_id'])) if pool else None

def motion(out,key,r,dt,duration,d,c,save,check_stop,beta=None,axis=2):
    if r['status']!='stationary':
        d['skips'][key]={'recorded_at':timestamp(),'reason':'Stationary preparation unqualified','parent_rest_id':r['id']};save();return None
    detail=duration==c['detail_duration'];d['current_operation']={'kind':'motion','case_id':key};save()
    return trajectory(out,key,r,c['beta'] if beta is None else beta,axis,dt,duration,c['detail_milestones'] if detail else c['screen_milestones'],c['detail_diagnostic_time'] if detail else c['screen_diagnostic_time'],d,c,save,check_stop)

def comparison(out,left,right,c,role,kind):
    requested=c['detail_duration'];reached=min(left.get('final_time',0),right.get('final_time',0)) if left and right else 0.;matched=[t for t in c['detail_milestones'] if t<=reached+1e-12];time_value=max(matched) if matched else None;row={'recorded_at':timestamp(),'kind':kind,'role':role,'case_ids':[left['id'] if left else None,right['id'] if right else None],'requested_time':requested,'time':time_value}
    if time_value is None:return {**row,'status':'incomplete','reason':'No matched declared endpoint available; early failures retained'}
    arrays=[]
    for r in [left,right]:
        n,v=at(out,r,time_value);g=Grid(tuple(r['physical']['grid']),tuple(r['physical']['lengths']),'fixed');arrays.append(common_samples(n,v,g,c))
    return {**row,'status':'measured' if time_value==requested else 'partial_matched_window','full_window_completed':time_value==requested,'fixed_cube_side':2*c['comparison_half_width'],'sampling_nodes':c['comparison_nodes'],'difference':difference(*arrays[0],*arrays[1]),'scope':'Same fixed physical cube, normalized Hermite field and raw cubic rate sampling at a reached common endpoint. No fitted registration; partial windows do not complete T0.5, and this is not a whole-box error or automatic convergence-order claim.'}

def output(out,d,c):
    d['updated_at']=timestamp();atomic_json(out/'campaign.json',d)
    lines=['# S5-B-010 Q3/Q4/Q7 candidate survey','',json.dumps(d['updated_at']),'',f"Status: **{d['status']}**; phase: {d.get('phase','starting')}. Q1 parked; Q2 reference retained.",'','| Rest state | Status | Calls | Force | Acceleration | Rest tail fraction |','|---|---|---:|---:|---:|---:|'];restrows=[];caserows=[]
    for key,r in d['rest'].items():
        m=r.get('final',r.get('latest',r.get('initial',{})));s=m.get('stationarity',{});tail=m.get('tail',{}).get('fraction');lines.append(f"| {key} | {r['status']} | {r['calls_allocated']} | {s.get('relative_force_l2','')} | {s.get('acceleration_max','')} | {tail} |")
        restrows.append({'recorded_utc':d['updated_at']['utc'],'recorded_melbourne':d['updated_at']['melbourne'],'rest_id':key,'seed_id':r['seed_id'],'q':r['q'],'route':r['lineage']['route'],'nodes':r['nodes'],'length':r['length'],'status':r['status'],'calls_allocated':r['calls_allocated'],'energy':s.get('energy'),'force':s.get('relative_force_l2'),'acceleration':s.get('acceleration_max'),'hopf':s.get('hopf_integral'),'cone':s.get('minimum_corner_cone'),'rest_tail_fraction':tail})
    lines+=['','| Motion case | Status | Time | Speed error | Shape error | Maximum tail |','|---|---|---:|---:|---:|---:|']
    for key,r in d['cases'].items():
        a=r.get('assessment',{});m=a.get('legacy_motion',{});lines.append(f"| {key} | {r['status']} | {r.get('final_time','')} | {m.get('speed_relative_error')} | {m.get('translated_static_field_relative_l2','')} | {a.get('maximum_observed_tail_fraction','')} |")
        caserows.append({'recorded_utc':d['updated_at']['utc'],'recorded_melbourne':d['updated_at']['melbourne'],'case_id':key,'rest_id':r['rest_id'],'q':r['q'],'beta':r['beta'],'axis':r['axis'],'dt':r['dt'],'status':r['status'],'final_time':r.get('final_time'),'speed_relative_error':m.get('speed_relative_error'),'shape_relative_l2':m.get('translated_static_field_relative_l2'),'max_tail_fraction':a.get('maximum_observed_tail_fraction'),'checks':json.dumps(m.get('checks',{}),sort_keys=True)})
    lines+=['','All values above are fractions/model units, not percentages or SI electron units. Original gates and failed/skipped cases are retained. Fresh seed labels are not final knot identifications. Q1 remains parked.','Full float64 initial/latest/milestone states and curves stay local until the included archive command uploads and download-verifies the entire run. Compact evidence excludes full fields.','']
    (out/'SUMMARY.md').write_text('\n'.join(lines))
    for name,rows in [('rest-metrics.csv',restrows),('case-metrics.csv',caserows)]:
        if rows:
            with (out/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def campaign(out,c):
    global STOP
    STOP=False;validate(c);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);lock=(out/'.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('Candidate survey already running')
    identity={'config_sha256':canonical_sha(c),'source_sha256':{n:sha(Path(__file__).with_name(n)) for n in FILES},'dependency_sha256':{n:sha(ROOT/n) for n in ['pyproject.toml','uv.lock']}}
    if (out/'campaign.json').exists():
        d=load(out/'campaign.json');need(d['record_id']==out.name,'Restored record ID differs from output folder');need(all(d[k]==v for k,v in identity.items()),'Config/numerical source changed; completed and interrupted runs retain their original inputs');need(not d['status'].startswith('complete'),'Completed campaign is immutable; start a new record')
    else:
        need(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip(),'Commit the prepared handover before computation')
        d={'record_id':out.name,'started_at':timestamp(),**identity,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'environment':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform()},'rest':{},'cases':{},'selected':{},'skips':{},'comparisons':{},'q1':'parked; original1.563660% speed failure retained','scope':c['scope']}
    d.update(status='working');d.pop('error',None);atomic_json(out/'plan.json',c)
    def save():output(out,d,c)
    def check_stop():
        if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt
        need(all(sha(Path(__file__).with_name(n))==h for n,h in d['source_sha256'].items()) and all(sha(ROOT/n)==h for n,h in d['dependency_sha256'].items()),'Source or dependency files changed during the campaign; checkpoint retained. Restore the original preparation before resume.')
    try:
        save();d['phase']='q2-reference';save()
        if 'controls' not in d:
            geo=geodesic_control();fixed=boundary_controls();need(geo['passed'] and fixed['passed'],'Analytical/fixed-layer controls failed');d['controls']={'recorded_at':timestamp(),'geodesic':geo,'fixed_layer':fixed};atomic_json(out/'controls.json',d['controls']);save()
        original=out/'sources/q2.npz';original.parent.mkdir(exist_ok=True)
        if not original.exists():shutil.copy2(recover(c['reference_source'],ROOT/'artifacts/cache/s5-b-010'),original)
        validate_field(original,c['reference_source']);refseed={'id':'q2-reference','q':2};refspec={'id':'reference','nodes':127,'length':20.16}
        ref=prepare(out,'q2-reference',refseed,refspec,'retained-reference',None,d,c,save,check_stop,optimize=False)
        ctrl=motion(out,'q2-reference-dt0.01',ref,.01,.2,d,c,save,check_stop)
        if not ctrl or ctrl['status']!='screen_pass':d['status']='complete_reference_blocked';d['skips']['candidate-survey']={'recorded_at':timestamp(),'reason':'Q2 short control unqualified'};save();compact_evidence(out);return d
        d['phase']='all-seed-coarse-survey';save()
        for seed in c['seeds']:
            check_stop();r=prepare(out,seed['id']+'-coarse-fresh',seed,c['levels'][0],'fresh',None,d,c,save,check_stop)
            motion(out,r['id']+'-screen-dt0.01',r,.01,.2,d,c,save,check_stop)
        # Assess all six inexpensive starts before any conditional detailed matrix.
        d['phase']='select-and-refine';save()
        for q in [3,4,7]:
            check_stop();seeds=[s for s in c['seeds'] if s['q']==q];pool=[d['rest'][s['id']+'-coarse-fresh'] for s in seeds]
            if not any(r['status']=='stationary' for r in pool):
                pool=[]
                for seed in seeds:
                    check_stop();r=prepare(out,seed['id']+'-medium-fresh',seed,c['levels'][1],'fresh',None,d,c,save,check_stop);pool.append(r);motion(out,r['id']+'-screen-dt0.01',r,.01,.2,d,c,save,check_stop)
            chosen=select(pool,d['cases'])
            if chosen is None:d['selected'][f'q{q}']={'recorded_at':timestamp(),'status':'preparation_unresolved','reason':'Neither coarse nor declared medium fresh-start retry qualified; no trajectory or further automatic mesh increase'};save();continue
            seed=next(s for s in seeds if s['id']==chosen['seed_id']);selection=d['selected'].setdefault(f'q{q}',{'recorded_at':timestamp(),'status':'selected','seed_id':seed['id'],'survey_parent':chosen['id'],'criterion':'Boundary-admitted stationary pool preferred, then lowest same-mesh D4 energy; seed ID breaks ties. Motion failure does not conceal spatial-refinement diagnostics.','levels':{}});need(selection['seed_id']==seed['id'],'Selection changed on resume')
            previous=None
            for spec in c['levels']:
                check_stop();fresh=prepare(out,seed['id']+'-'+spec['id']+'-fresh',seed,spec,'fresh',None,d,c,save,check_stop);arms=[fresh]
                if previous:
                    warm=prepare(out,seed['id']+'-'+spec['id']+'-warm',seed,spec,'cubic-warm-start',previous,d,c,save,check_stop);arms.append(warm)
                valid=[r for r in arms if r['status']=='stationary']
                if not valid:selection['levels'][spec['id']]={'status':'preparation_unresolved','rest_ids':[r['id'] for r in arms]};save();continue
                primary=min(valid,key=lambda r:(r['final']['stationarity']['energy'],r['id']));selection['levels'][spec['id']]={'status':'stationary','primary_rest':primary['id'],'rest_ids':[r['id'] for r in arms],'route':primary['lineage']['route']};previous=primary;save();core_diagnostics(out,primary,c,save)
                if len(valid)==2:
                    a,ag=rest_state(out,valid[0]);b,bg=rest_state(out,valid[1]);need(ag==bg,'Fresh/warm comparison geometry differs')
                    d['comparisons'][f'q{q}-{spec["id"]}-fresh-warm']={'recorded_at':timestamp(),'status':'measured','kind':'same-grid-fresh-warm-rest','rest_ids':[r['id'] for r in valid],'field_relative_l2':float(np.linalg.norm(a-b)/max(np.linalg.norm(b-NORTH),1e-30)),'energy_relative_difference':abs(valid[0]['final']['stationarity']['energy']-valid[1]['final']['stationarity']['energy'])/abs(valid[1]['final']['stationarity']['energy']),'scope':'Raw full-grid comparison, no registration or claim of identical basins from equal Q/energy.'};save()
                motion(out,primary['id']+'-rest-dt0.01',primary,.01,.2,d,c,save,check_stop,beta=0.)
                motion(out,primary['id']+'-z-dt0.01',primary,.01,.5,d,c,save,check_stop)
            fine_info=selection['levels'].get('fine',{});fine=d['rest'].get(fine_info.get('primary_rest'))
            if fine:
                d['phase']=f'q{q}-temporal-axis-domain';save()
                for dt in [.02,.005]:motion(out,fine['id']+f'-z-dt{dt:g}',fine,dt,.5,d,c,save,check_stop)
                rows=[d['cases'].get(fine['id']+f'-z-dt{dt:g}') for dt in c['time_steps']];d['comparisons'][f'q{q}-temporal']=temporal_comparison(out,rows,c);save()
                motion(out,fine['id']+'-x-dt0.01',fine,.01,.2,d,c,save,check_stop,axis=0)
                domain=prepare(out,seed['id']+'-domain-warm',seed,c['domain'],'same-spacing-extension',fine,d,c,save,check_stop)
                dm=motion(out,domain['id']+'-z-dt0.01',domain,.01,.5,d,c,save,check_stop)
                d['comparisons'][f'q{q}-domain']=comparison(out,d['cases'].get(fine['id']+'-z-dt0.01'),dm,c,f'q{q}','matched-spacing-domain');save()
            else:d['skips'][f'q{q}-fine-temporal-axis-domain']={'recorded_at':timestamp(),'reason':'No strictly stationary fine-grid parent; no finer moving calculation or domain extension queued'};save()
            levels=[selection['levels'].get(s['id'],{}).get('primary_rest') for s in c['levels']]
            for i,j in [(0,1),(1,2),(0,2)]:
                left=d['cases'].get(levels[i]+'-z-dt0.01') if levels[i] else None;right=d['cases'].get(levels[j]+'-z-dt0.01') if levels[j] else None;d['comparisons'][f'q{q}-mesh-{i}-{j}']=comparison(out,left,right,c,f'q{q}','fixed-box-physical-mesh')
            save()
        d.update(status='complete_pending_review',phase='complete');atomic_json(out/'comparisons.json',{'recorded_at':timestamp(),'rows':d['comparisons']});atomic_json(out/'followup.json',{'recorded_at':timestamp(),'parent_run':out.name,'selected':d['selected'],'q1':'parked','q2':'Physical-mesh/domain work remains open; this control is short.','scope':'Review seed/basin, strict preparation, original motion gates and mesh/domain/time comparisons separately. Any unfulfilled matrix cells remain skips, not acceptance.'})
    except KeyboardInterrupt:d.update(status='stopped_checkpoint_retained')
    except Exception as e:d.update(status='error',error=str(e));save();compact_evidence(out);raise
    save();compact_evidence(out);return d

def main():
    global STOP
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,default=CONFIG);a=p.parse_args();start=time.monotonic();done=threading.Event();a.output.mkdir(parents=True,exist_ok=True)
    def stop(*_):
        global STOP
        STOP=True;raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    def heartbeat():
        while not done.wait(30):atomic_json(a.output/'heartbeat.json',{'recorded_at':timestamp(),'wall_seconds':time.monotonic()-start})
    threading.Thread(target=heartbeat,daemon=True).start()
    try:r=campaign(a.output,load(a.config));code=0 if r['status'].startswith('complete') else 2
    except Exception as e:atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':'error','error':str(e),'wall_seconds':time.monotonic()-start,'exit_code':1});raise
    finally:done.set()
    atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':r['status'],'wall_seconds':time.monotonic()-start,'exit_code':code});event('SUMMARY',status=r['status'],output=str(a.output));return code
if __name__=='__main__':sys.exit(main())
