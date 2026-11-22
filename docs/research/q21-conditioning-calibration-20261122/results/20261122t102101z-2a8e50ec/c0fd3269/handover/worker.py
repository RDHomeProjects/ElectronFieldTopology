"""Bounded, restartable one-factor calibration; no physical-time integration."""
import argparse,fcntl,gc,os,signal,sys,threading,traceback
from pathlib import Path
import numpy as np
from common import ROOT,load,save,sha,canonical,stamp,need,log,verify_manifest
from integrity import authenticate,read_parent,source_run,verify_sources,reserves,process_identity
from evaluations import metrics,gate_result,derivative_check
from engine import Engine
from cases import run_case,charge_count
from fitting import curves,next_sample,select,acceptable,response
from diagnostics import audit
from reporting import render,seal
STOP=threading.Event()

def sample(record):
    cfg=record['case'];return {'case':cfg['id'],'shift':cfg['shift'],'log2_shift':cfg['log2_shift'],'response':record['response'],'all_readiness_gates':record['history'][min(30,len(record['history'])-1)]['gates']['all_readiness_gates'],'charged_attempts':record['charged_attempts']}

def campaign(out,parent,g,backend,phase,update,case_runner=run_case):
    """Frozen proposals, then matched trials; resumes preserve every ledger."""
    p=load(ROOT/'PLAN.json');records={};samples=[]
    def run(cfg,horizon):
        if STOP.is_set() or (out/'STOP.json').exists():raise KeyboardInterrupt('Orderly pause between cases')
        phase.clear();phase.update(name='case',case=cfg['id'],shift=cfg['shift'],horizon=horizon)
        r=case_runner(out,parent,g,cfg,horizon,backend,STOP.is_set,phase);records[cfg['id']]=r;update();return r
    cfg={'id':'exact-control','shift':.25,'start':'exact','max_attempts':p['exact_control_attempts']}
    run(cfg,p['exact_control_attempts'])
    baseline_cfg=None
    for i,x in enumerate(p['initial_log2_values']):
        baseline=x==-2;cfg={'id':'scan-baseline' if baseline else f'scan-{i:02d}','shift':2.**x,'log2_shift':x,'start':'restart','max_attempts':120 if baseline else p['measurement_attempts'],'design':'registered_initial_measurement'}
        if baseline:baseline_cfg=cfg
        r=run(cfg,p['measurement_attempts']);samples.append(sample(r));save(out/'SAMPLES.json',samples);update()
    path=out/'ADAPTIVE-PROPOSALS.json';proposals=load(path) if path.exists() else []
    for i in range(p['maximum_adaptive_samples']):
        if i<len(proposals):proposal=proposals[i]
        else:
            proposal=next_sample(samples,p)
            if proposal is None:break
            proposals.append(proposal);save(path,proposals)
        cfg={'id':f'adaptive-{i:02d}','shift':proposal['shift'],'log2_shift':proposal['log2_shift'],'start':'restart','max_attempts':p['measurement_attempts'],'design':proposal['reason']}
        r=run(cfg,p['measurement_attempts']);samples.append(sample(r));save(out/'SAMPLES.json',samples);update()
    fit=curves(samples,p);save(out/'CURVE-FITS.json',fit)
    selection=select(samples,p)
    if (out/'SELECTION.json').exists():need(load(out/'SELECTION.json')==selection,'Selection differs after restart')
    else:save(out/'SELECTION.json',selection)
    validation={'allocated':False,'reason':'No supported joint improvement; unused budget is not consumed'}
    if selection['mode']!='no_supported_improvement':
        cfg={'id':'optimal-validation','shift':selection['shift'],'log2_shift':selection['log2_shift'],'start':'restart','max_attempts':p['validation_candidate_attempts'],'design':'independent_restart_of_selected_value'}
        trial=run(cfg,p['measurement_attempts']);base=next(s for s in samples if s['case']=='scan-baseline');qualified=trial['history'][min(30,len(trial['history'])-1)]['gates']['all_readiness_gates'] or (trial['response']['eligible'] and base['response']['eligible'] and acceptable(trial['response'],base['response'],p))
        decision={'recorded_at':stamp(),'qualified_for_longer_comparison':bool(qualified),'candidate_measured_response':trial['response'],'baseline_matched_response':base['response'],'actual_readiness':trial['history'][min(30,len(trial['history'])-1)]['gates']['all_readiness_gates'],'prediction_grants_admission':False}
        dp=out/'VALIDATION-DECISION.json'
        if dp.exists():
            prior=load(dp);need({k:v for k,v in prior.items() if k!='recorded_at'}=={k:v for k,v in decision.items() if k!='recorded_at'},'Measured qualification changed after restart');decision=prior
        else:save(dp,decision)
        validation={'allocated':True,'trial':decision,'longer_comparison_allocated':bool(qualified)}
        if qualified:
            baseline=run(baseline_cfg,p['validation_baseline_total_attempts']);candidate=run(cfg,p['validation_candidate_attempts'])
            equal=baseline['accepted_steps']==candidate['accepted_steps']==120
            validation['longer_comparison']={'matched_accepted_horizon':equal,'baseline_final':baseline['final'],'candidate_final':candidate['final'],'baseline_final_window':baseline['final_window'],'candidate_final_window':candidate['final_window'],'interpretation':'Compare120 accepted updates only if both reached120. Earlier scientific stops are reported explicitly; do not compare unequal horizons as a matched optimum.'}
    save(out/'VALIDATION.json',validation)
    return {'cases':list(records.values()),'samples':samples,'fits':fit,'selection':selection,'validation':validation}

