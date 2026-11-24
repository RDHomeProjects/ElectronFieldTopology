"""Read-only resource routing: CPU fallback before a branch starts."""
import argparse,json,sys,gc
from pathlib import Path
import numpy as np
from common import ROOT,stamp,load,need
sys.path.append(str(ROOT/'kernel'))

def route(requested,available,free_gpu=None,cuda_ready=False):
    plan=load(ROOT/'PLAN.json');nodes=177;host_est=nodes**3*600/1024**3+.5;gpu_est=nodes**3*1100/1024**3+.5
    host_ok=host_est<=min(6.5,available-plan['host_reserve_gib']);gpu_ok=bool(cuda_ready and free_gpu is not None and gpu_est<=free_gpu-plan['gpu_reserve_gib'])
    need(host_ok,'Host memory estimate does not preserve reserve')
    if requested=='cuda':need(gpu_ok,'Explicit CUDA geometry fails admission; use --backend auto or cpu for fallback')
    selected='cuda' if requested!='cpu' and gpu_ok else 'cpu'
    return {'selected':selected,'host_estimated_gib':host_est,'gpu_estimated_gib':gpu_est,'free_gpu_gib':free_gpu,'gpu_admitted':gpu_ok,'fallback_reason':None if selected=='cuda' or requested=='cpu' else 'CUDA unavailable or geometry does not preserve the 1 GiB device reserve','one_backend_for_both_matched_arms':True,'mapping_backend':'cpu'}

def probe(requested):
    from common import host
    from engine import Engine
    from electron_field_topology.sf_time import Grid
    from electron_field_topology.skyrme import rational_field,NORTH
    need(sys.version_info[:3]==(3,12,14),'Pinned Python 3.12.14 required')
    grid=Grid((17,)*3,(12.,)*3,'fixed');n=rational_field(grid.points(),alpha=1,beta=1,scale=2.,cutoff=4.);n[grid.fixed_mask()]=NORTH
    cpu=Engine('cpu');e,g=cpu.value(n,grid);need(np.isfinite(e) and np.isfinite(g).all(),'CPU reference kernel failed');free=None;ready=False;error=None;identity=None
    if requested!='cpu':
        try:
            cuda=Engine('cuda');free=cuda.xp.cuda.runtime.memGetInfo()[0]/1024**3;decision=route('auto',host()['available_gib'],free,True)
            if decision['gpu_admitted']:
                audit=cuda.audit(cuda.xp.asarray(n),grid);need(audit['passed'],'Small-grid CPU/CUDA gradient mismatch');identity=cuda.port.identity();ready=True
            del cuda;gc.collect()
        except Exception as exc:error=repr(exc)
    decision=route(requested,host()['available_gib'],free,ready)
    return {'recorded_at':stamp(),'status':'pass','requested':requested,**decision,'cuda_identity':identity,'cuda_probe_error':error,'qualification_optimizer_attempts':0,'physical_time_steps':0,'scope':'Small-grid backend check plus native geometry memory estimate. Independent native-field audit is mandatory before either arm.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--backend',choices=['auto','cpu','cuda'],default='auto');a=p.parse_args();print(json.dumps(probe(a.backend),allow_nan=False))
