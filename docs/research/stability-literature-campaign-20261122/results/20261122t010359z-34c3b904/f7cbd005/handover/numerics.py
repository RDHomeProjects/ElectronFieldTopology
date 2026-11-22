"""One-factor maps, constrained curvature and geometry for the unchanged SF action."""
import numpy as np
from scipy.ndimage import map_coordinates
from common import need
NORTH=np.array([0.,0.,1.])

def tangent(v,n,g):
    v=v-n*np.sum(n*v,axis=-1,keepdims=True);v[g.fixed_mask()]=0;return v

def retract(n,v,g):
    p=n+v;size=np.linalg.norm(p,axis=-1,keepdims=True)
    need(float(size.min())>1e-8,'Retraction singularity; transformed field remains unresolved')
    p=p/size;p[g.fixed_mask()]=NORTH;return p

def sample(n,g,points):
    coordinates=np.moveaxis((points+np.asarray(g.lengths)/2)/np.asarray(g.spacing),-1,0)
    u=np.stack([map_coordinates(n[...,i]-NORTH[i],coordinates,order=3,mode='constant',cval=0.,prefilter=True)+NORTH[i] for i in range(3)],axis=-1)
    size=np.linalg.norm(u,axis=-1,keepdims=True)
    need(float(size.min())>1e-6,'Cubic map has an unresolved near-zero interpolant')
    return u/size,{'minimum_interpolant_norm':float(size.min()),'maximum_normalization_correction':float(np.max(abs(size-1)))}

def transformed(n,g,arm,curvature=None):
    from electron_field_topology.sf_time import Grid
    info={'factor_changed':arm['kind'],'source_shape':list(g.shape),'source_lengths':list(g.lengths),'optimizer_memory_reset':arm['kind']!='exact'}
    kind=arm['kind'];gg=g
    if kind in ['exact','identity']:p=n.copy()
    elif kind=='domain':
        pad=arm['padding'];nn=g.shape[0]+2*pad;gg=Grid((nn,)*3,tuple((nn-1)*h for h in g.spacing),'fixed')
        p=np.broadcast_to(NORTH,gg.shape+(3,)).copy();p[pad:-pad,pad:-pad,pad:-pad]=n
        info['old_held_layers_become_interior']=True;info['spacing_preserved']=True
    elif kind=='mesh':
        nn=arm['nodes'];gg=Grid((nn,)*3,g.lengths,'fixed');p,extra=sample(n,g,gg.points());info.update(extra)
    elif kind in ['bend','scale']:
        points=g.points()
        if kind=='scale':points/=arm['factor']
        else:
            # Global x-shear, determinant one; compact transverse displacement.
            points[...,0]-=arm['amplitude']*g.lengths[0]*np.exp(-(points[...,1]**2+points[...,2]**2)/16)
        p,extra=sample(n,g,points);info.update(extra)
    elif kind=='curvature':
        need(curvature is not None,'No qualified negative tested-subspace curvature direction')
        v=curvature/max(float(np.max(np.linalg.norm(curvature,axis=-1))),1e-30)
        p=retract(n,arm['amplitude']*v,g)
    elif kind=='fresh':
        from electron_field_topology.skyrme import rational_field
        a,b=arm['alpha'],arm['beta'];degree=2*a+7*b if arm['family']=='torus72' else 3*a+2*b
        need(degree==21,'Fresh map algebraic degree differs')
        p=rational_field(g.points(),kind=arm['family'],alpha=a,beta=b,scale=4.,cutoff=8.8,amplitude=arm['map_amplitude'])
        info['degree_formula']='2*alpha+7*beta' if arm['family']=='torus72' else '3*alpha+2*beta'
        info['algebraic_degree']=degree;info['initial_family_is_not_final_knot_identification']=True
    else:raise ValueError(kind)
    correction=float(np.max(abs(p[gg.fixed_mask()]-NORTH)));p[gg.fixed_mask()]=NORTH
    info.update(shape=list(gg.shape),lengths=list(gg.lengths),spacing=list(gg.spacing),held_layer_correction=correction)
    return p,gg,info

