"""Additive publication executed only by commands on the user's workstation."""
import gzip,hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
from common import ROOT,load,save,sha,stamp,need,verify_zip,log
REMOTE='https://github.com/RDHomeProjects/ElectronFieldTopology.git';REPOSITORY='RDHomeProjects/ElectronFieldTopology';DOC=Path('docs/research/project-pause-20261124');MARKER='final-folder-cleanup-publication.json'

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

def prepare(repo,pub,out):
 from engine import read_plan,verify_remote
 from transport import Remote
 verify_manifest_count=__import__('common').verify_manifest(ROOT);plan=read_plan(out);remote=Remote(REPOSITORY);release=verify_remote(out,remote);need((out/'CLEANUP-RECEIPT.json').exists(),'Finish verified folder cleanup first');snapshot=sha(out/'CLEANUP-RECEIPT.json');receipt=load(out/'CLEANUP-RECEIPT.json');need(receipt['journal_sha256']==sha(out/'DELETIONS.jsonl'),'Cleanup receipt/journal binding differs')
 state=load(marker(pub)) if marker(pub).exists() else None
 resuming=bool(state and state['snapshot_sha256']==snapshot and state['phase']=='staging')
 if state and state['snapshot_sha256']==snapshot and not resuming:
  need(state['package_sha256']==sha(ROOT/'SHA256SUMS'),'Toolset identity changed')
  if state['phase']=='applied':checks(pub,state)
  return state
 need(not state or state['phase']=='merged' or resuming,'Finish the prior final-cleanup publication first')
 if not pub.exists():subprocess.run(['git','clone','--no-hardlinks',str(repo),str(pub)],check=True);cmd(pub,['git','remote','set-url','origin',REMOTE])
 need(cmd(pub,['git','remote','get-url','origin'],True)==REMOTE,'Publication origin differs')
 if resuming:base,branch=state['base'],state['branch'];need(cmd(pub,['git','branch','--show-current'],True)==branch,'Publication branch changed')
 else:
  need(not cmd(pub,['git','status','--porcelain'],True),'Publication clone contains changes; nothing is reset');cmd(pub,['git','fetch','origin','refs/heads/main:refs/remotes/origin/main']);base=cmd(pub,['git','rev-parse','origin/main'],True);branch='archive/final-folder-cleanup-20261126-'+snapshot[:8];cmd(pub,['git','switch','-c',branch,base]);save(marker(pub),{'recorded_at':stamp(),'phase':'staging','base':base,'branch':branch,'snapshot_sha256':snapshot,'package_sha256':sha(ROOT/'SHA256SUMS'),'pr':None})
 files={};prefix=DOC/'residual-cleanup'/plan['tag']/snapshot[:8]
 def put(relative,data):
  need(len(data)<50*1024**2,'Report payload is too large for Git documentation');p=pub/relative;p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists():need(p.read_bytes()==data,'Existing immutable cleanup record differs')
  else:p.write_bytes(data)
  files[relative.as_posix()]=hashlib.sha256(data).hexdigest()
 for name in ['CLEANUP-RECEIPT.json','REPORT.md','STATUS.json','IDENTITY.json','RESIDUAL-MANIFEST.json.gz','VERIFIED-SUPPLEMENT.json','PROOF-ASSET.json']:
  put(prefix/name,(out/name).read_bytes())
 (out/'DELETIONS.jsonl.gz').write_bytes(gzip.compress((out/'DELETIONS.jsonl').read_bytes(),mtime=0))
 put(prefix/'DELETIONS.jsonl.gz',(out/'DELETIONS.jsonl.gz').read_bytes())
 for p in sorted(ROOT.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts:put(prefix/'handover'/p.relative_to(ROOT),p.read_bytes())
 text='# Final folder cleanup and additional archive\n\nSupplement: '+release['html_url']+'\n\nVerification receipt SHA256: `'+sha(out/'VERIFIED-SUPPLEMENT.json')+'`.\n\n[Folder outcomes](REPORT.md), [cleanup receipt](CLEANUP-RECEIPT.json), [restore instructions](handover/RESTORE.md). One working checkout is retained at `'+plan['workspace']+'`; original pause controls and the final cleanup controls remain. Unrelated home and Downloads files remain untouched. Additional regular records and Git metadata were preserved and download-verified before exact quarantined deletion. Recognised rebuildable environments and bytecode were omitted from the data archive and are listed explicitly in the manifest. Retained items, if any, remain visible in the receipt. No scientific steps or gate changes were performed.\n'
 put(prefix/'README.md',text.encode());index=pub/DOC/'README.md';old=index.read_text() if index.exists() else '# Project pause records\n';link='[Final folder cleanup and supplemental archive]('+(prefix/'README.md').relative_to(DOC).as_posix()+')'
 if link not in old:index.write_text(old.rstrip()+'\n\n'+link+'\n')
 attrs=pub/DOC/'.gitattributes';oldattrs=attrs.read_text() if attrs.exists() else ''
 if 'residual-cleanup/** -text -diff' not in oldattrs:attrs.write_text(oldattrs.rstrip()+'\nresidual-cleanup/** -text -diff\n')
 paths=sorted(set(files)|{(DOC/'README.md').as_posix(),(DOC/'.gitattributes').as_posix()});cmd(pub,['git','add','-f','--',*paths]);state={'recorded_at':stamp(),'phase':'applied','base':base,'branch':branch,'snapshot_sha256':snapshot,'package_sha256':sha(ROOT/'SHA256SUMS'),'stage_paths':paths,'immutable_files':files,'pr':None};save(marker(pub),state);checks(pub,state);return state

def view(pub,ref):return json.loads(cmd(pub,['gh','pr','view',str(ref),'--repo',REPOSITORY,'--json','number,url,state,headRefOid,mergeCommit,headRefName,baseRefName'],True))

def execute(mode,repo,pub,out):
 if mode=='install':return prepare(repo,pub,out)
 need(marker(pub).exists(),'Install completed results/plan or record supplement results first');state=load(marker(pub));need(state['package_sha256']==sha(ROOT/'SHA256SUMS'),'Publication package differs')
 if state['phase']=='merged':return state
 if mode=='publish':
  need(cmd(pub,['git','branch','--show-current'],True)==state['branch'],'Publication branch changed')
  if state['phase'] in ['applied','committing']:
   head=cmd(pub,['git','rev-parse','HEAD'],True)
   if state['phase']=='committing' and head!=state['precommit_head']:verify_bytes(pub,'HEAD',state['immutable_files'])
   else:
    checks(pub,state);state.update(phase='committing',precommit_head=head);save(marker(pub),state);cmd(pub,['git','commit','-m','Record final workstation folder cleanup and supplemental archive'])
   state.update(phase='committed',commit=cmd(pub,['git','rev-parse','HEAD'],True));save(marker(pub),state)
  need(state['phase'] in ['committed','published'],'Publication phase is not publishable');need(not cmd(pub,['git','status','--porcelain'],True),'Publication has unexpected changes');need(cmd(pub,['git','rev-parse','HEAD'],True)==state['commit'],'Publication head changed');verify_bytes(pub,'HEAD',state['immutable_files']);cmd(pub,['git','push','-u','origin',state['branch']])
  probe=subprocess.run(['gh','pr','view',state['branch'],'--repo',REPOSITORY,'--json','url'],cwd=pub,capture_output=True,text=True)
  url=json.loads(probe.stdout)['url'] if probe.returncode==0 else cmd(pub,['gh','pr','create','--repo',REPOSITORY,'--base','main','--head',state['branch'],'--title','Record final workstation folder cleanup and supplemental archive','--body-file',str(ROOT/'PR-BODY.md')],True).splitlines()[-1]
  pr=view(pub,url);need(pr['headRefOid']==state['commit'] and pr['baseRefName']=='main','PR head/base differs');state.update(phase='published',pr=pr);save(marker(pub),state);return state
 need(state['phase']=='published','Publish before merge');pr=view(pub,state['pr']['url']);need(pr['headRefOid']==state['commit'],'PR head changed')
 if pr['state']!='MERGED':
  need(pr['state']=='OPEN','PR is not open');checks_data=json.loads(cmd(pub,['gh','pr','view',pr['url'],'--repo',REPOSITORY,'--json','statusCheckRollup'],True))
  if checks_data['statusCheckRollup']:cmd(pub,['gh','pr','checks',pr['url'],'--repo',REPOSITORY,'--watch','--interval','10'])
  cmd(pub,['gh','pr','merge',pr['url'],'--repo',REPOSITORY,'--squash','--delete-branch','--match-head-commit',state['commit']]);pr=view(pub,pr['url'])
 need(pr['state']=='MERGED' and pr.get('mergeCommit'),'Merge not confirmed');cmd(pub,['git','fetch','origin','refs/heads/main:refs/remotes/origin/main']);cmd(pub,['git','merge-base','--is-ancestor',pr['mergeCommit']['oid'],'origin/main']);count=verify_bytes(pub,'origin/main',state['immutable_files']);state.update(phase='merged',pr=pr,verified_published_payloads=count);save(marker(pub),state);log('Merged publication payloads verified',payloads=count,pr=pr);return state
