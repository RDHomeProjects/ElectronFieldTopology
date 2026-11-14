"""Local-only publication of the immutable assessment and bounded follow-up."""
import json,os,secrets,shutil,sys,subprocess,time,zipfile
from pathlib import Path
from datetime import datetime,timezone
from runtime import ROOT,CFG,stamp,load,save,sha,event,need,command,source_check,inputs

def identifier():return datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4)
def manifest(folder):
    (folder/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.relative_to(folder).as_posix()+'\n' for f in sorted(folder.rglob('*')) if f.is_file() and f!=folder/'SHA256SUMS'))
def record(folder,study,rid,role,base,outcome,body,extra=None):
    folder.mkdir(parents=True,exist_ok=True);save(folder/'record.json',{'study_id':study['id'],'record_id':rid,'role':role,'recorded_at':stamp(),'source_commit':base,'outcome':outcome,'input_sha256':{'completed_screen':CFG['screen_evidence_sha256'],'original_survey':CFG['prior_evidence_sha256']},'model_and_units':'Unchanged neutral SF D4 action; float64, dimensionless model units; optimizer iterations are not physical time','field_retention':'Original full fields remain in their existing local artifacts; new continuation fields remain in the separate follow-up clone','limitations':['AI-assisted analysis, not independent scientific peer review','Completed compact evidence assessed; new local field/device audit is mandatory before continuation','No Q rejection, gate relaxation, motion or physical acceptance implied'],**(extra or {})});(folder/'README.md').write_text(body+'\n');manifest(folder)
def loc(study,kind,rid):return Path('reports')/study['stage']/f"{study['number']:03d}-{study['slug']}"/kind/rid

