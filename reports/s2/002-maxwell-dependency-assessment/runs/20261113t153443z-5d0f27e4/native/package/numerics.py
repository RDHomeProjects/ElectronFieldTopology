"""Bounded Yee diagnostics and manufactured periodic controls; Apache-2.0.

c=epsilon0=mu0=1; float64; array component axis first for native Yee fields.
See MODEL.md for the equation map, derived controls and qualifications.
"""
import hashlib, json, time
from pathlib import Path
import numpy as np
from yee_primitives import curl, derivative, points

SOURCE_HASHES={
 'fields.py':'1926edeeabb360b77f87eb8f00bcce412ab102b540d9d5282e56007e0f577688',
 'evolution.py':'c1a3b8820fc192ce25fca332004623be838d400404830ddbabaf97d35d3d8735'}
OFF_E=[(.5,0,0),(0,.5,0),(0,0,.5)]
OFF_B=[(0,.5,.5),(.5,0,.5),(.5,.5,0)]
MODES=np.array([(1,0,0),(1,1,0),(2,1,1),(1,-1,1),(0,1,2),(2,-1,0),(0,0,1),(1,2,-1)],float)
AMPLITUDES=np.array([1,.55,.3,.4,.25,.35,.5,.2])
PHASES=np.array([.1,.7,-.2,1.1,-.4,.3,.8,-.6])

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_reference(repo):
    import sys
    for name,h in SOURCE_HASHES.items():
        if sha(repo/'src/electron_field_topology'/name)!=h:raise ValueError('Source mismatch: '+name)
    sys.path.insert(0,str(repo/'src'))
    from electron_field_topology.fields import hopfion
    from electron_field_topology.evolution import FourierMaxwell,cube_diagnostics
    return hopfion,FourierMaxwell,cube_diagnostics

def rotation(angle=0.,code=None):
    t=np.deg2rad(angle);c,s=np.cos(t),np.sin(t)
    if code=='x90':return np.array([[1,0,0],[0,0,-1],[0,1,0]],float)
    if code=='y90':return np.array([[0,0,1],[0,1,0],[-1,0,0]],float)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]])

def packet(p,t,length=8.,R=None):
    """Finite superposition of eight exact transverse periodic plane waves.

    For each k, E=a cos(k.x-|k|t+phase), B=khat cross E.
    Polarisation a is perpendicular to k by construction. R must be a cubic
    lattice rotation: generic rotations do not preserve box periodicity.
    """
    R=np.eye(3) if R is None else R
    e=np.zeros_like(p);b=np.zeros_like(p)
    for j,(m,amplitude,phase) in enumerate(zip(MODES,AMPLITUDES,PHASES)):
        k=(R@m)*(2*np.pi/length);direction=k/np.linalg.norm(k)
        axis=np.eye(3)[np.argmin(abs(m))];polar=np.cross(m,axis);polar=R@(polar/np.linalg.norm(polar))
        wave=amplitude*np.cos(np.einsum('...i,i->...',p,k)-np.linalg.norm(k)*t+phase)
        e+=wave[...,None]*polar;b+=wave[...,None]*np.cross(direction,polar)
    return e,b

def evaluator(field,hopfion,length,angle=0.,code=None):
    R=rotation(angle,code)
    if field=='packet':return lambda p,t:packet(p,t,length,R)
    def exact(p,t):
        e,b=hopfion(p@R,t)
        return e@R.T,b@R.T
    return exact

def collocate(f,offsets):
    """Linear interpolation to (.5,.5,.5); wraps only at periodic seam.
    Driven Hopfion diagnostics use an interior cube, away from this seam.
    """
    out=[]
    for component,offset in zip(f,offsets):
        a=component
        for axis,v in enumerate(offset):
            if v==0:a=.5*(a+np.roll(a,-1,axis=axis))
        out.append(a)
    return np.stack(out,axis=-1)

def divergence(e,b,h):
    return (sum(derivative(e[i],h,i,False) for i in range(3)),
            sum(derivative(b[i],h,i,True) for i in range(3)))

def relative(a,b,mask=None):
    if mask is not None:a,b=a[mask],b[mask]
    return float(np.sqrt(np.sum((a-b)**2)/max(float(np.sum(b*b)),1e-30)))

