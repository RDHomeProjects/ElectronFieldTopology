"""Generic preimages of a piecewise linear unit-vector field.

Kuhn tetrahedra agree on shared faces. Closed components require degree-two
face adjacency; ambiguous/boundary components are rejected, never joined by eye.
Optional SnapPy/Spherogram identifies the resulting finite polygon diagrams.
"""
from itertools import permutations,combinations
import numpy as np
from .knot_diagram import crossings,VIEWS


def canonical_gauss(link):
    """Diagram equality after cyclic relabelling/reversal, not a universal invariant."""
    if len(link.link_components)!=1:return None
    entries=[(id(e.crossing),bool(e.is_over_crossing()),int(e.crossing.sign)) for e in link.link_components[0]]
    candidates=[]
    for sequence in [entries,entries[::-1]]:
        for offset in range(len(sequence)):
            mapping={};word=[]
            for label,over,sign in sequence[offset:]+sequence[:offset]:
                if label not in mapping:mapping[label]=len(mapping)
                word.append((mapping[label],int(over),sign))
            candidates.append(tuple(word))
    return min(candidates) if candidates else ()


def jones_a(link,max_crossings=18):
    """Exact integer Kauffman state sum in A, writhe-normalised. Not unique."""
    from math import comb
    pd=link.PD_code();m=len(pd)
    if not m:return {'0':1}
    if m>max_crossings:raise ValueError('Jones state-sum budget')
    states={}
    for state in range(1<<m):
        parent=list(range(2*m))
        def root(a):
            while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
            return a
        for i,(a,b,c,d) in enumerate(pd):
            pairs=[(a,b),(c,d)] if (state>>i)&1 else [(a,d),(b,c)]
            for x,y in pairs:parent[root(x)]=root(y)
        loops=len({root(i) for i in range(2*m)})
        exponent=2*state.bit_count()-m
        states[(exponent,loops)]=states.get((exponent,loops),0)+1
    poly={};w=sum(c.sign for c in link.crossings)
    for (exponent,loops),count in states.items():
        power=loops-1
        for j in range(power+1):
            a=exponent+2*power-4*j-3*w
            poly[a]=poly.get(a,0)+count*comb(power,j)*(-1)**(power+w)
    return {str(a):int(c) for a,c in sorted(poly.items()) if c}


def cable_reference(count=384):
    """Eq. 3.7 polynomial parameter t -> (t^4,t^6+.5t^3) intersected with S3."""
    from scipy.optimize import brentq
    theta=np.linspace(.017,2*np.pi+.017,count+1);points=[]
    for angle in theta:
        radius=brentq(lambda r:r**8+r**12+.25*r**6+r**9*np.cos(3*angle)-1,.01,2.)
        t=radius*np.exp(1j*angle);z1=t**4;z0=t**6+.5*t**3
        points.append(np.array([z1.real,z1.imag,z0.imag])/(1-z0.real))
    points=np.array(points);points[-1]=points[0];return points


