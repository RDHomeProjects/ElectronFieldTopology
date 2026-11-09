"""Fresh-map, original-gate, exact continuation and failure-preservation controls.

Small controller fixtures with artificial gate stubs test orchestration only;
they are not Q3/Q4/Q7 production preparation or motion results.
"""
import copy,json
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology import sf_candidate_seeds as seeds,sf_candidate_survey as s,sf_candidate_motion as m,sf_candidate_local as local
from electron_field_topology.sf_time import Grid,step
from electron_field_topology.sf_time_run import state_sha
from electron_field_topology.skyrme import NORTH,diagnostics,rational_field
from electron_field_topology.knot_diagram import invariant_gate

def plan():return json.loads(s.CONFIG.read_text())

def test_native_contract_and_old_gates_are_preserved():
    c=plan();s.validate(c);assert [x['q'] for x in c['seeds']]==[3,3,4,4,7,7]
    assert c['maximum_preparation_calls']*c['readmission']['iterations_per_pass']==1200
    assert c['domain']['length']/(c['domain']['nodes']-1)==c['levels'][-1]['length']/(c['levels'][-1]['nodes']-1)==.16

def test_display_profile_is_valid_for_the_existing_offline_renderer():
    from electron_field_topology.sf_preview import export_settings
    from electron_field_topology.sf_renderer import presentation_settings
    profile=json.loads(local.PROFILE.read_text());assert export_settings(profile)['grid']==[41,41,41] and presentation_settings(profile)['colors']==16

@pytest.mark.parametrize('key,value',[('beta',.1),('maximum_preparation_calls',60),('runtime_tail_reserve',.01),('time_steps',[.02,.01]),('speed_stop_from_time',.5)])
def test_frozen_study_drift_rejected(key,value):
    c=plan();c[key]=value
    with pytest.raises(ValueError):s.validate(c)

def test_no_weakened_motion_or_stationary_criteria():
    for which in ['limits','readmission']:
        c=plan();c[which][next(iter(c[which]))]*=2
        with pytest.raises(ValueError):s.validate(c)

def test_seed_degree_and_vacuum_unit_constraints():
    points=np.array([[0.,0.,0.],[1.25,-.7,.3],[30.,30.,30.]])
    for seed in seeds.candidates():
        n=seeds.field(points,seed);assert np.allclose(np.linalg.norm(n,axis=-1),1,atol=3e-16) and np.array_equal(n[-1],NORTH)
        assert seeds.degree(seed)==seed['q']
        bad={**seed,'q':seed['q']+1}
        with pytest.raises(ValueError):seeds.field(points,bad)

def test_axial_map_matches_existing_independent_implementation_without_shear_rotation():
    seed={**seeds.candidates()[0],'bend':0.,'perturbation':0.};points=np.random.default_rng(35).normal(size=(53,3))*2
    old=rational_field(points,'axial',seed['alpha'],seed['beta'],seed['scale'],seed['cutoff'],seed['amplitude'])
    assert np.max(abs(seeds.field(points,seed)-old))<5e-16

def test_trefoil_homogeneous_formula_direct_scalar_control():
    seed={**seeds.candidates()[-1],'bend':0.,'perturbation':0.};point=np.array([1.2,-.7,.5]);r=np.linalg.norm(point);f=2*np.arctan(seed['scale']/r);z1=(point[0]+1j*point[1])*np.sin(f)/r;z0=np.cos(f)+1j*point[2]*np.sin(f)/r
    w=seed['amplitude']*z1**2*z0/(z1**3+z0**2);expect=np.array([2*w.real,2*w.imag,1-abs(w)**2])/(1+abs(w)**2)
    assert np.max(abs(seeds.field(point,seed)-expect))<8e-16

def test_independent_integer_degree_is_approached_under_mesh_refinement():
    seed=dict(id='degree-control',q=1,family='axial',alpha=1,beta=1,scale=1.6,cutoff=6.4,bend=0.,amplitude=1.,perturbation=0.)
    errors=[]
    for count in [25,33,49]:
        g=Grid((count,)*3,(16.,)*3,'fixed');n=seeds.sampled(g,seed);errors.append(abs(diagnostics(n,g.spacing[0])['hopf_integral']+1))
    assert errors[2]<errors[1]<errors[0] and errors[-1]<.05

