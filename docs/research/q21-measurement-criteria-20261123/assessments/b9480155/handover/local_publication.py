"""Additive publication executed only by commands on the user's workstation."""
import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
from criteria_common import ROOT,load,save,sha,stamp,need,verify_package,verify_zip,log
REMOTE='https://github.com/RDHomeProjects/ElectronFieldTopology.git';REPOSITORY='RDHomeProjects/ElectronFieldTopology';DOC=Path('docs/research/q21-measurement-criteria-20261123');MARKER='q21-criteria-publication.json'

def cmd(repo,args,capture=False):
 log('Local publication command',argv=args if len(args)<18 else args[:3]+['explicit scoped paths'],checkout=str(repo));r=subprocess.run(args,cwd=repo,text=True,capture_output=capture);need(r.returncode==0,'Local command failed: '+repr(args[:6])+('\n'+r.stderr if capture else ''));return r.stdout.strip() if capture else None

def marker(pub):return pub/'.git'/MARKER

def verify_bytes(pub,ref,files):
 queries=[ref+':'+n for n in sorted(files)];need(not any('\n' in q or '\r' in q for q in queries),'Unsafe Git path');r=subprocess.run(['git','cat-file','--batch'],cwd=pub,input=('\n'.join(queries)+'\n').encode(),capture_output=True);need(r.returncode==0,'Git batch read failed');position=0
 for name in sorted(files):
  end=r.stdout.find(b'\n',position);header=r.stdout[position:end].split();need(end>=position and len(header)==3 and header[1]==b'blob','Published blob missing: '+name);length=int(header[2]);position=end+1;data=r.stdout[position:position+length];need(hashlib.sha256(data).hexdigest()==files[name],'Published bytes differ: '+name);position+=length+1
 need(position==len(r.stdout),'Unexpected batch remainder');return len(files)

def checks(pub,state):
 changed=set(cmd(pub,['git','diff','--cached','--name-only'],True).splitlines());need(changed<=set(state['stage_paths']),'Unexpected staged paths');cmd(pub,['git','diff','--cached','--check'])
 need((pub/'scripts/project_records.py').is_file() and (pub/'scripts/check_docs.py').is_file(),'Repository validation scripts missing; restore the correct publication checkout')
 cmd(pub,['/usr/bin/python3','scripts/project_records.py','check','--compare-ref',state['base']]);cmd(pub,['/usr/bin/python3','scripts/check_docs.py'])

