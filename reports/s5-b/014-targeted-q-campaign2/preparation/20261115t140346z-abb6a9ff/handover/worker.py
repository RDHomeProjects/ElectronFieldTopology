import argparse,os,sys,time,zipfile,shutil,json,threading,signal,traceback,fcntl,gc
from pathlib import Path
from support import *
p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','run']);p.add_argument('--repo',type=Path,required=True);p.add_argument('--source-run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--prior-run',type=Path,required=True);p.add_argument('--backend',choices=['auto','cpu','cuda'],required=True);a=p.parse_args()
repo=a.repo.resolve();source=a.source_run.resolve();prior=a.prior_run.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
lock=(out/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
sys.path.insert(0,str(repo/'src'))
import numpy as np
from electron_field_topology.sf_time import Grid
from electron_field_topology.sf_readmission import static_value_gradient,stationarity
from electron_field_topology.sf_temporal_metrics import tail_band
from electron_field_topology.rapid_q_screen.engine import Engine,checkpoint,restore
from electron_field_topology.rapid_q_screen.policy import representation,stationary,classify
from analysis import spatial_summary,curve_fits
PLAN=load(ROOT/'PLAN.json');GATES=load(ROOT/'GATES.json')
with zipfile.ZipFile(ROOT/'data/completed-evidence.zip') as z:
 completed=json.loads(z.read('record.json'));field_manifest=json.loads(z.read('field-manifest.json'))['files'];older_bytes=z.read('handover/data/parent-evidence.zip');completed_seals={v['seed']:json.loads(z.read('jobs/'+v['label']+'/latest.seal.json')) for v in completed['results']}
with zipfile.ZipFile(__import__('io').BytesIO(older_bytes)) as z:
 parent=json.loads(z.read('record.json'));prior_fieldmap={v['path']:v for v in json.loads(z.read('field-manifest.json'))['files']}
rows={j['job']['id']:j for j in parent['jobs']}
for v in completed['results']:
 if v['label'] in ['q8-continuation','q10-continuation','q5-fine-restart']:
  seed=rows[v['seed']]['seed'];rows[v['seed']]={**rows[v['seed']],**v,'seed':seed}
fieldmap={f['path']:f for f in field_manifest}
PROFILE=load(out/'performance.json').get('component_times',{}) if (out/'performance.json').exists() else {}
def record_time(label,seconds):
 v=PROFILE.setdefault(label,{'calls':0,'seconds':0.});v['calls']+=1;v['seconds']+=seconds
original_checkpoint=checkpoint
def checkpoint(*args):
 t=time.perf_counter()
 try:return original_checkpoint(*args)
 finally:record_time('checkpoint_compression_and_write',time.perf_counter()-t)
def audited(e,n,g):
 t=time.perf_counter()
 try:return e.audit(n,g,GATES['qualification_rtol'],GATES['qualification_atol'])
 finally:record_time('independent_CPU_device_gradient_audit',time.perf_counter()-t)

def metrics(n,g):
 t=time.perf_counter();m=stationarity(n,g);record_time('CPU_stationarity_including_Hopf',time.perf_counter()-t)
 t=time.perf_counter();tail=tail_band(n,np.zeros_like(n),g,GATES['shell_width'])['fraction'];record_time('CPU_tail_metric',time.perf_counter()-t)
 return {**m,'tail_fraction':tail}

def guard():
 mem={l.split(':')[0]:l.split(':')[1] for l in Path('/proc/meminfo').read_text().splitlines()};available=int(mem['MemAvailable'].split()[0])/1024**2
 need(available>=PLAN['memory_reserve_gib'],'Host memory reserve below 4 GiB')
 need(shutil.disk_usage(out).free>=PLAN['disk_reserve_gib']*1024**3,'Free disk reserve below 12 GiB; all fields retained')
def safe(path):
 f=(source/path).resolve();need(f.is_relative_to(source) and f.is_file(),'Missing or unsafe source field: '+str(f));return f
def source_verify(full):
 need(sha(prior/'evidence.zip')==__import__('hashlib').sha256(older_bytes).hexdigest(),'Original Q4 source archive differs')
 q4=rows['q4-axial22'];need(sha(prior/q4['checkpoint'])==q4['checkpoint_sha256'],'Original Q4 retained field differs')
 need(sha(source/'evidence.zip')==PLAN['completed_evidence_sha256'],'Wrong completed parent run')
 for name,h in load(ROOT/'SOURCE.json').items():need((repo/name).is_file() and sha(repo/name)==h,'Source/lock changed: '+name)
 for name in ['record.json','field-manifest.json']:
  with zipfile.ZipFile(ROOT/'data/completed-evidence.zip') as z:need(sha(source/name)==__import__('hashlib').sha256(z.read(name)).hexdigest(),'Parent metadata changed: '+name)
 if full:
  for f in field_manifest:
   path=safe(f['path']);need(sha(path)==f['sha256'],'Parent field changed: '+f['path'])
   with zipfile.ZipFile(path) as z:need(z.testzip() is None,'NPZ CRC failed: '+f['path'])
  log('All retained parent fields verified',count=len(field_manifest))

def read_state(path,expected,iteration,nodes):
 need(sha(path)==expected,'Selected source checkpoint hash differs')
 with np.load(path,allow_pickle=False) as z:
  need(int(z['iteration'])==iteration,'Selected checkpoint iteration differs')
  state={k:float(z[k]) if k=='alpha' else int(z[k]) for k in ['alpha','iteration','next_observe','observe_spacing']}
  for k in ['n','old_g','old_z','direction']:
   arr=z[k];need(arr.dtype==np.float64 and np.isfinite(arr).all(),'Invalid source array: '+k)
   need(arr.size==0 or arr.shape==(nodes,)*3+(3,),'Checkpoint shape differs')
   state[k]=arr.copy() if arr.size else None
  original_backend=str(z['backend']);original_identity=str(z['identity_sha256'])
 need(state['n'] is not None,'Missing source field')
 return state,{'backend':original_backend,'identity_sha256':original_identity,'sha256':expected,'path':str(path)}
def endpoint(key,start=False):
 row=rows[key]
 if key=='q4-axial22':path=(prior/row['checkpoint']).resolve();need(path.is_relative_to(prior),'Unsafe Q4 source');expected=row['checkpoint_sha256'];identity_hash=row['branch_identity_sha256']
 else:path=safe(row['checkpoint']);expected=row['checkpoint_sha256'];identity_hash=completed_seals[key]['identity_sha256']
 state,meta=read_state(path,expected,row['iteration'],row['nodes']);need(meta['identity_sha256']==identity_hash,'Source checkpoint branch identity differs')
 return state,meta

def adapt_state(s,e):return {k:(e.xp.asarray(v).copy() if k in ['n','old_g','old_z','direction'] and v is not None else v) for k,v in s.items()}
def clone_state(s,e):return adapt_state(s,e)
def cpu_replay(key,s,g,expected):
 m=metrics(s['n'],g)
 for k,v in expected.items():
  if isinstance(v,(float,int)) and k in m:need(np.isclose(m[k],v,rtol=1e-9,atol=1e-12),'CPU metric replay mismatch: '+key+' '+k)
 return m

def qualify(s,g,label):
 cpu=Engine('cpu');cpu.audit(s['n'],g);times=[]
 for i in range(3):
  disposable=adapt_state(s,cpu);t=time.perf_counter();accepted,info=cpu.step(disposable,g);cpu.sync();times.append(time.perf_counter()-t)
  if i==0:reference=cpu.host(disposable['n']);ref_accepted=accepted
  del disposable
 result={'recorded_at':stamp(),'label':label,'nodes':g.shape[0],'cpu_median_step_seconds':float(np.median(times[1:])),'disposable_cpu_steps':3,'selected_backend':'cpu','production_steps':0,'CPU_GPU_parity':None}
 if a.backend=='cpu':return result
 try:
  gpu=Engine('cuda');gs=adapt_state(s,gpu);gpu.audit(gs['n'],g,GATES['qualification_rtol'],GATES['qualification_atol']);gt=[]
  for i in range(3):
   disposable=adapt_state(s,gpu);gpu.sync();t=time.perf_counter();accepted,info=gpu.step(disposable,g);gpu.sync();gt.append(time.perf_counter()-t)
   need(accepted==ref_accepted,'CPU/GPU acceptance disagreement');actual=gpu.host(disposable['n']);need(np.allclose(reference,actual,rtol=2e-9,atol=2e-10),'CPU/GPU disposable step field disagreement')
   del disposable
  result.update(cuda_median_step_seconds=float(np.median(gt[1:])),cuda_identity=gpu.port.identity(),CPU_GPU_parity='passed',maximum_step_field_difference=float(np.max(abs(reference-actual))))
  result['speedup']=result['cpu_median_step_seconds']/max(result['cuda_median_step_seconds'],1e-12)
  if a.backend=='cuda' or result['speedup']>=GATES['gpu_speedup_required']:result['selected_backend']='cuda'
  del gpu,gs
 except Exception as ex:
  if a.backend=='cuda':raise
  result['cuda_unavailable_or_rejected']=str(ex);result['selected_backend']='cpu';log('CUDA not selected; explicit CPU qualification retained',label=label,reason=str(ex))
 gc.collect();return result

def engine_for(label,receipt):
 q=receipt['backends'][label];e=Engine(q['selected_backend'])
 if e.kind=='cuda':need(e.port.identity()==q['cuda_identity'],'CUDA runtime/device changed since qualification')
 return e

def diagnose_q10(result):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 diagnosis=[];key='q10-trefoil32-2-2';paths=[('retained200',safe('jobs/q10-continuation/stage-0200.npz')),('start300',safe(rows[key]['checkpoint'])),('new_endpoint',out/result['checkpoint'])]
 for label,path in paths:
  with np.load(path,allow_pickle=False) as z:iteration=int(z['iteration'])
  state,meta=read_state(path,sha(path),iteration,145);g=Grid((145,)*3,(23.04,)*3,'fixed');m=metrics(state['n'],g);_,raw=static_value_gradient(state['n'],g);d,mag=spatial_summary(state['n'],raw,g.spacing,g.fixed_mask(),state);d.update(label=label,iteration=iteration,metrics=m,source=meta)
  plot=out/'diagnostics'/('q10-'+label+'.png');plot.parent.mkdir(exist_ok=True);fig,ax=plt.subplots(figsize=(6,5),layout='constrained');im=ax.imshow(np.log10(np.maximum(np.max(mag,axis=2),1e-20)),origin='lower',extent=[-11.52,11.52,-11.52,11.52]);fig.colorbar(im,ax=ax,label='log10 projected raw gradient');ax.set_title('Q10 '+label+' iteration '+str(iteration));fig.savefig(plot,dpi=220);plt.close(fig);d['plot']=plot.relative_to(out).as_posix();diagnosis.append(d);del state,raw,mag;gc.collect()
 save(out/'diagnostics.json',{'recorded_at':stamp(),'Q10_diagnosed_after_requested_continuation':True,'states':diagnosis})

def fine_q5():
 # Domain-only change at exactly equal node spacing; no resampling.
 s,meta=endpoint('q5-trefoil32-1-1');n=np.zeros((145,)*3+(3,),np.float64);n[...,2]=1.;n[12:133,12:133,12:133]=s['n']
 need(np.array_equal(n[12:133,12:133,12:133],s['n']),'Aligned domain embedding changed parent samples')
 g=Grid((145,)*3,(27.648,)*3,'fixed');state=Engine('cpu').state(n);state['iteration']=100
 return state,g,{'parent':meta,'domain_embedding':'exact12-node vacuum padding per face; parent samples bitwise retained','old_nodes':121,'new_nodes':145,'old_length':23.04,'new_length':27.648,'spacing_both':.192,'restart_conjugacy_and_alpha_in_both_arms':True,'common_native_start_iteration':100,'interpolation_used':False}

def identity():return {'package_sha256':verify_package(),'repo':str(repo),'source_run':str(source),'prior_run':str(prior),'backend_request':a.backend,'source_code_sha256':load(ROOT/'SOURCE.json'),'source_commit':__import__('subprocess').check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'python':sys.version,'numpy':np.__version__,'scipy':__import__('scipy').__version__,'threads':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']}}

def preflight():
 guard();source_verify(True);backends={};replays=[]
 for key in ['q8-trefoil32-1-2','q10-trefoil32-2-2','q4-axial22','q5-trefoil32-1-1']:
  s,meta=endpoint(key);g=Grid((rows[key]['nodes'],)*3,(23.04,)*3,'fixed');m=cpu_replay(key,s,g,rows[key]['metrics']);need(representation(m,rows[key]['q'],GATES),'Selected field lacks representation admission: '+key)
  if key.startswith('q5'):s=Engine('cpu').state(s['n']);s['iteration']=100
  replays.append({'seed':key,'source':meta,'replayed_metrics':m});backends[key]=qualify(s,g,key)
  if key=='q4-axial22':
   alpha=s['alpha'];s.update(old_g=None,old_z=None,direction=None);need(s['alpha']==alpha,'Q4 alpha changed');backends['q4-memory-clear']=qualify(s,g,'q4-memory-clear')
  save(out/'qualification-progress.json',{'recorded_at':stamp(),'backends':backends});del s;gc.collect()
 s,g,embedding=fine_q5();m=metrics(s['n'],g);save(out/'q5-domain-embedding.json',{'recorded_at':stamp(),**embedding,'metrics':m,'representation_pass':representation(m,5,GATES),'tail_pass':m['tail_fraction']<=GATES['initial_tail_limit']});backends['q5-domain']=qualify(s,g,'q5-domain');del s;gc.collect()
 for left,right in [('q4-axial22','q4-memory-clear'),('q5-trefoil32-1-1','q5-domain')]:
  if backends[left]['selected_backend']!=backends[right]['selected_backend']:
   for key in [left,right]:backends[key]['selected_backend']='cpu';backends[key]['pair_backend_reason']='Common qualified CPU selected to hold backend equal within paired comparison'
 receipt={'recorded_at':stamp(),'status':'local_preflight_passed','identity':identity(),'backends':backends,'endpoint_replays':replays,'scope':'All test steps disposable; production not started; Q4 trial preserves alpha; Q5 exact aligned domain embedding at equal spacing'};save(out/'preflight.json',receipt);(out/'preflight.sha256').write_text(sha(out/'preflight.json')+'\n');log('Preflight qualified',backends={k:v['selected_backend'] for k,v in backends.items()});return receipt

def save_history(folder,h):
 save(folder/'history.json',h);(folder/'history.sha256').write_text(sha(folder/'history.json')+'\n')

def branch_job(key,label,maximum,base,receipt,fine=False,trial=False):
 folder=out/'jobs'/label;folder.mkdir(parents=True,exist_ok=True);summary=folder/'summary.json'
 if summary.exists():
  need(sha(summary)==summary.with_suffix('.sha256').read_text().strip(),'Result summary seal changed');item=load(summary);need(sha(out/item['checkpoint'])==item['checkpoint_sha256'],'Completed result checkpoint changed');return item
 e=engine_for('q5-domain' if fine else 'q4-memory-clear' if trial else key,receipt);seed=rows[key]['seed'];start=rows[key]['iteration'];g=Grid(((145 if fine else rows[key]['nodes']),)*3,((27.648 if fine else 23.04),)*3,'fixed');ident={**receipt['identity'],'seed':seed,'label':label,'shape':list(g.shape),'lengths':list(g.lengths),'backend':e.kind};latest=folder/'latest.npz'
 if latest.exists():
  s=restore(latest,e,ident);need(sha(folder/'history.json')==(folder/'history.sha256').read_text().strip(),'History seal changed');h=load(folder/'history.json')
 else:
  if fine:cs,_,provenance=fine_q5()
  else:
   cs,provenance=endpoint(key,key.startswith('q5'))
   if key.startswith('q5'):cs=Engine('cpu').state(cs['n']);cs['iteration']=100
   if trial:cs.update(old_g=None,old_z=None,direction=None)
  s=adapt_state(cs,e);s.update(observe_spacing=5,next_observe=s['iteration']+5);del cs;h=[{'recorded_at':stamp(),'iteration':s['iteration'],**metrics(e.host(s['n']),g)}];e.audit(s['n'],g);checkpoint(latest,s,e,ident);save_history(folder,h);shutil.copy2(latest,folder/'initial.npz');save(folder/'import.json',{'recorded_at':stamp(),'source':provenance,'backend':e.kind,'optimizer_continuation':'matching Q5 restart of conjugacy/alpha on both grids' if key.startswith('q5') else 'only conjugacy memory cleared; alpha retained exactly' if trial else 'all retained optimizer arrays and alpha preserved; backend migration explicit and disposable-step qualified','initial_alpha':s['alpha'],'initial_memory_present':s['old_g'] is not None,'new_observation_schedule':'paired Q4/Q5 fixed5-step observations; Q8/Q10 adaptive; all gates unchanged'})
 if h[-1]['iteration']!=s['iteration']:h.append({'recorded_at':stamp(),'iteration':s['iteration'],'recovered_checkpoint_observation':True,**metrics(e.host(s['n']),g)});save_history(folder,h)
 spacing=s.get('observe_spacing') or 5;reason=None;allocation='budget_exhausted_unresolved';next_observe=s.get('next_observe') or s['iteration']+spacing
 try:
  while s['iteration']<start+maximum:
   last=h[-1]
   if not representation(last,seed['q'],GATES):allocation='deferred_representation_loss';break
   if stationary(last,seed['q'],GATES):allocation='measured_static_survivor_pending_mesh_confirmation' if last['tail_fraction']<=GATES['initial_tail_limit'] else 'measured_stationary_boundary_followup';break
   if s['iteration']>=start+base and (s['iteration']-start)%50==0 and key.startswith('q8'):
    allowed,details=contingency(h,start);save(folder/('contingency-'+str(s['iteration'])+'.json'),{'recorded_at':stamp(),'allowed':allowed,**details})
    if not allowed:allocation='deferred_no_recent_joint_progress';break
   target=min(start+maximum,start+base if s['iteration']<start+base else ((s['iteration']-start)//50+1)*50+start)
   save(out/'status.json',{'recorded_at':stamp(),'status':'working','pid':os.getpid(),'seed':label,'native_iteration':s['iteration'],'batch_target':target,'maximum_additional_steps':maximum})
   while s['iteration']<target:
    guard();t=time.perf_counter();accepted,step=e.step(s,g);e.sync();record_time('optimizer_step_'+e.kind,time.perf_counter()-t)
    if not accepted:reason=step;allocation='deferred_solver_stall';break
    if s['iteration']>=next_observe or s['iteration']==target:
     e.sync();m=metrics(e.host(s['n']),g);audit=audited(e,s['n'],g);h.append({'recorded_at':stamp(),'iteration':s['iteration'],**m,'backend_audit':audit,'optimizer_alpha':s['alpha'],'step':{k:float(v) if isinstance(v,(np.floating,)) else v for k,v in step.items()}});spacing,why=observation_interval(h,spacing,seed['q']) if seed['q'] in [8,10] else (5,['fixed paired measurement schedule']);next_observe=min(s['iteration']+spacing,start+((s['iteration']-start)//50+1)*50);s.update(observe_spacing=spacing,next_observe=next_observe);checkpoint(latest,s,e,ident);save_history(folder,h);save(folder/'next-observation.json',{'recorded_at':stamp(),'spacing':spacing,'reasons':why,'next_iteration':next_observe});save(out/'performance.json',{'recorded_at':stamp(),'component_times':PROFILE,'scope':'Synchronized optimizer steps, CPU stationarity/tail, independent audits and checkpoint compression measured separately; other I/O and startup are unallocated wall time'});
     if (s['iteration']-start)%50==0:shutil.copy2(latest,folder/('stage-'+str(s['iteration']).zfill(4)+'.npz'))
     log('Candidate observation',seed=label,iteration=s['iteration'],joint_gate_multiple=proximity(m),spacing=spacing)
     if not representation(m,seed['q'],GATES) or stationary(m,seed['q'],GATES):break
   checkpoint(latest,s,e,ident)
   if h[-1]['iteration']!=s['iteration']:h.append({'recorded_at':stamp(),'iteration':s['iteration'],**metrics(e.host(s['n']),g)});save_history(folder,h)
   stage=folder/('stage-'+str(s['iteration']).zfill(4)+'.npz');shutil.copy2(latest,stage)
   if reason:break
  final=h[-1]
  if not representation(final,seed['q'],GATES):allocation='deferred_representation_loss'
  elif stationary(final,seed['q'],GATES):allocation='measured_static_survivor_pending_mesh_confirmation' if final['tail_fraction']<=GATES['initial_tail_limit'] else 'measured_stationary_boundary_followup'
  save(folder/'relationships.json',curve_fits(h))
  item={'recorded_at':stamp(),'seed':key,'label':label,'nodes':g.shape[0],'length':g.lengths[0],'backend':e.kind,'native_start_iteration':start,'iteration':s['iteration'],'additional_steps':s['iteration']-start,'maximum_additional_steps':maximum,'allocation_status':allocation,'reason':reason,'metrics':final,'checkpoint':latest.relative_to(out).as_posix(),'checkpoint_sha256':sha(latest),'whole_Q_rejected':False,'history':h};save(summary,item);summary.with_suffix('.sha256').write_text(sha(summary)+'\n');return item
 except BaseException:
  checkpoint(latest,s,e,ident);save_history(folder,h);raise
 finally:del s,e;gc.collect()

def report(results):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import html,base64,csv
 fig,axes=plt.subplots(3,2,figsize=(12,13),layout='constrained')
 for ax,v in zip(axes.flat,results):
  h=v['history'];x=[r['iteration']-v['native_start_iteration'] for r in h];ax.semilogy(x,[r['relative_force_l2']/1e-4 for r in h],'-o',markersize=2,label='force / gate');ax.semilogy(x,[r['acceleration_max']/1e-3 for r in h],'-s',markersize=2,label='acceleration / gate');ax.axhline(1,color='green',linestyle='--');ax.set_title(v['label']);ax.set_xlabel('Added optimizer steps');ax.grid(alpha=.2)
 axes.flat[0].legend();fig.savefig(out/'histories.png',dpi=200);plt.close(fig)
 table=[{'seed':v['label'],'nodes':v['nodes'],'added_steps':v['additional_steps'],'allocation':v['allocation_status'],'force':v['metrics']['relative_force_l2'],'acceleration':v['metrics']['acceleration_max'],'tail':v['metrics']['tail_fraction']} for v in results]
 with (out/'measurements.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 text='<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Targeted Q diagnostics</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:25px auto;padding:15px}img{max-width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere}td,th{padding:8px;border-bottom:1px solid #ddd}table{border-collapse:collapse}</style><h1>Targeted Q diagnostics and bounded continuation</h1><p>'+html.escape(json.dumps(stamp()))+'</p><p>Unchanged neutral static D4 model; optimizer steps are not physical time. Q4 compares exact continuation with memory clearing only; Q6 remains unallocated. Q7/Q9 remain deferred. Q5 compares domains at spacing0.192 from native iteration100. Requested budgets are bounded allocations; prior curve fits do not validate a passing-time prediction.</p><table><tr>'+''.join('<th>'+k+'</th>' for k in table[0])+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row.values())+'</tr>' for row in table)+'</table>'
 for path in [out/'histories.png']+sorted((out/'diagnostics').glob('*.png')):text+='<h2>'+html.escape(path.stem)+'</h2><img src="data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()+'">'
 text+='<h2>Q10 diagnosis after continuation</h2><pre>'+html.escape((out/'diagnostics.json').read_text())+'</pre><h2>Allocation basis</h2><pre>'+html.escape((ROOT/'PLAN.json').read_text())+'</pre></html>';text=text.replace('</html>','<h2>Performance components</h2><pre>'+html.escape(json.dumps(PROFILE,indent=2))+'</pre></html>');(out/'REPORT.html').write_text(text)

def seal_output():
 shutil.copytree(ROOT,out/'handover',ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
 full=[{'path':f.relative_to(out).as_posix(),'sha256':sha(f),'bytes':f.stat().st_size} for f in out.rglob('*.npz')];save(out/'field-manifest.json',{'recorded_at':stamp(),'files':full,'scope':'New full fields stay local; parent fields unchanged at recorded source paths; compact ZIP excludes NPZ'})
 excluded={'worker.lock','SHA256SUMS','evidence.zip','runner.log','status.json','heartbeat.json','launch.json'}
 payload=[f for f in out.rglob('*') if f.is_file() and f.suffix not in ['.npz','.tmp'] and f.name not in (excluded-{'SHA256SUMS'}) and f!=out/'SHA256SUMS']
 (out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.relative_to(out).as_posix()+'\n' for f in sorted(payload)))
 with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(payload)+[out/'SHA256SUMS']:z.write(f,f.relative_to(out))

def run():
 source_verify(False)
 if (out/'record.json').exists() and load(out/'record.json').get('status')=='complete_pending_review' and (out/'evidence.zip').is_file() and (out/'REPORT.html').is_file():log('Already complete',output=str(out));return
 need((out/'preflight.json').is_file() and sha(out/'preflight.json')==(out/'preflight.sha256').read_text().strip(),'Run preflight/benchmark first')
 receipt=load(out/'preflight.json');need(receipt['identity']==identity(),'Preflight identity changed; use a new output allocation')
 results=[]
 jobs=[('q8-trefoil32-1-2','q8-continuation-2',250,150,False,False),('q10-trefoil32-2-2','q10-continuation-2',150,150,False,False),('q4-axial22','q4-exact-control',50,50,False,False),('q4-axial22','q4-memory-clear',50,50,False,True),('q5-trefoil32-1-1','q5-domain-control',50,50,False,False),('q5-trefoil32-1-1','q5-domain-expanded',50,50,True,False)]
 for key,label,maximum,base,fine,trial in jobs:
  item=branch_job(key,label,maximum,base,receipt,fine,trial);results.append(item)
  if key.startswith('q10'):diagnose_q10(item)
 q4=[v for v in results if v['seed']=='q4-axial22'];save(out/'q4-comparison.json',{'recorded_at':stamp(),'common_start_checkpoint_sha256':rows['q4-axial22']['checkpoint_sha256'],'control':q4[0],'memory_clear_trial':q4[1],'only_treatment':'conjugacy memory cleared once; starting alpha retained','Q6_relaxation_steps':0,'decision':'review paired outcome before allocating Q6; no automatic promotion'})
 q5=[v for v in results if v['seed']=='q5-trefoil32-1-1'];save(out/'q5-domain-comparison.json',{'recorded_at':stamp(),'control':q5[0],'expanded':q5[1],'spacing':.192,'only_geometric_change':'domain length and node count increase together to preserve spacing; matching optimizer restarts','convergence_certified':False})
 source_verify(True);record={'recorded_at':stamp(),'status':'complete_pending_review','identity':receipt['identity'],'plan':PLAN,'results':results,'q6_relaxation_steps':0,'deferrals':[{'seed':s,'allocation_status':'explicitly_deferred','whole_Q_rejected':False} for s in PLAN['deferred']],'additional_steps':sum(v['additional_steps'] for v in results),'maximum_additional_steps':600,'motion_cases':0,'parent_fields_verified_unchanged':True,'static_readiness':[v['label'] for v in results if v['allocation_status']=='measured_static_survivor_pending_mesh_confirmation']};save(out/'record.json',record);save(out/'performance.json',{'recorded_at':stamp(),'component_times':PROFILE,'scope':'Measured components accumulated across resumes; other startup and I/O remain unallocated wall time'});report(results);seal_output();save(out/'status.json',{'recorded_at':stamp(),'status':'complete_pending_review','additional_steps':record['additional_steps'],'evidence':str(out/'evidence.zip'),'report':str(out/'REPORT.html')});log('Analysis complete pending review',output=str(out))

stop=threading.Event()
def pulse():
 while not stop.wait(15):save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid()})
def interrupt(*_):raise KeyboardInterrupt('Graceful stop requested; latest optimizer state retained')
signal.signal(signal.SIGTERM,interrupt);save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid()});threading.Thread(target=pulse,daemon=True).start()
try:
 verify_package();guard()
 if a.mode=='preflight':
  source_verify(False)
  if (out/'preflight.json').exists():need(load(out/'preflight.json')['identity']==identity(),'Existing preflight identity changed');need(sha(out/'preflight.json')==(out/'preflight.sha256').read_text().strip(),'Preflight seal changed');log('Matching preflight receipt retained')
  else:
   save(out/'status.json',{'recorded_at':stamp(),'status':'preflight_working','pid':os.getpid()});preflight();save(out/'status.json',{'recorded_at':stamp(),'status':'preflight_passed','pid':os.getpid()})
 else:run()
except BaseException as ex:
 save(out/'status.json',{'recorded_at':stamp(),'status':'interrupted' if isinstance(ex,KeyboardInterrupt) else 'failed','pid':os.getpid(),'error':str(ex)});traceback.print_exc();raise
finally:
 stop.set()
 if not ((out/'evidence.zip').exists() and (out/'status.json').exists() and load(out/'status.json').get('status')=='complete_pending_review'):save(out/'performance.json',{'recorded_at':stamp(),'component_times':PROFILE,'scope':'Measured components accumulated across resumes; unmeasured startup and I/O remain outside these totals'})