def test_finite_polygon_controls_distinguish_unknot_and_trefoil_without_unique_claim():
    t=np.linspace(.013,2*np.pi+.013,129);circle=np.array([np.cos(t),np.sin(t),.1*np.sin(2*t)]).T;trefoil=np.array([(2+np.cos(3*t))*np.cos(2*t),(2+np.cos(3*t))*np.sin(2*t),np.sin(3*t)]).T
    a=invariant_gate(circle);b=invariant_gate(trefoil);assert a['agreed'] and a['determinant']==1 and b['agreed'] and b['determinant']==3
    assert b['knot_type']=='not_identified'

def gates(**updates):
    checks={k:True for k in ['energy','momentum','constraints','shape','speed','topology','tail']};checks.update(updates);return {'legacy_motion':{'checks':checks},'tail_pass_all_observations':True}

def test_short_speed_failure_is_retained_not_silently_passed():
    c=plan();a=m.decision(gates(speed=False),.1,.3,c);b=m.decision(gates(speed=False),.2,.3,c)
    assert a['failed_original_checks']==['speed'] and not a['stop'] and b['stop']
    assert m.decision(gates(speed=False),.1,0.,c)['stop']

@pytest.mark.parametrize('name',['energy','momentum','constraints','shape','topology','tail'])
def test_other_failures_stop_at_first_observation(name):assert m.decision(gates(**{name:False}),.1,.3,plan())['stop']

def fixture(tmp_path):
    g=Grid((9,)*3,(8.,)*3,'fixed');theta=np.exp(-np.sum(g.points()**2,axis=-1))*1e-3;n=np.stack([np.sin(theta),np.zeros(g.shape),np.cos(theta)],axis=-1);n[g.fixed_mask()]=NORTH
    folder=tmp_path/'rest/toy';folder.mkdir(parents=True);np.savez_compressed(folder/'latest.npz',field=n,field_rate=np.zeros_like(n))
    row={'id':'toy','seed_id':'toy','q':1,'nodes':9,'length':8.,'checkpoint':'rest/toy/latest.npz','checkpoint_sha256':s.sha(folder/'latest.npz'),'status':'stationary'}
    d={'cases':{},'config_sha256':'a'*64,'source_sha256':{'fixture':'b'*64}};c=plan();c.update(shell_width=.25,expanded_guard_width=.5,snapshot_time=.01)
    return row,d,c,n,g

def test_segmented_worker_equals_direct_unchanged_rk4_and_idempotent(tmp_path,monkeypatch):
    row,d,c,n,g=fixture(tmp_path);monkeypatch.setattr(m,'decision',lambda *a:{'stop':False,'stop_checks':[],'failed_original_checks':[]})
    result=m.trajectory(tmp_path,'toy-motion',row,0.,2,.01,.02,[.01,.02],.01,d,c,lambda:None,lambda:None)
    n,v=m.at(tmp_path,result,0.)
    for i in range(2):n,v,_=step(n,v,g,.01,i*.01)
    assert result['final_state_sha256']==state_sha(n,v) and len(result['attempts'])==2
    assert m.trajectory(tmp_path,'toy-motion',row,0.,2,.01,.02,[.01,.02],.01,d,c,lambda:None,lambda:None)==result
    assert result['status']=='screen_failed' # no artificial scientific success from the decision stub

def test_recover_after_last_milestone_keeps_latest_not_initial(tmp_path,monkeypatch):
    row,d,c,_,_=fixture(tmp_path);monkeypatch.setattr(m,'decision',lambda *a:{'stop':False,'stop_checks':[],'failed_original_checks':[]})
    r=m.trajectory(tmp_path,'toy-motion',row,0.,2,.01,.02,[.01,.02],.01,d,c,lambda:None,lambda:None);expected=r['final_state_sha256'];r['status']='working'
    again=m.trajectory(tmp_path,'toy-motion',row,0.,2,.01,.02,[.01,.02],.01,d,c,lambda:None,lambda:None)
    assert again['final_state_sha256']==expected and again['final_time']==.02

