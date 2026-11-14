"""Seven fixed-configuration continuation jobs; no automatic mesh or motion run."""
import json,os,shutil,signal,threading,time,traceback,zipfile,csv,base64,io,html
from pathlib import Path
import numpy as np
from electron_field_topology.rapid_q_screen.engine import checkpoint,restore
from electron_field_topology.rapid_q_screen.runner import branch,sealed,metrics
from .common import load,save,sha,stamp,log,memory_guard
from .audit import receipt_identity,backend,load_job,load_plan
from .relationships import fits

def report(out,record):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows=[]
    for result in record['jobs']:
        m=result['metrics'];job=result['job'];rows.append({'seed':job['id'],'source':job['source'],'priority':job['priority'],'nodes':job['nodes'],'start_iteration':job['start_iteration'],'final_iteration':result['iteration'],'additional_steps':result['iteration']-job['start_iteration'],'allocation_status':result['allocation_status'],'measured_decision':result['classification']['decision'],'force':m['relative_force_l2'],'acceleration':m['acceleration_max'],'tail_fraction':m['tail_fraction']})
    with (out/'measurements.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    fig,axes=plt.subplots(4,2,figsize=(12,13),layout='constrained')
    for ax,result in zip(axes.flat,record['jobs']):
        job=result['job'];h=[v for v in result['history'] if v['iteration']>=job['start_iteration']];x=[v['iteration']-job['start_iteration'] for v in h]
        ax.semilogy(x,[v['relative_force_l2']/1e-4 for v in h],'-o',markersize=2,label='force / gate');ax.semilogy(x,[v['acceleration_max']/1e-3 for v in h],'-s',markersize=2,label='acceleration / gate');ax.axhline(1,color='green',linestyle='--');ax.set_title(job['id']);ax.set_xlabel('Additional accepted optimizer steps');ax.set_ylabel('Measured value / gate');ax.grid(alpha=.2)
    axes.flat[0].legend(fontsize=8)
    for ax in list(axes.flat)[len(record['jobs']):]:ax.set_visible(False)
    fig.suptitle('Fixed-configuration follow-up — static model units, not physical time');fig.savefig(out/'histories.png',dpi=145);plt.close(fig)
    table='<table><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in rows[0])+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row.values())+'</tr>' for row in rows)+'</table>'
    text='<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rapid Q bounded follow-up</title><style>body{font:15px/1.6 system-ui;margin:25px}table{border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}img{max-width:100%}.wide{overflow:auto}</style><h1>Rapid Q bounded follow-up</h1><p>'+html.escape(json.dumps(record['finished_at']))+'</p><p>'+html.escape(json.dumps(record['counts']))+'</p><p>Completed preparation budgets are distinct from measured static eligibility. No Q sector is rejected. Original gates, seed, geometry, optimizer and tail criterion remain fixed. Legacy Q4/Q7 imports explicitly restart conjugacy; other jobs continue the exact parent optimizer state and adaptive schedule.</p><p><a href="record.json">Full record</a> · <a href="measurements.csv">Measurements</a> · <a href="relationships.json">Curve checks</a> · <a href="static-readiness-queue.json">Conditional refinement queue</a> · <a href="audit.json">Local field/device audit</a></p><div class="wide">'+table+'</div><img src="histories.png" alt="Force and acceleration versus additional optimizer iterations"><p>Values at or below one in both curves are necessary stationarity gates. Static readiness still requires representation, unit and tail checks. No new motion or continuum-stability claim follows. Curve fits are retrospective within-configuration descriptions, not threshold-crossing predictions.</p></html>'
    (out/'REPORT.html').write_text(text);(out/'SUMMARY.md').write_text('# Rapid Q bounded follow-up\n\n'+json.dumps(record['finished_at'])+'\n\nStatus: **complete_pending_review**.\n\n'+json.dumps(record['counts'])+'\n\nAll original gates retained. No automatic mesh refinement or motion.\n')

def initialize(job,screen,past,screen_run,past_run,engine,folder,outer):
    g,state,parent_identity,history,kind=load_job(job,screen,past,screen_run,past_run,engine);folder.mkdir(parents=True,exist_ok=True)
    if parent_identity is not None:
        source=(screen_run/job['checkpoint']).parent
        for name in ['latest.npz','latest.seal.json','history.json']:shutil.copy2(source/name,folder/name)
        shutil.copy2(source/'latest.npz',folder/'followup-start.npz');identity=screen['record.json']['identity']
    else:
        identity={**outer,'legacy_parent_sha256':job['checkpoint_sha256'],'legacy_optimizer_restart':True};full={**identity,'seed':job['seed'],'shape':list(g.shape),'lengths':list(g.lengths),'backend':engine.kind};checkpoint(folder/'latest.npz',state,engine,full);shutil.copy2(folder/'latest.npz',folder/'followup-start.npz');shutil.copy2(past_run/job['checkpoint'],folder/'legacy-source.npz');m=metrics(engine.host(state['n']),g,screen['record.json']['plan']);save(folder/'history.json',[{'recorded_at':stamp(),'iteration':state['iteration'],'legacy_optimizer_restart':True,**m}])
    meta={'recorded_at':stamp(),'job':job,'branch_identity':identity,'continuation_mode':kind,'parent_sha256':job['checkpoint_sha256'],'outer_identity':outer};save(folder/'import.json',meta);(folder/'import.json.sha256').write_text(sha(folder/'import.json')+'\n');del state
    return g,identity

def run(repo,screen_run,past_run,out,audit_receipt):
    from runtime import ROOT,CFG,verify_inputs
    plan=load(ROOT/'FOLLOWUP.json');memory_guard(plan['memory_min_available_gib']);screen,past,jobs=verify_inputs(screen_run,past_run,full=False);audit=load(audit_receipt);outer=receipt_identity(repo,screen_run,past_run)
    if audit.get('status')!='local_field_and_backend_audit_passed' or audit.get('identity')!=outer or sha(audit_receipt)!=audit_receipt.with_suffix('.json.sha256').read_text().strip():raise ValueError('Missing/changed/stale local field and backend audit')
    out.mkdir(parents=True,exist_ok=True)
    if (out/'identity.json').exists():
        if load(out/'identity.json')!=outer:raise ValueError('Follow-up identity changed on resume')
    else:save(out/'identity.json',outer)
    if not (out/'audit.json').exists():shutil.copy2(audit_receipt,out/'audit.json')
    if sha(out/'audit.json')!=sha(audit_receipt):raise ValueError('Copied audit receipt changed')
    started=load(out/'started.json') if (out/'started.json').exists() else {'recorded_at':stamp()};save(out/'started.json',started);finished=[];stop=threading.Event()
    def pulse():
        while not stop.wait(15):save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid()})
    def interrupted(*_):raise KeyboardInterrupt('Graceful follow-up stop requested')
    signal.signal(signal.SIGTERM,interrupted);threading.Thread(target=pulse,daemon=True).start()
    try:
        for job in jobs:
            folder=out/'jobs'/job['id'];summary=folder/'job-summary.json'
            if summary.exists():
                item=sealed(summary)
                if sha(out/item['checkpoint'])!=item['checkpoint_sha256']:raise ValueError('Completed job field changed')
                finished.append(item);continue
            if shutil.disk_usage(out).free<plan['disk_reserve_gib']*1024**3:raise RuntimeError('Disk reserve reached; parent and continuation fields retained')
            engine=backend(screen['benchmark.json'],job['nodes'])
            if (folder/'import.json').exists():
                meta=sealed(folder/'import.json')
                if meta['outer_identity']!=outer or meta['job']!=job:raise ValueError('Job import provenance changed')
                from electron_field_topology.sf_time import Grid
                g=Grid((job['nodes'],)*3,(job['length'],)*3,'fixed');identity=meta['branch_identity']
            else:g,identity=initialize(job,screen,past,screen_run,past_run,engine,folder,outer)
            # Targets are fixed before execution. A restart revisits cached batch
            # results, then resumes the exact last sealed optimizer checkpoint.
            targets=range(job['start_iteration']+plan['batch_steps'],job['start_iteration']+job['additional_steps']+1,plan['batch_steps']);allocation='budget_exhausted_unresolved';result=None
            for target in targets:
                save(out/'status.json',{'recorded_at':stamp(),'status':'working','pid':os.getpid(),'phase':job['priority'],'seed':job['id'],'batch_target_iteration':target,'job_additional_budget':job['additional_steps'],'completed_jobs':len(finished)})
                result=branch(job['seed'],g,engine,target,out,folder,screen['record.json']['plan'],identity)
                log('Bounded follow-up batch completed',seed=job['id'],iteration=result['iteration'],added_steps=result['iteration']-job['start_iteration'],force=result['metrics']['relative_force_l2'],acceleration=result['metrics']['acceleration_max'])
                decision=result['classification']['decision']
                if decision=='static_survivor':allocation='measured_static_survivor_pending_mesh_confirmation';break
                if decision=='boundary_followup':allocation='measured_stationary_boundary_followup';break
                if decision=='refine_representation':allocation='deferred_representation_loss';break
                if result['reason'] or result['iteration']<target:allocation='deferred_solver_stall';break
            item={**result,'job':job,'continuation_mode':load(folder/'import.json')['continuation_mode'],'allocation_status':allocation,'whole_Q_rejected':False};sealed(summary,item);finished.append(item);del engine
        queue=[{'seed':v['job']['id'],'q':v['q'],'checkpoint':v['checkpoint'],'checkpoint_sha256':v['checkpoint_sha256'],'status':'pending_same_box_mesh_confirmation_then_boost_and_motion_admission'} for v in finished if v['classification']['decision']=='static_survivor'];save(out/'static-readiness-queue.json',{'recorded_at':stamp(),'candidates':queue,'automatic_mesh_refinement':False,'motion_execution':False})
        relationships={v['job']['id']:fits(v['history'],v['job']['start_iteration']) for v in finished};save(out/'relationships.json',{'recorded_at':stamp(),'branches':relationships})
        record={**started,'status':'complete_pending_review','finished_at':stamp(),'identity':outer,'plan':plan,'jobs':finished,'counts':{'jobs':len(finished),'additional_steps':sum(v['iteration']-v['job']['start_iteration'] for v in finished),'maximum_additional_steps':plan['total_additional_step_budget'],'static_readiness':len(queue),'hard_Q_rejections':0,'motion_cases':0},'parent_run_unchanged':True};save(out/'record.json',record);report(out,record)
        shutil.copytree(ROOT/'science',out/'code',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'));shutil.copy2(ROOT/'FOLLOWUP.json',out/'FOLLOWUP.json')
        fields=[{'path':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.rglob('*.npz')];save(out/'field-manifest.json',{'recorded_at':stamp(),'files':fields,'scope':'Full states remain local until separately archived and verified; compact ZIP excludes all NPZ files'})
        payload=[f for f in out.rglob('*') if f.is_file() and f.suffix not in ['.npz','.tmp'] and f.name not in ['SHA256SUMS','evidence.zip','status.json','heartbeat.json','launch.json','runner.log']];(out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.relative_to(out).as_posix()+'\n' for f in sorted(payload)))
        with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in sorted(payload)+[out/'SHA256SUMS']:z.write(f,f.relative_to(out))
        save(out/'status.json',{'recorded_at':stamp(),'status':'complete_pending_review','pid':os.getpid(),'counts':record['counts'],'evidence':str(out/'evidence.zip'),'report':str(out/'REPORT.html')})
    except BaseException as e:
        save(out/'status.json',{'recorded_at':stamp(),'status':'interrupted' if isinstance(e,KeyboardInterrupt) else 'failed','pid':os.getpid(),'error':str(e)});traceback.print_exc();raise
    finally:stop.set()
