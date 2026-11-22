"""Piecewise-linear near-south preimage extraction; qualified geometric diagnostics only."""
import itertools
import numpy as np
from scipy.ndimage import map_coordinates
BITS=np.array(list(itertools.product([0,1],repeat=3)))
TARGET=np.array([.11,-.07,-np.sqrt(1-.11**2-.07**2)])
U=np.cross(TARGET,[0.,0.,1.]);U/=np.linalg.norm(U)
V=np.cross(TARGET,U)
TETS=[(0,1,3,7),(0,3,2,7),(0,2,6,7),(0,6,4,7),(0,4,5,7),(0,5,1,7)]

def extract(n,g):
    segments=[];ambiguous=0;nx,ny,nz=g.shape;h=np.array(g.spacing);origin=-np.array(g.lengths)/2
    for start in range(0,nx-1,4):
        stop=min(start+4,nx-1);shape=(stop-start,ny-1,nz-1)
        base=np.stack(np.meshgrid(np.arange(start,stop),np.arange(ny-1),np.arange(nz-1),indexing='ij'),axis=-1).reshape(-1,3)
        corners=np.stack([n[start+a:stop+a,b:b+ny-1,c:c+nz-1] for a,b,c in BITS],axis=-2).reshape(-1,8,3)
        for ids in TETS:
            points=[];valids=[]
            for face in itertools.combinations(ids,3):
                vals=corners[:,face,:];weights=np.cross(vals@U,vals@V);den=weights.sum(axis=1)
                valid=abs(den)>1e-14;weights=np.divide(weights,den[:,None],out=np.zeros_like(weights),where=valid[:,None])
                valid&=(weights.min(axis=1)>=-1e-9)&(weights.max(axis=1)<=1+1e-9)&(np.sum(weights*(vals@TARGET),axis=1)>.05)
                pos=origin+h*(base+weights@BITS[list(face)])
                points.append(pos);valids.append(valid)
            valid=np.stack(valids,axis=1);points=np.stack(points,axis=1);counts=valid.sum(axis=1);ambiguous+=int(np.count_nonzero(counts>2))
            rows=np.flatnonzero(counts==2)
            if len(rows):
                pair=np.argsort(~valid[rows],axis=1)[:,:2];segments.append(points[rows[:,None],pair])
    if not segments:return [],{'status':'no_resolved_south_preimage','ambiguous_tetrahedra':ambiguous}
    segments=np.concatenate(segments);tol=min(h)*1e-7;coordinates={};adj={};edges=set()
    for a,b in segments:
        ka,kb=tuple(np.rint(a/tol).astype(np.int64)),tuple(np.rint(b/tol).astype(np.int64))
        if ka==kb:continue
        edge=tuple(sorted((ka,kb)))
        if edge in edges:continue
        edges.add(edge);coordinates[ka]=a;coordinates[kb]=b;adj.setdefault(ka,set()).add(kb);adj.setdefault(kb,set()).add(ka)
    bad=sum(len(v)!=2 for v in adj.values())
    if bad:return [],{'status':'open_or_nonmanifold_preimage','non_degree_two_vertices':bad,'ambiguous_tetrahedra':ambiguous,'segments':len(edges)}
    unused=set(adj);loops=[]
    while unused:
        first=min(unused);current=first;previous=None;loop=[]
        for _ in range(len(adj)+1):
            loop.append(coordinates[current]);unused.discard(current);options=adj[current]-({previous} if previous is not None else set());nxt=min(options)
            if nxt==first:break
            previous,current=current,nxt
        else:return [],{'status':'trace_failed'}
        loops.append(np.asarray(loop))
    return loops,{'status':'closed_piecewise_linear_preimages','target':TARGET.tolist(),'components':len(loops),'segments':len(edges),'ambiguous_tetrahedra':ambiguous,'scope':'Near-south regular-target preimage of tetrahedrally interpolated sampled field. No knot name inferred; refinement qualification still required.'}

