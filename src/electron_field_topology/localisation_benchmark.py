"""Bounded S3-B centroid, width and origin/observer study; Apache-2.0."""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
import numpy as np
from .benchmark import digest,git
from .diagnostics import energy_flow
from .fields import hopfion
from .localisation import density_peak,energy_moments,integrate_moments,stress_energy
from .relativity import boosted_hopfion,lorentz_matrix,transform_fields,velocity_vector


def validate(c):
    if c['model_id']!='B0-H11-Centroid':raise ValueError('unsupported model')
    if c['times']!=[0,1,2]:raise ValueError('standard times 0,1,2 required')
    if len(c['velocities'])!=4 or c['velocities'][0]!=[0,0,0] or c['velocities'][-1]!=[0,0,-.5]:
        raise ValueError('four frames including source and zero-momentum controls required')
    for v in c['velocities']:
        if np.linalg.norm(velocity_vector(v))>.600000000001:raise ValueError('speed limited to 0.6')
    for key,low,high in [('orders',12,64),('radii',2,16),('peak_grids',9,33)]:
        values=c[key]
        if len(values)!=3 or any(not isinstance(x,int) or not low<=x<=high for x in values) or any(b<=a for a,b in zip(values,values[1:])):
            raise ValueError('three increasing bounded values required')
    if c['contained_radius']!=2 or c['peak_half_extent']!=4:raise ValueError('standard localisation/peak extent required')
    if c.get('radial_order_multiplier',1) not in [1,2]:raise ValueError('radial multiplier 1 or 2 required')
    if not isinstance(c['seed'],int):raise ValueError('integer seed required')


def angular_tensor(energy,momentum,centroid,angular,time):
    m=np.zeros((4,4));m[0,1:]=time*np.array(momentum)-energy*np.array(centroid)
    m[1:,0]=-m[0,1:]
    for i,j,k in [(1,2,2),(2,3,0),(3,1,1)]:m[i,j]=angular[k];m[j,i]=-angular[k]
    return m


def reference(velocity,time):
    matrix=lorentz_matrix(velocity)
    p=matrix@np.array([2*np.pi**2,0,0,-np.pi**2])
    source=angular_tensor(2*np.pi**2,[0,0,-np.pi**2],[0,0,0],[0,0,-np.pi**2],0)
    m=matrix@source@matrix.T
    return p,m,(time*p[1:]-m[0,1:])/p[0]


def moment_case(v,t,order,radius=None,radial_order=None):
    field=lambda p,time:boosted_hopfion(p,time,v)
    row=integrate_moments(field,t,order,radius=radius,radial_order=radial_order)
    p,m,r=reference(v,t)
    measured=angular_tensor(row['energy'],row['momentum'],row['centroid'],row['angular_momentum_about_origin'],t)
    return {'time':t,'order':order,'radial_order':order if radial_order is None else radial_order,'radius':radius,**row,'reference_centroid':r.tolist(),
        'centroid_error':float(np.linalg.norm(np.array(row['centroid'])-r)),
        'angular_tensor_error_over_reference_energy':float(np.max(np.abs(measured-m))/p[0]),
        'relative_energy_error':float(abs(row['energy']/p[0]-1))}


def generic_controls(seed):
    rng=np.random.default_rng(seed);e,b=rng.normal(size=(2,32,3));p=rng.normal(size=(32,3));w=rng.uniform(.2,1,32)
    v=np.array([.2,-.3,.4]);matrix=lorentz_matrix(v)
    a=stress_energy(*transform_fields(e,b,v))
    expected=np.einsum('ij,...jk,lk->...il',matrix,stress_energy(e,b),matrix)
    eta=np.diag([-1,1,1,1]);tensor=stress_energy(e,b)
    origin=np.array([.7,-.2,.1]);first=energy_moments(p,w,e,b);shifted=energy_moments(p,w,e,b,origin)
    expected_j=np.array(first['angular_momentum_about_origin'])-np.cross(origin,first['momentum'])
    centered_j=np.array(first['angular_momentum_about_origin'])-np.cross(first['centroid'],first['momentum'])
    return {'stress_tensor_covariance_error':float(np.max(np.abs(a-expected))),
        'stress_trace_error':float(np.max(np.abs(np.einsum('ij,...ij->...',eta,tensor)))),
        'angular_origin_identity_error':float(np.max(np.abs(np.array(shifted['angular_momentum_about_origin'])-expected_j))),
        'centroid_angular_identity_error':float(np.max(np.abs(np.array(first['angular_momentum_about_centroid'])-centered_j))),
        'origin_change_centroid_error':float(np.max(np.abs(np.array(first['centroid'])-shifted['centroid']))),
        'origin_change_covariance_error':float(np.max(np.abs(np.array(first['covariance'])-shifted['covariance'])))}