def case_records(out):
    """Include committed updates from an interrupted, not-yet-ended case."""
    result=[];p=load(ROOT/'PLAN.json')
    for folder in sorted((out/'cases').glob('*')):
        if not folder.is_dir():continue
        record=load(folder/'record.json') if (folder/'record.json').exists() else None
        if (folder/'control.json').exists():
            c=load(folder/'control.json');charged=len(load(folder/'attempt-ledger.json')) if (folder/'attempt-ledger.json').exists() else 0
            if record is None or len(c['history'])>len(record['history']):
                record={'case':load(folder/'CASE.json'),'status':'partial_committed_checkpoint','reason':'Case endpoint not yet sealed; latest committed restart state is retained','charged_attempts':charged,'accepted_steps':c['history'][-1]['accepted_step'],'history':c['history'],'response':response(c['history'],p),'final':c['history'][-1],'best_retained':c['best'],'checkpoint':c['checkpoint'],'endpoint':None,'physical_time_steps':0}
            else:record['charged_attempts']=charged
        if record is not None:result.append(record)
    return result

def execute(repo,out):
    from electron_field_topology.sf_time import Grid
    verify_manifest(ROOT);verify_sources(repo);receipt=authenticate(repo);spec=load(ROOT/'SOURCE.json');p=load(ROOT/'PLAN.json');identity=load(out/'identity.json')
    need(identity['package_sha256']==sha(ROOT/'SHA256SUMS') and identity['source_evidence_sha256']==receipt['evidence_sha256'],'Campaign package/source differs')
    parent=read_parent(receipt['endpoint']);g=Grid(tuple(spec['shape']),tuple(spec['lengths']),'fixed');backend=identity['backend'];phase={'name':'source-replay'};finished=threading.Event();status='working';error=None;result={}
    def beat():
        while not finished.is_set():save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid(),'process_identity':process_identity(os.getpid()),'operation':dict(phase)});finished.wait(15)
    thread=threading.Thread(target=beat,daemon=True);thread.start()
    def update(final=False):
        cases=case_records(out);charged=charge_count(out);need(charged<=p['maximum_new_optimizer_attempts'],'Campaign attempt ceiling exceeded')
        record={'recorded_at':stamp(),'status':status,'phase':dict(phase),'error':error,'source':receipt,'backend':backend,'charged_optimizer_attempts':charged,'maximum_optimizer_attempts':580,'unused_attempt_budget':580-charged,'physical_time_steps':0,'cases':cases,'samples':load(out/'SAMPLES.json') if (out/'SAMPLES.json').exists() else [],'fits':load(out/'CURVE-FITS.json') if (out/'CURVE-FITS.json').exists() else {},'selection':load(out/'SELECTION.json') if (out/'SELECTION.json').exists() else {},'validation':load(out/'VALIDATION.json') if (out/'VALIDATION.json').exists() else {},'residual_audit':load(out/'RESIDUAL-AUDIT.json') if (out/'RESIDUAL-AUDIT.json').exists() else {},'deferred':['Physical-time motion and long-term stability require subsequent admission and numerical checks.','Changing the continuum action, adding a mass/isospin/current or changing the seed family requires a separate registered campaign.','Q22 historical exact-field recovery remains separately documented; this campaign changes no Q22 fields.'],'physical_Q_rejection':False}
        save(out/'record.json',record);save(out/'status.json',{k:record[k] for k in ['recorded_at','status','phase','error','charged_optimizer_attempts','maximum_optimizer_attempts','unused_attempt_budget','physical_time_steps']});render(out,record)
        if final:seal(out)
    try:
        reserves(out);m=metrics(parent['n'],g,p['registered_gates'])
        for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(m[k],spec['expected_metrics'][k],rtol=1e-6,atol=1e-10),'Parent replay differs: '+k)
        save(out/'SOURCE-REPLAY.json',{'recorded_at':stamp(),'metrics':m,'gates':gate_result(m,21,p['registered_gates']),'source_sha256':receipt['endpoint_sha256']})
        with np.load(receipt['q2'],allow_pickle=False) as z:q2=z[spec['q2']['key']].copy()
        qg=Grid((spec['q2']['nodes'],)*3,(spec['q2']['length'],)*3,'fixed');qm=metrics(q2,qg,p['registered_gates']);need(gate_result(qm,2,p['registered_gates'])['all_readiness_gates'],'Q2 control failed')
        save(out/'Q2-CONTROL.json',{'recorded_at':stamp(),'metrics':qm,'gates':gate_result(qm,2,p['registered_gates'])});del q2;gc.collect();update()
        if not (out/'RESIDUAL-AUDIT.json').exists():
            phase.update(name='read-only-localized-residual-audit');e=Engine(backend['selected']);need(e.kind!='cuda' or e.port.identity()==backend['device'],'Backend device changed')
            check=derivative_check(parent['n'],g,{'epsilons':[.001,.0003,.0001],'rtol':.002,'atol':1e-7});save(out/'DERIVATIVE-CHECK.json',check);need(check['passed'],'Directional-derivative instrument failed')
            save(out/'RESIDUAL-AUDIT.json',audit(parent['n'],g,e,p['read_only_hessian_epsilons']));save(out/'RESIDUAL-AUDIT.seal.json',{'sha256':sha(out/'RESIDUAL-AUDIT.json')});del e;gc.collect()
        else:need(load(out/'RESIDUAL-AUDIT.seal.json')['sha256']==sha(out/'RESIDUAL-AUDIT.json'),'Read-only diagnostic changed')
        result=campaign(out,parent,g,backend,phase,update);authenticate(repo);verify_sources(repo);status='complete_pending_review';phase.clear();phase.update(name='complete');update(True)
    except BaseException as exc:
        error=str(exc);resource=isinstance(exc,MemoryError) or any(t in str(exc).lower() for t in ['reserve reached','outofmemory','out of memory']);status='interrupted' if isinstance(exc,KeyboardInterrupt) or resource else 'failed';update(True)
        if status=='failed':traceback.print_exc();raise
    finally:finished.set();thread.join(timeout=2)

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.repo/'src'));signal.signal(signal.SIGTERM,lambda *_:STOP.set());signal.signal(signal.SIGINT,lambda *_:STOP.set())
    with (source_run(a.repo)/'.worker.lock').open('r') as old,(a.output/'.worker.lock').open('a') as new:
        fcntl.flock(old,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(new,fcntl.LOCK_EX|fcntl.LOCK_NB);execute(a.repo,a.output)
if __name__=='__main__':main()
