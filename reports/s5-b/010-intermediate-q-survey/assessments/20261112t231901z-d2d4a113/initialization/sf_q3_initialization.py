"""Controlled Q3 lab-sampling diagnosis; no relaxation or physical-time steps.

Uses the repository's normalized cubic Hermite reconstruction and original D4
vector field. All lengths, times and velocities are in neutral SF model units.
"""
import argparse,gc,hashlib,html,json,secrets,subprocess,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
RUN='20261109t134425z-89d28344'
MERGE='50a1337739f5063bfb459c8d7111077b9ccffd33'
EVIDENCE='c066b7f2bab8308cf68945b0b6e5de837585775647634ffd721b3e84bee87517'
def need(x,s):
    if not x:raise ValueError(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def state_sha(n,v):
    h=hashlib.sha256()
    for a in [n,v]:h.update(memoryview(np.ascontiguousarray(a,dtype='<f8')))
    return h.hexdigest()
def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def save(p,x):
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');temp.replace(p)
def lab_grid(g,count,beta,axis,k):
    shape=[count]*3;shape[axis]=2*int(np.ceil((count-1)/np.sqrt(1-beta*beta)/2))+1
    return k.Grid(tuple(shape),g.lengths,'fixed')
def derivative_probes(rest,rg,g,axis,beta,reconstruction):
    # Probe up to 512 deterministic interior lab nodes near the core. Restrict
    # to the common interior cube to avoid conflating fixed-layer projection.
    axes=[np.linspace(-min(rg.lengths)/4,min(rg.lengths)/4,8) for _ in range(3)]
    points=np.stack(np.meshgrid(*axes,indexing='ij'),-1).reshape(-1,3)
    # Off-node coordinates expose interpolant derivatives instead of only nodal slopes.
    points+=np.array(rg.spacing)*np.array([.137,.219,.311])
    gamma=1/np.sqrt(1-beta*beta);rp=points.copy();rp[:,axis]*=gamma
    n,d=reconstruction.sample_cubic(rest,rg,rp,axis);v=-gamma*beta*d
    rows=[]
    for eps in [1e-3,5e-4,2.5e-4]:
        dx=eps*rg.spacing[axis];delta=np.eye(3)[axis]*dx
        plus,_=reconstruction.sample_cubic(rest,rg,rp+delta,axis);minus,_=reconstruction.sample_cubic(rest,rg,rp-delta,axis)
        ds=(plus-minus)/(2*dx)
        dt=eps*rg.spacing[axis]/max(abs(beta)*gamma,1e-30)
        plus,_=reconstruction.sample_cubic(rest,rg,rp-gamma*beta*np.eye(3)[axis]*dt,axis);minus,_=reconstruction.sample_cubic(rest,rg,rp+gamma*beta*np.eye(3)[axis]*dt,axis)
        vt=(plus-minus)/(2*dt)
        rows.append({'epsilon_in_rest_spacing':eps,'space_absolute_rms':float(np.sqrt(np.mean((ds-d)**2))),'space_relative_l2':float(np.linalg.norm(ds-d)/max(np.linalg.norm(d),1e-30)),'time_absolute_rms':float(np.sqrt(np.mean((vt-v)**2))),'time_relative_l2':float(np.linalg.norm(vt-v)/max(np.linalg.norm(v),1e-30))})
    return {'sample_points':len(points),'scope':'Centered finite perturbations of the prescribed interpolant, not evolved states; deterministic interior off-node points. C1 Hermite knot crossings can reduce apparent order.','rows':rows}
def calculate(rest,rg,count,axis,k,reconstruction,metrics):
    beta=.3;g=lab_grid(rg,count,beta,axis,k)
    raw_n,raw_v=reconstruction.boosted_cubic(rest,rg,g,beta,axis);n,v=k.retract(raw_n,raw_v,g);fixed=g.fixed_mask();free=~fixed
    projection={'field_max':float(np.max(abs(n-raw_n))),'rate_max':float(np.max(abs(v-raw_v))),'free_field_max':float(np.max(abs(n[free]-raw_n[free]))),'free_rate_max':float(np.max(abs(v[free]-raw_v[free]))),'raw_fixed_field_max':float(np.max(abs(raw_n[fixed]-[0,0,1]))),'raw_fixed_rate_max':float(np.max(abs(raw_v[fixed])))}
    del raw_n,raw_v
    r=metrics.evaluate(n,v,g,k);r.update(nominal_lab_nodes=count,axis=axis,beta=beta,grid=list(g.shape),spacing=list(g.spacing),lengths=list(g.lengths),state_sha256=state_sha(n,v),projection=projection)
    r['initial_speed_error_percent']=float(100*np.linalg.norm(np.array(r['continuum_centroid_rate'])-np.eye(3)[axis]*beta)/beta)
    # D4 translation relation is a diagnostic of lab spatial sampling, not an
    # alternative boost initializer or an exact lattice Lorentz symmetry.
    dv=v+beta*k.derivative(n-np.array([0.,0.,1.]),g.spacing[axis],axis,g.boundary)
    r['translation_rate_mismatch_relative_l2']=float(np.linalg.norm(dv[free])/max(np.linalg.norm(v[free]),1e-30))
    r['derivative_probes']=derivative_probes(rest,rg,g,axis,beta,reconstruction)
    del n,v,dv;gc.collect();return r
def report(out,record):
    rows=''
    for r in record['cases']:
        a=r['axis'];rows+='<tr><td>'+str(r['nominal_lab_nodes'])+'</td><td>'+['x','y','z'][a]+'</td><td>'+str(r['grid'])+'</td><td>'+format(r['initial_speed_error_percent'],'.8g')+'</td><td>'+format(r['momentum_over_continuum_energy'][a],'.10g')+'</td><td>'+format(r['weighted_continuity_residual_over_energy'][a],'.8g')+'</td><td>'+str(r.get('historical_state_matches'))+'</td></tr>'
    (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Q3 fixed-rest initialization study</title><style>body{font:16px/1.6 system-ui;margin:32px;color:#18324a}td,th{padding:10px;border-bottom:1px solid #ddd}</style><h1>Q3 fixed-rest initialization study</h1><p>'+html.escape(json.dumps(record['recorded_at']))+'</p><p>Same retained fine rest field, box, beta 0.3 and cubic reconstruction. Only lab sampling and direction vary. No physical evolution or new admission decision.</p><table><tr><th>Nominal lab nodes</th><th>Axis</th><th>Actual grid</th><th>Initial speed error %</th><th>Axial P/E proxy</th><th>Weighted residual/E</th><th>Original fine state matches</th></tr>'+rows+'</table><p>Changing lab sampling does not refine the retained rest field. Projection changes are reported. No Richardson order or continuum convergence is inferred from this diagnostic alone. JSON includes all derivatives, projection corrections and density-rate checks.</p></html>')
def main():
    if not __debug__:raise RuntimeError('Run without Python optimization')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--nodes',type=int,nargs='+',default=[97,121,145]);p.add_argument('--axes',type=int,nargs='+',default=[2,0]);a=p.parse_args();repo=a.repo.expanduser().resolve()
    need(set(a.nodes)<=set([97,121,145]) and len(set(a.nodes))==len(a.nodes),'Use unique nominal node counts from 97,121,145')
    need(set(a.axes)<=set([0,2]) and len(set(a.axes))==len(a.axes),'Use unique axes 0/x and 2/z')
    subprocess.run(['git','merge-base','--is-ancestor',MERGE,'HEAD'],cwd=repo,check=True)
    need(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo,text=True).strip(),'Tracked source checkout changes found')
    source=repo/'artifacts/s5-b/010-intermediate-q-survey'/RUN;need(sha(source/'evidence.zip')==EVIDENCE,'Source compact evidence differs')
    with zipfile.ZipFile(source/'evidence.zip') as z:campaign=json.loads(z.read('campaign.json'))
    need(json.loads((source/'campaign.json').read_text())==campaign,'Loose campaign differs from sealed evidence')
    kernels=['sf_time.py','sf_dynamics.py','skyrme.py','sf_reconstruction.py']
    for name in kernels:need(sha(repo/'src/electron_field_topology'/name)==campaign['source_sha256'][name],'Measured kernel changed: '+name)
    for name,h in campaign['dependency_sha256'].items():need(sha(repo/name)==h,'Measured lock changed: '+name)
    sys.path.insert(0,str(repo/'src'))
    from electron_field_topology import sf_time as k,sf_reconstruction as reconstruction
    try:from . import sf_initial_centroid as metrics
    except ImportError:import sf_initial_centroid as metrics
    restrow=campaign['rest']['q3-axial-fine-warm'];path=source/restrow['checkpoint'];need(sha(path)==restrow['checkpoint_sha256'],'Fine rest seal differs')
    with np.load(path,allow_pickle=False) as z:rest=z['field'].copy()
    rg=k.Grid((restrow['nodes'],)*3,(restrow['length'],)*3,'fixed')
    need(rest.dtype==np.float64 and rest.shape==rg.shape+(3,) and np.isfinite(rest).all(),'Invalid rest shape/precision')
    need(np.max(abs(rest[rg.fixed_mask()]-[0,0,1]))<1e-10 and np.max(abs(np.linalg.norm(rest,axis=-1)-1))<1e-10,'Invalid fixed rest constraints')
    out=repo/'artifacts/q3-initialization-study'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4));out.mkdir(parents=True)
    rec={'recorded_at':stamp(),'status':'working','source_run':RUN,'source_evidence_sha256':EVIDENCE,'rest_id':restrow['id'],'rest_checkpoint_sha256':restrow['checkpoint_sha256'],'kernel_sha256':{n:campaign['source_sha256'][n] for n in kernels},'dependency_sha256':campaign['dependency_sha256'],'script_sha256':sha(Path(__file__)),'metrics_sha256':sha(Path(metrics.__file__)),'python':sys.version,'numpy':np.__version__,'nodes':a.nodes,'axes':a.axes,'output':str(out),'cases':[],'scope':'Read-only fixed-rest initialization diagnosis. No relaxation, physical steps, new pass/fail decisions or changed gates.'}
    pointer=repo/'artifacts/Q3-INITIALIZATION-STUDY-CURRENT';pointer.write_text(str(out)+'\n')
    def progress():save(out/'study.json',rec);save(out/'status.json',{key:value for key,value in rec.items() if key!='cases'}|{'completed_cases':len(rec['cases'])})
    progress()
    try:
        for axis in a.axes:
            for count in a.nodes:
                print(json.dumps({'recorded_at':stamp(),'message':'Evaluating fixed-rest lab sampling','nominal_nodes':count,'axis':axis}),flush=True)
                r=calculate(rest,rg,count,axis,k,reconstruction,metrics)
                if count==145:
                    key='q3-axial-fine-warm-'+['x','y','z'][axis]+'-dt0.01';original=campaign['cases'][key]
                    r['historical_state_matches']=r['state_sha256']==original['initial_state_sha256'];need(r['historical_state_matches'],'Fine-grid reconstruction does not reproduce original admitted state')
                rec['cases'].append(r);progress()
        rec.update(status='complete_pending_review',finished_at=stamp());progress();report(out,rec)
        for name,path in [('sf_q3_initialization.py',Path(__file__)),('sf_initial_centroid.py',Path(metrics.__file__))]:(out/name).write_bytes(path.read_bytes())
        (out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file()))
        with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.iterdir()):
                if f.is_file() and f.name!='evidence.zip':z.write(f,f.name)
        print('Upload: '+str(out/'evidence.zip'));print('Browser report: '+str(out/'REPORT.html'))
    except BaseException as error:
        rec.update(status='error',error=str(error),finished_at=stamp());progress();raise
if __name__=='__main__':main()