def study(c):
    frames=[]
    for v in c['velocities']:
        all_space=[{'order':o,'samples':[moment_case(v,t,o,radial_order=o*c.get('radial_order_multiplier',1)) for t in c['times']]} for o in c['orders']]
        finest=all_space[-1]['samples'];initial=finest[0];pf,_,_=reference(v,0);speed=pf[1:]/pf[0]
        slope=(np.array(finest[-1]['centroid'])-finest[0]['centroid'])/(c['times'][-1]-c['times'][0])
        predicted_width=[initial['central_rms_squared']+2*(initial['r_dot_flow_integral']/initial['energy']-np.dot(initial['centroid'],speed))*t+(1-np.dot(speed,speed))*t*t for t in c['times']]
        domain=[moment_case(v,c['times'][-1],c['orders'][-1],radius=r) for r in c['radii']]
        for row in domain:row['central_rms_squared_error_vs_all_space']=abs(row['central_rms_squared']-finest[-1]['central_rms_squared'])
        frames.append({'velocity':v,'all_space':all_space,'finite_spheres_at_final_time':domain,
            'reference_centroid_velocity':speed.tolist(),'measured_secant_centroid_velocity':slope.tolist(),
            'centroid_velocity_error':float(np.linalg.norm(slope-speed)),
            'virial_predicted_central_rms_squared':predicted_width,
            'virial_max_relative_width_error':float(max(abs(r['central_rms_squared']-pred)/pred for r,pred in zip(finest,predicted_width)))})
        print(f'velocity={v}: centroid error={max(r["centroid_error"] for r in finest):.6g}, velocity error={frames[-1]["centroid_velocity_error"]:.6g}',flush=True)
    peaks=[{'time':t,'searches':[density_peak(hopfion,t,c['peak_half_extent'],n) for n in c['peak_grids']]} for t in c['times']]
    contained=[]
    for v in [c['velocities'][0],c['velocities'][-1]]:
        field=lambda p,t:boosted_hopfion(p,t,v)
        for t in c['times']:
            p,_,center=reference(v,t);rows=[]
            for order in c['orders']:
                fixed=integrate_moments(field,t,order,radius=c['contained_radius'])
                moving=integrate_moments(field,t,order,radius=c['contained_radius'],center=center)
                rows.append({'order':order,'fixed_fraction_of_exact_total':fixed['energy']/p[0],
                             'centroid_centered_fraction_of_exact_total':moving['energy']/p[0]})
            contained.append({'velocity':v,'time':t,'radius':c['contained_radius'],'center':center.tolist(),'samples':rows})
    # A source centroid worldline through the origin still passes the primed
    # origin. The actual x-boost equal-time centroid has a transverse offset.
    xboost=moment_case([.6,0,0],0,c['orders'][-1],radial_order=c['orders'][-1]*c.get('radial_order_multiplier',1))
    m={'experiment_id':c['experiment_id'],'generic_controls':generic_controls(c['seed']),
       'frames':frames,'source_energy_density_peaks':peaks,'contained_energy':contained,
       'naive_centroid_worldline_negative_control':{'velocity':[.6,0,0],'time':0,'naive_position':[0,0,0],
            'direct_centroid':xboost['centroid'],'miss_distance':float(np.linalg.norm(xboost['centroid']))},
       'scope':'Analytical unbounded fields; energy moments and bounded peak candidates. Arbitrary scales; no particle/confinement/topology or quantum-spin claim.'}
    m['acceptance']=acceptance(m)
    return m


