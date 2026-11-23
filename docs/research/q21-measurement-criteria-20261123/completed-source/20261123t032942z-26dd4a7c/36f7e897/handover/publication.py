"""Additive documentation/results publication using Git and gh on the zbook only."""
import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
from common import ROOT,load,log,need,save,sha,stamp,verify_manifest
from integrity import merged_source,checked_evidence,authenticate
REMOTE='https://github.com/RDHomeProjects/ElectronFieldTopology.git';REPOSITORY='RDHomeProjects/ElectronFieldTopology';DOC=Path('docs/research/q21-fixedbox-resolution-20261123');MARKER='q21-resolution-publication.json'

def cmd(repo,args,capture=False):
    log('Workstation publication command',argv=args if len(args)<20 else args[:3]+['explicit scoped payload paths'],checkout=str(repo));r=subprocess.run(args,cwd=repo,text=True,capture_output=capture);need(r.returncode==0,'Local command failed: '+repr(args[:6])+('\n'+r.stderr if capture else ''));return r.stdout.strip() if capture else None

def marker(pub):return pub/'.git'/MARKER

def verify_bytes(pub,ref,files):
    queries=[ref+':'+n for n in sorted(files)];need(not any('\n' in q or '\r' in q for q in queries),'Unsafe Git path')
    r=subprocess.run(['git','cat-file','--batch'],cwd=pub,input=('\n'.join(queries)+'\n').encode(),capture_output=True);need(r.returncode==0,'Published Git batch failed');data=r.stdout;pos=0
    for name in sorted(files):
        end=data.find(b'\n',pos);head=data[pos:end].split();need(end>=pos and len(head)==3 and head[1]==b'blob','Published file missing: '+name);length=int(head[2]);pos=end+1;blob=data[pos:pos+length];need(hashlib.sha256(blob).hexdigest()==files[name],'Published bytes differ: '+name);pos+=length+1
    need(pos==len(data),'Unexpected Git batch data');return len(files)

def checks(pub,state):
    staged=set(cmd(pub,['git','diff','--cached','--name-only'],True).splitlines());need(staged<=set(state['stage_paths']),'Unexpected staged paths')
    cmd(pub,['git','diff','--cached','--check'])
    if (pub/'scripts/project_records.py').exists():cmd(pub,['/usr/bin/python3','scripts/project_records.py','check','--compare-ref',state['base']])
    if (pub/'scripts/check_docs.py').exists():cmd(pub,['/usr/bin/python3','scripts/check_docs.py'])

