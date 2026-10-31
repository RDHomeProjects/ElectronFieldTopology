"""Projected Sobolev nonlinear conjugate gradients for a static functional.

The positive Dirichlet inverse (1-ell² Laplacian)^-1 preconditions directions;
it does not add a term to the objective or constrain the core's knot type.
"""
import numpy as np
from scipy.fft import dstn,idstn
from .skyrme import normalize,K


def minimize_static(engine,initial,maxiter,callback,expired,length=.5):
    u=initial.copy();n=len(u);h=engine.h;m=n-4
    k=np.arange(1,m+1)
    lam=4*np.sin(np.pi*k/(2*(m+1)))**2/h**2
    divisor=1+length**2*(lam[:,None,None]+lam[None,:,None]+lam[None,None,:])
    def projected(a):
        a-=u*np.sum(a*u,axis=-1,keepdims=True)
        for ax in range(3):
            sl=[slice(None)]*4;sl[ax]=[0,1,n-2,n-1];a[tuple(sl)]=0
        return a
    parts,g=engine.evaluate(u);energy=float(sum(parts));old_g=None;old_z=None;direction=None;alpha=.01
    evaluations=1
    for iteration in range(1,maxiter+1):
        if expired():return u,{'status':'time_budget','iterations':iteration-1,'evaluations':evaluations}
        g=projected(g/(K*h**3))
        z=np.zeros_like(g)
        z[2:-2,2:-2,2:-2]=idstn(dstn(g[2:-2,2:-2,2:-2],axes=(0,1,2),type=1,norm='ortho')/divisor[...,None],axes=(0,1,2),type=1,norm='ortho')
        z=projected(z)
        if old_g is None:beta=0.
        else:beta=max(0.,float(np.sum(g*(z-old_z))/max(float(np.sum(old_g*old_z)),1e-30)))
        direction=-z if direction is None else -z+beta*projected(direction)
        dot=float(np.sum(g*direction))*K*h**3
        if dot>=0:direction=-z;dot=-float(np.sum(g*z))*K*h**3
        maximum=float(np.max(np.linalg.norm(direction,axis=-1)))
        alpha=min(alpha*1.5,.1/max(maximum,1e-30))
        accepted=False
        for line in range(20):
            trial=normalize(u+alpha*direction)
            if float(np.max(np.linalg.norm(trial-u,axis=-1)))>min(.2,.5*engine.minimum_corner_cone):
                alpha*=.5;continue
            p,gg=engine.evaluate(trial);evaluations+=1
            e=float(sum(p))
            if engine.minimum_corner_cone>0 and e<=energy+1e-4*alpha*dot:accepted=True;break
            alpha*=.5
        if not accepted:return u,{'status':'line_search_limit','iterations':iteration-1,'evaluations':evaluations}
        old_g=g.copy();old_z=z.copy();u=trial;g=gg;energy=e
        callback(u,iteration)
        if np.sqrt(np.mean(old_g[2:-2,2:-2,2:-2]**2))<1e-3:
            return u,{'status':'gradient_stationary','iterations':iteration,'evaluations':evaluations}
    return u,{'status':'iteration_budget','iterations':maxiter,'evaluations':evaluations}
