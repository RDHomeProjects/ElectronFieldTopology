"""Self-contained browser report and race-free compact evidence snapshots."""
import csv,html,hashlib,io,json,os,zipfile
import numpy as np
from common import ROOT,save,sha,stamp,load
from fitting import evaluate

def plot(samples,fit,path,key="score",trial=None):
    points=[s for s in samples if s['response']['eligible']]
    if not points:return
    xs=[s['log2_shift'] for s in points];ys=[np.log10(s['response'][key]) for s in points];xmin=min(xs)-.25;xmax=max(xs)+.25;lines=[]
    models=fit.get(key,{}).get('models',[])
    for m in models:
        if m['validated']:
            xx=np.linspace(min(xs),max(xs),201);yy=evaluate(m,xx);keep=yy>0
            lines.append((m['model'],xx[keep],np.log10(yy[keep])))
    if trial and trial['response']['eligible']:
        xmin=min(xmin,trial['log2_shift']-.25);xmax=max(xmax,trial['log2_shift']+.25);ys.append(float(np.log10(trial['response'][key])))
    values=ys+[float(y) for _,_,line in lines for y in line];lo=min(values);hi=max(values);pad=max((hi-lo)*.1,.05);lo-=pad;hi+=pad
    x=lambda v:70+760*(v-xmin)/(xmax-xmin)
    y=lambda v:400-330*(v-lo)/(hi-lo)
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 490" role="img"><title>Measured conditioning response and validated fits</title><rect width="900" height="490" fill="white"/>','<path d="M70 40V400H830" fill="none" stroke="#444"/>']
    for v in range(int(np.floor(xmin)),int(np.ceil(xmax))+1):parts.append(f'<text x="{x(v):.2f}" y="425" text-anchor="middle">{v}</text>')
    for v in np.linspace(lo,hi,6):parts.append(f'<text x="60" y="{y(v):.2f}" text-anchor="end">{10**v:.2g}</text>')
    colors=['#277da1','#f8961e','#43aa8b']
    for i,(name,xx,yy) in enumerate(lines):
        line=' '.join(f'{x(a):.2f},{y(b):.2f}' for a,b in zip(xx,yy));parts.append(f'<polyline points="{line}" fill="none" stroke="{colors[i%3]}" stroke-width="2"/><text x="{90+i*240}" y="24" fill="{colors[i%3]}">{html.escape(name)} LOO validated</text>')
    for s in points:
        parts.append(f'<circle cx="{x(s["log2_shift"]):.2f}" cy="{y(np.log10(s["response"][key])):.2f}" r="5" fill="#172a3a"><title>{html.escape(s["case"])}: shift={s["shift"]:.7g},response={s["response"][key]:.7g}</title></circle>')
    if trial and trial['response']['eligible']:
        parts.append(f'<circle cx="{x(trial["log2_shift"]):.2f}" cy="{y(np.log10(trial["response"][key])):.2f}" r="8" fill="none" stroke="#dc2626" stroke-width="3"><title>Independent selected-value30-update confirmation</title></circle>')
    parts.append('<text x="450" y="460" text-anchor="middle">log₂(preconditioner shift); points are actual matched measurements</text><text x="450" y="485" text-anchor="middle">Vertical axis: '+html.escape(key)+' (log scale); red ring: selected-value confirmation</text></svg>');path.write_text('\n'.join(parts)+'\n')

