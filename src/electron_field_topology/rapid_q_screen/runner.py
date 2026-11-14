"""Isolated bounded static funnel; no automatic physical-time trajectories."""
import csv,json,os,platform,shutil,signal,subprocess,threading,time,traceback,zipfile
from pathlib import Path
import numpy as np
from .common import load,save,sha,canonical,stamp,log,memory_guard
from .engine import Engine,checkpoint,restore
from .catalogue import catalogue
from .policy import representation,stationary,classify,interval,trend

def sealed(path,value=None):
 p=Path(path);h=p.with_suffix(p.suffix+'.sha256')
 if value is not None:save(p,value);h.write_text(sha(p)+'\n');return value
 if not h.exists() or sha(p)!=h.read_text().strip():raise ValueError('Changed sealed result: '+str(p))
 return load(p)
def metrics(n,g,p):
 from electron_field_topology.sf_readmission import stationarity
 from electron_field_topology.sf_temporal_metrics import tail_band
 return {**stationarity(n,g),'tail_fraction':tail_band(n,np.zeros_like(n),g,p['shell_width'])['fraction']}
def field_from(row,out):
 path=out/row['checkpoint']
 if sha(path)!=row['checkpoint_sha256']:raise ValueError('Selected field checkpoint changed')
 with np.load(path,allow_pickle=False) as z:return z[row.get('field_key','n')].copy()
def branch(seed,g,engine,target,out,folder,p,identity,initial_field=None):
 folder.mkdir(parents=True,exist_ok=True);result_path=folder/f'result-{target:04d}.json'
 if result_path.exists():
  r=sealed(result_path);field_from(r,out);return r
 branch_identity={**identity,'seed':seed,'shape':list(g.shape),'lengths':list(g.lengths),'backend':engine.kind};latest=folder/'latest.npz';history=load(folder/'history.json') if (folder/'history.json').exists() else []
 if latest.exists():s=restore(latest,engine,branch_identity)
 else:
  from electron_field_topology.sf_candidate_seeds import sampled
  n=initial_field if initial_field is not None else sampled(g,seed);s=engine.state(n);engine.audit(s['n'],g,p['qualification_rtol'],p['qualification_atol']);m=metrics(n,g,p);history=[{'recorded_at':stamp(),'iteration':0,**m}];checkpoint(latest,s,engine,branch_identity);shutil.copy2(latest,folder/'initial.npz');save(folder/'history.json',history)
 if not history:
  history=[{'recorded_at':stamp(),'iteration':s['iteration'],**metrics(engine.host(s['n']),g,p)}];save(folder/'history.json',history)
 if s['iteration']==0 and not (folder/'initial.npz').exists():shutil.copy2(latest,folder/'initial.npz')
 if history[-1]['iteration']!=s['iteration']:
  m=metrics(engine.host(s['n']),g,p);engine.audit(s['n'],g,p['qualification_rtol'],p['qualification_atol']);history.append({'recorded_at':stamp(),'iteration':s['iteration'],'recovered_checkpoint_observation':True,**m});save(folder/'history.json',history)
 first=history[0];spacing=s.get('observe_spacing') or p['initial_observe_interval'];next_observe=s.get('next_observe') or s['iteration']+spacing;s.update(observe_spacing=spacing,next_observe=next_observe);reason=None
 try:
  while s['iteration']<target and representation(history[-1],seed['q'],p) and not stationary(history[-1],seed['q'],p):
   if shutil.disk_usage(out).free<p['disk_reserve_gib']*1024**3:raise RuntimeError('Disk reserve reached; source data retained')
   accepted,step=engine.step(s,g)
   if not accepted:reason=step['reason'];break
   if s['iteration']>=next_observe or s['iteration']==target:
    engine.sync();host=engine.host(s['n']);m=metrics(host,g,p);audit=engine.audit(s['n'],g,p['qualification_rtol'],p['qualification_atol']);history.append({'recorded_at':stamp(),'iteration':s['iteration'],**m,'backend_audit':audit});spacing,choice=interval(history,spacing,p);next_observe=s['iteration']+spacing
    s.update(observe_spacing=spacing,next_observe=next_observe);checkpoint(latest,s,engine,branch_identity);save(folder/'history.json',history);save(folder/'next-observation.json',{'recorded_at':stamp(),'next_iteration':next_observe,'interval':spacing,**choice});log('Candidate checkpoint',seed=seed['id'],nodes=g.shape[0],iteration=s['iteration'],force=m['relative_force_l2'])
  host=engine.host(s['n']);m=metrics(host,g,p);engine.audit(s['n'],g,p['qualification_rtol'],p['qualification_atol']);checkpoint(latest,s,engine,branch_identity)
  if history[-1]['iteration']!=s['iteration']:history.append({'recorded_at':stamp(),'iteration':s['iteration'],**m});save(folder/'history.json',history)
 except BaseException:
  checkpoint(latest,s,engine,branch_identity);save(folder/'history.json',history);raise
 stage=folder/f'stage-{target:04d}.npz';shutil.copy2(latest,stage)
 r={'recorded_at':stamp(),'seed':seed,'q':seed['q'],'nodes':g.shape[0],'length':g.lengths[0],'backend':engine.kind,'iteration':s['iteration'],'requested_iterations':target,'initial':first,'metrics':m,'classification':classify(m,first,seed['q'],p,m['tail_fraction']),'reason':reason,'history':history,'trend':trend(history),'checkpoint':stage.relative_to(out).as_posix(),'checkpoint_sha256':sha(stage),'field_key':'n','origin':'new static screening; optimizer iteration is not model time','branch_identity_sha256':canonical(branch_identity)}
 return sealed(result_path,r)

