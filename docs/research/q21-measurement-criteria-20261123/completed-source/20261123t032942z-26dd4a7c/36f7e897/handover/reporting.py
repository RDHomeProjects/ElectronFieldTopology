"""Browser report, CSVs and final compact seal; no full fields in evidence."""
import csv,html,io,os,time,zipfile
from common import ROOT,load,save,sha,stamp

def svg_series(out,records):
    import numpy as np
    colors=['#1764a4','#c54d24','#318149','#9457a3','#a1801d','#008b8b','#be3b72','#555555'];paths=[];values=[]
    for r in records:
        y=[max(x['metrics']['relative_force_l2']/1e-4,x['metrics']['acceleration_max']/1e-3) for x in r['history']];values+=y
    if not values:return
    ymin=min(.8,min(values));ymax=max(2,max(values));ly=np.log10(ymin);hy=np.log10(ymax)
    for i,r in enumerate(records):
        pts=[]
        for x in r['history']:
            score=max(x['metrics']['relative_force_l2']/1e-4,x['metrics']['acceleration_max']/1e-3);xx=60+x['accepted_step']/120*760;yy=360-(np.log10(max(score,1e-12))-ly)/max(hy-ly,1e-12)*300;pts.append(f'{xx:.2f},{yy:.2f}')
        color=colors[i%len(colors)];paths.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.5" points="'+ ' '.join(pts)+'"/>');paths.append(f'<text x="850" y="{45+i*25}" fill="{color}">'+html.escape(r['case']['id'])+'</text>')
    gate=360-(0-ly)/max(hy-ly,1e-12)*300
    body='<svg xmlns="http://www.w3.org/2000/svg" width="1150" height="440" viewBox="0 0 1150 440"><rect width="100%" height="100%" fill="white"/><g font-family="sans-serif" font-size="13"><text x="40" y="25">Measured joint residual score (log scale); admission requires score ≤ 1 and all other gates</text><path d="M60 45V360H820" fill="none" stroke="black"/><line x1="60" x2="820" y1="'+str(gate)+'" y2="'+str(gate)+'" stroke="green" stroke-dasharray="5 4"/><line x1="408.3" x2="408.3" y1="45" y2="360" stroke="gray" stroke-dasharray="4 4"/><text x="365" y="390">Accepted updates (0–120); dashed vertical: native restart at update55</text>'+''.join(paths)+'</g></svg>\n';(out/'matched-residuals.svg').write_text(body)

def parameter_plot(out):
    if not (out/'CURVE-FITS.json').exists():return
    pts=load(out/'CURVE-FITS.json').get('responses',[])
    if not pts:return
    pieces=[]
    for panel,key in enumerate(['force','acceleration','joint']):
        vals=[r[key] for r in pts];low=min(vals)*.9;high=max(vals)*1.1;left=60+panel*365
        pieces.append(f'<path d="M{left} 45V280H{left+300}" fill="none" stroke="black"/><text x="{left}" y="25">'+key+'</text>')
        for r in pts:
            x=left+(r['spacing']-.15)/.10*300;y=280-(r[key]-low)/max(high-low,1e-30)*220
            pieces.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#1764a4"><title>nodes{r["nodes"]}; spacing{r["spacing"]}; {key}{r[key]}</title></circle><text x="{x+5:.2f}" y="{y-5:.2f}">{r["nodes"]}</text>')
        pieces.append(f'<text x="{left}" y="310">Spacing0.15 to0.25; labels=node count</text>')
    (out/'parameter-response.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1150" height="355" viewBox="0 0 1150 355"><rect width="100%" height="100%" fill="white"/><g font-family="sans-serif" font-size="12">'+''.join(pieces)+'<text x="45" y="340">Actual matched80-update medians; no unvalidated fitted optimum is drawn.</text></g></svg>\n')

