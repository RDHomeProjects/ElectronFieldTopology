"""Full local hashes and selected-field metric replay before bounded continuation."""
import os,platform,sys,subprocess,shutil,json
from pathlib import Path
import numpy as np
import scipy
from electron_field_topology.sf_time import Grid
from electron_field_topology.rapid_q_screen.engine import Engine,restore
from electron_field_topology.rapid_q_screen.runner import metrics
from .common import stamp,save,sha,canonical,log,memory_guard
from .selection import select_prior,allocation_ledger

def context():
    from runtime import ROOT,CFG
    return ROOT,CFG

def receipt_identity(repo,screen_run,past_run):
    root,cfg=context()
    return {'source_commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'package_sha256':sha(root/'SHA256SUMS'),'plan_sha256':sha(root/'FOLLOWUP.json'),'screen_evidence_sha256':cfg['screen_evidence_sha256'],'prior_evidence_sha256':cfg['prior_evidence_sha256'],'screen_run':str(screen_run.resolve()),'past_run':str(past_run.resolve()),'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'threads':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']}}

def backend(benchmark,nodes):
    row=next(v for v in benchmark['rows'] if v['nodes']==nodes)
    if benchmark['status']!='backend_qualification_passed':raise ValueError('Original backend qualification was not passed')
    engine=Engine(row['selected_backend'])
    if engine.kind=='cuda' and engine.port.identity()!=benchmark['cuda_identity']:raise ValueError('CUDA device/runtime differs from original qualified receipt; no fallback')
    env=benchmark['identity']
    for key,actual in [('python',platform.python_version()),('numpy',np.__version__),('scipy',scipy.__version__)]:
        if env[key]!=actual:raise ValueError('Original benchmark environment differs: '+key)
    threads={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']}
    if env['threads']!=threads:raise ValueError('Use original four-thread benchmark environment')
    return engine

def load_job(job,screen,past,screen_run,past_run,engine):
    from runtime import safe_field
    root=screen_run if job['source']=='screen' else past_run;path=safe_field(root,job['checkpoint'])
    if sha(path)!=job['checkpoint_sha256']:raise ValueError('Selected parent checkpoint changed')
    g=Grid((job['nodes'],)*3,(job['length'],)*3,'fixed')
    if job['source']=='screen':
        identity={**screen['record.json']['identity'],'seed':job['seed'],'shape':list(g.shape),'lengths':list(g.lengths),'backend':engine.kind};latest=path.parent/'latest.npz';state=restore(latest,engine,identity)
        if state['iteration']!=job['start_iteration'] or sha(latest)!=job['checkpoint_sha256']:raise ValueError('Parent optimizer continuation endpoint differs from selected stage')
        history=json.loads((path.parent/'history.json').read_text())
        if history[-1]['iteration']!=state['iteration']:raise ValueError('Parent observation history differs from optimizer state')
        kind='exact optimizer state and adaptive schedule continuation'
    else:
        with np.load(path,allow_pickle=False) as z:
            n=z['field'].copy()
        if n.dtype!=np.float64 or n.shape!=g.shape+(3,):raise ValueError('Invalid legacy field precision or geometry')
        state=engine.state(n);state['iteration']=job['start_iteration'];identity=None;history=None;kind='legacy field import; explicit conjugacy and step-length restart at native iteration count'
    n=engine.host(state['n'])
    if not np.isfinite(n).all():raise ValueError('Nonfinite selected field')
    return g,state,identity,history,kind

def replay(job,engine,g,state,plan):
    root,_=context();p=load_plan(root);observed=metrics(engine.host(state['n']),g,p);differences={}
    for key,expected in job['metrics'].items():
        if key not in observed or not isinstance(expected,(int,float)):continue
        actual=observed[key]
        if not isinstance(actual,(int,float)) or not np.isclose(actual,expected,rtol=plan['metric_replay_rtol'],atol=plan['metric_replay_atol']):raise ValueError('Selected field metric replay mismatch: '+job['id']+' '+key)
        differences[key]=abs(actual-expected)
    raw=engine.audit(state['n'],g,p['qualification_rtol'],p['qualification_atol'])
    # Test one accepted continuation step on disposable copies. The actual parent
    # and future execution state remain unchanged, including all CG memory.
    cpu=Engine('cpu');cs={k:(cpu.xp.asarray(engine.host(v)).copy() if k in ['n','old_g','old_z','direction'] and v is not None else v) for k,v in state.items()};gs={k:(engine.xp.asarray(v).copy() if k in ['n','old_g','old_z','direction'] and v is not None else v) for k,v in state.items()}
    ca=cpu.step(cs,g)[0];ga=engine.step(gs,g)[0];engine.sync()
    if ca!=ga:raise ValueError('CPU/CUDA continuation-step acceptance differs')
    error=float(np.max(abs(cpu.host(cs['n'])-engine.host(gs['n']))))
    if not np.allclose(cpu.host(cs['n']),engine.host(gs['n']),rtol=2e-9,atol=2e-10):raise ValueError('CPU/CUDA one-step continuation audit differs')
    return {'recorded_at':stamp(),'seed':job['id'],'nodes':job['nodes'],'backend':engine.kind,'parent_sha256':job['checkpoint_sha256'],'replayed_metrics':observed,'metric_abs_differences':differences,'raw_gradient_audit':raw,'one_step_accepted':ca,'one_step_field_max_difference':error,'scope':'Disposable one-step copies; parent field and optimizer state unchanged'}

def load_plan(root):
    import zipfile
    with zipfile.ZipFile(root/'data/completed-screen-evidence.zip') as z:return json.loads(z.read('record.json'))['plan']

def run_audit(repo,screen_run,past_run,out):
    from runtime import verify_inputs
    root,cfg=context();plan=json.loads((root/'FOLLOWUP.json').read_text());memory_guard(plan['memory_min_available_gib']);screen,past,jobs=verify_inputs(screen_run,past_run,full=True);out.mkdir(parents=True,exist_ok=False);replays=[];engines={}
    for job in jobs:
        log('Replaying selected endpoint',seed=job['id'],nodes=job['nodes'])
        if job['nodes'] not in engines:engines[job['nodes']]=backend(screen['benchmark.json'],job['nodes'])
        engine=engines[job['nodes']];g,state,_,_,kind=load_job(job,screen,past,screen_run,past_run,engine);r=replay(job,engine,g,state,plan);r['continuation_mode']=kind;replays.append(r);save(out/'progress.json',{'recorded_at':stamp(),'completed':len(replays),'total':len(jobs)})
        del state
    selections=[];p=screen['record.json']['plan']
    for seed in [v['seed'] for v in screen['record.json']['broad']]:
        candidates=[(k,v) for k,v in past['rest'].items() if (seed['family']=='reference' and k=='q2-reference') or v.get('lineage',{}).get('seed_sha256')==canonical(seed)]
        if candidates:selections.append({'seed':seed['id'],**select_prior(candidates,p)})
    result={'recorded_at':stamp(),'status':'local_field_and_backend_audit_passed','identity':receipt_identity(repo,screen_run,past_run),'full_screen_manifest_verified':True,'selected_endpoint_replays':replays,'corrected_prior_selection':selections,'completed_screen_allocation_ledger':allocation_ledger(screen['record.json']['broad'],screen['record.json']['priority']),'benchmark_reuse_basis':'Exact same CPU/D4/CUDA adapter, engine and branch function; same locks, environment, threads and device; original qualified geometries cover every fixed follow-up job. New selected fields additionally replayed on CPU and one disposable CPU/device continuation step. New commit changes selection/reporting only.'}
    save(out/'audit.json',result);(out/'audit.json.sha256').write_text(sha(out/'audit.json')+'\n');log('Local selected-field audit passed',receipt=str(out/'audit.json'));return result
