"""Small controls; no overnight or production-field work in hosted CI."""
import copy
import json
import numpy as np
import pytest
from electron_field_topology import sf_q1_settling as s,sf_q1_campaign as c
from electron_field_topology.sf_tail_domain import seed_continuation,checked_field,exact_extension
from electron_field_topology.sf_readmission import relax
from electron_field_topology.sf_time import Grid
from electron_field_topology.skyrme import NORTH,rational_field


def fixture():
    g=Grid((33,)*3,(8.,)*3,'fixed');n=rational_field(g.points(),alpha=1,beta=1,scale=1.1,cutoff=3.2);n[g.fixed_mask()]=NORTH
    config={'q':1,'nodes':33,'length':8.,'relative_force_l2':1e-12,'acceleration_max':1e-12,'charge_relative_error':.05,'iterations_per_pass':3,'checkpoint_every':1,'stagnation_relative_energy':1e-14}
    study=json.loads(c.CONFIG.read_text());study.update(spacing=.25,max_iterations_per_case=12,observe_every=1,common_nodes=17,profile_half_widths=[1.,2.,3.],shell_width=.5,core_field_relative_change=0.)
    return n,g,config,study


def test_native_contract_and_unchanged_tail_limit():
    study=json.loads(c.CONFIG.read_text());c.validate(study)
    for key,value in [('tail_fraction_limit',.002),('spacing',.15),('max_iterations_per_case',2400)]:
        bad=copy.deepcopy(study);bad[key]=value
        with pytest.raises(ValueError):c.validate(bad)


def test_first_optimizer_steps_match_established_original_bit_exact(tmp_path):
    n,g,config,study=fixture();a=tmp_path/'old';b=tmp_path/'new'
    seed_continuation(a,n,g,1,config);s.seed(b,n,g,config)
    old=relax(config,a,pass_limit=1);new=s.relax_settling(config,b,study,pass_limit=1)
    na,_=checked_field(a,config);nb,_=s.checked(b,config)
    assert np.array_equal(na,nb) and old['iterations']==new['iterations']==3
    assert old['status']==new['status']=='checkpointed'
    assert np.array_equal(np.load(b/'initial.npz')['field'],n)


def test_iteration_budget_is_unresolved_and_checkpoint_is_resumable_state(tmp_path):
    n,g,config,study=fixture();study['max_iterations_per_case']=2;s.seed(tmp_path,n,g,config)
    r=s.relax_settling(config,tmp_path,study)
    assert r['status']=='settling_budget_exhausted' and r['iterations']==2
    final,_=s.checked(tmp_path,config);assert np.isfinite(final).all()
    assert len(json.loads((tmp_path/'observations.json').read_text()))==3


def test_stability_requires_separate_regular_intervals_and_all_metrics():
    study=json.loads(c.CONFIG.read_text());rows=[]
    for i in range(4):
        rows.append({'iteration':i*100,'regular_observation':True,'tail_fraction_change':0.,'shell_energy_change':0.,'core_field_relative_change':0.,'hamiltonian_relative_change':0.})
    assert not s.stable_intervals(rows[:3],study)
    assert s.stable_intervals(rows,study)
    bad=copy.deepcopy(rows);bad[-1]['iteration']=250;assert not s.stable_intervals(bad,study)
    for key in ['tail_fraction_change','shell_energy_change','core_field_relative_change','hamiltonian_relative_change']:
        bad=copy.deepcopy(rows);bad[-1][key]=1.;assert not s.stable_intervals(bad,study)


def test_stable_tail_failure_remains_a_failure_not_optimizer_objective(tmp_path):
    _,_,config,study=fixture();study['observe_every']=100
    rows=[{'iteration':i*100,'regular_observation':True,'shell_fraction':.002,'tail_fraction_change':0.,'shell_energy_change':0.,'core_field_relative_change':0.,'hamiltonian_relative_change':0.} for i in range(4)]
    (tmp_path/'observations.json').write_text(json.dumps(rows))
    m={'relative_force_l2':0.,'acceleration_max':0.,'hopf_integral':-1.,'minimum_corner_cone':1.,'unit_error':0.}
    assert s.settled(tmp_path,m,config,study,300)
    assert not s.settled(tmp_path,m,config,study,325)
    assert rows[-1]['shell_fraction']>study['tail_fraction_limit']


def test_checkpoint_identity_rejects_changed_configuration(tmp_path):
    n,g,config,_=fixture();s.seed(tmp_path,n,g,config);bad={**config,'length':9.}
    with pytest.raises(ValueError,match='identity'):s.checked(tmp_path,bad)


def test_existing_observation_rejects_rewritten_field_and_newer_restart(tmp_path):
    n,g,config,study=fixture();s.seed(tmp_path,n,g,config);s.observe(tmp_path,n,g,1,study,config)
    with pytest.raises(ValueError,match='newer'):s.observe(tmp_path,n,g,0,study,config)
    row=json.loads((tmp_path/'observations.json').read_text())[0];p=tmp_path/row['snapshot'];p.write_bytes(b'damaged')
    with pytest.raises(ValueError,match='changed'):s.observe(tmp_path,n,g,2,study,config)


