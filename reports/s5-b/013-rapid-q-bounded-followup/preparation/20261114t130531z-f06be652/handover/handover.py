import argparse,os,sys,json,secrets,signal,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from runtime import ROOT,CFG,stamp,load,save,sha,event,need,package_check,source_check,verify_inputs
from science.common import active_jobs

def identifier():return datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4)
def alive(pid,out):
    try:
        os.kill(pid,0);cmd=(Path('/proc')/str(pid)/'cmdline').read_bytes().replace(b'\0',b' ').decode();return 'followup_worker.py' in cmd and str(out) in cmd
    except (OSError,UnicodeError):return False

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['verify','install','publish','merge','preflight','qualify','audit','run','resume','status','stop']);p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-rapid-q-screen');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-rapid-q-followup');p.add_argument('--source-run',type=Path);p.add_argument('--past-run',type=Path,default=Path.home()/'ElectronFieldTopology-repository-admin'/CFG['legacy_run_relative']);a=p.parse_args();repo=a.repo.expanduser().resolve();dest=a.publication.expanduser().resolve();past=a.past_run.expanduser().resolve();runpointer=dest/'artifacts/RAPID-Q-FOLLOWUP-CURRENT';auditpointer=dest/'artifacts/RAPID-Q-FOLLOWUP-AUDIT'
    if a.mode not in ['status','stop','preflight']:package_check()
    if a.mode=='merge':
        import publication
        publication.merge(dest);return 0
    current=Path(runpointer.read_text().strip()) if runpointer.exists() else None
    if a.mode in ['status','stop']:
        if current is None:event('Follow-up has not started');return 0
        status=load(current/'status.json') if (current/'status.json').exists() else {};launch=load(current/'launch.json') if (current/'launch.json').exists() else {};pid=next((pid for pid in [status.get('pid'),launch.get('launcher_pid')] if pid and alive(pid,current)),None)
        if a.mode=='stop' and pid:os.kill(pid,signal.SIGTERM);event('Graceful follow-up stop requested',output=str(current));return 0
        event('Follow-up status',**{**status,'runner_alive':pid is not None,'heartbeat':load(current/'heartbeat.json') if (current/'heartbeat.json').exists() else None,'output':str(current),'log':str(current/'runner.log')});return 0
    if a.mode=='preflight':event('Read-only follow-up preflight',active_eft_jobs=active_jobs(),source_checkout=str(repo),publication_checkout=str(dest));return 0
    if a.mode in ['verify','install','publish']:
        source_check(repo);pointer=repo/'artifacts/RAPID-Q-SCREEN-CURRENT';source=(a.source_run or (Path(pointer.read_text().strip()) if pointer.exists() else None));need(source is not None,'Supply --source-run pointing to the completed rapid screen');source=source.expanduser().resolve();verify_inputs(source,past,full=a.mode=='verify')
        if a.mode=='verify':event('Follow-up inputs verified',source_run=str(source),past_run=str(past));return 0
        import publication
        if a.mode=='install':publication.install(repo,dest,source,past)
        else:publication.publish(repo,dest,source,past)
        return 0
    need((dest/'.git/rapid-followup-merged.json').is_file(),'Publish and merge the assessment/follow-up preparation first');m=load(dest/'.git/rapid-followup-handover.json');source=(a.source_run or Path(m['source_run'])).expanduser().resolve();need(str(past)==m['past_run'],'Use the same --past-run as publication');source_check(dest,installed=True)
    if current:
        status=load(current/'status.json') if (current/'status.json').exists() else {};launch=load(current/'launch.json') if (current/'launch.json').exists() else {}
        if any(pid and alive(pid,current) for pid in [status.get('pid'),launch.get('launcher_pid')]):event('Follow-up already running',output=str(current));return 0
        if a.mode=='resume' and status.get('status')=='complete_pending_review':event('Follow-up already complete_pending_review',output=str(current));return 0
    jobs=active_jobs();need(not jobs,'Another EFT analysis is active; leave it running. Active processes: '+str(jobs));env=os.environ.copy();threads=os.environ.get('EFT_THREADS','4');need(threads=='4','The retained device receipt requires EFT_THREADS=4')
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:env[key]=threads
    uv=['uv','run','--frozen','--python','3.12.14']
    if a.mode in ['audit','run','resume']:uv+=['--extra','gpu']
    cmd=uv+['python',str(ROOT/'followup_worker.py')]
    if a.mode=='qualify':return subprocess.run(cmd+['qualify','--repo',str(dest)],cwd=dest,env=env).returncode
    if a.mode=='audit':
        out=dest/'artifacts/rapid-q-followup-audit'/identifier();result=subprocess.run(cmd+['audit','--repo',str(dest),'--source-run',str(source),'--past-run',str(past),'--output',str(out)],cwd=dest,env=env)
        if result.returncode==0:auditpointer.parent.mkdir(parents=True,exist_ok=True);auditpointer.write_text(str(out/'audit.json')+'\n');event('Follow-up audit receipt ready',receipt=str(out/'audit.json'))
        return result.returncode
    need(auditpointer.is_file(),'Run audit first');receipt=Path(auditpointer.read_text().strip())
    if a.mode=='resume':need(current is not None,'No follow-up run to resume');out=current
    else:out=dest/'artifacts/rapid-q-followup'/identifier();out.mkdir(parents=True);runpointer.parent.mkdir(parents=True,exist_ok=True);runpointer.write_text(str(out)+'\n')
    argv=cmd+['run','--repo',str(dest),'--source-run',str(source),'--past-run',str(past),'--output',str(out),'--audit-receipt',str(receipt)]
    with (out/'runner.log').open('a') as log:proc=subprocess.Popen(argv,cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    save(out/'launch.json',{'recorded_at':stamp(),'launcher_pid':proc.pid,'argv':argv});time.sleep(.5);event('Bounded follow-up started',output=str(out),log=str(out/'runner.log'));return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as e:event('Follow-up handover stopped',error=str(e));raise SystemExit(1)
