"""Reproducible analytical sampling; Apache-2.0. No evolution solver."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import os
import subprocess
import sys
import time
import numpy as np
from scipy.integrate import quad
from .fields import hopfion
from .diagnostics import energy_flow, maxwell_residuals, sphere_integrals, sphere_flux


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def validate(c):
    if c['model_id'] != 'B0-H11':
        raise ValueError('only B0-H11 is implemented')
    for key in ['order', 'local_order']:
        if not isinstance(c[key], int) or not 4 <= c[key] <= 96:
            raise ValueError(f'{key} must be an integer in [4,96]')
    if not 0 < c['local_radius'] <= c['radius'] <= 16:
        raise ValueError('invalid radii')
    if not 2 <= len(c['times']) <= 12 or not np.isfinite(c['times']).all():
        raise ValueError('require 2..12 finite times')
    if not isinstance(c['plot_points'], int) or not 21 <= c['plot_points'] <= 301:
        raise ValueError('invalid plot sampling')
    if not 0 < c['plot_extent'] <= 16:
        raise ValueError('invalid plot extent')
    for key, lo, hi in [('residual_steps', 0, 1), ('flux_orders', 2, 96)]:
        vals = c[key]
        if not 3 <= len(vals) <= 8 or not all(np.isfinite(v) and lo < v <= hi for v in vals):
            raise ValueError(f'invalid {key}')
    if not all(isinstance(v,int) for v in c['flux_orders']):
        raise ValueError('flux orders must be integers')


def plots(c, rows, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt'] = 'eft-s1'
    times = c['times']
    fig, axes = plt.subplots(3, len(times), figsize=(4*len(times), 9), squeeze=False,
                             constrained_layout=True)
    line = np.linspace(-c['plot_extent'], c['plot_extent'], c['plot_points'])
    x, z = np.meshgrid(line, line)
    p = np.stack((x, np.zeros_like(x), z), axis=-1)
    for j,t in enumerate(times):
        e,b = hopfion(p,t)
        u,flow = energy_flow(e,b)
        for k,(v,label) in enumerate([(e,'E projection'),(b,'B projection'),(flow,'Energy flow projection')]):
            ax = axes[k,j]
            im=ax.pcolormesh(x,z,np.log10(np.maximum(u,1e-12)),shading='auto',vmin=-6,vmax=1.3,cmap='magma',rasterized=True)
            skip=(slice(None,None,10),slice(None,None,10))
            norm=np.sqrt(v[...,0]**2+v[...,2]**2)
            vx=np.divide(v[...,0],norm,out=np.zeros_like(norm),where=norm>1e-14)
            vz=np.divide(v[...,2],norm,out=np.zeros_like(norm),where=norm>1e-14)
            ax.quiver(x[skip],z[skip],vx[skip],vz[skip],color='cyan',scale=23)
            ax.set(title=f'{label}, t={t:g}',xlabel='x / l0',ylabel='z / l0',aspect='equal')
    fig.colorbar(im, ax=axes.ravel().tolist(),label='log10 dimensionless energy density')
    fig.suptitle('Analytical (1,1) Hopfion: y=0 slices; arrows normalised, not 3D knot traces')
    fig.savefig(out/'field-slices.svg', metadata={'Date':None})
    fig.savefig(out/'field-slices.png',dpi=130)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7,4),constrained_layout=True)
    ax.plot(times,[r['fixed_sphere_energy_fraction_of_exact_total'] for r in rows],'o-',label='Sphere centred at origin')
    ax.plot(times,[r['moving_sphere_energy_fraction_of_exact_total'] for r in rows],'s-',label='Sphere centred at (0,0,-t/2)')
    ax.set(xlabel='t / (l0/c)',ylabel='Fraction of exact total energy',ylim=(0,1),
           title=f'Energy inside radius {c["local_radius"]:g}; analytical samples')
    ax.legend()
    fig.savefig(out/'localisation.svg',metadata={'Date':None})
    plt.close(fig)


def run(config_path, output):
    start=time.perf_counter()
    config_path=Path(config_path).resolve()
    c=json.loads(config_path.read_text())
    validate(c)
    out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('output directory must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2]
    if not (root/'uv.lock').exists():
        raise ValueError('run from an editable repository installation with uv.lock')
    p=np.random.default_rng(c['seed']).uniform(-1,1,(40,3))
    residual=[]
    for h in c['residual_steps']:
        r=maxwell_residuals(p,.37,h)
        residual.append({'step':h, **{k:float(np.max(np.abs(v))) for k,v in r.items()}})
    flux=[{'order':n,**sphere_flux(1.4,n,.7,(.3,-.2,.1))} for n in c['flux_orders']]
    exact_total=2*np.pi**2
    rows=[]
    for t in c['times']:
        moments=sphere_integrals(c['radius'],c['order'],t)
        local=sphere_integrals(c['local_radius'],c['local_order'],t)
        moving=sphere_integrals(c['local_radius'],c['local_order'],t,(0,0,-t/2))
        rows.append({'time':t, **moments,
            'fixed_sphere_energy_fraction_of_exact_total':local['energy']/exact_total,
            'moving_sphere_energy_fraction_of_exact_total':moving['energy']/exact_total})
    volume=[]
    reference,_=quad(lambda r:64*np.pi*r*r/(1+r*r)**4,0,4,epsabs=1e-11)
    for n in [8,16,32]:
        measured=sphere_integrals(4,n)['energy']
        volume.append({'order':n,'energy':measured,'absolute_quadrature_error':abs(measured-reference)})
    domains=[]
    for radius in [4,8,12]:
        measured=sphere_integrals(radius,64)['energy']
        tail,_=quad(lambda r:64*np.pi*r*r/(1+r*r)**4,radius,np.inf,epsabs=1e-11)
        domains.append({'radius':radius,'energy':measured,'exact_tail_energy':tail,
                        'tail_corrected_error':abs(measured+tail-exact_total)})
    null=[]
    for t in c['times']:
        e,b=hopfion(p,t);u,_=energy_flow(e,b)
        null.append({'time':t,'max_abs_E_dot_B_over_u':float(np.max(np.abs(np.sum(e*b,axis=-1))/u)),
            'max_abs_E2_minus_B2_over_u':float(np.max(np.abs(np.sum(e*e-b*b,axis=-1))/u))})
    metrics={'experiment_id':c['experiment_id'],'exact_total_energy':float(exact_total),
             'residuals':residual,'offcentre_surface_flux':flux,'volume_quadrature':volume,
             'domain_truncation_at_t0':domains,'null_invariants':null,'time_samples':rows,
             'interpretation':'Analytical field evaluation only; no solver, confinement, charge or quantum-spin discovery.'}
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n')
    (out/'config.json').write_bytes(config_path.read_bytes())
    plots(c,rows,out)
    tracked_sources=[root/'pyproject.toml',root/'uv.lock',*sorted((root/'src').rglob('*.py'))]
    manifest={'experiment_id':c['experiment_id'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'repository':'https://github.com/RDHomeProjects/ElectronFieldTopology',
        'commit':git(root,'rev-parse','HEAD'),'dirty_tree':bool(git(root,'status','--porcelain')),
        'source_sha256':{str(p.relative_to(root)):digest(p) for p in tracked_sources},
        'config_sha256':digest(config_path),'dependency_lock_sha256':digest(root/'uv.lock'),
        'python':sys.version,'platform':platform.platform(),'processor':platform.processor(),
        'cpu_count':os.cpu_count(),'thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
        'machine':platform.machine(),'precision':'float64 / complex128',
        'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib']},
        'command':sys.argv,'configuration':c,'elapsed_seconds':time.perf_counter()-start,
        'boundaries':'none imposed; finite integration spheres sample unbounded analytical solution',
        'units':'c=epsilon_0=mu_0=l0=1, unit dimensionless amplitude',
        'artifacts_sha256':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(out),'energy_t0':rows[0]['energy'],
        'flux_finest':flux[-1]['electric_flux'],'elapsed_seconds':manifest['elapsed_seconds']}))
    return metrics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    run(args.config,args.output)


if __name__=='__main__':
    main()
