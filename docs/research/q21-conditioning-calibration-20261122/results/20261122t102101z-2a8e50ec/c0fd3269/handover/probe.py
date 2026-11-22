"""Replay the exact source and reference; qualify one backend for all cases."""
import argparse,gc,json,sys
from pathlib import Path
from common import ROOT,load,need,stamp

def choose_backend(n,g,requested):
    from engine import Engine
    import numpy as np
    detail={'requested':requested,'automatic_cpu_reason':None};choice=requested
    if requested=='auto':
        try:
            e=Engine('cuda');free,_=e.xp.cuda.runtime.memGetInfo();choice='cuda' if np.prod(g.shape)*1100<free*.75 else 'cpu'
            if choice=='cpu':detail['automatic_cpu_reason']='Grid estimate exceeds75% of free VRAM'
            del e;gc.collect()
        except Exception as error:choice='cpu';detail['automatic_cpu_reason']=str(error)
    e=Engine(choice);audit=e.audit(e.xp.asarray(n),g)
    detail.update(selected=choice,device=e.port.identity() if choice=='cuda' else None,source_backend='cuda',backend_transfer=choice!='cuda',bitwise_trajectory_claimed=False,audit=audit)
    del e;gc.collect();return detail

def replay(repo,requested):
    sys.path.insert(0,str(repo/'src'))
    import numpy as np
    from electron_field_topology.sf_time import Grid
    from integrity import authenticate,read_parent
    from evaluations import metrics,gate_result
    r=authenticate(repo);s=load(ROOT/'SOURCE.json');p=load(ROOT/'PLAN.json')['registered_gates'];parent=read_parent(r['endpoint']);g=Grid(tuple(s['shape']),tuple(s['lengths']),'fixed')
    m=metrics(parent['n'],g,p)
    for key in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(m[key],s['expected_metrics'][key],rtol=1e-6,atol=1e-10),'Larger-box parent replay differs: '+key)
    need(gate_result(m,21,p)['representation'] and gate_result(m,21,p)['boundary_admitted'],'Parent representation/boundary admission failed')
    be=choose_backend(parent['n'],g,requested);del parent;gc.collect()
    with np.load(r['q2'],allow_pickle=False) as z:n=z[s['q2']['key']].copy()
    qg=Grid((s['q2']['nodes'],)*3,(s['q2']['length'],)*3,'fixed');qm=metrics(n,qg,p)
    need(gate_result(qm,2,p)['all_readiness_gates'],'Q2 reference control failed')
    for key in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(qm[key],s['q2']['expected'][key],rtol=1e-6,atol=1e-10),'Q2 replay differs: '+key)
    return {'recorded_at':stamp(),'status':'preflight_pass','backend':be,'q21_metrics':m,'q2_metrics':qm,'optimizer_attempts':0,'physical_time_steps':0}

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--backend',choices=['auto','cpu','cuda'],required=True);a=p.parse_args();print(json.dumps(replay(a.repo,a.backend),allow_nan=False))
if __name__=='__main__':main()
