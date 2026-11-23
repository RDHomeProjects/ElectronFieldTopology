"""Read-only retained-field triage, followed by a one-factor Q21 mesh pilot."""
import argparse,fcntl,gc,json,signal,sys,threading,time,traceback
from pathlib import Path
import numpy as np
from common import ROOT,load,save,sha,stamp,need,log,verify_manifest,canonical
from integrity import authenticate,read_parent,verify_sources,reserves,process_identity
from engine import Engine
from evaluations import metrics,gate_result,array_sha,derivative_check
from measurements import localized,core_persists
from resources import geometry_budget
from relationships import window,better,acquire,propose_supported,fit_curve,spatial_comparison
from cases import run_case,charge_count
from reporting import render,seal
import bulk
STOP=threading.Event()

def records(out):
    result=[]
    for folder in sorted((out/'cases').glob('*')):
        if not folder.is_dir():continue
        r=load(folder/'record.json') if (folder/'record.json').exists() else None
        if (folder/'control.json').exists():
            c=load(folder/'control.json');cfg=load(folder/'CASE.json');last=c['history'][-1]
            if r is None or last['iteration']>r['final']['iteration']:
                r={'case':cfg,'shape':[cfg['nodes']]*3,'lengths':[30.72]*3,'spacing':[30.72/(cfg['nodes']-1)]*3,'status':'partial_committed_checkpoint','accepted_steps':last['accepted_step'],'charged_attempts':len(load(folder/'attempt-ledger.json')) if (folder/'attempt-ledger.json').exists() else 0,'history':c['history'],'final':last,'best_retained':c['best']}
        if r is not None:result.append(r)
    return result
def responses(cases,horizon):
    result=[]
    for r in cases:
        if r['case']['start']=='exact':continue
        w=window(r['history'],horizon)
        if w.get('eligible'):result.append({'nodes':r['case']['nodes'],'spacing':r['spacing'][0],**w})
    return result

def mesh_campaign(out,p,trial,deferrals=None):
    deferrals=[] if deferrals is None else deferrals
    trial(129,'exact',80)
    for nodes in p['grid_nodes']:trial(nodes,horizon=80)
    proposals=load(out/'ADAPTIVE-MESHES.json') if (out/'ADAPTIVE-MESHES.json').exists() else []
    for i in range(p['maximum_adaptive_meshes']):
        points=responses(records(out),80);used=[r['case']['nodes'] for r in records(out) if r['case']['start']!='exact'];blocked=[d.get('admission',{}).get('nodes') for d in deferrals]
        if i<len(proposals):proposal=proposals[i]
        else:
            proposal,fits=propose_supported(points,used+blocked,p)
            if proposal is None:
                nodes=acquire(points,used,p,blocked)
                if nodes is None:break
                proposal={'nodes':nodes,'kind':'measured_slope_change_or_gap_sampling_no_optimum_claim','admission_granted':False}
            proposals.append(proposal);save(out/'ADAPTIVE-MESHES.json',proposals)
        trial(proposal['nodes'],horizon=80)
    rr=records(out);points=responses(rr,80);save(out/'CURVE-FITS.json',{'recorded_at':stamp(),'matched_horizon':80,'parameter':'spacing at fixed box30.72','responses':points,'fits':{k:fit_curve(points,k,p) for k in ['joint','force','acceleration']},'optimum_established':False})
    base=next((r for r in rr if r['case']['id']=='mesh-129'),None);eligible=[]
    if base is not None:
        for r in rr:
            if r['case']['start']=='exact' or r['case']['nodes']==129:continue
            if all(better(window(r['history'],h),window(base['history'],h),p) for h in [30,80]):eligible.append(r)
    selection={'recorded_at':stamp(),'mode':'no_persistent_measured_joint_benefit','admission_granted':False}
    if eligible:
        chosen=min(eligible,key=lambda r:window(r['history'],80)['joint']);selection.update(mode='persistent_measured_value_for_longer_matched_confirmation',nodes=chosen['case']['nodes']);save(out/'SELECTION.json',selection)
        trial(129,horizon=120);trial(chosen['case']['nodes'],horizon=120)
    else:save(out/'SELECTION.json',selection)
    save(out/'SPATIAL-COMPARISON.json',spatial_comparison(records(out),p))
    return selection

