"""Author-specific comparisons; no published error estimate becomes a new gate."""
import csv,io,html,statistics,math
from pathlib import Path
from criteria_common import ROOT,load,save,stamp,source_record

def write_csv(path,rows):
 buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows);Path(path).write_text(buf.getvalue())
def trailing_true(values):
 count=0
 for v in reversed(values):
  if not v:break
  count+=1
 return count

def compare_case(case):
 h=case['history'];drops=[]
 for left,right in zip(h,h[1:]):
  e0,e1=left['metrics']['energy'],right['metrics']['energy'];d=abs(e1-e0)/max(abs(e0),1e-30)
  drops.append({'case':case['case']['id'],'accepted_update':right['accepted_step'],'native_iteration':right['iteration'],'utc':right['recorded_at']['utc'],'melbourne':right['recorded_at']['melbourne'],'energy':e1,'relative_energy_change':d,'energy_nonincreasing':e1<=e0+1e-12,'below_1e_minus7':d<1e-7,'below_1e_minus9':d<1e-9})
 m=h[-1]['metrics'];tail=drops[-10:];window=h[-10:];joint=max(statistics.median(r['metrics']['relative_force_l2'] for r in window)/1e-4,statistics.median(r['metrics']['acceleration_max'] for r in window)/1e-3)
 row={'case':case['case']['id'],'nodes':case['shape'][0],'backend':case['backend']['selected'],'accepted_updates':h[-1]['accepted_step'],'native_iteration':h[-1]['iteration'],'observed_utc':h[-1]['recorded_at']['utc'],'observed_melbourne':h[-1]['recorded_at']['melbourne'],'relative_force':m['relative_force_l2'],'maximum_acceleration':m['acceleration_max'],'component_acceleration_rms':m['acceleration_rms'],'maximum_neighbour_degrees':math.degrees(m['max_neighbour_angle']),'literature_30_degree_sampling_warning':math.degrees(m['max_neighbour_angle'])>30,'original_force_le_1e_minus3':m['relative_force_l2']<=1e-3,'original_acceleration_le_1e_minus2':m['acceleration_max']<=1e-2,'current_readiness_pass':h[-1]['gates']['all_readiness_gates'],'energy_change_window_count':len(tail),'final10_relative_energy_change_median':statistics.median(r['relative_energy_change'] for r in tail) if tail else None,'final10_updates_below_1e_minus7':sum(r['below_1e_minus7'] for r in tail),'final10_updates_below_1e_minus9':sum(r['below_1e_minus9'] for r in tail),'trailing_updates_below_1e_minus9':trailing_true([r['below_1e_minus9'] for r in drops]),'median_window_joint_score':joint,'final_energy':m['energy']}
 return row,drops

