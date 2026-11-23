"""Read-only regional, spectral and residual-oriented curvature measurements."""
import gc
import numpy as np
from scipy.fft import dstn
from scipy.ndimage import distance_transform_edt,gaussian_filter
from common import need,stamp
from evaluations import array_sha

def tangent(v,n,g):
    r=v-n*np.sum(n*v,axis=-1,keepdims=True);r[g.fixed_mask()]=0;return r

def masks(n,g):
    xyz=g.points();distance=np.min(np.asarray(g.lengths)/2-abs(xyz),axis=-1);guard=distance<=3.
    oldband=np.any(np.minimum(abs(abs(xyz)-11.28),abs(abs(xyz)-11.52))<=.24,axis=-1)
    core=distance_transform_edt(~(n[...,2]<0),sampling=g.spacing)<=1.
    regions={'outer_guard':guard,'old_held_layers':oldband&~guard,'core_neighborhood':core&~guard&~oldband}
    regions['remaining_interior']=~np.logical_or.reduce(list(regions.values()))
    return xyz,regions

def spectrum(v,g):
    interior=(slice(2,-2),)*3;coef=dstn(v[interior],axes=(0,1,2),type=1,norm='ortho');power=np.sum(coef*coef,axis=-1);total=float(power.sum())
    axes=[4*np.sin(np.pi*np.arange(1,count-3)/(2*(count-3)))**2/h**2 for count,h in zip(g.shape,g.spacing)];eig=sum(a.reshape(tuple(len(a) if i==j else 1 for i in range(3))) for j,a in enumerate(axes));norm=np.sqrt(eig/sum(4/h**2 for h in g.spacing));bins=np.linspace(0,1,21)
    fractions=np.histogram(norm,bins=bins,weights=power)[0]/max(total,1e-30);order=np.argsort(eig.ravel());ev=eig.ravel()[order];cum=np.cumsum(power.ravel()[order])/max(total,1e-30)
    return {'dirichlet_laplacian_eigenvalue_weighted_mean':float(np.sum(eig*power)/max(total,1e-30)),'eigenvalue_weighted_quantiles':{str(q):(float(ev[min(np.searchsorted(cum,q),len(ev)-1)]) if total>0 else None) for q in [.1,.5,.9]},'normalized_frequency_bin_edges':bins.tolist(),'power_fractions':fractions.tolist(),'low_frequency_power_fraction':float(power[norm<.3].sum()/max(total,1e-30)),'high_frequency_power_fraction':float(power[norm>=.7].sum()/max(total,1e-30)),'scope':'Orthonormal DST-I on free interior nodes. Frequency is normalized by the discrete Laplacian maximum; this is a conditioning diagnostic, not a physical dispersion relation.'}

def curvature(n,g,e,directions,epsilons):
    from electron_field_topology.sf_time import gradients
    d=gradients(n-[0,0,1],g);null=[]
    for v in [d[...,i,:] for i in range(3)]+[np.cross([0.,0.,1.],n)]:
        v=tangent(v,n,g)
        for u in null:v-=np.sum(u*v)*u
        norm=np.linalg.norm(v)
        if norm>1e-12:null.append(v/norm)
    del d;basis=[];names=[]
    for name,v in directions:
        v=tangent(v,n,g)
        for u in null+basis:v-=np.sum(u*v)*u
        norm=np.linalg.norm(v)
        if norm>1e-12:basis.append(v/norm);names.append(name)
        if len(basis)==8:break
    def grad(p):
        _,raw=e.value(e.xp.asarray(p),g);return tangent(e.host(raw),p,g)
    def retract(v):
        p=n+v;p/=np.linalg.norm(p,axis=-1,keepdims=True);p[g.fixed_mask()]=[0.,0.,1.];return p
    results=[]
    for eps in epsilons:
        H=np.empty((len(basis),len(basis)))
        for j,v in enumerate(basis):
            hv=tangent((grad(retract(eps*v))-grad(retract(-eps*v)))/(2*eps),n,g);H[:,j]=[float(np.sum(u*hv)) for u in basis]
        sym=(H+H.T)/2;results.append({'epsilon':eps,'relative_antisymmetry':float(np.linalg.norm(H-H.T)/max(np.linalg.norm(H),1e-30)),'eigenvalues':np.linalg.eigvalsh(sym).tolist(),'matrix':sym.tolist()})
    if not basis:return {'basis':[],'status':'no_nonzero_residual_basis','results':results,'negative_direction_in_tested_subspace':False,'energy_gradient_calls':0}
    low=[r['eigenvalues'][0] for r in results];difference=abs(low[0]-low[1])/max(abs(low[0]),abs(low[1]),1e-12)
    return {'basis':names,'removed_approximate_symmetry_modes':len(null),'results':results,'minimum_eigenvalue_relative_epsilon_difference':difference,'negative_direction_in_tested_subspace':bool(max(low)<-1e-10 and difference<.1 and all(r['relative_antisymmetry']<.05 for r in results)),'energy_gradient_calls':2*len(basis)*len(epsilons),'scope':'Residual-oriented constrained Hessian at a nonstationary field; neither a global minimum eigenvalue nor a physical stability certificate.'}