def preimages(field,h,target=(.000007,.000011,-1.),max_tetrahedra=300000):
    n=len(field);target=np.asarray(target,dtype=float);target/=np.linalg.norm(target)
    u=np.cross(target,np.eye(3)[np.argmin(abs(target))]);u/=np.linalg.norm(u);v=np.cross(target,u)
    values=np.stack([field@u,field@v,field@target],axis=-1)
    corners=list(np.ndindex(2,2,2))
    lo=np.full((n-1,n-1,n-1,2),np.inf);hi=-lo.copy();south=np.zeros((n-1,n-1,n-1),bool)
    for offset in corners:
        a=values[tuple(slice(o,o+n-1) for o in offset)]
        lo=np.minimum(lo,a[...,:2]);hi=np.maximum(hi,a[...,:2]);south|=a[...,2]>0
    cells=np.argwhere(np.all(lo<=0,axis=-1)&np.all(hi>=0,axis=-1)&south)
    tetra=[]
    for perm in permutations(range(3)):
        off=np.zeros((4,3),int)
        for j,k in enumerate(perm):off[j+1]=off[j];off[j+1,k]=1
        tetra.append(cells[:,None,:]+off)
    tetra=np.concatenate(tetra,axis=0)
    if len(tetra)>max_tetrahedra:raise ValueError('preimage tetrahedron budget')
    vert=values[tuple(tetra[...,i] for i in range(3))]
    mask=np.all(np.min(vert[...,:2],axis=1)<=0,axis=-1)&np.all(np.max(vert[...,:2],axis=1)>=0,axis=-1)
    tetra=tetra[mask];vert=vert[mask]
    hits={};points={};adj={};ambiguous=0
    for face in combinations(range(4),3):
        fv=vert[:,face,:];matrix=np.stack([fv[:,:,0],fv[:,:,1],np.ones((len(fv),3))],axis=1)
        good=abs(np.linalg.det(matrix))>1e-13
        ids=np.where(good)[0];weights=np.linalg.solve(matrix[good],np.broadcast_to([0.,0.,1.],(len(ids),3))[...,None])[...,0]
        ok=(np.min(weights,axis=1)>-1e-9)&(np.max(weights,axis=1)<1+1e-9)&(np.sum(weights*fv[good,:,2],axis=1)>0)
        for tid,w in zip(ids[ok],weights[ok]):
            vertices=tetra[tid,list(face),:]
            key=tuple(sorted((vertices[:,0]*n*n+vertices[:,1]*n+vertices[:,2]).tolist()))
            point=(w@vertices-(n-1)/2)*h
            if key in points and np.linalg.norm(points[key]-point)>1e-7*h:raise ValueError('inconsistent shared-face interpolation')
            points[key]=point;hits.setdefault(int(tid),[]).append(key)
    for keys in hits.values():
        if len(keys)!=2 or keys[0]==keys[1]:ambiguous+=1;continue
        a,b=keys;adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    if ambiguous or any(len(set(neighbours))!=2 for neighbours in adj.values()):
        return {'status':'unresolved_adjacency','ambiguous_tetrahedra':ambiguous,'vertices':len(adj),'curves':[],'target':target.tolist()}
    unused=set(adj);curves=[]
    while unused:
        start=min(unused);path=[start];prev=None;current=start
        while True:
            unused.discard(current);nexts=sorted(set(adj[current]));nxt=nexts[0] if nexts[0]!=prev else nexts[1]
            if nxt==start:break
            if nxt not in unused:raise ValueError('preimage component joins itself inconsistently')
            path.append(nxt);prev,current=current,nxt
        curves.append(np.array([points[k] for k in path]+[points[start]]))
    return {'status':'closed_components' if curves else 'no_preimage','components':len(curves),
            'vertices':sum(len(c)-1 for c in curves),'curves':curves,'target':target.tolist()}


def resample(curve,count=384):
    steps=np.linalg.norm(np.diff(curve,axis=0),axis=1);s=np.r_[0,np.cumsum(steps)]
    t=np.linspace(0,s[-1],count+1)
    return np.array([np.interp(t,s,curve[:,i]) for i in range(3)]).T


def pd_code(curve,view=VIEWS[0]):
    """CCW half-edges starting at the incoming underpass; all arcs retained."""
    rows=crossings(curve,normal=view)
    events=sorted([d[k] for d in rows for k in ['first','second']]);m=len(events)
    def arcs(position):
        j=events.index(position);return (j-1)%m,j
    pd=[]
    for d in rows:
        under,over=(d['second'],d['first']) if d['first_over'] else (d['first'],d['second'])
        ui,uo=arcs(under);oi,oo=arcs(over)
        pd.append([ui,oo,uo,oi] if d['sign']>0 else [ui,oi,uo,oo])
    return pd


def diagram_analysis(curve,view=VIEWS[0]):
    import snappy
    from spherogram import Link
    pd=pd_code(curve,view)
    if not pd:return {'crossings':0,'diagram':'unknot','pd':[]}
    import random
    state=random.getstate();random.seed(35)
    try:
        link=Link(pd);link.simplify('global',type_III_limit=100)
    finally:random.setstate(state)
    result={'pd':pd,'simplified_pd':link.PD_code(),'dt_code':str(link.DT_code()),
            'crossings':len(link.crossings),'components':len(link.link_components),
            'canonical_gauss':canonical_gauss(link)}
    try:result['jones_A']=jones_a(link)
    except ValueError as error:result['jones_status']=str(error)
    manifold=link.exterior()
    result['solution_type']=str(manifold.solution_type());result['volume']=float(manifold.volume())
    if 'positively oriented' in result['solution_type']:
        result['census_matches']=[str(x) for x in manifold.identify()]
        result['matches_10_139']=bool(manifold.is_isometric_to(snappy.Manifold('10_139')))
    return result


def analyse_field(field,h):
    p=preimages(field,h);curves=p.pop('curves');p['diagrams']=[]
    for curve in curves:
        rows=[]
        for view in VIEWS:
            try:rows.append({'view':list(view),**diagram_analysis(resample(curve),view)})
            except (ValueError,RuntimeError) as error:rows.append({'view':list(view),'status':'unresolved','reason':str(error)})
        p['diagrams'].append(rows)
    return p,curves
