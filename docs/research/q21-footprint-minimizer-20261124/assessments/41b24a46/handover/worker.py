"""Paired fixed-geometry method experiment with precharged, resumable work."""
import argparse,gc,json,os,signal,sys,threading,time,shutil
from pathlib import Path
import numpy as np
from common import ROOT,load,save,sha,stamp,need,log,host,process_identity,source_endpoint,source_metrics,seal,csv_write,canonical
sys.path.append(str(ROOT/'kernel'))
from engine import Engine
from checkpoints import write_state,read_state
from evaluations import metrics,gate_result,derivative_check,array_sha
from science import footprint,next_batch,response_fits
STOP=threading.Event()

class CallCeiling(Exception):pass

class MeasuredEngine(Engine):
    def __init__(self,backend,folder,method,plan):
        super().__init__(backend,plan['sobolev_shift']);self.folder=folder;self.method=method;self.plan=plan
        self.calls=load(folder/'CALLS.json') if (folder/'CALLS.json').exists() else {'optimizer_energy_gradient_calls':0,'optimizer_energy_gradient_seconds':0.,'interrupted_calls_counted':True}
    def value(self,n,g):
        if self.calls['optimizer_energy_gradient_calls']>=self.plan['maximum_objective_calls_per_arm']:raise CallCeiling('Registered objective-call ceiling reached')
        self.calls['optimizer_energy_gradient_calls']+=1;save(self.folder/'CALLS.json',self.calls)
        self.sync();clock=time.perf_counter()
        try:return super().value(n,g)
        finally:
            self.sync();self.calls['optimizer_energy_gradient_seconds']+=time.perf_counter()-clock;save(self.folder/'CALLS.json',self.calls)
    def step(self,s,g):
        if self.method=='sobolev-descent':
            for key in ['old_g','old_z','direction']:s[key]=None
        result=super().step(s,g)
        if self.method=='sobolev-descent':
            for key in ['old_g','old_z','direction']:s[key]=None
        return result

def load_parent(path,e,method):
    with np.load(path,allow_pickle=False) as z:
        need(int(z['iteration'])==625 and str(z['backend'])=='cpu','Must start from native iteration-625 CPU endpoint')
        s={'alpha':float(z['alpha']),'iteration':int(z['iteration']),'pairs':[]}
        for key in ['n','old_g','old_z','direction']:
            a=z[key];need(a.dtype==np.float64 and np.isfinite(a).all(),'Parent precision/value differs')
            s[key]=e.xp.asarray(a).copy() if a.size and (key=='n' or method=='exact-cg') else None
    need(s['n'].shape==(177,177,177,3),'Primary source geometry differs')
    return s

def replay_close(m,expected):
    for key in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:
        need(np.isclose(m[key],expected[key],rtol=1e-6,atol=1e-10),'Retained measurement replay differs: '+key)

