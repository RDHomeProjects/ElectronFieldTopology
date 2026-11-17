"""Single-worker adaptive funnel; CPU audits govern every promotion."""
import argparse,csv,fcntl,html,json,os,shutil,signal,subprocess,sys,threading,time,traceback,zipfile
from pathlib import Path
from common import ROOT,load,save,sha,canonical,stamp,log,need

def source_check(repo):
 for n,h in load(ROOT/'SOURCE.json').items():need((repo/n).is_file() and sha(repo/n)==h,'Pinned source/lock differs: '+n)
 return {n:sha(repo/n) for n in load(ROOT/'SOURCE.json')}
def snapshot(folder):
 allowed={'.json','.csv','.md','.html','.py','.c','.cu','.sh','.txt','.svg','.png'}
 return {p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file() and p.suffix in allowed and not p.relative_to(folder).parts[0].startswith('restored') and not any(x in ('__pycache__','.git') for x in p.relative_to(folder).parts) and p.name not in ('SHA256SUMS','runner.log','heartbeat.json','status.json','launch.json')}
def fit_panels(out,record):
 import math
 from science.fits import predict
 panels=[];p=record['plan']
 for phase in ['broad','mesh','domain']:
  for r in record.get(phase,[]):
   folder=Path(r['endpoint']).parent if r.get('endpoint') else out/phase/r['seed']['id']/('optimizer' if phase=='broad' else '')
   if not (folder/'history.json').exists():continue
   rows=load(folder/'history.json');decisions=load(folder/'decisions.json') if (folder/'decisions.json').exists() else [];choice=decisions[-1] if decisions else None
   if len(rows)<2:continue
   keys=[('relative_force_l2',p['force_limit'],'#2563eb'),('acceleration_max',p['acceleration_limit'],'#dc2626')]
   xmax=max(rows[-1]['iteration'],(choice['iteration']+choice['steps']) if choice else 1,1);ys=[math.log10(max(row[k]/gate,1e-12)) for row in rows for k,gate,c in keys];low=min(-.2,min(ys));high=max(.2,max(ys));span=max(high-low,.1)
   x=lambda v:55+610*v/xmax;y=lambda v:210-170*(math.log10(max(v,1e-12))-low)/span
   svg='<svg viewBox="0 0 710 250" style="max-width:900px;width:100%" role="img" aria-label="Normalized force and acceleration histories"><rect x="55" y="40" width="610" height="170" fill="#f8fafc"/><path d="M55 40V210H665" fill="none" stroke="#64748b"/>'
   gate_y=y(1);svg+=f'<path d="M55 {gate_y:.2f}H665" stroke="#334155" stroke-dasharray="4 4"/><text x="58" y="30" font-size="12">Force / gate (blue), acceleration / gate (red); log scale; dashed = fit prediction</text><text x="300" y="242" font-size="12">Optimizer iteration</text><text x="55" y="226" font-size="11">0</text><text x="640" y="226" font-size="11">{xmax}</text>'
   for k,gate,color in keys:
    points=' '.join(f"{x(row['iteration']):.2f},{y(row[k]/gate):.2f}" for row in rows);svg+=f'<polyline points="{points}" stroke="{color}" fill="none" stroke-width="1.5"/>'
    if choice and choice.get('models',{}).get(k,{}).get('accepted'):
     model=choice['models'][k]['accepted'][0];start=choice['iteration'];end=start+choice['steps'];sample=[start+(end-start)*i/20 for i in range(21)];points=' '.join(f'{x(t):.2f},{y(float(predict(model,t))/gate):.2f}' for t in sample if float(predict(model,t))>0);svg+=f'<polyline points="{points}" stroke="{color}" fill="none" stroke-dasharray="5 3"/>'
   svg+='</svg>';label=html.escape(phase+' / '+r['seed']['id']+' / '+r['status']);details=html.escape(json.dumps(choice,indent=2)) if choice else 'Bootstrap only: no fit-based extension.'
   panels.append('<details><summary>'+label+'</summary>'+svg+'<details><summary>Last allocation and fitted coefficients</summary><pre>'+details+'</pre></details></details>')
 return ''.join(panels)
