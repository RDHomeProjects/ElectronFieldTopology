"""Admission, recovery and orchestration checks; synthetic jobs are not CUDA data."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile

import numpy as np
import pytest
from electron_field_topology import sf_q_basin as b
from electron_field_topology.sf_checkpoints import atomic_json,checkpoint
from electron_field_topology.sf_relax import validate
from electron_field_topology.skyrme import coordinates,rational_field,set_boundary


def empty_inventory(): return {'verified_fields':[],'recorded_at':b.timestamp(),'historical_q18':'no verified field found; fresh reconstruction'}


def test_plan_keeps_one_factor_controls_and_three_fine_meshes():
    plan=b.build_plan(empty_inventory());assert len(plan['stages'])==31
    assert plan['overall_wall_seconds'] is None
    stages={s['id']:s for s in plan['stages']};seen=set()
    for stage in plan['stages']:
        if 'from' in stage:assert stage['from'] in seen
        seen.add(stage['id']);validate(b.prepare_config(stage,plan=plan))
    for label in ('q18-baseline','q17-neighbour','q19-neighbour'):
        assert {(stages[label+f'-{n}']['n']-1)*stages[label+f'-{n}']['h'] for n in (129,161,193)}=={15.36}
        assert stages[label+'-domain']['h']==stages[label+'-161']['h']
    base=b.prepare_config(stages['q18-baseline-97'],plan=plan)
    for key in ('q18-scale35-97','q18-scale45-97'):
        c=b.prepare_config(stages[key],plan=plan)
        assert {k:v for k,v in c['seed'].items() if k!='scale'}=={k:v for k,v in base['seed'].items() if k!='scale'}
    other=b.prepare_config(stages['q18-ell025-97'],plan=plan)
    assert other['seed']==base['seed'] and other['precondition_length']==.25
    for q,pair in ((17,(5,1)),(19,(6,1))):
        c=b.prepare_config(stages[f'q{q}-neighbour-129'],plan=plan)
        assert 2*c['seed']['alpha']+7*c['seed']['beta']==q
        c['seed']['alpha']=2
        with pytest.raises(ValueError,match='reviewed'):validate(c)


def test_rolling_recovery_falls_back_and_requires_same_config_charge_geometry(tmp_path):
    stage={'n':17,'h':.2,'q':1}
    u=set_boundary(rational_field(coordinates(17,.2),scale=.6,cutoff=1.3))
    checkpoint(tmp_path/'previous.npz',u,.2,1,4,2.,'right')
    (tmp_path/'latest.npz').write_bytes(b'corrupt interrupted write')
    path,receipt=b.recover_field(tmp_path,stage,'right')
    assert path.name=='previous.npz' and receipt['requires_new_initial_cpu_gpu_audit']
    assert receipt['rejected_candidates']
    with np.load(path) as d:assert 'written_utc' in d and '+11:00' in str(d['written_melbourne'])
    with pytest.raises(ValueError,match='No recoverable'):b.recover_field(tmp_path,stage,'wrong')
    with pytest.raises(ValueError,match='No recoverable'):b.recover_field(tmp_path,{**stage,'q':2},'right')


def test_inventory_requires_exact_published_hash_and_missing_is_a_fresh_start(tmp_path,monkeypatch):
    folder=tmp_path/'q18-193';folder.mkdir();p=folder/'final.npz';p.write_bytes(b'historical bytes')
    digest=b.stream_sha(p)
    item={'config':{'expected_q':18},'stationary':True,'record':'committed fixture'}
    monkeypatch.setattr(b,'published_checkpoints',lambda:{digest:item})
    receipt=b.inventory([tmp_path,tmp_path])
    assert len(receipt['verified_fields'])==1 and receipt['historical_q18']=='available'
    p.write_bytes(b'changed bytes')
    receipt=b.inventory([tmp_path]);assert not receipt['verified_fields'] and receipt['unmatched_fields']
    p.unlink();assert 'fresh reconstruction' in b.inventory([tmp_path])['historical_q18']


def synthetic_executor(argv,log,seconds):
    Path(log).write_text('Synthetic orchestration fixture, not GPU evidence.\n')
    if 'electron_field_topology.sf_relax' not in argv:return {'status':'completed','returncode':0}
    c=b.read(argv[argv.index('--config')+1]);case=Path(argv[argv.index('--output')+1]);case.mkdir()
    atomic_json(case/'config.json',c)
    final={'hopf_integral':-c['expected_q'],'minimum_corner_cone':.1,'unit_error':1e-15,'tangent_gradient_rms':.0008,
           'cpu_tangent_gradient_rms':.0008,'cpu_endpoint_audit':{'fixture_only':True},'virial_residual':.01,'energy':c.get('published_energy',12.),'e2':6.,'e4':6.}
    atomic_json(case/'result.json',{'status':'gradient_stationary','config':c,'initial':final,'final':final})
    atomic_json(case/'history.json',[])
    for name in ('initial.npz','final.npz'):(case/name).write_bytes(b'fixture only; no physical field')
    m={'source_unchanged_during_run':True,'device_validation':{'passed':True,'scope':'synthetic test only'},
       'artifacts_sha256':{p.name:b.sha(p) for p in case.iterdir()}}
    atomic_json(case/'manifest.json',m)
    return {'status':'completed','returncode':0}


def fixture_run(tmp_path,monkeypatch,executor=synthetic_executor):
    monkeypatch.setattr(b,'clean_commit',lambda:'synthetic-commit')
    monkeypatch.setattr(b,'code_hashes',lambda:{'fixture':'unchanged'})
    monkeypatch.setattr(b,'inventory',lambda roots:empty_inventory())
    return b.run(tmp_path/'campaign',_executor=executor)


def test_full_orchestration_collect_and_resume_do_not_rerun_completed_jobs(tmp_path,monkeypatch):
    calls=[]
    def executor(*args):calls.append(args[0]);return synthetic_executor(*args)
    state=fixture_run(tmp_path,monkeypatch,executor)
    assert len(state['stages'])==31 and all(j['status']=='stationary' for j in state['stages'].values())
    out=tmp_path/'campaign';before=len(calls)
    b.run(out,resume=True,_executor=executor);assert len(calls)==before
    summary=b.collect(out)
    assert summary['comparisons']['q18-baseline-161__q18-baseline-193']['status']=='pass'
    with zipfile.ZipFile(out/'evidence.zip') as z:
        assert not any(n.startswith('cases/') and n.endswith('.npz') for n in z.namelist())
        m=json.loads(z.read('evidence-hashes.json'))
        assert all(hashlib.sha256(z.read(n)).hexdigest()==v['sha256'] for n,v in m['files'].items())
    with pytest.raises(FileExistsError):b.run(out,_executor=executor)
    plan=b.read(out/'plan.json');plan['pass_seconds']=1700;atomic_json(out/'plan.json',plan)
    with pytest.raises(ValueError,match='frozen plan'):b.run(out,resume=True,_executor=executor)


def test_failed_control_prevents_research_and_records_partial_result(tmp_path,monkeypatch):
    calls=[]
    def executor(argv,log,seconds):
        calls.append(argv);Path(log).write_text('deliberate fixture failure\n');return {'status':'failed','returncode':2}
    state=fixture_run(tmp_path,monkeypatch,executor)
    assert len(calls)==2  # Q1 and Q2 only; no Q17/Q18/Q19/Q22 solve.
    assert state['stages']['q18-baseline-97']['status']=='control_failure'
    assert b.read(tmp_path/'campaign/summary.json')['disposition']=='partial_pending_scientific_review'


def test_interrupt_resume_keeps_unique_attempts(tmp_path,monkeypatch):
    stopped=[False]
    def executor(argv,log,seconds):
        result=synthetic_executor(argv,log,seconds)
        if '-m' in argv and not stopped[0]:
            stopped[0]=True;raise KeyboardInterrupt
        return result
    state=fixture_run(tmp_path,monkeypatch,executor);assert state['interrupted']
    out=tmp_path/'campaign'
    state=b.run(out,resume=True,_executor=synthetic_executor)
    job=state['stages']['q1-control'];assert len(job['attempts'])==2
    assert len({a['directory'] for a in job['attempts']})==2 and job['recovery']['kind']=='audited_endpoint'


def test_original_archive_check_allows_live_edits_but_rejects_manifest_tampering(tmp_path):
    spec=importlib.util.spec_from_file_location('recovery',b.ROOT/'scripts/check_pr36_staged_recovery.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    (tmp_path/'docs').mkdir();ledger=b.read(b.ROOT/'docs/pr36-staged-recovery.json')
    target=tmp_path/ledger['source_bundle']['path'];target.parent.mkdir(parents=True)
    shutil.copyfile(b.ROOT/ledger['source_bundle']['path'],target)
    atomic_json(tmp_path/'docs/pr36-staged-recovery.json',ledger)
    (tmp_path/'src').mkdir();(tmp_path/'src/new-development.py').write_text('legitimate evolution\n')
    assert module.verify(tmp_path)==191
    key=next(iter(ledger['stages'][0]['files']));ledger['stages'][0]['files'][key]='0'*40
    atomic_json(tmp_path/'docs/pr36-staged-recovery.json',ledger)
    with pytest.raises(ValueError,match='archived blob'):module.verify(tmp_path)
    target.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='SHA-256'):module.verify(tmp_path)


def test_reviewed_q22_infrastructure_does_not_admit_later_edits(tmp_path,monkeypatch):
    from electron_field_topology import sf_q22_closure as closure
    key='src/electron_field_topology/sf_checkpoints.py'
    old,new=closure.INFRASTRUCTURE_REVISIONS[key]
    target=tmp_path/key;target.parent.mkdir(parents=True)
    shutil.copyfile(b.ROOT/key,target)
    assert b.sha(target)==new
    monkeypatch.setattr(closure,'ROOT',tmp_path)
    closure.verify_historical_sources({'source_sha256':{key:old}})
    target.write_bytes(target.read_bytes()+b'\n# unreviewed edit\n')
    with pytest.raises(ValueError,match='source changed'):
        closure.verify_historical_sources({'source_sha256':{key:old}})


def test_independent_curve_link_audit_uses_retained_hashes_and_known_link(tmp_path):
    t=np.linspace(0,2*np.pi,257)
    a=np.stack([np.cos(t),np.sin(t),np.zeros_like(t)],axis=-1)
    z=np.stack([1+np.cos(t),np.zeros_like(t),np.sin(t)],axis=-1)
    a[-1]=a[0];z[-1]=z[0]
    np.savez(tmp_path/'final-primary-curves.npz',curve_0=a,curve_1=z)
    atomic_json(tmp_path/'topology.json',{'phases':{'final':{'checkpoint_sha256':'fixture','targets':{'primary':{'components':2}}}}})
    r=b.audit_curve_links(tmp_path);row=r['targets']['final-primary']
    assert row['curves_sha256']==b.sha(tmp_path/'final-primary-curves.npz')
    values=[x['linking_integral'] for x in row['pairs'][0]['gauss_samples']]
    assert all(abs(abs(v)-1)<1e-3 for v in values)
    assert row['pairs'][0]['signed_diagram_link'] is None  # Do not invent a missing diagram comparison.
