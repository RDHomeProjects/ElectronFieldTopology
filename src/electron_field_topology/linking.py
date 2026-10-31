"""Closed polygon Gauss linking and bounded field-line tracing; Apache-2.0."""
import numpy as np
from scipy.integrate import solve_ivp


def closed_curve(points):
    p=np.asarray(points,dtype=float)
    if p.ndim!=2 or p.shape[1]!=3 or len(p)<5 or not np.isfinite(p).all():
        raise ValueError('finite closed curve (N+1,3), N>=4 required')
    gap=float(np.linalg.norm(p[-1]-p[0]))
    if gap>1e-10:raise ValueError('open curve rejected; no artificial closure')
    p=p.copy();p[-1]=p[0]
    if np.any(np.linalg.norm(np.diff(p,axis=0),axis=1)<1e-12):raise ValueError('degenerate segment rejected')
    return p,gap


def segment_separation(a,b,self_pairs=False):
    """Minimum exact distance of polygon segments; exclude adjacent self pairs."""
    amin=np.inf;v=np.diff(b,axis=0)[None,:,:];c=np.sum(v*v,axis=-1)
    for start in range(0,len(a)-1,64):
        u=np.diff(a,axis=0)[start:start+64,None,:];w=a[start:start+len(u),None,:]-b[None,:-1,:]
        aa=np.sum(u*u,axis=-1);bb=np.sum(u*v,axis=-1);dd=np.sum(u*w,axis=-1);ee=np.sum(v*w,axis=-1)
        det=aa*c-bb*bb
        ss=np.divide(bb*ee-c*dd,det,out=np.zeros_like(det),where=det>1e-25)
        tt=np.divide(aa*ee-bb*dd,det,out=np.zeros_like(det),where=det>1e-25)
        def distance(s,t):return np.sum((w+s[...,None]*u-t[...,None]*v)**2,axis=-1)
        candidates=[distance(np.zeros_like(ee),np.clip(ee/c,0,1)),
            distance(np.ones_like(ee),np.clip((ee+bb)/c,0,1)),
            distance(np.clip(-dd/aa,0,1),np.zeros_like(dd)),
            distance(np.clip((bb-dd)/aa,0,1),np.ones_like(dd)),
            np.where((det>1e-25)&(ss>=0)&(ss<=1)&(tt>=0)&(tt<=1),distance(ss,tt),np.inf)]
        dist=np.minimum.reduce(candidates)
        if self_pairs:
            i=np.arange(start,start+len(u))[:,None];j=np.arange(len(b)-1)[None,:];n=len(a)-1
            dist=np.where((i==j)|((i-j)%n==1)|((j-i)%n==1),np.inf,dist)
        amin=min(amin,float(np.min(dist)))
    return float(np.sqrt(amin))


def gauss_link(first,second):
    a,gap_a=closed_curve(first);b,gap_b=closed_curve(second)
    separation=segment_separation(a,b);sa=segment_separation(a,a,True);sb=segment_separation(b,b,True)
    if min(separation,sa,sb)<1e-8:raise ValueError('intersecting or unresolved polygon curves rejected')
    da=np.diff(a,axis=0);db=np.diff(b,axis=0);ma=(a[:-1]+a[1:])/2;mb=(b[:-1]+b[1:])/2;total=0.
    for start in range(0,len(da),64):
        r=ma[start:start+64,None,:]-mb[None,:,:]
        total+=np.sum(np.sum(np.cross(da[start:start+64,None,:],db[None,:,:])*r,axis=-1)/np.linalg.norm(r,axis=-1)**3)
    return {'linking_integral':float(total/(4*np.pi)),'minimum_polygon_separation':separation,
        'minimum_nonadjacent_self_separation':min(sa,sb),'segments':[len(da),len(db)],'input_closure_gaps':[gap_a,gap_b]}


def trace_closed_line(field,seed,*,samples=256,tolerance=1e-10,max_step=.05,max_arclength=40):
    """Return-section closure of dr/ds=field/|field|; finite budget can fail.

    This does not apply periodic wrapping. Successful endpoints are snapped
    only after measured gap and tangent checks pass; the correction is recorded.
    """
    seed=np.asarray(seed,dtype=float)
    if seed.shape!=(3,) or not np.isfinite(seed).all() or not isinstance(samples,int) or not 16<=samples<=512 or not 1e-13<=tolerance<=1e-6 or not 0<max_step<=.2 or not 1<=max_arclength<=80:
        raise ValueError('invalid bounded trace settings')
    def direction(p):
        v=np.asarray(field(p),dtype=float)
        if v.shape!=(3,) or not np.isfinite(v).all() or not np.any(v):raise ValueError('field null or invalid trace field')
        scaled=v/np.max(np.abs(v))
        return scaled/np.linalg.norm(scaled)
    tangent=direction(seed)
    def rhs(s,p):return direction(p)
    departure=.05
    first=solve_ivp(rhs,(0,departure),seed,rtol=tolerance,atol=tolerance*.1,max_step=max_step,dense_output=True)
    def section(s,p):return np.dot(p-seed,tangent)
    section.direction=1;section.terminal=True
    second=solve_ivp(rhs,(departure,max_arclength),first.y[:,-1],rtol=tolerance,atol=tolerance*.1,max_step=max_step,events=section,dense_output=True)
    returned=bool(len(second.t_events[0]));length=float(second.t[-1]);last=second.y[:,-1]
    gap=float(np.linalg.norm(last-seed));mismatch=float(np.linalg.norm(direction(last)-tangent))
    closed=bool(first.success and second.success and returned and gap<1e-6 and mismatch<1e-6)
    s=np.linspace(0,length,samples+1);points=np.empty((samples+1,3));early=s<=departure
    points[early]=first.sol(s[early]).T;points[~early]=second.sol(s[~early]).T
    if closed:points[-1]=seed
    meta={'closed':closed,'section_returned':returned,'arclength':length,'closure_gap_before_correction':gap,
        'tangent_mismatch':mismatch,'endpoint_correction':gap if closed else 0.,'ode_success':bool(first.success and second.success),
        'function_evaluations':first.nfev+second.nfev,'samples':samples,'tolerance':tolerance,'max_step':max_step,
        'max_arclength':max_arclength,'seed':seed.tolist()}
    return points,meta