def audit(n,g,e,epsilons):
    from electron_field_topology.sf_readmission import static_value_gradient
    from electron_field_topology.sf_time import acceleration,sigma_terms
    from electron_field_topology.skyrme import K
    before=array_sha(n);energy,raw=static_value_gradient(n,g);force=tangent(-raw/(2*K*np.prod(g.spacing)),n,g);del raw
    a=acceleration(n,np.zeros_like(n),g)[1];xyz,regions=masks(n,g);summary={}
    for label,v in [('force',force),('acceleration',a)]:
        square=np.sum(v*v,axis=-1);total=float(square.sum());peak=np.unravel_index(np.argmax(square),square.shape)
        summary[label]={'maximum':float(np.sqrt(square[peak])),'peak_index':list(map(int,peak)),'peak_position':xyz[peak].tolist(),'peak_regions':[k for k,m in regions.items() if m[peak]],'regions':{k:{'squared_residual_fraction':float(square[m].sum()/max(total,1e-30)),'voxel_count':int(m.sum()),'maximum':float(np.sqrt(square[m].max())) if m.any() else None} for k,m in regions.items()},'spectrum':spectrum(v,g)}
    fp=summary['force']['peak_position'];ap=summary['acceleration']['peak_position'];fs=gaussian_filter(force,(1.,1.,1.,0.));asmooth=gaussian_filter(a,(1.,1.,1.,0.))
    # Directions are evaluated sequentially; only the qualified eight-vector
    # basis is retained. No optimization step is performed by this audit.
    directions=[('full_tangent_force',force),('smoothed_force',fs),('force_high_pass',force-fs),('core_force',force*regions['core_neighborhood'][...,None]),('old_layer_force',force*regions['old_held_layers'][...,None]),('guard_force',force*regions['outer_guard'][...,None]),('force_hotspot',force*np.exp(-np.sum((xyz-fp)**2,axis=-1)/2)[...,None]),('acceleration_hotspot',a*np.exp(-np.sum((xyz-ap)**2,axis=-1)/2)[...,None]),('full_acceleration',a),('acceleration_high_pass',a-asmooth)]
    h=curvature(n,g,e,directions,epsilons);need(array_sha(n)==before,'Read-only residual audit mutated source field')
    return {'recorded_at':stamp(),'energy':energy,'source_array_sha256':before,'regions':summary,'region_priority':['outer_guard','old_held_layers','core_neighborhood','remaining_interior'],'region_definitions':{'outer_guard':'distance to new outer face<=3','old_held_layers':'within0.24 of absolute coordinate11.28 or11.52 on any axis, excluding outer guard','core_neighborhood':'Euclidean distance<=1 from n3<0, excluding earlier regions'},'curvature':h,'optimizer_attempts':0,'physical_time_steps':0,'source_modified':False}
