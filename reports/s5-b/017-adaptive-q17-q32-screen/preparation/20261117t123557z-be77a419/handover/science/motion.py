"""Conditional short coasting screens; unchanged seven physical screening gates."""
import gc,os,time
import numpy as np
from scipy.ndimage import map_coordinates
from common import save,load,sha,stamp,log,need,canonical
from .numeric import resources

def linear_reference(rest,rg,points):
 coordinates=np.moveaxis((points+np.asarray(rg.lengths)/2)/np.asarray(rg.spacing),-1,0)
 raw=np.stack([map_coordinates(rest[...,i]-[0,0,1][i],coordinates,order=1,mode='constant',cval=0,prefilter=False)+[0,0,1][i] for i in range(3)],axis=-1)
 norm=np.linalg.norm(raw,axis=-1,keepdims=True);need(np.min(norm)>1e-8,'Unresolved historical trilinear reference');return raw/norm
def fieldsave(path,n,v,identity,step,dt):
 tmp=path.with_suffix('.tmp')
 with tmp.open('wb') as f:np.savez_compressed(f,field=n,field_rate=v,identity_sha256=canonical(identity),step=step,dt=dt);f.flush();os.fsync(f.fileno())
 tmp.replace(path);save(path.with_suffix('.json'),{'recorded_at':stamp(),'sha256':sha(path),'identity':canonical(identity),'step':step})
def tail(n,v,g,width):
 from electron_field_topology.sf_time import densities
 e=densities(n,v,g)['energy_density'];mask=np.any(abs(g.points())>=np.array(g.lengths)/2-width,axis=-1)
 return float(np.sum(e[mask])/max(float(np.sum(e)),1e-30))

