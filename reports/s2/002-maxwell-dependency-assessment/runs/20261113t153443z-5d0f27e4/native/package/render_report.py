"""Offline compact tables, CSV and exact scientific plots; Apache-2.0."""
import csv,html,io,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dependencies import predict

def render(out):
    r=json.loads((out/'record.json').read_text());fig,axes=plt.subplots(3,2,figsize=(12,12),layout='constrained');table='';csvrows=[]
    for ax,block in zip(axes.flat,r['blocks']):
        dev=block['development'];val=block['validation'];model=block['models'][0];xs=np.linspace(min(v['x'] for v in dev),max(v['x'] for v in dev),300)
        for i,m in enumerate(block['models'][:2]):ax.plot(xs,100*predict(m,xs),label=('Frozen ' if i==0 else 'Alternative ')+m['model'],alpha=1 if i==0 else .5)
        for role,label,marker in [('seed_development','Seed','o'),('adaptive_development','Adaptive','D')]:
            rows=[v for v in dev if v['role']==role];ax.scatter([v['x'] for v in rows],[100*v['y'] for v in rows],label=label,marker=marker,s=30,zorder=3)
        ax.scatter([v['x'] for v in val],[100*v['y'] for v in val],label='Validation',marker='s',s=30,zorder=3)
        xlabel='Orientation (degrees)' if block['variable']=='angle_degrees' else block['variable']+' (model units)'
        ax.set(title=block['id'],xlabel=xlabel,ylabel='Synchronized native field L2 (%)');ax.grid(alpha=.2);ax.legend(fontsize=7)
        if np.ptp([v['y'] for v in dev+val])<=1e-12:
            centre=100*float(np.mean([v['y'] for v in dev+val]));ax.set_ylim(centre-.00005,centre+.00005);ax.ticklabel_format(axis='y',style='plain',useOffset=False);ax.text(.5,.85,'Variation below acquisition floor',ha='center',transform=ax.transAxes,fontsize=9)
        table+=f"<tr><td>{block['id']}</td><td>{model['model']}</td><td>{model['validation_rmse']:.5g}</td><td>{block['stop_reason']}</td><td>{block['empirical_prediction_check']}</td></tr>"
        csvrows.extend({'block':block['id'],**v} for v in dev+val)
    axes.flat[-1].axis('off');axes.flat[-1].text(0,.95,'Fixed N='+str(r['config']['nodes'])+'; box side 8\nOne variable per block\nSeparate validation after model freeze\nNo accuracy budget → no optimum selected\nPhysical / SF gates unchanged',va='top',fontsize=12)
    fig.suptitle('Bounded Maxwell variable dependencies — '+r['role'],fontsize=14);fig.savefig(out/'dependency-curves.png',dpi=300);buf=io.StringIO();fig.savefig(buf,format='svg');svg=buf.getvalue();svg=svg[svg.index('<svg'):];plt.close(fig)
    with (out/'measurements.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]),lineterminator='\n');w.writeheader();w.writerows(csvrows)
    cases=[(p.stem,json.loads(p.read_text())) for p in sorted((out/'cases').glob('*.json'))];case_table=''
    for key,c in cases:
        p=c['parameters'];fourier=c.get('fourier',{});case_table+=f"<tr><td>{key}</td><td>{p['field']}</td><td>{p['duration']:.6g}</td><td>{c['dt']:.6g}</td><td>{p['angle_degrees']}</td><td>{p['rotation_code']}</td><td>{c['sync_native_error']:.6g}</td><td>{c['poynting_balance']['defect_over_initial_energy']:.5g}</td><td>{c['max_discrete_divergence_change_normalized']:.5g}</td><td>{fourier.get('yee_difference','—')}</td></tr>"
    limits='Hopfion boundaries remain analytically driven; the interior Poynting cube is not an isolated outer boundary. Common-grid linear interpolation and magnetic time synchronization contribute diagnostic error. Periodic packet and driven Hopfion are separate numerical problems. Cubic packet rotations preserve periodicity and test axis permutations, not arbitrary-angle isotropy. Flux uses nested temporal quadrature on the same trajectory; a flux defect is not solely an integration-time error. Fixed grid and box do not establish spatial/domain convergence. The dt-dependent analytic half-step startup is retained and qualified. No SF, topology, confinement, charge, spin or electron gate is closed.'
    text=f'''<h1>Bounded Maxwell validation extension</h1><p>Status: {r['status']}; role: {r['role']}; completed cases: {r['completed_cases']}. All periodic numerical controls pass: {r['all_packet_controls_pass']}.</p><p>Started: {html.escape(json.dumps(r['recorded_at']))}<br>Finished: {html.escape(json.dumps(r['finished_at']))}</p>{svg}<h2>Conditional relationships</h2><table><tr><th>Block</th><th>Frozen primary model</th><th>Validation RMSE (fraction)</th><th>Refinement stop</th><th>Prediction check</th></tr>{table}</table><p>Models are chosen using development leave-one-out residuals, frozen before block validation, and never extrapolated. Validation residuals remain separate from scientific acceptance. A budget-exhausted label is not a convergence certificate. Suspected inflections require bracketing confirmation; a quadratic turning point is not an inflection. No optional operating condition is selected because no new accuracy/cost objective has been declared.</p><h2>Synchronized diagnostics</h2><p>E is at T. B_sync averages a temporary B at T+dt/2 with the retained B at T-dt/2. Common-grid fields are linearly interpolated to cell centres before energy and Poynting calculations. The native E/B_half trajectory is preserved. Periodic energy also has a separately reported native leapfrog modified invariant; it is not identified with continuum physical energy.</p><h2>Cases</h2><div style="overflow:auto"><table><tr><th>ID</th><th>Field</th><th>T</th><th>dt</th><th>Angle</th><th>Cubic rotation</th><th>Sync native error</th><th>Cube balance/U0</th><th>Div change</th><th>Yee/Fourier common-grid difference</th></tr>{case_table}</table></div><h2>Limits</h2><p>{limits}</p><p>Full float64 states stay local under fields/. Their hashes and NPZ CRC checks are in field-manifest.json. Compact evidence.zip excludes those arrays. Code and analysis received AI assistance; these records are not independent scientific peer review.</p>'''
    (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bounded Maxwell dependencies</title><style>body{font:16px/1.6 system-ui;max-width:1300px;margin:28px auto;padding:0 18px;color:#18324a}svg{width:100%;height:auto}table{border-collapse:collapse;font-size:13px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}</style>'+text+'</html>')
    (out/'SUMMARY.md').write_text('# Bounded Maxwell validation extension\n\n'+json.dumps(r['finished_at'])+'\n\nStatus: '+r['status']+'; role: '+r['role']+'.\n\nCases: '+str(r['completed_cases'])+'; all periodic numerical controls pass: '+str(r['all_packet_controls_pass'])+'.\n\n'+limits+'\n\nOpen REPORT.html for curves, coefficients via blocks/*/result.json, and validation outcomes. Full fields remain local; compact evidence excludes arrays.\n')