def apply(repo,base):
    data=load(repo/'docs/project/roadmap.json');screen=next((s for s in data['studies'] if s['slug']=='rapid-q-screening'),None);need(screen,'Published rapid screening study is missing');need(not any(s['slug']=='rapid-q-bounded-followup' for s in data['studies']),'Follow-up study already registered; preserve and reconcile')
    # Publish the completed raw compact evidence and immutable assessment.
    rid=identifier();rel=loc(screen,'assessments',rid);folder=repo/rel
    record(folder,screen,rid,'assessment',base,'completed bounded screen; CUDA controls passed; no newly stationary candidate; selection/reporting limitations identified','# Completed rapid Q screen assessment\n\n[Browser assessment with plotted histories](ASSESSMENT.html) · [Original compact evidence](evidence.zip) · [Corrected selection and allocation ledger](CORRECTIONS.json)\n\nThe 89.27-minute screen covered 30 variants / 15 Q magnitudes, reused seven endpoints and extended four branches. CUDA passed recorded controls and was selected on 97/121/145 cubed. No new strict survivor, mesh confirmation or motion followed. All 195 compact hashes and 55 result seals agree; full fields were not replayed by the remote assessment and stay local.\n\nThe coarsest unresolved reuse rule hid better medium Q4/Q7 endpoints. Q5 trefoil was an eligible capacity omission; Q9/Q10 trefoil seeds sit just outside the compute cutoff. None is a physical Q rejection. Preserve all original outcomes and gates.\n\nA new study records representation-first prior selection, explicit capacity/budget ledgers and fixed-configuration continuation. New local full-field/device checks precede computation.')
    shutil.copy2(ROOT/'ASSESSMENT.html',folder/'ASSESSMENT.html');shutil.copy2(ROOT/'data/completed-screen-evidence.zip',folder/'evidence.zip');shutil.copy2(ROOT/'ASSESSMENT.json',folder/'ASSESSMENT.json');shutil.copy2(ROOT/'CORRECTIONS.json',folder/'CORRECTIONS.json');manifest(folder);screen['records'].append({'role':'assessment','path':(rel/'README.md').as_posix(),'label':'Completed rapid screen, qualified GPU and retained selection/deferral limitations'});screen.update(state='assessed',gate='open',finding='30 variants over Q2-Q16; seven prior states reused; four branches extended; no newly stationary survivor or motion. CUDA controls passed. Coarsest unresolved reuse masked better medium Q4/Q7 endpoints; capacity and exhausted budgets need explicit reporting.',next_action='Use the separately registered bounded follow-up; retain all original evidence, original gates and unresolved states.')
    number=max(s['number'] for s in data['studies'] if s['stage']=='s5-b')+1;sid=f's5-b-{number:03d}';spec='docs/models/rapid-q-bounded-followup-20261114.md'
    study={'id':sid,'stage':'s5-b','number':number,'slug':'rapid-q-bounded-followup','title':'Fixed-configuration Q6 continuation, medium Q4 Q7 reassessment and bounded controls','state':'prepared','gate':'open','question':'Can a declared additional preparation budget recover strict survivors while preserving gates, geometry, optimizer identity and all deferrals?','finding':'Completed rapid screen assessed; representation-first legacy selection and explicit allocation reporting prepared. Additional candidate outcomes remain unmeasured.','next_action':'Run the local field/device audit, then Q6 +200, medium Q4/Q7 +100 each, secondary Q8 +100, and Q5/Q9/Q10 controls +50 each, all in batches of at most 50. Stop measured survivors for later mesh/boost/motion admission.','exit_evidence':'650 additional accepted steps maximum, unchanged action and all scientific gates; exact continuation for screen states, declared optimizer restart for legacy imports, all failures/deferrals and full states retained; no automatic mesh or motion.','depends_on':[screen['id']],'requirements':['SCI-001','SCI-003','SCI-004','NUM-001','NUM-003','SRCH-001','SRCH-002','REP-001','REP-002'],'specifications':[spec],'records':[]};data['studies'].append(study)
    target=repo/'src/electron_field_topology/rapid_q_followup';need(not target.exists(),'Follow-up namespace exists');shutil.copytree(ROOT/'science',target,ignore=shutil.ignore_patterns('__pycache__'))
    old=repo/'src/electron_field_topology/rapid_q_screen/runner.py';need(sha(old)==CFG['original_code_sha256']['runner.py'],'Existing screen runner changed');shutil.copy2(ROOT/'patches/runner.py',old)
    shutil.copy2(ROOT/'MODEL.md',repo/spec);shutil.copy2(ROOT/'FOLLOWUP.json',repo/'experiments/configs/rapid-q-followup-20261114.json');shutil.copy2(ROOT/'tests/test_rapid_q_followup.py',repo/'tests/test_rapid_q_followup.py')
    prep=identifier();pr=loc(study,'preparation',prep);pf=repo/pr;record(pf,study,prep,'preparation',base,'bounded continuation and correction controls prepared; production pending','# Prepared fixed-configuration follow-up\n\nQ6 +200; medium Q4/Q7 +100 each; secondary Q8 +100; Q5/Q9/Q10 controls +50 each. Total ≤650 additional accepted steps in batches ≤50.\n\nAll original static/representation/tail gates remain fixed. Screen imports retain conjugacy, step length and adaptive schedule. Legacy Q4/Q7 field imports explicitly restart conjugacy and step length while retaining native iteration provenance. No automatic mesh refinement or motion.\n\n[Host validation](HOST-VALIDATION.json) and [frozen plan](FOLLOWUP.json). The workstation must validate the full original field manifest, replay seven selected endpoints on CPU, and check one disposable CPU/device continuation step per endpoint before launch.')
    shutil.copy2(ROOT/'HOST-VALIDATION.json',pf/'HOST-VALIDATION.json');shutil.copy2(ROOT/'FOLLOWUP.json',pf/'FOLLOWUP.json');shutil.copytree(ROOT/'validation',pf/'validation');shutil.copytree(ROOT,pf/'handover',ignore=shutil.ignore_patterns('__pycache__'));manifest(pf);study['records'].append({'role':'preparation','path':(pr/'README.md').as_posix(),'label':'Frozen 650-step budget, selection/deferral correction and restart controls'})
    # Keep an unrelated active top priority and its current assessment. When this
    # screen was already first, its registered continuation takes that slot.
    oldpriority=[v for v in data['priority'] if v not in [screen['id'],sid]]
    if data['priority'] and data['priority'][0]!=screen['id']:data['priority']=oldpriority[:1]+[sid]+oldpriority[1:]
    else:data['priority']=[sid]+oldpriority
    data['current']={'latest_assessed_study':screen['id'],'summary':screen['finding'],'limits':'Compact evidence assessed; local full-field replay and bounded continuation pending. No new stationary candidate, spatial/domain closure, motion, electric charge or quantum spin claim.'}
    data['updated_at']=stamp();save(repo/'docs/project/roadmap.json',data);command([sys.executable,'scripts/project_records.py','render'],repo)
    return {'base':base,'studies':{'screening':screen['id'],'followup':sid}}

