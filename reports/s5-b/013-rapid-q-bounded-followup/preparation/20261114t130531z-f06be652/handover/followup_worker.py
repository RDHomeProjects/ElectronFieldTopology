import argparse,sys,os,json
from pathlib import Path
from runtime import ROOT,load,save,stamp,source_check
p=argparse.ArgumentParser();p.add_argument('mode',choices=['audit','run','qualify']);p.add_argument('--repo',type=Path,required=True);p.add_argument('--source-run',type=Path);p.add_argument('--past-run',type=Path);p.add_argument('--output',type=Path);p.add_argument('--audit-receipt',type=Path);a=p.parse_args();repo=a.repo.resolve();sys.path.insert(0,str(repo/'src'))

try:
    source_check(repo,installed=True)
    if a.mode=='qualify':
        from electron_field_topology.rapid_q_screen.qualification import qualify
        from science.selection import select_prior,allocation_ledger
        from runtime import inputs
        screen,past=inputs();plan=screen['record.json']['plan'];chosen={}
        for seed_id in ['q4-axial22','q7-trefoil']:
            rows=[(k,v) for k,v in past['rest'].items() if v['seed_id']==seed_id];chosen[seed_id]=select_prior(rows,plan)['primary_rest_id']
        assert chosen=={'q4-axial22':'q4-axial22-medium-fresh','q7-trefoil':'q7-trefoil-medium-fresh'}
        ledger=allocation_ledger(screen['record.json']['broad'],screen['record.json']['priority']);assert any(v['seed']=='q5-trefoil32-1-1' and v['allocation_status']=='deferred_priority_capacity' for v in ledger)
        print(json.dumps({'recorded_at':stamp(),'selection':chosen,'host_kernels':qualify(),'cuda_executed':False},indent=2));raise SystemExit(0)
    from science.common import active_jobs
    jobs=active_jobs()
    if jobs:raise RuntimeError('Another EFT job is active; leave it running and start follow-up after it finishes: '+str(jobs))
    if a.mode=='audit':
        from science.audit import run_audit
        run_audit(repo,a.source_run.resolve(),a.past_run.resolve(),a.output.resolve())
    else:
        from science.runner import run
        run(repo,a.source_run.resolve(),a.past_run.resolve(),a.output.resolve(),a.audit_receipt.resolve())
except BaseException as e:
    if isinstance(e,SystemExit) and e.code in (None,0):raise
    if a.output is not None:
        target=a.output.resolve();target.mkdir(parents=True,exist_ok=True);old=load(target/'status.json') if (target/'status.json').exists() else {}
        save(target/'status.json',{**old,'recorded_at':stamp(),'status':'interrupted' if isinstance(e,KeyboardInterrupt) else 'failed','pid':os.getpid(),'error':str(e)})
    raise
