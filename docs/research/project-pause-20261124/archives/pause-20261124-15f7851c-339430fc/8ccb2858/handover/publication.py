"""Additive publication executed only by commands on the user's workstation."""
import gzip,hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
from common import ROOT,load,save,sha,stamp,need,verify_zip,log
REMOTE='https://github.com/RDHomeProjects/ElectronFieldTopology.git';REPOSITORY='RDHomeProjects/ElectronFieldTopology';DOC=Path('docs/research/project-pause-20261124');MARKER='pause-archive-publication.json'

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
 from archive import verify_package,verify_remote,read_plan
 verify_package();current=verify_remote(out);plan=read_plan(out);need((out/'CLEANUP-RECEIPT.json').exists(),'Run verified cleanup before publishing the completion record');snapshot=sha(out/'CLEANUP-RECEIPT.json')
 receipt=load(out/'CLEANUP-RECEIPT.json');asset=load(out/'CLEANUP-ASSET.json');need(snapshot==asset['sha256'],'Local cleanup receipt differs from its uploaded bytes');remote_asset=next((x for x in current['assets'] if x['name']==asset['name']),None);need(remote_asset and remote_asset['id']==asset['asset_id'] and remote_asset['size']==asset['bytes'],'Published cleanup receipt is missing/replaced');need(not remote_asset.get('digest') or remote_asset['digest']=='sha256:'+snapshot,'Published cleanup receipt digest differs')
 with gzip.open(out/'DELETIONS.jsonl.gz','rb') as f:need(hashlib.sha256(f.read()).hexdigest()==receipt['deletion_journal_sha256'],'Cleanup journal differs from the uploaded receipt')
 state=load(marker(pub)) if marker(pub).exists() else None
 resuming=bool(state and state['snapshot_sha256']==snapshot and state['phase']=='staging')
 if state and state['snapshot_sha256']==snapshot and not resuming:
  need(state['package_sha256']==sha(ROOT/'SHA256SUMS'),'Publication package changed')
  if state['phase']=='applied':checks(pub,state)
  return state
 need(not state or state['phase']=='merged' or resuming,'Finish the existing publication first')
 if not pub.exists():subprocess.run(['git','clone','--no-hardlinks',str(repo),str(pub)],check=True);cmd(pub,['git','remote','set-url','origin',REMOTE])
 need(cmd(pub,['git','remote','get-url','origin'],True) in [REMOTE,REMOTE.removesuffix('.git'),'git@github.com:'+REPOSITORY+'.git'],'Publication origin differs')
 if resuming:
  base,branch=state['base'],state['branch'];need(cmd(pub,['git','branch','--show-current'],True)==branch,'Staging branch changed')
 else:
  need(not cmd(pub,['git','status','--porcelain'],True),'Publication checkout contains changes; nothing is reset');cmd(pub,['git','fetch','origin','refs/heads/main:refs/remotes/origin/main']);base=cmd(pub,['git','rev-parse','origin/main'],True);branch='archive/pause-verified-cleanup-20261124-'+snapshot[:8];cmd(pub,['git','switch','-c',branch,base]);save(marker(pub),{'recorded_at':stamp(),'phase':'staging','base':base,'branch':branch,'snapshot_sha256':snapshot,'package_sha256':sha(ROOT/'SHA256SUMS'),'pr':None})
 files={}
 def put(relative,data):
  need(len(data)<50*1024**2,'Documentation file exceeds metadata limit');path=pub/relative;path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists():need(path.read_bytes()==data,'Existing immutable archive record differs: '+str(relative))
  else:path.write_bytes(data)
  files[relative.as_posix()]=hashlib.sha256(data).hexdigest()
 prefix=DOC/'archives'/plan['tag']/snapshot[:8]
 for name in ['STATUS.json','IDENTITY.json','MATTER-WAVES-ARCHIVE.json.gz','VERIFIED-UPLOAD.json','PROOF-ASSET.json','CLEANUP-RECEIPT.json','CLEANUP-ASSET.json','DELETIONS.jsonl.gz']:
  put(prefix/name,(out/name).read_bytes())
 put(prefix/'RESTORE.md',(ROOT/'RESTORE.md').read_bytes());put(prefix/'KNOWN-STATE.json',(ROOT/'KNOWN-STATE.json').read_bytes());put(prefix/'restore-kit.zip',(ROOT/'restore-kit.zip').read_bytes())
 proof_sha=sha(out/'VERIFIED-UPLOAD.json');text='# Verified full-data archive and local cleanup\n\nRelease: '+current['html_url']+'\n\nVerified upload receipt SHA256: `'+proof_sha+'`. Inventory: `'+plan['inventory_id']+'`. Pinned main: `'+plan['main_commit']+'`.\n\nAll parts were downloaded and every content object rehashed before cleanup. Recent checkpoint NPZ CRCs, float64 field geometry, primary CG native iterations and conjugacy arrays, plus a fresh source clone were checked. This is byte-level restoration validation, not a new scientific run.\n\n[Restore instructions](RESTORE.md), [receipt](CLEANUP-RECEIPT.json), [upload proof](VERIFIED-UPLOAD.json), [restart state](KNOWN-STATE.json). The manifest preserves every original absolute-to-root path mapping. Unchanged inventoried untracked records and project Downloads were eligible for deletion. Tracked files, runtimes, new/unlisted files and changed data were retained.\n\nPrimary scientific restart is exact-CG iteration 665; best iteration 663 is separate. Strict stationarity remains unachieved. Preserve the original gates and do not infer stability from archival success. Repository remains writable until the maintainer elects to archive it.\n'
 put(prefix/'README.md',text.encode())
 # Store this exact handover as reproducible publication input.
 for path in sorted(ROOT.rglob('*')):
  if path.is_file() and '__pycache__' not in path.parts:put(prefix/'handover'/path.relative_to(ROOT),path.read_bytes())
 index=pub/DOC/'README.md';index.parent.mkdir(parents=True,exist_ok=True);old=index.read_text() if index.exists() else '# Matter Waves project pause and restart records\n'
 link='[Verified full-data archive and local cleanup]('+(prefix/'README.md').relative_to(DOC).as_posix()+')'
 if link not in old:index.write_text(old.rstrip()+'\n\n'+link+'\n')
 attrs=pub/DOC/'.gitattributes';old_attrs=attrs.read_text() if attrs.exists() else ''
 if 'archives/** -text -diff' not in old_attrs:attrs.write_text(old_attrs.rstrip()+'\narchives/** -text -diff\n')
 root=pub/'README.md';rootlink='[Project pause and restart records]('+DOC.as_posix()+'/README.md)'
 if rootlink not in root.read_text():root.write_text(root.read_text().rstrip()+'\n\n'+rootlink+'\n')
 paths=sorted(set(files)|{'README.md',(DOC/'README.md').as_posix(),(DOC/'.gitattributes').as_posix()});cmd(pub,['git','add','-f','--',*paths]);state={'recorded_at':stamp(),'kind':'full-data-archive-and-verified-cleanup','phase':'applied','base':base,'branch':branch,'snapshot_sha256':snapshot,'package_sha256':sha(ROOT/'SHA256SUMS'),'stage_paths':paths,'immutable_files':files,'pr':None};save(marker(pub),state);checks(pub,state);return state

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
    checks(pub,state);state.update(phase='committing',precommit_head=head);save(marker(pub),state);cmd(pub,['git','commit','-m','Record verified full-data archive, restart guide and local cleanup'])
   state.update(phase='committed',commit=cmd(pub,['git','rev-parse','HEAD'],True));save(marker(pub),state)
  need(state['phase'] in ['committed','published'],'Publication phase is not publishable');need(not cmd(pub,['git','status','--porcelain'],True),'Publication has unexpected changes');need(cmd(pub,['git','rev-parse','HEAD'],True)==state['commit'],'Publication head changed');verify_bytes(pub,'HEAD',state['immutable_files']);cmd(pub,['git','push','-u','origin',state['branch']])
  probe=subprocess.run(['gh','pr','view',state['branch'],'--repo',REPOSITORY,'--json','url'],cwd=pub,capture_output=True,text=True)
  url=json.loads(probe.stdout)['url'] if probe.returncode==0 else cmd(pub,['gh','pr','create','--repo',REPOSITORY,'--base','main','--head',state['branch'],'--title','Record verified full-data archive, restart guide and local cleanup','--body-file',str(ROOT/'PR-BODY.md')],True).splitlines()[-1]
  pr=view(pub,url);need(pr['headRefOid']==state['commit'] and pr['baseRefName']=='main','PR head/base differs');state.update(phase='published',pr=pr);save(marker(pub),state);return state
 need(state['phase']=='published','Publish before merge');pr=view(pub,state['pr']['url']);need(pr['headRefOid']==state['commit'],'PR head changed')
 if pr['state']!='MERGED':
  need(pr['state']=='OPEN','PR is not open');checks_data=json.loads(cmd(pub,['gh','pr','view',pr['url'],'--repo',REPOSITORY,'--json','statusCheckRollup'],True))
  if checks_data['statusCheckRollup']:cmd(pub,['gh','pr','checks',pr['url'],'--repo',REPOSITORY,'--watch','--interval','10'])
  cmd(pub,['gh','pr','merge',pr['url'],'--repo',REPOSITORY,'--squash','--delete-branch','--match-head-commit',state['commit']]);pr=view(pub,pr['url'])
 need(pr['state']=='MERGED' and pr.get('mergeCommit'),'Merge not confirmed');cmd(pub,['git','fetch','origin','refs/heads/main:refs/remotes/origin/main']);cmd(pub,['git','merge-base','--is-ancestor',pr['mergeCommit']['oid'],'origin/main']);count=verify_bytes(pub,'origin/main',state['immutable_files']);state.update(phase='merged',pr=pr,verified_published_payloads=count);save(marker(pub),state);log('Merged publication payloads verified',payloads=count,pr=pr);return state
