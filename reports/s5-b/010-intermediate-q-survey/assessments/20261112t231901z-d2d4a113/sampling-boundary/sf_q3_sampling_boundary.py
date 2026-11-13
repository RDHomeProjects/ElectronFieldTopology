"""Read-only Q3 sampling/boundary controls. Neutral SF, +---, c=1 model units.
No relaxation, physical-time steps, altered historical gates or fitted beta.
"""
import argparse,gc,hashlib,html,json,secrets,subprocess,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
try:
    from . import sf_q3_initialization as prior,sf_initial_centroid as metrics
except ImportError:
    import sf_q3_initialization as prior,sf_initial_centroid as metrics
stamp,save,sha,need=prior.stamp,prior.save,prior.sha,prior.need
RUN=prior.RUN

def recipes():
    return [dict(id=['x','y','z'][a]+label,axis=a,nodes=n,pad=p,phase=f) for a in [2,0] for label,n,p,f in [('121-native',121,0,0.),('121-pad',121,12,0.),('145-native',145,0,0.),('145-pad',145,12,0.),('145-half',145,12,.5),('169-refine',169,14,0.)]]

def reconstruct(rest,rg,c,k,reconstruction):
    axis=c['axis'];base=prior.lab_grid(rg,c['nodes'],.3,axis,k);pad=c['pad']
    if c['nodes']==169:
        # Refine within exactly the 145-pad physical box, rather than shrinking
        # the vacuum margin when h changes. This is not a paired padding case.
        reference=prior.lab_grid(rg,145,.3,axis,k)
        g=k.Grid(tuple(n+2*pad for n in base.shape),tuple(l+24*h for l,h in zip(reference.lengths,reference.spacing)),'fixed')
        axes=[-l/2+np.arange(n)*h for n,l,h in zip(g.shape,g.lengths,g.spacing)]
    else:
        g=k.Grid(tuple(n+2*pad for n in base.shape),tuple(l+2*pad*h for l,h in zip(base.lengths,base.spacing)),'fixed')
        need(np.allclose(g.spacing,base.spacing,rtol=0,atol=1e-15),'Padding changed lab spacing')
        axes=[-l/2+(np.arange(n)-pad)*h for n,l,h in zip(g.shape,base.lengths,base.spacing)]
    points=np.stack(np.meshgrid(*axes,indexing='ij'),-1)
    shift=c['phase']*g.spacing[axis];points[...,axis]+=shift;gamma=1/np.sqrt(1-.3**2);points[...,axis]*=gamma
    raw_n,d=reconstruction.sample_cubic(rest,rg,points,axis);del points
    raw_v=-gamma*.3*d;del d
    n,v=k.retract(raw_n,raw_v,g);fixed=g.fixed_mask();free=~fixed
    projection={'field_max':float(np.max(abs(n-raw_n))),'rate_max':float(np.max(abs(v-raw_v))),'free_field_max':float(np.max(abs(n[free]-raw_n[free]))),'free_rate_max':float(np.max(abs(v[free]-raw_v[free]))),'raw_fixed_field_max':float(np.max(abs(raw_n[fixed]-[0.,0.,1.]))),'raw_fixed_rate_max':float(np.max(abs(raw_v[fixed])))}
    del raw_n,raw_v
    return n,v,g,base,projection,shift

