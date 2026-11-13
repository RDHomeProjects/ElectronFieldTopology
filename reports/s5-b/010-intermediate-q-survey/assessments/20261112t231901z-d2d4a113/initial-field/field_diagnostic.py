"""Read-only initial SF field/centroid-rate diagnostics. Apache-2.0.
No optimizer, RK step, reconstructed time state or changed acceptance flag.
"""
import argparse,gc,hashlib,json,os,platform,secrets,subprocess,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
if not __debug__:raise RuntimeError('Run without Python optimization')
HERE=Path(__file__).resolve().parent
MERGE='50a1337739f5063bfb459c8d7111077b9ccffd33'
RUN='20261109t134425z-89d28344'
EVIDENCE='c066b7f2bab8308cf68945b0b6e5de837585775647634ffd721b3e84bee87517'
def need(x,s):
    if not x:raise ValueError(s)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while b:=f.read(8*1024**2):h.update(b)
    return h.hexdigest()
def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sigma_rate(n,ndot,vacuum,g):
    u=n-vacuum;result=np.zeros(g.shape)
    for axis,(h,count) in enumerate(zip(g.spacing,g.shape)):
        if count==1:continue
        if g.boundary=='periodic':at=lambda a,k:np.roll(a,-k,axis)
        else:
            def at(a,k):
                pads=[(0,0)]*a.ndim;pads[axis]=(2,2);p=np.pad(a,pads);sl=[slice(None)]*a.ndim;sl[axis]=slice(2+k,2+k+count);return p[tuple(sl)]
        f=(at(u,1)-u)/h;b=(u-at(u,-1))/h
        ft=(at(ndot,1)-ndot)/h;bt=(ndot-at(ndot,-1))/h
        d2=(at(u,1)-2*u+at(u,-1))/h**2;d2t=(at(ndot,1)-2*ndot+at(ndot,-1))/h**2
        result+=np.sum(f*ft+b*bt,axis=-1)+h*h/6*np.sum(d2*d2t,axis=-1)
    return result
def density_rate(n,v,ndot,a,g,gradients,K,NORTH):
    d=gradients(n-NORTH,g);dt=gradients(ndot,g)
    value=np.sum(v*a,axis=-1)+np.sum(d*dt,axis=(-2,-1))
    for i in range(3):
        c=np.cross(v,d[...,i,:]);ct=np.cross(a,d[...,i,:])+np.cross(v,dt[...,i,:]);value+=np.sum(c*ct,axis=-1)
    for i,j in [(0,1),(0,2),(1,2)]:
        c=np.cross(d[...,i,:],d[...,j,:]);ct=np.cross(dt[...,i,:],d[...,j,:])+np.cross(d[...,i,:],dt[...,j,:]);value+=np.sum(c*ct,axis=-1)
    rhodot=2*K*value
    hdot=rhodot+K*(sigma_rate(n,ndot,NORTH,g)-2*np.sum(d*dt,axis=(-2,-1)))
    return rhodot,hdot
def moments(rho,rhodot,g):
    volume=float(np.prod(g.spacing));energy=float(np.sum(rho)*volume);edot=float(np.sum(rhodot)*volume)
    need(energy>0,'Nonpositive total density')
    centre=[];rate=[];axes=[]
    for i,(count,h,l) in enumerate(zip(g.shape,g.spacing,g.lengths)):
        shape=[1,1,1];shape[i]=count;x=(-l/2+np.arange(count)*h).reshape(shape);axes.append(x)
        c=float(np.sum(x*rho)*volume/energy);centre.append(c);rate.append(float(np.sum((x-c)*rhodot)*volume/energy))
    return energy,edot,centre,rate,axes