def marker(repo):return repo/'.git/rapid-followup-handover.json'
def fingerprint(repo):return {n:sha(repo/n) for n in command(['git','diff','--cached','--name-only','-z'],repo,True).split('\0') if n}
def checks(repo,base):
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='4'
    command([sys.executable,'scripts/project_records.py','check','--compare-ref',base],repo);command([sys.executable,'scripts/check_docs.py'],repo);command(['git','diff','--check'],repo)
    command(['uv','run','--frozen','--python','3.12.14','python','-m','pytest','-q','tests/test_rapid_q_followup.py','tests/test_rapid_q_screen.py','tests/test_rapid_q_gpu_adapter.py'],repo)
    command(['uv','run','--frozen','--python','3.12.14','python',ROOT/'followup_worker.py','qualify','--repo',repo],repo)

def install(source_repo,dest,source_run,past_run):
    if dest.exists():
        need(marker(dest).is_file(),'Publication path exists without this package marker; choose a new --publication path');m=load(marker(dest));need(m['package_sha256']==sha(ROOT/'SHA256SUMS') and m['source_run']==str(source_run) and m['past_run']==str(past_run),'Installed handover or input paths differ')
        if not m.get('commit'):need(fingerprint(dest)==m['staged'] and not command(['git','diff','--name-only'],dest,True),'Staged/unstaged publication changed')
        return m
    source_check(source_repo);origin=command(['git','remote','get-url','origin'],source_repo,True);need(origin.rstrip('/').removesuffix('.git').lower() in ['https://github.com/rdhomeprojects/electronfieldtopology','git@github.com:rdhomeprojects/electronfieldtopology'],'Unexpected origin')
    temp=dest.with_name(dest.name+'.installing');tm=temp/'.git/rapid-followup-clone.json';pkg=sha(ROOT/'SHA256SUMS')
    if temp.exists():need(tm.is_file() and load(tm)['package_sha256']==pkg,'Unknown/incompatible partial clone; preserve it and select a new publication path')
    else:
        command(['git','clone','--no-hardlinks',source_repo,temp]);save(tm,{'recorded_at':stamp(),'package_sha256':pkg,'phase':'clone','initial_head':command(['git','rev-parse','HEAD'],temp,True)})
    state=load(tm)
    if state['phase']=='clone':
        need(not command(['git','status','--porcelain'],temp,True),'Partial clone has unrelated working changes');need(command(['git','rev-parse','HEAD'],temp,True)==state.get('base',state['initial_head']),'Partial clone has unrelated commits; preserve and reconcile')
        command(['git','remote','set-url','origin',origin],temp)
        # A DNS/fetch failure retains this exact marked clean clone. Repeating
        # publish retries fetch; it never requires deleting or renaming a clone.
        command(['git','fetch','origin','main'],temp);command(['git','switch','-C',CFG['branch'],'origin/main'],temp);base=command(['git','rev-parse','HEAD'],temp,True);command(['git','merge-base','--is-ancestor',CFG['required_source_commit'],base],temp);source_check(temp);state['base']=base;save(tm,state)
        backup=dest.parent/(dest.name+'-before-followup.bundle')
        if backup.exists():need(state.get('backup_sha256')==sha(backup),'Unknown backup bundle exists; preserve and choose another publication path')
        else:command(['git','bundle','create',backup,'--all'],temp);command(['git','bundle','verify',backup],temp)
        state.update(base=base,backup=str(backup),backup_sha256=sha(backup));save(tm,state)
        m=apply(temp,base);command(['git','add','--','README.md','docs','reports','experiments/configs/rapid-q-followup-20261114.json','src/electron_field_topology/rapid_q_screen/runner.py','src/electron_field_topology/rapid_q_followup','tests/test_rapid_q_followup.py'],temp);m.update(package_sha256=pkg,source_run=str(source_run),past_run=str(past_run),staged=fingerprint(temp),commit=None,backup=str(backup),installed_at=stamp());save(marker(temp),m);state.update(phase='staged');save(tm,state)
    else:m=load(marker(temp));need(m['package_sha256']==pkg and fingerprint(temp)==m['staged'] and not command(['git','diff','--name-only'],temp,True),'Partial staged installation changed')
    checks(temp,m['base']);command(['git','diff','--cached','--check'],temp);temp.rename(dest);event('Follow-up assessment and preparation staged',checkout=str(dest),studies=m['studies']);return m