def test_modified_completed_checkpoint_rejected(tmp_path,monkeypatch):
    row,d,c,_,_=fixture(tmp_path);monkeypatch.setattr(m,'decision',lambda *a:{'stop':False,'stop_checks':[],'failed_original_checks':[]})
    r=m.trajectory(tmp_path,'toy-motion',row,0.,2,.01,.02,[.01,.02],.01,d,c,lambda:None,lambda:None);(tmp_path/r['final_checkpoint']).write_bytes(b'bad')
    with pytest.raises(ValueError,match='Completed moving state'):m.trajectory(tmp_path,'toy-motion',row,0.,2,.01,.02,[.01,.02],.01,d,c,lambda:None,lambda:None)

def test_reference_or_boost_admission_failure_never_evolves(tmp_path,monkeypatch):
    row,d,c,n,g=fixture(tmp_path)
    monkeypatch.setattr(m,'admission',lambda *a:(n,np.zeros_like(n),g,{'passed':False}))
    monkeypatch.setattr(m,'evolve',lambda *a,**k:pytest.fail('Unqualified input was evolved'))
    r=m.trajectory(tmp_path,'rejected',row,.3,2,.01,.2,[.1,.2],.01,d,c,lambda:None,lambda:None)
    assert r['status']=='admission_rejected' and not r['attempts']

def test_unqualified_stationary_field_records_skip(tmp_path):
    d={'skips':{}};row={'id':'bad','status':'preparation_unresolved'}
    assert s.motion(tmp_path,'bad-motion',row,.01,.2,d,plan(),lambda:None,lambda:None) is None and d['skips']['bad-motion']['parent_rest_id']=='bad'

def test_selection_preserves_failed_motion_and_prefers_boundary_admitted_pool():
    def r(id,energy,status='stationary'):return {'id':id,'seed_id':id,'status':status,'final':{'stationarity':{'energy':energy}}}
    a,b,unresolved=r('a',2.),r('b',3.),r('c',1.,'preparation_unresolved')
    cases={'b-screen-dt0.01':{'status':'screen_failed','admission':{'passed':True}}}
    assert s.select([a,b,unresolved],cases)['id']=='b' and s.select([unresolved],{}) is None

def test_missing_temporal_endpoint_is_incomplete_not_pass(tmp_path):assert m.temporal_comparison(tmp_path,[None,None,None],plan())['status']=='incomplete'

def test_unknown_pid_identity_never_authorizes_kill(monkeypatch):
    monkeypatch.setattr(local,'process_identity',lambda pid:'different');assert not local.alive({'pid':7,'process_identity':'old'}) and not local.alive({'pid':7,'process_identity':None})

def test_already_running_launch_is_guarded_by_process_identity(monkeypatch):
    monkeypatch.setattr(local,'process_identity',lambda pid:'boot:namespace:start');assert local.alive({'pid':7,'process_identity':'boot:namespace:start'})

def preparation_fixture(tmp_path,monkeypatch):
    row,_,c,n,g=fixture(tmp_path);d={'rest':{},'config_sha256':'a'*64};c['maximum_preparation_calls']=2
    metric={'energy':1.,'relative_force_l2':.01,'acceleration_max':.02,'hopf_integral':-1.,'minimum_corner_cone':.9,'unit_error':0.}
    monkeypatch.setattr(s,'sampled',lambda *a:n.copy());monkeypatch.setattr(s,'stationarity',lambda *a:dict(metric));monkeypatch.setattr(s,'metrics',lambda n,g,c:{'recorded_at':s.timestamp(),'stationarity':dict(metric),'tail':{'fraction':0.},'state_sha256':state_sha(n,np.zeros_like(n))})
    return d,c,{'id':'toy','q':1},{'id':'toy','nodes':9,'length':8.},metric

