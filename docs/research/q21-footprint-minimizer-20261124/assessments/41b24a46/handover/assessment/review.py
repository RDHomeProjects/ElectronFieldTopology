"""Independent compact-record review; does not execute archived handover code."""
import argparse,csv,hashlib,io,json,math,statistics,zipfile
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
EXPECTED='e7497eeb4c0f533ff4c999fee37480876436ccfabadc96c74167d41a9261af12'
PARENT='36f7e89797230762ad9dec9385d9132543581835b82e60c7610ef33f3ab219d8'
def stamp():
 t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def digest(data):return hashlib.sha256(data).hexdigest()
def canonical(x):return digest(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def same(a,b):assert np.isclose(a,b,rtol=2e-10,atol=1e-13),(a,b)
def check_archive(z):
 names=z.namelist();assert len(names)==len(set(names)) and all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and '\\' not in n for n in names);assert z.testzip() is None
 items={}
 for line in z.read('SHA256SUMS').decode().splitlines():
  h,n=line.split('  ',1);assert n not in items and digest(z.read(n))==h;items[n]=h
 assert set(items)|{'SHA256SUMS'}==set(names);return items

def gates(m,q):
 finite=all(math.isfinite(m[k]) for k in ['relative_force_l2','acceleration_max','hopf_integral','minimum_corner_cone','unit_error','tail_fraction','guard_fraction'])
 rep=finite and abs(abs(m['hopf_integral'])-q)/q<=.05 and m['minimum_corner_cone']>0 and m['unit_error']<1e-10
 stationary=rep and m['relative_force_l2']<=1e-4 and m['acceleration_max']<=1e-3
 boundary=finite and m['tail_fraction']<=.00075 and m['guard_fraction']<=.001
 return {'representation':rep,'strict_stationary':stationary,'boundary_admitted':boundary,'all_readiness_gates':stationary and boundary}
def window(history,left,right):
 rows=[r for r in history if left<=r['accepted_step']<=right];return {k:float(np.median([r['metrics'][k] for r in rows])) for k in ['relative_force_l2','acceleration_max','acceleration_rms']}
def refits(points,key):
 points=sorted(points,key=lambda p:p['spacing']);x=np.array([p['spacing'] for p in points]);y=np.array([p[key] for p in points]);scale=max(float(np.ptp(y)),.05*float(np.median(abs(y))),1e-12);out=[]
 for kind,degree in [('linear',1),('quadratic',2),('exponential',1)]:
  pred=[];constant=[]
  for i in range(len(x)):
   keep=np.arange(len(x))!=i;coef=np.polyfit(x[keep],np.log(y[keep]) if kind=='exponential' else y[keep],degree);value=np.polyval(coef,x[i]);pred.append(np.exp(np.clip(value,-700,700)) if kind=='exponential' else value);constant.append(y[keep].mean())
  mse=float(np.mean((pred-y)**2));baseline=float(np.mean((constant-y)**2));error=math.sqrt(mse)/scale;skill=1-mse/baseline;coef=np.polyfit(x,np.log(y) if kind=='exponential' else y,degree)
  out.append({'model':kind,'coefficients':coef.tolist(),'loo_range_nrmse':error,'skill':skill,'eligible':bool(error<=.25 and skill>=.1)})
 return out

