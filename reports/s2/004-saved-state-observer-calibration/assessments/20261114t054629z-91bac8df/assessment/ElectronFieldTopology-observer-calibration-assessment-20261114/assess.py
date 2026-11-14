"""Independent compact calibration audit; no raw state replay or GitHub access."""
import argparse,collections,csv,hashlib,html,json,math,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--evidence-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
root=args.evidence_dir.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
KEYS=['evolution_observed_error','observer_baseline_error','total_observed_error']
def delta(a,b):return max(abs(a[k]-b[k]) for k in KEYS)
def predict(m,x):
 z=(x-m['origin'])/m['scale'];c=m['coefficients']
 return math.exp(max(-700,min(700,c[0]+c[1]*z))) if m['model']=='exponential' else float(np.polynomial.polynomial.polyval(z,c))
assert sha(args.archive)=='04cd1d5d7ffc79cef09dcd5c77dfd27008e8760f843f5d3a420b20a62034419d'
with zipfile.ZipFile(args.archive) as z:
 assert z.testzip() is None and len(z.infolist())==209
 names=z.namelist();assert len(set(names))==len(names) and all((root/n).resolve().is_relative_to(root) for n in names)
hashed=set()
for line in (root/'SHA256SUMS').read_text().splitlines():
 h,n=line.split('  ',1);assert n not in hashed and sha(root/n)==h;hashed.add(n)
assert hashed==set(names)-{'SHA256SUMS'}
r=load(root/'record.json');budget=r['config']['measurement_error_budget'];assert budget==1e-6 and len(r['anchors'])==6
assert r['identity']==load(root/'identity.json') and r['recorded_at']==load(root/'started.json')['recorded_at']
for n,h in r['identity']['code_sha256'].items():assert sha(root/'code'/n)==h
measurements={v.stem:load(v) for v in (root/'measurements').glob('*.json')}
for n,v in measurements.items():
 assert (root/'measurements'/(n+'.sha256')).read_text().strip()==sha(root/'measurements'/(n+'.json'))
 closure=abs(v[KEYS[2]]**2-v[KEYS[0]]**2-v[KEYS[1]]**2-v['normalized_cross_term']);assert closure<1e-15
