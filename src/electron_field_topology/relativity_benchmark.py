"""Bounded analytical S3-A covariance study; Apache-2.0."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
import numpy as np
from .benchmark import digest, git
from .diagnostics import energy_flow, maxwell_residuals, sphere_rule
from .fields import hopfion
from .relativity import (boosted_hopfion, field_tensor, fields_from_tensor,
                         lorentz_matrix, transform_events, transform_fields,
                         velocity_vector)


def validate(c):
    """Bound CPU/memory and require the declared convergence studies."""
    if c['model_id'] != 'B0-H11-Lorentz': raise ValueError('unsupported model')
    if not isinstance(c['seed'], int): raise ValueError('integer seed required')
    if not 1 <= len(c['velocities']) <= 4: raise ValueError('1..4 velocities required')
    if any(np.linalg.norm(velocity_vector(v)) > .600000000001 for v in c['velocities']):
        raise ValueError('benchmark speed limited to 0.6')
    if not isinstance(c['event_count'], int) or not 16 <= c['event_count'] <= 256:
        raise ValueError('event count 16..256 required')
    for key in ['event_half_extent', 'flux_radius']:
        if not np.isfinite(c[key]) or not .5 <= c[key] <= 3: raise ValueError('invalid extent')
    for key in ['target_time', 'integration_time']:
        if not np.isfinite(c[key]) or abs(c[key]) > 1: raise ValueError('invalid time')
    for key, low, high in [('radii',2,16),('orders',12,64)]:
        values=c[key]
        if len(values)!=3 or any(not isinstance(x,int) or not low<=x<=high for x in values) or any(b<=a for a,b in zip(values,values[1:])):
            raise ValueError('three increasing bounded radii/orders required')
    steps=np.asarray(c['difference_steps'], dtype=float)
    if steps.shape!=(3,) or not np.isfinite(steps).all() or not .002<=steps[-1]<=steps[0]<=.08 or not np.allclose(steps[:-1],2*steps[1:]):
        raise ValueError('three halved steps required')
    center=np.asarray(c['flux_center'],dtype=float)
    if center.shape!=(3,) or not np.isfinite(center).all() or np.linalg.norm(center)>1:
        raise ValueError('bounded center required')


def residual_rms(field, points, time, steps):
    rows=[]
    for h in steps:
        residuals=maxwell_residuals(points,time,h,field=field)
        rows.append({'step':h, **{k:float(np.sqrt(np.mean(v*v))) for k,v in residuals.items()}})
    return rows


def local_case(v,c,points,events,e,b):
    matrix=lorentz_matrix(v);inverse=lorentz_matrix(-np.array(v));eta=np.diag([-1,1,1,1])
    ev,bv=transform_fields(e,b,v)
    tensor=np.einsum('ij,...jk,lk->...il',matrix,field_tensor(e,b),matrix)
    et,bt=fields_from_tensor(tensor)
    back=transform_fields(ev,bv,-np.array(v))
    # Generic non-null controls, normalised by positive field scale.
    scale=np.max(np.sum(e*e+b*b,axis=-1))
    transformed=transform_events(events,matrix)
    original=hopfion(events[:,1:],events[:,0])
    expected=transform_fields(*original,v)
    actual=boosted_hopfion(transformed[:,1:],transformed[:,0],v)
    field=lambda p,t:boosted_hopfion(p,t,v)
    hp=field(points,c['target_time']);u,_=energy_flow(*hp)
    null1=np.sum(hp[0]*hp[1],axis=-1)
    null2=np.sum(hp[0]**2-hp[1]**2,axis=-1)
    return {'velocity':v,
        'metric_error':float(np.max(np.abs(matrix.T@eta@matrix-eta))),
        'matrix_inverse_error':float(np.max(np.abs(inverse@matrix-np.eye(4)))),
        'event_roundtrip_error':float(np.max(np.abs(transform_events(transformed,inverse)-events))),
        'tensor_vector_error':float(max(np.max(np.abs(ev-et)),np.max(np.abs(bv-bt)))),
        'field_inverse_error':float(max(np.max(np.abs(back[0]-e)),np.max(np.abs(back[1]-b)))),
        'generic_invariant_error_normalised':float(max(np.max(np.abs(np.sum(ev*bv-e*b,axis=-1))),np.max(np.abs(np.sum(ev**2-bv**2-e**2+b**2,axis=-1))))/scale),
        'common_event_error':float(max(np.max(np.abs(actual[0]-expected[0])),np.max(np.abs(actual[1]-expected[1])))),
        'null_invariant_error_normalised':float(max(np.max(np.abs(null1)),np.max(np.abs(null2)))/np.max(u)),
        'maxwell':residual_rms(field,points,c['target_time'],c['difference_steps'])}


def integrate(v,radius,order,time):
    p,w=sphere_rule(radius,order)
    e,b=boosted_hopfion(p,time,v);u,s=energy_flow(e,b)
    axes=tuple(range(w.ndim))
    return np.r_[np.sum(w*u),np.sum(w[...,None]*s,axis=axes)]


def integral_case(v,radius,order,time,reference):
    measured=integrate(v,radius,order,time)
    mass2=measured[0]**2-np.dot(measured[1:],measured[1:])
    return {'radius':radius,'order':order,'four_momentum':measured.tolist(),
        'relative_four_momentum_error':float(np.linalg.norm(measured-reference)/np.linalg.norm(reference)),
        'invariant_mass_squared':float(mass2),
        'relative_mass_squared_error':float(abs(mass2/(3*np.pi**4)-1))}


def study(c):
    rng=np.random.default_rng(c['seed'])
    points=rng.uniform(-c['event_half_extent'],c['event_half_extent'],(c['event_count'],3))
    events=rng.uniform(-1,1,(c['event_count'],4));e,b=rng.normal(size=(2,c['event_count'],3))
    local=[];integrals=[];fluxes=[]
    for v in c['velocities']:
        local.append(local_case(v,c,points,events,e,b))
        reference=lorentz_matrix(v)@np.array([2*np.pi**2,0,0,-np.pi**2])
        domain=[integral_case(v,r,c['orders'][-1],c['integration_time'],reference) for r in c['radii']]
        quadrature=[integral_case(v,c['radii'][-1],o,c['integration_time'],reference) for o in c['orders'][:-1]]+[domain[-1]]
        integrals.append({'velocity':v,'all_space_reference':reference.tolist(),'domain':domain,'quadrature':quadrature})
        rows=[]
        for order in c['orders']:
            p,w,n=sphere_rule(c['flux_radius'],order,c['flux_center'],volume=False)
            ev,_=boosted_hopfion(p,c['target_time'],v);f=np.sum(ev*n,axis=-1)
            rows.append({'order':order,'electric_flux':float(np.sum(w*f)),
                         'absolute_flux_integral':float(np.sum(w*np.abs(f)))})
        fluxes.append({'velocity':v,'samples':rows})
        print(f'velocity={v}: finest four-momentum error={domain[-1]["relative_four_momentum_error"]:.6g}',flush=True)
    v=np.array([.6,0,0])
    def wrong_snapshot(p,t):
        event=np.concatenate((np.full(p.shape[:-1]+(1,),t),p),axis=-1)
        source=transform_events(event,lorentz_matrix(-v))
        # Deliberate error: discard inverse-mapped, spatially varying source time.
        return transform_fields(*hopfion(source[...,1:],t),v)
    negative=residual_rms(wrong_snapshot,points,c['target_time'],c['difference_steps'])
    metrics={'experiment_id':c['experiment_id'],'local':local,'integrals':integrals,
             'fluxes':fluxes,'wrong_snapshot_negative_control':negative,
             'scope':'Unbounded analytical Hopfion, passive boosts. Finite integration cutoffs; arbitrary field normalisation. No electron or confinement inference.'}
    metrics['acceptance']=acceptance(metrics)
    return metrics


def acceptance(m):
    keys=['metric_error','matrix_inverse_error','event_roundtrip_error','tensor_vector_error','field_inverse_error','generic_invariant_error_normalised','common_event_error','null_invariant_error_normalised']
    ratios=[r['maxwell'][i][k]/r['maxwell'][i+1][k] for r in m['local'] for i in [0,1] for k in ['div_e','div_b','faraday','ampere']]
    return {'local_covariance_below_1e-12':max(r[k] for r in m['local'] for k in keys)<1e-12,
        'maxwell_second_order':all(3.7<x<4.3 for x in ratios),
        'four_momentum_finest_below_2e-4':all(r['domain'][-1]['relative_four_momentum_error']<2e-4 for r in m['integrals']),
        'domain_error_reduces':all(r['domain'][-1]['relative_four_momentum_error']<r['domain'][0]['relative_four_momentum_error'] for r in m['integrals']),
        'quadrature_finest_change_below_2e-5':all(np.linalg.norm(np.array(r['quadrature'][-1]['four_momentum'])-r['quadrature'][-2]['four_momentum'])/np.linalg.norm(r['all_space_reference'])<2e-5 for r in m['integrals']),
        'electric_flux_finest_normalised_below_1e-10':all(abs(r['samples'][-1]['electric_flux'])/r['samples'][-1]['absolute_flux_integral']<1e-10 for r in m['fluxes']),
        'wrong_snapshot_detected':max(m['wrong_snapshot_negative_control'][-1][k] for k in ['div_e','div_b','faraday','ampere'])>.01}


def plot(m,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='eft-s3a'
    fig,axs=plt.subplots(1,2,figsize=(9,3.7),constrained_layout=True)
    for r in m['integrals']:
        axs[0].semilogy([s['radius'] for s in r['domain']],[s['relative_four_momentum_error'] for s in r['domain']],'o-',label=str(r['velocity']))
    axs[0].set(xlabel='Integration radius, order 64',ylabel='Relative four-momentum error',title='Finite-cutoff convergence')
    axs[0].legend(fontsize=7)
    for i,r in enumerate(m['local']):
        axs[1].loglog([s['step'] for s in r['maxwell']],[s['ampere'] for s in r['maxwell']],'o-',label=f'boost {i}')
    r=m['wrong_snapshot_negative_control']
    axs[1].loglog([s['step'] for s in r],[s['ampere'] for s in r],'x--',label='Wrong snapshot')
    axs[1].set(xlabel='Difference step',ylabel='Ampere residual RMS',title='Event mapping control')
    axs[1].legend(fontsize=7)
    fig.savefig(out/'convergence.svg',metadata={'Date':None});plt.close(fig)


def run(config_path,output):
    start=time.perf_counter();path=Path(config_path).resolve();c=json.loads(path.read_text());validate(c)
    out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('new or empty output required')
    out.mkdir(parents=True,exist_ok=True)
    m=study(c)
    (out/'metrics.json').write_text(json.dumps(m,indent=2,allow_nan=False)+'\n')
    (out/'config.json').write_bytes(path.read_bytes());plot(m,out)
    root=Path(__file__).resolve().parents[2]
    sources=[root/'pyproject.toml',root/'uv.lock',*sorted((root/'src').rglob('*.py'))]
    manifest={'experiment_id':c['experiment_id'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'repository':'https://github.com/RDHomeProjects/ElectronFieldTopology','commit':git(root,'rev-parse','HEAD'),
        'dirty_tree':bool(git(root,'status','--porcelain')),'source_sha256':{str(p.relative_to(root)):digest(p) for p in sources},
        'config_sha256':digest(path),'dependency_lock_sha256':digest(root/'uv.lock'),'configuration':c,
        'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'cpu_count':os.cpu_count(),
        'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib']},
        'precision':'float64 / complex128','thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
        'command':sys.argv,'boundaries':'unbounded analytical evaluation; finite spheres only for integration, no imposed evolution boundary',
        'units':'c=epsilon_0=mu_0=l0=1, dimensionless fields','elapsed_seconds':time.perf_counter()-start,
        'artifacts_sha256':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'acceptance':m['acceptance'],'elapsed_seconds':manifest['elapsed_seconds']}))
    return all(m['acceptance'].values())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if not run(a.config,a.output):raise SystemExit('Verification acceptance failed; retain metrics for investigation.')


if __name__=='__main__':main()
