"""Small numerical equivalence, audit, reserve and workflow controls; no native study."""
import copy,json,hashlib
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology import sf_temporal as c,sf_temporal_run as r
from electron_field_topology.sf_time_run import run as original_run,state_sha
from electron_field_topology.sf_temporal_metrics import endpoint_audit,geodesic_control,observed_order,centred_cube
from electron_field_topology.sf_tail_domain import seed_continuation
from electron_field_topology.sf_time import Grid
from electron_field_topology.skyrme import NORTH,rational_field


def physical(dt=.01):return {'case_id':'manufactured-unadmitted-probe','grid':[17]*3,'lengths':[8.]*3,'boundary':'fixed','dt':dt,'steps':round(.04/dt),'diagnostic_every':1,'checkpoint_every':2,'initial':{'kind':'rational','q':1,'scale':1.1,'cutoff':2.5}}
def monitor(enabled=True):return {'enabled':enabled,'shell_width':.5,'warning_fraction':.0009,'tail_fraction_limit':.001,'snapshot_every_time':.02}

def test_native_contract_retains_speed_original_gates_and_ordered_ladders():
    cfg=json.loads(c.CONFIG.read_text());c.validate(cfg)
    for name,value in [('beta',.1),('runtime_tail_reserve',.002),('time_steps',[.01,.005])]:
        bad=copy.deepcopy(cfg);bad[name]=value
        with pytest.raises(ValueError):c.validate(bad)


def test_audit_separates_good_irregular_endpoint_from_unmet_native_certificate():
    p=json.loads(c.CONFIG.read_text())['readmission'];p.update(relative_force_l2=1e-9,acceleration_max=1e-8)
    w={'stable_intervals':3,'observe_every':100,'tail_fraction_change':1e-7,'shell_energy_change':1e-7,'core_field_relative_change':1e-5,'hamiltonian_relative_change':1e-9}
    m={'relative_force_l2':1e-14,'acceleration_max':1e-13,'hopf_integral':-.997,'minimum_corner_cone':.93,'unit_error':1e-16}
    rows=[{'iteration':k,'regular_observation':True,'tail_fraction_change':0.,'shell_energy_change':0.,'core_field_relative_change':0.,'hamiltonian_relative_change':0.} for k in [100,200,300,400]]
    rows.append({'iteration':484,'regular_observation':False})
    a=endpoint_audit(m,rows,p,w,'stationarity_unresolved','Armijo search stalled')
    assert a['strict_endpoint_stationarity_pass'] and a['preceding_regular_window_stable'] and not a['historical_regular_certificate_pass']
    assert a['native_status_preserved']=='stationarity_unresolved' and rows[-1]['iteration']==484


def test_analytic_temporal_control_has_fourth_order():
    a=geodesic_control();assert a['passed'] and min(a['orders'])>3.9


def test_observer_and_snapshots_do_not_change_rk4_endpoint(tmp_path):
    cfg=physical();old=original_run(cfg,tmp_path/'old');on=r.run(cfg,tmp_path/'on',monitor=monitor());off=r.run(cfg,tmp_path/'off',monitor=monitor(False))
    assert old['state_sha256']==on['state_sha256']==off['state_sha256']
    assert [x['time'] for x in on['retained_snapshots']]==[.02,.04]
    assert all(x['original_tail_pass'] for x in json.loads((tmp_path/'on/history.json').read_text()))


def test_warning_stops_before_original_limit_and_retains_complete_state(tmp_path,monkeypatch):
    calls=0
    def observer(*args):
        nonlocal calls
        calls+=1;v=0. if calls==1 else .00095
        return {'fraction':v,'energy':v,'total_continuum_energy':1.,'width':.5}
    monkeypatch.setattr(r,'tail_band',observer)
    out=tmp_path/'warning';result=r.run(physical(),out,monitor=monitor())
    assert result['status']=='boundary_reserve_stop' and result['step']==1
    rows=json.loads((out/'history.json').read_text());assert rows[-1]['original_tail_pass'] and not rows[-1]['tail_warning_clear']
    with np.load(out/'latest.npz',allow_pickle=False) as d:assert int(d['step'])==1 and np.isfinite(d['field']).all()
    assert (out/'final.npz').exists()


def test_original_tail_failure_is_retained_if_a_sample_crosses_it(tmp_path,monkeypatch):
    calls=[]
    def observer(*args):
        calls.append(True);v=0. if len(calls)==1 else .0012;return {'fraction':v,'energy':v,'total_continuum_energy':1.,'width':.5}
    monkeypatch.setattr(r,'tail_band',observer);out=tmp_path/'failed';v=r.run(physical(),out,monitor=monitor())
    assert v['status']=='boundary_reserve_stop' and not json.loads((out/'history.json').read_text())[-1]['original_tail_pass']


