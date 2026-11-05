"""Independent fixed-mask, continuation and display-isolation controls for S5-B-006."""
import json,hashlib
import copy
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology import sf_focused_motion as f
from electron_field_topology.sf_time import Grid
from electron_field_topology.sf_time_run import run as original_run,state_sha
from electron_field_topology.sf_lowq_motion import campaign,evidence
from electron_field_topology.skyrme import NORTH


def config():return json.loads(f.CONFIG.read_text())


def fingerprint(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def test_thin_layer_failure_is_exposed_then_constraints_and_event_derivative_hold():
    r=f.boundary_controls()
    assert r['passed'] and len(r['rows'])==8 and max(r['free_node_event_errors'])<1e-8
    assert any(x['raw_fixed_field_max']>1e-4 for x in r['rows'] if x['method']=='cubic' and x['beta']==.1)
    assert all(x['fixed_field_max']==0 and x['fixed_rate_max']==0 for x in r['rows'])


@pytest.mark.parametrize('axis',[0,2])
def test_projection_preserves_every_free_value_and_rate_to_roundoff(axis):
    rg=Grid((17,)*3,(8.,)*3,'fixed');p=rg.points()
    theta=.1*np.maximum(1-np.sum(p*p,axis=-1)/4,0)**6
    rest=np.stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1);before=rest.copy()
    g=f.lab_grid(rg,.1,axis);n,v,r=f.readmit(rest,rg,g,.1,axis,'cubic')
    assert r['passed'] and r['free_field_correction_max']<1e-12 and r['free_rate_correction_max']<1e-12
    assert np.array_equal(rest,before)


@pytest.fixture(scope='session')
def cached_boundary_controls():
    result=f.boundary_controls();assert result['passed'];return result


@pytest.fixture
def source(tmp_path,monkeypatch,cached_boundary_controls):
    # Reuse one genuinely executed independent control across software fixtures;
    # each production campaign still executes its own controls before evolution.
    monkeypatch.setattr(f,'boundary_controls',lambda:copy.deepcopy(cached_boundary_controls))
    c=json.loads((f.ROOT/'experiments/configs/sf-motion/smoke.json').read_text())
    c['seeds']=[{'q':1,'nodes':9,'length':4.,'seed_scale':1.6,'seed_cutoff':1.6}]
    c.update(betas=[.3],axes=[0,2],duration=.04,time_steps=[.01,.005],boundary_shell_width=.5,diagnostic_every=1,checkpoint_every=2)
    path=tmp_path/'source';campaign(c,path,{'export':{'enabled':False}})
    # Direct numerical probes on an explicitly unresolved coarse rest fixture.
    # Keep its unresolved status and all failed topology gates; do not relax any
    # research threshold to manufacture an admitted physical soliton.
    ledger=json.loads((path/'campaign.json').read_text())
    for row in ledger['cases'].values():
        if row['beta']==0:continue
        attempt=path/'cases'/row['id']/'attempt-001'
        result=original_run(row['physical'],attempt,{'export':{'enabled':False}})
        row.update(status='complete',attempts=[str(attempt)],result=result,
                   final_checkpoint_sha256=f.sha(attempt/'final.npz'),
                   fixture_scope='Unadmitted coarse numerical probe only; not research acceptance')
    f.atomic_json(path/'campaign.json',ledger);evidence(path)
    cfg=config();cfg.update(source_evidence_sha256=f.sha(path/'evidence.zip'),seeds=['q1-n9-L4'],
         admission_seeds=['q1-n9-L4'],milestone_times=[.02,.04],shell_width=.5,diagnostic_every=1,checkpoint_every=2)
    return path,cfg


def final_hashes(result):return {k:v['milestones']['0.04']['state_sha256'] for k,v in result['cases'].items()}


def test_real_runner_bridge_matches_direct_solver_and_does_not_mutate_source(source,tmp_path):
    path,cfg=source;before=fingerprint(path);out=tmp_path/'run'
    r=f.run(path,out,cfg,{'export':{'enabled':False}})
    assert r['status']=='complete_pending_review' and len(r['cases'])==4
    row=next(iter(r['cases'].values()));physics=row['physics']
    g=f.validate(physics);initial=out/'cases'/row['id']/'admitted.npz'
    direct=original_run(physics,tmp_path/'direct',{'export':{'enabled':False}},resume=initial)
    assert direct['state_sha256']==row['milestones']['0.04']['state_sha256']
    assert all(x['admission']['original_raw_replay_bit_exact'] for x in r['cases'].values())
    assert any(not all(m['assessment']['checks'].values()) for c in r['cases'].values() for m in c['milestones'].values())
    assert fingerprint(path)==before
    import zipfile
    with zipfile.ZipFile(out/'evidence.zip') as z:
        h=json.loads(z.read('evidence-hashes.json'))['sha256']
        assert set(z.namelist())==set(h)|{'evidence-hashes.json'}
        for n,d in h.items():assert hashlib.sha256(z.read(n)).hexdigest()==d
    # No repeated computation or overwrite of completed milestone state.
    assert final_hashes(f.run(path,out,cfg,{'export':{'enabled':False}}))==final_hashes(r)


def test_checkpoint_stop_resume_is_bit_exact_and_truncates_uncommitted_history(source,tmp_path,monkeypatch):
    path,cfg=source;real=f.evolve;calls=[]
    def paused(physics,output,profile,resume,stop_after):
        if not calls:
            calls.append(True);value=real(physics,output,profile,resume=resume,stop_after=1);f.STOP=True;return value
        return real(physics,output,profile,resume=resume,stop_after=stop_after)
    monkeypatch.setattr(f,'evolve',paused)
    out=tmp_path/'resumed';first=f.run(path,out,cfg,{'export':{'enabled':False}})
    assert first['status']=='stopped_checkpoint_retained'
    resumed=f.run(path,out,cfg,{'export':{'enabled':False}})
    uninterrupted=f.run(path,tmp_path/'uninterrupted',cfg,{'export':{'enabled':False}})
    assert final_hashes(resumed)==final_hashes(uninterrupted)


def test_display_export_changes_no_scientific_endpoint(source,tmp_path):
    path,cfg=source
    off=f.run(path,tmp_path/'off',cfg,{'export':{'enabled':False}})
    on=f.run(path,tmp_path/'on',cfg,{'export':{'enabled':True,'every_steps':1,'grid':[5]*3,'fields':['field'],'vtk':True}})
    assert final_hashes(off)==final_hashes(on)
    for row in on['cases'].values():
        p=tmp_path/'on'/'cases'/row['id']/'preview/series.pvd';assert p.exists()


def test_sealed_checkpoint_tamper_and_plan_change_are_rejected(source,tmp_path):
    path,cfg=source;out=tmp_path/'run';r=f.run(path,out,cfg,{'export':{'enabled':False}})
    changed={**cfg,'milestone_times':[.02,.03,.04]}
    with pytest.raises(ValueError,match='changed'):f.run(path,out,changed,{'export':{'enabled':False}})
    victim=Path(next(iter(r['cases'].values()))['milestones']['0.02']['checkpoint'])
    victim.write_bytes(victim.read_bytes()+b'Synthetic tamper')
    with pytest.raises(ValueError,match='changed'):f.run(path,out,cfg,{'export':{'enabled':False}})
