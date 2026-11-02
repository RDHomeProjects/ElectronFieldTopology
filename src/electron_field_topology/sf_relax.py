"""Bounded static minimisation with immutable configuration and checkpoints."""
import argparse
import json
from pathlib import Path
import time
import hashlib
import importlib.metadata
import os
import platform
import subprocess
import numpy as np
from scipy.optimize import minimize
from .skyrme import Energy,K,NORTH,normalize,coordinates,rational_field,set_boundary,diagnostics


def validate(c):
    if c.get('model_id')!='SF-J2015-static':raise ValueError('static model ID required')
    n=c.get('n');h=c.get('h');iters=c.get('iterations');seconds=c.get('seconds')
    if isinstance(n,bool) or not isinstance(n,int) or not 17<=n<=193 or n%2!=1:raise ValueError('bounded odd grid required')
    if isinstance(h,bool) or not isinstance(h,(int,float)) or not np.isfinite(h) or not .04<=h<=.5 or (n-1)*h/2>12:raise ValueError('bounded spacing/box required')
    if isinstance(iters,bool) or not isinstance(iters,int) or not 1<=iters<=3000:raise ValueError('iteration budget required')
    if isinstance(seconds,bool) or not isinstance(seconds,(int,float)) or not 1<=seconds<=1800:raise ValueError('wall-clock budget required')
    if c.get('expected_q') not in [1,2,17,18,19,22] or isinstance(c.get('expected_q'),bool):raise ValueError('selected charge only')
    if c['expected_q'] in (17,19):
        seed=c.get('seed',{});pair=(5,1) if c['expected_q']==17 else (6,1)
        if seed.get('kind')!='torus72' or (seed.get('alpha'),seed.get('beta'))!=pair:
            raise ValueError('Q17/Q19 require the reviewed K(7,2) numerator')
    if c.get('discretisation','forward') not in ['forward','cell'] or c.get('solver','lbfgs') not in ['lbfgs','sobolev_cg']:raise ValueError('declared method required')
    if not isinstance(c.get('record_every',50),int) or not 1<=c.get('record_every',50)<=100:raise ValueError('record budget')
    amplitude=c.get('perturbation_amplitude',0)
    if isinstance(amplitude,bool) or not isinstance(amplitude,(int,float)) or not 0<=amplitude<=.01:raise ValueError('bounded declared perturbation')
    if not isinstance(c.get('perturbation_seed',35),int):raise ValueError('deterministic perturbation seed')