def render(out,record):
    samples=record.get('samples',[]);fits=record.get('fits',{});trial_record=next((c for c in record.get('cases',[]) if c['case']['id']=='optimal-validation'),None);trial=({'log2_shift':trial_record['case']['log2_shift'],'response':trial_record['response']} if trial_record else None)
    plot(samples,fits,out/'conditioning-response.svg',trial=trial)
    plot(samples,fits,out/'force-response.svg',key='median_force',trial=trial)
    plot(samples,fits,out/'acceleration-response.svg',key='median_acceleration',trial=trial)
    buf=io.StringIO(newline='');w=csv.writer(buf,lineterminator='\n');w.writerow(['case','shift','log2_shift','eligible','accepted_steps','median_force','median_acceleration','joint_score','all_readiness_gates'])
    for s in samples:
        r=s['response'];w.writerow([s['case'],s['shift'],s['log2_shift'],r['eligible'],r.get('accepted_steps',0),r.get('median_force',''),r.get('median_acceleration',''),r.get('score',''),s['all_readiness_gates']])
    (out/'sampling.csv').write_text(buf.getvalue())
    buf=io.StringIO(newline='');w=csv.writer(buf,lineterminator='\n');w.writerow(['case','shift','accepted_step','native_iteration','charged_attempt','energy','force','acceleration','tail','guard','all_readiness_gates','optimization_seconds'])
    for c in record.get('cases',[]):
        for r in c['history']:
            m=r['metrics'];w.writerow([c['case']['id'],c['case']['shift'],r['accepted_step'],r['iteration'],r.get('charged_attempt',''),m['energy'],m['relative_force_l2'],m['acceleration_max'],m['tail_fraction'],m['guard_fraction'],r['gates']['all_readiness_gates'],r.get('optimization_seconds','')])
    (out/'measurements.csv').write_text(buf.getvalue())
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [s['case'],f'{s["shift"]:.7g}',s['response'].get('score','ineligible'),s['all_readiness_gates']])+'</tr>' for s in samples)
    diag=record.get('residual_audit',{});selection=record.get('selection',{});validation=record.get('validation',{})
    body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Q21 conditioning calibration</title><style>body{{font:17px system-ui;max-width:1100px;margin:3rem auto;padding:0 1rem;line-height:1.5}}table{{border-collapse:collapse}}td,th{{padding:.4rem;border:1px solid #bbb}}img{{width:100%}}pre{{white-space:pre-wrap}}a{{color:#075985}}</style><h1>Q21 conditioning calibration</h1><p>{html.escape(record['status'])} · {record['charged_optimizer_attempts']} /580 charged attempts; physical-time steps:0.</p><p>The unchanged129³ field occupies a30.72 box with0.24 spacing. Only the numerical Sobolev shift is varied in consistently restarted cases. The exact-memory control is separate. These are preparations, not motion simulations or a proof of stability.</p><p>The response uses medians over accepted updates21–30. Lower joint score is better; score1 corresponds to the force and acceleration thresholds. Topology, representation and boundary gates are also checked at every update. A favorable fit never grants admission.</p><p><a href="sampling.csv">Matched samples CSV</a> · <a href="measurements.csv">Every measured update CSV</a> · <a href="record.json">Full record</a> · <a href="RESIDUAL-AUDIT.json">Localized and spectral audit</a> · <a href="handover/PROTOCOL.md">Protocol</a></p>'''
    for image,title in [('conditioning-response.svg','Joint normalized residual'),('force-response.svg','Median force'),('acceleration-response.svg','Median maximum acceleration')]:
        if (out/image).exists():body+='<h2>'+title+'</h2><img src="'+image+'" alt="Actual matched measurements and validated parameter curves">'
    body+='<table><tr><th>Case</th><th>Shift</th><th>Joint score</th><th>Final readiness</th></tr>'+rows+'</table><h2>Selection and confirmation</h2><pre>'+html.escape(json.dumps({'selection':selection,'validation':validation},indent=2))+'</pre><h2>Interpretation</h2><p>Linear, quadratic and exponential response models use log₂(shift). They must outperform a constant predictor under leave-one-out validation. Additional measurements concentrate near turns and unresolved best regions. Extrapolation is bounded. A longer comparison is allocated only after a new measured trial improves the joint response. A measured best setting without fit support is explicitly labelled as such.</p><p>All original gates remain fixed. Passing static readiness would still require spatial/domain confirmation and controlled physical-time tests. Positive curvature in a finite tested subspace does not certify global stability.</p></html>'
    (out/'REPORT.html').write_text(body+'\n')

def seal(out):
    transient={'evidence.zip','SHA256SUMS','heartbeat.json','status.json','supervisor.json','worker-launch.json','telemetry-latest.json','STOP.json','PAUSE-REQUEST.json'}
    fields=[{'path':f.relative_to(out).as_posix(),'sha256':sha(f),'bytes':f.stat().st_size} for f in sorted(out.rglob('*.npz'))]
    save(out/'FIELD-MANIFEST.json',{'recorded_at':stamp(),'fields':fields,'scope':'All retained full fields remain local; compact evidence includes their hashes and every recorded measurement.'})
    members={}
    for f in sorted(out.rglob('*')):
        if not f.is_file() or '__pycache__' in f.parts or f.suffix in ['.npz','.so','.tmp','.lock'] or (f.parent==out and f.name in transient):continue
        data=f.read_bytes()
        if f.name=='telemetry.jsonl':data=data[:data.rfind(b'\n')+1]
        members[f.relative_to(out).as_posix()]=data
    receipt={'recorded_at':stamp(),'snapshot_policy':'Each compact member is read once into immutable bytes; exactly those bytes are both hashed and written. Telemetry is a complete-line prefix. The live supervisor can append later without invalidating this archive.','telemetry_snapshot_bytes':len(members.get('telemetry.jsonl',b'')),'full_fields_included':False}
    save(out/'SEAL-RECEIPT.json',receipt);members['SEAL-RECEIPT.json']=(out/'SEAL-RECEIPT.json').read_bytes()
    members['SHA256SUMS']=''.join(hashlib.sha256(b).hexdigest()+'  '+n+'\n' for n,b in sorted(members.items()) if n!='SHA256SUMS').encode()
    temp=out/'evidence.tmp'
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in sorted(members.items()):z.writestr(n,b)
    with temp.open('rb') as f:os.fsync(f.fileno())
    temp.replace(out/'evidence.zip');(out/'SHA256SUMS').write_bytes(members['SHA256SUMS'])
    from integrity import checked_evidence
    return {'recorded_at':stamp(),'evidence_sha256':sha(out/'evidence.zip'),'matching_compact_members':len(checked_evidence(out/'evidence.zip'))}