def test_interrupt_retains_state_and_restart_continues(tmp_path,monkeypatch):
    n,g,config,study=fixture();s.seed(tmp_path,n,g,config);real=s.static_value_gradient;calls=0
    def interrupted(*args):
        nonlocal calls
        calls+=1
        if calls==3:raise KeyboardInterrupt
        return real(*args)
    monkeypatch.setattr(s,'static_value_gradient',interrupted)
    r=s.relax_settling(config,tmp_path,study);assert r['status']=='interrupted'
    s.checked(tmp_path,config);monkeypatch.setattr(s,'static_value_gradient',real)
    r=s.relax_settling(config,tmp_path,study,pass_limit=1)
    assert r['status']=='checkpointed' and r['iterations']>=3


def test_source_hash_mismatch_blocks_without_changing_input(tmp_path):
    p=tmp_path/c.SOURCE_FILE;p.parent.mkdir(parents=True);p.write_bytes(b'not original')
    with pytest.raises(ValueError,match='SHA-256'):c.source_inventory(tmp_path,json.loads(c.CONFIG.read_text()))
    assert p.read_bytes()==b'not original'


def test_same_source_core_is_copied_without_scaling():
    n,g,_,_=fixture();before=n.copy();b=exact_extension(n,39)
    assert np.array_equal(n,before) and np.array_equal(b[3:36,3:36,3:36],n)
    assert np.array_equal(b[:2],np.broadcast_to(NORTH,b[:2].shape))


def test_completed_local_campaign_cannot_resume(tmp_path,monkeypatch):
    from electron_field_topology import sf_q1_local as local
    import sys
    (tmp_path/'campaign.json').write_text(json.dumps({'status':'complete_with_unresolved_pending_review'}))
    monkeypatch.setattr(local,'current',lambda :(tmp_path,{}));monkeypatch.setattr(local,'alive',lambda _:False)
    monkeypatch.setattr(sys,'argv',['q1-local','resume'])
    with pytest.raises(ValueError,match='immutable'):local.main()


def test_fixed_profile_planes_are_identical_even_with_float_box_division():
    from electron_field_topology.sf_q1_metrics import fixed_coordinate_max
    # L22.08/138 is one ulp below .16; exact plane membership must still agree.
    for nodes,length in [(127,20.16),(139,22.08)]:
        radius=fixed_coordinate_max(Grid((nodes,)*3,(length,)*3,'fixed'),.16)
        assert np.count_nonzero(radius<4.)==49**3
        assert np.count_nonzero(radius<=8.)==101**3


def test_missing_or_zero_energy_observables_cannot_qualify_settling():
    study=json.loads(c.CONFIG.read_text())
    rows=[{'iteration':i*100,'regular_observation':True,'tail_fraction_change':None,'shell_energy_change':0.,'core_field_relative_change':None,'hamiltonian_relative_change':0.} for i in range(4)]
    assert not s.stable_intervals(rows,study)


def test_loose_force_alone_cannot_finish_without_distinct_observations(tmp_path):
    n,g,config,study=fixture();config.update(relative_force_l2=1e3,acceleration_max=1e3)
    study.update(core_field_relative_change=1e3,tail_fraction_change=1e3,shell_energy_change=1e3,hamiltonian_relative_change=1e3)
    study['readmission']=config.copy();s.seed(tmp_path,n,g,config)
    r=s.relax_settling(config,tmp_path,study)
    assert r['status']=='settled' and r['iterations']==3
    assert [r['iteration'] for r in json.loads((tmp_path/'observations.json').read_text())]==[0,1,2,3]


def test_restart_keeps_observation_grid_aligned_after_odd_stop(tmp_path):
    n,g,config,study=fixture();config['checkpoint_every']=2;study['observe_every']=2;s.seed(tmp_path,n,g,config)
    a=s.relax_settling(config,tmp_path,study,pass_limit=1)
    assert a['iterations']==3 and a['status']=='checkpointed'
    b=s.relax_settling(config,tmp_path,study,pass_limit=1)
    assert b['iterations']==6 and b['status']=='checkpointed'
    rows=json.loads((tmp_path/'observations.json').read_text())
    assert [r['iteration'] for r in rows if r['regular_observation']]==[0,2,4,6]


def test_restart_rejects_malformed_zero_rate_array(tmp_path):
    n,g,config,_=fixture();s.seed(tmp_path,n,g,config)
    with np.load(tmp_path/'latest.npz',allow_pickle=False) as d:payload={k:d[k].copy() for k in d.files}
    payload['field_rate']=np.zeros(1)
    np.savez_compressed(tmp_path/'latest.npz',**payload)
    with pytest.raises(ValueError,match='rate shape'):s.checked(tmp_path,config)