def prepare(repo,pub,out=None):
 verify_package();kind='supplement-results' if out else 'completed-results-assessment-and-CPU-plan';snapshot=sha(out/'evidence.zip') if out else sha(ROOT/'SHA256SUMS');state=load(marker(pub)) if marker(pub).exists() else None
 resuming=bool(state and state['kind']==kind and state['snapshot_sha256']==snapshot and state['phase']=='staging')
 if state and state['kind']==kind and state['snapshot_sha256']==snapshot and not resuming:
  need(state['package_sha256']==sha(ROOT/'SHA256SUMS'),'Publication package changed')
  if state['phase']=='applied':checks(pub,state)
  return state
 need(not state or state['phase']=='merged' or resuming,'Finish existing publication before staging another snapshot')
 if not pub.exists():
  subprocess.run(['git','clone','--no-hardlinks',str(repo),str(pub)],check=True);cmd(pub,['git','remote','set-url','origin',REMOTE])
 need(cmd(pub,['git','remote','get-url','origin'],True) in [REMOTE,REMOTE.removesuffix('.git'),'git@github.com:'+REPOSITORY+'.git'],'Publication origin differs')
 if resuming:
  base,branch=state['base'],state['branch'];need(cmd(pub,['git','branch','--show-current'],True)==branch,'Staging branch changed')
 else:
  need(not cmd(pub,['git','status','--porcelain'],True),'Publication checkout has changes; no reset is performed');cmd(pub,['git','fetch','origin','refs/heads/main:refs/remotes/origin/main']);base=cmd(pub,['git','rev-parse','origin/main'],True);branch='analysis/q21-criteria-'+('results-' if out else 'record-plan-')+'20261123-'+snapshot[:8];cmd(pub,['git','switch','-c',branch,base]);save(marker(pub),{'recorded_at':stamp(),'kind':kind,'phase':'staging','base':base,'branch':branch,'snapshot_sha256':snapshot,'package_sha256':sha(ROOT/'SHA256SUMS'),'pr':None})
 files={}
 def put(relative,data):
  path=pub/relative;path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists():need(path.read_bytes()==data,'Immutable publication payload differs: '+str(relative))
  else:path.write_bytes(data)
  files[relative.as_posix()]=hashlib.sha256(data).hexdigest()
 if out:
  hashes=verify_zip(out/'evidence.zip')
  for name in ['identity.json','record.json','status.json','FIELD-MANIFEST.json']:need(sha(out/name)==hashes[name],'Supplement metadata differs from sealed evidence: '+name)
  need(load(out/'status.json')['status']=='complete_pending_review','Only completed supplement results can be staged automatically')
  for field in load(out/'FIELD-MANIFEST.json')['fields']:need(sha(out/field['path'])==field['sha256'],'New full-field retention differs: '+field['path'])
  prefix=DOC/'supplement-results'/load(out/'identity.json')['run_id']/snapshot[:8]
  with zipfile.ZipFile(out/'evidence.zip') as z:
   for name in z.namelist():put(prefix/name,z.read(name))
  put(prefix/'evidence.zip',(out/'evidence.zip').read_bytes());addition='\n\nCompleted CPU supplement: [browser assessment]('+(prefix/'REPORT.html').relative_to(DOC).as_posix()+') · [full compact record]('+(prefix/'record.json').relative_to(DOC).as_posix()+').\n'
 else:
  prefix=DOC/'completed-source'/load(ROOT/'PLAN.json')['source_run']/load(ROOT/'PLAN.json')['source_evidence_sha256'][:8]
  with zipfile.ZipFile(ROOT/'data/completed-evidence.zip') as z:
   for name in z.namelist():put(prefix/name,z.read(name))
  put(prefix/'evidence.zip',(ROOT/'data/completed-evidence.zip').read_bytes());pack=DOC/'assessments'/snapshot[:8]/'handover'
  for path in sorted(ROOT.rglob('*')):
   if path.is_file() and '__pycache__' not in path.parts:put(pack/path.relative_to(ROOT),path.read_bytes())
  addition='\n\nOriginal completed run: [browser report]('+(prefix/'REPORT.html').relative_to(DOC).as_posix()+') · [record]('+(prefix/'record.json').relative_to(DOC).as_posix()+').\n\nScientific review: [detailed illustrated assessment]('+(pack/'documentation/scientific-review/ASSESSMENT.html').relative_to(DOC).as_posix()+'). Author-specific limits: [assessment]('+(pack/'documentation/author-comparison/ASSESSMENT.md').relative_to(DOC).as_posix()+') · [browser comparison]('+(pack/'documentation/author-comparison/REPORT.html').relative_to(DOC).as_posix()+'). Registered supplementary measurements and explicit 177³/193³ CPU branches: [protocol]('+(pack/'PROTOCOL.md').relative_to(DOC).as_posix()+') · [plan]('+(pack/'PLAN.json').relative_to(DOC).as_posix()+'). Up to160 new optimizer attempts; no physical-time evolution and no changed admission gates.\n'
 index=pub/DOC/'README.md';index.parent.mkdir(parents=True,exist_ok=True);old=index.read_text() if index.exists() else '# Q21 measurement criteria and CPU resolution supplement\n\nCompleted results, author-specific measurement comparisons and a separately registered CPU follow-up. Existing evidence, graphics and negative findings remain unchanged.\n'
 if addition.strip() not in old:index.write_text(old.rstrip()+addition)
 attrs=pub/DOC/'.gitattributes';oldattrs=attrs.read_text() if attrs.exists() else ''
 for line in ['completed-source/** -text -diff','assessments/** -text -diff','supplement-results/** -text -diff']:
  if line not in oldattrs.splitlines():oldattrs=oldattrs.rstrip()+'\n'+line+'\n'
 attrs.write_text(oldattrs.lstrip('\n'));mutable={(DOC/'README.md').as_posix(),(DOC/'.gitattributes').as_posix()}
 root=pub/'README.md';link='[Q21 measurement criteria and CPU resolution supplement]('+DOC.as_posix()+'/README.md)'
 if link not in root.read_text():root.write_text(root.read_text().rstrip()+'\n\n'+link+'\n')
 mutable.add('README.md');prior=pub/'docs/research/q21-fixedbox-resolution-20261123/README.md'
 if prior.exists():
  link='[Completed-result criteria assessment and CPU supplement](../q21-measurement-criteria-20261123/README.md)'
  if link not in prior.read_text():prior.write_text(prior.read_text().rstrip()+'\n\n'+link+'\n')
  mutable.add(prior.relative_to(pub).as_posix())
 paths=sorted(set(files)|mutable);cmd(pub,['git','add','-f','--',*paths]);state={'recorded_at':stamp(),'kind':kind,'phase':'applied','base':base,'branch':branch,'snapshot_sha256':snapshot,'package_sha256':sha(ROOT/'SHA256SUMS'),'stage_paths':paths,'immutable_files':files,'pr':None};save(marker(pub),state);checks(pub,state);return state

