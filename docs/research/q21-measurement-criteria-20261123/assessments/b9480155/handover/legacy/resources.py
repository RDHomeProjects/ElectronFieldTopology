"""Conservative per-geometry admission; no backend switch inside a branch."""
import gc,time
import numpy as np
from common import ROOT,load,need,stamp
from integrity import host
from engine import Engine

def geometry_budget(nodes,backend,available=None,free_gpu=None):
    p=load(ROOT/'PLAN.json');available=host()['available_gib'] if available is None else available
    host_gib=(nodes**3*p['resource_host_bytes_per_node'])/1024**3+p['resource_geometry_overhead_gib']
    result={'nodes':nodes,'backend':backend,'estimated_host_gib':host_gib,'host_available_gib':available,'passed':host_gib<=min(p['geometry_host_budget_gib'],available-6),'scope':'Conservative admission estimate; actual component timing and memory telemetry remain required'}
    if backend=='cuda':
        if free_gpu is None:
            e=Engine('cuda');e.xp.get_default_memory_pool().free_all_blocks();free_gpu=e.xp.cuda.runtime.memGetInfo()[0]/1024**3;del e;gc.collect()
        gpu_gib=nodes**3*p['resource_gpu_bytes_per_node']/1024**3+p['resource_geometry_overhead_gib']
        result.update(estimated_gpu_gib=gpu_gib,free_gpu_gib=free_gpu);result['passed']&=gpu_gib<=free_gpu-p['geometry_gpu_reserve_gib']
    return result

def qualify(n,g,kind,alpha,iteration):
    admission=geometry_budget(g.shape[0],kind);need(admission['passed'],'Geometry does not satisfy memory bounds')
    e=Engine(kind,.25);s=e.state(n);s.update(alpha=alpha,iteration=iteration);audit=e.audit(s['n'],g)
    e.sync();start=time.perf_counter();value,gradient=e.value(s['n'],g);e.sync();seconds=time.perf_counter()-start
    final=e.host(gradient);post=audit;device=e.port.identity() if kind=='cuda' else None
    del s,e;gc.collect();return {'recorded_at':stamp(),'kind':kind,'device':device,'admission':admission,'audit':audit,'post_step_audit':post,'qualification_only_steps':0,'charged_campaign_attempts':0,'seconds':seconds},final

def choose(n,g,requested,alpha,iteration):
    cpu,cpu_n=qualify(n,g,'cpu',alpha,iteration);gpu=None;reason=None
    if requested in ['auto','cuda']:
        try:
            gpu,gpu_n=qualify(n,g,'cuda',alpha,iteration)
            need(np.allclose(cpu_n,gpu_n,rtol=2e-9,atol=2e-10),'CPU/CUDA static gradient qualification differs')
        except Exception as error:
            if requested=='cuda':raise
            reason=str(error);gpu=None
    selected='cuda' if gpu and (requested=='cuda' or cpu['seconds']/max(gpu['seconds'],1e-12)>=1.15) else 'cpu'
    return {'requested':requested,'selected':selected,'device':gpu['device'] if selected=='cuda' else None,'cpu':cpu,'cuda':gpu,'automatic_cpu_reason':reason if not gpu else None,'source_backend':'cuda','backend_transfer':selected!='cuda','qualification_optimizer_steps':0,'scope':'Read-only energy-gradient qualification changes no optimizer state; independent CPU metrics/audits remain active. One backend is pinned across resolution branches.'}
