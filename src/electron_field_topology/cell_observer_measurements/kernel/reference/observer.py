"""Fixed physical observer and vector error decomposition; Apache-2.0."""
import numpy as np
from scipy.ndimage import map_coordinates
from .numerics import OFF_E,OFF_B,points,curl,evaluator,load_reference

def observe(native,offsets,target,h,length):
 arrays=[]
 for component,offset in zip(native,offsets):
  coordinates=np.moveaxis((target+length/2)/h-np.asarray(offset),-1,0)
  arrays.append(map_coordinates(component,coordinates,order=1,mode='nearest',prefilter=False))
 return np.stack(arrays,axis=-1)

def metrics(E,B_half,parameters,repo,observer_nodes=33):
 hopfion,_,_=load_reference(repo);p=parameters;n=p['nodes'];L=p['length'];h=L/n;T=p['duration'];dt=T/p['steps'];exact=evaluator(p['field'],hopfion,L,p.get('angle_degrees',0),p.get('rotation_code'))
 plus=B_half-dt*curl(E,h,True)
 ep=[points(n,L,o,2,0) for o in OFF_E];bp=[points(n,L,o,2,0) for o in OFF_B]
 if p['field']=='hopfion':
  guard=np.zeros((n,n,n),bool)
  for axis in range(3):
   s=[slice(None)]*3;s[axis]=[0,1,n-2,n-1];guard[tuple(s)]=True
  for i,v in enumerate(bp):plus[i][guard]=exact(v[guard],T+dt/2)[1][...,i]
 sync=.5*(B_half+plus)
 nodes=np.linspace(-2.,2.,observer_nodes);target=np.stack(np.meshgrid(nodes,nodes,nodes,indexing='ij'),-1)
 observed=np.stack([observe(E,OFF_E,target,h,L),observe(sync,OFF_B,target,h,L)],-1)
 exact_native_E=np.array([exact(v,T)[0][...,i] for i,v in enumerate(ep)]);exact_native_B=np.array([exact(v,T)[1][...,i] for i,v in enumerate(bp)])
 matched=np.stack([observe(exact_native_E,OFF_E,target,h,L),observe(exact_native_B,OFF_B,target,h,L)],-1)
 ref=np.stack(exact(target,T),-1);weight=np.ones(observer_nodes);weight[[0,-1]]=.5;w=weight[:,None,None]*weight[None,:,None]*weight[None,None,:]
 norm=lambda v:float(np.sum(w[...,None,None]*v*v));total=observed-ref;evolution=observed-matched;interpolation=matched-ref;den=max(norm(ref),1e-30)
 cross=float(2*np.sum(w[...,None,None]*evolution*interpolation)/den)
 return {'observer_nodes':observer_nodes,'observer_half_extent':2.,'observer_interpolation':'componentwise linear, fixed physical nodes; tensor nodal trapezoidal weights','evolution_observed_error':float(np.sqrt(norm(evolution)/den)),'observer_baseline_error':float(np.sqrt(norm(interpolation)/den)),'total_observed_error':float(np.sqrt(norm(total)/den)),'normalized_cross_term':cross,'vector_decomposition_closure':float(abs(norm(total)/den-(norm(evolution)/den+norm(interpolation)/den+cross))),'scope':'Vector differences share one observer and denominator. Scalar error norms are not additive; cancellation is explicitly retained. Observation-node refinement uses the same saved physical state.'}