def execute(repo,out):
    from electron_field_topology.sf_time import Grid
    verify_manifest(ROOT);verify_sources(repo);receipt=authenticate(repo);spec=load(ROOT/'SOURCE.json');p=load(ROOT/'PLAN.json');identity=load(out/'identity.json');need(identity['package_sha256']==sha(ROOT/'SHA256SUMS'),'Run package identity differs')
    parent=read_parent(receipt['endpoint']);g=Grid((129,)*3,(30.72,)*3,'fixed');backend=identity['backend'];phase={'name':'final-parent-replay'};finished=threading.Event();status='working';error=None;deferrals=[];began=time.perf_counter()
    def beat():
        while not finished.is_set():save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid(),'process_identity':process_identity(os.getpid()),'operation':dict(phase)});finished.wait(15)
    import os
    thread=threading.Thread(target=beat,daemon=True);thread.start()
    def update(final=False):
        rec={'recorded_at':stamp(),'status':status,'phase':dict(phase),'error':error,'source':receipt,'backend':backend,'charged_optimizer_attempts':charge_count(out),'maximum_optimizer_attempts':720,'physical_time_steps':0,'cases':records(out),'deferrals':deferrals,'elapsed_seconds':time.perf_counter()-began,'physical_Q_rejection':False,'next_method_experiment':'Deferred pending review of core-resolution findings; no new model or optimizer policy is silently substituted'}
        save(out/'record.json',rec);save(out/'status.json',{k:rec[k] for k in ['recorded_at','status','phase','error','charged_optimizer_attempts','maximum_optimizer_attempts','physical_time_steps','deferrals']});render(out,rec)
        if final:
            if (out/'telemetry-latest.json').exists():save(out/'TELEMETRY-FROZEN.json',load(out/'telemetry-latest.json'))
            seal(out)
    def diagnostic(label,path,expected):
        dest=out/(label+'.json')
        if dest.exists():need(load(dest)['source_sha256']==expected,'Diagnostic source identity differs');return load(dest)
        phase.clear();phase.update(name='read-only-final-field-diagnosis',source=label)
        with np.load(path,allow_pickle=False) as z:n=z['n'].copy();native_iteration=int(z['iteration'])
        before=array_sha(n);clock=time.perf_counter();m=metrics(n,g,p['registered_gates']);result={'recorded_at':stamp(),'source':str(path),'source_sha256':expected,'native_iteration':native_iteration,'metrics':m,'gates':gate_result(m,21,p['registered_gates']),'metrics_seconds':time.perf_counter()-clock,'localized':localized(n,g),'source_modified':False,'optimizer_attempts':0,'physical_time_steps':0}
        need(before==array_sha(n) and sha(path)==expected,'Diagnostic changed source');save(dest,result);del n;gc.collect();return result
    def trial(nodes,start='restart',horizon=80):
        cfg={'id':'exact-control' if start=='exact' else 'mesh-%03d'%nodes,'nodes':nodes,'start':start,'shift':.25,'max_attempts':80 if start=='exact' else 120}
        admission=geometry_budget(nodes,backend['selected'])
        if not admission['passed']:
            d={'case':cfg['id'],'reason':'resource_geometry_deferred','admission':admission};deferrals.append(d);save(out/'DEFERRED-GEOMETRIES.json',deferrals);update();return None
        r=run_case(out,parent,g,cfg,horizon,backend,STOP.is_set,phase);update();return r
    try:
        reserves(out);need(backend['selected'] in ['cpu','cuda'],'Explicit runtime backend required')
        with np.load(receipt['q2'],allow_pickle=False) as z:q2=z[spec['q2']['key']].copy()
        qm=metrics(q2,Grid((spec['q2']['nodes'],)*3,(spec['q2']['length'],)*3,'fixed'),p['registered_gates']);need(gate_result(qm,2,p['registered_gates'])['all_readiness_gates'],'Q2 unchanged control failed');save(out/'Q2-CONTROL.json',{'recorded_at':stamp(),'metrics':qm,'gates':gate_result(qm,2,p['registered_gates']),'source_sha256':spec['q2']['sha256'],'source_modified':False});del q2;gc.collect()
        final=diagnostic('FINAL-BASELINE-REPLAY',receipt['endpoint'],spec['endpoint_sha256'])
        for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(final['metrics'][k],spec['expected_metrics'][k],rtol=1e-6,atol=1e-10),'Final baseline replay differs: '+k)
        need(final['gates']['representation'] and final['gates']['boundary_admitted'],'Declared parent no longer admitted for relaxation')
        diagnostic('EARLIER-BEST-COMPARISON',receipt['best'],spec['best']['sha256']);diagnostic('SELECTED-SHIFT-CONTRAST',receipt['contrast'],spec['contrast']['sha256'])
        if not (out/'DERIVATIVE-CHECK.json').exists():save(out/'DERIVATIVE-CHECK.json',derivative_check(parent['n'],g,{'epsilons':[.001,.0003,.0001],'rtol':.002,'atol':1e-7}))
        need(load(out/'DERIVATIVE-CHECK.json')['passed'],'Directional derivative qualification failed');update()
        bulk.run(repo.parent,out,receipt,STOP.is_set,phase,update);update()
        decision={'recorded_at':stamp(),'core_localization_persists':core_persists(final['localized'],p),'parent_all_readiness_gates':final['gates']['all_readiness_gates'],'rule':'Only continue the mesh pilot if core localization persists and the final parent remains unresolved'};save(out/'PILOT-DECISION.json',decision)
        if decision['parent_all_readiness_gates'] or not decision['core_localization_persists']:
            deferrals.append({'case':'resolution_pilot','reason':'No unresolved core-dominated parent under the registered decision rule'});save(out/'CURVE-FITS.json',{'status':'deferred_no_resolution_pilot','optimum_established':False});save(out/'SPATIAL-COMPARISON.json',{'status':'deferred_no_resolution_pilot','convergence_certified':False})
        else:
            selection=mesh_campaign(out,p,trial,deferrals)
            # Replay measured final candidate fields only; no earlier best state substitution.
            for r in records(out):
                if r['case']['id'] in ['mesh-129','mesh-%03d'%selection.get('nodes',-1)]:
                    gg=Grid(tuple(r['shape']),tuple(r['lengths']),'fixed');path=out/'cases'/r['case']['id']/'endpoint.npz'
                    with np.load(path,allow_pickle=False) as z:n=z['n'].copy()
                    save(path.parent/'FINAL-LOCALIZATION.json',localized(n,gg));del n;gc.collect()
        authenticate(repo);verify_sources(repo);status='complete_pending_review';phase.clear();phase.update(name='complete');update(True)
    except BaseException as exc:
        error=str(exc);resource=isinstance(exc,MemoryError) or any(x in error.lower() for x in ['reserve reached','out of memory','outofmemory']);status='interrupted' if isinstance(exc,KeyboardInterrupt) or resource else 'failed';update(True)
        if status=='failed':traceback.print_exc();raise
    finally:finished.set();thread.join(timeout=2)

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.repo/'src'));signal.signal(signal.SIGTERM,lambda *_:STOP.set());signal.signal(signal.SIGINT,lambda *_:STOP.set())
    with (a.repo/'.git/q21-resolution-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);execute(a.repo,a.output)
if __name__=='__main__':main()