def acceptance(m):
    rows=[r for f in m['frames'] for r in f['all_space'][-1]['samples']]
    source=m['frames'][0]['all_space'][-1]['samples']
    increments=[abs(a['central_rms_squared']-b['central_rms_squared']) for f in m['frames'] for a,b in zip(f['all_space'][-1]['samples'],f['all_space'][-2]['samples'])]
    increments += [float(np.linalg.norm(np.array(a['centroid'])-b['centroid'])) for f in m['frames'] for a,b in zip(f['all_space'][-1]['samples'],f['all_space'][-2]['samples'])]
    return {'generic_tensor_origin_controls_below_1e-12':max(m['generic_controls'].values())<1e-12,
        'source_closed_form_centroid_width_below_1e-6':max(max(r['centroid_error'],abs(r['central_rms_squared']-(1+.75*r['time']**2))) for r in source)<1e-6,
        'boosted_centroids_below_1e-6':max(r['centroid_error'] for r in rows)<1e-6,
        'centroid_velocity_below_1e-6':max(f['centroid_velocity_error'] for f in m['frames'])<1e-6,
        'angular_tensor_error_over_energy_below_1e-6':max(r['angular_tensor_error_over_reference_energy'] for r in rows)<1e-6,
        'finest_quadrature_increment_below_1e-6':max(increments)<1e-6,
        'finite_radius_centroid_width_error_reduces':all(f['finite_spheres_at_final_time'][-1]['centroid_error']<f['finite_spheres_at_final_time'][0]['centroid_error'] for f in m['frames']) and all(f['finite_spheres_at_final_time'][-1]['central_rms_squared_error_vs_all_space']<f['finite_spheres_at_final_time'][0]['central_rms_squared_error_vs_all_space'] for f in m['frames']),
        'all_frames_virial_width_relative_error_below_1e-5':max(f['virial_max_relative_width_error'] for f in m['frames'])<1e-5,
        'density_peak_search_finest_positions_agree':all(np.linalg.norm(np.array(p['searches'][-1]['position'])-p['searches'][-2]['position'])<1e-4 and p['searches'][-1]['distance_to_search_boundary']>.1 for p in m['source_energy_density_peaks']),
        'density_peak_distinct_from_centroid_at_t2':bool(np.linalg.norm(np.array(m['source_energy_density_peaks'][-1]['searches'][-1]['position'])-source[-1]['centroid'])>.2),
        'naive_centroid_worldline_offset_detected':m['naive_centroid_worldline_negative_control']['miss_distance']>.1,
        'constant_width_negative_control_rejected':source[-1]['central_rms_squared']-source[0]['central_rms_squared']>1}


def plot(m,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='eft-s3b'
    fig,axs=plt.subplots(1,3,figsize=(12,3.6),constrained_layout=True)
    for i in [0,-1]:
        f=m['frames'][i];r=f['all_space'][-1]['samples'];times=[x['time'] for x in r]
        axs[0].plot(times,[np.sqrt(x['central_rms_squared']) for x in r],'o-',label='Source' if i==0 else 'Zero momentum')
    axs[0].set(xlabel='Observer time',ylabel='Central RMS radius',title='Spread about energy centroid');axs[0].legend(fontsize=8)
    for v,label in [(m['frames'][0]['velocity'],'Source'),(m['frames'][-1]['velocity'],'Zero momentum')]:
        r=[x for x in m['contained_energy'] if x['velocity']==v]
        axs[1].plot([x['time'] for x in r],[x['samples'][-1]['centroid_centered_fraction_of_exact_total'] for x in r],'o-',label=label)
    axs[1].set(xlabel='Observer time',ylabel='Fraction of exact total energy',title='Radius 2 about energy centroid');axs[1].legend(fontsize=8)
    f=m['frames'][0];r=f['all_space'][-1]['samples'];times=[x['time'] for x in r]
    axs[2].plot(times,[x['centroid'][2] for x in r],'o-',label='Energy centroid')
    axs[2].plot(times,[p['searches'][-1]['position'][2] for p in m['source_energy_density_peaks']],'s--',label='Density peak candidate')
    axs[2].set(xlabel='Source time',ylabel='z coordinate',title='Peak and centroid differ');axs[2].legend(fontsize=8)
    fig.savefig(out/'localisation.svg',metadata={'Date':None});plt.close(fig)


def run(config_path,output):
    start=time.perf_counter();path=Path(config_path).resolve();c=json.loads(path.read_text());validate(c)
    out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('new or empty output required')
    out.mkdir(parents=True,exist_ok=True);m=study(c)
    (out/'metrics.json').write_text(json.dumps(m,indent=2,allow_nan=False)+'\n');(out/'config.json').write_bytes(path.read_bytes());plot(m,out)
    root=Path(__file__).resolve().parents[2];sources=[root/'pyproject.toml',root/'uv.lock',*sorted((root/'src').rglob('*.py'))]
    manifest={'experiment_id':c['experiment_id'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'repository':'https://github.com/RDHomeProjects/ElectronFieldTopology','commit':git(root,'rev-parse','HEAD'),
        'dirty_tree':bool(git(root,'status','--porcelain')),'source_sha256':{str(p.relative_to(root)):digest(p) for p in sources},
        'config_sha256':digest(path),'dependency_lock_sha256':digest(root/'uv.lock'),'configuration':c,
        'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'cpu_count':os.cpu_count(),
        'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib']},
        'precision':'float64 / complex128','thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
        'command':sys.argv,'boundaries':'unbounded analytical evaluation; compactified all-space quadrature and separate finite diagnostic spheres',
        'units':'c=epsilon_0=mu_0=l0=1, arbitrary dimensionless amplitude','elapsed_seconds':time.perf_counter()-start,
        'artifacts_sha256':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'acceptance':m['acceptance'],'elapsed_seconds':manifest['elapsed_seconds']}))
    return all(m['acceptance'].values())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if not run(a.config,a.output):raise SystemExit('Verification acceptance failed; retain metrics for investigation.')


if __name__=='__main__':main()
