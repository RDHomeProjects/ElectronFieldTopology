"""Analytical and independently manufactured controls for SF time evolution."""
import numpy as np


def wave(points, t, lengths, modes, offset=0.):
    """Exact continuum great-circle waves; no forcing or numerical stepping here."""
    theta = np.full(points.shape[:-1],offset);rate = np.zeros_like(theta)
    for mode in modes:
        k = 2*np.pi*np.asarray(mode['wave_numbers'])/np.asarray(lengths)
        omega = np.linalg.norm(k);phase = points@k-omega*t+mode.get('phase',0.)
        theta += mode['amplitude']*np.cos(phase)
        rate += mode['amplitude']*omega*np.sin(phase)
    n = np.stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1)
    v = np.stack((np.cos(theta)*rate,np.zeros_like(theta),-np.sin(theta)*rate),axis=-1)
    return n,v


def pulse(points, t, amplitude=.3, centre=-3., radius=1.5, axis=0):
    """Compact C7 1D right-moving great-circle pulse, valid before wall return."""
    x = points[...,axis]-t-centre;inside = abs(x)<radius
    phase = np.pi*x/(2*radius);theta = np.where(inside,amplitude*np.cos(phase)**8,0.)
    rate = np.where(inside,8*amplitude*np.pi/(2*radius)*np.cos(phase)**7*np.sin(phase),0.)
    n = np.stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1)
    v = np.stack((np.cos(theta)*rate,np.zeros_like(theta),-np.sin(theta)*rate),axis=-1)
    return n,v


def angle_jets(points,t,kind):
    """Explicit four-coordinate sine jets. x0=t, metric +---, length=2pi."""
    if kind=='theta': offset=1.1;modes=[(.12,[-.7,1.,0.,0.],.2),(.08,[.4,0.,0.,1.],.7)]
    else: offset=0.;modes=[(.17,[.9,0.,1.,0.],.3),(.09,[-.3,1.,0.,1.],-.4)]
    value=np.full(points.shape[:-1],offset);d=np.zeros(points.shape[:-1]+(4,));h=np.zeros(points.shape[:-1]+(4,4))
    for amplitude,vector,phase in modes:
        w=np.array(vector);arg=w[0]*t+points@w[1:]+phase
        value+=amplitude*np.sin(arg);d+=amplitude*np.cos(arg)[...,None]*w
        h-=amplitude*np.sin(arg)[...,None,None]*np.outer(w,w)
    return value,d,h


def manufactured(points,t,with_acceleration=False):
    theta,a,ha=angle_jets(points,t,'theta');phi,b,hb=angle_jets(points,t,'phi')
    s=np.sin(theta);c=np.cos(theta);cp=np.cos(phi);sp=np.sin(phi)
    n=np.stack((s*cp,s*sp,c),axis=-1);et=np.stack((c*cp,c*sp,-s),axis=-1)
    ep=np.stack((-sp,cp,np.zeros_like(sp)),axis=-1)
    v=et*a[...,0,None]+s[...,None]*ep*b[...,0,None]
    if not with_acceleration:return n,v
    npp=np.stack((-s*cp,-s*sp,np.zeros_like(s)),axis=-1)
    acc=et*ha[...,0,0,None]+s[...,None]*ep*hb[...,0,0,None]-n*a[...,0,None]**2
    acc+=2*c[...,None]*ep*a[...,0,None]*b[...,0,None]+npp*b[...,0,None]**2
    return n,v,acc


def manufactured_force(points,t):
    """Independent angle-coordinate EL source, not a call to the numerical RHS.

    L/K = X+sin(theta)^2*((1-X)*Y+Z^2); X=theta_mu theta^mu,
    Y=phi_mu phi^mu, Z=theta_mu phi^mu. Source is divided by 2K.
    """
    theta,a,ha=angle_jets(points,t,'theta');phi,b,hb=angle_jets(points,t,'phi')
    eta=np.array([1.,-1.,-1.,-1.]);au=a*eta;bu=b*eta
    x=np.sum(a*au,axis=-1);y=np.sum(b*bu,axis=-1);z=np.sum(a*bu,axis=-1)
    dx=2*np.einsum('...mn,...n->...m',ha,au);dy=2*np.einsum('...mn,...n->...m',hb,bu)
    dz=np.einsum('...mn,...n->...m',ha,bu)+np.einsum('...mn,...n->...m',hb,au)
    boxa=np.einsum('...ii,i->...',ha,eta);boxb=np.einsum('...ii,i->...',hb,eta)
    s=np.sin(theta);c=np.cos(theta);ss=s*s;dss=2*(s*c)[...,None]*a
    ac=1-ss*y;dac=-dss*y[...,None]-ss[...,None]*dy
    bc=ss*z;dbc=dss*z[...,None]+ss[...,None]*dz
    cc=ss*(1-x);dcc=dss*(1-x)[...,None]-ss[...,None]*dx
    etheta=ac*boxa+np.sum(dac*au,axis=-1)+bc*boxb+np.sum(dbc*bu,axis=-1)
    etheta-=s*c*((1-x)*y+z*z)
    ephi=cc*boxb+np.sum(dcc*bu,axis=-1)+bc*boxa+np.sum(dbc*au,axis=-1)
    et=np.stack((c*np.cos(phi),c*np.sin(phi),-s),axis=-1)
    ep=np.stack((-np.sin(phi),np.cos(phi),np.zeros_like(phi)),axis=-1)
    return etheta[...,None]*et+(ephi/s)[...,None]*ep