def render(out,record):
    cases=record.get('cases',[]);svg_series(out,cases);parameter_plot(out);rows=[]
    for r in cases:
        for x in r['history']:
            rows.append({'utc':x['recorded_at']['utc'],'melbourne':x['recorded_at']['melbourne'],'case':r['case']['id'],'nodes':r['case']['nodes'],'spacing':r['spacing'][0],'accepted_step':x['accepted_step'],'native_iteration':x['iteration'],'energy':x['metrics']['energy'],'force':x['metrics']['relative_force_l2'],'acceleration':x['metrics']['acceleration_max'],'tail':x['metrics']['tail_fraction'],'guard':x['metrics']['guard_fraction'],'all_gates':x['gates']['all_readiness_gates'],**x.get('timing',{})})
    if rows:
        fields=list(dict.fromkeys(k for row in rows for k in row));buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);(out/'measurements.csv').write_text(buf.getvalue())
    bulk=load(out/'BULK-LEDGER.json') if (out/'BULK-LEDGER.json').exists() else {};text='<!doctype html><html lang="en"><meta charset="utf-8"><title>Retained-field audit and Q21 resolution pilot</title><style>body{font:16px/1.5 system-ui;max-width:1200px;margin:2rem auto;padding:1rem}td,th{border:1px solid #ccc;padding:.5rem;text-align:left}table{border-collapse:collapse;width:100%}img{max-width:100%}code{overflow-wrap:anywhere}</style><h1>Retained-field audit and Q21 fixed-box resolution pilot</h1><p>Status: <b>'+html.escape(record['status'])+'</b>. Source iteration545; box30.72; shift0.25. Optimizer updates are not physical time. Curve predictions grant no admission. Existing references remain unchanged.</p><p><a href="record.json">Full record</a> · <a href="BULK-LEDGER.json">Q2–Q32 ledger</a> · <a href="CURVE-FITS.json">Curve validation</a> · <a href="measurements.csv">Measured updates</a></p><p>Charged optimizer attempts: '+str(record.get('charged_optimizer_attempts',0))+'/720. Resource/metadata deferrals: '+html.escape(str(record.get('deferrals',[])))+'</p>'
    if cases:text+='<img src="matched-residuals.svg" alt="Measured joint residual trajectories"><table><tr><th>Case</th><th>Spacing</th><th>Accepted</th><th>Final force</th><th>Final acceleration</th><th>All gates</th></tr>'
    for r in cases:
        vals=[r['case']['id'],str(r['spacing'][0]),str(r['accepted_steps']),str(r['final']['metrics']['relative_force_l2']),str(r['final']['metrics']['acceleration_max']),str(r['final']['gates']['all_readiness_gates'])];text+='<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in vals)+'</tr>'
    if cases:text+='</table>'
    if (out/'parameter-response.svg').exists():text+='<h2>Measured spacing responses</h2><img src="parameter-response.svg" alt="Measured parameter responses">'
    text+='<h2>Charge coverage</h2><table><tr><th>Q</th><th>Catalogued</th><th>Replayed</th><th>Deferred</th><th>Readiness passes</th></tr>'
    for r in bulk.get('q_summary',[]):text+='<tr>'+''.join('<td>'+str(r[k])+'</td>' for k in ['q','catalogued','replayed','deferred','all_readiness_passes'])+'</tr>'
    text+='</table><p>The finite endpoint catalogue does not enumerate every possible seed or knot. Historical cell-native successes are not overwritten by D4 replay. Failed preparation is not a rejection of a charge. Interpolated fields and fixed-horizon relaxed fields are not a stationary convergence proof. Full float64 fields remain local.</p></html>\n';(out/'REPORT.html').write_text(text)

def seal(out):
    fields=[]
    for p in sorted(out.rglob('*.npz')):
        if 'handover' not in p.relative_to(out).parts:fields.append({'path':p.relative_to(out).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
    save(out/'FIELD-MANIFEST.json',{'recorded_at':stamp(),'fields':fields,'scope':'Full local initial/restart/best/final states, not included in compact evidence'})
    excluded={'evidence.zip','heartbeat.json','supervisor.json','worker-launch.json','telemetry-latest.json','telemetry.jsonl','.worker.lock','STOP.json','PAUSE-REQUEST.json'}
    files=[p for p in sorted(out.rglob('*')) if p.is_file() and p.name not in excluded and p.suffix not in ['.npz','.so','.tmp'] and '__pycache__' not in p.parts and p!=out/'SHA256SUMS']
    hashes={p.relative_to(out).as_posix():sha(p) for p in files}
    (out/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in hashes.items()))
    tmp=out/'evidence.tmp'
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(out).as_posix())
        z.write(out/'SHA256SUMS','SHA256SUMS')
    tmp.replace(out/'evidence.zip')
