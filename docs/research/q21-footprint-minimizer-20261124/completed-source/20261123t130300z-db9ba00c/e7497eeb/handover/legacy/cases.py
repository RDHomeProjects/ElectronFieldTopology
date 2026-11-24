"""Matched fixed-box trials with charged attempts and retained optimizer phase."""
import gc,time
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from common import ROOT,load,save,sha,canonical,stamp,need,log
from checkpoints import write_state,read_state
from engine import Engine
from evaluations import metrics,gate_result,array_sha
from integrity import reserves
from relationships import window
from resources import geometry_budget

def charge_count(out):return sum(len(load(f)) for f in (out/'cases').glob('*/attempt-ledger.json'))
def resample(n,g,nodes):
    from electron_field_topology.sf_time import Grid
    gg=Grid((nodes,)*3,g.lengths,'fixed');before=array_sha(n)
    if nodes==g.shape[0]:return n.copy(),gg,{'method':'identity','source_array_sha256':before,'source_modified':False,'held_layer_correction':0.}
    coordinates=np.moveaxis((gg.points()+np.asarray(g.lengths)/2)/np.asarray(g.spacing),-1,0)
    field=np.stack([map_coordinates(n[...,i]-(1. if i==2 else 0.),coordinates,order=3,mode='constant',cval=0.,prefilter=True)+(1. if i==2 else 0.) for i in range(3)],axis=-1)
    size=np.linalg.norm(field,axis=-1,keepdims=True);need(float(size.min())>1e-6,'Near-zero cubic interpolant; unresolved representation')
    normalization=float(np.max(abs(size-1)));field/=size;mask=gg.fixed_mask();correction=float(np.max(abs(field[mask]-[0,0,1])));field[mask]=[0,0,1]
    need(array_sha(n)==before,'Resampling changed parent');return field,gg,{'method':'cubic_target_grid_then_unit_normalization_and_held_layers','source_array_sha256':before,'minimum_interpolant_norm':float(size.min()),'normalization_correction':normalization,'held_layer_correction':correction,'source_modified':False,'scope':'Initialization transformation; not stationary-solution convergence'}