def run_arm(out,source,backend,method,plan,phase,check):
    from electron_field_topology.sf_time import Grid
    folder=out/'cases'/method;folder.mkdir(parents=True,exist_ok=True);g=Grid((177,)*3,(plan['length'],)*3,'fixed')
    e=MeasuredEngine(backend,folder,method,plan);identity={'campaign':load(out/'identity.json'),'method':method,'nodes':177,'length':plan['length'],'backend':backend,'shift':plan['sobolev_shift']}
    ledger=load(folder/'ATTEMPTS.json') if (folder/'ATTEMPTS.json').exists() else []
    need(all(r['attempt']==i+1 and r['precharged'] for i,r in enumerate(ledger)),'Attempt ledger changed')
    cp=folder/'control.json'
    if cp.exists():
        control=load(cp);need(control['identity']==canonical(identity),'Resume identity differs');s=read_state(folder/control['checkpoint'],e,identity)
        history=control['history'];need(control['history_sha256']==canonical(history),'History checksum differs');need(len(ledger)>=control['committed_attempts'],'Attempt ledger truncated')
        m=metrics(e.host(s['n']),g,plan['registered_gates']);replay_close(m,history[-1]['metrics'])
    else:
        s=load_parent(source_endpoint(source,177),e,method);m=metrics(e.host(s['n']),g,plan['registered_gates']);replay_close(m,source_metrics(177))
        history=[{'recorded_at':stamp(),'accepted_updates':0,'native_iteration':625,'charged_attempts':len(ledger),'alpha':s['alpha'],'metrics':m,'gates':gate_result(m,21,plan['registered_gates']),'diagnostics_seconds':0.,'optimizer_calls':e.calls['optimizer_energy_gradient_calls']}]
        write_state(folder/'restart-0.npz',s,e,identity)
        control={'identity':canonical(identity),'checkpoint':'restart-0.npz','slot':0,'committed_attempts':0,'history':history,'history_sha256':canonical(history),'target_attempts':plan['initial_attempts_per_arm'],'reason':None,'best_score':max(m['relative_force_l2']/1e-4,m['acceleration_max']/1e-3)}
        write_state(folder/'best.npz',s,e,identity);save(cp,control)
    # A qualified independent directional check and backend audit precede this arm's first update.
    if not (folder/'QUALIFICATION.json').exists():
        check();phase.update(name='minimizer-qualification',case=method,nodes=177,backend=backend)
        native=e.host(s['n']);q=derivative_check(native,g,{'epsilons':[.001,.0003,.0001],'rtol':.002,'atol':1e-7});need(q['passed'],'Independent constrained energy derivative qualification failed')
        # Audit work is recorded separately from optimization work for a fair comparison.
        auditor=Engine(backend,plan['sobolev_shift']);audit=auditor.audit(s['n'],g);del auditor
        save(folder/'QUALIFICATION.json',{'recorded_at':stamp(),'directional':q,'backend_audit':audit,'qualification_static_gradient_calls':q['energy_gradient_calls']+2,'source_memory_retained':method=='exact-cg','backend_transfer':backend!='cpu','exact_control_scope':'Same inherited algorithm, memory, alpha, restart schedule, action and geometry; CPU preserves source arithmetic backend. CUDA is a separately audited arithmetic transfer.'})
        del native;gc.collect()
    reason=control.get('reason')
    while reason is None and len(ledger)<plan['maximum_attempts_per_arm']:
        check();last=history[-1]
        if not last['gates']['representation']:reason='representation_unresolved';break
        if not last['gates']['boundary_admitted']:reason='boundary_admission_lost';break
        if last['gates']['all_readiness_gates']:reason='all_readiness_gates_measured';break
        if len(ledger)>=control['target_attempts']:
            decision=next_batch(history,plan);decision.update(recorded_at=stamp(),charged_attempts=len(ledger))
            decisions=load(folder/'DECISIONS.json') if (folder/'DECISIONS.json').exists() else [];decisions.append(decision);save(folder/'DECISIONS.json',decisions)
            if not decision['continue']:reason=decision['reason'];break
            control['target_attempts']=min(plan['maximum_attempts_per_arm'],len(ledger)+decision['attempts']);save(cp,control)
        ledger.append({'recorded_at':stamp(),'attempt':len(ledger)+1,'precharged':True});save(folder/'ATTEMPTS.json',ledger)
        phase.clear();phase.update(name='matched-minimizer',case=method,nodes=177,backend=backend,charged_attempts=len(ledger),target_attempts=control['target_attempts'],native_iteration=int(s['iteration']))
        e.sync();clock=time.perf_counter()
        try:accepted,step=e.step(s,g)
        except CallCeiling as exc:reason=str(exc);break
        e.sync();optimizer_seconds=time.perf_counter()-clock
        if not accepted:reason='line_search_stalled';save(folder/'LINE-SEARCH.json',step);break
        clock=time.perf_counter();n=e.host(s['n']);m=metrics(n,g,plan['registered_gates']);diagnostics_seconds=time.perf_counter()-clock
        row={'recorded_at':stamp(),'accepted_updates':last['accepted_updates']+1,'native_iteration':int(s['iteration']),'charged_attempts':len(ledger),'alpha':float(s['alpha']),'metrics':m,'gates':gate_result(m,21,plan['registered_gates']),'optimizer_seconds':optimizer_seconds,'diagnostics_seconds':diagnostics_seconds,'optimizer_calls':e.calls['optimizer_energy_gradient_calls'],'step':step,'native_restart':int(s['iteration'])%200==0}
        row['relative_energy_change']=abs(m['energy']-last['metrics']['energy'])/max(abs(last['metrics']['energy']),1e-300)
        if len(history)>=2:
            for key in ['relative_force_l2','acceleration_max']:
                a,b,c=history[-2]['metrics'][key],last['metrics'][key],m[key]
                if (b-a)*(c-b)<0:row['turning_point_measured']=True
        # Both alternating snapshots remain valid until control.json commits the new state.
        slot=1-control['slot'];name=f'restart-{slot}.npz';write_state(folder/name,s,e,identity);score=max(m['relative_force_l2']/1e-4,m['acceleration_max']/1e-3)
        if score<control['best_score']:write_state(folder/'best.npz',s,e,identity);control['best_score']=score
        history.append(row);control.update(checkpoint=name,slot=slot,committed_attempts=len(ledger),history=history,history_sha256=canonical(history));save(cp,control)
        log('Measured Q21 minimizer update',case=method,charged_attempts=len(ledger),accepted_updates=row['accepted_updates'],force=m['relative_force_l2'],acceleration=m['acceleration_max'])
        del n;gc.collect()
    if reason is None:reason='registered_attempt_ceiling'
    control.update(reason=reason);save(cp,control);write_state(folder/'endpoint.npz',s,e,identity)
    changes=[r['relative_energy_change'] for r in history if 'relative_energy_change' in r][-10:]
    result={'recorded_at':stamp(),'case':method,'backend':backend,'reason':reason,'charged_attempts':len(ledger),'accepted_updates':history[-1]['accepted_updates'],'uncommitted_attempts_not_refunded':len(ledger)-control['committed_attempts'],'history':history,'final':history[-1],'best_retained':{'path':'best.npz','sha256':sha(folder/'best.npz'),'joint_score':control['best_score'],'not_substituted_for_final':True},'calls':e.calls,'diagnostic_static_gradient_calls_minimum':len(history)+load(folder/'QUALIFICATION.json')['qualification_static_gradient_calls'],'diagnostic_call_count_scope':'Includes accepted-state metric evaluations and recorded qualification; restart replay calls are additional. Optimizer calls are separately precharged exactly.','energy_change_comparison':{'final_up_to_10_median':float(np.median(changes)) if changes else None,'updates_below_1e_minus9':sum(v<1e-9 for v in changes),'scope':'Accepted-update diagnostic; different optimizer, not an exact author stopping-rule reproduction and not a readiness gate.'},'fits':response_fits(history,plan),'physical_time_steps':0,'scope':'Fixed-grid algorithm comparison. No independent evidence of physical stability or continuum convergence.'}
    save(folder/'record.json',result);del s,e;gc.collect();return result