def run(rest,rg,q,folder,p,identity,requested,dt):
 from electron_field_topology.sf_time import Grid,step,diagnostics,acceleration
 from electron_field_topology.sf_reconstruction import boosted_cubic,sample_cubic
 from electron_field_topology.sf_time_initial import boosted_static
 from electron_field_topology.sf_readmission import cone
 from electron_field_topology.sf_time_gpu import CUDATime
 folder.mkdir(parents=True,exist_ok=True)
 input_identity=canonical({'source':identity,'rest_state':__import__('hashlib').sha256(rest.tobytes()).hexdigest(),'rest_shape':list(rg.shape),'rest_lengths':list(rg.lengths),'q':q,'dt':dt,'requested_backend':requested,'plan':p})
 if (folder/'result.json').exists():
  cached_result=load(folder/'result.json');need(cached_result['input_identity']==input_identity,'Cached motion source identity differs');need(sha(folder/'result.json')==load(folder/'result.seal.json')['sha256'],'Cached motion result checksum differs')
  if cached_result.get('final_sha256'):need(sha(folder/'final.npz')==cached_result['final_sha256'],'Retained final motion state differs')
  return cached_result
 m=p['motion'];beta=m['beta'];axis=m['axis'];gamma=1/np.sqrt(1-beta*beta);shape=list(rg.shape);shape[axis]=2*int(np.ceil((rg.shape[axis]-1)*gamma/2))+1
 g=Grid(tuple(shape),rg.lengths,'fixed');need(dt/min(g.spacing)<=.2,'Motion dt/h exceeds original bound')
 n,v=boosted_cubic(rest,rg,g,beta,axis);mask=g.fixed_mask();correction=max(float(np.max(abs(n[mask]-[0,0,1]))),float(np.max(abs(v[mask]))));n[mask]=[0,0,1];v[mask]=0
 points=g.points();points[...,axis]*=gamma;historical=linear_reference(rest,rg,points);oldn,_=boosted_static(rest,rg.spacing[0],g,beta,axis)
 need(np.allclose(historical,oldn,rtol=2e-11,atol=2e-12),'Historical trilinear reference implementation differs')
 shape_floor=float(np.linalg.norm(n-historical)/max(np.linalg.norm(historical-[0,0,1]),1e-30));future_points=g.points();future_points[...,axis]=gamma*(future_points[...,axis]-beta*m['duration']);future,fd=sample_cubic(rest,rg,future_points,axis);future_rate=-gamma*beta*fd
 admission={'fixed_projection_max':correction,'historical_shape_floor':shape_floor,'initial_tail':tail(n,v,g,p['shell_width']),'initial_guard':tail(n,v,g,p['guard_width']),'known_coasting_tail':tail(future,future_rate,g,p['shell_width'])}
 from .topology import anisotropic_hopf
 admission.update(hopf_integral=anisotropic_hopf(n,g),minimum_corner_cone=cone(n),unit_error=float(np.max(abs(np.linalg.norm(n,axis=-1)-1))),tangency_error=float(np.max(abs(np.sum(n*v,axis=-1)))))
 admitted=correction<1e-8 and shape_floor<=m['shape_relative'] and admission['initial_tail']<=p['initial_tail_limit'] and admission['initial_guard']<=p['tail_guard_limit'] and admission['known_coasting_tail']<=p['initial_tail_limit']
 admitted=admitted and abs(abs(admission['hopf_integral'])-q)/q<=p['charge_relative_error'] and admission['minimum_corner_cone']>0 and admission['unit_error']<p['unit_limit'] and admission['tangency_error']<p['unit_limit']
 save(folder/'admission.json',{'recorded_at':stamp(),'admitted':admitted,**admission})
 if not admitted:
  r={'recorded_at':stamp(),'status':'admission_rejected','admission':admission,'physical_Q_rejected':False,'input_identity':input_identity};save(folder/'result.json',r);save(folder/'result.seal.json',{'sha256':sha(folder/'result.json')});return r
 backend='cpu';port=None;backend_details={};qualification_identity=canonical({'source':identity,'shape':shape,'dt':dt,'rest':__import__('hashlib').sha256(rest.tobytes()).hexdigest()})
 cached=load(folder/'backend.json') if (folder/'backend.json').exists() else None
 if cached:
  need(cached['qualification_identity']==qualification_identity and cached['requested']==requested,'Motion backend qualification identity differs')
  backend=cached['backend'];backend_details=cached['details']
  if backend=='cuda':port=CUDATime();need(port.identity()==backend_details['device'],'Qualified motion CUDA runtime/device changed')
 elif requested!='cpu':
  try:port=CUDATime();free,_=port.xp.cuda.runtime.memGetInfo();need(np.prod(g.shape)*p['gpu_memory_bytes_per_node']<free*.75,'Motion CUDA memory reserve insufficient')
  except Exception as e:
   if requested=='cuda':raise
   port=None;backend_details['cuda_unavailable']=repr(e)
 if port is not None and cached is None:
  # Nonzero-velocity acceleration and RK4 parity are mandatory on this actual state.
  an,av=acceleration(n,v,g);gn,gv=port.upload(n,v);ga,gb=port.acceleration(gn,gv,g)
  need(np.allclose(port.host(ga),an,rtol=2e-9,atol=2e-10) and np.allclose(port.host(gb),av,rtol=2e-9,atol=2e-10),'Nonzero-rate CUDA acceleration parity failed')
  clock=time.perf_counter();cn,cv,_=step(n,v,g,dt);cpu=time.perf_counter()-clock
  port.synchronize();clock=time.perf_counter();nn,vv,_=port.step(gn,gv,g,dt);port.synchronize();gpu=time.perf_counter()-clock
  need(np.allclose(port.host(nn),cn,rtol=2e-9,atol=2e-10) and np.allclose(port.host(vv),cv,rtol=2e-9,atol=2e-10),'Nonzero-rate CUDA RK4 parity failed')
  backend_details.update(cpu_step_seconds=cpu,cuda_step_seconds=gpu,device=port.identity(),actual_nonzero_rate_parity=True)
  if requested=='cuda' or cpu/gpu>=p['gpu_speedup_required']:backend='cuda'
  else:port=None
  del an,av,ga,gb,cn,cv,nn,vv,gn,gv;gc.collect()
 if cached is None:save(folder/'backend.json',{'recorded_at':stamp(),'requested':requested,'backend':backend,'details':backend_details,'qualification_identity':qualification_identity})
 identity={**identity,'q':q,'shape':shape,'dt':dt,'backend':backend,'rest_state_sha256':__import__('hashlib').sha256(rest.tobytes()).hexdigest()};history=[];index=0
 if (folder/'latest.npz').exists():
  seal=load(folder/'latest.json');need(sha(folder/'latest.npz')==seal['sha256'] and seal['identity']==canonical(identity),'Motion checkpoint identity/seal differs')
  with np.load(folder/'latest.npz',allow_pickle=False) as z:n=z['field'].copy();v=z['field_rate'].copy();index=int(z['step'])
  history=[h for h in load(folder/'history.json') if h['step']<=index]
 if not history:
  d=diagnostics(n,v,g);history=[{'recorded_at':stamp(),'step':0,'time':0.,**d}];fieldsave(folder/'initial.npz',n,v,identity,0,dt)
 initial=history[0];status='screen_pass';reason=None;count=round(m['duration']/dt);every=round(m['observe_time']/dt)
 def observe(i,n,v):
  t=i*dt;d=diagnostics(n,v,g);points=g.points();points[...,axis]=gamma*(points[...,axis]-beta*t);ref=linear_reference(rest,rg,points);shape_error=float(np.linalg.norm(n-ref)/max(np.linalg.norm(ref-[0,0,1]),1e-30))
  # The historical Hopf diagnostic expects isotropic spacing. Re-evaluate the
  # anisotropic lab grid with the explicitly qualified per-axis implementation.
  from .topology import anisotropic_hopf
  hopf=anisotropic_hopf(n,g)
  d.update(shape_relative=shape_error,tail_fraction=tail(n,v,g,p['shell_width']),hopf_integral=hopf,minimum_corner_cone=cone(n))
  points_history=history+[{'time':t,'centroid':d['centroid']}];ts=np.array([r['time'] for r in points_history]);cs=np.array([r['centroid'][axis] for r in points_history]);speed=float(np.polyfit(ts,cs,1)[0]) if len(ts)>1 else 0.
  gates={'energy':abs(d['energy']/initial['energy']-1)<=m['energy_relative'],'momentum':np.linalg.norm(np.array(d['momentum'])-initial['momentum'])/initial['energy']<=m['momentum_scaled'],'shape':shape_error<=m['shape_relative'],'speed':abs(speed-beta)/beta<=m['speed_relative'],'tail':d['tail_fraction']<=m['tail_fraction'],'representation':abs(abs(hopf)-q)/q<=p['charge_relative_error'] and d['minimum_corner_cone']>0,'constraints':d['unit_error']<p['unit_limit'] and d['tangency_error']<p['unit_limit']}
  gates={k:bool(value) for k,value in gates.items()}
  return {'recorded_at':stamp(),'step':i,'time':t,**d,'speed':speed,'speed_relative':abs(speed-beta)/beta,'gates':gates}
 try:
  gn,gv=port.upload(n,v) if port else (None,None)
  for i in range(index+1,count+1):
   resources(folder,p)
   if port:
    gn,gv,_=port.step(gn,gv,g,dt,(i-1)*dt)
   else:n,v,_=step(n,v,g,dt,(i-1)*dt)
   if i%every==0 or i==count:
    if port:n,v=port.host(gn),port.host(gv)
    row=observe(i,n,v);history.append(row);save(folder/'history.json',history);fieldsave(folder/'latest.npz',n,v,identity,i,dt)
    milestone=any(abs(i*dt-t)<1e-10 for t in m['milestones'])
    if milestone:fieldsave(folder/f'milestone-t{round(i*dt*1000):04d}.npz',n,v,identity,i,dt)
    failed=[k for k,val in row['gates'].items() if not val and (k!='speed' or i*dt>=m['speed_stop_from_time'])]
    if row['tail_fraction']>m['runtime_tail_safety'] or not row['gates']['constraints'] or not row['gates']['representation'] or (milestone and failed):status='screen_failed';reason=failed or ['tail safety reserve'];break
    log('Motion observation',q=q,dt=dt,time=i*dt,backend=backend,shape=row['shape_relative'],speed_error=row['speed_relative'])
  fieldsave(folder/'final.npz',n,v,identity,history[-1]['step'],dt)
 except BaseException:raise  # Last sealed complete observation remains available.
 r={'recorded_at':stamp(),'status':status,'reason':reason,'backend':backend,'backend_qualification':backend_details,'identity':canonical(identity),'admission':admission,'dt':dt,'time':history[-1]['time'],'final':history[-1],'final_sha256':sha(folder/'final.npz'),'input_identity':input_identity,'physical_Q_rejected':False,'scope':'Short coasting screen, not long-time/continuum stability or electron acceptance'};save(folder/'result.json',r);save(folder/'result.seal.json',{'sha256':sha(folder/'result.json')});return r