table=[];metric_rows=[];prediction_rows=[];audit=[]
for a in r['anchors']:
 cid=a['case_id'];assert load(root/'anchors'/(cid+'.json'))==a
 def measurement(v):
  label='gauss'+str(v['order']) if v['order'] else v['method']+str(v['observer_nodes'])
  assert measurements[cid+'-'+label]==v
 for v in a['development']+a['validation']+a['gauss_refinement']+[a['midpoint_control']]:measurement(v)
 dev=a['development'];vals=a['validation'];gauss=a['gauss_refinement'];ref=gauss[-1];assert ref==a['reference']
 rp=delta(gauss[-1],gauss[-2])<=budget;assert rp==a['reference_empirical_pass']
 assert delta(dev[0],ref)==a['original_33_max_difference_from_reference'] and delta(dev[-1],ref)==a['final_uniform_max_difference_from_reference']
 assert not {v['observer_nodes'] for v in dev}&{v['observer_nodes'] for v in vals}
 assert [v['observer_nodes'] for v in vals]==r['config']['validation_observer_nodes']
 frozen=load(root/'frozen'/(cid+'.json'));assert frozen['frozen_at']==a['frozen_at'] and frozen['payload']['development_counts']==[v['observer_nodes'] for v in dev]
 for response,data in a['models'].items():
  fm=frozen['payload']['models'][response];assert fm['development']==data['development']
  assert data['development']==[{'x':1/(v['observer_nodes']-1),'y':v[response]} for v in dev]
  for frozen_model,model in zip(fm['models'],data['models']):
   assert all(model[k]==v for k,v in frozen_model.items())
   residual=[predict(model,1/(v['observer_nodes']-1))-v[response] for v in vals]
   assert np.allclose(residual,model['validation_residuals'],rtol=1e-9,atol=1e-16)
   assert math.isclose(max(map(abs,residual)),model['validation_max_abs_error'],rel_tol=1e-9,abs_tol=1e-16)
  primary=data['models'][0];prediction_rows.append({'field':a['parameters']['field'],'native_nodes':a['parameters']['nodes'],'response':response,'model':primary['model'],'max_residual_fraction':primary['validation_max_abs_error'],'pass':primary['validation_max_abs_error']<=budget})
 assert all(v['measured_at']['utc']>a['frozen_at']['utc'] for v in vals)
 assert max(v['models'][0]['validation_max_abs_error'] for v in a['models'].values())==a['fresh_prediction_max_error']
 assert (a['fresh_prediction_max_error']<=budget)==a['fresh_prediction_pass']
 consecutive=0
 for i,selection in enumerate(a['adaptive_selections']):
  previous=dev[len(r['config']['seed_observer_nodes'])+i-1];nextrow=dev[len(r['config']['seed_observer_nodes'])+i]
  choice=load(root/'choices'/f'{cid}-{i:02d}.json');assert choice['selected_at']==selection['selected_at']
  assert all(selection[k]==v for k,v in choice['selection'].items())
  assert nextrow['observer_nodes']==selection['observer_nodes'] and selection['selected_at']['utc']<nextrow['measured_at']['utc']
  good=delta(nextrow,previous)<=budget and delta(nextrow,ref)<=budget and rp
  consecutive=consecutive+1 if good else 0;assert good==selection['qualifying'] and consecutive==selection['successive_qualifying']
 uniform=bool(rp and consecutive>=2 and delta(a['midpoint_control'],ref)<=budget and delta(dev[-1],ref)<=budget)
 assert uniform==a['uniform_observer_pass']
 for key in KEYS:
  old=dev[0][key];new=ref[key];diff=new-old;order_change=abs(gauss[-1][key]-gauss[-2][key])
  metric_rows.append({'field':a['parameters']['field'],'native_nodes':a['parameters']['nodes'],'response':key,'old_33_fraction':old,'cell_gauss4_fraction':new,'change_fraction':diff,'change_percentage_points':100*diff,'change_relative_percent':100*diff/old,'gauss3_to4_fraction':order_change,'final_uniform_difference_fraction':abs(dev[-1][key]-new),'midpoint_difference_fraction':abs(a['midpoint_control'][key]-new)})
 table.append({'field':a['parameters']['field'],'native_nodes':a['parameters']['nodes'],'cell_reference_pass':rp,'uniform_pass':uniform,'prediction_pass':a['fresh_prediction_pass'],'gauss3_to4_max_fraction':delta(gauss[-1],gauss[-2]),'original33_max_fraction':delta(dev[0],ref),'final_observer_nodes':dev[-1]['observer_nodes'],'final_uniform_max_fraction':delta(dev[-1],ref),'midpoint_max_fraction':delta(a['midpoint_control'],ref),'primary_evolution_prediction_pass':a['models'][KEYS[0]]['models'][0]['validation_max_abs_error']<=budget})
 audit.append({'case_id':cid,'anchor_and_measurement_receipts_match':True,'selection_precedes_measurement':True,'frozen_coefficients_match':True,'validation_disjoint_and_after_freeze':True,'all_candidate_residuals_recomputed':True,'consecutive_rule_and_status_recomputed':True})
for filename,rows in [('anchor-summary.csv',table),('metric-shifts.csv',metric_rows),('prediction-summary.csv',prediction_rows)]:
 with (out/filename).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
dt=lambda s:datetime.fromisoformat(s)
t=datetime.now(timezone.utc);stamp={'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
summary={'assessment_at':stamp,'input_sha256':sha(args.archive),'source_record_id':r['source_record_id'],'recorded_source_commit':r['environment']['source_commit'],'execution_started':r['recorded_at'],'execution_finished':r['finished_at'],'wall_seconds':(dt(r['finished_at']['utc'])-dt(r['recorded_at']['utc'])).total_seconds(),'zip_members':209,'compact_hashes_verified':len(hashed),'measurements':len(measurements),'gauss_evaluations':sum(len(a['gauss_refinement']) for a in r['anchors']),'development_evaluations':sum(len(a['development']) for a in r['anchors']),'validation_evaluations':sum(len(a['validation']) for a in r['anchors']),'midpoint_evaluations':6,'cell_reference_passes':sum(v['cell_reference_pass'] for v in table),'uniform_passes':sum(v['uniform_pass'] for v in table),'all_response_prediction_passes':sum(v['prediction_pass'] for v in table),'evolution_prediction_passes':sum(v['primary_evolution_prediction_pass'] for v in table),'anchor_results':table,'audit':audit,'scope':'Compact payload, chronology, scalar identities and residual replay; full NPZ arrays absent. No independent physical-field replay or live GitHub verification. Cell references are empirical quadrature checks, not rigorous bounds.','disposition':'Useful calibration diagnosis; not an all-pass instrument qualification. Prefer targeted cell-aware quadrature confirmation and all-mesh saved-state remeasurement over another broad physical campaign.'}
save(out/'assessment.json',summary)
print(json.dumps(summary,indent=2))
