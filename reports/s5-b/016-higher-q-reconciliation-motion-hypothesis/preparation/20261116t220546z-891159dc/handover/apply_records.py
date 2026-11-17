"""Append a prepared reconciliation record, preserving existing numerical findings."""
from pathlib import Path
import os,shutil
def apply(dest,m):
 from publication import ROOT,SLUG,load,need,save,record_dir,manifest,entry,sha
 path=dest/'docs/project/roadmap.json';d=load(path)
 parent=next((s for s in d['studies'] if s['slug']=='q2-q16-closure-higher-q-review'),None);need(parent and parent['state']=='assessed','Published Q2-Q16 closure is required; merge PR77 first')
 new=next((s for s in d['studies'] if s['slug']==SLUG),None)
 if new is None:
  number=max(s['number'] for s in d['studies'] if s['stage']=='s5-b')+1
  new={'id':f's5-b-{number:03d}','stage':'s5-b','number':number,'slug':SLUG,'title':'Higher Q reconciliation and motion dependent stability hypothesis','state':'prepared','gate':'open','question':'Do retained Q22 and Q18 records establish reproduction readiness, and could genuine time dependence require a separate stability branch?','finding':'Desk assessment distinguishes Lorentz translation from internal rotation and periodic states. Original allocations remain parked. Local source reconciliation and frozen-field diagnostics are prepared; their results are pending.','next_action':'Collect pinned Q22/Q18 models, seed/endpoint records and archive references; optionally replay read-only Q2/Q8 instantaneous balance probes. Review evidence before executing the conditional Q22 cable/link pilot or a later Q18 hyperbolic case.','exit_evidence':'Pinned repository snapshot, explicit missing-field/size deferrals, unchanged gate and source identities, motion-hypothesis assessment, and a conditional benchmark-first pilot contract. Zero relaxation and physical-time steps in this tranche.','depends_on':[parent['id']],'requirements':['SCI-001','SCI-003','SCI-004','NUM-001','NUM-003','REP-001','REP-002'],'specifications':['docs/models/higher-q-reconciliation-motion-20261117.md'],'records':[]};d['studies'].append(new)
 else:need(new['state']=='prepared','Reconciliation study already advanced; preserve and reconcile')
 cfg=load(ROOT/'PLAN.json');rid=cfg['record_id'];rel=record_dir(new,rid).as_posix().replace('/assessments/','/preparation/');folder=dest/rel
 if folder.exists():need(load(folder/'record.json')['handover_sha256']==m['package_sha256'],'Existing preparation differs')
 folder.mkdir(parents=True,exist_ok=True)
 save(folder/'record.json',{'study_id':new['id'],'record_id':rid,'role':'preparation','recorded_at':m['installed_at'],'source_commit':m['base'],'outcome':'Q22/Q18 reconciliation and read-only motion hypothesis probes prepared; no new relaxation or time evolution','handover_sha256':m['package_sha256'],'input_sha256':{'legacy_neutral_dynamics':load(ROOT/'LEGACY-ENDPOINTS.json')['source_sha256'],'retained_field_anchors':sha(ROOT/'ANCHORS.json')},'limitations':['Local reconciliation results pending','Instantaneous dynamic residual is not a stability certificate','Original static and motion gates unchanged','Conditional pilot not executed by this package']})
 shutil.copytree(ROOT,folder/'handover',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 (folder/'README.md').write_text('# Higher Q reconciliation and motion hypothesis\n\n[Scientific assessment](handover/ASSESSMENT.md) · [Browser report](handover/ASSESSMENT.html) · [Frozen scope](handover/PLAN.json) · [Conditional pilot](handover/PILOT.json) · [Primary bibliography](handover/BIBLIOGRAPHY.md) · [Local execution](handover/README.md)\n\nPreparation only. Local metadata collection and frozen-field acceleration probes require assessment. No numerical relaxation, new model potential, physical-time evolution or gate relaxation is prepared here.\n')
 manifest(folder)
 e={'role':'preparation','path':rel+'/README.md','label':'Pinned source reconciliation, motion hypothesis assessment and zero-evolution diagnostic plan'}
 if not any(x['path']==e['path'] for x in new['records']):new['records'].append(e)
 spec=dest/new['specifications'][0];spec.parent.mkdir(parents=True,exist_ok=True);link=Path(os.path.relpath(folder/'handover/ASSESSMENT.md',spec.parent)).as_posix();plan=Path(os.path.relpath(folder/'handover/PLAN.json',spec.parent)).as_posix()
 spec.write_text('# Higher Q reconciliation and motion hypothesis scope\n\n'+f'[Assessment and model distinctions]({link}) · [Frozen read-only scope]({plan})\n\nReconcile existing Q22/Q18 seed families, energy/action normalization, old-cell versus D4 admission, full-field provenance and archive availability before new relaxation. Analyze uniform translation separately from internal rotation, spatial rotation and genuinely periodic states. Frozen-field velocity probes do not authorize dynamic stability claims. Q17-Q32 broad work remains deferred.\n')
 priority=d.get('priority',[])
 if new['id'] not in priority:priority=[new['id'] if x==parent['id'] else x for x in priority] if parent['id'] in priority else priority+[new['id']]
 d['priority']=priority;d['updated_at']=m['installed_at'];save(path,d);m.update(assessment_path=rel,study_id=new['id']);return m