def assess(output,new_cases=(),runtime=None):
 output=Path(output);output.mkdir(parents=True,exist_ok=True);source=source_record();cases=source['cases']+list(new_cases);rows=[];drops=[]
 for c in cases:
  row,d=compare_case(c);rows.append(row);drops+=d
 baseline=next(r['final_energy'] for r in rows if r['case']=='mesh-129')
 for row in rows:
  row['energy_relative_difference_from_129_reset']=abs(row['final_energy']-baseline)/abs(baseline)
  row['within_Sutcliffe_relative_energy_accuracy_0p1_percent_band']=row['energy_relative_difference_from_129_reset']<=.001
  row['Sutcliffe_band_is_a_project_gate']=False
 report={'recorded_at':stamp(),'source_run':load(ROOT/'PLAN.json')['source_run'],'status':'author_metric_comparison_not_a_literature_reproduction_certificate','cases':rows,'method_assessments':[
  {'author':'Hietarinta and Salo (2000)','source':'https://users.aalto.fi/~ala/pdf/081201R.pdf','location':'PDF page 2, numerical methods; pages 3–4, terraces and finite-box/discretization checks','applied':'Per-accepted-update relative energy changes at 1e-7 and 1e-9; persistence counts; neighbour-angle warning at 30 degrees. These reproduce a reported measure, not the original optimizer or stopping implementation.','known_state_energy_relative_tolerance':.0025,'known_state_match_assessment':'not_assessed_no_authenticated_same_configuration','not_completed':'No perturbation-and-return experiment, independent same-state literature identification, or fixed-spacing domain comparison is performed. Nonstationary Q21 endpoints cannot establish local-minimum stability from a return claim.','verdict':'Energy-only diagnostic evaluated; full published convergence/stability procedure not reproduced.'},
  {'author':'Sutcliffe (2007)','source':'https://arxiv.org/pdf/0705.1468','location':'Numerical methods, PDF page 4','applied':'Registered fixed-box energy and geometric comparisons; literature approximately 0.1% relative-energy accuracy shown only as context. Additional native residual/morphology diagnostics are supplied by the workstation supplement.','not_completed':'Approximately 1% absolute bias and 0.1% relative-energy accuracy are reported estimates, not stopping thresholds. The paper studies Q through 16; it has no Q21 target field. No matching absolute-energy target is inferred.','verdict':'Refinement consistency assessed on unresolved endpoints; stationary continuum convergence and reproduction remain unestablished.'},
  {'author':'Jennings (2015)','source':'https://arxiv.org/pdf/1412.8597','location':'Section 4, numerical methods, PDF pages 9–10','applied':'Report actual grid spacing against the published 301^3, spacing 0.06 setup; export display-only n3=-0.95 surfaces and compare measured energies and residuals across our grids.','not_completed':'The methods description supplies no equivalent normalized-force/maximum-acceleration cutoff. Knot/link preimage correspondence and identical-state energy comparison are not established; no published-stability pass is invented.','verdict':'Method-informed diagnostics applied; exact published basin, spatial accuracy and local-minimum reproduction remain unverified.'}],
 'project_threshold_provenance':{'document':'documentation/SF-tail-domain-screening.md.txt','date':'2026-11-05','older':{'force':.001,'acceleration':.01},'current':{'force':.0001,'acceleration':.001},'purpose':'Tighter preparation to distinguish domain effects from incomplete relaxation','literature_equivalent_derivation_found':False,'physical_duration_error_calibration_established':False},'physical_time_steps':0,'new_optimizer_attempt_ceiling':160,'runtime':runtime,'interpretation':'All old gate results remain visible. Energy stagnation is distinct from stationarity; stationarity is distinct from perturbation stability. Display surfaces are not knot invariants. No alternative gate is substituted.'}
 save(output/'AUTHOR-METRICS.json',report);write_csv(output/'AUTHOR-METRICS.csv',rows);write_csv(output/'ENERGY-CHANGE-PER-UPDATE.csv',drops)
 table='\n'.join('| '+r['case']+' | '+str(r['backend'])+' | '+str(r['accepted_updates'])+' | '+f"{r['relative_force']:.6g}"+' | '+f"{r['maximum_acceleration']:.6g}"+' | '+f"{r['final10_relative_energy_change_median']:.3g}"+' | '+str(r['final10_updates_below_1e_minus9'])+'/'+str(r['energy_change_window_count'])+' |' for r in rows)
 authors='\n\n'.join('### '+a['author']+'\n\nSource: '+a['source']+' ('+a['location']+').\n\nApplied: '+a['applied']+'\n\nLimit: '+a['not_completed']+'\n\nAssessment: **'+a['verdict']+'**' for a in report['method_assessments'])
 text='''# Q21 measurement criteria, completed results and CPU resolution supplement

Review timestamps: UTC '''+report['recorded_at']['utc']+'; Australia/Melbourne '+report['recorded_at']['melbourne']+'''.

The original run completed with 480 updates and no new stationary Q21 field. The current force 1e-4 and maximum-acceleration 1e-3 limits are project preparation targets, tightened tenfold in S5-B-008. Their equivalence to the papers' criteria has not been established. They remain unchanged in both new CPU branches.

The comparison below separates each author's actual measure from project admission. A threshold is not invented where a paper reports only an accuracy estimate. Known-state recognition, perturbation/return and spatial convergence remain separate from a small energy change.

| Case | Backend | Updates | Final force | Final max acceleration | Median relative energy change, last 10 | Updates below 1e-9, last 10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
'''+table+'\n\n'+authors+'''

## Supplementary measurement and execution scope

The new executable plan measures all six retained Q21 endpoints, reconstructs the four original refined initial fields from the authenticated iteration-545 parent, and runs separate 177^3 and 193^3 CPU-float64 branches. Each new branch has at most 80 charged attempts, a 160-attempt total ceiling, the same box 30.72, shift 0.25, source alpha, native restart schedule and original gates. New branches reset conjugacy like the original resolution arms. No completed branch is transferred or overwritten. The first attempt after native iteration 599 triggers the same scheduled native restart at 600.

The CPU branches and existing endpoints are not compared as bit-identical backend trajectories. The unchanged D4 action and independent directional-derivative checks qualify the arithmetic; CPU repeat evaluations are explicitly not called independent implementations. No GPU package or device is needed for the new work.

Read-only field outputs include core/guard residual distributions, maxima, vector RMS and component RMS, energy components and a labelled continuum-inspired virial proxy. That proxy is not an exact fixed-lattice scaling derivative or a new admission gate. Images use authors' n3 isosurface levels as display conventions; neither connected-component counts nor pictures identify a knot or prove stability. Original field bytes are hashed before and after reading. Missing supplementary inputs remain explicit deferrals; changed hashes are faults.

The original 177^3 and 193^3 deferrals arose because auto pinned CUDA across grids, with no per-grid CPU fallback. The new explicit CPU branches repair coverage without relabelling the original deferrals. CPU resource qualification is repeated for each geometry. Memory pressure or an unqualified geometry pauses or defers work; no scientific threshold or host reserve is lowered.

## Interpretation and next decision

A relative-energy-change threshold is optimizer-step dependent. Flat energy can coexist with a nonzero core residual. The original refined endpoints have last-ten median changes around 1.7e-7 to 2.1e-7 and no final-ten update below 1e-9; they do not gain a Hietarinta–Salo convergence certificate. Some paper-inspired measurements are available now, while full-field and new-grid outcomes are added only after actual workstation execution.

Supplementary morphology, residual localization and CPU-grid outcomes should decide whether to continue, change an optimizer in a separately registered comparison, or investigate finite-box effects. A future duration-specific rest-evolution calibration may test whether the project preparation limits are unnecessarily restrictive. This handover performs no physical-time evolution, no perturbation-and-return relaxation, no model change and no blanket Q2–Q32 rerun.

See AUTHOR-METRICS.json, AUTHOR-METRICS.csv and ENERGY-CHANGE-PER-UPDATE.csv for all calculated values. The original evidence and the earlier detailed scientific review are retained unchanged elsewhere in the published package. In a completed supplement, FIELD-AUDIT-SUMMARY.json and record.json distinguish measured, deferred, interrupted and untested work.
'''
 (output/'ASSESSMENT.md').write_text(text)
 htmltable='<table><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in ['Case','Backend','Updates','Force','Max acceleration','Last-ten median energy change','Last-ten <1e-9'])+'</tr>'
 for r in rows:htmltable+='<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [r['case'],r['backend'],r['accepted_updates'],f"{r['relative_force']:.6g}",f"{r['maximum_acceleration']:.6g}",f"{r['final10_relative_energy_change_median']:.3g}",r['final10_updates_below_1e_minus9']])+'</tr>'
 body='<h1>Q21 author-specific measurement assessment</h1><p>UTC '+report['recorded_at']['utc']+'; Melbourne '+report['recorded_at']['melbourne']+'</p><p>No original admission gate has changed. Optimizer updates are not physical time.</p>'+htmltable+'</table>'
 for a in report['method_assessments']:body+='<h2>'+html.escape(a['author'])+'</h2><p><a href="'+a['source']+'">Primary paper</a></p>'+''.join('<p>'+html.escape(a[k])+'</p>' for k in ['applied','not_completed','verdict'])
 body+='<p><a href="ASSESSMENT.md">Detailed assessment</a> · <a href="AUTHOR-METRICS.json">Measured comparisons</a> · <a href="ENERGY-CHANGE-PER-UPDATE.csv">Every measured energy change</a></p>'
 if runtime:
  body+='<p>Supplement status: '+html.escape(runtime['status'])+'</p><p><a href="FIELD-AUDIT-SUMMARY.json">Full-field audit summary</a> · <a href="record.json">Execution record</a> · <a href="UPDATED-RESPONSE-CURVES.json">Updated response fits</a> · <a href="SPATIAL-COMPARISON.json">Matched spatial comparisons</a></p><h2>Native measurements and author-style surfaces</h2><ul>'
  for row in runtime.get('full_field_diagnostics',[]):body+='<li><a href="'+html.escape(str(Path(row['path']).parent/'REPORT.html'))+'">'+html.escape(row['label'])+'</a></li>'
  body+='</ul><h2>Matched response measurements</h2><p>Points and qualified fits only; mixed CPU/CUDA optimization paths remain a comparison limit.</p><img style="max-width:100%" src="updated-response.png" alt="Matched force and acceleration responses">'
 (output/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Q21 criteria assessment</title><style>body{font:16px/1.6 system-ui;max-width:1150px;margin:2rem auto;padding:1rem}table{border-collapse:collapse}th,td{border:1px solid #bbb;padding:.5rem}a{color:#075a9e}</style>'+body+'</html>\n')
 return report
if __name__=='__main__':assess(ROOT/'documentation/author-comparison')


def plot_responses(points,fits,output):
 import numpy as np
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(1,2,figsize=(11,4.5))
 for ax,key,limit in zip(axes,['force','acceleration'],[1e-4,1e-3]):
  for row in points:
   ax.scatter(row['spacing'],row[key],marker='s' if row['backend']=='cpu' else 'o',color='#1460a4' if row['backend']=='cpu' else '#8b4513');ax.annotate(str(row['nodes']),(row['spacing'],row[key]),xytext=(3,4),textcoords='offset points',fontsize=8)
  if points:
   x=np.linspace(min(p['spacing'] for p in points),max(p['spacing'] for p in points),200)
   for model in fits[key]['models']:
    if model['eligible']:
     y=np.polyval(model['coefficients_highest_power_first'],x)
     if model['model']=='exponential':y=np.exp(np.clip(y,-700,700))
     ax.plot(x,np.where(y>0,y,np.nan),label='qualified '+model['model'],alpha=.7)
  ax.axhline(limit,color='green',linestyle='--',label='unchanged project limit');ax.set_yscale('log');ax.set_xlabel('Spacing at fixed box 30.72');ax.set_ylabel(key);ax.grid(alpha=.2);ax.legend(fontsize=7)
 t=stamp();fig.suptitle('Matched 80-update responses: squares CPU; circles original CUDA');fig.text(.01,.01,'UTC '+t['utc']+' | Melbourne '+t['melbourne']+'\nFinite-horizon measurements, not stationary spatial convergence or a fitted stability certificate.',fontsize=6);fig.tight_layout(rect=(0,.08,1,.94));fig.savefig(Path(output)/'updated-response.png',dpi=200);fig.savefig(Path(output)/'updated-response.svg');plt.close(fig)
