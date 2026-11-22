"""Synthetic small-grid end-to-end control flow; never workstation science."""
import copy,json,sys,tempfile,zipfile,shutil
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common import load,save,sha,stamp
import worker
from electron_field_topology.sf_time import Grid as RealGrid
from electron_field_topology.skyrme import rational_field
from evaluations import metrics
from optimizers import ComparisonEngine

with tempfile.TemporaryDirectory() as td:
    out=Path(td);(out/'handover').mkdir();g=RealGrid((17,)*3,(12.,)*3,'fixed');n=rational_field(g.points(),scale=2.,cutoff=4.5);n[g.fixed_mask()]=[0,0,1]
    plan=copy.deepcopy(load(ROOT/'PLAN.json'));plan['registered_gates'].update(force_limit=1e-12,acceleration_limit=1e-12,charge_relative_error=2.);plan['hessian_basis']=3
    for arm in plan['arms']:
        arm['cap']=1
        if arm['kind']=='mesh':arm['nodes']=25 if arm['id']=='mesh-129' else 33
    plan['maximum_new_optimizer_attempts']=len(plan['arms']);spec=copy.deepcopy(load(ROOT/'SOURCE.json'));spec['expected_metrics']=metrics(n,g,plan['registered_gates']);spec['q2'].update(nodes=17,length=12.)
    # The Q2 gate function is replaced only for the labelled control; preparation
    # measurements and optimizer behavior remain actual small-grid evaluations.
    original_gate=worker.gate_result
    def gates(m,q,p):
        if q==2:return {'representation':True,'strict_stationary':True,'boundary_admitted':True,'all_readiness_gates':True}
        return original_gate(m,q,p)
    parent=ComparisonEngine('cpu').state(n);parent.update(iteration=335,alpha=.18)
    q2path=out/'synthetic-q2.npz';np.savez(q2path,field=n)
    for name,v in [('PLAN.json',plan),('SOURCE.json',spec)]:save(out/'handover'/name,v)
    save(out/'identity.json',{'requested_backend':'cpu'});save(out/'status.json',{'status':'working'})
    original_load=worker.load
    def loader(p):
        pp=Path(p)
        return plan if pp==ROOT/'PLAN.json' else spec if pp==ROOT/'SOURCE.json' else original_load(p)
    def grid(shape,lengths,boundary):
        if tuple(shape)==(97,)*3 and tuple(lengths)==(23.04,)*3:return g
        return RealGrid(shape,lengths,boundary)
    receipt={'endpoint':'synthetic','endpoint_sha256':'synthetic-only','q2':str(q2path)}
    with patch.object(worker,'verify_sources'),patch.object(worker,'authenticate',return_value=receipt),patch.object(worker,'parent_state',return_value=parent),patch.object(worker,'reserves'),patch.object(worker,'load',side_effect=loader),patch.object(worker,'gate_result',side_effect=gates),patch('electron_field_topology.sf_time.Grid',side_effect=grid):
        worker.execute(out,out)
    r=load(out/'record.json');assert r['status']=='complete_pending_review',r;assert len(r['arms'])==19;assert r['charged_attempts']<=19
    from integrity import checked_evidence
    hashes=checked_evidence(out/'evidence.zip');assert 'RELATIONSHIPS.json' in hashes and 'OPTIONS.json' in hashes and 'MOTION.json' in hashes
    assert load(out/'MOTION.json')['production_steps']==0
    print(json.dumps({'recorded_at':stamp(),'status':'pass','synthetic':True,'branches':len(r['arms']),'charged_attempts':r['charged_attempts'],'budget':19,'verified_compact_payloads':len(hashes),'motion_correctly_deferred':True,'scope':'Actual small-grid CPU preparation and full worker/report/seal control flow. Source authentication, resource guards and the labelled Q2 gate use explicit fixtures; this is not workstation validation or a Q21 stability result.'}))
