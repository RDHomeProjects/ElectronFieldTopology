import tempfile
from pathlib import Path
import numpy as np
from scipy.fft import dstn
from common import stamp,need
def qualify():
 from electron_field_topology.sf_time import Grid,step
 from electron_field_topology.sf_time_gpu import ArrayTime
 from electron_field_topology.sf_readmission import static_value_gradient
 from electron_field_topology.skyrme import rational_field,Energy,numpy_cell_energy
 from .engine import Engine,dst_fft,checkpoint,restore
 g=Grid((17,)*3,(12.,)*3,'fixed');n=rational_field(g.points(),alpha=1,beta=1,scale=1.4,cutoff=4.5);n[g.fixed_mask()]=[0,0,1]
 e,grad=static_value_gradient(n,g);ae,ag=ArrayTime(np).static_value_gradient(n,g);need(np.isclose(e,ae,rtol=1e-12,atol=1e-13) and np.allclose(grad,ag,rtol=1e-12,atol=1e-13),'Independent array-port static operator parity failed')
 rng=np.random.default_rng(1732);d=rng.normal(size=n.shape);d-=n*np.sum(n*d,axis=-1,keepdims=True);d[g.fixed_mask()]=0;d/=np.linalg.norm(d);eps=1e-5
 plus=n+eps*d;plus/=np.linalg.norm(plus,axis=-1,keepdims=True);minus=n-eps*d;minus/=np.linalg.norm(minus,axis=-1,keepdims=True)
 fd=(static_value_gradient(plus,g)[0]-static_value_gradient(minus,g)[0])/(2*eps);need(abs(fd-np.sum(grad*d))<1e-8,'Constrained D4 directional derivative failed')
 arr=rng.normal(size=(7,9,11,3));dst_error=float(np.max(abs(dst_fft(arr,np)-dstn(arr,axes=(0,1,2),type=1,norm='ortho'))));need(dst_error<1e-12,'DST preconditioner parity failed')
 with tempfile.TemporaryDirectory() as td:
  cell=Energy(17,g.spacing[0],Path(td)/'cell');parts,cg=cell.evaluate(n);ref=numpy_cell_energy(n,g.spacing[0]);need(np.allclose(parts,ref,rtol=1e-11,atol=1e-12),'Cell energy independent quadrature failed')
  engine=Engine('cpu');s=engine.state(n)
  for _ in range(3):need(engine.step(s,g)[0],'Optimizer control stalled')
  p=Path(td)/'state.npz';checkpoint(p,s,engine,{'control':1});b=restore(p,engine,{'control':1});engine.step(s,g);engine.step(b,g);need(np.array_equal(s['n'],b['n']),'Exact optimizer continuation control failed')
 geodesic=[]
 for dt in [.1,.05,.025]:
  gg=Grid((1,1,1),(2.,2.,2.),'periodic');nn=np.array([[[[0.,0.,1.]]]]);vv=np.array([[[[.7,0.,0.]]]])
  for i in range(round(.4/dt)):nn,vv,_=step(nn,vv,gg,dt,i*dt)
  geodesic.append(float(np.linalg.norm(nn-np.array([np.sin(.28),0,np.cos(.28)]))))
 orders=[float(np.log2(a/b)) for a,b in zip(geodesic,geodesic[1:])];need(min(orders)>3.8,'Closed-form temporal order control failed')
 return {'recorded_at':stamp(),'status':'host_instruments_passed','array_vs_cpu_energy_difference':abs(e-ae),'array_vs_cpu_gradient_max':float(np.max(abs(grad-ag))),'directional_derivative_error':abs(fd-float(np.sum(grad*d))),'dst_max_error':dst_error,'geodesic_orders':orders,'optimizer_checkpoint_resume':'bitwise equal','actual_cuda_executed':False,'scope':'Small independent instruments; retained field and actual-device qualification remain required'}