def test_interrupted_batch_consumes_allocation_without_forged_native_pass(tmp_path,monkeypatch):
    d,c,seed,grid,_=preparation_fixture(tmp_path,monkeypatch);calls=[]
    def interrupted(*args,**kw):calls.append(True);return {'status':'interrupted','reason':'test interruption','iterations':0,'passes':0}
    monkeypatch.setattr(s,'relax',interrupted)
    with pytest.raises(KeyboardInterrupt):s.prepare(tmp_path,'new-rest',seed,grid,'fresh',None,d,c,lambda:None,lambda:None)
    row=d['rest']['new-rest'];assert row['calls_allocated']==1 and row['native_result']['passes']==0
    monkeypatch.setattr(s,'relax',lambda *a,**k:{'status':'checkpointed','reason':None,'iterations':0,'passes':0})
    result=s.prepare(tmp_path,'new-rest',seed,grid,'fresh',None,d,c,lambda:None,lambda:None)
    assert result['calls_allocated']==2 and result['status']=='preparation_unresolved' and result['native_result']['passes']==0

def test_native_optimizer_stall_is_retained_and_not_retried_away(tmp_path,monkeypatch):
    d,c,seed,grid,_=preparation_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(s,'relax',lambda *a,**k:{'status':'stationarity_unresolved','reason':'Armijo search stalled','iterations':0,'passes':1})
    row=s.prepare(tmp_path,'new-rest',seed,grid,'fresh',None,d,c,lambda:None,lambda:None)
    assert row['status']=='stationarity_unresolved' and row['reason']=='Armijo search stalled' and row['calls_allocated']==1

def test_bad_representation_never_enters_optimizer(tmp_path,monkeypatch):
    d,c,seed,grid,metric=preparation_fixture(tmp_path,monkeypatch);metric['hopf_integral']=-.8
    monkeypatch.setattr(s,'relax',lambda *a,**k:pytest.fail('Unresolved representation was optimized'))
    row=s.prepare(tmp_path,'new-rest',seed,grid,'fresh',None,d,c,lambda:None,lambda:None)
    assert row['status']=='representation_unresolved' and row['calls_allocated']==0

def test_unsealed_optimizer_checkpoint_is_explicitly_labelled_on_recovery(tmp_path,monkeypatch):
    d,c,seed,grid,_=preparation_fixture(tmp_path,monkeypatch);monkeypatch.setattr(s,'relax',lambda *a,**k:{'status':'interrupted','iterations':0,'passes':0})
    with pytest.raises(KeyboardInterrupt):s.prepare(tmp_path,'new-rest',seed,grid,'fresh',None,d,c,lambda:None,lambda:None)
    row=d['rest']['new-rest'];folder=tmp_path/'rest/new-rest';n,g=s.checked_field(folder,row['config']);manifest=json.loads((folder/'manifest.json').read_text());s.checkpoint(folder/'latest.npz',n,g,1,s.canonical_sha(row['config']),0,0,manifest['code_sha256'])
    monkeypatch.setattr(s,'relax',lambda *a,**k:{'status':'checkpointed','iterations':0,'passes':0})
    row=s.prepare(tmp_path,'new-rest',seed,grid,'fresh',None,d,c,lambda:None,lambda:None)
    assert row['recovery'][-1]['kind']=='unsealed-atomic-optimizer-checkpoint' and row['calls_allocated']==2

def test_polygon_crossing_budget_is_retained_as_unresolved(monkeypatch):
    monkeypatch.setattr(s,'crossings',lambda *a,**kw:[{}]*41);row=s.polygon_summary(np.zeros((129,3)),plan());assert not row['agreed'] and row['determinant'] is None and all(v['status']=='projection_budget' for v in row['projections'])

