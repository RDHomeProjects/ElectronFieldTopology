"""Same-field same-box SF method/alignment comparison; no physical steps."""
if not __debug__:raise RuntimeError('Run without Python optimization')
import argparse,gc,hashlib,html,json,secrets,subprocess,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
try:
    from . import sf_q3_sampling_boundary as boundary,sf_d2_comparison as d2,sf_method_observables as obs
except ImportError:
    import sf_q3_sampling_boundary as boundary,sf_d2_comparison as d2,sf_method_observables as obs
import numpy as np
stamp,save,sha,need=boundary.stamp,boundary.save,boundary.sha,boundary.need
BASE_SHA='8153def6438d84aa480b14d125b9e6b8a8dd933423e8efedc9440e955f03a595'
def analyze(n,v,g,k,method):
    spatial=k if method=='D4' else d2;nd,a=spatial.acceleration(n,v,g)
    sr4=lambda n,w,g:boundary.metrics.sigma_rate(n,w,k.NORTH,g)
    sr=sr4 if method=='D4' else d2.sigma_rate
    native=obs.evaluate(n,v,nd,a,g,spatial,sr,probe=True)
    common=native if method=='D4' else obs.evaluate(n,v,nd,a,g,k,sr4,probe=False)
    # Instantaneous native Hamiltonian balance checks the variational vector
    # field, not the scientific motion gate. Common D4 H need not be conserved by D2.
    need(abs(native['hamiltonian_rate'])/max(abs(native['hamiltonian']),1)<1e-9,'Native Hamiltonian directional balance failed')
    return {'native':native,'common_D4_observer':common,'common_equals_native':method=='D4','constraint_acceleration_error':float(np.max(abs(np.sum(n*a,-1)+np.sum(v*v,-1))))}
