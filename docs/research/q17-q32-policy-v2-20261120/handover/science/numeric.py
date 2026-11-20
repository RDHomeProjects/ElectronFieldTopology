import gc,os,shutil,time
from pathlib import Path
import numpy as np
from common import ROOT,load,save,sha,canonical,stamp,log,need
from .engine import Engine,checkpoint,restore

def representation(m,q,p):
 return bool(all(np.isfinite(m[k]) for k in ['relative_force_l2','acceleration_max','hopf_integral','minimum_corner_cone','unit_error']) and abs(abs(m['hopf_integral'])-q)/q<=p['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<p['unit_limit'])
def stationary(m,q,p):return representation(m,q,p) and m['relative_force_l2']<=p['force_limit'] and m['acceleration_max']<=p['acceleration_limit']
def metrics(n,g,p):
 from electron_field_topology.sf_readmission import stationarity
 from electron_field_topology.sf_time import densities
 m=stationarity(n,g);d=densities(n,np.zeros_like(n),g)['energy_density'];total=float(np.sum(d));points=g.points()
 for name,width in [('tail_fraction',p['shell_width']),('guard_fraction',p['guard_width'])]:
  mask=np.any(abs(points)>=np.asarray(g.lengths)/2-width,axis=-1);m[name]=float(np.sum(d[mask])/max(total,1e-30))
 return m
def boundary(m,p):return m['tail_fraction']<=p['initial_tail_limit'] and m['guard_fraction']<=p['tail_guard_limit']
def resources(out,p):
 free=shutil.disk_usage(out).free/1024**3
 info=dict(x.split(':',1) for x in Path('/proc/meminfo').read_text().splitlines());ram=int(info['MemAvailable'].split()[0])/1024**2
 need(free>=p['disk_reserve_gib'],'Disk reserve reached; resume after freeing unrelated space, retained fields unchanged')
 need(ram>=p['host_reserve_gib'],'Host memory reserve reached; pause without deleting fields')
 return {'free_gib':free,'available_ram_gib':ram}

def qualify_geometry(g,p,out,requested):
 from .catalogue import field
 out.mkdir(parents=True,exist_ok=True);resources(out,p);receipt=out/'benchmark.json'
 if receipt.exists():
  r=load(receipt);need(r['requested']==requested and r['shape']==list(g.shape) and r['plan_sha256']==canonical(p),'Benchmark identity differs');return r
 seed=dict(id='benchmark-control',q=3,kind='axial',alpha=3,beta=1,scale=2.8,cutoff=8.8,amplitude=1.)
 n=field(g,seed);results={};states={};gpu=None;unavailable=None
 if requested!='cpu':
  try:
   gpu=Engine('cuda');gpu.xp.get_default_memory_pool().free_all_blocks();free,total=gpu.xp.cuda.runtime.memGetInfo()
   need(np.prod(g.shape)*p['gpu_memory_bytes_per_node']<free*.8,'Estimated CUDA reserve insufficient for this geometry')
  except Exception as e:
   unavailable=repr(e);gpu=None
   if requested=='cuda':raise RuntimeError('Forced CUDA cannot qualify this geometry: '+unavailable)
 for kind,e in [('cpu',Engine('cpu'))]+([('cuda',gpu)] if gpu is not None else []):
  try:
   warm=e.state(n);e.value(warm['n'],g);need(e.step(warm,g)[0],'Benchmark warm-up optimizer stalled');e.sync();del warm
   s=e.state(n);e.audit(s['n'],g,p['qualification_rtol'],p['qualification_atol']);start=time.perf_counter()
   for _ in range(p['benchmark_steps']):need(e.step(s,g)[0],'Optimizer benchmark stalled')
   e.sync();seconds=(time.perf_counter()-start)/p['benchmark_steps'];start=time.perf_counter();m=metrics(e.host(s['n']),g,p);e.audit(s['n'],g,p['qualification_rtol'],p['qualification_atol']);diagnostic=time.perf_counter()-start
   start=time.perf_counter();checkpoint(out/f'timing-{kind}.npz',s,e,{'benchmark':list(g.shape),'kind':kind});io=time.perf_counter()-start
   observations=int(np.ceil(50/p['observe_limits'][0]));results[kind]={'step_seconds':seconds,'cpu_observation_and_audit_seconds':diagnostic,'checkpoint_seconds':io,'assumed_observations_per_50_steps':observations,'estimated_50_step_cost':50*seconds+observations*(diagnostic+io)};states[kind]=e.host(s['n']);del s;gc.collect()
  except Exception as er:
   if kind=='cpu' or requested=='cuda':raise
   # Only resource unavailability permits skipping CUDA before a branch starts.
   if 'OutOfMemory' not in type(er).__name__ and 'out of memory' not in str(er).lower():raise
   unavailable=repr(er);gpu=None;results.pop('cuda',None);states.pop('cuda',None)
 if 'cuda' in states:
  need(np.allclose(states['cpu'],states['cuda'],rtol=2e-9,atol=2e-10),'CPU/CUDA short optimizer path parity failed; no fallback after numerical mismatch')
 speed=results['cpu']['estimated_50_step_cost']/results['cuda']['estimated_50_step_cost'] if 'cuda' in results else None
 choice='cuda' if 'cuda' in results and (requested=='cuda' or speed>=p['gpu_speedup_required']) else 'cpu'
 r={'recorded_at':stamp(),'status':'qualified','shape':list(g.shape),'lengths':list(g.lengths),'requested':requested,'selected_backend':choice,'results':results,'speedup_estimate':speed,'cuda_unavailable':unavailable,'cuda_identity':gpu.port.identity() if gpu is not None else None,'plan_sha256':canonical(p),'scope':'Synchronized measured local step, CPU audit and checkpoint cost; not a total-runtime promise'}
 save(receipt,r);log('Geometry qualified',shape=list(g.shape),backend=choice,estimated_speedup=speed);return r

def immutable_field(path,n,g,q,identity,iteration=0):
 if path.exists():
  seal=load(path.with_suffix('.json'));need(seal['identity']==canonical(identity) and sha(path)==seal['sha256'],'Retained field identity differs');return seal
 tmp=path.with_suffix('.tmp');path.parent.mkdir(parents=True,exist_ok=True)
 with tmp.open('wb') as f:np.savez_compressed(f,field=n,field_rate=np.zeros_like(n),h=g.spacing[0],expected_q=q,iteration=iteration,identity_sha256=canonical(identity),model_id='SF-relativistic-neutral-v1',scheme='D4-action-projected-RK4-v1');f.flush();os.fsync(f.fileno())
 tmp.replace(path);seal={'recorded_at':stamp(),'sha256':sha(path),'identity':canonical(identity),'iteration':iteration};save(path.with_suffix('.json'),seal);return seal

class Branch:
 def __init__(self,folder,g,seed,p,receipt,identity,initial=None):
  self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);self.g=g;self.seed=seed;self.p=p
  self.identity={**identity,'seed':seed,'shape':list(g.shape),'lengths':list(g.lengths),'backend':receipt['selected_backend']};self.engine=Engine(receipt['selected_backend'])
  if self.engine.kind=='cuda':need(self.engine.port.identity()==receipt['cuda_identity'],'CUDA runtime/device identity differs')
  self.history=load(self.folder/'history.json') if (self.folder/'history.json').exists() else []
  self.attempts=load(self.folder/'attempts.json')['attempts'] if (self.folder/'attempts.json').exists() else 0
  self.slot=0
  if (self.folder/'latest.json').exists():
   pointer=load(self.folder/'latest.json');self.slot=pointer['slot'];self.s=restore(self.folder/f'state-{self.slot}.npz',self.engine,self.identity)
   self.history=[h for h in self.history if h['iteration']<=self.s['iteration']]
   need(canonical(self.history)==pointer['history_sha256'],'Committed optimizer history differs from checkpoint pointer')
  else:
   from .catalogue import field
   self.s=self.engine.state(initial if initial is not None else field(g,seed));self.observe();self.persist()
   immutable_field(self.folder/'initial.npz',self.engine.host(self.s['n']),g,seed['q'],self.identity)
  if not self.history or self.history[-1]['iteration']!=self.s['iteration']:self.observe(recovered=True)
  self.plateaus=load(self.folder/'planner.json').get('plateau_count',0) if (self.folder/'planner.json').exists() else 0
 def observe(self,recovered=False):
  self.engine.sync();n=self.engine.host(self.s['n']);m=metrics(n,self.g,self.p);audit=self.engine.audit(self.s['n'],self.g,self.p['qualification_rtol'],self.p['qualification_atol'])
  row={'recorded_at':stamp(),'iteration':self.s['iteration'],'attempts':self.attempts,'optimizer_alpha':float(self.s['alpha']),'optimizer_memory_present':self.s['old_g'] is not None,'optimizer_epoch':self.s['iteration']//200,'recovered_checkpoint_observation':recovered,**m,'backend_audit':audit}
  if self.history and self.history[-1]['iteration']==row['iteration']:self.history[-1]=row
  else:self.history.append(row)
  save(self.folder/'history.json',self.history);log('Candidate observation',seed=self.seed['id'],nodes=self.g.shape[0],iteration=row['iteration'],attempts=self.attempts,force=m['relative_force_l2'],acceleration=m['acceleration_max']);return row
 def persist(self):
  # Write the inactive slot completely, then advance the atomic pointer.
  slot=1-self.slot;checkpoint(self.folder/f'state-{slot}.npz',self.s,self.engine,self.identity)
  save(self.folder/'latest.json',{'recorded_at':stamp(),'slot':slot,'iteration':self.s['iteration'],'identity':canonical(self.identity),'history_sha256':canonical(self.history)});self.slot=slot
 def batch(self,count,observe,total_budget):
  target=self.s['iteration']+count;next_observation=self.s['iteration']+observe;reason=None
  try:
   while self.s['iteration']<target and self.attempts<total_budget:
    if not representation(self.history[-1],self.seed['q'],self.p) or stationary(self.history[-1],self.seed['q'],self.p):break
    resources(self.folder,self.p);self.attempts+=1;save(self.folder/'attempts.json',{'recorded_at':stamp(),'attempts':self.attempts,'scope':'Every attempted optimizer step, including interrupted/replayed work, consumes budget'})
    accepted,step=self.engine.step(self.s,self.g)
    if not accepted:reason=step['reason'];break
    reset_observation=self.s['iteration']%200 in (199,0)
    if self.s['iteration']>=next_observation or self.s['iteration']==target or reset_observation:
     self.observe();self.persist();next_observation=self.s['iteration']+observe
     if self.s['iteration']%200==199:checkpoint(self.folder/f'before-reset-{self.s["iteration"]:05d}.npz',self.s,self.engine,self.identity)
     elif reset_observation:immutable_field(self.folder/f'after-reset-{self.s["iteration"]:05d}.npz',self.engine.host(self.s['n']),self.g,self.seed['q'],self.identity,self.s['iteration'])
   if self.history[-1]['iteration']!=self.s['iteration']:self.observe()
   self.persist()
  except BaseException:
   # Keyboard/resource stops preserve the latest fully accepted optimizer state.
   self.persist();raise
  return reason
 def result(self,status,reason=None):
  row=self.history[-1];terminal=self.folder/'endpoint.npz'
  # Endpoint is written only when the branch is terminal; never overwritten.
  if status!='active':immutable_field(terminal,self.engine.host(self.s['n']),self.g,self.seed['q'],self.identity,self.s['iteration'])
  r={'recorded_at':stamp(),'seed':self.seed,'q':self.seed['q'],'nodes':self.g.shape[0],'length':self.g.lengths[0],'backend':self.engine.kind,'iteration':self.s['iteration'],'attempts':self.attempts,'status':status,'reason':reason,'metrics':row,'strict_stationary':stationary(row,self.seed['q'],self.p),'boundary_admitted':boundary(row,self.p),'physical_Q_rejected':False,'identity':canonical(self.identity),'endpoint':str(terminal) if status!='active' else None,'checkpoint_sha256':sha(terminal) if terminal.exists() else None}
  save(self.folder/'result.json',r);save(self.folder/'result.seal.json',{'sha256':sha(self.folder/'result.json'),'identity':canonical(self.identity)});return r
