"""Resumable CPU-only supplement; original evidence and fields stay read-only."""
import argparse,gc,json,os,signal,sys,threading,time,zipfile
from pathlib import Path
import numpy as np
from criteria_common import ROOT,load,save,sha,stamp,need,log,host,process_identity,manifest,verify_manifest,verify_zip
sys.path.insert(0,str(ROOT/'legacy'))
from electron_field_topology.sf_time import Grid
from cases import run_case,resample,charge_count
from integrity import read_parent
from criteria import assess,plot_responses
from field_audit import measure,qualify_derivative
from resources import geometry_budget
STOP=threading.Event()

def run(repo,output,source,parent_path):
 output=Path(output);identity=load(output/'identity.json');plan=load(ROOT/'PLAN.json');need(identity['package_sha256']==sha(ROOT/'SHA256SUMS'),'Package identity differs');phase={'name':'starting'};finished=threading.Event();measures=[];deferrals=[];status='working';error=None
 def heartbeat():
  while not finished.is_set():
   save(output/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid(),'process_identity':process_identity(os.getpid()),'phase':dict(phase),'charged_optimizer_attempts':charge_count(output)});finished.wait(10)
 signal.signal(signal.SIGTERM,lambda *_:STOP.set());signal.signal(signal.SIGINT,lambda *_:STOP.set());thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
 def check_stop():
  if STOP.is_set() or (output/'STOP.json').exists():raise KeyboardInterrupt('Orderly stop requested')
  need(host()['available_gib']>=6,'Host memory reserve reached before next task')
 def update():
  row={'recorded_at':stamp(),'status':status,'phase':dict(phase),'error':error,'charged_optimizer_attempts':charge_count(output),'maximum_optimizer_attempts':160,'physical_time_steps':0,'deferrals':deferrals};save(output/'status.json',row);return row
 def audit(label,n,g,expected=None,q=21):
  folder=output/'field-audit'/label;path=folder/'MEASUREMENTS.json'
  if path.exists() and (folder/'REPORT.html').exists() and (folder/'author-surfaces.png').exists():
   value=load(path);need(value['source_array_sha256']==__import__('evaluations').array_sha(n),'Cached measurement array differs');measures.append({'label':label,'path':str(path.relative_to(output)),'status':'measured','array_sha256':value['source_array_sha256']});return value
  check_stop();phase.clear();phase.update(name='read-only-field-audit',case=label,nodes=g.shape[0]);update();value=measure(n,g,folder,label,expected,q=q);measures.append({'label':label,'path':str(path.relative_to(output)),'status':'measured','array_sha256':value['source_array_sha256']});return value
 try:
  frozen=__import__('criteria_common').source_record();source_manifest=load(source/'FIELD-MANIFEST.json');hashes={r['path']:r['sha256'] for r in source_manifest['fields']};verify_zip(source/'evidence.zip',plan['source_evidence_sha256']);parent=read_parent(parent_path)
  # The new arms reset conjugacy, so validated old vectors need not remain resident.
  for unused in ['old_g','old_z','direction']:parent.pop(unused,None)
  gc.collect();base_grid=Grid((129,)*3,(30.72,)*3,'fixed')
  for case in frozen['cases']:
   check_stop();name=case['case']['id'];path=source/'cases'/name/'endpoint.npz';need(sha(path)==hashes['cases/'+name+'/endpoint.npz'],'Original endpoint hash differs')
   with np.load(path,allow_pickle=False) as z:n=z['n'].copy();need(int(z['iteration'])==625 and str(z['backend'])=='cuda','Original endpoint metadata differs')
   audit('retained-'+name,n,Grid(tuple(case['shape']),tuple(case['lengths']),'fixed'),case['final']['metrics']);del n;gc.collect();need(sha(path)==hashes['cases/'+name+'/endpoint.npz'],'Original endpoint changed after read')
  for nodes in plan['reconstruct_initial_grids']:
   check_stop();phase.clear();phase.update(name='reconstruct-original-initial-field',nodes=nodes);update();n,g,initial=resample(parent['n'],base_grid,nodes);expected=next(c['history'][0]['metrics'] for c in frozen['cases'] if c['case']['nodes']==nodes)
   audit('reconstructed-initial-%d'%nodes,n,g,expected);save(output/'field-audit'/('reconstructed-initial-%d'%nodes)/'RECONSTRUCTION.json',{'recorded_at':stamp(),'parent_sha256':sha(parent_path),'reconstructed_not_original_snapshot':True,**initial});del n;gc.collect()
  spec=load(ROOT/'legacy/SOURCE.json')['q2'];q2=repo/load(ROOT/'legacy/SOURCE.json')['q2_relative']
  if q2.exists():
   need(sha(q2)==spec['sha256'],'Q2 control hash differs')
   with np.load(q2,allow_pickle=False) as z:n=z[spec['key']].copy()
   audit('q2-reference',n,Grid((spec['nodes'],)*3,(spec['length'],)*3,'fixed'),spec['expected'],q=2);del n;gc.collect();need(sha(q2)==spec['sha256'],'Q2 changed after read')
  else:deferrals.append({'case':'q2-reference-replay','reason':'Authenticated control file missing; original compact passing measurement remains retained'})
  for nodes in plan['cpu_grids']:
   check_stop();case_id='cpu-%03d'%nodes;phase.clear();phase.update(name='cpu-geometry-admission',case=case_id,nodes=nodes);update();admission=geometry_budget(nodes,'cpu');save(output/(case_id+'-ADMISSION.json'),admission)
   if not admission['passed']:raise KeyboardInterrupt('CPU geometry reserve not qualified for '+case_id+'; free host resources and resume')
   folder=output/'cases'/case_id;folder.mkdir(parents=True,exist_ok=True);n,g,initial=resample(parent['n'],base_grid,nodes)
   if not (output/'field-audit'/('initial-'+case_id)/'DIRECTIONAL-DERIVATIVE.json').exists():
    phase.clear();phase.update(name='cpu-directional-derivative-qualification',case=case_id,nodes=nodes);update();qualify_derivative(n,g,output/'field-audit'/('initial-'+case_id))
   audit('initial-'+case_id,n,g);del n;gc.collect();check_stop();phase.clear();phase.update(name='cpu-resolution-branch',case=case_id,nodes=nodes);update()
   cfg={'id':case_id,'nodes':nodes,'start':'restart','shift':.25,'max_attempts':80};backend={'requested':'cpu','selected':'cpu','device':None,'source_backend':'cuda','backend_transfer':True,'scope':'New branch from authenticated source; no running checkpoint is transferred. CPU repeat checks are not independent implementations.'}
   existing=load(folder/'record.json') if (folder/'record.json').exists() else None
   if existing and (existing['charged_attempts']>=80 or existing['reason']!='matched_horizon_reached'):result=existing
   else:result=run_case(output,parent,base_grid,cfg,80,backend,STOP.is_set,phase)
   path=folder/'endpoint.npz';expected_hash=sha(path)
   with np.load(path,allow_pickle=False) as z:n=z['n'].copy();need(str(z['backend'])=='cpu','New branch backend differs')
   audit('final-'+case_id,n,g,result['final']['metrics'])
   if not (output/'field-audit'/('final-'+case_id)/'DIRECTIONAL-DERIVATIVE.json').exists():qualify_derivative(n,g,output/'field-audit'/('final-'+case_id))
   del n;gc.collect();need(sha(path)==expected_hash,'CPU endpoint changed during read-only audit')
  need(sha(parent_path)==plan['source_parent_sha256'],'Source parent changed');need(sha(source/'evidence.zip')==plan['source_evidence_sha256'],'Original evidence changed')
  status='complete_pending_review';phase.clear();phase.update(name='complete')
 except KeyboardInterrupt as exc:status='interrupted';error=str(exc)
 except Exception as exc:status='failed';error=repr(exc)
 finally:
  save(output/'FIELD-AUDIT-SUMMARY.json',{'recorded_at':stamp(),'measurements':measures,'deferrals':deferrals,'physical_time_steps':0,'interpretation':'Read-only distributions and display surfaces are not perturbation-return or stability tests.'})
  runtime=update();new=[load(p) for p in sorted((output/'cases').glob('*/record.json'))];record={**runtime,'source_run':plan['source_run'],'source_evidence_sha256':plan['source_evidence_sha256'],'new_cases':new,'registered_plan':plan,'full_field_diagnostics':measures};save(output/'record.json',record);assess(output,new,record)
  from relationships import fit_curve,window,spatial_comparison
  points=[]
  for case in __import__('criteria_common').source_record()['cases']+new:
   if case['case']['start']=='exact':continue
   response=window(case['history'],80,10)
   if response.get('eligible'):points.append({'nodes':case['case']['nodes'],'spacing':case['spacing'][0],'backend':case['backend']['selected'],**response})
  fitplan=load(ROOT/'legacy/PLAN.json')
  save(output/'UPDATED-RESPONSE-CURVES.json',{'recorded_at':stamp(),'points':points,'fits':{key:fit_curve(points,key,fitplan) for key in ['joint','force','acceleration']},'backend_varies_with_spacing':True,'warning':'CPU/CUDA arithmetic is separately qualified; these measurements do not fully isolate backend-dependent optimization paths. No automatic optimum or additional budget is authorized.'})
  save(output/'SPATIAL-COMPARISON.json',spatial_comparison(__import__('criteria_common').source_record()['cases']+new,fitplan))
  plot_responses(points,{key:fit_curve(points,key,fitplan) for key in ['force','acceleration']},output)
  fields=[]
  for f in sorted((output/'cases').glob('*/*.npz')):fields.append({'path':f.relative_to(output).as_posix(),'sha256':sha(f),'bytes':f.stat().st_size})
  save(output/'FIELD-MANIFEST.json',{'recorded_at':stamp(),'fields':fields,'original_24_full_fields_remain_in_source_run':True});finished.set();thread.join(timeout=12)
  # Stable terminal metadata is sealed; live telemetry is not copied into evidence.
  if (output/'telemetry-latest.json').exists():save(output/'TELEMETRY-FROZEN.json',load(output/'telemetry-latest.json'))
  files=sorted(p for p in output.rglob('*') if p.is_file() and p.suffix not in ['.npz','.tmp'] and p.name not in ['evidence.zip','SHA256SUMS','telemetry.jsonl','telemetry-latest.json','runner.log','heartbeat.json','supervisor.json','worker-launch.json','STOP.json'] and '__pycache__' not in p.parts and not any(part.startswith('STOP-retained-') for part in p.parts))
  import hashlib
  sums=''.join(sha(f)+'  '+f.relative_to(output).as_posix()+'\n' for f in files);(output/'SHA256SUMS').write_text(sums)
  temp=output/'evidence.tmp'
  with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for f in files:z.write(f,f.relative_to(output).as_posix())
   z.writestr('SHA256SUMS',sums)
  temp.replace(output/'evidence.zip');verify_zip(output/'evidence.zip');log('Q21 supplement finished',status=status,output=str(output),charged_attempts=charge_count(output),evidence=str(output/'evidence.zip'))
 return 0 if status in ['complete_pending_review','interrupted'] else 1
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-run',type=Path,required=True);p.add_argument('--parent',type=Path,required=True);a=p.parse_args();raise SystemExit(run(a.repo,a.output,a.source_run,a.parent))
