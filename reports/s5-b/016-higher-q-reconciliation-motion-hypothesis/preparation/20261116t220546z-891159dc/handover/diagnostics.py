"""Read-only instantaneous isorotation-balance probes; never evolve or relax a field."""
import argparse,json,hashlib,sys,time,gc
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
def stamp():
 n=datetime.now(timezone.utc);return {'utc':n.isoformat(),'melbourne':n.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def log(message,**kw):print(json.dumps({'recorded_at':stamp(),'message':message,**kw}),flush=True)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')
def require(ok,message):
 if not ok:raise RuntimeError(message)
def fit_squared_frequency(a0,c,mask,cap):
 import numpy as np
 denominator=float(np.sum(c[mask]*c[mask]));numerator=float(np.sum(a0[mask]*c[mask]))
 raw=-numerator/denominator if denominator>1e-30 else None
 u=float(np.clip(raw,0,cap*cap)) if raw is not None else 0.
 return {'omega_squared_unconstrained':raw,'omega_squared_clipped':u,'omega_clipped':float(np.sqrt(u)),'cap':cap,'identifiable':raw is not None,'clipped_at_boundary':raw is not None and (raw<0 or raw>cap*cap),'scope':'Instantaneous least-squares balance at a frozen field; no stationary or dynamical stability acceptance'}
def probe(n,g,cpu,port,omega=.01,cap=.05):
 import numpy as np
 start=time.monotonic();north=np.array([0.,0.,1.]);n=cpu.retract(n,np.zeros_like(n),g)[0];mask=~g.fixed_mask();generator=np.cross(north,n);centripetal=np.cross(north,generator)
 def acceleration(w):
  log('Evaluating frozen-field acceleration',omega=w)
  return cpu.acceleration(n,w*generator,g)[1]
 a0=acceleration(0.);ap=acceleration(omega);am=acceleration(-omega)
 array=port.acceleration(n,omega*generator,g)[1]
 require(np.allclose(ap,array,rtol=2e-9,atol=2e-10),'CPU/array nonzero-rate acceleration parity failed');del array
 even=float(np.max(abs(ap-am)));require(np.allclose(ap,am,rtol=2e-8,atol=2e-10),'Unexpected odd velocity dependence')
 velocity_coefficient=((ap+am)/2-a0)/(omega*omega);c=velocity_coefficient-centripetal
 a2=acceleration(2*omega);predicted=a0+4*omega*omega*velocity_coefficient;quad=float(np.max(abs(a2-predicted)));scale=max(float(np.max(abs(a2))),1e-12)
 require(quad<=2e-8*scale+2e-10,'Quadratic-in-rate balance qualification failed')
 fit=fit_squared_frequency(a0,c,mask,cap);w=fit['omega_clipped'];actual=acceleration(w);residual=actual-w*w*centripetal
 predicted_residual=a0+w*w*c;require(np.allclose(residual,predicted_residual,rtol=2e-8,atol=2e-10),'Fitted instantaneous residual replay differs')
 def norms(x):
  mag=np.linalg.norm(x,axis=-1);idx=np.unravel_index(np.argmax(np.where(mask,mag,-1)),mag.shape)
  return {'l2_rms':float(np.sqrt(np.mean(mag[mask]**2))),'maximum':float(mag[mask].max()),'maximum_index':list(map(int,idx))}
 before=norms(a0);after=norms(residual)
 constraint=float(np.max(abs(np.sum(n*actual,axis=-1)+np.sum((w*generator)**2,axis=-1))))
 require(constraint<=1e-9,'Sphere-acceleration operator qualification failed')
 samples=[]
 for frequency in [0.,omega,2*omega,w]:
  r=norms(a0+frequency*frequency*c);samples.append({'omega':frequency,'omega_squared':frequency*frequency,**r})
 return {'recorded_at':stamp(),'probe_axis':'target-space north axis; NOT spatial spin or center-of-mass translation','probe_frequency':omega,'fit':fit,'static_acceleration':before,'fitted_ansatz_residual':after,'rms_ratio':after['l2_rms']/max(before['l2_rms'],1e-30),'maximum_ratio':after['maximum']/max(before['maximum'],1e-30),'qualifications':{'cpu_array_nonzero_rate_allclose':True,'even_velocity_max_difference':even,'quadratic_prediction_max_difference':quad,'sphere_acceleration_constraint_max_error':constraint},'predicted_samples':samples,'wall_seconds':time.monotonic()-start,'relaxation_steps':0,'physical_time_steps':0,'stability_certified':False,'gate_override':False,'massless_radiation_warning':'A lower t0 residual does not supply a localized, non-radiating periodic solution or remove the massless far-field obstruction.'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--q2-run',type=Path,required=True);p.add_argument('--q8-run',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(exist_ok=True,parents=True)
 require((out/'COLLECTION.json').is_file(),'Collect the repository reconciliation first')
 for n,h in load(ROOT/'SOURCE.json').items():require((a.repo/n).is_file() and sha(a.repo/n)==h,'Audited numerical source/lock differs: '+n)
 sys.path.insert(0,str(a.repo.resolve()/'src'))
 import numpy as np
 from electron_field_topology import sf_time as cpu
 from electron_field_topology.sf_time_gpu import ArrayTime
 from electron_field_topology.sf_readmission import stationarity
 roots={'Q2':a.q2_run.resolve(),'Q8':a.q8_run.resolve()};anchors=load(ROOT/'ANCHORS.json');results=[]
 for key in ['Q2','Q8']:
  ref=anchors[key];f=roots[key]/ref['checkpoint'];result={'field':key,'recorded_at':stamp(),'path':str(f),'expected_sha256':ref['checkpoint_sha256']}
  try:
   available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))/1024**2;require(available>=4,'Available memory below4GiB')
   require(sha(roots[key]/'evidence.zip')==ref['archive_sha256'],'Retained archive differs');require(sha(f)==ref['checkpoint_sha256'],'Retained field differs')
   with np.load(f,allow_pickle=False) as z:n=z[ref['field_key']].copy()
   require(n.dtype==np.float64 and n.shape==(ref['nodes'],)*3+(3,) and np.isfinite(n).all(),'Invalid retained float64 field')
   g=cpu.Grid((ref['nodes'],)*3,(ref['length'],)*3,'fixed');m=stationarity(n,g)
   for k in ['energy','relative_force_l2','acceleration_max']:
    require(np.isclose(m[k],ref['expected_metrics'][k],rtol=1e-9,atol=1e-12),'Retained source metric replay differs: '+k)
   result.update(status='diagnostic_complete_not_stability_acceptance',metrics=m,probe=probe(n,g,cpu,ArrayTime(np)))
   require(sha(f)==ref['checkpoint_sha256'],'Input field changed during read-only probe');del n;gc.collect()
  except Exception as e:result.update(status='explicitly_deferred',reason=str(e));log('Frozen-field probe deferred',field=key,error=str(e))
  results.append(result);save(out/'MOTION-PROBES.json',{'recorded_at':stamp(),'status':'complete_pending_review','results':results,'scope':'No relaxation, field evolution, new model term or dynamic gate acceptance'})
 log('Read-only motion probes finished',completed=sum(x['status'].startswith('diagnostic_complete') for x in results),deferred=sum(x['status']=='explicitly_deferred' for x in results))
if __name__=='__main__':
 try:main()
 except Exception as e:log('Read-only probes blocked',error=str(e));raise
