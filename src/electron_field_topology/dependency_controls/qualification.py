"""Independent manufactured controls; no candidate scientific gate; Apache-2.0."""
import numpy as np
from .numerics import packet,points,curl,divergence,load_reference,relative
from .dependencies import fit_models,predict,choose

def qualify(repo):
    _,FourierMaxwell,_=load_reference(repo);checks={}
    n=17;L=8.;h=L/n;p=points(n,L,(.5,.5,.5),2,0.);e,b=packet(p,0,L);solver=FourierMaxwell(e,b,h,project=False);u0=solver.energy();solver.advance(1.);ef,bf=solver.fields();er,br=packet(p,1.,L)
    err=relative(np.stack([ef,bf],-1),np.stack([er,br],-1));energy=abs(solver.energy()/u0-1)
    checks['fourier_multimode']={'relative_error':err,'energy_drift':energy,'divergence_max':solver.divergence_max(),'pass':bool(err<1e-11 and energy<1e-11 and solver.divergence_max()<1e-10)}
    # Independent discrete travelling-wave solution, including Yee phase shift.
    dt=.03;steps=30;k=2*np.pi/L;omega=2/dt*np.arcsin(dt/h*np.sin(k*h/2));xe=points(n,L,(0,.5,0),2,0.)[...,0];xb=points(n,L,(.5,.5,0),2,0.)[...,0]
    e=np.zeros((3,n,n,n));b=np.zeros_like(e);e[1]=np.cos(k*xe);b[2]=np.cos(k*xb+omega*dt/2);initial=.5*np.sum(e*e+b*(b-dt*curl(e,h,True)))
    d0=divergence(e,b,h)
    for _ in range(steps):b-=dt*curl(e,h,True);e+=dt*curl(b,h,False)
    plus=b-dt*curl(e,h,True);sync=.5*(b+plus);T=steps*dt
    wave=max(float(np.max(abs(e[1]-np.cos(k*xe-omega*T)))),float(np.max(abs(b[2]-np.cos(k*xb-omega*(T-dt/2))))))
    sync_error=float(np.max(abs(sync[2]-np.cos(omega*dt/2)*np.cos(k*xb-omega*T))))
    invariant=abs(.5*np.sum(e*e+b*plus)/initial-1);dg=max(float(np.max(abs(a-c))) for a,c in zip(divergence(e,b,h),d0))
    checks['discrete_yee_wave']={'native_max_error':wave,'synchronization_formula_error':sync_error,'modified_energy_drift':float(invariant),'divergence_change':dg,'pass':bool(max(wave,sync_error,invariant,dg)<1e-11)}
    # Independently differentiate the manufactured field; no update stencil.
    rng=np.random.default_rng(317);q=rng.uniform(-2,2,(13,3));delta=1e-5;t=.37
    derivatives=[]
    for axis in range(3):
        shift=np.eye(3)[axis]*delta;f1=packet(q+shift,t);f0=packet(q-shift,t);derivatives.append(tuple((a-b)/(2*delta) for a,b in zip(f1,f0)))
    ce=np.stack([derivatives[1][0][:,2]-derivatives[2][0][:,1],derivatives[2][0][:,0]-derivatives[0][0][:,2],derivatives[0][0][:,1]-derivatives[1][0][:,0]],-1)
    cb=np.stack([derivatives[1][1][:,2]-derivatives[2][1][:,1],derivatives[2][1][:,0]-derivatives[0][1][:,2],derivatives[0][1][:,1]-derivatives[1][1][:,0]],-1)
    f1=packet(q,t+delta);f0=packet(q,t-delta);et,bt=[(a-b)/(2*delta) for a,b in zip(f1,f0)];res=max(float(np.max(abs(et-cb))),float(np.max(abs(bt+ce))))
    checks['manufactured_maxwell_pde']={'central_difference_residual':res,'pass':bool(res<1e-7)}
    # Separate fit/acquisition controls: known quadratic and cubic inflection.
    rows=[{'x':x,'y':.01+.003*(x-.4)**2} for x in [0,.2,.7,1.]];m=fit_models(rows)[0];err=float(np.max(abs(predict(m,np.array([.1,.4,.8]))-(.01+.003*(np.array([.1,.4,.8])-.4)**2))))
    opts={'accuracy_budget_fraction':None};selection=choose(rows,[{'x':i/100,'level':i} for i in range(1,100) if i not in [20,70]],opts)
    checks['adaptive_relationship']={'model':m['model'],'validation_error':err,'selected_x':selection['x'],'reason':selection['reason'],'pass':bool(m['model']=='quadratic' and err<1e-12 and abs(selection['x']-.4)<.03)}
    from .dependencies import features
    cr=[{'x':x,'y':1+x**3} for x in [-1.,-.6,-.2,.2,.6,1.]];fs=features(cr,fit_models(cr)[0]);checks['inflection_detection']={'features':fs,'pass':any(k=='possible_inflection' and abs(v)<.21 for k,v in fs)}
    return {'status':'qualification_passed' if all(c['pass'] for c in checks.values()) else 'qualification_failed','checks':checks,'scope':'Manufactured software/numerical controls, not a physical candidate admission.'}