def view(pub,ref):return json.loads(cmd(pub,['gh','pr','view',str(ref),'--repo',REPOSITORY,'--json','number,url,state,headRefOid,mergeCommit,headRefName,baseRefName'],True))

def execute(mode,repo,pub,out=None):
 if mode in ['install','record-results']:return prepare(repo,pub,out)
 need(marker(pub).exists(),'Install completed results/plan or record supplement results first');state=load(marker(pub));need(state['package_sha256']==sha(ROOT/'SHA256SUMS'),'Publication package differs')
 if state['phase']=='merged':return state
 if mode=='publish':
  need(cmd(pub,['git','branch','--show-current'],True)==state['branch'],'Publication branch changed')
  if state['phase'] in ['applied','committing']:
   head=cmd(pub,['git','rev-parse','HEAD'],True)
   if state['phase']=='committing' and head!=state['precommit_head']:verify_bytes(pub,'HEAD',state['immutable_files'])
   else:
    checks(pub,state);state.update(phase='committing',precommit_head=head);save(marker(pub),state);cmd(pub,['git','commit','-m','Record Q21 measurement criteria '+state['kind']])
   state.update(phase='committed',commit=cmd(pub,['git','rev-parse','HEAD'],True));save(marker(pub),state)
  need(state['phase'] in ['committed','published'],'Publication phase is not publishable');need(not cmd(pub,['git','status','--porcelain'],True),'Publication has unexpected changes');need(cmd(pub,['git','rev-parse','HEAD'],True)==state['commit'],'Publication head changed');verify_bytes(pub,'HEAD',state['immutable_files']);cmd(pub,['git','push','-u','origin',state['branch']])
  probe=subprocess.run(['gh','pr','view',state['branch'],'--repo',REPOSITORY,'--json','url'],cwd=pub,capture_output=True,text=True)
  url=json.loads(probe.stdout)['url'] if probe.returncode==0 else cmd(pub,['gh','pr','create','--repo',REPOSITORY,'--base','main','--head',state['branch'],'--title','Record Q21 '+state['kind'],'--body-file',str(ROOT/('PR-RESULTS.md' if state['kind']=='supplement-results' else 'PR-BODY.md'))],True).splitlines()[-1]
  pr=view(pub,url);need(pr['headRefOid']==state['commit'] and pr['baseRefName']=='main','PR head/base differs');state.update(phase='published',pr=pr);save(marker(pub),state);return state
 need(state['phase']=='published','Publish before merge');pr=view(pub,state['pr']['url']);need(pr['headRefOid']==state['commit'],'PR head changed')
 if pr['state']!='MERGED':
  need(pr['state']=='OPEN','PR is not open');checks_data=json.loads(cmd(pub,['gh','pr','view',pr['url'],'--repo',REPOSITORY,'--json','statusCheckRollup'],True))
  if checks_data['statusCheckRollup']:cmd(pub,['gh','pr','checks',pr['url'],'--repo',REPOSITORY,'--watch','--interval','10'])
  cmd(pub,['gh','pr','merge',pr['url'],'--repo',REPOSITORY,'--squash','--delete-branch','--match-head-commit',state['commit']]);pr=view(pub,pr['url'])
 need(pr['state']=='MERGED' and pr.get('mergeCommit'),'Merge not confirmed');cmd(pub,['git','fetch','origin','refs/heads/main:refs/remotes/origin/main']);cmd(pub,['git','merge-base','--is-ancestor',pr['mergeCommit']['oid'],'origin/main']);count=verify_bytes(pub,'origin/main',state['immutable_files']);state.update(phase='merged',pr=pr,verified_published_payloads=count);save(marker(pub),state);log('Merged publication payloads verified',payloads=count,pr=pr);return state