def report(out,record,seal=False):
 rows=[]
 for phase in ['broad','mesh','domain']:
  for r in record.get(phase,[]):
   m=r.get('metrics',{});rows.append({'phase':phase,'seed':r['seed']['id'],'q':r['q'],'nodes':r.get('nodes'),'backend':r.get('backend'),'attempts':r.get('attempts',0),'iteration':r.get('iteration',0),'status':r['status'],'force':m.get('relative_force_l2'),'acceleration':m.get('acceleration_max'),'tail':m.get('tail_fraction'),'physical_Q_rejected':False})
 headers=list(rows[0]) if rows else ['phase','seed','q','status']
 with (out/'screening.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=headers,lineterminator='\n');w.writeheader();w.writerows(rows)
 table='<tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r.get(h,'')))+'</td>' for h in headers)+'</tr>' for r in rows)
 text='<!doctype html><html lang="en"><meta charset="utf-8"><title>Adaptive Q17–Q32 screen</title><style>body{font:15px/1.5 system-ui;margin:25px}td,th{padding:7px;border-bottom:1px solid #ddd;text-align:left}table{border-collapse:collapse}pre{white-space:pre-wrap}details{margin:12px 0}</style><h1>Adaptive Q17–Q32 screening</h1><p>'+html.escape(record['status'])+'</p><p>Optimizer steps are not physical time. Model fits determine allocations and observations; only measured original gates permit promotion. Unresolved and capacity-limited cases do not reject Q sectors. All full fields stay local until independently archived.</p><p><a href="record.json">Complete record</a> · <a href="screening.csv">CSV</a> · <a href="NATIVE-BRIDGE.json">Native operator comparison</a> · <a href="Q2-CONTROL.json">Q2 instrument</a> · <a href="motion-queue.json">Motion outcomes and deferrals</a></p><table>'+table+'</table><h2>Measured histories and fitted allocations</h2>'+fit_panels(out,record)+'<h2>Counts and scope</h2><pre>'+html.escape(json.dumps(record.get('counts',{}),indent=2))+'</pre></html>'
 (out/'REPORT.html').write_text(text);(out/'SUMMARY.md').write_text('# Adaptive Q17–Q32 screening\n\n'+json.dumps(stamp())+'\n\nStatus: **'+record['status']+'**.\n\n'+json.dumps(record.get('counts',{}))+'\n\nNo Q sector is physically rejected; screen success is not long-time stability or electron acceptance.\n')
 if seal:
  fields=[{'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*.npz')]
  save(out/'field-manifest.json',{'recorded_at':stamp(),'fields':fields,'scope':'Original inputs, initial/bootstrap/turn/final/promoted fields, rolling optimizer recovery states and moving milestones remain local; no deletion or automatic cleanup'})
  payload=snapshot(out);(out/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in sorted(payload.items())))
  with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
   for n in sorted(payload):z.write(out/n,n)
   z.write(out/'SHA256SUMS','SHA256SUMS')
  with zipfile.ZipFile(out/'evidence.zip') as z:need(z.testzip() is None,'Final compact archive CRC failed')

