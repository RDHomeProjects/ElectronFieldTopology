"""Read-only source and CPU/CUDA instrument qualification."""
import argparse,gc,json,sys
from pathlib import Path
from common import ROOT,load,need,stamp

def replay(repo,requested):
    sys.path.insert(0,str(repo/'src'))
    import numpy as np
    from electron_field_topology.sf_time import Grid
    from integrity import authenticate,read_parent
    from evaluations import metrics,gate_result
    from resources import choose
    receipt=authenticate(repo);spec=load(ROOT/'SOURCE.json');p=load(ROOT/'PLAN.json')['registered_gates'];parent=read_parent(receipt['endpoint']);g=Grid((129,)*3,(30.72,)*3,'fixed');m=metrics(parent['n'],g,p)
    for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(m[k],spec['expected_metrics'][k],rtol=1e-6,atol=1e-10),'Final-parent replay differs: '+k)
    need(gate_result(m,21,p)['representation'] and gate_result(m,21,p)['boundary_admitted'],'Final parent representation/boundary fails');backend=choose(parent['n'],g,requested,parent['alpha'],545);del parent;gc.collect()
    with np.load(receipt['q2'],allow_pickle=False) as z:q2=z[spec['q2']['key']].copy()
    qm=metrics(q2,Grid((spec['q2']['nodes'],)*3,(spec['q2']['length'],)*3,'fixed'),p);need(gate_result(qm,2,p)['all_readiness_gates'],'Unchanged Q2 reference failed')
    return {'recorded_at':stamp(),'status':'preflight_pass','backend':backend,'q21_metrics':m,'q2_metrics':qm,'optimizer_attempts':0,'physical_time_steps':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--backend',choices=['auto','cpu','cuda'],required=True);a=p.parse_args();print(json.dumps(replay(a.repo,a.backend),allow_nan=False))
