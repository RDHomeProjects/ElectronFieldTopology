"""Offline browser report and bounded scientific plots."""
import csv,html,json
import numpy as np
from .common import save,sha
from .fits import predict
from .kernel.calibration import RESPONSES
def finish(out,record):
 rows=[]
 for c in record['cases']:
  for order,v in c['orders'].items():
   row={'case_id':c['case_id'],'field':c['parameters']['field'],'native_nodes':c['parameters']['nodes'],'order':order,'origin':v['origin']}
   for k in RESPONSES:row[k]=v['measurement'][k];row['original33_'+k]=c['original_observer'][k]
   rows.append(row)
 if rows:
  with (out/'measurements.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
 for field,ax in zip(['hopfion','packet'],axes):
  cases=sorted([c for c in record['cases'] if c['parameters']['field']==field],key=lambda c:c['parameters']['nodes'])
  for key,label in zip(RESPONSES,['Evolution','Interpolation baseline','Total']):
   ax.plot([c['parameters']['nodes'] for c in cases],[100*c['orders']['6']['measurement'][key] for c in cases],'o-',label=label)
  ax.set(yscale='log',xlabel='Native nodes N',ylabel='Relative error (%)',title=field.title()+' — same cube, order-6 measurement');ax.grid(alpha=.2);ax.legend(fontsize=8)
 fig.savefig(out/'measured-spacing.png',dpi=300);plt.close(fig)
 if record.get('fits'):
  fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained');fit_rows=[]
  for i,field in enumerate(['hopfion','packet']):
   for j,key in enumerate(RESPONSES):
    item=next(f for f in record['fits'] if f['field']==field and f['response']==key);m=item['models'][0];rows=item['rows'];x=np.array([v['x'] for v in rows]);y=np.array([v['y'] for v in rows]);grid=np.linspace(min(x),max(x),300);ax=axes[i,j]
    ax.plot(grid,100*predict(m,grid),label=m['model']);ax.scatter(x,100*y,s=22,label='order-6 measurements',zorder=3)
    old=[next(c for c in record['cases'] if c['case_id']==v['case_id'])['original_observer'][key] for v in rows];ax.scatter(x,100*np.array(old),s=20,marker='x',label='original 33-node observer')
    ax.set(xlabel='h = L/N (model units)',ylabel='Relative error (%)',title=field.title()+' — '+key.replace('_observed_error','').replace('_error',''));ax.grid(alpha=.2);ax.legend(fontsize=6)
    fit_rows.append({'field':field,'response':key,'model':m['model'],'origin':m['origin'],'scale':m['scale'],'coefficients':json.dumps(m['coefficients']),'development_loo_rmse':m['development_loo_rmse'],'development_max_residual':m['development_max_residual'],'measurement_contract_pass':item['measurement_contract_pass'],'validation_status':item['validation_status']})
  fig.suptitle('Descriptive fits — all existing physical points are development context');fig.savefig(out/'fitted-spacing.png',dpi=300);plt.close(fig)
  with (out/'fits.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(fit_rows[0]),lineterminator='\n');w.writeheader();w.writerows(fit_rows)
 table=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [c['parameters']['field'],c['parameters']['nodes'],c['all_response_pass'],f"{max(c['order_differences']['5-to-6'].values()):.6g}"])+'</tr>' for c in record['cases'])
 fit_table=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [f['field'],f['response'],f['models'][0]['model'],f"{f['models'][0]['development_loo_rmse']:.6g}"])+'</tr>' for f in record.get('fits',[]))
 body='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Cell-aware spacing measurements</title><style>body{font:16px/1.65 system-ui;max-width:1200px;margin:auto;padding:20px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}img{max-width:100%}</style><h1>Cell-aware saved-state measurements</h1><p>'''+html.escape(json.dumps(record['finished_at']))+'''</p><p>Status: complete_pending_review. Phase: '''+html.escape(record['phase'])+'''. Original E/B_half states are unchanged. No physical time integration ran.</p><p>The common observation contract is the same physical cube, native linear interpolation and synchronized B convention, measured by cell-aware Gauss order 6. Order comparisons use the registered 1e-6 fractional norm budget for all three responses. Agreement is empirical, not a rigorous bound.</p><p>Anchor gate: '''+str(record['anchor_contract_pass'])+'''; all measured-state contract: '''+str(record.get('all_spacing_contract_pass'))+'''. Earlier calibration failures and the original physical-mesh prediction failure are retained.</p><table><tr><th>Field</th><th>N</th><th>All-response check</th><th>Maximum order 5→6 difference</th></tr>'''+table+'''</table><img src="measured-spacing.png" alt="Measured spatial dependence"><h2>Descriptive development relationships</h2><p>Every existing physical point, including previously inspected validation points, is development context here. No fresh physical validation has run. Candidate coefficients, residuals, frozen models and feature estimates are in record.json and frozen-fits.json. Leave-one-out selection does not create independent validation. These fits cannot select an optimal production mesh without an accuracy/cost objective.</p><table><tr><th>Field</th><th>Response</th><th>Development-selected model</th><th>LOO RMSE (fraction)</th></tr>'''+fit_table+'''</table><p>Future physical validation nodes are reserved but not executed: '''+html.escape(str(record['config']['future_physical_validation_nodes']))+'''. Any future validation must preserve this frozen contract or declare a new model.</p><p><a href="record.json">Full record</a> · <a href="measurements.csv">Measurements</a></p><p>Maxwell observation changes do not qualify SF dynamics or isolated physical behaviour. Q1 remains parked; Q2 reference; Q4/Q7 original admissions remain unresolved. Duration confirmation is separate. AI-assisted preparation is not scientific peer review.</p></html>'''
 if record.get('fits'):body=body.replace('<h2>Descriptive development relationships</h2>','<h2>Descriptive development relationships</h2><img src="fitted-spacing.png" alt="Measured points and development-selected fitted curves"><p><a href="fits.csv">Fit coefficients and residuals</a></p>')
 (out/'REPORT.html').write_text(body)
 (out/'SUMMARY.md').write_text('# Cell-aware spacing measurements\n\n'+json.dumps(record['finished_at'])+'\n\nStatus: **complete_pending_review**; phase: '+record['phase']+'.\n\nAnchor contract: '+str(record['anchor_contract_pass'])+'; measured states: '+str(len(record['cases']))+'; all-spacing contract: '+str(record.get('all_spacing_contract_pass'))+'.\n\nAll fits are descriptive development fits; no fresh physical prediction validation or physical evolution. Source fields retained unchanged.\n')
 save(out/'record.json',record)
