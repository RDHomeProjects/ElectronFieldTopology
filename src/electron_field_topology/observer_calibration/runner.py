"""Bounded saved-state calibration with provenance, checkpoints and fresh observers."""
import argparse,csv,hashlib,html,json,os,platform,signal,subprocess,threading,time,traceback,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
from .calibration import prepare,measure,max_change,RESPONSES,next_resolution
from .reference.dependencies import fit_models,predict,features

def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def load(p):return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()
def journal(out,name,fn):
    p=out/'measurements'/(name+'.json');h=p.with_suffix('.sha256')
    if p.exists():
        if not h.exists() or h.read_text().strip()!=sha(p):raise ValueError('Changed checkpoint: '+str(p))
        return load(p)
    result={'measured_at':stamp(),**fn()};save(p,result);h.write_text(sha(p)+'\n');return result

def calibrate(state,case_id,source_case,out,plan):
    budget=plan['measurement_error_budget'];chunk=plan['chunk_x'];rows=[];consecutive=0
    def take(nodes=None,order=None,midpoint=False):
        method='gauss'+str(order) if order else ('midpoint' if midpoint else 'trapezoid')+str(nodes)
        return journal(out,case_id+'-'+method,lambda:measure(state,nodes=nodes,order=order,midpoint=midpoint,chunk=chunk))
    gauss=[]
    for order in plan['cell_gauss_orders']:
        gauss.append(take(order=order))
        if len(gauss)>1 and max_change(gauss[-1],gauss[-2])<=budget:break
    reference=gauss[-1];reference_pass=len(gauss)>1 and max_change(gauss[-1],gauss[-2])<=budget
    # The cell-exact evolution numerator still uses a numerically integrated
    # exact-field denominator. Agreement of orders is empirical, not a bound.
    for count in plan['seed_observer_nodes']:
        rows.append(take(nodes=count))
    old=source_case.get('observer')
    if old and max_change(rows[0],old)>2e-12:raise ValueError('33-node saved-state baseline was not reproduced')
    selections=[]
    for k in range(plan['adaptive_additions']):
        selection=next_resolution(rows,budget,plan['observer_max_nodes'],plan['validation_observer_nodes'])
        if selection is None:break
        choice=out/'choices'/f'{case_id}-{k:02d}.json'
        if choice.exists():
            previous=load(choice)
            if previous['selection']!=selection:raise ValueError('Resume selection changed')
            selected_at=previous['selected_at']
        else:selected_at=stamp();save(choice,{'selected_at':selected_at,'selection':selection})
        nextrow=take(nodes=selection['observer_nodes'])
        if selected_at['utc']>nextrow['measured_at']['utc']:raise ValueError('Selection did not precede measurement')
        good=max_change(nextrow,rows[-1])<=budget and max_change(nextrow,reference)<=budget and reference_pass
        consecutive=consecutive+1 if good else 0
        selections.append({'selected_at':selected_at,**selection,'max_reference_difference':max_change(nextrow,reference),'qualifying':good,'successive_qualifying':consecutive})
        rows.append(nextrow)
        if consecutive>=plan['successive_good_rounds']:break
    models={}
    for response in RESPONSES:
        values=[{'x':1/(r['observer_nodes']-1),'y':r[response]} for r in rows]
        candidates=fit_models(values)
        models[response]={'independent_variable':'observer spacing 4/(M-1), represented as x=1/(M-1)','development':values,'models':candidates,'features':features(values,candidates[0])}
    frozen=out/'frozen'/(case_id+'.json');payload=json.loads(json.dumps({'models':models,'development_counts':[r['observer_nodes'] for r in rows],'reserved_counts':plan['validation_observer_nodes']}))
    if frozen.exists():
        stored=load(frozen)
        if stored['payload']!=payload:raise ValueError('Frozen model changed on resume')
        frozen_at=stored['frozen_at']
    else:frozen_at=stamp();save(frozen,{'frozen_at':frozen_at,'payload':payload})
    validation=[take(nodes=n) for n in plan['validation_observer_nodes']]
    if any(v['measured_at']['utc']<frozen_at['utc'] for v in validation):raise ValueError('Validation was inspected before freeze')
    max_prediction=0.
    for response,v in models.items():
        for model in v['models']:
            residual=[float(predict(model,1/(r['observer_nodes']-1))-r[response]) for r in validation]
            model['validation_residuals']=residual;model['validation_max_abs_error']=max(map(abs,residual))
        max_prediction=max(max_prediction,v['models'][0]['validation_max_abs_error'])
    midpoint=take(nodes=rows[-1]['observer_nodes'],midpoint=True)
    uniform_pass=bool(reference_pass and consecutive>=plan['successive_good_rounds'] and max_change(midpoint,reference)<=budget and max_change(rows[-1],reference)<=budget)
    return {'case_id':case_id,'parameters':source_case['parameters'],'state_sha256':source_case['state']['sha256'],'gauss_refinement':gauss,'reference_empirical_pass':reference_pass,'reference':reference,'development':rows,'adaptive_selections':selections,'frozen_at':frozen_at,'models':models,'validation':validation,'midpoint_control':midpoint,'original_33_max_difference_from_reference':max_change(rows[0],reference),'final_uniform_max_difference_from_reference':max_change(rows[-1],reference),'uniform_observer_pass':uniform_pass,'fresh_prediction_max_error':max_prediction,'fresh_prediction_pass':max_prediction<=budget,'stop_reason':'two_successive_and_independent_rule_met' if uniform_pass else 'bounded_budget_or_independent_rule_unresolved','scope':'Six fixed native states only; no physical mesh fit or continuum proof. Order agreement is an empirical quadrature check.'}

