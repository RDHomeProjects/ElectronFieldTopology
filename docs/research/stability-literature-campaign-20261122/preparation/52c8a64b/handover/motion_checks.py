"""Conditional rest/boost pair, Q2 control, mesh alignment and dt refinement."""
import gc,json
import numpy as np
from common import load,save,sha,stamp,need,canonical
from evaluations import gate_result,metrics
from numerics import sample
from motionlib import numeric

def rest_run(n,g,q,folder,p):
    from electron_field_topology.sf_time import step,diagnostics
    from electron_field_topology.sf_readmission import cone
    from motionlib.motion import tail,fieldsave
    from motionlib.topology import anisotropic_hopf
    folder.mkdir(parents=True,exist_ok=True);dt=p['motion']['dt'];count=round(p['motion']['duration']/dt);identity={'source_array':__import__('hashlib').sha256(n.tobytes()).hexdigest(),'shape':g.shape,'lengths':g.lengths,'dt':dt,'q':q,'case':'rest'}
    if (folder/'result.json').exists():
        result=load(folder/'result.json');need(result['identity']==canonical(identity),'Cached rest identity differs');need(sha(folder/'final.npz')==result['final_sha256'],'Cached rest field differs');return result
    source=n.copy();v=np.zeros_like(n);initial=diagnostics(n,v,g);history=[];index=0;status='screen_pass'
    if (folder/'latest.npz').exists():
        seal=load(folder/'latest.json');need(seal['identity']==canonical(identity) and sha(folder/'latest.npz')==seal['sha256'],'Rest restart seal differs')
        with np.load(folder/'latest.npz',allow_pickle=False) as z:n=z['field'].copy();v=z['field_rate'].copy();index=int(z['step'])
        history=[r for r in load(folder/'history.json') if r['step']<=index]
    else:fieldsave(folder/'initial.npz',n,v,identity,0,dt)
    for i in range(index+1,count+1):
        numeric.resources(folder,p);n,v,_=step(n,v,g,dt,(i-1)*dt);d=diagnostics(n,v,g);h=anisotropic_hopf(n,g)
        gates={'energy':abs(d['energy']/initial['energy']-1)<=p['motion']['energy_relative'],'momentum':np.linalg.norm(np.asarray(d['momentum'])-initial['momentum'])/initial['energy']<=p['motion']['momentum_scaled'],'shape':np.linalg.norm(n-source)/max(np.linalg.norm(source-[0,0,1]),1e-30)<=p['motion']['shape_relative'],'tail':tail(n,v,g,p['shell_width'])<=p['motion']['runtime_tail_safety'],'representation':abs(abs(h)-q)/q<=p['charge_relative_error'] and cone(n)>0,'constraints':d['unit_error']<p['unit_limit'] and d['tangency_error']<p['unit_limit']}
        history.append({'recorded_at':stamp(),'step':i,'time':i*dt,'gates':{k:bool(v) for k,v in gates.items()},'diagnostics':d});save(folder/'history.json',history);fieldsave(folder/'latest.npz',n,v,identity,i,dt)
        if not all(gates.values()):status='screen_failed';break
    fieldsave(folder/'final.npz',n,v,identity,history[-1]['step'],dt)
    result={'recorded_at':stamp(),'status':status,'identity':canonical(identity),'time':history[-1]['time'],'final':history[-1],'final_sha256':sha(folder/'final.npz'),'backend':'cpu','scope':'Rest control; same physical gates except translation speed is inapplicable'};save(folder/'result.json',result);return result

def control_pass(results):
    screens=[r['result'] for r in results if r.get('candidate')=='q2-control']
    pairs=[r['temporal_comparison'] for r in results if r.get('temporal_comparison',{}).get('candidate')=='q2-control']
    return len(screens)==4 and len(pairs)==2 and all(r['status']=='screen_pass' for r in screens+pairs)

