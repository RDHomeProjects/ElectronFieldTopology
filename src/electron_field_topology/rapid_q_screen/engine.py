"""D4 static action adapter and the existing projected Sobolev-CG algorithm.

No cell-energy functional, damping in physical time, precision reduction or
CUDA-to-CPU fallback occurs within a branch. Apache-2.0.
"""
import os,time
from pathlib import Path
import numpy as np
from scipy.fft import dstn
from .common import canonical,sha,stamp,save

def dst_fft(a,xp):
 for axis in range(3):
  m=a.shape[axis];shape=list(a.shape);shape[axis]=2*(m+1);odd=xp.zeros(shape,dtype=xp.float64);sl=[slice(None)]*a.ndim;sl[axis]=slice(1,m+1);odd[tuple(sl)]=a;sl[axis]=slice(m+2,None);odd[tuple(sl)]=-xp.flip(a,axis=axis)
  transformed=xp.fft.fft(odd,axis=axis);sl[axis]=slice(1,m+1);a=-transformed[tuple(sl)].imag/xp.sqrt(2*(m+1))
 return a
class Engine:
 def __init__(self,kind='cpu'):
  from electron_field_topology.sf_readmission import static_value_gradient
  self.cpu_value=static_value_gradient;self.kind=kind
  if kind=='cuda':
   from electron_field_topology.sf_time_gpu import CUDATime
   self.port=CUDATime();self.xp=self.port.xp
  elif kind=='cpu':self.xp=np;self.port=None
  else:raise ValueError('Explicit cpu or cuda engine required')
 def host(self,a):return np.array(a,copy=True) if self.kind=='cpu' else self.xp.asnumpy(a)
 def sync(self):
  if self.kind=='cuda':self.xp.cuda.get_current_stream().synchronize()
 def value(self,n,g):return self.cpu_value(n,g) if self.kind=='cpu' else self.port.static_value_gradient(n,g)
 def cone(self,n):
  xp=self.xp;shape=tuple(v-1 for v in n.shape[:3]);total=xp.zeros(shape+(3,));parts=[]
  for bits in np.ndindex(2,2,2):
   piece=n[tuple(slice(b,b+s) for b,s in zip(bits,shape))];parts.append(piece);total+=piece
  size=xp.linalg.norm(total,axis=-1,keepdims=True)
  if float(xp.min(size))<1e-12:return -1.
  centre=total/size;return min(float(xp.min(xp.sum(v*centre,axis=-1))) for v in parts)
 def state(self,n):return {'n':self.xp.asarray(n,dtype=self.xp.float64).copy(),'old_g':None,'old_z':None,'direction':None,'alpha':1.,'iteration':0}
 def step(self,s,g):
  from electron_field_topology.skyrme import K
  xp=self.xp;n=s['n'];mask=xp.asarray(g.fixed_mask());vol=float(np.prod(g.spacing));interior=tuple(slice(2,-2) for _ in range(3))
  def tangent(a):
   a=a-n*xp.sum(n*a,axis=-1,keepdims=True);a[mask]=0;return a
  value,raw=self.value(n,g);gradient=tangent(raw/(2*K*vol));axes=[4*xp.sin(xp.pi*xp.arange(1,count-3)/(2*(count-3)))**2/h**2 for count,h in zip(g.shape,g.spacing)];symbol=.25+sum(xp.reshape(v,tuple(len(v) if i==j else 1 for i in range(3))) for j,v in enumerate(axes))
  transform=lambda a:dstn(a,axes=(0,1,2),type=1,norm='ortho') if self.kind=='cpu' else dst_fft(a,xp)
  z=xp.zeros_like(gradient);z[interior]=transform(transform(gradient[interior])/symbol[...,None]);z=tangent(z)
  if s['old_g'] is None:direction=-z
  else:
   coeff=max(0.,min(1.,float(xp.sum(gradient*(z-tangent(s['old_z']))))/max(float(xp.sum(s['old_g']*s['old_z'])),1e-30)));direction=-z+coeff*tangent(s['direction'])
  if float(xp.sum(direction*gradient))>=0:direction=-z
  slope=float(2*K*vol*xp.sum(gradient*direction));margin=self.cone(n)
  if margin<=0:raise ValueError('Representation cone failed before step')
  maximum=float(xp.max(xp.linalg.norm(direction,axis=-1)));alpha=min(s['alpha']*1.6,min(.15,.25*margin)/max(maximum,1e-30));accepted=False;calls=1
  for line in range(45):
   trial=n+alpha*direction;trial/=xp.linalg.norm(trial,axis=-1,keepdims=True);trial[mask]=xp.asarray([0.,0.,1.]);nextvalue,_=self.value(trial,g);calls+=1
   if np.isfinite(nextvalue) and nextvalue<=value+1e-4*alpha*slope:accepted=True;break
   alpha*=.5
  if not accepted or alpha*maximum<1e-14:return False,{'reason':'Armijo search stalled','objective_calls':calls}
  s.update(n=trial,old_g=gradient,old_z=z,direction=direction,alpha=alpha,iteration=s['iteration']+1)
  if s['iteration']%200==0:s.update(old_g=None,old_z=None,direction=None,alpha=1.)
  return True,{'energy':nextvalue,'objective_calls':calls,'accepted_step_max':alpha*maximum}
 def audit(self,n,g,rtol=2e-10,atol=2e-11):
  host=self.host(n);cpu_e,cpu_g=self.cpu_value(host,g);e,gradient=self.value(n,g);gpu_g=self.host(gradient)
  if not np.isclose(e,cpu_e,rtol=rtol,atol=atol) or not np.allclose(gpu_g,cpu_g,rtol=rtol,atol=atol):raise ValueError('Independent CPU D4 energy/gradient audit failed')
  return {'passed':True,'energy_abs_difference':abs(e-cpu_e),'gradient_max_abs_difference':float(np.max(abs(gpu_g-cpu_g))),'reference':'independent CPU sf_readmission.static_value_gradient'}
