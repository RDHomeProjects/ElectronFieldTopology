"""Same Coulomb-gauge Hopf quadrature with explicit per-axis lab spacings."""
import numpy as np
from scipy.fft import fftn,ifftn,fftfreq
def anisotropic_hopf(n,g):
 from electron_field_topology.skyrme import derivative,NORTH
 d=[derivative(n-NORTH,h,i) for i,h in enumerate(g.spacing)]
 b=np.stack([np.sum(n*np.cross(d[1],d[2]),axis=-1),np.sum(n*np.cross(d[2],d[0]),axis=-1),np.sum(n*np.cross(d[0],d[1]),axis=-1)],axis=-1)
 k=np.stack(np.meshgrid(*[2*np.pi*fftfreq(v,h) for v,h in zip(g.shape,g.spacing)],indexing='ij'),axis=-1);k2=np.sum(k*k,axis=-1);safe=np.where(k2>0,k2,1)
 bh=fftn(b,axes=(0,1,2));ah=1j*np.cross(k,bh)/safe[...,None];ah[k2==0]=0;a=ifftn(ah,axes=(0,1,2)).real
 return float(np.sum(a*b)*np.prod(g.spacing)/(16*np.pi**2))
