"""Matched restart cases and an explicitly separate exact-memory control."""
import gc,time
from pathlib import Path
import numpy as np
from common import ROOT,load,save,sha,canonical,stamp,need,log
from checkpoints import write_state,read_state
from engine import Engine
from evaluations import metrics,gate_result
from integrity import reserves
from fitting import response

def charge_count(out):return sum(len(load(f)) for f in (out/'cases').glob('*/attempt-ledger.json'))

def run_case(out,parent,g,cfg,limit,backend,stop,phase):
    plan=load(ROOT/'PLAN.json');p=plan['registered_gates'];folder=out/'cases'/cfg['id'];folder.mkdir(parents=True,exist_ok=True)
    if (folder/'CASE.json').exists():need(load(folder/'CASE.json')==cfg,'Case settings changed')
    else:save(folder/'CASE.json',cfg)
    need(0<limit<=cfg['max_attempts'],'Case horizon exceeds declared cap')
    e=Engine(backend['selected'],cfg['shift']);need(e.kind!='cuda' or e.port.identity()==backend['device'],'CUDA identity changed during calibration')
    identity={'campaign':load(out/'identity.json'),'case':cfg,'backend':backend,'source':load(ROOT/'SOURCE.json')['endpoint_sha256']}
    cp=folder/'control.json';ledger=load(folder/'attempt-ledger.json') if (folder/'attempt-ledger.json').exists() else []
    need(all(r['attempt']==i+1 and r['charged_before_execution'] for i,r in enumerate(ledger)),'Attempt ledger sequence differs')
    if cp.exists():
        c=load(cp);need(c['identity']==canonical(identity) and c['history_sha256']==canonical(c['history']),'Case identity/history changed');s=read_state(folder/c['checkpoint'],e,identity)
        need(len(ledger)>=c['committed_attempts'] and c['history'][-1]['iteration']==s['iteration'],'Restart would refund work or select wrong state')
        replay=metrics(e.host(s['n']),g,p)
        for key in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(replay[key],c['history'][-1]['metrics'][key],rtol=1e-6,atol=1e-10),'Restart replay differs: '+key)
    else:
        s=e.state(parent['n']);s.update(alpha=parent['alpha'],iteration=parent['iteration'],pairs=[])
        if cfg['start']=='exact':
            for k in ['old_g','old_z','direction']:s[k]=e.xp.asarray(parent[k]).copy()
            need(cfg['shift']==.25,'Exact-memory control must retain the source preconditioner')
        m=metrics(parent['n'],g,p);history=[{'recorded_at':stamp(),'accepted_step':0,'iteration':int(s['iteration']),'metrics':m,'gates':gate_result(m,21,p)}]
        write_state(folder/'restart-0.npz',s,e,identity);write_state(folder/'best-00000.npz',s,e,identity)
        c={'identity':canonical(identity),'checkpoint':'restart-0.npz','slot':0,'committed_attempts':0,'history':history,'history_sha256':canonical(history),'best':{'path':'best-00000.npz','sha256':sha(folder/'best-00000.npz'),'accepted_step':0,'score':max(m['relative_force_l2']/p['force_limit'],m['acceleration_max']/p['acceleration_limit'])}}
        save(cp,c)
    reason='line_search_stalled' if (folder/'LINE-SEARCH.json').exists() else 'measurement_horizon_reached'
    while len(ledger)<limit and reason!='line_search_stalled':
        gates=c['history'][-1]['gates']
        if not gates['representation']:reason='representation_unresolved';break
        if not gates['boundary_admitted']:reason='boundary_admission_lost';break
        if gates['all_readiness_gates']:reason='measured_all_readiness_gates';break
        if stop() or (out/'STOP.json').exists():raise KeyboardInterrupt('Orderly calibration pause before next attempt')
        reserves(out);need(charge_count(out)<plan['maximum_new_optimizer_attempts'],'Global calibration attempt ceiling exhausted')
        ledger.append({'recorded_at':stamp(),'attempt':len(ledger)+1,'charged_before_execution':True});save(folder/'attempt-ledger.json',ledger)
        phase.update(name='matched-conditioning-case',case=cfg['id'],shift=cfg['shift'],charged_attempts=len(ledger),limit=limit,accepted_steps=c['history'][-1]['accepted_step'])
        e.sync();clock=time.perf_counter();accepted,step=e.step(s,g);e.sync();seconds=time.perf_counter()-clock
        if not accepted:reason='line_search_stalled';save(folder/'LINE-SEARCH.json',step);break
        audit=e.audit(s['n'],g);m=metrics(e.host(s['n']),g,p);row={'recorded_at':stamp(),'accepted_step':c['history'][-1]['accepted_step']+1,'iteration':int(s['iteration']),'charged_attempt':len(ledger),'alpha':float(s['alpha']),'metrics':m,'gates':gate_result(m,21,p),'objective_calls':step['objective_calls'],'optimization_seconds':seconds,'backend_audit':audit,'step':step}
        slot=1-c['slot'];name='restart-'+str(slot)+'.npz';write_state(folder/name,s,e,identity);oldbest=c['best'];score=max(m['relative_force_l2']/p['force_limit'],m['acceleration_max']/p['acceleration_limit'])
        if score<oldbest['score']:
            bn='best-%05d.npz'%len(ledger);write_state(folder/bn,s,e,identity);c['best']={'path':bn,'sha256':sha(folder/bn),'accepted_step':row['accepted_step'],'score':score}
        c['history'].append(row);c.update(checkpoint=name,slot=slot,committed_attempts=len(ledger),history_sha256=canonical(c['history']));save(cp,c)
        if c['best']['path']!=oldbest['path']:
            (folder/oldbest['path']).unlink(missing_ok=True);(folder/oldbest['path']).with_suffix('.seal.json').unlink(missing_ok=True)
        log('Measured conditioning update',case=cfg['id'],shift=cfg['shift'],accepted_step=row['accepted_step'],force=m['relative_force_l2'],acceleration=m['acceleration_max'],readiness=row['gates']['all_readiness_gates'])
    write_state(folder/'endpoint.npz',s,e,identity);latest=c['history'][-1];lastplan=dict(plan,measurement_attempts=len(c['history'])-1)
    finalwindow=response(c['history'],lastplan) if lastplan['measurement_attempts']>=30 else {'eligible':False,'reason':'short_case'}
    r={'recorded_at':stamp(),'case':cfg,'reason':reason,'status':'all_readiness_gates_pass' if latest['gates']['all_readiness_gates'] else 'preparation_unresolved','requested_attempt_horizon':limit,'charged_attempts':len(ledger),'accepted_steps':latest['accepted_step'],'history':c['history'],'response':response(c['history'],plan),'final_window':finalwindow,'final':latest,'best_retained':c['best'],'endpoint':{'path':'endpoint.npz','sha256':sha(folder/'endpoint.npz')},'physical_time_steps':0,'backend':backend,'scope':'Source alpha/action/grid/box/gates unchanged. Restart cases differ only in preconditioner shift; exact-memory control is separately labelled.'}
    save(folder/'record.json',r);save(folder/'record.seal.json',{'recorded_at':stamp(),'sha256':sha(folder/'record.json')});del s,e;gc.collect();return r
