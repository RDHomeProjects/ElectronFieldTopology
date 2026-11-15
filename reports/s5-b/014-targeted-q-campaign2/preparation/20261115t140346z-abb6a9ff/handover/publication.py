"""Record-only publication, executed exclusively on the local workstation."""
import argparse, hashlib, json, shutil, subprocess, sys, zipfile, re
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
REPO='RDHomeProjects/ElectronFieldTopology'
BRANCH='analysis/targeted-q-campaign2-20261115'
RUN='20261114t132254z-9e6c35d4'
ASSESSMENT_ID='20261114t231325z-431f3acf'
LEGACY_PACKAGE_SHA256='4876326d669f8cbe55066344112187b49b824fcc1c03d2adad6a439469a1d7e1'
EVIDENCE='c4215257a2a52622866ada5847378eeefd89147d0aaad2a8da0b44741bf1f605'
SOURCE='cffd6fc10c84a50b0a0dcce768b965a9aa5e7b09'
def stamp():
 n=datetime.now(timezone.utc);return {'utc':n.isoformat(),'melbourne':n.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def event(message,**kw):print(json.dumps({'recorded_at':stamp(),'message':message,**kw}),flush=True)
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(args,cwd,capture=False):
 args=list(map(str,args));event('Command',argv=args)
 r=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE if capture else None,stderr=subprocess.PIPE if capture else None)
 need(r.returncode==0,'Command failed: '+repr(args)+ ('\n'+r.stderr if capture else ''))
 return r.stdout.strip() if capture else ''
def verify(run=None):
 from support import verify_package
 verify_package();archive=ROOT/'data/completed-evidence.zip';need(sha(archive)==EVIDENCE,'Unexpected completed evidence')
 with zipfile.ZipFile(archive) as z:
  need(z.testzip() is None,'Completed ZIP CRC failure');names=z.namelist();seen=[]
  for line in z.read('SHA256SUMS').decode().splitlines():
   h,n=line.split('  ',1);need(hashlib.sha256(z.read(n)).hexdigest()==h,'Completed archive member differs: '+n);seen.append(n)
  need(set(seen)|{'SHA256SUMS'}==set(names) and len(names)==len(set(names)),'Completed compact coverage differs')
  r=json.loads(z.read('record.json'));need(r['status']=='complete_pending_review' and r['additional_steps']==600,'Completed outcome differs')
 if run:need(sha(Path(run)/'evidence.zip')==EVIDENCE,'Supplied completed run differs')
 event('Campaign package and completed evidence verified',compact_hashes=len(seen));return r

def marker(dest):return dest/'.git/campaign2-publication.json'
def clean(dest):return not cmd(['git','status','--porcelain'],dest,True)
def fingerprint(dest):
 names=cmd(['git','diff','--cached','--name-only','-z'],dest,True).split('\0')
 return {n:sha(dest/n) for n in names if n}
def manifest(folder):
 (folder/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(folder).as_posix()+'\n' for p in sorted(folder.rglob('*')) if p.is_file() and p!=folder/'SHA256SUMS'))