def calculate(rest,rg,c,k,reconstruction,cache=None):
    n,v,g,base,projection,shift=reconstruct(rest,rg,c,k,reconstruction)
    r=metrics.evaluate(n,v,g,k);axis=c['axis'];r.update(c,grid=list(g.shape),lengths=list(g.lengths),spacing=list(g.spacing),native_grid=list(base.shape),native_spacing=list(base.spacing),projection=projection,lab_sample_shift=shift,state_sha256=prior.state_sha(n,v))
    r['initial_speed_error_percent']=float(100*np.linalg.norm(np.array(r['continuum_centroid_rate'])-np.eye(3)[axis]*.3)/.3)
    if c['pad'] and not c['phase'] and c['nodes'] in [121,145]:
        # Native coarse walls impose north values where a larger box need not.
        # Report that difference instead of imposing the old wall on the padding.
        native=dict(c,pad=0);bn,bv,_,_,_,_=reconstruct(rest,rg,native,k,reconstruction)
        sl=tuple(slice(c['pad'],c['pad']+count) for count in base.shape);cn,cv=n[sl],v[sl];free=~base.fixed_mask()
        r['embedded_native_comparison']={'free_field_max':float(np.max(abs(cn[free]-bn[free]))),'free_rate_max':float(np.max(abs(cv[free]-bv[free]))),'all_field_max':float(np.max(abs(cn-bn))),'all_rate_max':float(np.max(abs(cv-bv))),'scope':'Same nominal h and same interior coordinates; all-node difference includes removal of the former held layers.'}
        need(r['embedded_native_comparison']['free_field_max']<1e-12 and r['embedded_native_comparison']['free_rate_max']<1e-12,'Padding changed free interior reconstruction')
        del bn,bv,cn,cv
    # Eulerian common cube only reports truncated density integrals; P/E here
    # is a proxy, not an isolated-region velocity or an acceptance criterion.
    data=k.densities(n,v,g);coords=g.points();roi=np.all(abs(coords)<=6.+1e-12,axis=-1);dv=float(np.prod(g.spacing))
    r['common_cube']={'half_width':6.,'nodes':int(np.sum(roi)),'continuum_energy':float(np.sum(data['energy_density'][roi])*dv),'momentum':(np.sum(data['energy_flux'][roi],axis=0)*dv).tolist(),'scope':'Fixed physical cube, native nodal quadrature; counts and boundary sampling vary with h and phase. Truncated integrals only, not isolation/velocity evidence.'}
    del data,coords,roi,n,v;gc.collect();return r