def prepare(repo,pub,source_pub,out=None):
    verify_manifest(ROOT);authenticate(repo);kind='results' if out else 'plan';snapshot=sha(out/'evidence.zip') if out else sha(ROOT/'SHA256SUMS')
    state=load(marker(pub)) if marker(pub).exists() else None
    resuming=bool(state and state['kind']==kind and state['snapshot_sha256']==snapshot and state['phase']=='staging')
    if state and state['kind']==kind and state['snapshot_sha256']==snapshot and not resuming:
        need(state['package_sha256']==sha(ROOT/'SHA256SUMS'),'Package identity differs')
        if state['phase']=='applied':checks(pub,state)
        log('Publication already prepared',phase=state['phase'],kind=kind);return state
    need(not state or state['phase']=='merged' or resuming,'Finish existing publication before staging another snapshot')
    merged_source(source_pub)
    if not pub.exists():
        subprocess.run(['git','clone','--no-hardlinks',str(source_pub),str(pub)],check=True);cmd(pub,['git','remote','set-url','origin',REMOTE])
    need(cmd(pub,['git','remote','get-url','origin'],True) in [REMOTE,REMOTE.removesuffix('.git'),'git@github.com:'+REPOSITORY+'.git'],'Unexpected publication origin')
    if resuming:
        base,branch=state['base'],state['branch'];need(cmd(pub,['git','branch','--show-current'],True)==branch,'Staging branch changed')
    else:
        need(not cmd(pub,['git','status','--porcelain'],True),'Publication checkout has changes; no reset is performed')
        cmd(pub,['git','fetch','origin','refs/heads/main:refs/remotes/origin/main']);base=cmd(pub,['git','rev-parse','origin/main'],True);branch='analysis/q21-resolution-'+kind+'-20261123-'+snapshot[:8];cmd(pub,['git','switch','-c',branch,base])
        save(marker(pub),{'recorded_at':stamp(),'kind':kind,'phase':'staging','base':base,'branch':branch,'package_sha256':sha(ROOT/'SHA256SUMS'),'snapshot_sha256':snapshot,'pr':None})
    files={}
    def put(relative,data):
        p=pub/relative;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():need(p.read_bytes()==data,'Immutable payload differs: '+str(relative))
        else:p.write_bytes(data)
        files[relative.as_posix()]=hashlib.sha256(data).hexdigest()
    if out:
        from handover import live
        from supervision import service_active
        need(not live(out) and not service_active(),'Wait for worker and service to stop before recording results');need(load(out/'status.json')['status']=='complete_pending_review','Assess interrupted/failed runs before publication');checked_evidence(out/'evidence.zip')
        for field in load(out/'FIELD-MANIFEST.json')['fields']:need(sha(out/field['path'])==field['sha256'],'Full retained output differs: '+field['path'])
        prefix=DOC/'results'/load(out/'identity.json')['run_id']/snapshot[:8]
        with zipfile.ZipFile(out/'evidence.zip') as z:
            for n in z.namelist():put(prefix/n,z.read(n))
        put(prefix/'evidence.zip',(out/'evidence.zip').read_bytes());addition='\n\nCompleted run: [browser report]('+(prefix/'REPORT.html').relative_to(DOC).as_posix()+') · [scientific record]('+(prefix/'record.json').relative_to(DOC).as_posix()+').\n'
    else:
        prefix=DOC/'preparation'/snapshot[:8]/'handover'
        for f in sorted(ROOT.rglob('*')):
            if f.is_file() and '__pycache__' not in f.parts:put(prefix/f.relative_to(ROOT),f.read_bytes())
        addition='\n\nRegistered next steps: [protocol]('+str((prefix/'PROTOCOL.md').relative_to(DOC)).replace('\\','/')+') · [plan]('+str((prefix/'PLAN.json').relative_to(DOC)).replace('\\','/')+') · [source identity]('+str((prefix/'SOURCE.json').relative_to(DOC)).replace('\\','/')+'). Read-only Q2–Q32 endpoint ledger and a conditional fixed-box Q21 resolution pilot; ceiling720 charged optimizer attempts, zero physical-time steps.\n'
    attr=pub/DOC/'.gitattributes';attr.parent.mkdir(parents=True,exist_ok=True);attr.write_text('preparation/** -text -diff\nresults/** -text -diff\n')
    index=pub/DOC/'README.md';old=index.read_text() if index.exists() else '# Retained-field audit and Q21 fixed-box resolution\n\nEarlier results and graphics remain unchanged. This study separates preparation, numerical admission, spatial convergence and physical stability.\n'
    if addition.strip() not in old:index.write_text(old.rstrip()+addition)
    root=pub/'README.md';link='[Retained-field audit and Q21 fixed-box resolution]('+DOC.as_posix()+'/README.md)'
    if link not in root.read_text():root.write_text(root.read_text().rstrip()+'\n\n'+link+'\n')
    paths=sorted(set(files)|{'README.md',(DOC/'README.md').as_posix(),(DOC/'.gitattributes').as_posix()});cmd(pub,['git','add','-f','--',*paths])
    state={'recorded_at':stamp(),'kind':kind,'phase':'applied','base':base,'branch':branch,'package_sha256':sha(ROOT/'SHA256SUMS'),'snapshot_sha256':snapshot,'immutable_files':files,'stage_paths':paths,'pr':None};save(marker(pub),state);checks(pub,state);return state

def view(pub,ref):return json.loads(cmd(pub,['gh','pr','view',str(ref),'--repo',REPOSITORY,'--json','number,url,state,headRefOid,mergeCommit,headRefName,baseRefName'],True))