def run_case(out,parent,g,cfg,limit,backend,stop,phase):
    p=load(ROOT/'PLAN.json');gates=p['registered_gates'];folder=out/'cases'/cfg['id'];folder.mkdir(parents=True,exist_ok=True)
    need(0<limit<=cfg['max_attempts'],'Case horizon exceeds registered cap')
    if (folder/'CASE.json').exists():need(load(folder/'CASE.json')==cfg,'Case settings changed')
    else:save(folder/'CASE.json',cfg)
    admission=geometry_budget(cfg['nodes'],backend['selected']);save(folder/'RESOURCE-ADMISSION.json',admission);need(admission['passed'],'Geometry memory qualification deferred')
    e=Engine(backend['selected'],.25);need(e.kind!='cuda' or e.port.identity()==backend['device'],'CUDA device changed')
    from electron_field_topology.sf_time import Grid
    gg=Grid((cfg['nodes'],)*3,g.lengths,'fixed');identity={'campaign':load(out/'identity.json'),'case':cfg,'backend':backend,'source':load(ROOT/'SOURCE.json')['endpoint_sha256'],'shape':list(gg.shape),'lengths':list(gg.lengths)}
    cp=folder/'control.json';ledger=load(folder/'attempt-ledger.json') if (folder/'attempt-ledger.json').exists() else []
    need(all(r['attempt']==i+1 and r['charged_before_execution'] for i,r in enumerate(ledger)),'Attempt ledger differs')
    if cp.exists():
        c=load(cp);need(c['identity']==canonical(identity) and c['history_sha256']==canonical(c['history']),'Case identity/history changed');s=read_state(folder/c['checkpoint'],e,identity)
        need(sha(folder/c['best']['path'])==c['best']['sha256'],'Retained best checkpoint differs')
        need(len(ledger)>=c['committed_attempts'] and c['history'][-1]['iteration']==s['iteration'],'Restart would refund work')
        replay=metrics(e.host(s['n']),gg,gates)
        for key in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(replay[key],c['history'][-1]['metrics'][key],rtol=1e-6,atol=1e-10),'Restart replay differs: '+key)
    else:
        transformed,gg,init=resample(parent['n'],g,cfg['nodes']);clock=time.perf_counter();m=metrics(transformed,gg,gates);init['metrics_seconds']=time.perf_counter()-clock
        save(folder/'INITIALIZATION.json',{'recorded_at':stamp(),**init,'metrics':m,'gates':gate_result(m,21,gates),'alpha':parent['alpha'],'native_iteration':parent['iteration'],'conjugacy_memory_reset':cfg['start']!='exact','source_optimizer_restart_after_accepted_updates':55,'spacing':list(gg.spacing),'lengths':list(gg.lengths)})
        s=e.state(transformed);s.update(alpha=parent['alpha'],iteration=parent['iteration'],pairs=[])
        if cfg['start']=='exact':
            need(cfg['nodes']==129,'Exact-memory arm must use the unchanged grid')
            for k in ['old_g','old_z','direction']:s[k]=e.xp.asarray(parent[k]).copy()
        history=[{'recorded_at':stamp(),'accepted_step':0,'iteration':545,'metrics':m,'gates':gate_result(m,21,gates),'alpha':s['alpha']}]
        write_state(folder/'restart-0.npz',s,e,identity);write_state(folder/'best-00000.npz',s,e,identity)
        c={'identity':canonical(identity),'checkpoint':'restart-0.npz','slot':0,'committed_attempts':0,'history':history,'history_sha256':canonical(history),'best':{'path':'best-00000.npz','sha256':sha(folder/'best-00000.npz'),'accepted_step':0,'score':max(m['relative_force_l2']/1e-4,m['acceleration_max']/1e-3)}};save(cp,c);del transformed;gc.collect()
    reason='line_search_stalled' if (folder/'LINE-SEARCH.json').exists() else 'matched_horizon_reached'
    while len(ledger)<limit and reason!='line_search_stalled':
        latest=c['history'][-1]
        if not latest['gates']['representation']:reason='representation_unresolved';break
        if not latest['gates']['boundary_admitted']:reason='boundary_admission_lost';break
        if latest['gates']['all_readiness_gates']:reason='measured_all_readiness_gates';break
        if stop() or (out/'STOP.json').exists():raise KeyboardInterrupt('Orderly pause before next attempt')
        reserves(out);need(charge_count(out)<p['maximum_new_optimizer_attempts'],'Global attempt ceiling exhausted')
        ledger.append({'recorded_at':stamp(),'attempt':len(ledger)+1,'charged_before_execution':True});save(folder/'attempt-ledger.json',ledger)
        phase.clear();phase.update(name='matched-resolution-case',case=cfg['id'],nodes=cfg['nodes'],backend=e.kind,charged_attempts=len(ledger),horizon=limit,native_iteration=int(s['iteration']))
        e.sync();clock=time.perf_counter();accepted,step=e.step(s,gg);e.sync();seconds=time.perf_counter()-clock
        if not accepted:save(folder/'LINE-SEARCH.json',step);reason='line_search_stalled';break
        clock=time.perf_counter();audit=e.audit(s['n'],gg);audit_seconds=time.perf_counter()-clock
        clock=time.perf_counter();m=metrics(e.host(s['n']),gg,gates);metrics_seconds=time.perf_counter()-clock
        row={'recorded_at':stamp(),'accepted_step':latest['accepted_step']+1,'iteration':int(s['iteration']),'charged_attempt':len(ledger),'alpha':float(s['alpha']),'metrics':m,'gates':gate_result(m,21,gates),'timing':{'optimizer_seconds':seconds,'backend_audit_seconds':audit_seconds,'metrics_seconds':metrics_seconds},'backend_audit':audit,'native_restart_this_update':s['iteration']%200==0,'step':step}
        slot=1-c['slot'];name='restart-'+str(slot)+'.npz';clock=time.perf_counter();write_state(folder/name,s,e,identity)
        score=max(m['relative_force_l2']/1e-4,m['acceleration_max']/1e-3)
        previous_best=c['best']['path']
        if score<c['best']['score']:
            best_name='best-%05d.npz'%len(ledger);write_state(folder/best_name,s,e,identity);c['best']={'path':best_name,'sha256':sha(folder/best_name),'accepted_step':row['accepted_step'],'score':score}
        row['timing']['checkpoint_seconds']=time.perf_counter()-clock;c['history'].append(row);c.update(checkpoint=name,slot=slot,committed_attempts=len(ledger),history_sha256=canonical(c['history']));save(cp,c)
        if previous_best!=c['best']['path']:
            (folder/previous_best).unlink(missing_ok=True);(folder/previous_best).with_suffix('.seal.json').unlink(missing_ok=True)
        log('Measured fixed-box update',case=cfg['id'],nodes=cfg['nodes'],accepted_step=row['accepted_step'],native_iteration=row['iteration'],force=m['relative_force_l2'],acceleration=m['acceleration_max'])
    write_state(folder/'endpoint.npz',s,e,identity);final=c['history'][-1]
    result={'recorded_at':stamp(),'case':cfg,'shape':list(gg.shape),'lengths':list(gg.lengths),'spacing':list(gg.spacing),'reason':reason,'status':'all_readiness_gates_pass' if final['gates']['all_readiness_gates'] else 'preparation_unresolved','requested_horizon':limit,'charged_attempts':len(ledger),'accepted_steps':final['accepted_step'],'history':c['history'],'windows':{str(h):window(c['history'],h,p['response_window']) for h in [30,60,80,120]},'final':final,'best_retained':c['best'],'endpoint_sha256':sha(folder/'endpoint.npz'),'backend':backend,'physical_time_steps':0,'scope':'Fixed action/box/shift/alpha policy/native restart schedule/gates. Memory consistently reset for every resolution arm; exact control separately labelled.'}
    save(folder/'record.json',result);del s,e;gc.collect();return result