def evaluate(n,v,g,kernel):
    from electron_field_topology.skyrme import K,NORTH
    ndot,a=kernel.acceleration(n,v,g)
    rd,hd=density_rate(n,v,ndot,a,g,kernel.gradients,K,NORTH)
    data=kernel.densities(n,v,g);rho=data['energy_density'];ham=data['hamiltonian_density'];flux=data['energy_flux'];del data
    e,ed,c,cr,axes=moments(rho,rd,g);he,hed,hc,hcr,_=moments(ham,hd,g);vol=float(np.prod(g.spacing))
    momentum=np.sum(flux,axis=(0,1,2))*vol
    div=sum(kernel.derivative(flux[...,i],h,i,g.boundary) for i,h in enumerate(g.spacing))
    residual=rd+div
    residual_moment=np.array([np.sum((axes[i]-c[i])*residual)*vol/e for i in range(3)])
    flux_moment=np.array([np.sum((axes[i]-c[i])*(-div))*vol/e for i in range(3)])
    summation=flux_moment-momentum/e
    closure=np.array(cr)-momentum/e-residual_moment-summation
    need(np.max(abs(closure))<1e-10,'Discrete algebraic moment decomposition failed')
    # These are independent directional-derivative probes in state space, not
    # physical-time steps. Do not normalize/retract probes or write them as states.
    fd=[]
    for eps in [1e-4,5e-5,2.5e-5]:
        plus=kernel.densities(n+eps*ndot,v+eps*a,g);pe=plus['energy_density'].copy();ph=plus['hamiltonian_density'].copy();del plus
        minus=kernel.densities(n-eps*ndot,v-eps*a,g)
        re=(pe-minus['energy_density'])/(2*eps);rh=(ph-minus['hamiltonian_density'])/(2*eps);del minus,pe,ph
        fd.append({'epsilon':eps,'continuum_relative_l2':float(np.linalg.norm(re-rd)/max(np.linalg.norm(rd),1e-20)),'hamiltonian_relative_l2':float(np.linalg.norm(rh-hd)/max(np.linalg.norm(hd),1e-20)),'continuum_absolute_rms':float(np.sqrt(np.mean((re-rd)**2))),'hamiltonian_absolute_rms':float(np.sqrt(np.mean((rh-hd)**2)))})
    # Relative checks are ill-conditioned for near-zero rest derivatives.
    need(min(x['continuum_absolute_rms'] for x in fd)<1e-8 and min(x['hamiltonian_absolute_rms'] for x in fd)<1e-8,'Directional derivative probe disagreement; retain output for diagnosis')
    return {'continuum_energy':e,'continuum_energy_rate':ed,'continuum_centroid':c,'continuum_centroid_rate':cr,'hamiltonian':he,'hamiltonian_rate':hed,'hamiltonian_centroid':hc,'hamiltonian_centroid_rate':hcr,'momentum':momentum.tolist(),'momentum_over_continuum_energy':(momentum/e).tolist(),'momentum_over_hamiltonian':(momentum/he).tolist(),'continuum_continuity_residual_rms':float(np.sqrt(np.mean(residual**2))),'weighted_continuity_residual_over_energy':residual_moment.tolist(),'discrete_summation_term':summation.tolist(),'moment_decomposition_closure':closure.tolist(),'directional_probes':fd,'constraint_projection_rate_correction':float(np.max(abs(ndot-v))),'scope':'Initial-state vector-field directional derivative, not measured physical trajectory or new acceptance. Discrete summation term includes discretization/domain effects; it is not an isolated physical surface flux. No Hamiltonian continuity identity is assumed.'}