def apply(dest,m):
 roadmap=dest/'docs/project/roadmap.json';d=load(roadmap);existing=next((x for x in d['studies'] if x['slug']=='rapid-q-bounded-followup'),None);need(existing,'Published bounded follow-up study is missing')
 assessment_id='20261115t112200z-c4215257';rel=Path('reports')/existing['stage']/f"{existing['number']:03d}-{existing['slug']}"/'assessments'/assessment_id;folder=dest/rel;folder.mkdir(parents=True,exist_ok=True)
 rec={'study_id':existing['id'],'record_id':assessment_id,'role':'assessment','recorded_at':m['installed_at'],'source_commit':m['base'],'outcome':'Targeted campaign completed600 steps; no strict survivor; Q8 near gate, Q10 late rebound, Q5 resolution/restart sensitivity, Q4/Q6 core residual diagnosis','input_sha256':{'completed_targeted_evidence':EVIDENCE},'field_retention':'20 new full NPZ files remain local; compact evidence is not a full-field backup','limitations':['AI-assisted analysis, not independent scientific peer review','Full fields not independently replayed by remote assessment','No motion or physical electron acceptance']}
 if (folder/'record.json').exists():need(load(folder/'record.json')==rec,'Existing assessment differs')
 save(folder/'record.json',rec)
 (folder/'README.md').write_text((ROOT/'ASSESSMENT.md').read_text().replace('data/completed-evidence.zip','evidence.zip'))
 for source,target in [('ASSESSMENT.html','ASSESSMENT.html'),('ASSESSMENT.json','ASSESSMENT.json'),('data/completed-evidence.zip','evidence.zip')]:shutil.copyfile(ROOT/source,folder/target)
 manifest(folder);entry={'role':'assessment','path':(rel/'README.md').as_posix(),'label':'Completed targeted600-step analysis: Q8 near gate, Q10 rebound, Q5 domain limits'}
 if not any(x['path']==entry['path'] for x in existing['records']):existing['records'].append(entry)
 existing.update(state='assessed',gate='open',finding='Targeted600-step campaign completed; no strict survivor. Q8 force passes but acceleration1.203x limit. Q10 worsened late; finer Q5 retains tail failure. Original gates and all unresolved findings preserved.',next_action='Use separately registered campaign2 for user-requested Q8/Q10 continuation, Q4 conjugacy-memory comparison and fixed-spacing Q5 domain test.')
 slug='targeted-q-campaign2';new=next((x for x in d['studies'] if x['slug']==slug),None)
 if new is None:
  number=max(x['number'] for x in d['studies'] if x['stage']=='s5-b')+1;spec='docs/models/targeted-q-campaign2-20261115.md'
  new={'id':f's5-b-{number:03d}','stage':'s5-b','number':number,'slug':slug,'title':'Targeted Q8 Q10 continuation and controlled Q4 Q5 comparisons','state':'prepared','gate':'open','question':'Can recent-progress-bounded continuation and single-variable optimizer/domain controls clarify admission while preserving every scientific gate?','finding':'Prepared only; production outcomes pending. Completed targeted600-step evidence and assessment recorded separately.','next_action':'Qualify local CPU/GPU endpoints, then Q8 +150 and at most two recent-progress-conditional +50 batches (250 maximum); Q10 +150 before read-only diagnosis; Q4 exact versus memory-cleared +50 each with alpha held equal; Q5 fixed-spacing domain control +50 each. No Q6 relaxation yet.','exit_evidence':'600 added accepted production steps maximum; all original gates, source hashes, paired controls, full fields, failed/unresolved outcomes, timing components and Q6/Q7/Q9 deferrals retained; no automatic motion.','depends_on':[existing['id']],'requirements':['SCI-001','SCI-003','SCI-004','NUM-001','NUM-003','SRCH-001','SRCH-002','REP-001','REP-002'],'specifications':[spec],'records':[]};d['studies'].append(new)
 else:need(new['state']=='prepared','Campaign study already progressed; preserve and reconcile')
 spec=dest/new['specifications'][0];spec.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'MODEL.md',spec)
 t=datetime.fromisoformat(m['installed_at']['utc']);rid=t.strftime('%Y%m%dt%H%M%Sz-')+m['package_sha256'][:8];pr=Path('reports')/new['stage']/f"{new['number']:03d}-{new['slug']}"/'preparation'/rid;pf=dest/pr;pf.mkdir(parents=True,exist_ok=True)
 save(pf/'record.json',{'study_id':new['id'],'record_id':rid,'role':'preparation','recorded_at':m['installed_at'],'source_commit':m['base'],'outcome':'Controlled campaign prepared; production pending','input_sha256':{'completed_targeted_evidence':EVIDENCE},'handover_sha256':m['package_sha256'],'limitations':['Preparation does not certify a scientific result','Mandatory local field and CPU/device qualification before production']})
 (pf/'README.md').write_text('# Prepared controlled campaign2\n\n[Model and budgets](../../../../../'+new['specifications'][0]+') · [Frozen plan](PLAN.json) · [Local handover](handover/README.md)\n\nQ8 +150 then up to two conditional +50 batches (250 maximum); Q10 +150 then diagnosis; Q4 two matched50-step arms, clearing only conjugacy memory in the trial; Q5 two matched50-step domains at spacing0.192. Q6 unallocated; Q7/Q9 deferred. All gates unchanged; no automatic motion.\n')
 shutil.copyfile(ROOT/'PLAN.json',pf/'PLAN.json');shutil.copytree(ROOT,pf/'handover',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'));manifest(pf)
 entry={'role':'preparation','path':(pr/'README.md').as_posix(),'label':'Frozen campaign2 plan with mandatory local CPU/GPU qualification'}
 if not any(x['path']==entry['path'] for x in new['records']):new['records'].append(entry)
 # Keep unrelated priorities in order. Replace the assessed study in its slot.
 priority=d.get('priority',[])
 if new['id'] not in priority:
  if existing['id'] in priority:priority=[new['id'] if x==existing['id'] else x for x in priority]
  else:priority.append(new['id'])
 d['priority']=priority;d['updated_at']=m['installed_at']
 if d.get('current',{}).get('latest_assessed_study')==existing['id']:d['current']={'latest_assessed_study':existing['id'],'summary':existing['finding'],'limits':'No strict survivor or motion. Campaign2 prepared; all new outcomes pending.'}
 save(roadmap,d);m.update(assessment_path=str(rel),preparation_path=str(pr),study_id=new['id']);return m

def checks(dest,m):
 cmd([sys.executable,'scripts/project_records.py','render'],dest)
 cmd(['git','add','--','README.md','docs','reports'],dest)
 cmd([sys.executable,'scripts/project_records.py','check','--compare-ref',m['base']],dest)
 cmd([sys.executable,'scripts/check_docs.py'],dest)
 cmd(['git','diff','--cached','--check'],dest)

ORIGINAL_PACKAGE_SHA256='abb6a9ff27588edbf7b6d4d7cb114ea79c3aec52ff2784ad37126b4565822cc3'
def repair_original_preparation(dest,m,pkg):
 need(m['package_sha256']==ORIGINAL_PACKAGE_SHA256 and m['phase']=='applied' and not m.get('commit') and not m.get('pr'),'Only the exact original uncommitted failed preparation can be upgraded')
 need(cmd(['git','rev-parse','HEAD'],dest,True)==m['base'],'Publication HEAD changed; preserve and reconcile')
 need(not cmd(['git','diff','--name-only'],dest,True),'Unstaged changes exist; preserve and reconcile')
 rel=Path(m['preparation_path']);folder=(dest/rel).resolve();need(folder.is_relative_to(dest.resolve()) and folder.is_dir(),'Preparation path differs')
 rec=load(folder/'record.json');need(rec['handover_sha256']==ORIGINAL_PACKAGE_SHA256,'Original preparation provenance differs')
 covered=set()
 for line in (folder/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);f=(folder/n).resolve();need(f.is_relative_to(folder) and n not in covered and f.is_file() and sha(f)==h,'Staged preparation changed: '+n);covered.add(n)
 actual={f.relative_to(folder).as_posix() for f in folder.rglob('*') if f.is_file() and f!=folder/'SHA256SUMS'}
 need(actual-covered=={'handover/SHA256SUMS'} and not covered-actual,'Checksum discrepancy differs from the known nested-manifest omission')
 # Validate the previously omitted file against the package identity too.
 need(sha(folder/'handover/SHA256SUMS')==ORIGINAL_PACKAGE_SHA256,'Original nested handover checksum file changed')
 backup=dest/'.git/campaign2-before-nested-checksum-repair';need(not backup.exists(),'Repair backup already exists; preserve it for reconciliation')
 backup.mkdir();shutil.copytree(folder,backup/'preparation');shutil.copy2(marker(dest),backup/'publication.json');shutil.copy2(dest/'docs/project/roadmap.json',backup/'roadmap.json')
 patch=subprocess.run(['git','diff','--cached','--binary'],cwd=dest,check=True,capture_output=True).stdout;(backup/'staged.patch').write_bytes(patch)
 shutil.copytree(ROOT,folder/'handover',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 rec.update(handover_sha256=pkg,original_handover_sha256=ORIGINAL_PACKAGE_SHA256,repair_recorded_at=stamp());save(folder/'record.json',rec);manifest(folder)
 m.update(package_sha256=pkg,original_package_sha256=ORIGINAL_PACKAGE_SHA256,repair_backup=str(backup));save(marker(dest),m)
 event('Repaired nested preparation checksum coverage',preparation=str(folder),backup=str(backup));return m

def install(args):
 verify(args.run);dest=args.publication;pkg=sha(ROOT/'SHA256SUMS')
 if dest.exists():
  need(marker(dest).is_file(),'Publication directory exists without this handover marker; choose a new --repo path')
  m=load(marker(dest))
  if m['package_sha256']!=pkg:m=repair_original_preparation(dest,m,pkg)
 else:
  origin=cmd(['git','remote','get-url','origin'],args.repo,True)
  need(origin.rstrip('/').removesuffix('.git').lower() in ['https://github.com/rdhomeprojects/electronfieldtopology','git@github.com:rdhomeprojects/electronfieldtopology'],'Unexpected source origin')
  cmd(['git','clone','--no-hardlinks',args.repo,dest],args.repo)
  m={'package_sha256':pkg,'installed_at':stamp(),'phase':'cloned','origin':origin};save(marker(dest),m)
 if m['phase']=='cloned':
  need(clean(dest),'Partial clone changed; preserve it and reconcile')
  cmd(['git','remote','set-url','origin',m['origin']],dest);cmd(['git','fetch','origin','main'],dest)
  cmd(['git','switch','-c',BRANCH,'origin/main'],dest)
  m.update(base=cmd(['git','rev-parse','HEAD'],dest,True),phase='base');save(marker(dest),m)
 if m['phase']=='base':
  need(clean(dest),'Unrecorded edits in publication checkout')
  cmd(['git','merge-base','--is-ancestor',SOURCE,m['base']],dest)
  m['phase']='applying';save(marker(dest),m)
 if m['phase']=='applying':
  m=apply(dest,m);m['phase']='applied';save(marker(dest),m)
 if m['phase']=='applied':
  checks(dest,m);m.update(phase='staged',staged=fingerprint(dest));save(marker(dest),m)
 if m['phase']=='staged':
  need(fingerprint(dest)==m['staged'] and not cmd(['git','diff','--name-only'],dest,True),'Staged publication changed')
 event('Record-only publication prepared',checkout=str(dest),phase=m['phase'],assessment_path=m.get('assessment_path'));return m

def publish(args):
 m=install(args);dest=args.publication
 if m.get('merged'):event('Already merged',url=m['pr']['url']);return
 cmd(['gh','auth','status'],dest)
 if m['phase']=='staged':
  cmd(['git','commit','-m','Assess targeted Q results and prepare controlled campaign2'],dest)
  m.update(phase='committed',commit=cmd(['git','rev-parse','HEAD'],dest,True));save(marker(dest),m)
 need(clean(dest) and cmd(['git','rev-parse','HEAD'],dest,True)==m['commit'],'Publication checkout changed')
 cmd(['git','fetch','origin','main'],dest)
 need(cmd(['git','rev-parse','origin/main'],dest,True)==m['base'],'Main advanced: preserve this checkout and reconcile before publishing; no forced reset or push is performed')
 cmd(['git','push','-u','origin',BRANCH],dest)
 body=dest/'.git/pr-body.md';body.write_text((ROOT/'PR-BODY.md').read_text())
 prs=json.loads(cmd(['gh','pr','list','--repo',REPO,'--head',BRANCH,'--state','all','--json','number,state,headRefOid,url'],dest,True))
 if not prs:
  cmd(['gh','pr','create','--repo',REPO,'--base','main','--head',BRANCH,'--title','Assess targeted Q results and prepare Q8 Q10 Q4 Q5 campaign2','--body-file',body],dest)
  pr=json.loads(cmd(['gh','pr','view',BRANCH,'--repo',REPO,'--json','number,state,headRefOid,url'],dest,True))
 else:need(len(prs)==1,'Ambiguous PR');pr=prs[0]
 need(pr['headRefOid']==m['commit'] and pr['state']=='OPEN','Existing PR differs or is closed')
 m['pr']=pr;save(marker(dest),m);event('Results and analysis PR ready',url=pr['url'])
def merge(args):
 verify();dest=args.publication;m=load(marker(dest));need(m.get('pr'),'Publish first');n=str(m['pr']['number'])
 pr=json.loads(cmd(['gh','pr','view',n,'--repo',REPO,'--json','state,headRefOid,url'],dest,True));need(pr['headRefOid']==m['commit'],'PR head changed')
 if pr['state']!='MERGED':
  need(pr['state']=='OPEN','PR is not open')
  cmd(['gh','pr','checks',n,'--repo',REPO,'--watch','--interval','15'],dest)
  cmd(['gh','pr','merge',n,'--repo',REPO,'--squash','--match-head-commit',m['commit']],dest)
  pr=json.loads(cmd(['gh','pr','view',n,'--repo',REPO,'--json','state,headRefOid,url'],dest,True))
 need(pr['state']=='MERGED','Merge not confirmed');m['merged']={'recorded_at':stamp(),**pr};m['pr']=pr;m['phase']='merged';save(marker(dest),m);event('Completed results and assessment merged',url=pr['url'])