def run(config,output):
    c=json.loads(Path(config).read_text());validate(c);out=Path(output)
    if out.exists() and any(out.iterdir()):raise ValueError('empty/new output required')
    out.mkdir(parents=True,exist_ok=True);(out/'config.json').write_text(json.dumps(c,indent=2)+'\n')
    root=Path(__file__).resolve().parents[2]
    def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
    sources={str(p.relative_to(root)):digest(p) for p in sorted((root/'src').rglob('*')) if p.suffix in ['.py','.c']}
    provenance={'model_id':'SF-J2015-static','github_base_commit':'5d95ca3f5b39539a55b2286c8623df320c83240c',
        'local_code_commit':git('rev-parse','HEAD'),'dirty_tree':bool(git('status','--porcelain')),
        'source_sha256':sources,'dependency_lock_sha256':digest(root/'uv.lock'),
        'config_sha256':digest(config),'platform':platform.platform(),
        'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],
        'compile_flags':['-O3','-std=c99','-shared','-fPIC','-fopenmp','-lm'],
        'threads':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']},
        'versions':{k:importlib.metadata.version(k) for k in ['numpy','scipy','matplotlib','snappy','spherogram']}}
    (out/'manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
    n=c['n'];h=c['h'];eng=Energy(n,h,out/'native',c.get('discretisation','forward'));start=time.monotonic()
    if c.get('initial_checkpoint'):
        from scipy.ndimage import map_coordinates
        data=np.load(c['initial_checkpoint']);u=data['field'].astype(float)
        oldh=float(data['h']) if 'h' in data else c['initial_checkpoint_h']
        provenance['initial_checkpoint_sha256']=digest(c['initial_checkpoint'])
        if u.shape!=(n,n,n,3) or oldh!=h:
            oldn=len(u);axis=(np.arange(n)-(n-1)/2)*h/oldh+(oldn-1)/2
            points=np.array(np.meshgrid(axis,axis,axis,indexing='ij'))
            u=np.stack([map_coordinates(u[...,i],points,order=1,mode='constant',cval=NORTH[i]) for i in range(3)],axis=-1)
            u=set_boundary(normalize(u))
        else:u=set_boundary(normalize(u))
    else:
        xyz=coordinates(n,h);u=set_boundary(rational_field(xyz,**c['seed']))
        if c.get('perturbation_amplitude',0):
            rng=np.random.default_rng(c.get('perturbation_seed',35));noise=np.zeros_like(u)
            for _ in range(8):
                wave=rng.normal(size=3);phase=rng.uniform(-np.pi,np.pi);polar=rng.normal(size=3)
                noise+=np.sin(xyz@wave+phase)[...,None]*polar
            noise*=np.exp(-(np.linalg.norm(xyz,axis=-1)/5)**4)[...,None]
            noise/=max(float(np.max(np.linalg.norm(noise,axis=-1))),1e-15)
            u=set_boundary(normalize(u+c['perturbation_amplitude']*noise))
    history=[];evaluations=0;last=[u.copy()];status=['iteration_budget']
    def row(u,iteration,initial=False):
        parts,g=eng.evaluate(u);tangent=g-u*np.sum(g*u,axis=-1,keepdims=True)
        diag=diagnostics(u,h)
        rec={'iteration':iteration,'elapsed_seconds':time.monotonic()-start,
             'e2':float(parts[0]),'e4':float(parts[1]),'energy':float(sum(parts)),
             'virial_residual':float(abs(parts[0]-parts[1])/sum(parts)),
             'minimum_quadrature_interpolant_norm':eng.minimum_interpolant_norm,
             'minimum_corner_cone':eng.minimum_corner_cone,
             'tangent_gradient_rms':float(np.sqrt(np.mean(tangent[2:-2,2:-2,2:-2]**2))/(K*h**3)),**diag}
        history.append(rec);(out/'history.json').write_text(json.dumps(history,indent=2)+'\n')
        np.savez_compressed(out/('initial.npz' if initial else 'latest.npz'),field=u.astype(np.float32),h=h)
        if not initial and iteration in [200,500]:np.savez_compressed(out/f'iteration-{iteration}.npz',field=u.astype(np.float32),h=h)
        print(json.dumps(rec),flush=True)
        return rec
    initial=row(u,0,True)
    if abs(abs(initial['hopf_integral'])-c['expected_q'])/c['expected_q']>.05 or initial['minimum_corner_cone']<=0:
        status[0]='initial_charge_unresolved'
    else:
        counter=[0]
        eng.reference=u.copy();eng.reference_margin=initial['minimum_corner_cone']
        def objective(v):
            nonlocal evaluations
            evaluations+=1
            if time.monotonic()-start>c['seconds']:raise TimeoutError('wall-clock budget')
            return eng.objective(v)
        def callback(v):
            counter[0]+=1;last[0]=normalize(v.reshape(n,n,n,3))
            eng.reference=last[0].copy();eng.reference_margin=eng.minimum_corner_cone
            if counter[0]%c.get('record_every',50)==0:
                rec=row(last[0],counter[0])
                if abs(abs(rec['hopf_integral'])-c['expected_q'])/c['expected_q']>.10:
                    status[0]='charge_resolution_lost';raise RuntimeError('charge resolution lost')
        try:
            if c.get('solver','lbfgs')=='sobolev_cg':
                from .sf_minimize import minimize_static
                def cg_callback(field,iteration):callback(field.ravel())
                last[0],result=minimize_static(eng,u,c['iterations'],cg_callback,
                    lambda:time.monotonic()-start>c['seconds'],length=c.get('precondition_length',.5))
                status[0]=result['status'];evaluations=result['evaluations'];message='Projected Sobolev CG: '+status[0]
            else:
                result=minimize(objective,u.ravel(),jac=True,method='L-BFGS-B',callback=callback,
                    options={'maxiter':c['iterations'],'maxcor':c.get('maxcor',4),'ftol':1e-13,'gtol':1e-8,'maxls':30})
                last[0]=normalize(result.x.reshape(n,n,n,3))
                status[0]='optimizer_reported_success' if result.success else 'optimizer_limit'
                message=str(result.message)
        except (TimeoutError,RuntimeError,ValueError) as error:
            if isinstance(error,TimeoutError):status[0]='time_budget'
            elif isinstance(error,ValueError):status[0]='invalid_interpolant'
            message=str(error)
        final=row(last[0],counter[0])
    if status[0]=='initial_charge_unresolved':final=initial;message='No optimisation: initial Hopf integral or positive cell-hemisphere resolution gate fails.'
    report={'status':status[0],'message':message,'config':c,'initial':initial,'final':final,
            'evaluations':evaluations,'elapsed_seconds':time.monotonic()-start,'history':history,
            'reproduction_status':'not_certified: topology, stationary and convergence gates must be assessed separately',
            'scope':'static energy minimisation, not physical evolution'}
    np.savez_compressed(out/'final.npz',field=last[0].astype(np.float32),h=h)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    provenance['artifacts_sha256']={p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'}
    provenance['source_unchanged_during_run']=sources=={str(p.relative_to(root)):digest(p) for p in sorted((root/'src').rglob('*')) if p.suffix in ['.py','.c']}
    (out/'manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('FINAL',status[0],flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--output',required=True)
    p.add_argument('--backend',choices=['cpu','gpu'],default='cpu')
    p.add_argument('--resume-checkpoint',help='GPU: continue a saved field into a new output directory')
    a=p.parse_args()
    if a.backend=='gpu':
        from .sf_gpu_relax import run as gpu_run
        result=gpu_run(a.config,a.output,a.resume_checkpoint)
        if result['status']=='interrupted':raise SystemExit(130)
    else:
        if a.resume_checkpoint:p.error('--resume-checkpoint currently requires --backend gpu')
        run(a.config,a.output)


if __name__=='__main__':main()
