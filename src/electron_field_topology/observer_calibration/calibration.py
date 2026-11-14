"""Fixed-state quadrature controls. Apache-2.0; c=epsilon0=mu0=1.

No integration in physical time. Scalar norms share a denominator and are
never added to assert vector separation. Cell Gauss rules integrate each
component on its own interpolation cells, clipped to the same physical cube.
"""
import numpy as np
from scipy.ndimage import map_coordinates
from .reference.numerics import OFF_E,OFF_B,curl,evaluator,load_reference

RESPONSES=['evolution_observed_error','observer_baseline_error','total_observed_error']

def line_rule(nodes,half=2.,midpoint=False):
    if midpoint:
        step=2*half/nodes
        return -half+(np.arange(nodes)+.5)*step,np.full(nodes,step)
    x=np.linspace(-half,half,nodes);w=np.full(nodes,2*half/(nodes-1));w[[0,-1]]*=.5
    return x,w

def cell_rule(n,length,offset,order,half=2.):
    native=-length/2+(np.arange(n)+offset)*length/n
    knots=np.r_[-half,native[(native>-half)&(native<half)],half]
    z,w=np.polynomial.legendre.leggauss(order)
    widths=np.diff(knots)/2;centres=(knots[:-1]+knots[1:])/2
    return (centres[:,None]+widths[:,None]*z).ravel(),(widths[:,None]*w).ravel()

def sample(a,offset,target,h,length):
    q=np.moveaxis((target+length/2)/h-np.asarray(offset),-1,0)
    # The fixed observation cube lies strictly inside every native grid.
    if q.min() < -1e-10 or q.max()>a.shape[0]-1+1e-10:raise ValueError('Observer leaves native interpolation support')
    return map_coordinates(a,q,order=1,mode='nearest',prefilter=False)

def integrate_component(observed,native_exact,offset,exact,part,index,n,length,T,axes,chunk=4):
    (x,wx),(y,wy),(z,wz)=axes;sums=np.zeros(5)
    for start in range(0,len(x),chunk):
        xx=x[start:start+chunk];target=np.stack(np.meshgrid(xx,y,z,indexing='ij'),-1)
        w=wx[start:start+chunk,None,None]*wy[None,:,None]*wz[None,None,:]
        actual=sample(observed,offset,target,length/n,length)
        matched=sample(native_exact,offset,target,length/n,length)
        ref=exact(target,T)[part][...,index]
        evolution=actual-matched;baseline=matched-ref;total=actual-ref
        sums+=np.array([np.sum(w*evolution**2),np.sum(w*baseline**2),np.sum(w*total**2),2*np.sum(w*evolution*baseline),np.sum(w*ref**2)])
    return sums

def normalise(sums):
    ev,baseline,total,cross,den=map(float,sums)
    if not np.isfinite(sums).all() or den<=0:raise ValueError('Nonfinite or zero observation norm')
    return dict(zip(RESPONSES,[float(np.sqrt(max(ev,0)/den)),float(np.sqrt(max(baseline,0)/den)),float(np.sqrt(max(total,0)/den))]),normalized_cross_term=cross/den,vector_decomposition_closure=abs(total-ev-baseline-cross)/den,exact_norm_squared=den)

def prepare(E,B_half,p,repo,chunk=4):
    hopfion,_,_=load_reference(repo);n=p['nodes'];L=p['length'];T=p['duration'];dt=T/p['steps'];h=L/n
    if E.shape!=(3,n,n,n) or B_half.shape!=E.shape or E.dtype!=np.float64 or B_half.dtype!=np.float64:raise ValueError('Unexpected native array shape or precision')
    if not np.isfinite(E).all() or not np.isfinite(B_half).all():raise ValueError('Nonfinite saved state')
    exact=evaluator(p['field'],hopfion,L,p.get('angle_degrees',0),p.get('rotation_code'))
    plus=B_half-dt*curl(E,h,True)
    if p['field']=='hopfion':
        guard=np.zeros((n,n,n),bool)
        for axis in range(3):
            s=[slice(None)]*3;s[axis]=[0,1,n-2,n-1];guard[tuple(s)]=True
        for i,o in enumerate(OFF_B):
            indices=np.stack(np.nonzero(guard),-1);q=-L/2+(indices+np.array(o))*h
            plus[i][guard]=exact(q,T+dt/2)[1][...,i]
    synchronized=.5*(B_half+plus);del plus
    native=[]
    for part,offsets in enumerate([OFF_E,OFF_B]):
        family=[]
        for i,o in enumerate(offsets):
            a=np.empty((n,n,n),np.float64);lines=[-L/2+(np.arange(n)+v)*h for v in o]
            for start in range(0,n,chunk):
                q=np.stack(np.meshgrid(lines[0][start:start+chunk],lines[1],lines[2],indexing='ij'),-1)
                a[start:start+chunk]=exact(q,T)[part][...,i]
            family.append(a)
        native.append(family)
    return {'fields':[E,synchronized],'native':native,'exact':exact,'parameters':p}

def measure(state,nodes=None,order=None,midpoint=False,chunk=4):
    p=state['parameters'];n=p['nodes'];L=p['length'];sums=np.zeros(5)
    for part,offsets in enumerate([OFF_E,OFF_B]):
        for i,o in enumerate(offsets):
            axes=[cell_rule(n,L,v,order) for v in o] if order else [line_rule(nodes,midpoint=midpoint)]*3
            sums+=integrate_component(state['fields'][part][i],state['native'][part][i],o,state['exact'],part,i,n,L,p['duration'],axes,chunk)
    r=normalise(sums)
    if r['vector_decomposition_closure']>1e-12:raise ValueError('Vector decomposition closure failed')
    return {'method':'cell-gauss' if order else 'midpoint' if midpoint else 'trapezoid','order':order,'observer_nodes':nodes,**r}

def max_change(a,b):return max(abs(a[k]-b[k]) for k in RESPONSES)

def next_resolution(rows,budget,maximum,reserved):
    """Refine faster when unresolved changes/curvature are large; never fixed intervals."""
    last=rows[-1]['observer_nodes'];delta=max_change(rows[-1],rows[-2]);curvature=0.
    if len(rows)>2:
        slope1=(rows[-1][RESPONSES[0]]-rows[-2][RESPONSES[0]])/(rows[-1]['observer_nodes']-rows[-2]['observer_nodes'])
        slope0=(rows[-2][RESPONSES[0]]-rows[-3][RESPONSES[0]])/(rows[-2]['observer_nodes']-rows[-3]['observer_nodes'])
        curvature=abs(slope1-slope0)*(last-rows[-2]['observer_nodes'])
    factor=1.65 if max(delta,curvature)>10*budget else 1.4 if max(delta,curvature)>budget else 1.2
    target=min(maximum,int(np.ceil((last-1)*factor))+1)
    available=[v for v in range(last+1,maximum+1) if v not in reserved]
    if not available:return None
    chosen=min(available,key=lambda v:abs(v-target))
    return {'observer_nodes':chosen,'last_metric_change':delta,'curvature_indicator':curvature,'growth_factor':factor,'reason':'bounded refinement from measured residual and local slope change; reserved counts excluded'}
