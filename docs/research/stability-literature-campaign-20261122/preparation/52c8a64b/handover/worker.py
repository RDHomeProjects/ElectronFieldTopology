"""Sequential, restartable literature-guided preparations; all gates preserved."""
import argparse,fcntl,gc,json,os,shutil,signal,sys,threading,traceback,zipfile
from pathlib import Path
import numpy as np
from common import ROOT,load,save,sha,canonical,stamp,need,log,verify_manifest
from integrity import authenticate,parent_state,source_run,verify_sources,reserves,process_identity
from evaluations import metrics,gate_result,derivative_check,q22_compare
from optimizers import ComparisonEngine,write_state,read_state
from numerics import transformed,curvature_probe,geometry
from reporting import campaign
from planner import decide
STOP=threading.Event()

def backend(n,g,requested):
    choice=requested;detail={'requested':requested,'selected':None,'automatic_cpu_reason':None}
    if requested=='auto':
        try:
            e=ComparisonEngine('cuda');e.xp.get_default_memory_pool().free_all_blocks();free,_=e.xp.cuda.runtime.memGetInfo()
            choice='cuda' if np.prod(g.shape)*1100<free*.75 else 'cpu'
            if choice=='cpu':detail['automatic_cpu_reason']='Declared grid memory estimate exceeds75% of currently free VRAM'
            del e;gc.collect()
        except (ImportError,RuntimeError) as error:choice='cpu';detail['automatic_cpu_reason']=str(error)
    e=ComparisonEngine(choice);detail.update(source_backend=load(ROOT/'SOURCE.json')['source_backend'],backend_transfer=choice!=load(ROOT/'SOURCE.json')['source_backend'],bitwise_trajectory_claimed=False,selected=choice,device=e.port.identity() if choice=='cuda' else None,audit=e.audit(e.xp.asarray(n),g))
    # Qualification failure is fatal; no CPU fallback on a failed parity audit.
    return e,detail

def state_to_engine(s,e):
    out={k:e.xp.asarray(s[k]).copy() if s.get(k) is not None else None for k in ['n','old_g','old_z','direction']};out.update(alpha=s['alpha'],iteration=s['iteration'],pairs=[]);return out

def score(row,p):return max(row['metrics']['relative_force_l2']/p['force_limit'],row['metrics']['acceleration_max']/p['acceleration_limit'])

