"""Read-only localization without a multi-vector Hessian allocation."""
import gc,time
import numpy as np
from common import stamp,need
from diagnostics import tangent,masks,spectrum
from evaluations import array_sha

def localized(n,g,spectral=True):
    from electron_field_topology.sf_readmission import static_value_gradient
    from electron_field_topology.sf_time import acceleration
    from electron_field_topology.skyrme import K
    before=array_sha(n);clock=time.perf_counter();energy,raw=static_value_gradient(n,g);force=tangent(-raw/(2*K*np.prod(g.spacing)),n,g);del raw
    xyz,regions=masks(n,g);summary={}
    for label in ['force','acceleration']:
        v=force if label=='force' else acceleration(n,np.zeros_like(n),g)[1]
        square=np.sum(v*v,axis=-1);total=float(square.sum());peak=np.unravel_index(np.argmax(square),square.shape)
        summary[label]={'maximum':float(np.sqrt(square[peak])),'quantiles':{str(q):float(np.quantile(np.sqrt(square),q)) for q in [.5,.9,.95,.99,.999]},'peak_index':list(map(int,peak)),'peak_position':xyz[peak].tolist(),'peak_regions':[k for k,m in regions.items() if m[peak]],'regions':{k:{'squared_residual_fraction':float(square[m].sum()/max(total,1e-30)),'voxel_count':int(m.sum())} for k,m in regions.items()},'spectrum':spectrum(v,g) if spectral else {'status':'deferred_nonpilot_spectrum','reason':'Full DST is reserved for the registered stratified diagnostic subset'}}
        if label=='force':del force
        del v,square;gc.collect()
    need(array_sha(n)==before,'Read-only localization changed source array')
    return {'recorded_at':stamp(),'energy':energy,'source_array_sha256':before,'regions':summary,'wall_seconds':time.perf_counter()-clock,'hessian_directions':0,'source_modified':False,'optimizer_attempts':0,'physical_time_steps':0,'scope':'Same disjoint core/guard/former-layer definitions as prior audit; no full Hessian or stability claim'}

def core_persists(record,p):
    return all(record['regions'][key]['regions']['core_neighborhood']['squared_residual_fraction']>=p['minimum_core_'+key+'_fraction_for_pilot'] for key in ['force','acceleration'])
