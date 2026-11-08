"""Selective recovery, early-stop orchestration and unchanged-step continuation controls."""
import copy,hashlib,io,json,tarfile
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology import sf_higher_q as h
from electron_field_topology import sf_higher_q_sources as s
from electron_field_topology.sf_time import Grid,step
from electron_field_topology.sf_time_run import state_sha
from electron_field_topology.skyrme import NORTH


def plan():return json.loads(h.CONFIG.read_text())

def test_production_matrix_anchors_and_unchanged_gates():
    c=plan();h.validate(c)
    assert (sum(round(c['duration']/dt) for dt in [c['time_step'],c['confirmation_dt']])*2+round(c['duration']/c['time_step']))==140
    assert c['maximum_readmission_calls']*c['readmission']['iterations_per_pass']==200

@pytest.mark.parametrize('key,value',[('beta',.2),('duration',1.),('runtime_tail_reserve',.002),('speed_stop_from_time',.05)])
def test_matrix_drift_is_rejected(key,value):
    c=plan();c[key]=value
    with pytest.raises(ValueError):h.validate(c)

def test_original_motion_gate_cannot_be_loosened():
    c=plan();c['limits']['speed_relative']=.1
    with pytest.raises(ValueError,match='Original motion criteria'):h.validate(c)

def test_coarse_nodes_keep_coordinates_and_original_values():
    c=plan();a=np.broadcast_to(NORTH,(129,)*3+(3,)).copy();a[64,64,64]=[.6,0,.8]
    n=h.coarse_field(a,c['sources']['q17'],c['coarse_rest'])
    assert n.shape==(97,97,97,3) and np.array_equal(n[16:81,16:81,16:81],a[::2,::2,::2])
    assert np.array_equal(n[48,48,48],a[64,64,64])
    assert np.array_equal(a[64,64,64],[.6,0,.8])
    assert np.max(abs(n[:16]-NORTH))==0

def test_pax_offsets_match_real_archive_even_long_names():
    manifest={'files':[]};stream=io.BytesIO();wanted={}
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as z:
        for i,name in enumerate(['files/a.txt','files/'+'long-directory/'*12+'state.npz','files/last.json']):
            payload=bytes([i])*([513,1400,3][i]);t=tarfile.TarInfo(name);t.size=len(payload);t.mode=0o644;t.mtime=1700000000;z.addfile(t,io.BytesIO(payload));manifest['files'].append({'archive_path':name,'size':len(payload),'mode':t.mode,'mtime_ns':t.mtime*10**9,'sha256':hashlib.sha256(payload).hexdigest()});wanted[name]=payload
    raw=stream.getvalue()
    for name,data in wanted.items():
        offset,row=s.member_position(manifest,name);assert raw[offset:offset+row['size']]==data

def test_selective_recovery_crosses_parts_and_checks_member_hash(tmp_path,monkeypatch):
    raw=b'ABCDE123456789XYZ';spec={'key':'q17','tar_offset':5,'bytes':9,'sha256':hashlib.sha256(b'123456789').hexdigest()};parts=[{'name':'r001-part-00001.tarpart','bytes':9},{'name':'r001-part-00002.tarpart','bytes':8}];reads=[]
    monkeypatch.setattr(s,'authenticate',lambda *a:({'tag':'archive-workstation-test'},None,{'parts':parts}))
    def fetch(url,start,size,total):
        number=0 if '00001.tarpart' in url else 1;chunk=raw[:9] if number==0 else raw[9:];reads.append((number,start,size));return chunk[start:start+size]
    monkeypatch.setattr(s,'fetch_range',fetch);p=s.recover(spec,tmp_path)
    assert p.read_bytes()==b'123456789' and reads==[(0,5,4),(1,0,5)]
    p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='Cached source'):s.recover(spec,tmp_path)

def test_bad_selected_payload_is_never_installed(tmp_path,monkeypatch):
    spec={'key':'q17','tar_offset':0,'bytes':3,'sha256':hashlib.sha256(b'abc').hexdigest()};monkeypatch.setattr(s,'authenticate',lambda *a:({'tag':'tag'},None,{'parts':[{'name':'part','bytes':3}]}));monkeypatch.setattr(s,'fetch_range',lambda *a:b'bad')
    with pytest.raises(ValueError,match='Recovered member SHA'):s.recover(spec,tmp_path)
    assert not list(tmp_path.glob('*.npz')) and not list(tmp_path.glob('*.partial'))