def run_arm(repo,out,parent,grid,arm,requested,curvature,phase,stop=STOP.is_set):
    from electron_field_topology.sf_time import Grid
    plan=load(ROOT/'PLAN.json');p=plan['registered_gates'];folder=out/'arms'/arm['id'];folder.mkdir(parents=True,exist_ok=True)
    if (folder/'record.json').exists():
        record=load(folder/'record.json');need(load(folder/'DONE.json')['sha256']==sha(folder/'record.json'),'Committed arm record differs')
        for k in ['endpoint','best']:
            if record.get(k):need(sha(folder/record[k]['path'])==record[k]['sha256'],'Retained arm field differs')
        return record
    path=folder/'control.json';ledger=load(folder/'attempt-ledger.json') if (folder/'attempt-ledger.json').exists() else []
    need(all(r['attempt']==i+1 and r['charged_before_execution'] for i,r in enumerate(ledger)),'Invalid charged attempt sequence')
    if path.exists():
        c=load(path);need(c['arm']==arm and c['package_sha256']==sha(ROOT/'SHA256SUMS'),'Restart branch identity changed');g=Grid(tuple(c['shape']),tuple(c['lengths']),'fixed')
        e=ComparisonEngine(c['backend']['selected']);need(e.kind!='cuda' or e.port.identity()==c['backend']['device'],'CUDA identity changed mid-branch')
        state=read_state(folder/c['checkpoint'],e,c['identity']);history=c['history'];init=c['initialization'];backend_info=c['backend'];best=c['best'];slot=c['slot'];decisions=c['decisions']
        need(len(ledger)>=c['committed_attempts'],'Restart would refund accepted optimizer attempts')
        replay=metrics(e.host(state['n']),g,p)
        for key in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(replay[key],history[-1]['metrics'][key],rtol=1e-6,atol=1e-10),'Restart metric replay differs: '+key)
    else:
        if arm['kind']=='curvature' and curvature is None:
            result={'arm':arm,'status':'deferred_no_qualified_negative_direction','reason':'No negative direction qualified by both finite-difference scales and Hessian symmetry','charged_attempts':0,'accepted_steps':0,'initialization':{},'history':[{'step':0,'iteration':335,'metrics':metrics(parent['n'],grid,p),'gates':gate_result(metrics(parent['n'],grid,p),21,p)}]};result['final']=result['history'][-1];save(folder/'record.json',result);save(folder/'DONE.json',{'sha256':sha(folder/'record.json')});return result
        n,g,init=transformed(parent['n'],grid,arm,curvature);e,backend_info=backend(n,g,requested)
        state=state_to_engine(parent,e) if arm['kind']=='exact' else e.state(n)
        state.update(iteration=335,alpha=parent['alpha'],pairs=[])
        # Counter335 aligns the CG automatic restart phase in all matched arms.
        # It never claims335 updates were performed on a newly initialized field.
        init.update(optimizer_counter_offset=335,offset_is_not_new_work=True,alpha_initial=parent['alpha'])
        identity={'source_endpoint':load(ROOT/'SOURCE.json')['endpoint_sha256'],'arm':arm,'grid':{'shape':g.shape,'lengths':g.lengths},'backend':backend_info,'package_sha256':sha(ROOT/'SHA256SUMS')}
        measured=metrics(n,g,p);history=[{'recorded_at':stamp(),'step':0,'iteration':335,'metrics':measured,'gates':gate_result(measured,21,p)}];slot=0;decisions=[]
        write_state(folder/'restart-0.npz',state,e,identity);write_state(folder/'best-a00000.npz',state,e,identity)
        best={'path':'best-a00000.npz','sha256':sha(folder/'best-a00000.npz'),'step':0,'score':score(history[-1],p)}
        c={'identity':identity,'arm':arm,'package_sha256':sha(ROOT/'SHA256SUMS'),'shape':g.shape,'lengths':g.lengths,'initialization':init,'backend':backend_info,'checkpoint':'restart-0.npz','committed_attempts':0,'history':history,'best':best,'slot':slot,'decisions':decisions,'pending_limit':None,'plateau_votes':0}
        save(path,c);del n;gc.collect()
    reason=None
    while reason is None:
        charged=len(ledger);ga=history[-1]['gates'];accepted_steps=history[-1]['step']
        if not ga['representation']:reason='representation_unresolved';break
        if ga['strict_stationary']:reason='strict_stationarity_measured_boundary_reported_separately';break
        if charged>=arm['cap']:reason='declared_branch_budget_reached';break
        if stop() or (out/'STOP.json').exists():raise KeyboardInterrupt('Orderly branch pause')
        if c['pending_limit'] is None or charged>=c['pending_limit']:
            if charged<plan['first_probe']:decision={'action':'continue','reason':'declared_initial_probe','next_attempts':min(plan['first_probe']-charged,arm['cap']-charged)}
            else:
                decision=decide(history,charged,plan['adaptive_policy'],p,arm['cap'])
                if decision['action']=='stop':
                    c['plateau_votes']+=1
                    if charged>=plan['minimum_before_plateau'] and c['plateau_votes']>=plan['plateau_decisions']:reason='repeated_measured_joint_progress_failure';decisions.append(decision);break
                    decision=decision|{'action':'continue','reason':'bounded_minimum_for_slow_relaxation_diagnosis','next_attempts':min(5,arm['cap']-charged),'initial_stop_reason':decision.get('reason')}
                else:c['plateau_votes']=0
            decision.update(recorded_at=stamp(),charged_attempts=charged,accepted_steps=accepted_steps);decisions.append(decision);c['pending_limit']=charged+decision['next_attempts'];save(path,c)
        reserves(out);need(sum(len(load(f)) for f in (out/'arms').glob('*/attempt-ledger.json'))<plan['maximum_new_optimizer_attempts'],'Global optimizer budget exhausted')
        ledger.append({'recorded_at':stamp(),'attempt':len(ledger)+1,'charged_before_execution':True});save(folder/'attempt-ledger.json',ledger)
        phase.update(name='preparation',arm=arm['id'],backend=e.kind,nodes=g.shape[0],charged_attempts=len(ledger),accepted_steps=accepted_steps)
        ok,step=e.step_method(state,g,arm['optimizer'])
        if not ok:reason='line_search_stalled';save(folder/'LINE-SEARCH.json',step);break
        e.sync();audit=e.audit(state['n'],g);measured=metrics(e.host(state['n']),g,p)
        row={'recorded_at':stamp(),'step':accepted_steps+1,'iteration':int(state['iteration']),'charged_attempt':len(ledger),'alpha':float(state['alpha']),'objective_calls':step['objective_calls'],'metrics':measured,'gates':gate_result(measured,21,p),'backend_audit':audit,'optimizer':step}
        other=1-slot;name='restart-'+str(other)+'.npz';write_state(folder/name,state,e,c['identity']);oldbest=best
        if score(row,p)<best['score']:
            bn='best-a%05d.npz'%len(ledger);write_state(folder/bn,state,e,c['identity']);best={'path':bn,'sha256':sha(folder/bn),'step':row['step'],'score':score(row,p)}
        history.append(row);slot=other;c.update(checkpoint=name,committed_attempts=len(ledger),history=history,best=best,slot=slot,decisions=decisions);save(path,c)
        if oldbest['path']!=best['path']:
            # Delete only superseded checkpoints belonging to this new branch,
            # after the replacement pointer has been durably committed.
            (folder/oldbest['path']).unlink(missing_ok=True);(folder/oldbest['path']).with_suffix('.seal.json').unlink(missing_ok=True)
        log('Measured literature-campaign update',arm=arm['id'],step=row['step'],force=measured['relative_force_l2'],acceleration=measured['acceleration_max'],all_readiness_gates=row['gates']['all_readiness_gates'])
    statepath=folder/'endpoint.npz';write_state(statepath,state,e,c['identity']);n=e.host(state['n']);geo=geometry(n,g)
    from curves import analyze
    curves,loops=analyze(n,g);save(folder/'CURVES.json',curves)
    if loops:
        with (folder/'curves.npz').open('wb') as f:np.savez_compressed(f,**{'curve_'+str(i):v for i,v in enumerate(loops)})
    result={'recorded_at':stamp(),'arm':arm,'status':'all_readiness_gates_pass' if history[-1]['gates']['all_readiness_gates'] else 'preparation_unresolved','reason':reason,'charged_attempts':len(ledger),'accepted_steps':history[-1]['step'],'initialization':init,'backend':backend_info,'history':history,'final':history[-1],'decisions':decisions,'geometry':geo,'curves':curves,'endpoint':{'path':'endpoint.npz','sha256':sha(statepath)},'best':best,'physical_time_steps':0,'physical_Q_rejection':False}
    save(folder/'record.json',result);save(folder/'DONE.json',{'recorded_at':stamp(),'sha256':sha(folder/'record.json')});del state,e,n;gc.collect();return result

