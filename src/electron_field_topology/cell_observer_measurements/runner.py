"""Read-only anchor confirmation and all-spacing measurements."""
import os,platform,signal,subprocess,threading,traceback,zipfile
from pathlib import Path
import numpy as np
from .common import load,save,sha,stamp,checkpoint
from .kernel.calibration import prepare,measure,RESPONSES
from .kernel.reference.dependencies import features
from .fits import models
from .report import finish

def qc(orders,pairs,budget):
 diffs={f'{a}-to-{b}':{k:abs(orders[str(a)]['measurement'][k]-orders[str(b)]['measurement'][k]) for k in RESPONSES} for a,b in pairs}
 return diffs,all(v<=budget for d in diffs.values() for v in d.values())
def seal(out):
 excluded={'evidence.zip','SHA256SUMS','runner.log','status.json','heartbeat.json','launch.json'}
 paths=[p for p in out.rglob('*') if p.is_file() and p.name not in excluded and p.suffix!='.tmp' and '__pycache__' not in p.parts]
 (out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(out).as_posix()+'\n' for p in sorted(paths)))
 with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(paths)+[out/'SHA256SUMS']:z.write(p,p.relative_to(out))

def run(repo,source,calibration,out,config):
 out.mkdir(parents=True,exist_ok=True);plan=load(config);old=load(calibration/'record.json');source_record=load(source/'record.json')
 identity={'source_evidence_sha256':sha(source/'evidence.zip'),'calibration_evidence_sha256':sha(calibration/'evidence.zip'),'config_sha256':sha(config),'code_sha256':{p.relative_to(Path(__file__).parent).as_posix():sha(p) for p in Path(__file__).parent.rglob('*.py')},'repo':str(repo),'source':str(source),'calibration':str(calibration),'threads':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']}}
 if (out/'identity.json').exists():
  if load(out/'identity.json')!=identity:raise ValueError('Source, configuration, code or environment changed on resume')
 else:save(out/'identity.json',identity)
 started=load(out/'started.json') if (out/'started.json').exists() else {'recorded_at':stamp()};save(out/'started.json',started)
 record={**started,'status':'working','role':'cell-aware-saved-state-measurements','config':plan,'identity':identity,'environment':{'python':platform.python_version(),'numpy':np.__version__,'source_commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'source_environment':source_record['environment']},'cases':[],'fits':[]}
 stop=threading.Event()
 def pulse():
  while not stop.wait(15):save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid()})
 threading.Thread(target=pulse,daemon=True).start()
 def interrupted(*_):raise KeyboardInterrupt('Stop requested; sealed measurements will be reused on resume')
 signal.signal(signal.SIGTERM,interrupted)
 try:
  selected=[]
  for p in (source/'cases').glob('*.json'):
   c=load(p);q=c['parameters']
   if q['field'] in plan['expected_spacing_counts'] and all(q.get(k)==v for k,v in plan['fixed_parameters'].items()):selected.append((p.stem,c))
  for field,count in plan['expected_spacing_counts'].items():
   if sum(c['parameters']['field']==field for _,c in selected)!=count:raise ValueError('Wrong spacing case count for '+field)
  used={c['parameters']['nodes'] for _,c in selected}
  if used&set(plan['future_physical_validation_nodes']):raise ValueError('Reserved future physical grid already inspected')
  old_anchors={a['case_id']:a for a in old['anchors']};anchors=[(cid,c) for cid,c in selected if c['parameters']['nodes'] in plan['anchor_nodes']]
  if len(anchors)!=6:raise ValueError('Expected six anchor states')
  def process(cid,c,anchor):
   save(out/'status.json',{'recorded_at':stamp(),'status':'working','phase':'anchor-confirmation' if anchor else 'all-spacing-measurement','pid':os.getpid(),'current_case':cid,'completed_states':len(record['cases'])})
   f=(source/'fields'/c['state']['file']).resolve()
   if not f.is_relative_to(source.resolve()) or f.stat().st_size!=c['state']['bytes'] or sha(f)!=c['state']['sha256']:raise ValueError('State identity failure: '+cid)
   with zipfile.ZipFile(f) as z:
    if z.testzip() is not None:raise ValueError('NPZ CRC failure')
   with np.load(f,allow_pickle=False) as arrays:
    E=arrays['E'];B=arrays['B_half']
    if abs(float(arrays['dt'])-c['parameters']['duration']/c['parameters']['steps'])>1e-15 or float(arrays['duration'])!=c['parameters']['duration']:raise ValueError('State time receipt mismatch')
   state=prepare(E,B,c['parameters'],repo,plan['chunk_x']);orders={}
   for order in plan['anchor_orders'] if anchor else plan['spacing_orders']:
    if anchor and order==4:
     a=old_anchors[cid]
     if a['state_sha256']!=c['state']['sha256'] or a['parameters']!=c['parameters']:raise ValueError('Original anchor identity changed')
     prior=next(v for v in a['gauss_refinement'] if v['order']==4)
     fn=lambda prior=prior:{'recorded_at':stamp(),'origin':'reused prior calibrated order-4 measurement','source_calibration_evidence_sha256':identity['calibration_evidence_sha256'],'measurement':prior}
    else:fn=lambda order=order:{'recorded_at':stamp(),'origin':'new observation of saved physical state','measurement':measure(state,order=order,chunk=plan['chunk_x'])}
    orders[str(order)]=checkpoint(out,cid+'-gauss'+str(order),fn)
   if sha(f)!=c['state']['sha256']:raise ValueError('Source array changed during observation')
   diffs,passed=qc(orders,[(4,5),(5,6)] if anchor else [(5,6)],plan['measurement_error_budget'])
   row={'case_id':cid,'parameters':c['parameters'],'state_sha256':c['state']['sha256'],'anchor':anchor,'orders':orders,'original_observer':c['observer'],'order_differences':diffs,'all_response_pass':passed,'per_response_pass':{k:all(d[k]<=plan['measurement_error_budget'] for d in diffs.values()) for k in RESPONSES},'source_case_sha256':sha(source/'cases'/(cid+'.json'))};save(out/'cases'/(cid+'.json'),row)
   record['cases'].append(row);print(__import__('json').dumps({'recorded_at':stamp(),'message':'Saved-state measurement complete','case_id':cid,'all_response_pass':passed}),flush=True)
  for cid,c in sorted(anchors,key=lambda item:(item[1]['parameters']['field'],item[1]['parameters']['nodes'])):process(cid,c,True)
  record['anchor_contract_pass']=all(c['all_response_pass'] for c in record['cases'])
  if record['anchor_contract_pass']:
   for cid,c in sorted(selected,key=lambda item:(item[1]['parameters']['field'],item[1]['parameters']['nodes'])):
    if cid not in old_anchors:process(cid,c,False)
   record['all_spacing_contract_pass']=all(c['all_response_pass'] for c in record['cases'])
   for field in plan['expected_spacing_counts']:
    cases=[c for c in record['cases'] if c['parameters']['field']==field]
    for key in RESPONSES:
     rows=sorted([{'x':c['parameters']['length']/c['parameters']['nodes'],'y':c['orders']['6']['measurement'][key],'case_id':c['case_id']} for c in cases],key=lambda v:v['x']);fitted=models(rows);primary=fitted[0]
     fs=features(rows,primary) if primary['model'] not in ['pure_power','nonnegative_offset_power'] else []
     record['fits'].append({'field':field,'response':key,'rows':rows,'models':fitted,'features':fs,'measurement_contract_pass':all(c['per_response_pass'][key] for c in cases),'validation_status':'not_performed_all_existing_physical_points_are_inspected_development','scope':'Descriptive range only; no production mesh optimum or physical acceptance'})
   payload={'config_sha256':identity['config_sha256'],'future_physical_validation_nodes':plan['future_physical_validation_nodes'],'fits':record['fits'],'source_evidence_sha256':identity['source_evidence_sha256']};freeze=out/'frozen-fits.json'
   if freeze.exists():
    stored=load(freeze)
    if stored['payload']!=__import__('json').loads(__import__('json').dumps(payload)):raise ValueError('Frozen descriptive fits changed on resume')
   else:save(freeze,{'frozen_at':stamp(),'payload':payload})
   record['phase']='all-spacing-measured-pending-review'
  else:
   record['all_spacing_contract_pass']=False;record['phase']='anchor-contract-unresolved';record['skipped_remaining_states']=len(selected)-6;record['skipped_reason']='Predeclared common anchor observation contract did not pass; no tolerance change'
  record.update(status='complete_pending_review',finished_at=stamp())
  code=Path(__file__).parent
  for p in code.rglob('*.py'):
   d=out/'code'/p.relative_to(code);d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(p.read_bytes())
  finish(out,record);seal(out);save(out/'status.json',{'recorded_at':stamp(),'status':'complete_pending_review','phase':record['phase'],'pid':os.getpid(),'completed_states':len(record['cases']),'report':str(out/'REPORT.html'),'evidence':str(out/'evidence.zip')})
 except BaseException as e:
  save(out/'status.json',{'recorded_at':stamp(),'status':'interrupted' if isinstance(e,KeyboardInterrupt) else 'failed','pid':os.getpid(),'error':str(e),'completed_states':len(record['cases'])});traceback.print_exc();raise
 finally:stop.set()
