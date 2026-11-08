"""Recompute compact temporal-study scalars, provenance, original gates and audit facts."""
import argparse,csv,hashlib,io,json,math,statistics,zipfile
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
RUN='20261106t212927z-589f5f5d';SOURCE='422bbcf59810938d26437f7dce9f6be83e3fb1a8';EVIDENCE='9c57be7d19ef234e16f05fee517a8146ae71c5de20edb53d5dcb4fdec0f861d1'
def stamp():
 t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,message):
 if not ok:raise ValueError(message)
def close(a,b,rel=1e-8,abs=1e-12):need(math.isclose(a,b,rel_tol=rel,abs_tol=abs),f'Numeric replay differs: {a} != {b}')
def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def audit_old(repo,actual):
 path=repo/'reports/s5-b/009-q1-tail-settling/runs/20261105t212644z-103ef9f4/evidence.zip'
 with zipfile.ZipFile(path) as z:
  old=json.loads(z.read('campaign.json'));policy=json.loads(z.read('plan.json'));rows=[]
  for k,r in old['cases'].items():
   m=r['final']['stationarity'];p=policy['readmission'];endpoint=m['relative_force_l2']<=p['relative_force_l2'] and m['acceleration_max']<=p['acceleration_max'] and abs(abs(m['hopf_integral'])-1)<=p['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<1e-10
   obs=json.loads(z.read('readmission/'+k+'/observations.json'));regular=[x for x in obs if x['regular_observation']];last=regular[-policy['stable_intervals']-1:]
   stable=len(last)==policy['stable_intervals']+1 and all(b['iteration']-a['iteration']==policy['observe_every'] and all(b[field]<=policy[field] for field in ['tail_fraction_change','shell_energy_change','core_field_relative_change','hamiltonian_relative_change']) for a,b in zip(last,last[1:]))
   got={'case_id':k,'strict_endpoint_stationarity_pass':endpoint,'preceding_regular_window_stable':stable,'final_observation_regular':obs[-1]['regular_observation'],'historical_regular_certificate_pass':bool(endpoint and stable and obs[-1]['regular_observation']),'native_status_preserved':r['status'],'native_reason_preserved':r['result']['reason']}
   expected=next(x for x in actual if x['case_id']==k)
   need(all(expected[x]==v for x,v in got.items()),'Historical endpoint/window audit differs');rows.append(got)
 return rows

def verify(evidence,repo,summary=None):
 repo=Path(repo);need(sha(evidence)==EVIDENCE,'Unexpected compact evidence ZIP')
 with zipfile.ZipFile(evidence) as z:
  names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Duplicate or corrupt compact member')
  need(all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names),'Unsafe ZIP path')
  hashes=json.loads(z.read('evidence-hashes.json'))['sha256'];need(set(names)==set(hashes)|{'evidence-hashes.json'},'Incomplete compact member ledger')
  for n,h in hashes.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Compact member differs: '+n)
  if summary:need(Path(summary).read_bytes()==z.read('SUMMARY.md'),'Uploaded summary differs')
  c=json.loads(z.read('campaign.json'));p=json.loads(z.read('plan.json'));audit=json.loads(z.read('audit.json'));pairs=json.loads(z.read('temporal-comparisons.json'))
  need(c['record_id']==RUN and c['source_commit']==SOURCE and c['status']=='complete_pending_review','Run/source/status differs')
  need(canonical(p)==c['config_sha256'] and not c['source_worktree_dirty'],'Config/Git provenance differs')
  for n,h in c['source_sha256'].items():need(sha(repo/'src/electron_field_topology'/n)==h,'Numerical source differs: '+n)
  original=json.loads((repo/'experiments/configs/sf-motion/lowq-motion.json').read_text())['limits'];need(p['limits']==original and original['tail_fraction']==.001,'Original limits differ')
  need(p['time_steps']==[.01,.005,.0025] and p['duration']==1 and p['beta']==.3 and p['spacing']==.16,'Declared matrix differs')
  need(c['selected_domains']=={'q1-x':'q1-x-n153-L24.32','q2-z':'q2-z-n127-L20.16'} and len(c['domains'])==2 and len(c['cases'])==6,'Coverage/fallback selection differs')
  need(audit['passed'] and audit['geodesic_control']['passed'] and audit['fixed_layer_control']['passed'],'Independent controls not passed')
  historical=audit_old(repo,audit['historical_endpoint_audit']);rows=[];failures={k:0 for k in ['energy','momentum','constraints','shape','speed','topology','tail']};observations=0
  for model in p['models']:
   domain=c['domains'][c['selected_domains'][model['id']]];adm=domain['admission'];m=domain['rest_final']['stationarity'];policy=p['readmission'];q=model['q']
   need(domain['status']=='admitted' and domain['family_status']=='accepted' and domain['rest_result']['status']=='stationary','Rest/family state differs')
   need(m['relative_force_l2']<=policy['relative_force_l2'] and m['acceleration_max']<=policy['acceleration_max'] and abs(abs(m['hopf_integral'])-q)/q<=policy['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<1e-10,'Rest admission fails original declared policy')
   for name,limit in [('initial_tail',p['initial_tail_reserve']),('expanded_guard',p['expanded_guard_limit']),('predicted_coasting_final_tail',p['initial_tail_reserve'])]:
    a=adm[name];close(a['energy']/a['total_continuum_energy'],a['fraction']);need(a['fraction']<=limit,'Boundary reserve failed')
   family=[r for r in c['cases'].values() if r['model']==model['id']];need(len(family)==3 and len({r['initial_state_sha256'] for r in family})==1,'Initial full states differ between time steps')
   for r in family:
    key=r['id'];a=r['assessment'];native=a['legacy_motion'];h=json.loads(z.read('cases/'+key+'/history-combined.json'));observations+=len(h);dt=r['dt']
    need(r['status']=='complete' and r['final_time']==1 and len(r['attempts'])==1 and len(h)==21,'Case/sampling/restart coverage differs')
    need(all(abs(x['time']-.05*i)<1e-12 and x['step']==round(x['time']/dt) for i,x in enumerate(h)),'Physical observation times differ')
    need(json.loads(z.read('cases/'+key+'/assessment.json'))==r,'Per-case record differs')
    x=np.asarray([x['time'] for x in h]);cent=np.asarray([x['centroid'] for x in h]);xx=x-x.mean();velocity=np.sum(xx[:,None]*(cent-cent.mean(axis=0)),axis=0)/np.sum(xx*xx)
    target=np.zeros(3);target[model['axis']]=p['beta'];speed=float(np.sqrt(np.sum((velocity-target)**2))/p['beta']);close(speed,native['speed_relative_error'])
    for x,y in zip(velocity,native['fitted_centroid_velocity']):close(float(x),y)
    energy=max(abs(x['energy']-h[0]['energy'])/abs(h[0]['energy']) for x in h);momentum=max(float(np.sqrt(np.sum((np.asarray(x['momentum'])-h[0]['momentum'])**2)))/abs(h[0]['energy']) for x in h)
    close(energy,native['max_energy_relative_drift']);close(momentum,native['max_momentum_drift_over_initial_energy'])
    tails=[]
    for x in h:
     b=x['boundary_tail'];close(b['energy']/b['total_continuum_energy'],b['fraction']);tails.append(b['fraction']);need(x['original_tail_pass']==(b['fraction']<=.001) and x['tail_warning_clear']==(b['fraction']<=.0009),'Tail flag differs')
    close(max(tails),a['max_observed_tail_fraction']);need(a['original_tail_pass_at_all_recorded_times']==all(x['original_tail_pass'] for x in h) and a['boundary_reserve_clear_at_all_recorded_times']==all(x['tail_warning_clear'] for x in h),'Historical tail/reserve summary differs')
    final=native['final'];checks={'energy':energy<=original['energy_relative'],'momentum':momentum<=original['momentum_scaled'],'constraints':max(max(x['unit_error'],x['tangency_error']) for x in h)<1e-10,'shape':native['translated_static_field_relative_l2']<=original['shape_relative'],'speed':speed<=original['speed_relative'],'topology':abs(abs(final['hopf_integral'])-q)/q<=original['charge_relative_error'] and final['minimum_corner_cone']>0,'tail':final['boundary_shell_energy_fraction']<=original['tail_fraction']}
    need(checks==native['checks'] and all(checks.values())==native['bounded_case_gates_pass'],'Original case gate differs')
    for k,v in checks.items():failures[k]+=not v
    rows.append({'case_id':key,'model':model['id'],'dt':dt,'fitted_speed':float(velocity[model['axis']]),'speed_relative_error':speed,'legacy_shape_relative_l2':native['translated_static_field_relative_l2'],'cubic_reference_relative_l2':a['projected_cubic_coast_reference']['raw_relative_l2'],'fixed_comoving_relative_l2':a['own_admitted_comoving']['comparison']['raw_relative_l2'],'maximum_observed_tail_fraction':max(tails),'final_tail_fraction':final['boundary_shell_energy_fraction'],'energy_drift':energy,'momentum_drift':momentum,'first_interval_speed':float((cent[1,model['axis']]-cent[0,model['axis']])/.05),'initial_flux_over_continuum_energy':h[0]['momentum'][model['axis']]/h[0]['continuum_energy'],'checks':checks})
  need(len(pairs['rows'])==8,'Temporal comparison coverage differs');orders=[]
  for x in pairs['rows']:
   need(x['time'] in [.25,.5,.75,1.] and x['common_nodes']==73,'Comparison grid/time differs')
   for key,field in [('field_order','field_relative_l2'),('rate_order','rate_relative_l2')]:
    a=x['coarse_medium'][field];b=x['medium_fine'][field];order=None if min(a,b)<=1e-12 else math.log2(a/b)
    if order is None:need(x[key]['order'] is None,'Below-floor order was asserted')
    else:close(order,x[key]['order']);orders.append(order)
  inv=json.loads(z.read('inventory.json'));need(inv['input_fingerprint']==c['input_fingerprint'],'Input identity differs')
  csvrows=list(csv.DictReader(io.StringIO(z.read('case-metrics.csv').decode())));need(len(csvrows)==6 and b'\r\n' not in z.read('case-metrics.csv'),'CSV row count/line endings differ')
  by_id={x['case_id']:x for x in rows}
  for row in csvrows:
   r=by_id[row['case_id']]
   for column,target_key in [('maximum_observed_tail_fraction','maximum_observed_tail_fraction'),('speed_relative_error','speed_relative_error'),('energy_drift','energy_drift'),('momentum_drift','momentum_drift'),('legacy_shape_relative_l2','legacy_shape_relative_l2')]:close(float(row[column]),r[target_key])
  return {'verified_at':stamp(),'run_id':RUN,'source_commit':SOURCE,'evidence_sha256':EVIDENCE,'archive_members':len(names),'hashed_members':len(hashes),'source_files_checked':len(c['source_sha256']),'cases':rows,'case_count':6,'tail_observations_replayed':observations,'tail_failures':sum(not x['checks']['tail'] for x in rows),'original_failures':failures,'bounded_case_passes':sum(all(x['checks'].values()) for x in rows),'temporal_rows':pairs['rows'],'nonnull_orders':len(orders),'order_range':[min(orders),max(orders)],'historical_endpoint_audit':historical,'controls':{'geodesic_orders':audit['geodesic_control']['orders'],'fixed_layer_controls_passed':True},'disposition':'tail_mitigation_and_fixed_grid_temporal_refinement_supported; Q1_speed_failure_retained; physical_mesh_and_domain_checks_next','full_field_replay':'separate replay_fields.py output required','scope':'Hash/provenance and recorded scalar/controller replay; no new trajectory or threshold change'}
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--repo',type=Path,required=True);a.add_argument('--summary',type=Path);a.add_argument('--output',type=Path,required=True);x=a.parse_args();r=verify(x.evidence,x.repo,x.summary);x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps({k:r[k] for k in ['verified_at','archive_members','hashed_members','tail_observations_replayed','original_failures','disposition']},indent=2))