def execute(mode,repo,pub,source_pub,out=None):
    if mode in ['install','record-results']:return prepare(repo,pub,source_pub,out if mode=='record-results' else None)
    need(marker(pub).exists(),'Install the plan or record completed results first');s=load(marker(pub));need(s['package_sha256']==sha(ROOT/'SHA256SUMS'),'Publication package differs')
    if s['phase']=='merged':log('Already merged',pr=s['pr']);return s
    need(cmd(pub,['git','branch','--show-current'],True)==s['branch'],'Publication branch changed')
    if mode=='publish':
        if s['phase']=='applied':checks(pub,s);cmd(pub,['git','commit','-m','Record Q21 fixed-box resolution '+s['kind']]);s.update(phase='committed',commit=cmd(pub,['git','rev-parse','HEAD'],True));save(marker(pub),s)
        need(not cmd(pub,['git','status','--porcelain'],True),'Publication has unexpected changes');need(cmd(pub,['git','rev-parse','HEAD'],True)==s['commit'],'Publication head differs');verify_bytes(pub,'HEAD',s['immutable_files']);cmd(pub,['git','push','-u','origin',s['branch']])
        probe=subprocess.run(['gh','pr','view',s['branch'],'--repo',REPOSITORY,'--json','url'],cwd=pub,capture_output=True,text=True)
        url=json.loads(probe.stdout)['url'] if probe.returncode==0 else cmd(pub,['gh','pr','create','--repo',REPOSITORY,'--base','main','--head',s['branch'],'--title','Record retained-field audit and Q21 resolution '+s['kind'],'--body-file',str(ROOT/'PR-BODY.md')],True).splitlines()[-1]
        pr=view(pub,url);need(pr['headRefOid']==s['commit'] and pr['baseRefName']=='main','PR identity differs');s.update(phase='published',pr=pr);save(marker(pub),s);return s
    need(s['phase']=='published','Publish before merge');pr=view(pub,s['pr']['url']);need(pr['headRefOid']==s['commit'],'PR head changed')
    if pr['state']!='MERGED':
        need(pr['state']=='OPEN','PR not open');checks_data=json.loads(cmd(pub,['gh','pr','view',pr['url'],'--repo',REPOSITORY,'--json','statusCheckRollup'],True))
        if checks_data['statusCheckRollup']:cmd(pub,['gh','pr','checks',pr['url'],'--repo',REPOSITORY,'--watch','--interval','10'])
        cmd(pub,['gh','pr','merge',pr['url'],'--repo',REPOSITORY,'--squash','--delete-branch','--match-head-commit',s['commit']]);pr=view(pub,pr['url'])
    need(pr['state']=='MERGED' and pr.get('mergeCommit'),'Merge did not complete');cmd(pub,['git','fetch','origin','refs/heads/main:refs/remotes/origin/main']);cmd(pub,['git','merge-base','--is-ancestor',pr['mergeCommit']['oid'],'origin/main']);count=verify_bytes(pub,'origin/main',s['immutable_files']);s.update(phase='merged',pr=pr,verified_published_payloads=count);save(marker(pub),s);log('Publication merged and exact payloads verified',pr=pr,payloads=count);return s

def require_plan_merged(pub):
    need(marker(pub).exists(),'Install, publish and merge this registered plan before execution');s=load(marker(pub));need(s['phase']=='merged' and s['package_sha256']==sha(ROOT/'SHA256SUMS'),'This package plan has not been merged')
    pr=view(pub,s['pr']['url']);need(pr['state']=='MERGED' and pr['headRefOid']==s['commit'] and pr.get('mergeCommit'),'Registered plan merge identity differs')
    cmd(pub,['git','fetch','origin','refs/heads/main:refs/remotes/origin/main']);cmd(pub,['git','merge-base','--is-ancestor',pr['mergeCommit']['oid'],'origin/main']);verify_bytes(pub,'origin/main',s['immutable_files']);return pr