def test_ignored_http_range_is_not_read(monkeypatch):
    class Reply:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):raise AssertionError('Ignored range must not trigger a bulk read')
    monkeypatch.setattr(s.urllib.request,'urlopen',lambda *a,**k:Reply())
    with pytest.raises(NotImplementedError):s.fetch_range('https://example.invalid',1,3,10)

def gates(**updates):
    checks={k:True for k in ['energy','momentum','constraints','shape','speed','topology','tail']};checks.update(updates)
    return {'legacy_motion':{'checks':checks,'bounded_case_gates_pass':all(checks.values())},'tail_pass_all_observations':True,'maximum_observed_tail_fraction':0}

def test_first_speed_flag_is_retained_then_stop_eligible():
    c=plan();a=gates(speed=False);first=h.decide(a,.05,c);next=h.decide(a,.1,c)
    assert first['failed_original_checks']==['speed'] and not first['stop']
    assert next['stop'] and next['stop_checks']==['speed']

@pytest.mark.parametrize('name',['energy','momentum','constraints','shape','topology','tail'])
def test_other_original_failures_stop_at_first_checkpoint(name):
    assert h.decide(gates(**{name:False}),.05,plan())['stop']

def fixture_case(tmp_path):
    out=tmp_path/'run';folder=out/'rest/q17';folder.mkdir(parents=True)
    g=Grid((17,)*3,(16.,)*3,'fixed');p=g.points();theta=.1*np.maximum(1-np.sum(p*p,axis=-1)/4,0)**4;n=np.stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1);np.savez_compressed(folder/'latest.npz',field=n)
    rest={'checkpoint':'rest/q17/latest.npz','checkpoint_sha256':s.sha(folder/'latest.npz'),'nodes':17,'length':16.}
    d={'cases':{},'source_sha256':{'fixture':'driver-isolation-only'},'config_sha256':'fixture'};model={'id':'q17','q':17,'axis':2,'source':'q17'}
    return out,rest,d,model,n,g

def test_segmented_orchestrator_is_bit_exact_to_direct_unchanged_steps(tmp_path,monkeypatch):
    # Acceptance is stubbed only to isolate IO/segmentation, never to report a scientific pass.
    out,rest,d,model,n,g=fixture_case(tmp_path);monkeypatch.setattr(h,'assess',lambda *args:gates());c=plan();r=h.trajectory(out,model,rest,.01,d,c,lambda:None)
    lab=h.lab_grid(g,.3,2);a,v,_=h.readmit(n,g,lab,.3,2,'cubic')
    for i in range(20):a,v,_=step(a,v,lab,.01,i*.01)
    with np.load(out/r['final_checkpoint']) as z:assert state_sha(z['field'],z['field_rate'])==state_sha(a,v)
    assert r['final_time']==.2 and len(r['attempts'])==3 and len(r['milestones'])==3
    assert h.trajectory(out,model,rest,.01,d,c,lambda:None)==r

def test_first_failure_saves_endpoint_and_skips_later_segments(tmp_path,monkeypatch):
    out,rest,d,model,_,_=fixture_case(tmp_path);monkeypatch.setattr(h,'assess',lambda *args:gates(energy=False));r=h.trajectory(out,model,rest,.01,d,plan(),lambda:None)
    assert r['status']=='screen_failed' and r['final_time']==.05 and len(r['attempts'])==1
    assert (out/r['final_checkpoint']).is_file()

def test_temporal_confirmation_does_not_invent_order(tmp_path):
    out=tmp_path;ids=['q17-dt0.01','q17-dt0.005'];d={'cases':{}}
    for i,key in enumerate(ids):
        n=np.broadcast_to(NORTH,(3,3,3,3)).copy();n[1,1,1]=[.1,0,np.sqrt(.99)];v=np.ones_like(n)*.01;p=out/(key+'.npz');np.savez(p,field=n,field_rate=v,time=.2)
        d['cases'][key]={'initial_state_sha256':'same','final_checkpoint':p.name}
    r=h.temporal_compare(out,{'id':'q17'},d,plan());assert r['screen_consistent'] and 'order' not in r
    d['cases'][ids[1]]['initial_state_sha256']='different'
    with pytest.raises(ValueError,match='initial field/rate'):h.temporal_compare(out,{'id':'q17'},d,plan())

def test_followup_preserves_original_source_and_never_starts_fine_work(tmp_path):
    d={'config_sha256':'config','rest':{},'cases':{},'temporal':{}};h.followup(tmp_path,d,plan());f=json.loads((tmp_path/'followup.json').read_text())
    assert not f['automatic_fine_work_started'] and len(f['candidates'])==2
    assert all(x['original129_source_sha256'] for x in f['candidates'])
    assert all(x['disposition']=='review_coarse_failure_or_preparation' for x in f['candidates'])