def test_checkpoint_resume_matches_uninterrupted_observed_driver(tmp_path):
    cfg=physical();a=r.run(cfg,tmp_path/'a',stop_after=2,monitor=monitor());assert a['status']=='checkpointed'
    b=r.run(cfg,tmp_path/'b',resume=tmp_path/'a/latest.npz',monitor=monitor());direct=r.run(cfg,tmp_path/'all',monitor=monitor())
    assert b['state_sha256']==direct['state_sha256']


def test_common_cube_uses_odd_physical_centre_and_roundoff_order_is_unresolved():
    a=np.zeros((19,17,17,3));a[9,8,8]=1.;assert np.all(centred_cube(a,9)[4,4,4]==1)
    assert observed_order(1e-15,0.)['order'] is None and observed_order(16e-6,1e-6)['order']==4.


@pytest.fixture(scope='session')
def boundary_control():
    a=c.boundary_controls();assert a['passed'];return a


@pytest.fixture
def workflow(tmp_path,monkeypatch,boundary_control):
    cfg=json.loads(c.CONFIG.read_text());cfg.update(duration=.04,time_steps=[.01,.005,.0025],diagnostic_time=.01,checkpoint_time=.02,comparison_times=[.02,.04],spacing=.5,shell_width=.5,common_nodes=9,fixed_comoving_half_width=1.)
    cfg['models']=[{'id':'q1-x','q':1,'axis':0,'source':'q1','domains':[{'nodes':17,'length':8.},{'nodes':19,'length':9.}]},{'id':'q2-z','q':2,'axis':2,'source':'q2','domains':[{'nodes':17,'length':8.}]}]
    src=tmp_path/'source';src.mkdir();files={}
    for key in ['q1','q2']:
        f=src/(key+'.bin');f.write_bytes(b'Manufactured fixture input; no native checkpoint');files[key]={'path':str(f),'sha256':c.sha(f)}
    source=src/'map.json';source.write_text('{}');inv={'recorded_at':c.timestamp(),'files':files,'input_fingerprint':c.canonical_sha(files)}
    monkeypatch.setattr(c,'validate',lambda _:None);monkeypatch.setattr(c,'source_inventory',lambda *_:(copy.deepcopy(inv),{}));monkeypatch.setattr(c,'boundary_controls',lambda:copy.deepcopy(boundary_control))
    original=c.subprocess.check_output
    def gitread(argv,**kwargs):
        if argv[:2]==['git','status']:return ''
        if argv[:2]==['git','rev-parse']:return '4e4ff50657fa312a4e764a0ec53a42e422a183da\n'
        return original(argv,**kwargs)
    monkeypatch.setattr(c.subprocess,'check_output',gitread)
    def preparation(out,model,domain,row,config,inventory,save):
        folder=out/'rest'/row['id'];g=Grid((domain['nodes'],)*3,(domain['length'],)*3,'fixed')
        n=rational_field(g.points(),alpha=model['q'],beta=1,scale=1.1,cutoff=2.5);n[g.fixed_mask()]=NORTH
        seed_continuation(folder,n,g,model['q'],row['relax_config']);row.update(status='admitted',rest_checkpoint_sha256=c.sha(folder/'latest.npz'),fixture_only='Preparation authorization mocked for unadmitted small-field numerical probes; all measured scientific gates retained');save();return row
    monkeypatch.setattr(c,'prepare_domain',preparation)
    return source,cfg,inv


def test_complete_workflow_has_identical_initial_states_three_dt_and_all_hashes(workflow,tmp_path):
    source,cfg,inv=workflow;before={k:c.sha(Path(v['path'])) for k,v in inv['files'].items()};out=tmp_path/'run';d=c.campaign(source,out,cfg)
    assert d['status']=='complete_pending_review' and len(d['cases'])==6 and len(d['selected_domains'])==2
    for selected in d['selected_domains'].values():assert len({d['cases'][f'{selected}-dt{dt:g}']['initial_state_sha256'] for dt in cfg['time_steps']})==1
    assert len(json.loads((out/'temporal-comparisons.json').read_text())['rows'])==4
    assert any(not r['assessment']['legacy_motion']['bounded_case_gates_pass'] for r in d['cases'].values())
    import zipfile
    with zipfile.ZipFile(out/'evidence.zip') as z:
        hashes=json.loads(z.read('evidence-hashes.json'))['sha256'];assert z.testzip() is None and set(z.namelist())==set(hashes)|{'evidence-hashes.json'}
        for name,h in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==h
    assert before=={k:c.sha(Path(v['path'])) for k,v in inv['files'].items()}