def reuse(seed,past,past_run,out,p):
 from electron_field_topology.sf_time import Grid
 candidates=[]
 for key,row in past['rest'].items():
  match=seed['family']=='reference' and key=='q2-reference' or row.get('lineage',{}).get('seed_sha256')==canonical(seed)
  if match:candidates.append((key,row))
 if not candidates:return None
 # Prefer actual stationary endpoints, then the least expensive geometry.
 key,row=min(candidates,key=lambda kv:(kv[1]['status']!='stationary',kv[1]['nodes'],kv[0]))
 source=(past_run/row['checkpoint']).resolve()
 if not source.is_relative_to(past_run.resolve()) or sha(source)!=row['checkpoint_sha256']:raise ValueError('Past field hash mismatch: '+key)
 with zipfile.ZipFile(source) as z:
  if z.testzip() is not None:raise ValueError('Past NPZ CRC failure')
 with np.load(source,allow_pickle=False) as z:
  n=z['field'].copy()
  if n.dtype!=np.float64 or n.shape!=(row['nodes'],)*3+(3,):raise ValueError('Past field precision/geometry mismatch')
 g=Grid((row['nodes'],)*3,(row['length'],)*3,'fixed');m=metrics(n,g,p);dest=out/'reused'/f'{seed["id"]}.npz';dest.parent.mkdir(exist_ok=True);shutil.copy2(source,dest)
 c=classify(m,m,seed['q'],p,m['tail_fraction'])
 if row['status']!='stationary':c={'decision':'prior_unresolved','reason':'Previously allocated preparation retained; no automatic repeat or physical Q rejection'}
 return {'recorded_at':stamp(),'seed':seed,'q':seed['q'],'nodes':row['nodes'],'length':row['length'],'backend':'cpu-audited-prior','iteration':row.get('native_result',{}).get('iterations',0),'initial':m,'metrics':m,'classification':c,'checkpoint':dest.relative_to(out).as_posix(),'checkpoint_sha256':sha(dest),'field_key':'field','origin':'authenticated prior survey state','prior_rest_id':key,'prior_native_status':row['status'],'prior_source_checkpoint_sha256':row['checkpoint_sha256'],'scope':'Existing evidence reused, not fresh screening or a new motion certificate'}

