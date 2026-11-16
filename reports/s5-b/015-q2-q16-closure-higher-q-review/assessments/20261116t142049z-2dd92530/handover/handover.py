"""Record-only local publication of completed evidence and a focused desk review."""
import argparse,hashlib,json,re,shutil,subprocess,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
REPOSITORY='RDHomeProjects/ElectronFieldTopology'
BRANCH='analysis/q2-q16-closure-higher-q-review-20261117'
SLUG='q2-q16-closure-higher-q-review'
SOURCE='cffd6fc10c84a50b0a0dcce768b965a9aa5e7b09'
MARKER='q-range-closure-publication.json'
LEGACY_PACKAGE_SHA256='cbb443a8d8560952d266e315cc72f866e1d20f1d84e261d0229cf19fdac90269'
def stamp():
 n=datetime.now(timezone.utc);return {'utc':n.isoformat(),'melbourne':n.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def event(message,**kw):print(json.dumps({'recorded_at':stamp(),'message':message,**kw}),flush=True)
def need(ok,message):
 if not ok:raise RuntimeError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')
def files(folder):return {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
def verify_manifest(folder):
 covered=[]
 for line in (folder/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);p=(folder/n).resolve();need(p.is_relative_to(folder.resolve()) and p.is_file(),'Unsafe/missing manifested path: '+n)
  need(sha(p)==h,'Checksum differs: '+n);covered.append(n)
 need(len(covered)==len(set(covered)) and set(covered)==files(folder)-{'SHA256SUMS'},'Manifest coverage differs')
 return len(covered)
def manifest(folder):
 (folder/'SHA256SUMS').write_text(''.join(sha(folder/n)+'  '+n+'\n' for n in sorted(files(folder)-{'SHA256SUMS'})))
def verify():
 count=verify_manifest(ROOT);payloads=0
 for p in ROOT.rglob('*.csv'):
  need(b'\r' not in p.read_bytes(),'CSV must use LF: '+str(p.relative_to(ROOT)))
 for src in load(ROOT/'INPUTS.json')['sources']:
  p=ROOT/src['file'];need(sha(p)==src['sha256'],'Source archive identity differs')
  with zipfile.ZipFile(p) as z:
   names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Archive CRC or duplicate member failure')
   if 'SHA256SUMS' in names:
    pairs=[l.split('  ',1) for l in z.read('SHA256SUMS').decode().splitlines()]
    hashes={n:h for h,n in pairs};need(len(hashes)==len(pairs),'Duplicate compact hashes');exclude='SHA256SUMS'
   else:
    hashes=json.loads(z.read('evidence-hashes.json'))['sha256'];exclude='evidence-hashes.json'
   need(set(hashes)|{exclude}==set(names),'Compact member coverage differs')
   for n,h in hashes.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Compact payload differs: '+n)
   need(len(hashes)==src['compact_payloads_checked'],'Declared coverage differs');payloads+=len(hashes)
 with zipfile.ZipFile(ROOT/'data/rapid-screen-evidence.zip') as z:
  r=json.loads(z.read('record.json'));need(r['counts']['seed_variants']==30 and r['counts']['hard_Q_rejections']==0,'Unexpected screen scope')
 with zipfile.ZipFile(ROOT/'data/campaign2-evidence.zip') as z:
  r=json.loads(z.read('record.json'));need(r['additional_steps']==500 and r['q6_relaxation_steps']==0 and not r['motion_cases'],'Campaign2 disposition differs')
 with zipfile.ZipFile(ROOT/'data/decision-audit-evidence.zip') as z:
  r=json.loads(z.read('COMPARISON.json'));need(r['audit']['status']=='audit_passed' and r['decision']=='not_ready_within_final_declared_audit_park_unchanged_route','Audit disposition differs')
 c=load(ROOT/'Q2-Q16-CLOSURE.json');need([x['q'] for x in c['rows']]==list(range(2,17)) and not any(x['physical_Q_rejected'] for x in c['rows']),'Closure scope differs')
 event('Closure package and six compact archives verified',payload_files=count,compact_payloads=payloads,production_started=False)
 return c
def cmd(args,cwd,capture=False):
 args=list(map(str,args));event('Command',argv=args)
 r=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE if capture else None,stderr=subprocess.PIPE if capture else None)
 need(r.returncode==0,'Command failed: '+repr(args)+ ('\n'+r.stderr if capture else ''))
 return r.stdout.strip() if capture else ''
def marker(dest):return dest/'.git'/MARKER
def clean(dest):return not cmd(['git','status','--porcelain'],dest,True)
def fingerprint(dest):
 names=cmd(['git','diff','--cached','--name-only','-z'],dest,True).split('\0')
 return {n:sha(dest/n) for n in names if n}
def record_dir(study,rid):return Path('reports')/study['stage']/f"{study['number']:03d}-{study['slug']}"/'assessments'/rid
def entry(study,rel,label):
 e={'role':'assessment','path':(rel/'README.md').as_posix(),'label':label}
 if not any(x['path']==e['path'] for x in study['records']):study['records'].append(e)
def apply(dest,m):
 path=dest/'docs/project/roadmap.json';d=load(path)
 campaign=next((s for s in d['studies'] if s['slug']=='targeted-q-campaign2'),None)
 need(campaign,'Campaign2 study is absent; first merge its existing preparation handover')
 inputs=load(ROOT/'INPUTS.json');at=datetime.fromisoformat(inputs['recorded_at']['utc']);rid=at.strftime('%Y%m%dt%H%M%Sz-')+sha(ROOT/'INPUTS.json')[:8]
 need(re.fullmatch(r'\d{8}t\d{6}z-[a-f0-9]{8}',rid),'Invalid assessment record ID')
 review=next((s for s in d['studies'] if s['slug']==SLUG),None)
 if review is None:
  number=max(s['number'] for s in d['studies'] if s['stage']=='s5-b')+1
  review={'id':f's5-b-{number:03d}','stage':'s5-b','number':number,'slug':SLUG,'title':'Q2 to Q16 allocation closure and higher Q feasibility review','state':'assessed','gate':'open','question':'What did the completed Q2 to Q16 work establish, and does it justify a detailed long Q17 to Q32 campaign?','finding':'Completed allocations assessed; Q2 reference and Q3 stationary controls retained. No new motion-ready survivor from rapid screening and follow-ups. Final Q8 audit supports parking the unchanged route; higher Q structural diversity is supported but a full long campaign is not justified now.','next_action':'Make the model-purpose decision and specify a benchmark-first reproduction pilot before new higher Q allocation. No production run is prepared by this record.','exit_evidence':'Immutable compact evidence, complete Q-by-Q and seed ledgers, final gate metrics, source bibliography, explicit deferrals and a bounded-pilot decision; no physical Q exclusions.','depends_on':[campaign['id']],'requirements':['SCI-001','SCI-003','SCI-004','NUM-001','NUM-003','SRCH-001','SRCH-002','REP-001','REP-002'],'specifications':[],'records':[]}
  d['studies'].append(review)
 spec_rel='docs/models/q-range-closure-feasibility-20261117.md'
 if spec_rel not in review['specifications']:review['specifications'].append(spec_rel)
 rel=record_dir(review,rid);folder=dest/rel
 if folder.exists():need((folder/'record.json').is_file() and load(folder/'record.json').get('handover_sha256')==m['package_sha256'],'Existing closure record differs; preserve it')
 folder.mkdir(parents=True,exist_ok=True)
 save(folder/'record.json',{'study_id':review['id'],'record_id':rid,'role':'assessment','recorded_at':m['installed_at'],'source_commit':m['base'],'outcome':'Q2 to Q16 numerical allocations assessed and unchanged route parked; full Q17 to Q32 long survey deferred pending benchmark-first pilot and model-purpose decision','input_sha256':{Path(s['file']).name:s['sha256'] for s in inputs['sources']},'handover_sha256':m['package_sha256'],'limitations':['No physical rejection of any Q sector','No new full-field replay or new numerical trajectory','Q2/Q3 controls retained without long-time electron acceptance','Full fields stay in their original retained run trees; this is compact evidence']})
 shutil.copytree(ROOT,folder/'handover',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 (folder/'README.md').write_text('# Q-range closure and higher-Q feasibility assessment\n\n[Complete assessment](handover/ASSESSMENT.md) · [Browser report](handover/ASSESSMENT.html) · [Q-by-Q disposition](handover/Q2-Q16-CLOSURE.csv) · [Full seed ledger](handover/SCREEN-LEDGER.csv) · [Primary bibliography](handover/BIBLIOGRAPHY.md) · [Source identities](handover/INPUTS.json) · [Full-field retention references](handover/RETENTION.json)\n\nCompleted numerical allocations are assessed; the unchanged search/continuation route is parked. Scientific gate remains open. Q2 reference and Q3 controls are retained. No Q sector is physically rejected. No new production campaign or numerical source change is introduced.\n')
 manifest(folder);entry(review,rel,'Q2 to Q16 closure and evidence-based Q17 to Q32 feasibility decision')
 spec_file=dest/spec_rel;spec_file.parent.mkdir(parents=True,exist_ok=True)
 import os
 report_link=Path(os.path.relpath(folder/'handover/ASSESSMENT.md',spec_file.parent)).as_posix()
 bibliography_link=Path(os.path.relpath(folder/'handover/BIBLIOGRAPHY.md',spec_file.parent)).as_posix()
 spec_text='# Q-range closure and feasibility decision scope\n\nThis is an assessment of completed numerical allocations and a focused primary-literature review. It does not prepare or authorize a new numerical campaign. The scientific gate remains open.\n\n'+f'[Evidence, Q-by-Q dispositions and conditional pilot criteria]({report_link}) · [Primary references and applicability]({bibliography_link})\n\nPreserve the original force, acceleration, representation and boundary gates; retain Q2/Q3 controls and all negative or deferred outcomes. No Q sector is physically rejected. Future reproduction must declare one changing variable at a time, mesh/domain controls, measured joint-progress rules, retained fields and separate static/motion budgets. A broad Q17–Q32 long campaign remains deferred until a benchmark-first pilot demonstrates readiness and decision value.\n'
 if spec_file.exists():need(spec_file.read_text()==spec_text,'Existing decision scope differs; preserve it')
 else:spec_file.write_text(spec_text)
 # A canonical assessment under the existing campaign records its actual completion too.
 arid='20261116t075244z-c52af436';arel=record_dir(campaign,arid);af=dest/arel
 if af.exists():need((af/'record.json').is_file() and load(af/'record.json').get('handover_sha256')==m['package_sha256'],'Existing campaign assessment differs; preserve it')
 af.mkdir(parents=True,exist_ok=True)
 link=Path(os.path.relpath(folder/'handover',af)).as_posix()
 save(af/'record.json',{'study_id':campaign['id'],'record_id':arid,'role':'assessment','recorded_at':m['installed_at'],'source_commit':m['base'],'outcome':'Campaign2 completed500 of600 possible steps and final Q8 audit100 steps; no new strict survivor; unchanged route parked','handover_sha256':m['package_sha256'],'input_sha256':{Path(s['file']).name:s['sha256'] for s in inputs['sources'] if 'campaign2' in s['file'] or 'decision-audit' in s['file']},'limitations':['Campaign2 optional Q8 budget correctly withheld','No Q6 relaxation or motion','Final CG/LBFGS result is budget-limited, not universal Q or optimizer rejection']})
 (af/'README.md').write_text('# Completed campaign2 and final decision audit\n\nCampaign2 completed500 accepted steps; optional Q8 continuation100 was withheld under its recent-progress rule. Q4 memory-only reset did not recover endpoint readiness; Q5 fixed-spacing domain expansion still failed; Q10 late residual improvement did not persist. Q6/Q7/Q9 remain deferred.\n\nThe full-field identity audit passed for Q2/Q8. The subsequent paired Q8 comparison accepted50 CG and50 L-BFGS steps with unchanged grid, box and gates; neither yielded a jointly passing observation. The unchanged route is parked.\n\n'+f'[Full assessment]({link}/ASSESSMENT.md) · [Campaign2 report]({link}/data/campaign2-assessment.html) · [Audit report]({link}/data/decision-audit-assessment.html) · [Campaign2 compact evidence]({link}/data/campaign2-evidence.zip) · [Audit compact evidence]({link}/data/decision-audit-evidence.zip)\n')
 manifest(af);entry(campaign,arel,'Completed campaign2 plus final Q8 decision audit; unchanged route parked')
 affected=[]
 for s in d['studies']:
  if s['slug'] in ['rapid-q-screening','rapid-q-bounded-followup','targeted-q-campaign2']:
   affected.append(s['id']);s['state']='assessed';s['gate']='open'
   if s['slug']=='targeted-q-campaign2':s['finding']='Completed500 of600 possible steps; optional Q8 budget correctly withheld; no new strict survivor. Final Q2/Q8 consistency audit passed; paired Q8 CG and L-BFGS remained unresolved within their declared budgets.'
   s['next_action']='Allocation closed and unchanged route parked. Preserve fields, failures and deferrals; consult the Q-range closure and benchmark-first higher-Q feasibility assessment before new numerical work.'
 # Keep unrelated priorities in order, replacing only the affected route's first slot.
 prior=d.get('priority',[]);new=[];inserted=False
 for sid in prior:
  if sid in affected:
   if not inserted and review['id'] not in prior:new.append(review['id']);inserted=True
  else:new.append(sid)
 if not inserted and review['id'] not in new:new.append(review['id'])
 d['priority']=new
 if d.get('current',{}).get('latest_assessed_study') in affected:
  d['current']={'latest_assessed_study':review['id'],'summary':review['finding'],'limits':'Numerical allocation closure; Q sectors remain open. Benchmark-first desk recommendation only; no new production launch.'}
 d['updated_at']=m['installed_at'];save(path,d)
 m.update(assessment_path=rel.as_posix(),campaign_assessment_path=arel.as_posix(),study_id=review['id']);return m
def checks(dest,m):
 cmd([sys.executable,'scripts/project_records.py','render'],dest)
 cmd(['git','add','--','README.md','docs','reports'],dest)
 cmd([sys.executable,'scripts/project_records.py','check','--compare-ref',m['base']],dest)
 cmd([sys.executable,'scripts/check_docs.py'],dest)
 cmd(['git','diff','--cached','--check'],dest)
def upgrade_lf(dest,m,pkg):
 """Upgrade only the exact original uncommitted validation failure, with rollback backup."""
 need(m['package_sha256']==LEGACY_PACKAGE_SHA256 and m['phase']=='applied' and not m.get('commit') and not m.get('pr'),'Only the exact original uncommitted CSV validation failure can be repaired automatically')
 need(cmd(['git','rev-parse','HEAD'],dest,True)==m['base'],'Publication HEAD changed; preserve it')
 need(cmd(['git','branch','--show-current'],dest,True)==BRANCH,'Publication branch changed; preserve it')
 need(not cmd(['git','diff','--name-only'],dest,True),'Unstaged edits exist; preserve and reconcile them')
 need(not cmd(['git','ls-files','--others','--exclude-standard'],dest,True),'Untracked edits exist; preserve and reconcile them')
 folders=[]
 for key in ['assessment_path','campaign_assessment_path']:
  f=(dest/m[key]).resolve();need(f.is_relative_to((dest/'reports').resolve()) and f.is_dir(),'Unexpected assessment path')
  rec=load(f/'record.json');need(rec['handover_sha256']==LEGACY_PACKAGE_SHA256 and rec['source_commit']==m['base'] and rec['record_id']==f.name,'Original assessment identity differs')
  verify_manifest(f);folders.append(f)
 old_handover=folders[0]/'handover'
 need(sha(old_handover/'SHA256SUMS')==LEGACY_PACKAGE_SHA256,'Original staged handover manifest differs')
 need((old_handover/'SHA256SUMS').read_bytes()==(ROOT/'LEGACY-SHA256SUMS').read_bytes(),'Original manifest identity differs')
 verify_manifest(old_handover)
 import csv,io,uuid
 for name in ['SCREEN-LEDGER.csv','ENDPOINTS.csv','Q2-Q16-CLOSURE.csv']:
  before=(old_handover/name).read_bytes();after=(ROOT/name).read_bytes()
  need(before.replace(b'\r\n',b'\n')==after and b'\r' not in after,'CSV repair changes more than line endings: '+name)
  need(list(csv.reader(io.StringIO(before.decode())))==list(csv.reader(io.StringIO(after.decode()))),'CSV cell contents differ: '+name)
 # Prove all scientific evidence and assessment bytes are unchanged.
 for n in files(old_handover):
  if n.startswith('data/') or n in ['INPUTS.json','ASSESSMENT.html','ASSESSMENT.md','Q2-Q16-CLOSURE.json','SCREEN-LEDGER.json','ENDPOINTS.json','GATES.json','HIGH-Q-ASSESSMENT.json','BIBLIOGRAPHY.md','RETENTION.json','endpoint-gates.png']:
   need((ROOT/n).is_file() and sha(ROOT/n)==sha(old_handover/n),'Scientific record differs during formatting repair: '+n)
 backup=dest/'.git'/('q-range-before-lf-repair-'+uuid.uuid4().hex[:8]);backup.mkdir()
 shutil.copy2(marker(dest),backup/'publication.json')
 patch=subprocess.run(['git','diff','--cached','--binary'],cwd=dest,capture_output=True,check=True).stdout;(backup/'staged.patch').write_bytes(patch)
 for i,f in enumerate(folders):shutil.copytree(f,backup/('assessment-'+str(i)))
 save(backup/'receipt.json',{'recorded_at':stamp(),'original_package_sha256':LEGACY_PACKAGE_SHA256,'replacement_package_sha256':pkg,'paths':[str(f.relative_to(dest)) for f in folders],'reason':'CSV CRLF to LF; source evidence and scientific values unchanged'})
 original=dict(m)
 try:
  shutil.copytree(ROOT,old_handover,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
  need(sha(old_handover/'SHA256SUMS')==pkg,'Replacement handover copy differs');verify_manifest(old_handover)
  repaired_at=stamp()
  for f in folders:
   rec=load(f/'record.json');rec.update(handover_sha256=pkg,original_handover_sha256=LEGACY_PACKAGE_SHA256,csv_lf_repair_recorded_at=repaired_at)
   save(f/'record.json',rec);manifest(f);verify_manifest(f)
  m.update(package_sha256=pkg,original_package_sha256=LEGACY_PACKAGE_SHA256,repair_backup=str(backup),repair_recorded_at=repaired_at)
  save(marker(dest),m)
 except BaseException:
  # Preserve the partial repair before restoring the exact original working files.
  for i,f in enumerate(folders):
   f.rename(backup/('interrupted-assessment-'+str(i)));shutil.copytree(backup/('assessment-'+str(i)),f)
  save(marker(dest),original)
  raise
 event('Repaired CSV line endings and enclosing record checksums',backup=str(backup),scientific_values_unchanged=True,production_started=False)
 return m
def install(args):
 verify();dest=args.publication;pkg=sha(ROOT/'SHA256SUMS')
 if dest.exists():
  need(marker(dest).is_file(),'Publication directory already exists without this handover marker; choose a new --publication directory')
  m=load(marker(dest))
  if m['package_sha256']!=pkg:m=upgrade_lf(dest,m,pkg)
 else:
  origin=cmd(['git','remote','get-url','origin'],args.repo,True)
  need(origin.rstrip('/').removesuffix('.git').lower() in ['https://github.com/rdhomeprojects/electronfieldtopology','git@github.com:rdhomeprojects/electronfieldtopology'],'Unexpected source repository origin')
  cmd(['git','clone','--no-hardlinks',args.repo,dest],args.repo)
  m={'package_sha256':pkg,'installed_at':stamp(),'phase':'cloned','origin':origin};save(marker(dest),m)
 if m['phase']=='cloned':
  need(clean(dest),'Partial clone changed; preserve it')
  cmd(['git','remote','set-url','origin',m['origin']],dest);cmd(['git','fetch','origin','main'],dest)
  cmd(['git','switch','-c',BRANCH,'origin/main'],dest)
  m.update(base=cmd(['git','rev-parse','HEAD'],dest,True),phase='base');save(marker(dest),m)
 if m['phase']=='base':
  need(clean(dest),'Unrecorded edits in publication checkout')
  cmd(['git','merge-base','--is-ancestor',SOURCE,m['base']],dest)
  m['phase']='applying';save(marker(dest),m)
 if m['phase']=='applying':m=apply(dest,m);m['phase']='applied';save(marker(dest),m)
 if m['phase']=='applied':checks(dest,m);m.update(phase='staged',staged=fingerprint(dest));save(marker(dest),m)
 if m['phase']=='staged':need(fingerprint(dest)==m['staged'] and not cmd(['git','diff','--name-only'],dest,True),'Staged publication changed')
 event('Closure and feasibility assessment prepared',checkout=str(dest),phase=m['phase'],assessment_path=m.get('assessment_path'),production_started=False)
 return m
def publish(args):
 m=install(args);dest=args.publication
 if m.get('merged'):event('Already merged',url=m['pr']['url']);return
 cmd(['gh','auth','status'],dest)
 if m['phase']=='staged':
  cmd(['git','commit','-m','Record Q2 to Q16 closure and assess higher Q campaign feasibility'],dest)
  m.update(phase='committed',commit=cmd(['git','rev-parse','HEAD'],dest,True));save(marker(dest),m)
 need(clean(dest) and cmd(['git','rev-parse','HEAD'],dest,True)==m['commit'],'Publication checkout changed')
 cmd(['git','fetch','origin','main'],dest)
 need(cmd(['git','rev-parse','origin/main'],dest,True)==m['base'],'Main advanced; preserve this checkout and reconcile before publishing. No forced reset or push is performed.')
 cmd(['git','push','-u','origin',BRANCH],dest)
 body=dest/'.git/q-range-pr-body.md';body.write_text((ROOT/'PR-BODY.md').read_text())
 prs=json.loads(cmd(['gh','pr','list','--repo',REPOSITORY,'--head',BRANCH,'--state','all','--json','number,state,headRefOid,url'],dest,True))
 if not prs:
  cmd(['gh','pr','create','--repo',REPOSITORY,'--base','main','--head',BRANCH,'--title','Record Q2–Q16 closure and assess Q17–Q32 feasibility','--body-file',body],dest)
  pr=json.loads(cmd(['gh','pr','view',BRANCH,'--repo',REPOSITORY,'--json','number,state,headRefOid,url'],dest,True))
 else:need(len(prs)==1,'Ambiguous existing PR');pr=prs[0]
 need(pr['headRefOid']==m['commit'] and pr['state']=='OPEN','Existing PR differs or is closed')
 m['pr']=pr;save(marker(dest),m);event('Closure assessment PR ready',url=pr['url'])
def merge(args):
 verify();dest=args.publication;m=load(marker(dest));need(m.get('pr'),'Publish first')
 need(clean(dest) and cmd(['git','rev-parse','HEAD'],dest,True)==m['commit'],'Publication checkout changed')
 n=str(m['pr']['number']);pr=json.loads(cmd(['gh','pr','view',n,'--repo',REPOSITORY,'--json','state,headRefOid,url'],dest,True));need(pr['headRefOid']==m['commit'],'PR head changed')
 if pr['state']!='MERGED':
  need(pr['state']=='OPEN','PR is not open');cmd(['gh','pr','checks',n,'--repo',REPOSITORY,'--watch','--interval','15'],dest)
  cmd(['gh','pr','merge',n,'--repo',REPOSITORY,'--squash','--match-head-commit',m['commit']],dest)
  pr=json.loads(cmd(['gh','pr','view',n,'--repo',REPOSITORY,'--json','state,headRefOid,url'],dest,True))
 need(pr['state']=='MERGED','Merge not confirmed');m.update(phase='merged',pr=pr,merged={'recorded_at':stamp(),**pr});save(marker(dest),m);event('Closure and assessment merged',url=pr['url'])
def main():
 p=argparse.ArgumentParser(description='Record-only closure; no numerical run/benchmark modes')
 p.add_argument('mode',choices=['verify','install','publish','merge','status']);p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-repository-admin');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-q-range-closure-20261117');a=p.parse_args()
 a.repo=a.repo.expanduser().resolve();a.publication=a.publication.expanduser().resolve()
 if a.mode=='verify':verify()
 elif a.mode=='install':install(a)
 elif a.mode=='publish':publish(a)
 elif a.mode=='merge':merge(a)
 else:
  m=load(marker(a.publication)) if marker(a.publication).exists() else {'phase':'not_installed'}
  event('Record-only handover status',checkout=str(a.publication),publication=m,production_started=False)
if __name__=='__main__':
 try:main()
 except Exception as e:event('Closure handover stopped',error=str(e));sys.exit(1)