def report(out,record):
    rows=''
    for r in record['cases']:
        a=r['axis']
        for method,data in r['methods'].items():
            for label in ['native','common_D4_observer']:
                q=data[label];err=100*np.linalg.norm(np.array(q['centroid_rate'])-np.eye(3)[a]*.3)/.3
                rows+=f'<tr><td>{r["id"]}</td><td>{method}</td><td>{label}</td><td>{err:.8g}</td><td>{q["centroid_rate"][a]:.11g}</td><td>{q["continuity_residual_physical_l2"]:.6g}</td></tr>'
    (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>SF method and alignment comparison</title><style>body{font:16px/1.6 system-ui;margin:30px}td,th{padding:8px;border-bottom:1px solid #ddd}</style><h1>SF initial method and alignment comparison</h1><p>'+html.escape(json.dumps(record.get('finished_at',record['recorded_at'])))+'</p><p>D2 and D4 are two discrete actions for the same continuum model, using identical reconstructed n/v and geometry. No physical steps or new acceptance. D4 common measurement is shared and independently qualified; native Hamiltonians are method-specific.</p><table><tr><th>Case</th><th>Method</th><th>Observer</th><th>Vector speed error %</th><th>Axial rate</th><th>Residual physical L2</th></tr>'+rows+'</table><p>Report every alignment. No favorable-phase selection or phase averaging replaces the original gate. A phase range is not a statistical uncertainty interval. Lab-only refinement leaves the rest-field resolution unchanged.</p></html>')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--case',action='append');p.add_argument('--baseline',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);a=p.parse_args();repo=a.repo.expanduser().resolve()
    subprocess.run(['git','merge-base','--is-ancestor',boundary.prior.MERGE,'HEAD'],cwd=repo,check=True);need(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo,text=True).strip(),'Tracked checkout changes found')
    need(sha(a.baseline)==BASE_SHA,'Boundary evidence ZIP differs')
    with zipfile.ZipFile(a.baseline) as z:baseline=json.loads(z.read('study.json'))
    source=repo/'artifacts/s5-b/010-intermediate-q-survey'/boundary.RUN;need(sha(source/'evidence.zip')==boundary.prior.EVIDENCE,'Native source evidence differs')
    with zipfile.ZipFile(source/'evidence.zip') as z:d=json.loads(z.read('campaign.json'))
    kernels=['sf_time.py','sf_dynamics.py','skyrme.py','sf_reconstruction.py']
    for name in kernels:need(sha(repo/'src/electron_field_topology'/name)==d['source_sha256'][name],'Measured kernel changed: '+name)
    for name,h in d['dependency_sha256'].items():need(sha(repo/name)==h,'Measured lock changed: '+name)
    rr=d['rest']['q3-axial-fine-warm'];rp=source/rr['checkpoint'];need(sha(rp)==rr['checkpoint_sha256']==baseline['rest_checkpoint_sha256'],'Retained rest seal differs')
    sys.path.insert(0,str(repo/'src'));from electron_field_topology import sf_time as k,sf_reconstruction as rec
    with np.load(rp,allow_pickle=False) as z:rest=z['field'].copy()
    rg=k.Grid((rr['nodes'],)*3,(rr['length'],)*3,'fixed');need(rest.dtype==np.float64 and rest.shape==rg.shape+(3,) and np.isfinite(rest).all(),'Rest precision/shape invalid')
    need(np.max(abs(np.linalg.norm(rest,axis=-1)-1))<1e-10 and np.max(abs(rest[rg.fixed_mask()]-k.NORTH))<1e-10,'Rest constraints fail')
    plan=json.loads(a.plan.read_text());expected=[dict(id=['x','y','z'][axis]+f'-phase{int(phase*100):02d}',axis=axis,nodes=169,pad=14,phase=phase) for axis in [2,0] for phase in [0.,.25,.5,.75]];need(plan==expected,'Bounded alignment plan differs')
    selected=a.case or [c['id'] for c in plan];need(len(selected)==len(set(selected)) and set(selected)<={c['id'] for c in plan},'Unknown/duplicate case')
    rest_controls={}
    for method,spatial in [('D4',k),('D2',d2)]:
        _,ra=spatial.acceleration(rest,np.zeros_like(rest),rg);rest_controls[method]={'acceleration_max':float(np.max(np.linalg.norm(ra,axis=-1))),'acceleration_rms':float(np.sqrt(np.mean(ra*ra))),'scope':'Same retained rest field, zero rate; not assumed to be a D2 equilibrium or assigned new admission.'};del ra;gc.collect()
    qp=repo/'artifacts/METHOD-QUALIFICATION-CURRENT';need(qp.is_file(),'Run qualification first');qualification=Path(qp.read_text().strip());qr=json.loads(qualification.read_text());need(qr['status']=='qualification_passed' and qr['kernel_sha256']=={n:d['source_sha256'][n] for n in kernels},'Qualification/source mismatch')
    out=repo/'artifacts/q3-method-alignment'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4));out.mkdir(parents=True);(repo/'artifacts/Q3-METHOD-ALIGNMENT-CURRENT').write_text(str(out)+'\n')
    record={'recorded_at':stamp(),'status':'working','output':str(out),'source_run':boundary.RUN,'source_evidence_sha256':boundary.prior.EVIDENCE,'baseline_sha256':BASE_SHA,'rest_checkpoint_sha256':rr['checkpoint_sha256'],'kernel_sha256':{n:d['source_sha256'][n] for n in kernels},'dependency_sha256':d['dependency_sha256'],'selected_cases':selected,'same_rest_zero_rate_controls':rest_controls,'python':sys.version,'numpy':np.__version__,'plan_sha256':sha(a.plan),'qualification_sha256':sha(qualification),'implementation_sha256':{Path(m.__file__).name:sha(Path(m.__file__)) for m in [boundary,boundary.prior,boundary.metrics,d2,obs]},'script_sha256':sha(Path(__file__)),'cases':[],'scope':'Initial vector fields only. Two discrete actions, same continuum model and reconstructed state. No SF time integration or changed gates.'}
    def progress():save(out/'study.json',record);save(out/'status.json',{k:v for k,v in record.items() if k!='cases'}|{'completed_alignments':len(record['cases'])})
    progress()
    try:
        for c in plan:
            if c['id'] not in selected:continue
            print(json.dumps({'recorded_at':stamp(),'message':'Reconstructing common state',**c}),flush=True)
            n,v,g,base,proj,shift=boundary.reconstruct(rest,rg,c,k,rec);state=boundary.prior.state_sha(n,v)
            if not c['phase']:
                old=next(r for r in baseline['cases'] if r['axis']==c['axis'] and r['id'].endswith('169-refine'));need(state==old['state_sha256'] and list(g.lengths)==old['lengths'],'Finest zero-phase state/box differs')
            row={**c,'grid':list(g.shape),'lengths':list(g.lengths),'spacing':list(g.spacing),'projection':proj,'sample_shift':shift,'state_sha256':state,'methods':{}}
            for method in ['D4','D2']:
                print(json.dumps({'recorded_at':stamp(),'case':c['id'],'message':'Evaluating native and common measurements','method':method}),flush=True)
                row['methods'][method]=analyze(n,v,g,k,method)
                if method=='D4' and not c['phase']:
                    q=row['methods'][method]['native']
                    for current,previous in [('continuum_energy','continuum_energy'),('hamiltonian','hamiltonian'),('centroid_rate','continuum_centroid_rate')]:np.testing.assert_allclose(q[current],old[previous],rtol=2e-11,atol=2e-12)
                gc.collect()
            record['cases'].append(row);progress();report(out,record);del n,v;gc.collect()
        record.update(status='complete_pending_review',finished_at=stamp());progress();report(out,record)
        modules=[Path(__file__),Path(boundary.__file__),Path(boundary.prior.__file__),Path(boundary.metrics.__file__),Path(d2.__file__),Path(obs.__file__)]
        for f in modules:(out/f.name).write_bytes(f.read_bytes())
        (out/'qualification.json').write_bytes(qualification.read_bytes());(out/'CASE_PLAN.json').write_bytes(a.plan.read_bytes());(out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file()))
        with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.iterdir()):
                if f.is_file() and f.name!='evidence.zip':z.write(f,f.name)
        print('Upload: '+str(out/'evidence.zip'));print('Browser report: '+str(out/'REPORT.html'))
    except BaseException as e:record.update(status='error',error=str(e),finished_at=stamp());progress();raise
if __name__=='__main__':main()
