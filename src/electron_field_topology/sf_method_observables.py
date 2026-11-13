"""Shared directional observable calculation; native and D4 common observers.
No trajectory fitting; separate native H balance from common density diagnostics.
"""
import numpy as np
K=1/(32*np.pi**2*np.sqrt(2));NORTH=np.array([0.,0.,1.])
def rates(n,v,ndot,a,g,spatial,sigma_rate):
    d=spatial.gradients(n-NORTH,g);b=spatial.gradients(ndot,g)
    r=np.sum(v*a,-1)+np.sum(d*b,axis=(-2,-1))
    for i in range(3):r+=np.sum(np.cross(v,d[...,i,:])*(np.cross(a,d[...,i,:])+np.cross(v,b[...,i,:])),-1)
    for i,j in [(0,1),(0,2),(1,2)]:r+=np.sum(np.cross(d[...,i,:],d[...,j,:])*(np.cross(b[...,i,:],d[...,j,:])+np.cross(d[...,i,:],b[...,j,:])),-1)
    rd=2*K*r;hd=rd+K*(sigma_rate(n,ndot,g)-2*np.sum(d*b,axis=(-2,-1)));return rd,hd

def evaluate(n,v,ndot,a,g,spatial,sigma_rate,probe=False):
    rd,hd=rates(n,v,ndot,a,g,spatial,sigma_rate);data=spatial.densities(n,v,g);rho=data['energy_density'];ham=data['hamiltonian_density'];flux=data['energy_flux'];del data
    dv=float(np.prod(g.spacing));e=float(np.sum(rho)*dv);he=float(np.sum(ham)*dv);ed=float(np.sum(rd)*dv);hed=float(np.sum(hd)*dv)
    axes=[];cent=[];velocity=[]
    for i,(count,h,l) in enumerate(zip(g.shape,g.spacing,g.lengths)):
        shape=[1]*3;shape[i]=count;x=(-l/2+np.arange(count)*h).reshape(shape);axes.append(x);c=float(np.sum(x*rho)*dv/e);cent.append(c);velocity.append(float(np.sum((x-c)*rd)*dv/e))
    p=np.sum(flux,axis=(0,1,2))*dv;div=sum(spatial.derivative(flux[...,i],h,i,g.boundary) for i,h in enumerate(g.spacing));res=rd+div
    moment=np.array([np.sum((axes[i]-cent[i])*res)*dv/e for i in range(3)]);summation=np.array([np.sum((axes[i]-cent[i])*(-div))*dv/e for i in range(3)])-p/e;closure=np.array(velocity)-p/e-moment-summation
    if max(abs(closure))>1e-10:raise ValueError('Moment decomposition failed')
    result={'continuum_energy':e,'continuum_energy_rate':ed,'hamiltonian':he,'hamiltonian_rate':hed,'centroid':cent,'centroid_rate':velocity,'momentum':p.tolist(),'momentum_over_continuum_energy':(p/e).tolist(),'weighted_continuity_residual_over_energy':moment.tolist(),'discrete_summation_term':summation.tolist(),'moment_closure':closure.tolist(),'continuity_residual_physical_l2':float(np.sqrt(np.sum(res*res)*dv))}
    if probe:
        eps=2.5e-5;plus=spatial.densities(n+eps*ndot,v+eps*a,g);minus=spatial.densities(n-eps*ndot,v-eps*a,g)
        er=(plus['energy_density']-minus['energy_density'])/(2*eps);hr=(plus['hamiltonian_density']-minus['hamiltonian_density'])/(2*eps)
        result['density_directional_probe']={'epsilon':eps,'continuum_absolute_rms':float(np.sqrt(np.mean((er-rd)**2))),'hamiltonian_absolute_rms':float(np.sqrt(np.mean((hr-hd)**2)))}
        if max(result['density_directional_probe'][k] for k in ['continuum_absolute_rms','hamiltonian_absolute_rms'])>1e-8:raise ValueError('Density derivative probe failed')
    return result
