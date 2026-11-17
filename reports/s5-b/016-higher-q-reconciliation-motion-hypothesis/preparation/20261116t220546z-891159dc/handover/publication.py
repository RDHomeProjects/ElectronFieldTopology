"""Record-only local publication of completed evidence and a focused desk review."""
import argparse,hashlib,json,re,shutil,subprocess,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
REPOSITORY='RDHomeProjects/ElectronFieldTopology'
BRANCH='analysis/higher-q-reconciliation-motion-20261117'
SLUG='higher-q-reconciliation-motion-hypothesis'
SOURCE='cffd6fc10c84a50b0a0dcce768b965a9aa5e7b09'
MARKER='higher-q-reconciliation-publication.json'
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
 count=verify_manifest(ROOT)
 for p in ROOT.rglob('*.csv'):need(b'\r' not in p.read_bytes(),'CSV must use LF: '+str(p))
 legacy=load(ROOT/'LEGACY-ENDPOINTS.json');p=ROOT/'data/legacy-SF-dynamics-evidence.zip';need(sha(p)==legacy['source_sha256'],'Legacy evidence differs')
 with zipfile.ZipFile(p) as z:
  need(z.testzip() is None,'Legacy evidence CRC failure');hashes=json.loads(z.read('evidence-hashes.json'))['sha256']
  need(set(hashes)|{'evidence-hashes.json'}==set(z.namelist()),'Legacy evidence coverage differs')
  for n,h in hashes.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Legacy evidence member differs: '+n)
 event('Reconciliation package verified',payload_files=count,legacy_payloads=len(hashes),relaxation_steps=0,physical_time_steps=0)
 return legacy
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

from apply_records import apply
def checks(dest,m):
 cmd([sys.executable,'scripts/project_records.py','render'],dest)
 cmd(['git','add','--','README.md','docs','reports'],dest)
 cmd([sys.executable,'scripts/project_records.py','check','--compare-ref',m['base']],dest)
 cmd([sys.executable,'scripts/check_docs.py'],dest)
 cmd(['git','diff','--cached','--check'],dest)
def install(args):
 verify();dest=args.publication;pkg=sha(ROOT/'SHA256SUMS')
 if dest.exists():
  need(marker(dest).is_file(),'Publication directory already exists without this handover marker; choose a new --publication directory')
  m=load(marker(dest))
  need(m['package_sha256']==pkg,'Publication belongs to a different package; preserve it')
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
 event('Higher Q reconciliation prepared',checkout=str(dest),phase=m['phase'],assessment_path=m.get('assessment_path'),production_started=False)
 return m
def publish(args):
 m=install(args);dest=args.publication
 if m.get('merged'):event('Already merged',url=m['pr']['url']);return
 cmd(['gh','auth','status'],dest)
 if m['phase']=='staged':
  cmd(['git','commit','-m','Prepare higher Q reconciliation and assess motion dependent stability'],dest)
  m.update(phase='committed',commit=cmd(['git','rev-parse','HEAD'],dest,True));save(marker(dest),m)
 need(clean(dest) and cmd(['git','rev-parse','HEAD'],dest,True)==m['commit'],'Publication checkout changed')
 cmd(['git','fetch','origin','main'],dest)
 need(cmd(['git','rev-parse','origin/main'],dest,True)==m['base'],'Main advanced; preserve this checkout and reconcile before publishing. No forced reset or push is performed.')
 cmd(['git','push','-u','origin',BRANCH],dest)
 body=dest/'.git/q-range-pr-body.md';body.write_text((ROOT/'PR-BODY.md').read_text())
 prs=json.loads(cmd(['gh','pr','list','--repo',REPOSITORY,'--head',BRANCH,'--state','all','--json','number,state,headRefOid,url'],dest,True))
 if not prs:
  cmd(['gh','pr','create','--repo',REPOSITORY,'--base','main','--head',BRANCH,'--title','Prepare Q22 Q18 reconciliation and assess motion dependent stability','--body-file',body],dest)
  pr=json.loads(cmd(['gh','pr','view',BRANCH,'--repo',REPOSITORY,'--json','number,state,headRefOid,url'],dest,True))
 else:need(len(prs)==1,'Ambiguous existing PR');pr=prs[0]
 need(pr['headRefOid']==m['commit'] and pr['state']=='OPEN','Existing PR differs or is closed')
 m['pr']=pr;save(marker(dest),m);event('Reconciliation assessment PR ready',url=pr['url'])
def merge(args):
 verify();dest=args.publication;m=load(marker(dest));need(m.get('pr'),'Publish first')
 need(clean(dest) and cmd(['git','rev-parse','HEAD'],dest,True)==m['commit'],'Publication checkout changed')
 n=str(m['pr']['number']);pr=json.loads(cmd(['gh','pr','view',n,'--repo',REPOSITORY,'--json','state,headRefOid,url'],dest,True));need(pr['headRefOid']==m['commit'],'PR head changed')
 if pr['state']!='MERGED':
  need(pr['state']=='OPEN','PR is not open');cmd(['gh','pr','checks',n,'--repo',REPOSITORY,'--watch','--interval','15'],dest)
  cmd(['gh','pr','merge',n,'--repo',REPOSITORY,'--squash','--match-head-commit',m['commit']],dest)
  pr=json.loads(cmd(['gh','pr','view',n,'--repo',REPOSITORY,'--json','state,headRefOid,url'],dest,True))
 need(pr['state']=='MERGED','Merge not confirmed');m.update(phase='merged',pr=pr,merged={'recorded_at':stamp(),**pr});save(marker(dest),m);event('Reconciliation preparation merged',url=pr['url'])