def report(out):
    import html
    plan=load(ROOT/'PLAN.json');records=[load(p) for p in sorted((out/'cases').glob('*/record.json'))];maps=[load(p) for p in sorted((out/'footprints').glob('*/FOOTPRINT.json'))]
    rows=[]
    for r in records:
        for h in r['history']:rows.append({'case':r['case'],'accepted_updates':h['accepted_updates'],'native_iteration':h['native_iteration'],'charged_attempts':h['charged_attempts'],'energy':h['metrics']['energy'],'relative_energy_change':h.get('relative_energy_change'),'force':h['metrics']['relative_force_l2'],'acceleration':h['metrics']['acceleration_max'],'tail':h['metrics']['tail_fraction'],'optimizer_calls':h['optimizer_calls'],'alpha':h['alpha'],'optimizer_seconds':h.get('optimizer_seconds',0),'diagnostics_seconds':h['diagnostics_seconds'],'all_readiness_gates':h['gates']['all_readiness_gates']})
    csv_write(out/'MEASUREMENTS.csv',rows)
    # Common-update comparisons supplemented by time and gradient-call coordinates.
    paired=[]
    if len(records)==2:
        by={r['case']:{h['accepted_updates']:h for h in r['history']} for r in records}
        for k in sorted(set(by['exact-cg'])&set(by['sobolev-descent'])):
            a,b=by['exact-cg'][k],by['sobolev-descent'][k];paired.append({'accepted_updates':k,'force_ratio_descent_over_cg':b['metrics']['relative_force_l2']/a['metrics']['relative_force_l2'],'acceleration_ratio_descent_over_cg':b['metrics']['acceleration_max']/a['metrics']['acceleration_max']})
    save(out/'METHOD-COMPARISON.json',{'recorded_at':stamp(),'matched_updates':paired,'factors':'Conjugacy retained versus removed; same Sobolev inverse, shift, line search, alpha policy, restart schedule, field, geometry and gates. Not an exact Hietarinta–Salo reproduction.','winner_automatically_promoted':False,'physical_time_steps':0})
    links=''.join(f'<h2>{html.escape(m["label"])}</h2><p><a href="footprints/{m["label"]}/FOOTPRINT.json">Footprint data</a></p><img src="footprints/{m["label"]}/capture.png"><img src="footprints/{m["label"]}/slices.png">' for m in maps)
    if rows:
        import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
        fig,axs=plt.subplots(2,3,figsize=(14,8))
        for r in records:
            hs=r['history'];elapsed=np.cumsum([h.get('optimizer_seconds',0)+h['diagnostics_seconds'] for h in hs])/3600
            for j,(xs,title) in enumerate([([h['accepted_updates'] for h in hs],'Accepted updates'),([h['optimizer_calls'] for h in hs],'Optimizer energy-gradient calls'),(elapsed,'Measured optimizer + diagnostic hours')]):
                for i,key in enumerate(['relative_force_l2','acceleration_max']):axs[i,j].semilogy(xs,[h['metrics'][key] for h in hs],label=r['case']);axs[i,j].set(xlabel=title,ylabel=key);axs[i,j].axhline([1e-4,1e-3][i],ls='--',color='black')
        axs[0,0].legend();fig.suptitle('Same field and geometry; method-dependent work and progress');fig.tight_layout();fig.savefig(out/'method-curves.png',dpi=180);plt.close(fig);links+='<h2>Method response curves</h2><img src="method-curves.png">'
    status=load(out/'status.json');save(out/'record.json',{'recorded_at':stamp(),**status,'plan':plan,'cases':records,'footprints':[m['label'] for m in maps],'physical_time_steps':0})
    deferrals=[{'stage':'coupled nested-grid evolution and progressive zoom','reason':plan['adaptive_grid_evolution']['reason']}]
    if not (out/'footprints/q2-control/FOOTPRINT.json').exists():deferrals.append({'stage':'Q2 full-field control','reason':'Authenticated Q2 full field unavailable; retained compact control is not a new replay'})
    save(out/'DEFERRALS.json',{'recorded_at':stamp(),'deferrals':deferrals})
    text='# Q21 footprint and minimizer assessment\n\nStatus: **'+status['status']+'**.\n\nThis campaign maps the last CPU endpoints and compares exact continuation with projected Sobolev steepest descent. All original gates remain active. It does not run a cropped-domain or coupled-grid evolution.\n\n'
    for r in records:text+=f'- {r["case"]}: {r["charged_attempts"]} charged attempts, {r["accepted_updates"]} accepted updates; {r["reason"]}.\n'
    text+='\nRead METHOD-COMPARISON.json, DEFERRALS.json and REPORT.html before further allocation. A footprint capture fraction is not a numerical error estimate. No candidate is promoted automatically.\n';(out/'SUMMARY.md').write_text(text)
    (out/'REPORT.html').write_text('<!doctype html><meta charset="utf-8"><title>Q21 footprint and minimizer assessment</title><style>body{font:17px system-ui;max-width:1150px;margin:40px auto;padding:0 20px}img{max-width:100%}</style><h1>Q21 footprint and minimizer assessment</h1><p>'+html.escape(str(stamp()))+'</p><p>Status: '+html.escape(status['status'])+'. No physical-time evolution; coupled-grid evolution remains explicitly deferred.</p><p><a href="record.json">Full record</a> · <a href="MEASUREMENTS.csv">Measurements</a> · <a href="DEFERRALS.json">Deferrals</a></p>'+links+'\n')