def case(params,repo,state_path=None,heartbeat=lambda *args:None,retain_trace=True):
    hopfion,FourierMaxwell,cube_diagnostics=load_reference(repo)
    n=params['nodes'];length=params['length'];T=params['duration'];steps=params['steps'];dt=T/steps;h=length/n
    if n<9 or n%2!=1 or not 0<dt<=h/np.sqrt(3) or not 0<T<=1 or steps>960:raise ValueError('Case outside bounded stable plan')
    exact=evaluator(params['field'],hopfion,length,params.get('angle_degrees',0),params.get('rotation_code'))
    ep=[points(n,length,o,2,0.) for o in OFF_E];bp=[points(n,length,o,2,0.) for o in OFF_B]
    cp=points(n,length,(.5,.5,.5),2,0.)
    e=np.array([exact(p,0)[0][...,i] for i,p in enumerate(ep)])
    b=np.array([exact(p,-dt/2)[1][...,i] for i,p in enumerate(bp)])
    packet_case=params['field']=='packet';guard=np.zeros((n,n,n),bool)
    for axis in range(3):
        s=[slice(None)]*3;s[axis]=[0,1,n-2,n-1];guard[tuple(s)]=True
    guard_points=[p[guard] for p in bp]
    def next_b(e,b,t):
        out=b-dt*curl(e,h,True)
        if not packet_case:
            for i,p in enumerate(guard_points):out[i][guard]=exact(p,t+dt/2)[1][...,i]
        return out
    roi=np.ones((n,n,n),bool) if packet_case else np.all(abs(cp)<=2,axis=-1)
    div0=divergence(e,b,h);divmask=np.ones((n,n,n),bool) if packet_case else np.all(abs(points(n,length,(0,0,0),2,0.))<=1.7,axis=-1)
    field_norm=max(float(np.sqrt(np.sum(e*e+b*b))),1e-30)
    half_cells=max(1,int(np.floor(2/h)));half_cells=min(half_cells,n//2-2)
    trace=[];modified=[];div_growth=0.;wall=time.perf_counter()
    # Record only every fourth solver step; nested trapezoids separate flux
    # sampling sensitivity without altering the physical time integrator.
    for j in range(steps+1):
        t=j*dt;plus=next_b(e,b,t)
        if j%4==0 or j==steps:
            es=collocate(e,OFF_E);bs=collocate(.5*(b+plus),OFF_B)
            d=cube_diagnostics(es,bs,h,half_cells)
            native=float(h**3/2*np.sum(e*e+b*plus))
            modified.append(native)
            de,db=divergence(e,b,h)
            growth=length*np.sqrt(np.sum((de[divmask]-div0[0][divmask])**2+(db[divmask]-div0[1][divmask])**2))/field_norm
            div_growth=max(div_growth,float(growth))
            trace.append({'time':t,**d,'collocated_full_box_energy':float(h**3/2*np.sum(es*es+bs*bs)),'native_modified_energy':native})
        if j==steps:break
        b=plus;e=e+dt*curl(b,h,False)
        if not packet_case:
            for i,p in enumerate(ep):e[i][guard]=exact(p[guard],(j+1)*dt)[0][...,i]
        if j%24==0:heartbeat(j,steps)
    sync=.5*(b+next_b(e,b,T))
    # Native component locations are compared at a common physical time.
    numerator=denominator=e_num=e_den=b_num=b_den=0.
    for family,coords,fields,part in [('E',ep,e,0),('B',bp,sync,1)]:
        for i,p in enumerate(coords):
            m=np.ones((n,n,n),bool) if packet_case else np.all(abs(p)<=2,axis=-1)
            ref=exact(p,T)[part][...,i];num=float(np.sum((fields[i][m]-ref[m])**2));den=float(np.sum(ref[m]**2))
            numerator+=num;denominator+=den
            if family=='E':e_num+=num;e_den+=den
            else:b_num+=num;b_den+=den
    es=collocate(e,OFF_E);bs=collocate(sync,OFF_B);refe,refb=exact(cp,T)
    common_error=relative(np.stack([es,bs],-1),np.stack([refe,refb],-1),roi)
    initial_div=length*np.sqrt(sum(np.sum(v[divmask]**2) for v in div0))/field_norm
    def flux_summary(items):
        ts=np.array([v['time'] for v in items]);flux=np.array([v['outward_flux'] for v in items]);integral=float(np.trapezoid(flux,x=ts));u0=trace[0]['energy'];change=trace[-1]['energy']-u0;defect=change+integral
        return {'samples':len(items),'integrated_flux':integral,'energy_change':change,'defect':defect,'defect_over_initial_energy':defect/max(abs(u0),1e-30),'defect_over_transport':defect/max(abs(change),abs(integral),1e-30)}
    coarse=trace[::2]
    if coarse[-1]['time']!=trace[-1]['time']:coarse=coarse+[trace[-1]]
    result={'parameters':params,'dt':dt,'wall_seconds':time.perf_counter()-wall,'E_error':float(np.sqrt(e_num/max(e_den,1e-30))),'B_synchronized_error':float(np.sqrt(b_num/max(b_den,1e-30))),'sync_native_error':float(np.sqrt(numerator/max(denominator,1e-30))),'collocated_error':common_error,'initial_discrete_divergence_normalized':float(initial_div),'max_discrete_divergence_change_normalized':div_growth,'cube_half_extent':float(half_cells*h),'poynting_balance':flux_summary(trace),'coarser_flux_quadrature':flux_summary(coarse),'modified_energy_relative_drift':float(max(abs(np.array(modified)/modified[0]-1))) if packet_case else None,'physical_energy_relative_change':float(trace[-1]['collocated_full_box_energy']/trace[0]['collocated_full_box_energy']-1) if packet_case else None,'trace':trace if retain_trace else []}
    if packet_case:
        e0,b0=exact(cp,0);solver=FourierMaxwell(e0,b0,h,project=False);u0=solver.energy();solver.advance(T);ef,bf=solver.fields()
        result['fourier']={'exact_error':relative(np.stack([ef,bf],-1),np.stack([refe,refb],-1)),'yee_difference':relative(np.stack([es,bs],-1),np.stack([ef,bf],-1)),'energy_relative_change':float(solver.energy()/u0-1),'divergence_max':solver.divergence_max(),'projection':False}
    else:ef=bf=np.empty((0,),dtype=np.float64)
    if not np.isfinite(result['sync_native_error']):raise ValueError('Nonfinite fields/error')
    if state_path is not None:
        np.savez_compressed(state_path,E=e,B_half=b,fourier_E=ef,fourier_B=bf,dt=np.float64(dt),duration=np.float64(T))
        result['state']={'file':str(Path(state_path).name),'sha256':sha(state_path),'bytes':Path(state_path).stat().st_size,'dtype':'float64','scope':'B_half at T-dt/2; E at T; reconstruct B_sync without changing E/B_half; Fourier packet arrays collocated at common cell centres and T.'}
    return result