def uniform(poly,count):
    closed=np.vstack([poly,poly[0]]);length=np.linalg.norm(np.diff(closed,axis=0),axis=1);arc=np.r_[0,np.cumsum(length)];t=np.linspace(0,arc[-1],count,endpoint=False)
    return np.stack([np.interp(t,arc,closed[:,i]) for i in range(3)],axis=-1)

def writhe(poly,count):
    p=uniform(poly,count);dr=np.roll(p,-1,axis=0)-p;mid=(p+np.roll(p,-1,axis=0))/2;delta=mid[:,None]-mid[None,:];dist=np.linalg.norm(delta,axis=-1)
    integrand=np.sum(np.cross(dr[:,None],dr[None,:])*delta,axis=-1)/np.maximum(dist,1e-30)**3
    ii=np.arange(count);integrand[ii,ii]=0;integrand[ii,(ii+1)%count]=0;integrand[ii,(ii-1)%count]=0
    return float(integrand.sum()/(4*np.pi))

def framed_twist(poly,n,g,count):
    from electron_field_topology.sf_time import derivative
    p=uniform(poly,count);t=np.roll(p,-1,axis=0)-np.roll(p,1,axis=0);t/=np.maximum(np.linalg.norm(t,axis=-1,keepdims=True),1e-30)
    scalar=n@U;coords=((p+np.asarray(g.lengths)/2)/np.asarray(g.spacing)).T
    grad=np.stack([map_coordinates(derivative(scalar,h,i,g.boundary),coords,order=1,mode='nearest') for i,h in enumerate(g.spacing)],axis=-1)
    frame=grad-t*np.sum(t*grad,axis=-1,keepdims=True);size=np.linalg.norm(frame,axis=-1,keepdims=True)
    if float(size.min())<1e-8:return None
    frame/=size;next_t=np.roll(t,-1,axis=0);next_frame=np.roll(frame,-1,axis=0);cross=np.cross(t,next_t);sn=np.linalg.norm(cross,axis=-1);cs=np.clip(np.sum(t*next_t,axis=-1),-1,1)
    if np.any(cs<-.99):return None
    axis=np.divide(cross,sn[:,None],out=np.zeros_like(cross),where=sn[:,None]>1e-12)
    transported=frame*cs[:,None]+np.cross(axis,frame)*sn[:,None]+axis*np.sum(axis*frame,axis=-1,keepdims=True)*(1-cs[:,None])
    angles=np.arctan2(np.sum(next_t*np.cross(transported,next_frame),axis=-1),np.sum(transported*next_frame,axis=-1))
    return float(angles.sum()/(2*np.pi))

def analyze(n,g):
    loops,info=extract(n,g);result={'extraction':info,'curves':[],'scope':'Rod-motivated length/bending/writhe diagnostics; the energy functional is unchanged. No geometric quantity grants stability or topology admission.'}
    for poly in loops:
        ds=np.linalg.norm(np.roll(poly,-1,axis=0)-poly,axis=1);t=(np.roll(poly,-1,axis=0)-poly)/np.maximum(ds[:,None],1e-30)
        angle=np.arccos(np.clip(np.sum(t*np.roll(t,1,axis=0),axis=1),-1,1));bending=float(np.sum(angle**2/np.maximum((ds+np.roll(ds,1))/2,1e-30)))
        w1,w2=writhe(poly,128),writhe(poly,256);tw1,tw2=framed_twist(poly,n,g,128),framed_twist(poly,n,g,256)
        result['curves'].append({'points':len(poly),'length':float(ds.sum()),'integrated_polygon_bending':bending,'writhe_128':w1,'writhe_256':w2,'writhe_sampling_difference':abs(w1-w2),'writhe_quadrature_qualified':abs(w1-w2)<.05,'framed_twist_128':tw1,'framed_twist_256':tw2,'twist_quadrature_qualified':tw1 is not None and tw2 is not None and abs(tw1-tw2)<.05,'framing':'Projected spatial gradient of n dot U along the extracted regular-target preimage. No Tw+Wr identification with total Hopf charge; mesh qualification remains separate.'})
    return result,loops