def report(out,r):
 rows=[]
 for phase in ['broad','priority','confirmation']:
  for row in r[phase]:rows.append({'phase':phase,'seed':row['seed']['id'],'q':row['q'],'nodes':row['nodes'],'origin':row['origin'],'backend':row['backend'],'iteration':row['iteration'],'decision':row['classification']['decision'],'force':row['metrics']['relative_force_l2'],'acceleration':row['metrics']['acceleration_max'],'tail_fraction':row['metrics']['tail_fraction']})
 with (out/'screening.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 import html
 table=''.join('<tr>'+''.join('<td>'+html.escape(str(v[k]))+'</td>' for k in rows[0])+'</tr>' for v in rows);heads=''.join('<th>'+k+'</th>' for k in rows[0])
 text='''<!doctype html><html><meta charset="utf-8"><title>Rapid Q screening</title><style>body{font:15px/1.6 system-ui;margin:25px}table{border-collapse:collapse}td,th{padding:7px;border-bottom:1px solid #ddd;text-align:left}</style><h1>Rapid SF Q screening</h1><p>'''+html.escape(json.dumps(r['finished_at']))+'''</p><p>Static D4 preparation only. No physical-time trajectory, exact integer-topology certificate, stability proof or electron acceptance. Early force decay sets compute priority; it does not certify future stationarity or motion. Unresolved/capacity-limited configurations are deferred, not rejected Q values.</p><p>'''+html.escape(json.dumps(r['counts']))+'''</p><p><a href="prior-survey-outcomes.json">Retained prior outcomes</a> · <a href="screening.csv">Decision table</a> · <a href="record.json">Full provenance and decisions</a> · <a href="motion-followup-queue.json">Conditional follow-up queue</a></p><table><tr>'''+heads+'''</tr>'''+table+'''</table><p>Original acceptance gates and all prior failures remain unchanged. CPU float64 stationarity/tail audits govern every decision. CUDA is used only with the exact local accuracy/timing receipt; no mid-branch backend fallback. GPU success is not inferred from NumPy host tests. All historical back-tests are retrospective and correlated, with unresolved endpoints censored.</p></html>'''
 (out/'REPORT.html').write_text(text);(out/'SUMMARY.md').write_text('# Rapid Q screening\n\n'+json.dumps(r['finished_at'])+'\n\nStatus: **complete_pending_review**.\n\n'+json.dumps(r['counts'])+'\n\nNo new motion, Q elimination or physical acceptance. Deferred branches and prior failures retained.\n')
def run(repo,past_run,out,config,benchmark_receipt,past_evidence):
 from electron_field_topology.sf_time import Grid
 from electron_field_topology.sf_candidate_seeds import sampled
 from electron_field_topology.sf_reconstruction import sample_cubic
 p=load(config);memory_guard(p['memory_min_available_gib']);bench=load(benchmark_receipt);past=load(past_run/'campaign.json');out.mkdir(parents=True,exist_ok=True)
 save(out/'prior-survey-outcomes.json',{'recorded_at':stamp(),'source_run':past_run.name,'source_evidence_sha256':sha(past_evidence),'rest':{k:{'status':v['status'],'q':v['q'],'seed_id':v['seed_id'],'checkpoint_sha256':v['checkpoint_sha256']} for k,v in past['rest'].items()},'motion':{k:{'status':v['status']} for k,v in past.get('cases',{}).items()},'scope':'All original unresolved/failed/admission-rejected outcomes retained. Reuse is not fresh validation.'})
 identity={'config_sha256':sha(config),'benchmark_sha256':sha(benchmark_receipt),'past_evidence_sha256':sha(past_evidence),'source_commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'code_sha256':{f.name:sha(f) for f in Path(__file__).parent.glob('*.py')},'threads':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']}}
 if (out/'identity.json').exists():
  if load(out/'identity.json')!=identity:raise ValueError('Screen identity changed on resume')
 else:save(out/'identity.json',identity)
 receipt=out/'benchmark.json'
 if not receipt.exists():shutil.copy2(benchmark_receipt,receipt)
 if sha(receipt)!=identity['benchmark_sha256']:raise ValueError('Benchmark receipt changed')
 stop=threading.Event()
 def heartbeat():
  while not stop.wait(15):save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid()})
 threading.Thread(target=heartbeat,daemon=True).start()
 def interrupted(*_):raise KeyboardInterrupt('Screen stop requested')
 signal.signal(signal.SIGTERM,interrupted)
 started=load(out/'started.json') if (out/'started.json').exists() else {'recorded_at':stamp()};save(out/'started.json',started);r={**started,'status':'working','identity':identity,'plan':p,'broad':[],'priority':[],'confirmation':[],'deferrals':[],'q1':'parked'}
 engines={}
 def engine(nodes):
  row=next(v for v in bench['rows'] if v['nodes']==nodes);kind=row['selected_backend']
  if kind not in engines:engines[kind]=Engine(kind)
  if kind=='cuda' and engines[kind].port.identity()!=bench['cuda_identity']:raise ValueError('CUDA device/runtime differs from qualified receipt')
  return engines[kind]
 def state(phase,seed):save(out/'status.json',{'recorded_at':stamp(),'status':'working','phase':phase,'seed':seed['id'],'pid':os.getpid(),'completed_broad':len(r['broad'])})
 try:
  for seed in catalogue(p):
   state('broad',seed);f=out/'broad'/(seed['id']+'.json')
   if f.exists():row=sealed(f);field_from(row,out);r['broad'].append(row);continue
   prior=reuse(seed,past,past_run,out,p)
   if prior is not None:row=prior
   else:
    attempts=[];row=None
    for nodes in p['grids']:
     g=Grid((nodes,)*3,(p['length'],)*3,'fixed');n=sampled(g,seed);m=metrics(n,g,p);attempts.append({'recorded_at':stamp(),'nodes':nodes,'initial_metrics':m,'field_state_sha256':canonical({'shape':n.shape,'sha':__import__('hashlib').sha256(n.tobytes()).hexdigest()})})
     if representation(m,seed['q'],p):
      row=branch(seed,g,engine(nodes),p['initial_iterations'],out,out/'branches'/seed['id']/str(nodes),p,identity)
      if row['classification']['decision']!='refine_representation':break
    if row is None:
     # A finite initial seed is retained even when no tested grid resolves it.
     e=Engine('cpu');s=e.state(n);dest=out/'unresolved'/f'{seed["id"]}.npz';checkpoint(dest,s,e,{**identity,'seed':seed,'initial_only':True});row={'recorded_at':stamp(),'seed':seed,'q':seed['q'],'nodes':nodes,'length':p['length'],'backend':'cpu','iteration':0,'metrics':m,'initial':m,'classification':{'decision':'defer_resolution','reason':'No declared grid passed measured representation; not a Q rejection'},'checkpoint':dest.relative_to(out).as_posix(),'checkpoint_sha256':sha(dest),'field_key':'n','origin':'unresolved fresh seed'}
    row['representation_attempts']=attempts
   sealed(f,row);r['broad'].append(row)
  choices=[]
  for q in p['q_values']:
   eligible=[v for v in r['broad'] if v['q']==q and v['origin'].startswith('new static') and v['classification']['decision']=='priority_continue']
   if eligible:choices.append(min(eligible,key=lambda v:(v['metrics']['relative_force_l2']/max(v['initial']['relative_force_l2'],1e-30),v['seed']['id'])))
  choice_file=out/'priority-choices.json';choice_payload=[v['seed']['id'] for v in choices]
  if choice_file.exists():
   if load(choice_file)['seeds']!=choice_payload:raise ValueError('Priority choices changed')
  else:save(choice_file,{'recorded_at':stamp(),'seeds':choice_payload,'policy':'At most one early-priority configuration per Q; no cross-Q raw-energy cutoff'})
  for row in choices:
   seed=row['seed'];state('priority',seed);g=Grid((row['nodes'],)*3,(row['length'],)*3,'fixed');r['priority'].append(branch(seed,g,engine(row['nodes']),p['priority_iterations'],out,out/'branches'/seed['id']/str(row['nodes']),p,identity))
  survivors=[v for v in r['priority']+r['broad'] if v['classification']['decision']=='static_survivor' and v['origin'].startswith('new static')];by_q={}
  for v in survivors:
   if v['q'] not in by_q or v['metrics']['relative_force_l2']<by_q[v['q']]['metrics']['relative_force_l2']:by_q[v['q']]=v
  candidates=sorted(by_q.values(),key=lambda v:(v['q'],v['seed']['id']));count=min(len(candidates),p['maximum_confirmation_branches']);indices=sorted(set(np.rint(np.linspace(0,len(candidates)-1,count)).astype(int))) if count else [];confirm=[candidates[i] for i in indices]
  confirmation_file=out/'confirmation-choices.json';confirmation_ids=[v['seed']['id'] for v in confirm]
  if confirmation_file.exists():
   if sealed(confirmation_file)['seeds']!=confirmation_ids:raise ValueError('Confirmation choices changed')
  else:sealed(confirmation_file,{'recorded_at':stamp(),'seeds':confirmation_ids,'policy':'Even coverage of surviving Q values within bounded confirmation capacity; no raw-energy cross-Q cutoff'})
  for i,row in enumerate(candidates):
   if i not in indices:r['deferrals'].append({'seed':row['seed']['id'],'reason':'confirmation capacity; not physical failure'})
  for row in confirm:
   seed=row['seed'];state('mesh-confirmation',seed);i=p['grids'].index(row['nodes'])
   if i+1==len(p['grids']):r['deferrals'].append({'seed':seed['id'],'reason':'No finer declared grid for confirmation'});continue
   nodes=p['grids'][i+1];old=field_from(row,out);og=Grid((row['nodes'],)*3,(row['length'],)*3,'fixed');g=Grid((nodes,)*3,(row['length'],)*3,'fixed');n=sample_cubic(old,og,g.points(),2)[0];correction=float(np.max(abs(n[g.fixed_mask()]-[0,0,1])));n[g.fixed_mask()]=[0,0,1]
   result=branch(seed,g,engine(nodes),p['confirmation_iterations'],out,out/'confirmations'/seed['id']/str(nodes),p,{**identity,'parent_checkpoint_sha256':row['checkpoint_sha256']},n);result={**result,'parent_checkpoint_sha256':row['checkpoint_sha256'],'held_layer_correction_max':correction,'comparison_scope':'same box, changed spacing; endpoint stationarity/tail checks only, not continuum stability'};r['confirmation'].append(result)
  queue=[{'seed':v['seed']['id'],'q':v['q'],'checkpoint':v['checkpoint'],'checkpoint_sha256':v['checkpoint_sha256'],'status':'pending_boost_boundary_and_motion_admission','scope':'Two finite-grid static endpoints survived; no motion has run'} for v in r['confirmation'] if v['classification']['decision']=='static_survivor'];save(out/'motion-followup-queue.json',{'recorded_at':stamp(),'candidates':queue,'motion_execution':False})
  r['counts']={'q_values':len(p['q_values']),'seed_variants':len(r['broad']),'reused_past_states':sum(v['origin'].startswith('authenticated') for v in r['broad']),'priority_branches':len(r['priority']),'confirmation_branches':len(r['confirmation']),'conditional_motion_followups':len(queue),'hard_Q_rejections':0};r.update(status='complete_pending_review',finished_at=stamp());save(out/'record.json',r);report(out,r)
  for f in Path(__file__).parent.glob('*.py'):
   d=out/'code'/f.name;d.parent.mkdir(exist_ok=True);d.write_bytes(f.read_bytes())
  files=[v for v in out.rglob('*') if v.is_file() and v.suffix not in {'.npz','.tmp'} and v.name not in {'evidence.zip','runner.log','status.json','heartbeat.json','launch.json','SHA256SUMS'}]
  full=[{'path':v.relative_to(out).as_posix(),'bytes':v.stat().st_size,'sha256':sha(v)} for v in out.rglob('*.npz')];save(out/'field-manifest.json',{'recorded_at':stamp(),'files':full,'scope':'Full fields remain local until separately archived and verified; no deletion'});files=list(set(files+[out/'field-manifest.json']));(out/'SHA256SUMS').write_text(''.join(sha(v)+'  '+v.relative_to(out).as_posix()+'\n' for v in sorted(files)))
  with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
   for f in sorted(files)+[out/'SHA256SUMS']:z.write(f,f.relative_to(out))
  save(out/'status.json',{'recorded_at':stamp(),'status':'complete_pending_review','pid':os.getpid(),'counts':r['counts'],'evidence':str(out/'evidence.zip'),'report':str(out/'REPORT.html')})
 except BaseException as e:
  save(out/'status.json',{'recorded_at':stamp(),'status':'interrupted' if isinstance(e,KeyboardInterrupt) else 'failed','pid':os.getpid(),'error':str(e)});traceback.print_exc();raise
 finally:stop.set()