def report(out,rec):
    rows=''
    for r in rec['cases']:
        a=r['axis'];rows+='<tr><td>'+r['id']+'</td><td>'+str(r['grid'])+'</td><td>'+format(r['initial_speed_error_percent'],'.8g')+'</td><td>'+format(100*(r['momentum_over_continuum_energy'][a]-.3)/.3,'.7g')+'</td><td>'+format(100*r['weighted_continuity_residual_over_energy'][a]/.3,'.7g')+'</td><td>'+format(r['projection']['field_max'],'.5g')+'</td></tr>'
    (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Q3 sampling and boundary diagnostic</title><style>body{font:16px/1.6 system-ui;margin:28px;color:#18324a}td,th{padding:9px;border-bottom:1px solid #ddd}</style><h1>Q3 sampling and boundary diagnostic</h1><p>'+html.escape(json.dumps(rec.get('finished_at',rec['recorded_at'])))+'</p><p>Same sealed rest field and beta 0.3. No physical-time evolution or new pass/fail decisions. Percent columns use requested beta as denominator. A small net error can reflect cancellation.</p><table><tr><th>Case</th><th>Grid</th><th>Initial vector error %</th><th>Signed axial P/E offset %</th><th>Axial residual contribution %</th><th>Boundary projection maximum</th></tr>'+rows+'</table><p>pad preserves nominal lab spacings and interior coordinates, within floating precision. half translates the sampling phase by half an axial lab cell in the padded box, shifting the profile relative to fixed walls. It is not physical evolution or a pure change of coordinate labels. 169-refine uses exactly the 145-pad physical box with finer lab sampling; the 145-cubed rest field remains fixed. Common-cube integrals are truncated diagnostics.</p></html>')

def main():
    if not __debug__:raise RuntimeError('Run without Python optimization')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--case',action='append');p.add_argument('--plan',type=Path,default=Path(__file__).with_name('CASE_PLAN.json'));a=p.parse_args();repo=a.repo.expanduser().resolve();allcases=json.loads(a.plan.read_text());need(allcases==recipes(),'Case plan differs from bounded twelve-case specification');chosen=a.case or [c['id'] for c in allcases]
    need(len(chosen)==len(set(chosen)) and set(chosen)<={c['id'] for c in allcases},'Unknown/duplicate case')
    subprocess.run(['git','merge-base','--is-ancestor',prior.MERGE,'HEAD'],cwd=repo,check=True)
    need(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo,text=True).strip(),'Tracked checkout changes found')
    source=repo/'artifacts/s5-b/010-intermediate-q-survey'/RUN;need(sha(source/'evidence.zip')==prior.EVIDENCE,'Native evidence differs')
    with zipfile.ZipFile(source/'evidence.zip') as z:d=json.loads(z.read('campaign.json'))
    need(json.loads((source/'campaign.json').read_text())==d,'Loose campaign differs')
    kernels=['sf_time.py','sf_dynamics.py','skyrme.py','sf_reconstruction.py']
    for name in kernels:need(sha(repo/'src/electron_field_topology'/name)==d['source_sha256'][name],'Measured kernel changed: '+name)
    for name,h in d['dependency_sha256'].items():need(sha(repo/name)==h,'Measured lock changed: '+name)
    sys.path.insert(0,str(repo/'src'));from electron_field_topology import sf_time as k,sf_reconstruction as reconstruction
    rr=d['rest']['q3-axial-fine-warm'];path=source/rr['checkpoint'];need(sha(path)==rr['checkpoint_sha256'],'Retained rest seal differs')
    with np.load(path,allow_pickle=False) as z:rest=z['field'].copy()
    rg=k.Grid((rr['nodes'],)*3,(rr['length'],)*3,'fixed');need(rest.dtype==np.float64 and rest.shape==rg.shape+(3,) and np.isfinite(rest).all(),'Invalid rest precision/shape')
    need(np.max(abs(rest[rg.fixed_mask()]-[0.,0.,1.]))<1e-10 and np.max(abs(np.linalg.norm(rest,axis=-1)-1))<1e-10,'Rest constraints fail')
    out=repo/'artifacts/q3-sampling-boundary'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4));out.mkdir(parents=True);(repo/'artifacts/Q3-SAMPLING-BOUNDARY-CURRENT').write_text(str(out)+'\n')
    rec={'recorded_at':stamp(),'status':'working','output':str(out),'source_run':RUN,'source_evidence_sha256':prior.EVIDENCE,'rest_checkpoint_sha256':rr['checkpoint_sha256'],'kernel_sha256':{n:d['source_sha256'][n] for n in kernels},'dependency_sha256':d['dependency_sha256'],'script_sha256':sha(Path(__file__)),'helper_sha256':{Path(m.__file__).name:sha(Path(m.__file__)) for m in [prior,metrics]},'selected_cases':chosen,'case_plan_sha256':sha(a.plan),'python':sys.version,'numpy':np.__version__,'cases':[],'scope':'Read-only sampling/boundary study; fixed rest representation; no physical steps, changed gates or acceptance flags.'}
    def progress():save(out/'study.json',rec);save(out/'status.json',{k:v for k,v in rec.items() if k!='cases'}|{'completed_cases':len(rec['cases'])})
    progress()
    try:
        for c in allcases:
            if c['id'] not in chosen:continue
            print(json.dumps({'recorded_at':stamp(),'message':'Evaluating sampling/boundary case',**c}),flush=True)
            r=calculate(rest,rg,c,k,reconstruction)
            if c['nodes'] in [121,145] and not c['pad']:
                if c['nodes']==145:
                    key='q3-axial-fine-warm-'+['x','y','z'][c['axis']]+'-dt0.01';need(r['state_sha256']==d['cases'][key]['initial_state_sha256'],'Historical fine initialized state differs');r['historical_state_matches']=True
            rec['cases'].append(r);progress();report(out,rec)
        rec.update(status='complete_pending_review',finished_at=stamp());progress();report(out,rec)
        for mod in [prior,metrics]:f=Path(mod.__file__);(out/f.name).write_bytes(f.read_bytes())
        (out/'CASE_PLAN.json').write_bytes(a.plan.read_bytes());(out/Path(__file__).name).write_bytes(Path(__file__).read_bytes());(out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file()))
        with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.iterdir()):
                if f.is_file() and f.name!='evidence.zip':z.write(f,f.name)
        print('Upload: '+str(out/'evidence.zip'));print('Browser report: '+str(out/'REPORT.html'))
    except BaseException as error:rec.update(status='error',error=str(error),finished_at=stamp());progress();raise
if __name__=='__main__':main()
