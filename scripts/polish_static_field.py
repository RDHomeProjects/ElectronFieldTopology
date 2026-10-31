"""Bounded L-BFGS polishing of a resolved static checkpoint.

The objective is unchanged. Accept a field only after an independent gradient
and continuous-step check; never promote a scipy success flag to stationarity.
"""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from electron_field_topology.skyrme import Energy,K,normalize,diagnostics


def run(case,output,seconds=600,iterations=500):
    if not 1<=seconds<=900 or not 1<=iterations<=1500:raise ValueError('bounded polishing budget')
    source=Path(case);out=Path(output)
    if out.exists() and any(out.iterdir()):raise ValueError('new/empty output required')
    out.mkdir(parents=True,exist_ok=True);config=json.loads((source/'config.json').read_text())
    config.update(case=config['case']+'-polish',solver='bounded-lbfgs-polish',seconds=seconds,iterations=iterations,
                  initial_checkpoint=str(source/'final.npz'))
    (out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    checkpoint=source/'final.npz';data=np.load(checkpoint);u=normalize(data['field'].astype(float));h=float(data['h']);n=len(u)
    eng=Energy(n,h,out/'native',method='cell');start=time.monotonic();history=[];counter=0;last=u.copy()
    def row(field,iteration):
        parts,g=eng.evaluate(field);tangent=g-field*np.sum(g*field,axis=-1,keepdims=True)
        r={'iteration':iteration,'energy':float(sum(parts)),'e2':float(parts[0]),'e4':float(parts[1]),
           'virial_residual':float(abs(parts[0]-parts[1])/sum(parts)),
           'tangent_gradient_rms':float(np.sqrt(np.mean(tangent[2:-2,2:-2,2:-2]**2))/(K*h**3)),
           'minimum_corner_cone':eng.minimum_corner_cone,'elapsed_seconds':time.monotonic()-start,**diagnostics(field,h)}
        history.append(r);(out/'history.json').write_text(json.dumps(history,indent=2)+'\n');print(json.dumps(r),flush=True)
        return r
    initial=row(u,0);margin=eng.minimum_corner_cone;maximum_step=0.;status='iteration_budget'
    def objective(raw):
        if time.monotonic()-start>seconds:raise TimeoutError('polishing time budget')
        return eng.objective(raw)
    def callback(raw):
        nonlocal last,counter,margin,maximum_step
        candidate=normalize(raw.reshape(n,n,n,3));step=float(np.max(np.linalg.norm(candidate-last,axis=-1)))
        if step>=min(.2,.5*margin):raise RuntimeError('accepted-step continuity check failed; previous checkpoint retained')
        maximum_step=max(maximum_step,step);last=candidate;counter+=1;margin=eng.minimum_corner_cone
        if counter%50==0:row(last,counter)
    try:
        result=minimize(objective,u.ravel(),jac=True,method='L-BFGS-B',callback=callback,
                        options={'maxiter':iterations,'maxcor':3,'ftol':1e-15,'gtol':1e-10,'maxls':40})
        message=str(result.message);status='optimizer_reported_success' if result.success else 'optimizer_limit'
    except (RuntimeError,TimeoutError,ValueError) as error:
        status='time_budget' if isinstance(error,TimeoutError) else 'polishing_rejected';message=str(error)
    final=row(last,counter)
    if final['tangent_gradient_rms']<1e-3 and final['minimum_corner_cone']>0:status='gradient_stationary'
    np.savez_compressed(out/'final.npz',field=last.astype(np.float32),h=h)
    report={'config':config,'initial':initial,'final':final,'status':status,'message':message,'history':history,
            'maximum_accepted_nodal_step':maximum_step,'elapsed_seconds':time.monotonic()-start,
            'scope':'unchanged static cell energy; accepted steps independently checked; no physical time'}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    root=Path(__file__).resolve().parents[1]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={'initial_checkpoint_sha256':sha(checkpoint),'script_sha256':sha(Path(__file__)),
              'source_sha256':{str(p.relative_to(root)):sha(p) for p in sorted((root/'src').rglob('*')) if p.suffix in ['.py','.c']},
              'local_code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
              'dirty_tree':bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()),
              'artifacts_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',required=True);p.add_argument('--output',required=True)
    p.add_argument('--seconds',type=int,default=600);p.add_argument('--iterations',type=int,default=500)
    a=p.parse_args();run(a.case,a.output,a.seconds,a.iterations)