def test_warning_restarts_whole_family_on_next_domain_without_mixing_grids(workflow,tmp_path,monkeypatch):
    source,cfg,_=workflow;real=c.run_case
    def warning(*args):
        row=real(*args);model=args[1];domain=args[2]
        if model['id']=='q1-x' and domain['nodes']==17:
            row['status']='boundary_reserve_stop';row['assessment']['boundary_reserve_clear_at_all_recorded_times']=False
        return row
    monkeypatch.setattr(c,'run_case',warning);d=c.campaign(source,tmp_path/'fallback',cfg)
    assert d['selected_domains']['q1-x'].endswith('n19-L9')
    assert d['domains']['q1-x-n17-L8']['family_status']=='rejected'
    assert len([r for r in d['cases'].values() if r['domain_id']=='q1-x-n19-L9'])==3


def test_blocked_admission_never_starts_a_trajectory(workflow,tmp_path,monkeypatch):
    source,cfg,_=workflow
    def reject(out,model,domain,row,*args):row.update(status='admission_rejected',reason='Manufactured blocked admission control');return row
    monkeypatch.setattr(c,'prepare_domain',reject)
    monkeypatch.setattr(c,'run_case',lambda *_:pytest.fail('Blocked candidate evolved'))
    d=c.campaign(source,tmp_path/'blocked',cfg)
    assert d['status']=='complete_admission_blocked_pending_review' and not d['cases'] and not d['selected_domains']


def test_workflow_stop_resume_is_bit_exact(workflow,tmp_path,monkeypatch):
    source,cfg,_=workflow;real=c.evolve;calls=[]
    def paused(physical,output,profile,resume,monitor):
        if not calls:
            calls.append(True);value=real(physical,output,profile,resume=resume,stop_after=1,monitor=monitor);c.STOP=True;return value
        return real(physical,output,profile,resume=resume,monitor=monitor)
    monkeypatch.setattr(c,'evolve',paused);out=tmp_path/'resumed';a=c.campaign(source,out,cfg);assert a['status']=='stopped_checkpoint_retained'
    resumed=c.campaign(source,out,cfg);direct=c.campaign(source,tmp_path/'direct',cfg)
    assert {k:v['final_state_sha256'] for k,v in resumed['cases'].items()}=={k:v['final_state_sha256'] for k,v in direct['cases'].items()}


def test_changed_config_and_completed_campaign_are_rejected(workflow,tmp_path):
    source,cfg,_=workflow;out=tmp_path/'run';c.campaign(source,out,cfg)
    with pytest.raises(ValueError,match='immutable'):c.campaign(source,out,cfg)
    bad=copy.deepcopy(cfg);bad['duration']=.03
    with pytest.raises(ValueError,match='changed'):c.campaign(source,out,bad)


@pytest.mark.parametrize("allow_projection",[False,True])
def test_native_preparation_bridge_records_real_measurements_and_keeps_rejected_rest(tmp_path,monkeypatch,allow_projection):
    # Exercise the actual seed/checkpoint/measurement integration, without authorizing a coarse test field.
    config=json.loads(c.CONFIG.read_text());config.update(common_nodes=9,profile_half_widths=[1.,2.,3.],shell_width=.5,spacing=.5)
    domain={'nodes':17,'length':8.};model={'id':'q1-x','q':1,'axis':0,'source':'q1'}
    g=Grid((17,)*3,(8.,)*3,'fixed');n=rational_field(g.points(),alpha=1,beta=1,scale=1.1,cutoff=2.5);n[g.fixed_mask()]=NORTH
    monkeypatch.setattr(c,'load_source',lambda *_:n.copy())
    monkeypatch.setattr(c,'relax',lambda *a,**k:{'status':'stationarity_unresolved','reason':'No optimization requested in bridge control'})
    # Gate is deliberately rejected: this is an instrument control, not an admitted candidate.
    monkeypatch.setattr(c,'admitted',lambda *_:allow_projection)
    row={'id':'coarse-fixture','status':'preparing','relax_config':{**config['readmission'],**domain,'q':1}}
    c.STOP=False;r0=c.prepare_domain(tmp_path,model,domain,row,config,{},lambda:None)
    assert r0['status']=='admission_rejected' and r0['passes_called']==1
    assert r0['rest_final']['recorded_at'] and isinstance(r0['rest_final']['shell_fraction'],float)
    assert r0['initial_checkpoint_sha256']==c.sha(tmp_path/'rest/coarse-fixture/initial.npz')
    assert c.sha(tmp_path/'rest/coarse-fixture/latest.npz')==r0['rest_checkpoint_sha256']

    if allow_projection:assert r0['admission']['projection']['passed'] and r0['admission']['expanded_guard']['fraction']>config['expanded_guard_limit']