def seal(out):
    transient={'evidence.zip','SHA256SUMS','heartbeat.json','status.json','supervisor.json','worker-launch.json','telemetry-latest.json','STOP.json','PAUSE-REQUEST.json'}
    fields=[{'path':f.relative_to(out).as_posix(),'sha256':sha(f),'bytes':f.stat().st_size} for f in sorted(out.rglob('*.npz'))]
    save(out/'FIELD-MANIFEST.json',{'recorded_at':stamp(),'fields':fields,'scope':'Retained local full restart/best/endpoint fields and curves; intermediate measured states not retained are never selected as checkpoints'})
    files=[f for f in sorted(out.rglob('*')) if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ['.npz','.tmp','.so','.lock'] and not(f.parent==out and f.name in transient)]
    sums=''.join(sha(f)+'  '+f.relative_to(out).as_posix()+'\n' for f in files);(out/'SHA256SUMS').write_text(sums)
    with zipfile.ZipFile(out/'evidence.tmp','w',zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,f.relative_to(out).as_posix())
        z.writestr('SHA256SUMS',sums)
    (out/'evidence.tmp').replace(out/'evidence.zip')

def execute(repo,out):
    from electron_field_topology.sf_time import Grid
    verify_manifest(ROOT);verify_sources(repo);receipt=authenticate(repo);parent=parent_state(receipt['endpoint']);plan=load(ROOT/'PLAN.json');spec=load(ROOT/'SOURCE.json');g=Grid((97,)*3,(23.04,)*3,'fixed');phase={'name':'source-replay'};finished=threading.Event();records=[]
    def heartbeat():
        while not finished.is_set():save(out/'heartbeat.json',{'recorded_at':stamp(),'pid':os.getpid(),'process_identity':process_identity(os.getpid()),'operation':dict(phase)});finished.wait(15)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start();status='working';error=None
    deferred=['Physical-time motion is conditional on unchanged static, boundary and two-grid consistency admission; its disposition is recorded in MOTION.json.','Massive/isospinning and supercurrent-coupled models: separate actions, qualified feasibility review in OPTIONS.json; no silent model change.','Mathematical existence theorems do not certify these numerical candidates.','Historical Q22 exact field remains deferred unless an explicit authenticated --q22 path is supplied.']
    def update(final=False):
        from options import dispositions
        save(out/'OPTIONS.json',dispositions(records,load(out/'CURVATURE.json') if (out/'CURVATURE.json').exists() else {'status':'pending'}))
        charged=sum(len(load(f)) for f in (out/'arms').glob('*/attempt-ledger.json'));need(charged<=plan['maximum_new_optimizer_attempts'],'Global budget exceeded')
        save(out/'record.json',{'recorded_at':stamp(),'status':status,'error':error,'phase':dict(phase),'source':receipt,'arms':records,'charged_attempts':charged,'maximum_new_optimizer_attempts':plan['maximum_new_optimizer_attempts'],'deferred':deferred,'physical_integration_attempts_charged':len(load(out/'motion-attempt-ledger.json')) if (out/'motion-attempt-ledger.json').exists() else 0})
        save(out/'status.json',{'recorded_at':stamp(),'status':status,'phase':dict(phase),'charged_attempts':charged,'completed_arms':len(records),'declared_arms':len(plan['arms']),'maximum_new_optimizer_attempts':plan['maximum_new_optimizer_attempts'],'physical_integration_attempts_charged':len(load(out/'motion-attempt-ledger.json')) if (out/'motion-attempt-ledger.json').exists() else 0,'error':error});campaign(out,records,phase,deferred,status=='complete_pending_review')
        if final:seal(out)
    try:
        reserves(out);m=metrics(parent['n'],g,plan['registered_gates'])
        for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:need(np.isclose(m[k],spec['expected_metrics'][k],rtol=1e-6,atol=1e-10),'Exact335 metric replay differs: '+k)
        save(out/'SOURCE-REPLAY.json',{'recorded_at':stamp(),'metrics':m,'gates':gate_result(m,21,plan['registered_gates']),'sha256':receipt['endpoint_sha256']})
        with np.load(receipt['q2'],allow_pickle=False) as z:q2=z['field'].copy()
        qg=Grid((spec['q2']['nodes'],)*3,(spec['q2']['length'],)*3,'fixed');qm=metrics(q2,qg,plan['registered_gates']);need(gate_result(qm,2,plan['registered_gates'])['all_readiness_gates'],'Q2 control fails; all new preparations blocked')
        save(out/'Q2-CONTROL.json',{'recorded_at':stamp(),'metrics':qm,'gates':gate_result(qm,2,plan['registered_gates'])});del q2;gc.collect();update()
        if not (out/'MODEL-AUDIT.json').exists():
            from model_audit import audit as model_audit
            phase.update(name='normalization-and-operator-audit');save(out/'MODEL-AUDIT.json',model_audit(parent['n'],g,out,plan['registered_gates']))
        if not (out/'CURVATURE.json').exists():
            phase.update(name='constrained-curvature-probe');e,be=backend(parent['n'],g,load(out/'identity.json')['requested_backend'])
            check=derivative_check(parent['n'],g,{'epsilons':[.001,.0003,.0001],'rtol':.002,'atol':1e-7});need(check['passed'],'Directional derivative instrument fails');save(out/'DERIVATIVE-CHECK.json',check)
            result,direction=curvature_probe(parent['n'],g,e,plan['hessian_epsilons'],plan['hessian_basis'])
            if direction is not None:
                with (out/'curvature-direction.npz').open('wb') as f:np.savez_compressed(f,direction=direction)
                result['direction_sha256']=sha(out/'curvature-direction.npz')
            save(out/'CURVATURE.json',result);del e;gc.collect()
        result=load(out/'CURVATURE.json');direction=None
        if result['direction_qualified']:
            need(sha(out/'curvature-direction.npz')==result['direction_sha256'],'Curvature direction hash differs')
            with np.load(out/'curvature-direction.npz',allow_pickle=False) as z:direction=z['direction'].copy()
        if not (out/'SCALE-SWEEP.json').exists():
            phase.update(name='measured-single-variable-scale');sweep=[];factors=[.96,.98,1.,1.02,1.04]
            for factor in factors:
                n,gg,info=transformed(parent['n'],g,{'kind':'scale','factor':factor});mm=metrics(n,gg,plan['registered_gates']);sweep.append({'factor':factor,'metrics':mm,'gates':gate_result(mm,21,plan['registered_gates']),'initialization':info})
            # Two extra actual measurements around the fitted interior turn.
            c=np.polyfit(factors,[r['metrics']['energy'] for r in sweep],2)
            turn=-c[1]/(2*c[0]) if c[0]>0 else None
            if turn is not None and .96<turn<1.04:
                for factor in [max(.96,turn-.005),min(1.04,turn+.005)]:
                    n,gg,info=transformed(parent['n'],g,{'kind':'scale','factor':float(factor)});mm=metrics(n,gg,plan['registered_gates']);sweep.append({'factor':float(factor),'metrics':mm,'gates':gate_result(mm,21,plan['registered_gates']),'initialization':info})
            save(out/'SCALE-SWEEP.json',{'recorded_at':stamp(),'measured':sweep,'quadratic_energy_coefficients':c.tolist(),'predicted_turn':turn,'admission_inferred':False,'normalization_and_finite_box_mapping_disclosed':True});del n;gc.collect()
        explicit=load(out/'identity.json').get('explicit_q22')
        if explicit and not (out/'Q22.json').exists():
            phase.update(name='explicit-native-q22-evaluation');need(sha(Path(explicit))==spec['q22']['sha256'],'Explicit historicalQ22 SHA differs');folder=out/'q22';folder.mkdir(exist_ok=True);save(out/'Q22.json',q22_compare(Path(explicit),spec['q22'],plan['registered_gates'],folder))
        for arm in plan['arms']:
            phase.clear();phase.update(name='arm-initialization',arm=arm['id']);update()
            if STOP.is_set() or (out/'STOP.json').exists():raise KeyboardInterrupt('Orderly pause before next independent arm')
            records.append(run_arm(repo,out,parent,g,arm,load(out/'identity.json')['requested_backend'],direction,phase));update()
        from relationships import analyze as relationship_analysis
        save(out/'RELATIONSHIPS.json',relationship_analysis(records,load(out/'SCALE-SWEEP.json')))
        from motion_checks import run as motion_run
        motion_run(repo,out,records,Path(receipt['q2']),load(out/'identity.json')['requested_backend'],STOP.is_set,phase)
        from options import dispositions
        save(out/'OPTIONS.json',dispositions(records,load(out/'CURVATURE.json')))
        authenticate(repo);status='complete_pending_review';phase.clear();phase.update(name='complete');update(True)
    except BaseException as exc:
        error=str(exc);resource=isinstance(exc,MemoryError) or any(t in str(exc).lower() for t in ['reserve reached','outofmemory','out of memory']);status='interrupted' if isinstance(exc,KeyboardInterrupt) or resource else 'failed';update(True)
        if status=='failed':traceback.print_exc();raise
    finally:finished.set();thread.join(timeout=2)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();sys.path.insert(0,str(args.repo/'src'))
    signal.signal(signal.SIGTERM,lambda *_:STOP.set());signal.signal(signal.SIGINT,lambda *_:STOP.set())
    with (source_run(args.repo)/'.worker.lock').open('r') as old,(args.output/'.worker.lock').open('a') as new:
        fcntl.flock(old,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(new,fcntl.LOCK_EX|fcntl.LOCK_NB);execute(args.repo,args.output)
if __name__=='__main__':main()
