import csv,html,io,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .dependencies import predict

def render(out):
 r=json.loads((out/'record.json').read_text());fig,axes=plt.subplots(1,3,figsize=(15,4.8),layout='constrained');table='';csvrows=[]
 for ax,b in zip(axes,r['blocks']):
  dev=b['development'];val=b['validation'];model=b['models'][0];xs=np.linspace(min(v['x'] for v in dev),max(v['x'] for v in dev),300);ax.plot(xs,100*predict(model,xs),label=model['model']);ax.scatter([v['x'] for v in dev],[100*v['y'] for v in dev],s=25,label='Development');ax.scatter([v['x'] for v in val],[100*v['y'] for v in val],marker='s',s=35,label='Fresh validation');ax.set(title=b['id'],xlabel='T' if b['variable']=='duration' else 'h',ylabel=b['response']+' (%)');ax.grid(alpha=.2);ax.legend(fontsize=8)
  table+=f"<tr><td>{b['id']}</td><td>{model['model']}</td><td>{model['validation_rmse']:.6g}</td><td>{b['stop_reason']}</td><td>{b['prediction_pass']}</td></tr>";csvrows.extend({'block':b['id'],**v} for v in dev+val)
 fig.suptitle('Controlled dependency continuation — '+r['role']);fig.savefig(out/'dependency-curves.png',dpi=300);buf=io.StringIO();fig.savefig(buf,format='svg');svg=buf.getvalue();svg=svg[svg.index('<svg'):];plt.close(fig)
 with (out/'measurements.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(csvrows[0]),lineterminator='\n');w.writeheader();w.writerows(csvrows)
 limits='Spacing is varied at fixed box side 8, T=1, dt=1/960, phase zero, orientation zero and startup prescription. The primary mesh response is a matched vector error on one fixed physical observer, separate from interpolation baseline and total observed error. Observer norms are not added as scalars; cross terms retain cancellation. Native-grid errors and moving native-cube flux diagnostics remain auxiliary. A power fit is empirical until its regime and withheld predictions are supported. No operating grid is selected without a numerical error budget. Driven Hopfion boundaries, source-free classical Maxwell limits, all SF gates and Q4/Q7 exclusions remain.'
 body=f'<h1>Controlled dependency continuation</h1><p>{html.escape(json.dumps(r["finished_at"]))}</p><p>Status: {r["status"]}; role: {r["role"]}; cases: {r["completed_cases"]}.</p>'+svg+'<table><tr><th>Study</th><th>Model</th><th>Validation RMSE (fraction)</th><th>Refinement stop</th><th>Prediction pass</th></tr>'+table+'</table><p>'+limits+'</p><p><a href="qx-transfer/QX-REPORT.html">Qx dependency transfer audit</a> applies the matching rules to existing results without new SF evolution or retrospective claims of fresh validation. Original failures remain visible.</p><p>Fields stay local under fields/. Compact evidence excludes their bytes. Reused old states are identified, hashed and CRC checked. Code and analysis received AI assistance; no independent scientific peer review or particle claim is implied.</p>'
 (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Controlled dependency continuation</title><style>body{font:16px/1.6 system-ui;max-width:1450px;margin:30px auto;padding:0 20px}svg{width:100%;height:auto}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}</style>'+body+'</html>')
 (out/'SUMMARY.md').write_text('# Controlled dependency continuation\n\n'+json.dumps(r['finished_at'])+'\n\nStatus: '+r['status']+'; role: '+r['role']+'; cases: '+str(r['completed_cases'])+'.\n\n'+limits+'\n\nSee REPORT.html and qx-transfer/QX-REPORT.html. Local full fields are not in compact evidence.zip.\n')