def geometry(n,g):
    from electron_field_topology.sf_time import gradients,sigma_terms
    from electron_field_topology.skyrme import K
    d=gradients(n-NORTH,g);e2=sigma_terms(n,g)[0];e4=sum(np.sum(np.cross(d[...,i,:],d[...,j,:])**2,axis=-1) for i,j in [(0,1),(0,2),(1,2)])
    density=e2+e4;weight=density/density.sum();xyz=g.points();centre=np.sum(weight[...,None]*xyz,axis=(0,1,2));delta=xyz-centre
    flat=delta.reshape(-1,3);cov=flat.T@(weight.reshape(-1,1)*flat);eigen=np.linalg.eigvalsh(cov)
    vol=np.prod(g.spacing);s2=float(K*vol*e2.sum());s4=float(K*vol*e4.sum())
    return {'e2':s2,'e4':s4,'continuum_scaling_proxy':(s2-s4)/max(s2+s4,1e-30),'scaling_proxy_scope':'Continuum E2=E4 is a diagnostic, not a finite-box/discrete stationarity certificate. Actual mapped-scale energies are recorded separately.',
            'energy_centroid':centre.tolist(),'energy_covariance_eigenvalues':eigen.tolist(),'rms_extent':float(np.sqrt(eigen.sum())),
            'core_voxel_volume_n3_negative':float(np.count_nonzero(n[...,2]<0)*vol),'scope':'Energy/core geometry proxies; not exact core length, twist, writhe or knot classification.'}

def curvature_probe(n,g,engine,epsilons=(.001,.0005),count=8):
    """Matrix-free HVPs in a declared smooth tangent subspace, not a full spectrum."""
    from electron_field_topology.sf_time import gradients
    coords=g.points();x,y,z=np.moveaxis(coords,-1,0);window=np.exp(-(x*x+y*y+z*z)/36)
    d=gradients(n-NORTH,g);basis=[];null=[]
    # Remove approximate translation and vacuum-preserving target rotation modes.
    for v in [d[...,i,:] for i in range(3)]+[np.cross(NORTH,n)]:
        v=tangent(v,n,g)
        for u in null:v-=np.sum(u*v)*u
        size=np.linalg.norm(v)
        if size>1e-12:null.append(v/size)
    for i in range(count+4):
        v=np.stack([np.sin((i+1)*.17*x+.31*y),np.cos(.23*y+(i+1)*.11*z),np.sin(.29*z+.13*x+i)],axis=-1)*window[...,None]
        v=tangent(v,n,g)
        for u in null+basis:v-=np.sum(u*v)*u
        size=np.linalg.norm(v)
        if size>1e-10:basis.append(v/size)
        if len(basis)==count:break
    def tg(p):
        _,raw=engine.value(engine.xp.asarray(p),g)
        return tangent(engine.host(raw),p,g)
    matrices=[];mins=[]
    for eps in epsilons:
        H=np.empty((len(basis),len(basis)))
        for j,v in enumerate(basis):
            hp=tangent((tg(retract(n,eps*v,g))-tg(retract(n,-eps*v,g)))/(2*eps),n,g)
            H[:,j]=[float(np.sum(u*hp)) for u in basis]
        asym=float(np.linalg.norm(H-H.T)/max(np.linalg.norm(H),1e-30));sym=(H+H.T)/2
        vals,vec=np.linalg.eigh(sym);mins.append(float(vals[0]));matrices.append({'epsilon':eps,'matrix':sym.tolist(),'relative_antisymmetry':asym,'eigenvalues':vals.tolist()})
    relative=abs(mins[0]-mins[1])/max(abs(mins[0]),abs(mins[1]),1e-12)
    qualified=all(m['relative_antisymmetry']<.05 for m in matrices) and relative<.1 and max(mins)<-1e-10
    direction=sum(vec[i,0]*basis[i] for i in range(len(basis))) if qualified else None
    return {'status':'negative_curvature_in_tested_subspace' if qualified else 'no_qualified_negative_direction_in_tested_subspace','basis_size':len(basis),'translation_and_target_rotation_modes_removed':len(null),'results':matrices,'epsilon_minimum_relative_difference':relative,'direction_qualified':qualified,'operator_calls':2*len(epsilons)*len(basis),'stationary_solution_assumed':False,'scope':'Constrained Hessian of the current lattice action. At an unconverged field this is a landscape diagnosis; no physical instability or global lowest-eigenvalue claim.'},direction