def execute(repo,out,backend,mode,allow_restore):
 source=source_check(repo);sys.path.insert(0,str(repo/'src'))
 import numpy as np
 from electron_field_topology.sf_time import Grid
 from electron_field_topology.sf_reconstruction import sample_cubic
 from science.catalogue import catalogue,field
 from science.numeric import Branch,metrics,representation,stationary,boundary,qualify_geometry,immutable_field,resources
 from science.fits import decide
 from science.native import control,bridge
 from science import motion
 p=load(ROOT/'PLAN.json');out.mkdir(parents=True,exist_ok=True)
 full_sources={f.relative_to(repo).as_posix():sha(f) for f in (repo/'src/electron_field_topology').rglob('*') if f.is_file() and f.suffix in ('.py','.c','.cu')}
 identity={'package_sha256':sha(ROOT/'SHA256SUMS'),'plan_sha256':sha(ROOT/'PLAN.json'),'source_sha256':source,'complete_numerical_source_sha256':full_sources,'checkout_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'requested_backend':backend,'threads':os.environ.get('OMP_NUM_THREADS')}
 if (out/'identity.json').exists():need(load(out/'identity.json')==identity,'Run identity changed; no backend/source/plan changes on resume')
 else:save(out/'identity.json',identity)
 resources(out,p)
 from science.instruments import qualify
 if (out/'host-instruments.json').exists():
  instrument=load(out/'host-instruments.json');need(instrument.get('identity')==canonical(identity) and instrument['status']=='host_instruments_passed','Host qualification receipt identity differs')
 else:
  instrument=qualify();instrument['identity']=canonical(identity);save(out/'host-instruments.json',instrument)
 engines={}
 def geometry(g):return qualify_geometry(g,p,out/'qualification'/('-'.join(map(str,g.shape))+'-L'+str(g.lengths[0])),backend)
 if mode=='benchmark':
  pairs={(n,p['length']) for n in p['grids']+[p['confirmation_nodes'],p['fallback_confirmation_nodes']]}
  for parent in [p['confirmation_nodes'],p['fallback_confirmation_nodes']]:
   n=parent+2*p['domain_padding_nodes_per_side'];pairs.add((n,p['length']*(n-1)/(parent-1)))
  for n,length in sorted(pairs):geometry(Grid((n,)*3,(length,)*3,'fixed'))
  save(out/'status.json',{'recorded_at':stamp(),'status':'benchmark_complete'});return
 q2=control(repo,out,p)
 if not (out/'NATIVE-BRIDGE.json').exists():bridge(repo,out,p,allow_restore)
 if mode=='preflight':
  geometry(Grid((p['grids'][0],)*3,(p['length'],)*3,'fixed'));save(out/'status.json',{'recorded_at':stamp(),'status':'preflight_pass','native':load(out/'NATIVE-BRIDGE.json')['status']});return
 stop=threading.Event();phase={'name':'broad-bootstrap'}
 def heartbeat():
  from runtime import process_identity
  while not stop.wait(15):
   operation=dict(phase)
   if operation.get('folder'):
    history_path=Path(operation['folder'])/'history.json'
    if history_path.exists():
     row=load(history_path)[-1];operation.update(iteration=row['iteration'],relative_force_l2=row['relative_force_l2'],acceleration_max=row['acceleration_max'])
   if operation.get('motion_folder'):
    history_path=Path(operation['motion_folder'])/'history.json'
    if history_path.exists():
     row=load(history_path)[-1];operation.update(time=row['time'],step=row['step'],shape_relative=row.get('shape_relative'),speed_relative=row.get('speed_relative'))
   save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid(),'process_identity':process_identity(os.getpid()),'phase':phase['name'],'operation':operation})
 threading.Thread(target=heartbeat,daemon=True).start()
 def interrupted(*_):raise KeyboardInterrupt('Campaign stop requested; accepted checkpoints retained')
 signal.signal(signal.SIGTERM,interrupted)
 record={'started_at':load(out/'started.json') if (out/'started.json').exists() else stamp(),'status':'working','identity':identity,'plan':p,'broad':[],'mesh':[],'domain':[],'deferrals':[],'motion':[]}
 save(out/'started.json',record['started_at']);save(out/'CATALOGUE.json',catalogue(p));shutil.copytree(ROOT,out/'handover',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 for name in full_sources:
  target=out/'numerical-source'/name;target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():shutil.copy2(repo/name,target)
 def update():
  spent=sum(load(f)['attempts'] for f in out.rglob('attempts.json'))
  record['counts']={'q_values':16,'declared_fresh_seed_variants':34,'broad_bootstrapped_or_classified':len(record['broad']),'broad_terminal':sum(r['status']!='active' for r in record['broad']),'mesh_branches':len(record['mesh']),'domain_branches':len(record['domain']),'motion_cases':len(record['motion']),'maximum_optimizer_attempts':34*p['branch_attempt_budget']+p['maximum_mesh_branches']*p['mesh_attempt_budget']+p['maximum_domain_branches']*p['domain_attempt_budget'],'spent_optimizer_attempts':spent,'physical_Q_rejections':0};save(out/'record.json',record);report(out,record);save(out/'status.json',{'recorded_at':stamp(),'status':record['status'],'phase':phase['name'],'counts':record['counts'],'error':record.get('error')})
 def branch_once(seed,g,folder,budget,bootstrap=False,initial=None,parent=None):
  phase.update(seed=seed['id'],nodes=g.shape[0],folder=str(folder),attempt_budget=budget)
  result=folder/'result.json'
  if result.exists() and load(result)['status']!='active':
   need(load(folder/'result.seal.json')['sha256']==sha(result),'Cached branch result checksum differs')
   r=load(result);need(r['identity']==canonical({**identity,**({'parent':parent} if parent else {}),'seed':seed,'shape':list(g.shape),'lengths':list(g.lengths),'backend':r['backend']}),'Cached branch identity differs')
   if r.get('endpoint'):need(sha(r['endpoint'])==r['checkpoint_sha256'],'Cached branch endpoint changed')
   return r
  b=Branch(folder,g,seed,p,geometry(g),{**identity,**({'parent':parent} if parent else {})},initial)
  last=b.history[-1];status=None;reason=None
  if not representation(last,seed['q'],p):status='representation_unresolved'
  elif stationary(last,seed['q'],p):status='static_survivor' if boundary(last,p) else 'stationary_boundary_unresolved'
  elif bootstrap:
   reason=b.batch(min(p['bootstrap_steps']-b.s['iteration'],budget-b.attempts),p['initial_observe'],budget)
   immutable_field(folder/'bootstrap.npz',b.engine.host(b.s['n']),g,seed['q'],b.identity,b.s['iteration'])
  else:
   choice=decide(b.history,p,budget-b.attempts,b.plateaus);save(folder/'planner.json',choice);b.plateaus=choice.get('plateau_count',0)
   need(not choice.get('systemic_fault'),choice['reason'])
   decisions=load(folder/'decisions.json') if (folder/'decisions.json').exists() else [];decisions.append({'recorded_at':stamp(),**choice});save(folder/'decisions.json',decisions)
   if choice['action']=='stop':status='budget_exhausted_unresolved' if b.attempts>=budget else 'preparation_unresolved';reason=choice['reason']
   else:
    if choice.get('turn_detected'):
     epoch=b.s['iteration']//200;prefix=f'turn-e{epoch}-'
     if len(list(folder.glob(prefix+'*.npz')))<p['maximum_turn_snapshots_per_optimizer_epoch']:immutable_field(folder/f'{prefix}{b.s["iteration"]:05d}.npz',b.engine.host(b.s['n']),g,seed['q'],b.identity,b.s['iteration'])
    reason=b.batch(choice['steps'],choice['observe'],budget)
  last=b.history[-1]
  if not representation(last,seed['q'],p):status='representation_unresolved'
  elif stationary(last,seed['q'],p):status='static_survivor' if boundary(last,p) else 'stationary_boundary_unresolved'
  elif reason and status is None:status='preparation_unresolved'
  elif b.attempts>=budget:status='budget_exhausted_unresolved'
  r=b.result(status or 'active',reason);del b;return r
 try:
  # Give every declared seed its bootstrap before any receives a deeper allocation.
  for seed in catalogue(p):
   folder=out/'broad'/seed['id'];initial_meta=folder/'initial-selection.json';folder.mkdir(parents=True,exist_ok=True)
   if initial_meta.exists():choice=load(initial_meta);nodes=choice['nodes']
   else:
    attempts=[];chosen=None
    for n in p['grids']:
     g=Grid((n,)*3,(p['length'],)*3,'fixed')
     try:
      raw=field(g,seed);immutable_field(folder/f'initial-grid{n}.npz',raw,g,seed['q'],identity);m=metrics(raw,g,p);attempts.append({'nodes':n,'metrics':m,'representation_pass':representation(m,seed['q'],p)})
      if representation(m,seed['q'],p):chosen=n;break
     except ValueError as e:attempts.append({'nodes':n,'representation_pass':False,'error':str(e)})
    nodes=chosen or p['grids'][-1];choice={'recorded_at':stamp(),'nodes':nodes,'attempts':attempts,'resolved':chosen is not None};save(initial_meta,choice)
   g=Grid((nodes,)*3,(p['length'],)*3,'fixed')
   if not choice['resolved']:
    r={'recorded_at':stamp(),'seed':seed,'q':seed['q'],'nodes':nodes,'status':'representation_unresolved','attempts':0,'reason':'No declared initial grid represented this seed; not a Q rejection','metrics':choice['attempts'][-1].get('metrics',{}),'physical_Q_rejected':False}
    try:immutable_field(folder/'unresolved-initial.npz',field(g,seed),g,seed['q'],identity)
    except ValueError:pass
   else:r=branch_once(seed,g,folder/'optimizer',p['branch_attempt_budget'],bootstrap=True)
   record['broad'].append(r);update()
  phase['name']='adaptive-broad'
  while any(r['status']=='active' for r in record['broad']):
   for i,r in enumerate(record['broad']):
    if r['status']!='active':continue
    g=Grid((r['nodes'],)*3,(r['length'],)*3,'fixed');record['broad'][i]=branch_once(r['seed'],g,out/'broad'/r['seed']['id']/'optimizer',p['branch_attempt_budget']);update()
  # Preserve all candidate outcomes. Capacity is a deferral, never a hidden ranking rejection.
  def rank(r):return (not r.get('strict_stationary',False),max(r['metrics']['relative_force_l2']/p['force_limit'],r['metrics']['acceleration_max']/p['acceleration_limit']),r['q'],r['seed']['id'])
  eligible=[r for r in record['broad'] if r.get('endpoint') and representation(r['metrics'],r['q'],p)];byq={}
  for r in sorted(eligible,key=rank):byq.setdefault(r['q'],r)
  selected=sorted(byq.values(),key=rank)[:p['maximum_mesh_branches']]
  selected_ids={r['seed']['id'] for r in selected}
  record['deferrals'] += [{'seed':r['seed']['id'],'reason':'mesh confirmation capacity','physical_Q_rejected':False} for r in eligible if r['seed']['id'] not in selected_ids]
  save(out/'mesh-selection.json',{'recorded_at':stamp(),'seeds':sorted(selected_ids),'policy':'One best measured normalized joint residual per Q, then four slots; no raw-energy ranking across Q'})
  phase['name']='mesh-confirmation'
  for parent in selected:
   seed=parent['seed'];fine_nodes=p['confirmation_nodes'] if parent['nodes']<p['confirmation_nodes'] else p['fallback_confirmation_nodes'];need(fine_nodes>parent['nodes'],'Mesh confirmation must use a strictly finer grid');g=Grid((fine_nodes,)*3,(p['length'],)*3,'fixed');pg=Grid((parent['nodes'],)*3,(p['length'],)*3,'fixed')
   with np.load(parent['endpoint'],allow_pickle=False) as z:old=z['field'].copy()
   initial=sample_cubic(old,pg,g.points(),2)[0];correction=float(np.max(abs(initial[g.fixed_mask()]-[0,0,1])));initial[g.fixed_mask()]=[0,0,1]
   folder=out/'mesh'/seed['id'];r=branch_once(seed,g,folder,p['mesh_attempt_budget'],True,initial,parent['checkpoint_sha256'])
   while r['status']=='active':r=branch_once(seed,g,folder,p['mesh_attempt_budget'],False,initial,parent['checkpoint_sha256'])
   r.update(parent_checkpoint_sha256=parent['checkpoint_sha256'],held_layer_correction_max=correction,energy_change=abs(r['metrics']['energy']/parent['metrics']['energy']-1),mesh_comparison_pass=bool(parent.get('strict_stationary') and r.get('strict_stationary') and abs(r['metrics']['energy']/parent['metrics']['energy']-1)<=p['mesh_energy_limit']))
   record['mesh'].append(r);update()
  phase['name']='domain-comparison'
  domain_candidates=sorted([r for r in record['mesh'] if r['mesh_comparison_pass']],key=rank)
  for parent in domain_candidates[:p['maximum_domain_branches']]:
   seed=parent['seed'];nodes=parent['nodes']+2*p['domain_padding_nodes_per_side'];h=parent['length']/(parent['nodes']-1);g=Grid((nodes,)*3,(h*(nodes-1),)*3,'fixed')
   with np.load(parent['endpoint'],allow_pickle=False) as z:old=z['field'].copy()
   initial=np.broadcast_to([0.,0.,1.],g.shape+(3,)).copy();offset=(nodes-parent['nodes'])//2;initial[offset:offset+len(old),offset:offset+len(old),offset:offset+len(old)]=old
   need(np.array_equal(initial[offset:offset+len(old),offset:offset+len(old),offset:offset+len(old)],old),'Domain embedding changed original samples')
   folder=out/'domain'/seed['id'];r=branch_once(seed,g,folder,p['domain_attempt_budget'],True,initial,parent['checkpoint_sha256'])
   while r['status']=='active':r=branch_once(seed,g,folder,p['domain_attempt_budget'],False,initial,parent['checkpoint_sha256'])
   r.update(parent_checkpoint_sha256=parent['checkpoint_sha256'],spacing_unchanged=True,domain_energy_change=abs(r['metrics']['energy']/parent['metrics']['energy']-1),domain_comparison_pass=bool(r.get('strict_stationary') and abs(r['metrics']['energy']/parent['metrics']['energy']-1)<=p['mesh_energy_limit']))
   record['domain'].append(r);update()
  record['deferrals'] += [{'seed':r['seed']['id'],'reason':'domain comparison capacity','physical_Q_rejected':False} for r in domain_candidates[p['maximum_domain_branches']:]]
  queue=[r for r in record['domain'] if r.get('domain_comparison_pass') and r.get('boundary_admitted')][:p['maximum_motion_branches']]
  phase.update(name='conditional-motion',folder=None,seed=None)
  save(out/'motion-queue.json',{'recorded_at':stamp(),'selected':[r['seed']['id'] for r in queue],'capacity':p['maximum_motion_branches'],'scope':'Static/mesh/domain and boundary admission required before short motion'})
  if queue:
   with np.load(q2['field'],allow_pickle=False) as z:q2n=z['field'].copy()
   phase.update(seed='q2-control',motion_folder=str(out/'motion/q2-control'),dt=p['motion']['dt'])
   reference=motion.run(q2n,Grid((q2['nodes'],)*3,(q2['length'],)*3,'fixed'),2,out/'motion/q2-control',p,identity,backend,p['motion']['dt']);record['motion'].append({'seed':'q2-control',**reference});update()
   if reference['status']=='screen_pass':
    for r in queue:
     with np.load(r['endpoint'],allow_pickle=False) as z:rest=z['field'].copy()
     g=Grid((r['nodes'],)*3,(r['length'],)*3,'fixed');folder=out/'motion'/r['seed']['id'];phase.update(seed=r['seed']['id'],motion_folder=str(folder/'dt001'),dt=p['motion']['dt']);first=motion.run(rest,g,r['q'],folder/'dt001',p,identity,backend,p['motion']['dt']);case={'seed':r['seed']['id'],'first':first}
     if first['status']=='screen_pass':
      phase.update(motion_folder=str(folder/'dt0005'),dt=p['motion']['confirmation_dt']);second=motion.run(rest,g,r['q'],folder/'dt0005',p,identity,first['backend'],p['motion']['confirmation_dt']);case['half_dt']=second;case['paired_backend_fixed']=first['backend']
      if second['status']=='screen_pass' and first['backend']=='cuda':need(first['backend_qualification']['device']==second['backend_qualification']['device'],'Paired time-step device identity changed')
      if second['status']=='screen_pass':
       with np.load(folder/'dt001/final.npz',allow_pickle=False) as a,np.load(folder/'dt0005/final.npz',allow_pickle=False) as b:
        fe=float(np.linalg.norm(a['field']-b['field'])/max(np.linalg.norm(b['field']-[0,0,1]),1e-30));ve=float(np.linalg.norm(a['field_rate']-b['field_rate'])/max(np.linalg.norm(b['field_rate']),1e-30))
       case['temporal_comparison']={'field_relative_l2':fe,'rate_relative_l2':ve,'pass':fe<=p['motion']['temporal_field_limit'] and ve<=p['motion']['temporal_rate_limit'],'scope':'Two dt values, no inferred convergence order or long-time stability'}
     record['motion'].append(case);update()
   else:record['deferrals'] += [{'seed':r['seed']['id'],'reason':'Q2 motion instrument failed; static results retained'} for r in queue]
  record.update(status='complete_pending_review',finished_at=stamp());update();report(out,record,True)
  save(out/'status.json',{'recorded_at':stamp(),'status':record['status'],'counts':record['counts'],'evidence':str(out/'evidence.zip'),'report':str(out/'REPORT.html')});log('Adaptive campaign completed',counts=record['counts'],evidence=str(out/'evidence.zip'))
 except BaseException as e:
  record.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',error=str(e));update();report(out,record,True);save(out/'status.json',{'recorded_at':stamp(),'status':record['status'],'error':str(e),'evidence':str(out/'evidence.zip')});traceback.print_exc();raise
 finally:stop.set()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['preflight','benchmark','run']);parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--backend',choices=['auto','cpu','cuda'],default='auto');parser.add_argument('--no-restore',action='store_true');a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 with (a.output/'.worker.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:execute(a.repo.resolve(),a.output.resolve(),a.backend,a.mode,not a.no_restore)
  except BaseException as e:
   if not (a.output/'record.json').exists():save(a.output/'status.json',{'recorded_at':stamp(),'status':'failed','error':str(e),'phase':a.mode})
   raise
if __name__=='__main__':main()