def test_small_disk_space_never_launches_worker(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(local.shutil,'disk_usage',lambda *a:SimpleNamespace(free=0));monkeypatch.setattr(local.subprocess,'Popen',lambda *a,**kw:pytest.fail('Worker launched without disk reserve'))
    with pytest.raises(ValueError,match='headroom'):local.launch(s.CONFIG)

def test_record_id_mapping_reads_restored_paths_without_rewriting_native_json(tmp_path):
    out=tmp_path/'restore'/'20261109t010203z-aabbccdd';out.mkdir(parents=True);p=out/'cases/case/attempt-000';p.mkdir(parents=True)
    old='/home/other/work/artifacts/20261109t010203z-aabbccdd/cases/case/attempt-000'
    assert m.local_path(out,old)==p
    with pytest.raises(ValueError):m.local_path(out,'/home/unknown/no-record/cases/state.npz')
    with pytest.raises(ValueError):m.local_path(out,'../escape')

def test_reached_partial_temporal_windows_are_retained_without_full_acceptance(monkeypatch,tmp_path):
    rows=[{'id':str(i),'initial_state_sha256':'same','final_time':.2} for i in range(3)]
    n=np.broadcast_to(NORTH,(3,)*3+(3,)).copy();v=np.ones_like(n)*.01
    monkeypatch.setattr(m,'at',lambda out,row,t:(n+int(row['id'])*1e-5,v+int(row['id'])*1e-5))
    data=m.temporal_comparison(tmp_path,rows,plan());assert data['status']=='partial_matched_windows' and not data['full_window_completed'] and [r['time'] for r in data['matched_windows']]==[.1,.2]

@pytest.mark.parametrize('reference_ok',[False,True])
def test_phase_controller_surveys_all_seeds_before_detail_and_refines_only_one_per_q(tmp_path,monkeypatch,reference_ok):
    c=plan();events=[];monkeypatch.setattr(s,'validate',lambda x:x);monkeypatch.setattr(s.subprocess,'check_output',lambda args,**k:('' if 'status' in args else '0'*40) if k.get('text') else (b'' if 'status' in args else b'0'*40));monkeypatch.setattr(s,'geodesic_control',lambda:{'passed':True});monkeypatch.setattr(s,'boundary_controls',lambda:{'passed':True})
    source=tmp_path/'reference.npz';source.write_bytes(b'software fixture only');monkeypatch.setattr(s,'recover',lambda *a:source);monkeypatch.setattr(s,'validate_field',lambda *a:None)
    # Controller-only fixtures deliberately omit any numerical qualification claim.
    def prep(out,key,seed,spec,route,parent,d,c,save,check_stop,optimize=True):
        events.append(('prepare',key,seed['id'],spec['id']))
        row=d['rest'].setdefault(key,{'id':key,'seed_id':seed['id'],'q':seed['q'],'nodes':spec['nodes'],'length':spec['length'],'status':'stationary','calls_allocated':0,'lineage':{'route':route},'initial':{},'final':{'stationarity':{'energy':float(seed['q'])}},'checkpoint_sha256':'0'*64})
        return row
    def moving(out,key,r,dt,duration,d,c,save,check_stop,**kw):
        events.append(('motion',key,r['seed_id'],duration));row={'id':key,'rest_id':r['id'],'q':r['q'],'beta':kw.get('beta',.3),'axis':kw.get('axis',2),'dt':dt,'duration':duration,'status':'screen_pass' if r['q']==2 and reference_ok else 'admission_rejected','admission':{'passed':False}}
        d['cases'][key]=row;return row
    n=np.broadcast_to(NORTH,(9,)*3+(3,)).copy();g=Grid((9,)*3,(8.,)*3,'fixed')
    monkeypatch.setattr(s,'prepare',prep);monkeypatch.setattr(s,'motion',moving);monkeypatch.setattr(s,'core_diagnostics',lambda *a:None);monkeypatch.setattr(s,'rest_state',lambda *a:(n,g));monkeypatch.setattr(s,'compact_evidence',lambda *a:None)
    result=s.campaign(tmp_path/'run',c)
    if not reference_ok:
        assert result['status']=='complete_reference_blocked' and len(result['rest'])==1 and not result['selected'];return
    first_detail=next(i for i,e in enumerate(events) if e[0]=='prepare' and e[3]=='medium')
    assert len({e[2] for e in events[:first_detail] if e[0]=='prepare' and e[3]=='coarse'})==6
    assert result['status']=='complete_pending_review' and set(result['selected'])=={'q3','q4','q7'}
    assert len({e[2] for e in events if e[0]=='prepare' and e[3]=='fine'})==3 and len(result['rest'])==22 and len(result['cases'])==37

def test_replay_preserves_failed_boolean_gates_and_rejects_numeric_drift():
    from electron_field_topology.sf_candidate_replay import equal
    assert equal({'x':1.+1e-12,'passed':False},{'x':1.,'passed':False})['numeric']==1
    with pytest.raises(ValueError,match='Gate differs'):equal({'passed':True},{'passed':False})
    with pytest.raises(ValueError,match='Numeric replay'):equal({'x':1.01},{'x':1.})

def test_publication_checker_rejects_synthetic_fixture_marker(tmp_path):
    import importlib.util
    spec=importlib.util.spec_from_file_location('candidate_audit',s.ROOT/'scripts/check_candidate_survey.py');tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    for name,value in [('campaign.json',{'test_fixture':True}),('plan.json',{}),('exit.json',{})]:(tmp_path/name).write_text(json.dumps(value))
    with pytest.raises(ValueError,match='Synthetic software fixtures'):tool.audit(tmp_path,s.ROOT)

def replay_fixture(tmp_path,monkeypatch):
    row,d,c,n,g=fixture(tmp_path);monkeypatch.setattr(m,'decision',lambda *a:{'stop':False,'stop_checks':[],'failed_original_checks':[]})
    m.trajectory(tmp_path,'toy-motion',row,0.,2,.01,.02,[.01,.02],.01,d,c,lambda:None,lambda:None)
    row['initial']=s.metrics(n,g,c);row['final']=s.metrics(n,g,c);(tmp_path/'rest/toy/initial.npz').write_bytes((tmp_path/'rest/toy/latest.npz').read_bytes());d.update(rest={'toy':row},record_id=tmp_path.name,status='complete_pending_review',comparisons={})
    for name,value in [('campaign.json',d),('plan.json',c)]:(tmp_path/name).write_text(json.dumps(value))
    return d,c

def test_full_field_replay_recomputes_real_tiny_rk4_metrics_with_seal_auditor_stub_only(tmp_path,monkeypatch):
    from electron_field_topology import sf_candidate_replay as replay
    out=tmp_path/'run';out.mkdir();d,c=replay_fixture(out,monkeypatch);fake=tmp_path/'fixture-auditor';(fake/'scripts').mkdir(parents=True);(fake/'scripts/check_candidate_survey.py').write_text("def audit(out,repo): return {'scope':'software fixture audit stub; not production'}\n")
    monkeypatch.setattr(replay,'ROOT',fake);dest=tmp_path/'replay';monkeypatch.setattr(replay.sys,'argv',['replay','--run',str(out),'--output',str(dest)]);replay.main();receipt=json.loads((dest/'field-replay.json').read_text());assert receipt['numeric_comparisons']['numeric']>50 and receipt['cases'][0]['native_status']=='screen_failed'

def test_offline_preview_writes_paraview_series_without_modifying_full_states(tmp_path,monkeypatch):
    out=tmp_path/'run';out.mkdir();d,c=replay_fixture(out,monkeypatch);before={str(p):s.sha(p) for p in out.rglob('*.npz')};profile=tmp_path/'profile.json';profile.write_text(json.dumps({'export':{'enabled':True,'every_steps':1,'grid':[5,5,5],'fields':['field','energy_density','energy_flux'],'vtk':True}}));monkeypatch.setattr(local,'ART',tmp_path/'preview-work');local.preview(out,'toy-motion',profile)
    assert before=={str(p):s.sha(p) for p in out.rglob('*.npz')};pvd=list((tmp_path/'preview-work').rglob('series.pvd'));assert len(pvd)==1
    manifest=json.loads(pvd[0].with_name('manifest.json').read_text());assert len(manifest['frames'])==3 and manifest['display_grid']==[5,5,5]