def publish(source_repo,dest,source_run,past_run):
    m=install(source_repo,dest,source_run,past_run);command(['gh','auth','status'],dest)
    if (dest/'.git/rapid-followup-merged.json').exists():event('Follow-up preparation already merged',url=load(dest/'.git/rapid-followup-merged.json')['url']);return
    if not m.get('commit'):
        need(fingerprint(dest)==m['staged'] and not command(['git','diff','--name-only'],dest,True),'Publication changed');command(['git','commit','-m','Assess completed rapid Q screen and prepare bounded fixed-configuration follow-up'],dest);m['commit']=command(['git','rev-parse','HEAD'],dest,True);save(marker(dest),m)
    need(command(['git','rev-parse','HEAD'],dest,True)==m['commit'] and not command(['git','status','--porcelain'],dest,True),'Publication checkout changed');command(['git','fetch','origin','main'],dest);need(command(['git','rev-parse','origin/main'],dest,True)==m['base'],'Main advanced after preparation; preserve this clone for reconciliation')
    command(['git','push','-u','origin',CFG['branch']],dest);body=dest/'.git/rapid-followup-pr.md';body.write_text('Record the completed 30-variant Q2-Q16 screen and its qualified static CUDA evidence, retaining all original failed and unresolved outcomes. No newly stationary candidate or motion followed.\n\nCorrect prior-state selection to prioritize measured representation and proximity to unchanged gates while retaining every alternative; explicitly report capacity omissions and exhausted budgets. Preserve the static D4 objective, optimizer branch, existing locks and all scientific thresholds.\n\nPrepare a separate fixed-configuration follow-up: Q6 +200, medium Q4/Q7 +100 each, secondary Q8 +100, and Q5/Q9/Q10 controls +50 each, in at most 50-step batches (650 additional accepted steps maximum). Require local full-field/metric/device checks before launch. No automatic mesh or motion.\n\nValidation: layout, immutable-record and documentation checks; selection/ledger and continuation tests; host numerical controls. Actual follow-up outcomes remain pending.\n')
    prs=json.loads(command(['gh','pr','list','--repo',CFG['repo'],'--head',CFG['branch'],'--state','all','--json','number,state,headRefOid,url'],dest,True))
    if prs:need(len(prs)==1 and prs[0]['state']=='OPEN' and prs[0]['headRefOid']==m['commit'],'Existing PR differs');pr=prs[0]
    else:
        command(['gh','pr','create','--repo',CFG['repo'],'--base','main','--head',CFG['branch'],'--title','Assess rapid Q screen and prepare bounded Q6 Q4 Q7 follow-up','--body-file',body],dest);pr=json.loads(command(['gh','pr','view',CFG['branch'],'--repo',CFG['repo'],'--json','number,state,headRefOid,url'],dest,True))
    m['pr']=pr;save(marker(dest),m);event('Follow-up PR ready',url=pr['url'])
def merge(dest):
    m=load(marker(dest));need(m.get('pr') and m.get('commit'),'Publish first');n=str(m['pr']['number']);pr=json.loads(command(['gh','pr','view',n,'--repo',CFG['repo'],'--json','state,headRefOid,mergeCommit,url'],dest,True));need(pr['headRefOid']==m['commit'],'PR head changed')
    if pr['state']!='MERGED':
        command(['gh','pr','checks',n,'--repo',CFG['repo'],'--watch','--interval','15'],dest);command(['gh','pr','merge',n,'--repo',CFG['repo'],'--squash','--match-head-commit',m['commit']],dest);pr=json.loads(command(['gh','pr','view',n,'--repo',CFG['repo'],'--json','state,headRefOid,mergeCommit,url'],dest,True))
    need(pr['state']=='MERGED','PR not merged');save(dest/'.git/rapid-followup-merged.json',{'recorded_at':stamp(),**pr});command(['git','fetch','origin','main'],dest);need(not command(['git','status','--porcelain'],dest,True),'Checkout has local changes');command(['git','switch','main'],dest);command(['git','merge','--ff-only','origin/main'],dest);event('Assessment and follow-up preparation merged',url=pr['url'])
