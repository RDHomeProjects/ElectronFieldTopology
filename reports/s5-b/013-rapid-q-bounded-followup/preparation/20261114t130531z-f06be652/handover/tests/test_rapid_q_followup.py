"""Regression controls for lost medium endpoints, capacity and continuation."""
import copy,json,tempfile
from pathlib import Path
import numpy as np
from electron_field_topology.rapid_q_followup.selection import select_prior,allocation_ledger
from electron_field_topology.rapid_q_screen.engine import Engine,checkpoint,restore
from electron_field_topology.sf_time import Grid
from electron_field_topology.sf_candidate_seeds import sampled


def test_medium_represented_endpoint_precedes_invalid_coarse_and_retains_both():
    p={'charge_relative_error':.05,'unit_limit':1e-10,'force_limit':1e-4,'acceleration_limit':1e-3,'initial_tail_limit':.00075}
    def row(nodes,hopf,force,accel):return {'q':4,'nodes':nodes,'length':23.04,'status':'preparation_unresolved','checkpoint_sha256':'a'*64,'latest':{'stationarity':{'hopf_integral':hopf,'relative_force_l2':force,'acceleration_max':accel,'minimum_corner_cone':.8,'unit_error':0.},'tail':{'fraction':.0002}}}
    candidates=[('coarse',row(97,-3.5,.2,10.)),('medium',row(121,-3.96,.00017,.00199))]
    r=select_prior(candidates,p);assert r['primary_rest_id']=='medium';assert {v['rest_id'] for v in r['alternatives']}=={'coarse','medium'}


def test_capacity_omission_and_exhausted_budget_are_explicit_without_q_rejection():
    def row(id):return {'q':5,'seed':{'id':id},'classification':{'decision':'priority_continue'}}
    rows=allocation_ledger([row('axial'),row('trefoil')],[row('axial')]);assert any(v['seed']=='trefoil' and v['allocation_status']=='deferred_priority_capacity' for v in rows);assert any(v['seed']=='axial' and v['allocation_status']=='budget_exhausted_unresolved' for v in rows);assert not any(v['whole_Q_rejected'] for v in rows)


def test_declared_production_budget_and_fixed_geometries():
    p=json.loads((Path(__file__).resolve().parents[1]/'experiments/configs/rapid-q-followup-20261114.json').read_text());assert p['batch_steps']==50 and sum(v['additional_steps'] for v in p['jobs'])==p['total_additional_step_budget']==650
    assert [(v['id'],v['nodes'],v['additional_steps']) for v in p['jobs']]==[('q6-axial6-1',97,200),('q4-axial22',121,100),('q7-trefoil',121,100),('q8-trefoil32-1-2',121,100),('q5-trefoil32-1-1',97,50),('q9-trefoil32-3-1',145,50),('q10-trefoil32-2-2',145,50)]
    assert not p['motion_execution'] and not p['automatic_mesh_refinement']


def test_checkpoint_continuation_preserves_conjugacy_and_observation_schedule():
    g=Grid((33,)*3,(12.,)*3,'fixed');seed={'id':'resume-control','q':3,'family':'axial','alpha':3,'beta':1,'scale':1.4,'cutoff':4.5,'bend':.1,'amplitude':1.,'perturbation':.005};e=Engine('cpu');state=e.state(sampled(g,seed))
    for _ in range(3):assert e.step(state,g)[0]
    state.update(next_observe=17,observe_spacing=5)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'latest.npz';checkpoint(path,state,e,{'control':'resume'});resumed=restore(path,e,{'control':'resume'});assert resumed['next_observe']==17 and resumed['observe_spacing']==5
        for _ in range(3):assert e.step(state,g)[0] and e.step(resumed,g)[0]
        np.testing.assert_array_equal(state['n'],resumed['n']);np.testing.assert_array_equal(state['direction'],resumed['direction'])
        try:restore(path,e,{'control':'changed'})
        except ValueError:pass
        else:raise AssertionError('Changed checkpoint identity accepted')
