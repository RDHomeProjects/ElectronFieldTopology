import argparse,json,sys,gc
from common import ROOT,load,need,stamp

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--backend',choices=['auto','cpu','cuda'],required=True);a=p.parse_args()
    from pathlib import Path
    sys.path.insert(0,str(Path(a.repo)/'src'))
    import numpy as np
    from integrity import authenticate,parent_state
    from evaluations import metrics,gate_result
    from electron_field_topology.sf_time import Grid
    from worker import backend
    receipt=authenticate(Path(a.repo));spec=load(ROOT/'SOURCE.json');plan=load(ROOT/'PLAN.json');parent=parent_state(receipt['endpoint']);g=Grid((97,)*3,(23.04,)*3,'fixed')
    e,be=backend(parent['n'],g,a.backend);m=metrics(parent['n'],g,plan['registered_gates'])
    for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(m[k],spec['expected_metrics'][k],rtol=1e-6,atol=1e-10),'Exact335 replay differs: '+k)
    del parent,e;gc.collect()
    with np.load(receipt['q2'],allow_pickle=False) as z:n=z['field'].copy()
    qg=Grid((spec['q2']['nodes'],)*3,(spec['q2']['length'],)*3,'fixed');qm=metrics(n,qg,plan['registered_gates'])
    need(gate_result(qm,2,plan['registered_gates'])['all_readiness_gates'],'Q2 control does not pass')
    for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(qm[k],spec['q2']['expected'][k],rtol=1e-6,atol=1e-10),'Q2 reference replay differs: '+k)
    print(json.dumps({'recorded_at':stamp(),'status':'preflight_pass','backend':be,'q21_metrics':m,'q2_metrics':qm,'optimizer_attempts':0,'physical_time_steps':0},allow_nan=False))
if __name__=='__main__':main()