def test_unsealed_segment_endpoint_can_resume_without_repeating_trajectory(tmp_path,monkeypatch):
    out,rest,d,model,n,g=fixture_case(tmp_path);monkeypatch.setattr(h,'assess',lambda *args:gates());original=h.evolve;called=[]
    def interrupt_after_sealed_array(*args,**kw):
        r=original(*args,**kw);called.append(True);raise KeyboardInterrupt
    monkeypatch.setattr(h,'evolve',interrupt_after_sealed_array)
    with pytest.raises(KeyboardInterrupt):h.trajectory(out,model,rest,.01,d,plan(),lambda:None)
    assert len(called)==1 and d['cases']['q17-dt0.01']['milestones']=={}
    monkeypatch.setattr(h,'evolve',original);r=h.trajectory(out,model,rest,.01,d,plan(),lambda:None)
    lab=h.lab_grid(g,.3,2);a,v,_=h.readmit(n,g,lab,.3,2,'cubic')
    for i in range(20):a,v,_=step(a,v,lab,.01,i*.01)
    with np.load(out/r['final_checkpoint']) as z:assert state_sha(z['field'],z['field_rate'])==state_sha(a,v)
    assert r['final_time']==.2


def test_preparation_allocation_is_bounded_and_not_repeated_when_unresolved(tmp_path,monkeypatch):
    out=tmp_path/'run';(out/'sources').mkdir(parents=True);c=plan();c['coarse_rest']={'nodes':17,'length':16.,'spacing':1.,'source_stride':2}
    g=Grid((17,)*3,(16.,)*3,'fixed');n=np.broadcast_to(NORTH,g.shape+(3,)).copy();model={'id':'q17','q':17,'axis':2,'source':'q17'};d={'rest':{}};calls=[]
    metric={'relative_force_l2':1.,'acceleration_max':1.,'hopf_integral':-17.,'minimum_corner_cone':1.,'unit_error':0.}
    monkeypatch.setattr(h,'validate_field',lambda *args:(n,{'fixture':True}));monkeypatch.setattr(h,'coarse_field',lambda *args:n);monkeypatch.setattr(h,'stationarity',lambda *args:metric)
    def seed(folder,*args):
        folder.mkdir(parents=True,exist_ok=True);np.savez(folder/'initial.npz',field=n);np.savez(folder/'latest.npz',field=n)
    monkeypatch.setattr(h,'seed_continuation',seed);monkeypatch.setattr(h,'checked_field',lambda *args:(n,g));monkeypatch.setattr(h,'rest_metrics',lambda *args:{'stationarity':metric,'state_sha256':'fixture'})
    def relax(*args,**kwargs):calls.append(True);return {'status':'checkpointed','iterations':len(calls)*50}
    monkeypatch.setattr(h,'relax',relax);r=h.prepare(out,model,d,c,lambda:None)
    assert r['status']=='preparation_unresolved' and len(calls)==r['optimizer_calls_allocated']==4
    h.prepare(out,model,d,c,lambda:None);assert len(calls)==4


def test_unqualified_q2_reference_never_calls_optimizer(tmp_path,monkeypatch):
    out=tmp_path/'run';(out/'sources').mkdir(parents=True);c=plan();c['reference_rest']={'nodes':17,'length':16.,'spacing':1.};g=Grid((17,)*3,(16.,)*3,'fixed');n=np.broadcast_to(NORTH,g.shape+(3,)).copy();metric={'relative_force_l2':1.,'acceleration_max':1.,'hopf_integral':-2.,'minimum_corner_cone':1.,'unit_error':0.}
    monkeypatch.setattr(h,'validate_field',lambda *args:(n,{}));monkeypatch.setattr(h,'stationarity',lambda *args:metric);monkeypatch.setattr(h,'checked_field',lambda *args:(n,g));monkeypatch.setattr(h,'rest_metrics',lambda *args:{'stationarity':metric,'state_sha256':'fixture'})
    def seed(folder,*args):
        folder.mkdir(parents=True,exist_ok=True);np.savez(folder/'initial.npz',field=n);np.savez(folder/'latest.npz',field=n)
    monkeypatch.setattr(h,'seed_continuation',seed)
    def no_optimizer(*args,**kw):raise AssertionError('Q2 reference must not be optimized in this screen')
    monkeypatch.setattr(h,'relax',no_optimizer);r=h.prepare(out,{'id':'q2','q':2,'axis':2,'source':'q2'},{'rest':{}},c,lambda:None)
    assert r['status']=='preparation_unresolved' and r['optimizer_calls_allocated']==0