def render_report(out,receipt):
    import html
    h=html.escape
    rows=''
    for r in receipt['cases']:
        ax=r['axis'];err=r['initial_speed_relative_error']
        rows+='<tr><td>'+h(r['case_id'])+'</td><td>'+format(r['continuum_centroid_rate'][ax],'.10g')+'</td><td>'+format(r['historical_fit_velocity'][ax],'.10g')+'</td><td>'+('rest' if err is None else format(100*err,'.7g'))+'</td><td>'+format(r['momentum_over_continuum_energy'][ax],'.10g')+'</td><td>'+format(r['weighted_continuity_residual_over_energy'][ax],'.7g')+'</td><td>'+format(r['discrete_summation_term'][ax],'.7g')+'</td></tr>'
    (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Q3 initial-field diagnostic</title><style>body{font:16px/1.6 system-ui;padding:28px;color:#18324a}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}table{border-collapse:collapse}</style><h1>Q3 initial-field diagnostic</h1><p>'+h(json.dumps(receipt['finished_at']))+'</p><p>Initial-state directional rates only. No physical steps or new acceptance. All quantities use model units; error column uses percent.</p><table><tr><th>Case</th><th>Initial centroid axial rate</th><th>Historical fitted axial speed</th><th>Initial vector speed error %</th><th>P/E axial proxy</th><th>Weighted residual / E</th><th>Discrete summation term</th></tr>'+rows+'</table><p>The centroid rate equals P/E plus the weighted continuity residual and discrete summation term. This algebraic closure does not certify a conservation law. The summation term is not isolated physical surface flux. See field-diagnostic.json for full vectors, Hamiltonian-density alternatives and derivative checks.</p></html>')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--case',action='append');a=p.parse_args();repo=a.repo.expanduser().resolve();source=(a.source or repo/'artifacts/s5-b/010-intermediate-q-survey'/RUN).expanduser().resolve()
    need(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo,text=True).strip(),'Tracked checkout changes found; preserve them before execution')
    subprocess.run(['git','merge-base','--is-ancestor',MERGE,'HEAD'],cwd=repo,check=True)
    d=json.loads((source/'campaign.json').read_text());need(d['record_id']==RUN and d['status']=='complete_pending_review','Wrong/incomplete native run')
    need(sha(source/'evidence.zip')==EVIDENCE,'Native evidence differs')
    with zipfile.ZipFile(source/'evidence.zip') as z:
        need(json.loads(z.read('campaign.json'))==d,'Campaign differs from sealed compact evidence')
    for name,h in d['dependency_sha256'].items():need(sha(repo/name)==h,'Measured dependency lock changed: '+name)
    for name in ['sf_time.py','sf_dynamics.py','skyrme.py']:
        need(sha(repo/'src/electron_field_topology'/name)==d['source_sha256'][name],'Measured kernel changed: '+name)
    sys.path.insert(0,str(repo/'src'));import electron_field_topology.sf_time as kernel
    default=['q2-reference-dt0.01','q3-axial-coarse-fresh-z-dt0.01','q3-axial-medium-warm-z-dt0.01','q3-axial-fine-warm-z-dt0.01','q3-axial-fine-warm-x-dt0.01','q3-axial-domain-warm-z-dt0.01','q3-axial-coarse-fresh-rest-dt0.01','q3-axial-medium-warm-rest-dt0.01','q3-axial-fine-warm-rest-dt0.01']
    selected=a.case or default;need(len(selected)==len(set(selected)) and all(k in default for k in selected),'Unknown/duplicate case selection')
    # Preflight the complete requested set before expensive evaluation.
    for key in selected:
        path=source/'cases'/key/'admitted.npz'
        need(path.is_file(),'Initial field missing; restore verified archive locally: '+str(path))
        need(sha(path)==d['cases'][key]['initial_checkpoint_sha256'],'Initial seal differs: '+key)
    out=repo/'artifacts/q3-initial-field-diagnostic'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4));out.mkdir(parents=True)
    receipt={'recorded_at':stamp(),'status':'working','output':str(out),'source':str(source),'source_run':RUN,'script_sha256':sha(Path(__file__)),'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),'checkout_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'selected_cases':selected,'kernel_sha256':{n:d['source_sha256'][n] for n in ['sf_time.py','sf_dynamics.py','skyrme.py']},'dependency_sha256':d['dependency_sha256'],'cases':[]};save(out/'status.json',receipt);(repo/'artifacts/Q3-INITIAL-FIELD-CURRENT').write_text(str(out)+'\n')
    try:
        for key in selected:
            print(json.dumps({'recorded_at':stamp(),'message':'Checking initial field','case':key}),flush=True)
            c=d['cases'][key];path=source/'cases'/key/'admitted.npz';need(path.is_file(),'Initial field missing; restore the verified archive locally: '+str(path));need(sha(path)==c['initial_checkpoint_sha256'],'Initial checkpoint seal differs')
            with np.load(path,allow_pickle=False) as z:
                n=z['field'].copy();v=z['field_rate'].copy();t=float(z['time'])
                canonical=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
                need(str(z['model_id'])=='SF-relativistic-neutral-v1' and str(z['scheme'])=='D4-action-projected-RK4-v1' and int(z['step'])==0,'Checkpoint model/scheme/step differs')
                need(str(z['physics_sha256'])==canonical(c['physical']),'Checkpoint physical metadata differs')
            state=hashlib.sha256()
            for arr in [n,v]:state.update(memoryview(np.ascontiguousarray(arr,dtype='<f8')))
            need(state.hexdigest()==c['initial_state_sha256'],'Initial state seal differs')
            g=kernel.Grid(tuple(c['physical']['grid']),tuple(c['physical']['lengths']),c['physical']['boundary']);need(t==0 and n.dtype==v.dtype==np.float64 and n.shape==g.shape+(3,) and v.shape==n.shape,'Initial precision/shape/time differs')
            need(np.max(abs(np.linalg.norm(n,axis=-1)-1))<1e-10 and np.max(abs(np.sum(n*v,axis=-1)))<1e-10,'Initial constraints fail')
            result=evaluate(n,v,g,kernel);result.update(case_id=key,checkpoint_sha256=c['initial_checkpoint_sha256'],beta=c['beta'],axis=c['axis'],grid=list(g.shape),lengths=list(g.lengths),original_status=c['status'])
            hp=source/'cases'/key/'history-combined.json'
            with zipfile.ZipFile(source/'evidence.zip') as z:
                need(hp.read_bytes()==z.read('cases/'+key+'/history-combined.json'),'History differs from compact seal')
            hist=json.loads(hp.read_text());initial=hist[0]
            result['historical_fit_velocity']=c['assessment']['legacy_motion']['fitted_centroid_velocity']
            result['initial_speed_relative_error']=float(np.linalg.norm(np.array(result['continuum_centroid_rate'])-np.eye(3)[c['axis']]*c['beta'])/c['beta']) if c['beta'] else None
            for k in ['continuum_energy','momentum']:np.testing.assert_allclose(result[k],initial[k],rtol=2e-11,atol=2e-12)
            np.testing.assert_allclose(result['hamiltonian'],initial['energy'],rtol=2e-11,atol=2e-12)
            np.testing.assert_allclose(result['continuum_centroid'],initial['centroid'],rtol=2e-11,atol=2e-12)
            receipt['cases'].append(result);save(out/'field-diagnostic.json',receipt);save(out/'status.json',{k:v for k,v in receipt.items() if k!='cases'} | {'completed_cases':len(receipt['cases'])});del n,v,result;gc.collect()
        receipt.update(status='complete_pending_review',finished_at=stamp());save(out/'field-diagnostic.json',receipt);save(out/'status.json',{k:v for k,v in receipt.items() if k!='cases'})
        render_report(out,receipt)
        (out/'field_diagnostic.py').write_bytes(Path(__file__).read_bytes())
        (out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file()))
        with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.iterdir()):
                if f.is_file() and f.name!='evidence.zip':z.write(f,f.name)
        print('Upload: '+str(out/'evidence.zip'),flush=True)
    except Exception as e:
        receipt.update(status='error',error=str(e),finished_at=stamp());save(out/'status.json',{k:v for k,v in receipt.items() if k!='cases'});raise
if __name__=='__main__':main()