def run(repo,out,records,q2_path,requested,stop,phase):
    from electron_field_topology.sf_time import Grid
    from motionlib.motion import run as boost_run
    spec=load(out/'handover/SOURCE.json');p=load(out/'handover/PLAN.json')['registered_gates'];numeric.CONTEXT.update(out=out,stop=stop)
    if (out/'MOTION.json').exists():return load(out/'MOTION.json')
    byid={r['arm']['id']:r for r in records};mesh={'passed':False,'reason':'Both mesh129 and mesh161 endpoints must pass unchanged static and boundary gates'}
    candidates=[]
    if all(byid[k]['final']['gates']['all_readiness_gates'] for k in ['mesh-129','mesh-161']):
        fields=[]
        for k in ['mesh-129','mesh-161']:
            r=byid[k];path=out/'arms'/k/r['endpoint']['path'];need(sha(path)==r['endpoint']['sha256'],'Motion source changed')
            with np.load(path,allow_pickle=False) as z:fields.append(z['n'].copy())
        coarse,fine=fields;cg=Grid((129,)*3,(23.04,)*3,'fixed');fg=Grid((161,)*3,(23.04,)*3,'fixed');mapped,_=sample(fine,fg,cg.points());shape=float(np.linalg.norm(mapped-coarse)/max(np.linalg.norm(coarse-[0,0,1]),1e-30));energies=[byid[k]['final']['metrics']['energy'] for k in ['mesh-129','mesh-161']];er=abs(energies[1]/energies[0]-1)
        mesh={'passed':bool(er<=p['mesh_energy_limit'] and shape<=.01),'energy_relative':er,'mapped_field_relative':shape,'limits':{'energy':p['mesh_energy_limit'],'field':.01},'scope':'Two-grid consistency only, not a continuum extrapolation'}
        if mesh['passed']:candidates.append(('q21-mesh161',out/'arms/mesh-161/endpoint.npz','n',fg,21))
        del fields,coarse,fine,mapped;gc.collect()
    qg=Grid((spec['q2']['nodes'],)*3,(spec['q2']['length'],)*3,'fixed');targets=[('q2-control',q2_path,'field',qg,2)]+candidates;results=[];control_failed=False
    # Q2 is evolved only if a Q21 endpoint has qualified, avoiding an expensive
    # standalone repeat when all scientific candidates are still unadmitted.
    if not candidates:
        result={'recorded_at':stamp(),'status':'deferred_no_mesh_admitted_candidate','mesh':mesh,'production_steps':0,'cases':[]};save(out/'MOTION.json',result);return result
    for name,path,key,g,q in targets:
        with np.load(path,allow_pickle=False) as z:n=z[key].copy()
        need(gate_result(metrics(n,g,p),q,p)['all_readiness_gates'],'Conditional motion source fails readiness gates')
        for case in ['rest','boost']:
            pair=[]
            for dt in [.01,.005]:
                phase.update(name='conditional-motion',candidate=name,case=case,dt=dt);pp=dict(p);pp['motion']=dict(p['motion'],dt=dt);folder=out/'motion'/name/(case+'-dt'+str(dt))
                if case=='rest':r=rest_run(n,g,q,folder,pp)
                else:
                    # Conservatively reserve four qualification integration calls
                    # in addition to production attempts; never refund on retry.
                    if not (folder/'backend.json').exists():
                        for _ in range(4):numeric.charge('qualification_call_reservation')
                    r=boost_run(n,g,q,folder,pp,{'campaign_source':spec['endpoint_sha256'],'case':name},requested,dt)
                pair.append((folder,r));results.append({'candidate':name,'case':case,'dt':dt,'result':r})
                if r['status']!='screen_pass':break
            temporal={'candidate':name,'case':case,'status':'incomplete_or_failed_pair'}
            if len(pair)==2 and all(r['status']=='screen_pass' for _,r in pair):
                arrays=[]
                for folder,r in pair:
                    with np.load(folder/'final.npz',allow_pickle=False) as z:arrays.append((z['field'].copy(),z['field_rate'].copy()))
                field=float(np.linalg.norm(arrays[0][0]-arrays[1][0])/max(np.linalg.norm(arrays[1][0]-[0,0,1]),1e-30));rate=float(np.linalg.norm(arrays[0][1]-arrays[1][1])/max(np.linalg.norm(arrays[1][1]),1.))
                temporal.update(status='screen_pass' if field<=p['motion']['temporal_field_limit'] and rate<=p['motion']['temporal_rate_limit'] else 'screen_failed',field_relative=field,rate_scaled=rate);del arrays;gc.collect()
            results.append({'temporal_comparison':temporal})
        del n;gc.collect()
        if name=='q2-control' and not control_pass(results):
            control_failed=True
            break
    result={'recorded_at':stamp(),'status':'instrument_motion_control_failed' if control_failed else 'measured_pending_review','candidate_motion_blocked_by_control':control_failed,'mesh':mesh,'cases':results,'integration_attempts_charged':len(load(out/'motion-attempt-ledger.json')) if (out/'motion-attempt-ledger.json').exists() else 0,'maximum_integration_call_allocation':300,'scope':'Paired rest/boost short finite-lattice screens with dt refinement; not long-time stability or electron acceptance'};save(out/'MOTION.json',result);return result