def run(repo,out,source,backend):
    from electron_field_topology.sf_time import Grid
    plan=load(ROOT/'PLAN.json');phase={'name':'starting'};done=threading.Event();status='working';error=None
    def heartbeat():
        while not done.is_set():save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid(),'process_identity':process_identity(os.getpid()),'phase':dict(phase)});done.wait(10)
    def check():
        if STOP.is_set() or (out/'STOP.json').exists():raise KeyboardInterrupt('Orderly stop requested')
        if host()['available_gib']<plan['host_reserve_gib']:raise KeyboardInterrupt('Host reserve reached before next task/update; free resources and resume')
    def update():save(out/'status.json',{'recorded_at':stamp(),'status':status,'phase':dict(phase),'error':error,'maximum_optimizer_attempts':plan['maximum_optimizer_attempts'],'physical_time_steps':0})
    def mapped(folder):
        receipt=folder/'COMPLETED.json'
        if not receipt.exists():return False
        for name,digest in load(receipt)['files'].items():need(sha(folder/name)==digest,'Cached footprint output differs: '+str(folder/name))
        return True
    def commit_map(folder):save(folder/'COMPLETED.json',{'recorded_at':stamp(),'files':{p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name!='COMPLETED.json'}})
    signal.signal(signal.SIGTERM,lambda *_:STOP.set());signal.signal(signal.SIGINT,lambda *_:STOP.set());thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    try:
        for nodes in plan['mapping_nodes']:
            check();folder=out/'footprints'/f'q21-{nodes}'
            if mapped(folder):continue
            phase.clear();phase.update(name='read-only-footprint',nodes=nodes);update();path=source_endpoint(source,nodes)
            with np.load(path,allow_pickle=False) as z:n=z['n'].copy();need(int(z['iteration'])==625,'Source iteration differs')
            result=footprint(n,Grid((nodes,)*3,(plan['length'],)*3,'fixed'),folder,f'q21-{nodes}',STOP.is_set);replay_close(result['metrics'],source_metrics(nodes));commit_map(folder);del n;gc.collect()
        spec=load(ROOT/'SOURCE.json');q2=repo/spec['q2_relative'];folder=out/'footprints/q2-control'
        if q2.exists() and not mapped(folder):
            check();need(sha(q2)==spec['q2']['sha256'],'Q2 control hash differs');phase.clear();phase.update(name='q2-control-footprint');update()
            with np.load(q2,allow_pickle=False) as z:n=z[spec['q2']['key']].copy()
            r=footprint(n,Grid((spec['q2']['nodes'],)*3,(spec['q2']['length'],)*3,'fixed'),folder,'q2-control');replay_close(r['metrics'],spec['q2']['expected']);commit_map(folder);del n;gc.collect()
        for method in plan['arms']:
            check();phase.clear();phase.update(name='method-start',case=method,backend=backend);update()
            record=out/'cases'/method/'record.json'
            if not record.exists():run_arm(out,source,backend,method,plan,phase,check)
        # Re-hash the two source endpoints to demonstrate no mutation across the campaign.
        for nodes in plan['mapping_nodes']:source_endpoint(source,nodes)
        status='complete_pending_review';phase.clear();phase.update(name='complete')
    except KeyboardInterrupt as exc:status='interrupted';error=str(exc)
    except Exception as exc:
        import traceback;traceback.print_exc();status='failed';error=repr(exc)
    finally:
        update();report(out)
        fields=[{'path':p.relative_to(out).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((out/'cases').glob('*/*.npz'))]
        save(out/'FIELD-MANIFEST.json',{'recorded_at':stamp(),'fields':fields,'original_full_fields_untouched':True});done.set();thread.join(timeout=12)
        if (out/'telemetry-latest.json').exists():save(out/'TELEMETRY-FROZEN.json',load(out/'telemetry-latest.json'))
        seal(out);log('Q21 assessment campaign finished',status=status,output=str(out),evidence=str(out/'evidence.zip'))
    return 0 if status in ['complete_pending_review','interrupted'] else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-run',type=Path,required=True);p.add_argument('--backend',choices=['cpu','cuda'],required=True);a=p.parse_args();raise SystemExit(run(a.repo,a.output,a.source_run,a.backend))
