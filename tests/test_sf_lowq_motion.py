"""Motion instruments: anisotropic topology, physical resolution, resume and fail ledgers."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology.sf_lowq_motion import campaign,plan_cases,merged_history,validate_campaign
from electron_field_topology.sf_motion_metrics import hopf,evaluate,spatial_metrics
from electron_field_topology.sf_time import Grid
from electron_field_topology.sf_readmission import checkpoint
from electron_field_topology.skyrme import NORTH,diagnostics as old_topology,rational_field

ROOT=Path(__file__).resolve().parents[1]


def config():return json.loads((ROOT/'experiments/configs/sf-motion/smoke.json').read_text())


def test_anisotropic_hopf_reduces_to_independent_existing_cubic_instrument():
    g=Grid((17,)*3,(8.,)*3,'fixed');n=rational_field(g.points(),cutoff=3.2)
    n[g.fixed_mask()]=NORTH
    assert abs(hopf(n,g)['hopf_integral']-old_topology(n,g.spacing[0])['hopf_integral'])<1e-14
    swapped=n.transpose(1,0,2,3);assert abs(hopf(swapped,g)['hopf_integral']+hopf(n,g)['hopf_integral'])<1e-14


def test_lab_grid_preserves_rest_longitudinal_resolution(tmp_path):
    c=config();c['betas']=[.1,.3];c['axes']=[0,2];before=copy.deepcopy(c);s=c['seeds'][0]
    p=tmp_path/'seed.npz';g=Grid((s['nodes'],)*3,(s['length'],)*3,'fixed')
    checkpoint(p,np.broadcast_to(NORTH,g.shape+(3,)).copy(),g,1,'cfg',0,0,'code')
    cases=plan_cases(c,'seed',s,p);assert len(cases)==10
    for row in cases:
        a=row['axis'];h=row['physical']['lengths'][a]/(row['physical']['grid'][a]-1)
        assert h<=g.spacing[a]*np.sqrt(1-row['beta']**2)+1e-15
    assert c==before # plan generation must not mutate the config


def test_resume_history_preserves_whole_run_baseline(tmp_path):
    a=tmp_path/'a';b=tmp_path/'b';a.mkdir();b.mkdir()
    (a/'history.json').write_text(json.dumps([{'step':0,'energy':10},{'step':2,'energy':11}]))
    (b/'history.json').write_text(json.dumps([{'step':2,'energy':11},{'step':4,'energy':12}]))
    rows=merged_history([a,b]);assert [r['step'] for r in rows]==[0,2,4]
    assert rows[0]['energy']==10


def test_campaign_keeps_failed_admission_and_skips_boosts(tmp_path):
    c=config();profile={'export':{'enabled':False}}
    first=campaign(c,tmp_path,profile)
    assert first['status']=='complete_pending_review'
    assert list(first['seeds'].values())[0]['status']=='topology_unresolved'
    assert sum(r['status']=='skipped_unadmitted_rest' for r in first['cases'].values())==2
    assert sum(r['status']=='complete' for r in first['cases'].values())==2
    assert all(not r['assessment']['bounded_case_gates_pass'] for r in first['cases'].values() if r['status']=='complete')
    assert (tmp_path/'evidence.zip').is_file()
    again=campaign(c,tmp_path,{'export':{'enabled':True,'grid':[9]*3}})
    for k,r in first['cases'].items():
        if r['status']=='complete':assert again['cases'][k]['final_checkpoint_sha256']==r['final_checkpoint_sha256']
    c2=copy.deepcopy(c);c2['duration']*=2
    with pytest.raises(ValueError,match='differs'):campaign(c2,tmp_path,profile)


def test_config_rejects_undeclared_high_speed_and_duplicate_seeds():
    c=config();c['betas']=[.9]
    with pytest.raises(ValueError):validate_campaign(c)
    c=config();c['seeds']*=2
    with pytest.raises(ValueError):validate_campaign(c)


def test_admitted_branch_records_actual_boost_diagnostics_and_transport_hashes(tmp_path,monkeypatch):
    # A deliberately neutral localized field isolates the admitted-branch I/O path.
    # Mock admission is not used as physics evidence; its charge gate must still fail.
    import hashlib,zipfile
    from electron_field_topology.sf_readmission import stationarity
    from electron_field_topology.sf_dynamics_admission import sha
    from electron_field_topology.sf_checkpoints import atomic_json
    def fixture_admission(c,out,limit):
        out=Path(out);out.mkdir(parents=True,exist_ok=True)
        g=Grid((c['nodes'],)*3,(c['length'],)*3,'fixed');x=g.points()
        a=.1*np.exp(-np.sum(x*x,axis=-1));n=np.stack((np.sin(a),np.zeros(g.shape),np.cos(a)),axis=-1);n[g.fixed_mask()]=NORTH
        checkpoint(out/'latest.npz',n,g,1,'fixture',0,0,'fixture')
        return {'status':'stationary','final':stationarity(n,g),'field_sha256':sha(out/'latest.npz')}
    monkeypatch.setattr('electron_field_topology.sf_lowq_motion.relax',fixture_admission)
    c=config();c['seeds'][0].update(nodes=9,length=4.,seed_cutoff=1.6);c['boundary_shell_width']=.5
    ledger=campaign(c,tmp_path,{'export':{'enabled':False}})
    boosts=[r for r in ledger['cases'].values() if r['beta']]
    assert len(boosts)==2 and all(r['status']=='complete' for r in boosts)
    assert all(not r['assessment']['checks']['topology'] for r in boosts)
    assert all('initial_particle_energy_relative_defect' in r['assessment'] for r in boosts)
    with zipfile.ZipFile(tmp_path/'evidence.zip') as z:
        hashes=json.loads(z.read('evidence-hashes.json'))['sha256']
        for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
