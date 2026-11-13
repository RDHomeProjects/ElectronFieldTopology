"""Read-only SF dependency grouping; never replaces old scientific gates."""
import hashlib,json,zipfile,html
from pathlib import Path
from collections import defaultdict,Counter
from .common import stamp,save,digest

def audit(evidence,output):
 with zipfile.ZipFile(evidence) as z:
  if z.testzip() is not None:raise ValueError('SF compact evidence CRC failure')
  campaign=json.loads(z.read('campaign.json'))
 cases=campaign['cases'];cases=list(cases.values()) if isinstance(cases,dict) else cases
 groups=defaultdict(list);rejected=[]
 for c in cases:
  physics=c.get('physical');admission=c.get('admission',{});assess=c.get('assessment',{}).get('legacy_motion',{})
  if not physics or not admission.get('passed') or not assess:
   rejected.append({'id':c['id'],'q':c.get('q'),'status':c.get('status'),'reason':'No admitted trajectory/compatible motion metric; original outcome retained'});continue
  initial=c.get('initial_state_sha256')
  if not initial:rejected.append({'id':c['id'],'reason':'Missing initial-state identity'});continue
  # Match a physical endpoint and initial field. Diagnostic cadence in model
  # units is fixed, even when integer step counters change with dt.
  fixed={'q':c['q'],'rest_id':c['rest_id'],'initial_state_sha256':initial,'beta':c['beta'],'axis':c['axis'],'grid':physics['grid'],'lengths':physics['lengths'],'boundary':physics['boundary'],'measurement_time':assess['time'],'diagnostic_model_interval':round(physics['diagnostic_every']*c['dt'],14),'source_sha256':campaign['source_sha256']}
  key=json.dumps(fixed,sort_keys=True);groups[key].append({'case_id':c['id'],'dt':c['dt'],'speed_error':assess.get('speed_relative_error'),'shape_error':assess.get('translated_static_field_relative_l2'),'status':c['status'],'original_checks':assess.get('checks',{})})
 outgroups=[]
 for key,rows in groups.items():
  unique=sorted(set(v['dt'] for v in rows));fixed=json.loads(key)
  # Retrospectively inspected points cannot be called fresh withheld points.
  outgroups.append({'fixed':fixed,'active_variable':'dt','rows':sorted(rows,key=lambda v:v['dt']),'distinct_levels':len(unique),'dependency_status':'descriptive_only' if len(unique)>=2 else 'insufficient_levels','validated_fit':False,'reason':'Existing points have been reviewed; no fresh reserved validation, and at least six to seven controlled levels are needed for competing-curve validation.'})
 report={'recorded_at':stamp(),'source_evidence_sha256':digest(evidence),'source_run':campaign['record_id'],'source_commit':campaign['source_commit'],'case_count':len(cases),'original_status_counts':dict(Counter(c.get('status') for c in cases)),'temporal_groups':outgroups,'admission_exclusions':rejected,'rest_statuses':{k:v.get('status') for k,v in campaign['rest'].items()},'scope':'Read-only application of matching, provenance and identifiability rules to existing Qx results. No new physical time step, admission decision, changed gate or certified fit. Q1 parked; Q2 reference; Q3 controlled temporal and mesh measurements need their own study; Q4/Q7 preparation/admission exclusions retained.'}
 output=Path(output);output.mkdir(parents=True,exist_ok=True);save(output/'qx-audit.json',report)
 rows=''.join('<tr><td>'+str(g['fixed']['q'])+'</td><td>'+html.escape(g['fixed']['rest_id'])+'</td><td>'+str(g['fixed']['axis'])+'</td><td>'+str(g['distinct_levels'])+'</td><td>'+g['dependency_status']+'</td></tr>' for g in outgroups)
 (output/'QX-REPORT.html').write_text('<!doctype html><meta charset="utf-8"><title>Qx dependency transfer</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:30px auto}td,th{padding:8px;border-bottom:1px solid #ddd}</style><h1>Qx dependency transfer: existing evidence audit</h1><p>'+html.escape(json.dumps(report['recorded_at']))+'</p><p>'+html.escape(report['scope'])+'</p><table><tr><th>Q</th><th>Rest</th><th>Axis</th><th>dt levels</th><th>Dependency status</th></tr>'+rows+'</table><p>Grouping matches field identity, grid, box, velocity, direction, endpoint and physical diagnostic cadence. Fresh/warm rest states are not pooled into one spacing curve. Different directions and domains remain separate. Original failed motion gates are retained rather than filtered out. Rejected admissions do not enter motion fits.</p><p>Next measurement order: Q2 reference qualification, then one Q3 temporal variable with fresh validation, then spacing with a fixed physical observer and fixed dt. A Maxwell error fit cannot certify the nonlinear SF equation. Additional Q4/Q7 motion requires its original rest/admission gates first.</p>')
 return report
