import tempfile,time,platform
from pathlib import Path
import numpy as np
from scipy.fft import dstn
from .engine import Engine,dst_fft,checkpoint,restore
from .common import stamp,save,sha,memory_guard
def qualify():
 from electron_field_topology.sf_time import Grid
 from electron_field_topology.sf_candidate_seeds import sampled
 from electron_field_topology.sf_time_gpu import ArrayTime
 from electron_field_topology.sf_readmission import static_value_gradient
 rng=np.random.default_rng(1320);a=rng.normal(size=(9,11,13,3));err=float(np.max(abs(dst_fft(a,np)-dstn(a,axes=(0,1,2),type=1,norm='ortho'))));assert err<1e-12
 g=Grid((33,)*3,(12.,)*3,'fixed');seed=dict(id='control',q=3,family='axial',alpha=3,beta=1,scale=1.4,cutoff=4.5,bend=.1,amplitude=1.,perturbation=.005);n=sampled(g,seed);ec,gc=static_value_gradient(n,g);ep,gp=ArrayTime(np).static_value_gradient(n,g);assert abs(ep-ec)<1e-12 and np.max(abs(gc-gp))<1e-12
 d=rng.normal(size=n.shape);d-=n*np.sum(n*d,axis=-1,keepdims=True);d[g.fixed_mask()]=0;d/=np.linalg.norm(d);eps=1e-5;fd=(static_value_gradient(n+eps*d,g)[0]-static_value_gradient(n-eps*d,g)[0])/(2*eps);variation=float(np.sum(gc*d));assert abs(fd-variation)<1e-8
 engine=Engine('cpu');s=engine.state(n);start=ec
 for _ in range(5):assert engine.step(s,g)[0]
 assert engine.value(s['n'],g)[0]<start
 with tempfile.TemporaryDirectory() as tmp:
  p=Path(tmp)/'state.npz';checkpoint(p,s,engine,{'test':1});resumed=restore(p,engine,{'test':1});engine.step(s,g);engine.step(resumed,g);difference=float(np.max(abs(s['n']-resumed['n'])));assert difference==0
 return {'recorded_at':stamp(),'status':'host_qualification_passed','dst_odd_fft_vs_scipy_max':err,'arraytime_numpy_vs_cpu_gradient_max':float(np.max(abs(gc-gp))),'finite_variation_error':abs(fd-variation),'checkpoint_resume_max_difference':difference,'cuda_executed':False,'scope':'NumPy adapter tests are not CUDA qualification'}
def benchmark(repo,plan,out,backend='auto'):
 from electron_field_topology.sf_time import Grid
 from electron_field_topology.sf_candidate_seeds import sampled
 from electron_field_topology.sf_readmission import stationarity
 from .catalogue import catalogue
 memory_guard(plan['memory_min_available_gib']);out.mkdir(parents=True,exist_ok=False);gpu=None;unavailable=None;gpu_dst_error=None
 if backend!='cpu':
  try:gpu=Engine('cuda')
  except (ImportError,RuntimeError) as e:
   unavailable=str(e)
   if backend=='cuda':raise
 if gpu is not None:
  a=np.random.default_rng(1320).normal(size=(9,11,13,3));actual=gpu.host(dst_fft(gpu.xp.asarray(a),gpu.xp));gpu_dst_error=float(np.max(abs(actual-dstn(a,axes=(0,1,2),type=1,norm='ortho'))))
  if gpu_dst_error>1e-12:raise ValueError('Actual CUDA DST differs from independent SciPy reference')
 rows=[];seed=next(s for s in catalogue(plan) if s['q']==3 and s['family']=='axial')
 for nodes in plan['grids']:
  g=Grid((nodes,)*3,(plan['length'],)*3,'fixed');n=sampled(g,seed);results={};states={}
  for kind,engine in [('cpu',Engine('cpu'))]+([('cuda',gpu)] if gpu is not None else []):
   warm=engine.state(n);engine.value(warm['n'],g)
   if not engine.step(warm,g)[0]:raise ValueError('Benchmark warm-up optimizer stalled')
   engine.sync();del warm;s=engine.state(n);audit=engine.audit(s['n'],g);t=time.perf_counter()
   for _ in range(plan['benchmark_steps']):
    if not engine.step(s,g)[0]:raise ValueError('Benchmark optimizer stalled')
   engine.sync();step_seconds=(time.perf_counter()-t)/plan['benchmark_steps'];t=time.perf_counter();metrics=stationarity(engine.host(s['n']),g);audit_end=engine.audit(s['n'],g);diagnostic_seconds=time.perf_counter()-t
   t=time.perf_counter();checkpoint(out/f'bench-{nodes}-{kind}.npz',s,engine,{'nodes':nodes,'kind':kind});io_seconds=time.perf_counter()-t
   results[kind]={'mean_step_seconds':step_seconds,'diagnostics_and_audit_seconds':diagnostic_seconds,'checkpoint_seconds':io_seconds,'estimated_50_step_three_observation_seconds':50*step_seconds+3*(diagnostic_seconds+io_seconds),'initial_audit':audit,'endpoint_audit':audit_end};states[kind]=engine.host(s['n'])
  pair=None
  if gpu is not None:
   pair=float(np.max(abs(states['cpu']-states['cuda'])))
   if not np.allclose(states['cpu'],states['cuda'],rtol=2e-9,atol=2e-10):raise ValueError('CPU/CUDA short optimizer path differs beyond declared qualification tolerance')
  speed=results['cpu']['estimated_50_step_three_observation_seconds']/results['cuda']['estimated_50_step_three_observation_seconds'] if gpu is not None else None;choice='cuda' if gpu is not None and (backend=='cuda' or speed>=plan['gpu_speedup_required']) else 'cpu'
  rows.append({'nodes':nodes,'results':results,'cpu_cuda_field_max_difference':pair,'estimated_speedup':speed,'selected_backend':choice});print(__import__('json').dumps({'recorded_at':stamp(),'message':'Backend geometry qualified','nodes':nodes,'choice':choice,'estimated_speedup':speed}),flush=True)
 result={'recorded_at':stamp(),'status':'backend_qualification_passed','requested_backend':backend,'cuda_unavailable':unavailable,'cuda_dst_vs_scipy_max':gpu_dst_error,'cuda_identity':gpu.port.identity() if gpu is not None else None,'rows':rows,'scope':'50-step cost is an estimate from synchronized completed optimizer steps plus CPU audits and checkpoint timing; no whole-campaign speed promise'};save(out/'benchmark.json',result);return result