def finish(out,record):
    rows=[]
    for a in record['anchors']:
        for role,items in [('development',a['development']),('validation',a['validation']),('cell-gauss',a['gauss_refinement']),('midpoint',[a['midpoint_control']])]:
            for v in items:rows.append({'case_id':a['case_id'],'field':a['parameters']['field'],'native_nodes':a['parameters']['nodes'],'role':role,**{k:v.get(k) for k in ['observer_nodes','order']+RESPONSES}})
    if rows:
        with (out/'measurements.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    table=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [a['parameters']['field'],a['parameters']['nodes'],a['reference_empirical_pass'],a['uniform_observer_pass'],a['fresh_prediction_pass'],f"{a['original_33_max_difference_from_reference']:.6g}",f"{a['final_uniform_max_difference_from_reference']:.6g}"])+'</tr>' for a in record['anchors'])
    text='''<html><meta charset="utf-8"><title>Saved-state observer calibration</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:30px auto;padding:15px}td,th{padding:8px;border-bottom:1px solid #ccc;text-align:left}img{max-width:100%}</style><h1>Saved-state observer calibration</h1><p>All physical states are held fixed. Native meshes are separate fixed-state strata, not a second fitted variable. No Maxwell or SF physical time integration occurred in this production activity.</p><p>'''+html.escape(json.dumps(record['finished_at']))+'''</p><p>The budget is 1e-6 as a fractional normalized field norm for each of evolution, interpolation and total errors. Cell-Gauss order agreement is empirical; it is not a rigorous error bound. Two consecutive uniform-resolution checks and an independent midpoint rule are required for uniform-observer readiness. Prediction checks are separately labelled.</p><table><tr><th>Field</th><th>Native N</th><th>Cell reference</th><th>Uniform readiness</th><th>Fresh prediction</th><th>33-node difference</th><th>Final uniform difference</th></tr>'''+table+'''</table><p><a href="measurements.csv">Measurements</a> · <a href="record.json">Full record, fitted coefficients, residuals and chronology</a></p><img src="calibration.png" alt="Observer convergence measurements"><p>Changing the observer does not improve the saved physical solution. Numerical orders, physical mesh selection, duration closure, isolated boundaries and electron/SF acceptance are outside this run. Old physical validation meshes remain inspected evidence; revised physical fits need fresh physical validation. No negative result or prior threshold is replaced.</p></html>'''
    (out/'REPORT.html').write_text(text)
    (out/'SUMMARY.md').write_text('# Observer calibration\n\n'+json.dumps(record['finished_at'])+'\n\nStatus: **complete_pending_review**.\n\n'+ '\n'.join(f"- {a['parameters']['field']} N{a['parameters']['nodes']}: reference={a['reference_empirical_pass']}; uniform={a['uniform_observer_pass']}; prediction={a['fresh_prediction_pass']}; original 33-node max difference={a['original_33_max_difference_from_reference']:.6g}." for a in record['anchors'])+'\n\nFull physical fields remain unchanged in the source run. No new physical evolution or Qx acceptance.\n')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
    for ax,a in zip(axes.flat,record['anchors']):
        for key in RESPONSES:
            values=[max(abs(v[key]-a['reference'][key]),1e-16) for v in a['development']]
            ax.plot([v['observer_nodes'] for v in a['development']],values,'o-',label=key.replace('_observed_error','').replace('_error',''))
        ax.axhline(record['config']['measurement_error_budget'],color='black',ls='--',label='budget');ax.set(yscale='log',xlabel='observer nodes M',ylabel='absolute norm difference',title=a['parameters']['field']+' N'+str(a['parameters']['nodes']));ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=7);fig.savefig(out/'calibration.png',dpi=250);plt.close(fig)
    # Include code/config and original compact source hash, never full arrays.
    for p in Path(__file__).parent.rglob('*.py'):
        dest=out/'code'/p.relative_to(Path(__file__).parent);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    save(out/'record.json',record)
    excluded={'evidence.zip','SHA256SUMS','runner.log','status.json','heartbeat.json','launch.json'}
    paths=[p for p in out.rglob('*') if p.is_file() and p.name not in excluded and p.suffix!='.tmp' and '__pycache__' not in p.parts]
    (out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(out).as_posix()+'\n' for p in sorted(paths)))
    with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths)+[out/'SHA256SUMS']:z.write(p,p.relative_to(out))

