"""Bounded holomorphic Bateman monomial candidates; Apache-2.0."""
from math import factorial,gcd
import numpy as np
from scipy.integrate import solve_ivp
from .fields import hopfion


def exponents(p,q):
    if any(isinstance(n,(bool,np.bool_)) or not isinstance(n,(int,np.integer)) or n<1 or n>5 for n in [p,q]):
        raise ValueError('positive integer exponents1..5 required; no singular/continuous powers')
    return int(p),int(q)


def coordinates(points,time=0.):
    x=np.asarray(points,dtype=float)
    if x.shape[-1:]!=(3,) or not np.isfinite(x).all() or np.iscomplexobj(time):raise ValueError('finite real points/time required')
    t=np.asarray(time,dtype=float)
    if not np.isfinite(t).all():raise ValueError('finite time required')
    shape=np.broadcast_shapes(x.shape[:-1],t.shape);x=np.broadcast_to(x,shape+(3,));t=np.broadcast_to(t,shape)
    r2=np.sum(x*x,axis=-1);d=r2-(t-1j)**2
    return (r2-t*t-1+2j*x[...,2])/d,2*(x[...,0]-1j*x[...,1])/d


def candidate(points,time,p,q):
    p,q=exponents(p,q);alpha,beta=coordinates(points,time);e,b=hopfion(points,time)
    factor=p*q*alpha**(p-1)*beta**(q-1)
    f=factor[...,None]*(e+1j*b)
    return f.real,f.imag


def potentials(points,time,p,q):
    p,q=exponents(p,q);x=np.asarray(points,dtype=float);alpha,beta=coordinates(x,time)
    d=np.sum(x*x,axis=-1)-(time-1j)**2;num=2*(x[...,0]-1j*x[...,1])
    grad_beta=(np.array([2,-2j,0])*d[...,None]-2*x*num[...,None])/d[...,None]**2
    v=(q*alpha**p*beta**(q-1))[...,None]*grad_beta
    return v.imag,v.real


def reference(p,q):
    p,q=exponents(p,q);h=2*np.pi**2*p*q*factorial(p)*factorial(q)/factorial(p+q);u=(p+q)*h
    return {'energy':float(u),'magnetic_helicity':float(h),'electric_helicity':float(h),'momentum':[0.,0.,float(-p*u/(p+q))]}


def catalogue(requests):
    """Policy rejection is distinct from mathematical invalidity."""
    rows=[]
    for pair in requests:
        if len(pair)!=2 or any(isinstance(n,bool) or not isinstance(n,int) or n<1 for n in pair):
            status='invalid_parameters';reason='positive integer powers required'
        elif max(pair)>3:status='deferred_budget';reason='regular monomial family, outside this catalogue budget'
        elif gcd(*pair)!=1:status='deferred_link_family';reason='valid noncoprime link family, outside current coprime-core catalogue'
        else:status='admitted';reason='within declared regular coprime family and budget'
        rows.append({'requested_pair':pair,'status':status,'reason':reason})
    return rows


def core_curve(theta,time,p,q,sign=1):
    """Published coprime core at t0, advected by the straight null flow.

    Return positions and analytic theta derivatives. These are parameterised
    reference curves; they are not output of the independent field-line ODE.
    """
    p,q=exponents(p,q)
    if gcd(p,q)!=1 or sign not in [-1,1]:raise ValueError('coprime core and sign±1 required')
    theta=np.asarray(theta,dtype=float)
    alpha=np.sqrt(p/(p+q))*np.exp(1j*q*theta)
    beta=np.sqrt(q/(p+q))*np.exp(-1j*p*theta+1j*(0 if sign==1 else -np.pi/q))
    aa=1-alpha.real;da=q*alpha.imag
    numerator=np.stack([beta.real,-beta.imag,alpha.imag],axis=-1)
    derivative=np.stack([p*beta.imag,p*beta.real,q*alpha.real],axis=-1)
    r=numerator/aa[...,None];dr=(derivative*aa[...,None]-numerator*da[...,None])/aa[...,None]**2
    x,y,z=np.moveaxis(r,-1,0);dx,dy,dz=np.moveaxis(dr,-1,0);d=1+np.sum(r*r,axis=-1);dd=2*np.sum(r*dr,axis=-1)
    n=np.stack([-2*(x*z-y),-2*(x+y*z),x*x+y*y-z*z-1],axis=-1)
    dn=np.stack([-2*(dx*z+x*dz-dy),-2*(dx+dy*z+y*dz),2*x*dx+2*y*dy-2*z*dz],axis=-1)
    return r+time*n/d[...,None],dr+time*(dn*d[...,None]-n*dd[...,None])/d[...,None]**2


