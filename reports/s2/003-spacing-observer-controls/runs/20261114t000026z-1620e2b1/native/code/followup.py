"""Focused duration closure, fixed-observer spacing and read-only Qx transfer."""
import argparse,hashlib,json,os,platform,shutil,signal,subprocess,sys,time,zipfile
from pathlib import Path
import numpy as np
from .common import stamp,load,save,digest
from .numerics import case,load_reference
from .observer import metrics
from .dependencies import choose,fit_models,predict,feature_width
from .selftest import test
from .qx_audit import audit

def params(field,n,steps=960,T=1.):return {'nodes':n,'length':8.,'duration':T,'field':field,'angle_degrees':0.,'rotation_code':None,'steps':steps}
def code_hashes():return {p.name:digest(p) for p in Path(__file__).resolve().parent.glob('*.py')}
def run(repo,source,out,config,evidence,smoke=False):
 cfg=load(config);original=load(source/'record.json')
 if digest(source/'evidence.zip')!=cfg['source_evidence_sha256']:raise ValueError('Wrong bounded source evidence')
 if original['status']!='complete_pending_review' or original['completed_cases']!=61:raise ValueError('Bounded source run is incomplete or different')
 load_reference(repo)
 if smoke:
  cfg['spacing'].update(seed_nodes=[9,17,23,29],validation_nodes=[13,19,27],candidate_nodes=[9,29],hopfion_max_additions=1,packet_max_additions=1,observer_nodes=17,observer_refinement_nodes=[21,25],time_anchor_nodes=[9,29]);cfg['duration']['nodes']=17;cfg['duration']['max_additions']=1
 env={'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'source_sha256':original['environment']['source_sha256'],'dependency_sha256':{n:digest(repo/n) for n in ['pyproject.toml','uv.lock']},'code_sha256':code_hashes(),'threads':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']}}
 out.mkdir(parents=True,exist_ok=True)
 for d in ['cases','fields','blocks']: (out/d).mkdir(exist_ok=True)
 recpath=out/'record.json'
 if recpath.exists():
  record=load(recpath)
  if record['config']!=cfg or record['environment']!=env:raise ValueError('Resume identity/config mismatch; preserve prior run')
 else:
  record={'recorded_at':stamp(),'role':'smoke' if smoke else 'controlled-dependency-followup','status':'working','config':cfg,'environment':env,'source_record_id':cfg['source_run'],'source_evidence_sha256':cfg['source_evidence_sha256'],'blocks':[]};save(recpath,record)
 start=time.monotonic();status={'recorded_at':stamp(),'status':'working','pid':os.getpid(),'output':str(out),'phase':'qualification','completed_cases':len(list((out/'cases').glob('*.json')))}
 def beat(operation=None,step=0,total=None):
  status.update(heartbeat=stamp(),wall_seconds_current_session=time.monotonic()-start)
  if operation is not None:status.update(operation=operation,current_step=step,total_steps=total)
  save(out/'status.json',status)
 def interrupted(sig,frame):raise KeyboardInterrupt('Signal '+str(sig))
 signal.signal(signal.SIGTERM,interrupted);beat()
 try:
  qpath=out/'qualification.json'
  if not qpath.exists():save(qpath,{'recorded_at':stamp(),**test(repo)})
  if load(qpath)['status']!='qualification_passed':raise ValueError('Numerical qualification failed')
  oldcases=[(f,load(f)) for f in (source/'cases').glob('*.json')]
  def measure(p,observe=True):
   key=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()[:16];dest=out/'cases'/(key+'.json');field=out/'fields'/(key+'.npz')
   if dest.exists():
    c=load(dest)
    if c['parameters']!=p:raise ValueError('Saved case parameters differ')
    if digest(field)!=c['state']['sha256']:raise ValueError('Saved field changed')
    return key,c
   if len(list((out/'cases').glob('*.json')))>=cfg['maximum_new_cases']:raise ValueError('Bounded case count exhausted')
   if shutil.disk_usage(out).free<4*1024**3:raise ValueError('Less than 4 GiB free; completed work preserved')
   op={'case_id':key,**p};beat(op,0,p['steps']);print(json.dumps({'recorded_at':stamp(),'message':'START','case':op}),flush=True)
   matching=next(((f,c) for f,c in oldcases if c['parameters']==p),None)
   if matching and not smoke:
    f,c=matching;c=json.loads(json.dumps(c));oldfield=source/'fields'/c['state']['file']
    if digest(oldfield)!=c['state']['sha256']:raise ValueError('Original full state hash mismatch')
    with zipfile.ZipFile(oldfield) as z:
     if z.testzip():raise ValueError('Original full state CRC mismatch')
    shutil.copy2(oldfield,field);c['reused_from']={'source_case':str(f),'case_sha256':digest(f),'source_finished_at':c['finished_at']};c['state']['file']=field.name
   else:c=case(p,repo,field,lambda i,n:beat(op,i,n))
   if observe:
    with np.load(field,allow_pickle=False) as state:c['observer']=metrics(state['E'],state['B_half'],p,repo,cfg['spacing']['observer_nodes'])
    if c['observer']['vector_decomposition_closure']>1e-12:raise ValueError('Observer vector identity failed')
   c['finished_at']=stamp();save(dest,c);status['completed_cases']=len(list((out/'cases').glob('*.json')));beat(op,p['steps'],p['steps'])
   print(json.dumps({'recorded_at':stamp(),'message':'FINISHED','case_id':key,'sync_native_error':c['sync_native_error'],'observer':c.get('observer')}),flush=True);return key,c
  def block_run(name,initial,candidates,validation,getter,response,limit,variable):
   bp=out/'blocks'/name;bp.mkdir(exist_ok=True);rows=list(initial);journal=[];options=cfg['adaptive'];stop='budget_exhausted';successive=0
   for j in range(limit):
    used={v['level'] for v in rows};available=[v for v in candidates if v['level'] not in used and v['level'] not in validation]
    s=choose(rows,available,options)
    if s is None:stop='candidate_space_exhausted';break
    s={**s,'round':j+1};sp=bp/f'selection-{j+1:02d}.json'
    if sp.exists():
     old=load(sp)
     if {k:v for k,v in old.items() if k!='recorded_at'}!=s:raise ValueError('Adaptive selection mismatch on resume')
     s=old
    else:s={'recorded_at':stamp(),**s};save(sp,s)
    journal.append(s);row=getter(s['level'],'adaptive_development');rows.append(row);m=fit_models(rows)[0];residual=abs(row['y']-s['predicted_y']);width=feature_width(rows,m,options)
    good=residual<=options['prediction_tolerance_fraction'] and width<=options['feature_bracket_fraction'];successive=successive+1 if good else 0
    save(bp/'development.json',{'rows':rows,'last_prediction_residual':residual,'feature_bracket_fraction':width})
    if j+1>=options['min_additions'] and successive>=2:stop='refinement_tolerances_met';break
   frozen={'rows':rows,'models':fit_models(rows),'stop_reason':stop,'response':response,'variable':variable};fp=bp/'frozen-fit.json'
   if fp.exists():
    old=load(fp)
    if {k:v for k,v in old.items() if k!='recorded_at'}!=frozen:raise ValueError('Frozen model differs')
    frozen=old
   else:frozen={'recorded_at':stamp(),**frozen};save(fp,frozen)
   vals=[getter(level,'fresh_validation') for level in validation]
   for m in frozen['models']:
    errors=np.array([float(predict(m,v['x']))-v['y'] for v in vals]);m['validation_rmse']=float(np.sqrt(np.mean(errors**2)));m['validation_max_abs_error']=float(max(abs(errors)))
   result={'id':name,'variable':variable,'response':response,'development':rows,'validation':vals,'models':frozen['models'],'frozen_at':frozen['recorded_at'],'selection_journal':journal,'stop_reason':stop,'prediction_pass':bool(frozen['models'][0]['validation_max_abs_error']<=options['validation_tolerance_fraction']),'operating_point':'not_selected: no new accuracy budget declared'}
   save(bp/'result.json',result);record['blocks']=[b for b in record['blocks'] if b['id']!=name]+[result];save(recpath,record)
  status['phase']='localized-duration';beat()
  dc=cfg['duration'];Tdt=dc['dt']
  def duration_row(level,role):
   p=params('hopfion',dc['nodes'],level,level*Tdt);key,c=measure(p,False);return {'level':level,'x':p['duration'],'y':c['sync_native_error'],'role':role,'case_id':key,'measured_at':c['finished_at'],'variable':'duration'}
  if smoke:initial=[duration_row(level,'seed_development') for level in [48,96,120,240]]
  else:
   previous=next(b for b in original['blocks'] if b['id']=='hopfion-duration')
   initial=[{**v,'role':'previously_reviewed_development','variable':'duration'} for v in previous['development']+previous['validation']]
  block_run('hopfion-duration-localized',initial,[{'level':n,'x':n*Tdt} for n in range(dc['candidate_levels'][0],dc['candidate_levels'][1]+1)],dc['reserved_validation'],duration_row,'sync_native_error',dc['max_additions'],'duration')
  sc=cfg['spacing']
  for kind in ['hopfion','packet']:
   status['phase']=kind+'-spacing';beat()
   def spacing_row(level,role):
    p=params(kind,level,sc['steps'],sc['duration']);key,c=measure(p);return {'level':level,'x':sc['length']/level,'y':c['observer']['evolution_observed_error'],'role':role,'case_id':key,'measured_at':c['finished_at'],'variable':'spacing'}
   initial=[spacing_row(n,'seed_development') for n in sc['seed_nodes']]
   block_run(kind+'-spacing',initial,[{'level':n,'x':sc['length']/n} for n in range(sc['candidate_nodes'][0],sc['candidate_nodes'][1]+1,2)],sc['validation_nodes'],spacing_row,'evolution_observed_error',sc[kind+'_max_additions'],'spacing')
  status['phase']='saved-state-observer-and-time-anchors';beat();anchors=[]
  for kind in ['hopfion','packet']:
   for n in sc['time_anchor_nodes']:
    key,c=measure(params(kind,n,sc['steps'],sc['duration']));statepath=out/'fields'/c['state']['file'];observations=[]
    with np.load(statepath,allow_pickle=False) as state:
     for count in sc['observer_refinement_nodes']:observations.append(metrics(state['E'],state['B_half'],c['parameters'],repo,count))
    key2,c2=measure(params(kind,n,sc['time_anchor_steps'],sc['duration']));anchors.append({'field':kind,'nodes':n,'base_case':key,'larger_dt_case':key2,'observer_refinement':observations})
  save(out/'observer-and-time-controls.json',anchors)
  status['phase']='qx-evidence-transfer';beat();qx=audit(evidence,out/'qx-transfer')
  fields=[]
  for f in sorted((out/'fields').glob('*.npz')):
   with zipfile.ZipFile(f) as z:
    if z.testzip():raise ValueError('NPZ CRC failure')
   fields.append({'file':str(f.relative_to(out)),'sha256':digest(f),'bytes':f.stat().st_size})
  save(out/'field-manifest.json',{'recorded_at':stamp(),'files':fields,'scope':'Local float64 arrays; no deletion or automatic archive upload'})
  record.update(status='complete_pending_review',finished_at=stamp(),completed_cases=status['completed_cases'],observer_and_time_controls=anchors,qx_transfer='qx-transfer/qx-audit.json');save(recpath,record)
  from .followup_report import render
  render(out)
  code=out/'code';code.mkdir(exist_ok=True)
  for f in Path(__file__).parent.glob('*.py'):shutil.copy2(f,code/f.name)
  shutil.copy2(config,out/'FOLLOWUP.json')
  status.update(status='complete_pending_review',phase='complete',report=str(out/'REPORT.html'),evidence=str(out/'evidence.zip'));beat()
  files=[f for f in out.rglob('*') if f.is_file() and 'fields' not in f.relative_to(out).parts and f.name not in ['evidence.zip','runner.log','SHA256SUMS'] and not f.name.endswith('.tmp')]
  (out/'SHA256SUMS').write_text(''.join(digest(f)+'  '+f.relative_to(out).as_posix()+'\n' for f in sorted(files)))
  with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
   for f in files+[out/'SHA256SUMS']:z.write(f,f.relative_to(out).as_posix())
  print('Upload: '+str(out/'evidence.zip'),flush=True)
 except BaseException as e:
  status.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'error',error=str(e));beat();raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--source-run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--qx-evidence',type=Path,required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args();run(a.repo.resolve(),a.source_run.resolve(),a.output.resolve(),a.config.resolve(),a.qx_evidence.resolve(),a.smoke)