def checkpoint(path,s,engine,identity):
 p=Path(path);tmp=p.with_suffix('.tmp');p.parent.mkdir(parents=True,exist_ok=True);empty=np.empty((0,),np.float64)
 arrays={k:engine.host(s[k]) if s[k] is not None else empty for k in ['n','old_g','old_z','direction']};t=stamp()
 with tmp.open('wb') as f:
  np.savez_compressed(f,**arrays,alpha=np.float64(s['alpha']),iteration=np.int64(s['iteration']),next_observe=np.int64(s.get('next_observe',0)),observe_spacing=np.int64(s.get('observe_spacing',0)),identity_sha256=canonical(identity),backend=engine.kind,written_utc=t['utc'],written_melbourne=t['melbourne']);f.flush();os.fsync(f.fileno())
 tmp.replace(p);save(p.with_suffix('.seal.json'),{'recorded_at':t,'sha256':sha(p),'identity_sha256':canonical(identity)})
def restore(path,engine,identity):
 p=Path(path);seal=__import__('json').loads(p.with_suffix('.seal.json').read_text())
 if seal['sha256']!=sha(p) or seal['identity_sha256']!=canonical(identity):raise ValueError('Checkpoint seal or identity changed')
 with np.load(p,allow_pickle=False) as z:
  if str(z['identity_sha256'])!=canonical(identity) or str(z['backend'])!=engine.kind:raise ValueError('Checkpoint metadata/backend differs')
  s={'alpha':float(z['alpha']),'iteration':int(z['iteration']),'next_observe':int(z['next_observe']),'observe_spacing':int(z['observe_spacing'])}
  for k in ['n','old_g','old_z','direction']:
   a=z[k]
   if a.dtype!=np.float64 or not np.isfinite(a).all():raise ValueError('Invalid checkpoint precision/value')
   s[k]=engine.xp.asarray(a).copy() if a.size else None
 return s