def write_csv(path,rows):
 with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def assess(evidence,out,terminal=None,released_package=None):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);data=Path(evidence).read_bytes();assert digest(data)==EXPECTED;checks={}
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  compact=check_archive(z);checks['outer_CRC_safe_unique_paths_and_150_payload_hashes']=len(compact)==150
  originals=z.read('handover/data/completed-evidence.zip');assert digest(originals)==PARENT and originals==z.read('handover/documentation/scientific-review/data/completed-evidence.zip')
  with zipfile.ZipFile(io.BytesIO(originals)) as old:
   oldhash=check_archive(old);source=json.loads(old.read('record.json'));bulk=json.loads(old.read('BULK-LEDGER.json'));q2=json.loads(old.read('Q2-CONTROL.json'));init={c['case']['nodes']:json.loads(old.read('cases/'+c['case']['id']+'/INITIALIZATION.json')) for c in source['cases'] if c['case']['id']!='exact-control'}
  checks['original_307_payloads_and_duplicate_embedded_source_match']=len(oldhash)==307
  release=Path(released_package) if released_package else Path(__file__).resolve().parent/'data/original-handover.zip'
  released=release.read_bytes();assert digest(released)=='4a13951aee67e51b73405e1bce001e163f5707fbbf5998510fac84069564f368'
  with zipfile.ZipFile(io.BytesIO(released)) as delivery:
   expected={n.split('/',1)[1]:delivery.read(n) for n in delivery.namelist()}
  package={}
  for line in expected['SHA256SUMS'].decode().splitlines():
   h,n=line.split('  ',1);assert n not in package and digest(expected[n])==h;package[n]=h
  actual={n.removeprefix('handover/'):z.read(n) for n in z.namelist() if n.startswith('handover/')}
  assert set(expected)-set(actual)=={'SHA256SUMS','documentation/scientific-review/SHA256SUMS'} and all(expected[n]==v for n,v in actual.items())
  identity=json.loads(z.read('identity.json'));assert identity['package_sha256']==digest(expected['SHA256SUMS'])=='b9480155d475944d258f9bc70b6789218efa99badab3c3e9449072d4eef65a7a';checks['58_archived_handover_files_match_authenticated_released_package']=len(actual)==58
  record=json.loads(z.read('record.json'));status=json.loads(z.read('status.json'));assert record['status']==status['status']=='complete_pending_review' and status['error'] is None and not status['deferrals'];new=record['new_cases'];assert [c['case']['nodes'] for c in new]==[177,193]
  fieldmanifest=json.loads(z.read('FIELD-MANIFEST.json'))['fields'];fields={r['path']:r for r in fieldmanifest};assert len(fields)==8
  checked=0;derivatives=0;endpoints=[];changes=[];timing={k:0. for k in ['optimizer_seconds','backend_audit_seconds','metrics_seconds','checkpoint_seconds']};allcases=source['cases']+new
  for c in allcases:
   h=c['history'];assert len(h)==81 and [r['accepted_step'] for r in h]==list(range(81));assert [r['iteration'] for r in h]==list(range(545,626));assert c['final']==h[-1]
   for row in h:
    assert row['gates']==gates(row['metrics'],21);checked+=c in new
   w=window(h,71,80);prior=window(h,61,70);m=h[-1]['metrics'];e=np.array([r['metrics']['energy'] for r in h]);d=np.abs(np.diff(e))/np.abs(e[:-1]);assert np.max(np.diff(e))<=1e-12
   joint=max(w['relative_force_l2']/1e-4,w['acceleration_max']/1e-3)
   for a,b in zip(h,h[1:]):changes.append({'case':c['case']['id'],'accepted_step':b['accepted_step'],'native_iteration':b['iteration'],'utc':b['recorded_at']['utc'],'melbourne':b['recorded_at']['melbourne'],'relative_energy_change':abs(b['metrics']['energy']-a['metrics']['energy'])/abs(a['metrics']['energy'])})
   endpoints.append({'case':c['case']['id'],'nodes':c['shape'][0],'backend':c['backend']['selected'],'spacing':c['spacing'][0],'observed_utc':h[-1]['recorded_at']['utc'],'observed_melbourne':h[-1]['recorded_at']['melbourne'],'energy':m['energy'],'initial_force':h[0]['metrics']['relative_force_l2'],'force':m['relative_force_l2'],'initial_acceleration':h[0]['metrics']['acceleration_max'],'acceleration_max':m['acceleration_max'],'acceleration_component_rms':m['acceleration_rms'],'neighbour_degrees':math.degrees(m['max_neighbour_angle']),'hopf_integral':m['hopf_integral'],'hopf_relative_error':abs(abs(m['hopf_integral'])-21)/21,'tail':m['tail_fraction'],'guard':m['guard_fraction'],'window_joint':joint,'late_force_ratio':w['relative_force_l2']/prior['relative_force_l2'],'late_acceleration_ratio':w['acceleration_max']/prior['acceleration_max'],'median_relative_energy_change_final10':float(np.median(d[-10:])),'final10_below_1e_minus9':int(sum(d[-10:]<1e-9)),'readiness':h[-1]['gates']['all_readiness_gates']})
   for horizon in [30,60,80]:
    actual=window(h,horizon-9,horizon)
    for x,y in [('force','relative_force_l2'),('acceleration','acceleration_max')]:same(c['windows'][str(horizon)][x],actual[y])
   if c not in new:continue
   folder='cases/'+c['case']['id'];control=json.loads(z.read(folder+'/control.json'));ledger=json.loads(z.read(folder+'/attempt-ledger.json'));assert len(ledger)==80 and all(row['attempt']==i+1 and row['charged_before_execution'] for i,row in enumerate(ledger));assert control['history']==h and control['history_sha256']==canonical(h);assert c['backend']['selected']=='cpu'
   for row in h[1:]:
    assert row['backend_audit']['passed'] and row['backend_audit']['independent_implementation'] is False;assert row['native_restart_this_update']==(row['iteration']%200==0)
    for key in timing:timing[key]+=row['timing'][key]
   assert h[55]['alpha']==1.;best=min(h,key=lambda r:max(r['metrics']['relative_force_l2']/1e-4,r['metrics']['acceleration_max']/1e-3));assert c['best_retained']['accepted_step']==best['accepted_step'];same(c['best_retained']['score'],max(best['metrics']['relative_force_l2']/1e-4,best['metrics']['acceleration_max']/1e-3))
   for path,f in fields.items():
    if not path.startswith(folder+'/'):continue
    seal=json.loads(z.read(path[:-4]+'.seal.json'));assert seal['sha256']==f['sha256'] and seal['identity_sha256']==control['identity']
   assert c['endpoint_sha256']==fields[folder+'/endpoint.npz']['sha256']
  checks['162_CPU_observations_gates_energy_windows_restart_and_charges']=checked==162 and record['charged_optimizer_attempts']==160
  checks['eight_retained_field_seals_and_best_endpoint_lineage_match']=True
  audits=[]
  for name in z.namelist():
   if not name.startswith('field-audit/') or not name.endswith('/MEASUREMENTS.json'):continue
   d=json.loads(z.read(name));label=d['label'];m=d['metrics'];q=2 if label=='q2-reference' else 21;assert d['gates']==gates(m,q) and d['source_modified'] is False
   if label.startswith('retained-'):expected=next(c for c in source['cases'] if c['case']['id']==label.removeprefix('retained-'))['final']['metrics']
   elif label.startswith('reconstructed-initial-'):expected=init[int(label.split('-')[-1])]['metrics']
   elif label.startswith('initial-cpu-'):expected=next(c for c in new if c['case']['id']==label.removeprefix('initial-'))['history'][0]['metrics']
   elif label.startswith('final-cpu-'):expected=next(c for c in new if c['case']['id']==label.removeprefix('final-'))['final']['metrics']
   else:expected=q2['metrics']
   for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:same(m[k],expected[k])
   count=math.prod(d['shape'][:3]);e=d['energy_components'];same(e['sum'],e['nodal_sigma_e2']+e['D4_skyrme_e4']);same(e['sum'],m['energy']);same(e['continuum_inspired_virial_proxy'],(e['nodal_sigma_e2']-e['D4_skyrme_e4'])/e['sum'])
   for key in ['force','acceleration']:
    v=d[key];same(v['component_rms']*math.sqrt(3),v['vector_rms']);same(sum(a['node_fraction'] for a in v['regions'].values()),1.);same(sum(a['squared_residual_fraction'] for a in v['regions'].values()),1.)
    total=count*v['vector_rms']**2
    for a in v['regions'].values():
     same(a['node_fraction'],a['nodes']/count)
     if a['nodes']:same(a['squared_residual_fraction'],a['nodes']*a['vector_rms']**2/total)
    for threshold,value in v['above_threshold_fraction_of_whole_grid'].items():same(value,sum(a['node_fraction']*(a['above_threshold_fraction_of_region'][threshold] or 0.) for a in v['regions'].values()))
   same(d['acceleration']['maximum_vector_magnitude'],m['acceleration_max']);same(d['acceleration']['component_rms'],m['acceleration_rms'])
   for level in d['native_level_sets']:same(level['occupied_volume'],level['native_occupied_nodes']*math.prod(d['spacing']))
   a=d['acceleration'];core=a['regions']['core_neighborhood'];audits.append({'label':label,'nodes':d['shape'][0],'spacing':d['spacing'][0],'q':q,'observed_utc':d['recorded_at']['utc'],'observed_melbourne':d['recorded_at']['melbourne'],'force':m['relative_force_l2'],'acceleration_max':m['acceleration_max'],'component_rms':a['component_rms'],'vector_rms':a['vector_rms'],'core_vector_rms':core['vector_rms'],'core_node_fraction':core['node_fraction'],'core_squared_acceleration_fraction':core['squared_residual_fraction'],'core_squared_force_fraction':d['force']['regions']['core_neighborhood']['squared_residual_fraction'],'fraction_grid_acceleration_above_0p001':a['above_threshold_fraction_of_whole_grid']['0.001'],'fraction_grid_acceleration_above_0p01':a['above_threshold_fraction_of_whole_grid']['0.01'],'acceleration_p99':a['quantiles_vector_magnitude']['0.99'],'acceleration_p999':a['quantiles_vector_magnitude']['0.999'],'guard_maximum_acceleration':a['regions']['outer_guard']['maximum_vector_magnitude'],'virial_proxy':e['continuum_inspired_virial_proxy'],'n3_minus0p95_voxel_components':d['native_level_sets'][2]['six_neighbour_voxel_components'],'n3_minus0p95_volume':d['native_level_sets'][2]['occupied_volume'],'display_spacing':d['display_surfaces'][0]['display_stride']*d['spacing'][0]})
  checks['15_field_audits_scalar_replays_regional_RMS_and_energy_sums']=len(audits)==15
  for name in z.namelist():
   if not name.endswith('/DIRECTIONAL-DERIVATIVE.json'):continue
   d=json.loads(z.read(name));assert d['passed'];assert d['optimizer_attempts']==d['physical_time_steps']==0
   for row in d['rows']:
    for t in row['differences']:
     same(t['absolute_error'],abs(t['predicted']-t['centered_difference']));same(t['tolerance'],1e-7+.002*abs(t['predicted']));assert t['passed']==(t['absolute_error']<=t['tolerance']);assert t['passed'];derivatives+=1
  checks['24_directional_derivative_comparison_records_consistent']=derivatives==24
  points=[]
  for c,e in zip(allcases,endpoints):
   if c['case']['start']=='exact':continue
   w=window(c['history'],71,80);points.append({'nodes':c['shape'][0],'spacing':c['spacing'][0],'joint':e['window_joint'],'force':w['relative_force_l2'],'acceleration':w['acceleration_max']})
  fits=json.loads(z.read('UPDATED-RESPONSE-CURVES.json'));refitted={key:refits(points,key) for key in ['joint','force','acceleration']}
  for key,models in refitted.items():
   for mine,actual in zip(models,fits['fits'][key]['models']):same(mine['loo_range_nrmse'],actual['loo_range_nrmse']);same(mine['skill'],actual['loo_skill_vs_constant']);assert mine['eligible']==actual['eligible']
  author=json.loads(z.read('AUTHOR-METRICS.json'))
  for e,row in zip(endpoints,author['cases']):
   same(e['median_relative_energy_change_final10'],row['final10_relative_energy_change_median']);assert e['final10_below_1e_minus9']==row['final10_updates_below_1e_minus9'];assert row['current_readiness_pass']==e['readiness']
  checks['all_nine_refits_and_eight_author_metric_summaries_match']=True
  replayed=[r for r in bulk['rows'] if r['status']=='native_D4_replayed'];assert len(replayed)==118
  for r in replayed:assert r['gates']==gates(r['metrics'],r['q_label'])
  summary=[]
  for q in range(2,33):
   rows=[r for r in bulk['rows'] if r['q_label']==q];good=[r for r in rows if r['status']=='native_D4_replayed'];unique={(tuple(r['shape']),tuple(r['lengths']),r['array_sha256']) for r in good}
   summary.append({'q':q,'catalogued_files':len(rows),'native_D4_replayed_rows':len(good),'unique_native_geometry_field_combinations':len(unique),'deferred_rows':len(rows)-len(good),'strict_stationary_rows':sum(r['gates']['strict_stationary'] for r in good),'all_readiness_rows':sum(r['gates']['all_readiness_gates'] for r in good),'new_Q21_CPU_branches':2 if q==21 else 0,'new_Q21_CPU_readiness_passes':0,'scope':'Rows and variants, not independent Hopf-sector exclusions; old deferral scopes remain separate.'})
  checks['118_prior_bulk_gate_decisions_and_Q2_to_Q32_accounting']=True
  frozen=json.loads(z.read('TELEMETRY-FROZEN.json'));assert all(frozen['cgroup']['memory.events'][k]==0 for k in ['max','oom','oom_kill']);checks['zero_physical_time_no_recorded_hard_limit_or_OOM']=record['physical_time_steps']==0
  launch=datetime.fromisoformat(identity['recorded_at']['utc']);complete=datetime.fromisoformat(status['recorded_at']['utc']);wall=(complete-launch).total_seconds();timing['other_measurements_and_overhead_seconds']=wall-sum(timing.values());timing['launch_to_complete_seconds']=wall
  predictions=json.loads(z.read('handover/documentation/scientific-review/ANGLE-EXPLORATION.json'))['models'];angle_comparison=[]
  for c,e in zip(allcases,endpoints):
   if c not in new:continue
   pred=[]
   for model in predictions:
    value=float(np.polyval(model['coefficients_highest_power_first'],e['spacing']));value=math.exp(value) if model['model']=='exponential' else value;pred.append({'model':model['model'],'predicted_degrees':value,'measured_degrees':e['neighbour_degrees'],'error_degrees':e['neighbour_degrees']-value})
   angle_comparison.append({'nodes':e['nodes'],'prior_post_hoc_forecasts_vs_new_measurement':pred,'not_a_stationarity_prediction':True})
  scope={'static_replayed':118,'static_reader_gaps':0,'physical_time_case_checkpoints':0,'secondary_source_items':0}
  for r in bulk['rows']:
   if r['status']!='deferred':continue
   path=r['relative_home_path']
   if '/cases/' in path:scope['physical_time_case_checkpoints']+=1
   elif '20261114t120027z-36ec7e6d' in path:scope['secondary_source_items']+=1
   else:scope['static_reader_gaps']+=1
  assert scope=={'static_replayed':118,'static_reader_gaps':11,'physical_time_case_checkpoints':43,'secondary_source_items':17}
  report={'reviewed_at':stamp(),'status':'compact_review_complete_full_arrays_not_replayed_here','source_sha256':EXPECTED,'source_run':identity['run_id'],'checks':checks,'compact_payloads':len(compact),'source_payloads':len(oldhash),'handover_archived_files':len(actual),'released_handover_payloads':len(package),'omitted_nested_manifests':['SHA256SUMS','documentation/scientific-review/SHA256SUMS'],'new_CPU_observations':checked,'field_audits':len(audits),'directional_comparison_records':derivatives,'new_charged_attempts':160,'new_full_field_files':len(fields),'new_unique_field_container_hashes':len({r['sha256'] for r in fields.values()}),'new_declared_field_bytes':sum(r['bytes'] for r in fields.values()),'cases':endpoints,'field_audits_summary':audits,'refits':refitted,'prior_angle_forecasts_checked':angle_comparison,'timing_seconds':timing,'prior_bulk_scope':scope,'prior_readiness_rows':sum(r['gates']['all_readiness_gates'] for r in replayed),'prior_strict_stationary_rows':sum(r['gates']['strict_stationary'] for r in replayed),'prior_unique_charge_geometry_fields':len({(r['q_label'],tuple(r['shape']),tuple(r['lengths']),r['array_sha256']) for r in replayed}),'limits':['No full NPZ arrays are in the attached compact archives; fields, morphology and derivative values are not independently replayed here.','CPU repeats are the same implementation; finite directional derivatives are distinct recorded checks, not a complete gradient or stability proof.','Mixed CPU/CUDA optimization paths and short nonstationary horizons limit causal mesh attribution.','Display downsampling and triangle discarding can fragment surfaces; native voxel counts are separate and not knot identification.','No live GitHub operation or scientific simulation is performed here.']}
  if terminal:
   lines=Path(terminal).read_text().splitlines();receipt=next(json.loads(line) for line in lines if line.startswith('{') and 'Merged publication payloads verified' in line);assert receipt['pr']['state']=='MERGED' and receipt['pr']['number']==97 and receipt['payloads']==152
   assert EXPECTED in Path(terminal).read_text();report['publication_from_terminal']={'pr':receipt['pr'],'payloads':152,'log_sha256':digest(Path(terminal).read_bytes()),'verification_scope':'Supplied local receipt; not a live remote check'}
  (out/'INDEPENDENT-REVIEW.json').write_text(json.dumps(report,indent=2)+'\n');write_csv(out/'Q21-ENDPOINTS.csv',endpoints);write_csv(out/'FIELD-AUDIT-REVIEW.csv',audits);write_csv(out/'ENERGY-CHANGE-REVIEW.csv',changes);write_csv(out/'Q2-Q32-LEDGER.csv',summary)
  return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--terminal',type=Path);p.add_argument('--released-package',type=Path);a=p.parse_args();r=assess(a.evidence,a.output,a.terminal,a.released_package);print(json.dumps({'status':r['status'],'checks':r['checks'],'payloads':r['compact_payloads'],'new_attempts':r['new_charged_attempts']}))