def run(repo,source,out,plan_path):
    out.mkdir(parents=True,exist_ok=True);plan=load(plan_path);source_record=load(source/'record.json')
    identity={'source_evidence_sha256':sha(source/'evidence.zip'),'plan_sha256':sha(plan_path),'code_sha256':{p.relative_to(Path(__file__).parent).as_posix():sha(p) for p in Path(__file__).parent.rglob('*.py')},'repo':str(repo),'source':str(source),'threads':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']}}
    if (out/'identity.json').exists():
        if load(out/'identity.json')!=identity:raise ValueError('Changed source/config/code/environment on resume')
    else:save(out/'identity.json',identity)
    record={'recorded_at':load(out/'started.json')['recorded_at'] if (out/'started.json').exists() else stamp(),'status':'working','role':'saved-state-calibration','source_record_id':plan['source_record_id'],'config':plan,'environment':{'python':platform.python_version(),'numpy':np.__version__,'source_environment':source_record['environment'],'source_commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()},'identity':identity,'anchors':[]}
    save(out/'started.json',{'recorded_at':record['recorded_at']});stop=threading.Event()
    def pulse():
        while not stop.wait(15):save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid()})
    thread=threading.Thread(target=pulse,daemon=True);thread.start()
    def interrupted(*args):raise KeyboardInterrupt('Stop requested; resume reuses sealed measurements')
    signal.signal(signal.SIGTERM,interrupted)
    try:
        choices=[]
        for file in (source/'cases').glob('*.json'):
            c=load(file);p=c['parameters']
            if p['field'] in plan['anchors'] and p['nodes'] in plan['anchors'][p['field']] and all(p.get(k)==v for k,v in plan['fixed_parameters'].items()):choices.append((file.stem,c))
        if len(choices)!=6:raise ValueError('Expected six exact matching saved states')
        for cid,c in sorted(choices,key=lambda item:(item[1]['parameters']['field'],item[1]['parameters']['nodes'])):
            save(out/'status.json',{'recorded_at':stamp(),'status':'working','pid':os.getpid(),'current_case':cid,'completed_anchors':len(record['anchors'])})
            field=(source/'fields'/c['state']['file']).resolve()
            if not field.is_relative_to(source.resolve()) or sha(field)!=c['state']['sha256']:raise ValueError('Saved state hash mismatch')
            with zipfile.ZipFile(field) as z:
                if z.testzip() is not None:raise ValueError('Saved state NPZ CRC failure')
            with np.load(field,allow_pickle=False) as arrays:
                E=arrays['E'];B=arrays['B_half']
                if abs(float(arrays['dt'])-c['parameters']['duration']/c['parameters']['steps'])>1e-15 or float(arrays['duration'])!=c['parameters']['duration']:raise ValueError('State time receipt mismatch')
            state=prepare(E,B,c['parameters'],repo,plan['chunk_x']);result=calibrate(state,cid,c,out,plan);save(out/'anchors'/(cid+'.json'),result);record['anchors'].append(result);del state,E,B
            if sha(field)!=c['state']['sha256']:raise ValueError('Source state changed during calibration')
            print(json.dumps({'recorded_at':stamp(),'message':'Anchor complete','case_id':cid,'uniform_pass':result['uniform_observer_pass'],'reference_pass':result['reference_empirical_pass']}),flush=True)
        record.update(status='complete_pending_review',finished_at=stamp());finish(out,record)
        save(out/'status.json',{'recorded_at':stamp(),'status':'complete_pending_review','pid':os.getpid(),'completed_anchors':6,'evidence':str(out/'evidence.zip'),'report':str(out/'REPORT.html')})
    except BaseException as e:
        save(out/'status.json',{'recorded_at':stamp(),'status':'interrupted' if isinstance(e,KeyboardInterrupt) else 'failed','pid':os.getpid(),'error':str(e),'completed_anchors':len(record['anchors'])});traceback.print_exc();raise
    finally:stop.set()