def core_level(points,time,p,q):
    alpha,beta=coordinates(points,time)
    magnitude=(p/(p+q))**(p/2)*(q/(p+q))**(q/2)
    return alpha**p*beta**q,magnitude


def trace_core(p,q,time,sign,*,phase=.17,tolerance=1e-9,max_step=.15,max_arclength=80,samples=256):
    """Independent B-field ODE; scan section returns rather than accepting the first.

    A first section return need not complete a knot. All missed returns are
    retained; only a position-and-tangent-qualified return is closed.
    """
    p,q=exponents(p,q)
    if not 1e-12<=tolerance<=1e-6 or not 0<max_step<=.2 or not 1<=max_arclength<=80 or not isinstance(samples,int) or not 32<=samples<=512:raise ValueError('invalid bounded trace settings')
    seed,_=core_curve(phase,time,p,q,sign)
    def direction(x):
        b=candidate(x,time,p,q)[1];scale=np.max(np.abs(b))
        if not np.isfinite(b).all() or scale==0:raise ValueError('null/invalid field encountered')
        b=b/scale;return b/np.linalg.norm(b)
    initial=direction(seed)
    def rhs(s,x):return direction(x)
    departure=.05
    first=solve_ivp(rhs,(0,departure),seed,method='DOP853',rtol=tolerance,atol=tolerance*.1,max_step=max_step,dense_output=True)
    def section(s,x):return np.dot(x-seed,initial)
    section.direction=1
    rest=solve_ivp(rhs,(departure,max_arclength),first.y[:,-1],method='DOP853',rtol=tolerance,atol=tolerance*.1,max_step=max_step,events=section,dense_output=True)
    returns=[];accepted=None
    for arclength,x in zip(rest.t_events[0],rest.y_events[0]):
        gap=float(np.linalg.norm(x-seed));tangent=float(np.linalg.norm(direction(x)-initial))
        returns.append({'arclength':float(arclength),'closure_gap':gap,'tangent_mismatch':tangent})
        if accepted is None and gap<1e-6 and tangent<1e-6:accepted=returns[-1]
    closed=bool(first.success and rest.success and accepted is not None)
    length=accepted['arclength'] if closed else float(rest.t[-1]);s=np.linspace(0,length,samples+1);points=np.empty((samples+1,3));early=s<=departure
    points[early]=first.sol(s[early]).T;points[~early]=rest.sol(s[~early]).T
    value,mag=core_level(points,time,p,q)
    meta={'pair':[p,q],'time':time,'sign':sign,'seed_phase':phase,'closed':closed,'section_returns':returns,
        'accepted_return':accepted,'evaluated_arclength_budget':max_arclength,'accepted_arclength':length if closed else None,
        'tolerance':tolerance,'max_step':max_step,'samples':samples,'function_evaluations':first.nfev+rest.nfev,
        'max_core_level_relative_error':float(np.max(np.abs(value-sign*mag))/mag),
        'endpoint_correction':float(np.linalg.norm(points[-1]-seed)) if closed else 0.}
    if closed:points[-1]=seed
    return points,meta
