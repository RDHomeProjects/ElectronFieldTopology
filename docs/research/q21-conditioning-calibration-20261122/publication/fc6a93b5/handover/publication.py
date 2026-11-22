"""Additive publication from the zbook, with exact merged-payload verification."""
import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
from common import ROOT,load,log,need,save,sha,stamp,verify_manifest
from verification import EVIDENCE,gitdir,local,package,safe_name
REMOTE='https://github.com/RDHomeProjects/ElectronFieldTopology.git'
REPOSITORY='RDHomeProjects/ElectronFieldTopology'
DOC=Path('docs/research/q21-conditioning-calibration-20261122')
MARKER='q21-conditioning-results-record-publication.json'

def command(repo,args,capture=False):
    shown=args if len(args)<=20 else args[:3]+['<'+str(len(args)-3)+' explicitly scoped paths>']
    log('Workstation publication command',argv=shown,argument_count=len(args),checkout=str(repo));r=subprocess.run(args,cwd=repo,text=True,capture_output=capture);need(r.returncode==0,'Local command failed: '+repr(args)+('\n'+r.stderr if capture else ''));return r.stdout.strip() if capture else None

def marker(pub):return gitdir(pub)/MARKER

def view(pub,reference):
    return json.loads(command(pub,['gh','pr','view',str(reference),'--repo',REPOSITORY,'--json','number,url,state,headRefOid,mergeCommit,headRefName,baseRefName'],True))

def plan_check(pub,ref='origin/main'):
    spec,members,_,_=package();expected=spec['required_plan_pr'];pr=view(pub,expected['number'])
    for key in ['number','state','baseRefName','headRefOid','mergeCommit']:need(pr[key]==expected[key],'Preparation PR identity/state differs: '+key)
    command(pub,['git','merge-base','--is-ancestor',pr['mergeCommit']['oid'],ref])
    prefix=DOC.as_posix()+'/preparation/'+spec['handover_manifest_sha256'][:8]+'/handover/'
    for n in ['PLAN.json','SOURCE.json','GATES.json','engine.py','worker.py','SHA256SUMS']:
        result=subprocess.run(['git','show',ref+':'+prefix+n],cwd=pub,capture_output=True);need(result.returncode==0 and result.stdout==members['handover/'+n],'Merged preparation bytes differ: '+n)
    return {'recorded_at':stamp(),'status':'merged_preparation_verified_on_workstation','pr':pr,'scope':'Live gh state, exact PR head/merge, main ancestry and published preparation bytes'}

def checks(pub,state):
    paths=set(command(pub,['git','diff','--cached','--name-only'],True).splitlines());need(paths<=set(state['stage_paths']),'Unexpected staged files; preserve/review them before publication')
    command(pub,['git','diff','--cached','--check'])
    if (pub/'scripts/project_records.py').exists():command(pub,['/usr/bin/python3','scripts/project_records.py','check','--compare-ref',state['base']])
    if (pub/'scripts/check_docs.py').exists():command(pub,['/usr/bin/python3','scripts/check_docs.py'])

def copy_bytes(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():need(path.is_file() and not path.is_symlink() and path.read_bytes()==data,'Existing immutable publication bytes differ: '+str(path))
    else:path.write_bytes(data)

def append(path,addition,needle):
    old=path.read_bytes() if path.exists() else b''
    if needle.encode() not in old:
        gap=b'' if old.endswith(b'\n\n') or not old else b'\n' if old.endswith(b'\n') else b'\n\n';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(old+gap+addition.encode().rstrip(b'\n')+b'\n')

def paths(spec):
    snapshot=spec['evidence_sha256'][:8];review_time=spec['reviewed_at']['utc'];from datetime import datetime
    rid=datetime.fromisoformat(review_time).strftime('%Y%m%dt%H%M%Sz-')+spec['review_manifest_sha256'][:8]
    return DOC/'results'/spec['run_id']/snapshot,DOC/'assessments'/rid,DOC/'publication'/sha(ROOT/'SHA256SUMS')[:8]

def published_bytes(pub,ref,expected):
    """One local git batch verifies every immutable file after commit or merge."""
    names=sorted(expected);queries=[ref+':'+n for n in names]
    need(all('\n' not in q and '\r' not in q for q in queries),'Unsafe Git batch reference');r=subprocess.run(['git','cat-file','--batch'],input=('\n'.join(queries)+'\n').encode(),cwd=pub,capture_output=True);need(r.returncode==0,'Git object batch failed');data=r.stdout;pos=0
    for n in names:
        end=data.find(b'\n',pos);need(end>=pos,'Incomplete Git batch header');header=data[pos:end].split();need(len(header)==3 and header[1]==b'blob','Missing/non-blob published member: '+n);size=int(header[2]);pos=end+1;value=data[pos:pos+size];need(len(value)==size and hashlib.sha256(value).hexdigest()==expected[n],'Published bytes differ: '+n);pos+=size;need(data[pos:pos+1]==b'\n','Incomplete Git batch member');pos+=1
    need(pos==len(data),'Unexpected trailing Git batch output');return len(names)

def working_bytes(pub,state):
    for n,h in state['immutable_files'].items():need((pub/n).is_file() and sha(pub/n)==h,'Immutable working-tree payload changed: '+n)

def prepare(repo,pub,run=None):
    need(pub.resolve()!=repo.resolve(),'Use the separate publication checkout');spec,members,_,_=package();receipt=local(repo,run,reuse=True);payload=sha(ROOT/'SHA256SUMS')
    state=load(marker(pub)) if (pub/'.git').exists() and marker(pub).exists() else None
    if state:
        need(state['package_sha256']==payload,'Existing publication belongs to another package')
        if state['phase'] in ['applied','committed','published','merged']:
            if state['phase']=='applied':
                need(command(pub,['git','branch','--show-current'],True)==state['branch'],'Publication branch changed');working_bytes(pub,state);checks(pub,state)
            log('Results and scientific assessment already prepared',phase=state['phase']);return state
    if not state:
        if not pub.exists():
            source=Path.home()/'ElectronFieldTopology-Q21-conditioning-record-20261122'
            if not (source/'.git').exists():source=repo
            subprocess.run(['git','clone','--no-hardlinks',str(source),str(pub)],check=True);command(pub,['git','remote','set-url','origin',REMOTE])
        else:need(command(pub,['git','remote','get-url','origin'],True) in [REMOTE,REMOTE.removesuffix('.git'),'git@github.com:'+REPOSITORY+'.git'],'Unexpected publication remote')
        need(not command(pub,['git','status','--porcelain'],True),'Publication checkout has changes; no reset or overwrite is performed')
        command(pub,['git','fetch','origin','main']);prior=plan_check(pub);base=command(pub,['git','rev-parse','origin/main'],True);branch='analysis/q21-conditioning-results-and-review-20261123-'+payload[:8];command(pub,['git','switch','-c',branch,base]);state={'recorded_at':stamp(),'kind':'completed-results-and-scientific-review','phase':'staging','base':base,'branch':branch,'package_sha256':payload,'evidence_sha256':spec['evidence_sha256'],'source_run':receipt['source_run'],'prior_plan':prior,'pr':None,'local_verification':receipt};save(marker(pub),state)
    need(state['phase']=='staging' and command(pub,['git','branch','--show-current'],True)==state['branch'],'Unexpected staging state or branch');raw,review,record=paths(spec);files={}
    def put(rel,data):
        copy_bytes(pub/rel,data);files[rel.as_posix()]=hashlib.sha256(data).hexdigest()
    for n,data in members.items():put(raw/n,data)
    put(raw/'evidence.zip',EVIDENCE.read_bytes())
    for f in sorted((ROOT/'assessment').rglob('*')):
        if f.is_file() and '__pycache__' not in f.parts:put(review/f.relative_to(ROOT/'assessment'),f.read_bytes())
    for f in sorted(ROOT.rglob('*')):
        if f.is_file() and '__pycache__' not in f.parts:put(record/'handover'/f.relative_to(ROOT),f.read_bytes())
    frozen=state['local_verification'];public={k:v for k,v in frozen.items() if k!='fields'};public['fields']=[{k:v for k,v in x.items() if k!='fingerprint'} for x in frozen['fields']]
    put(record/'VERIFIED-RETAINED-FIELDS.json',(json.dumps(public,indent=2,allow_nan=False)+'\n').encode());put(record/'PREPARATION-MERGE-CHECK.json',(json.dumps(state['prior_plan'],indent=2,allow_nan=False)+'\n').encode())
    # Extra files in new immutable destinations are not silently staged.
    for prefix in [raw,review,record]:
        actual={f.relative_to(pub).as_posix() for f in (pub/prefix).rglob('*') if f.is_file() and '__pycache__' not in f.parts};expected={n for n in files if n.startswith(prefix.as_posix()+'/')};need(actual==expected,'Unexpected files in immutable publication destination: '+prefix.as_posix())
    attrs=DOC/'.gitattributes'
    for rule in ['results/** -text -diff -filter -merge','assessments/** -text -diff -filter -merge','publication/** -text -diff -filter -merge']:append(pub/attrs,rule,rule)
    rawrel=raw.relative_to(DOC);reviewrel=review.relative_to(DOC);recordrel=record.relative_to(DOC);tag='Completed conditioning results and scientific review — '+spec['run_id']
    addition='## '+tag+'\n\nCompleted unresolved preparation:580 accepted updates across13 cases; no Q21 stationarity or physical-time result. All recorded representation/boundary gates and the Q2 control passed. The early shift0.125 benefit did not persist at120 updates, and no response fit qualified as an optimum. The bulk Q2–Q32 recommendation is a diagnostic audit and pilot, not an automatic full sweep.\n\n[Original browser report]('+rawrel.as_posix()+'/REPORT.html) · [complete measured record]('+rawrel.as_posix()+'/record.json) · [unchanged evidence ZIP]('+rawrel.as_posix()+'/evidence.zip).\n\n[Detailed scientific review]('+reviewrel.as_posix()+'/ASSESSMENT.html) · [Markdown review]('+reviewrel.as_posix()+'/ASSESSMENT.md) · [literature alignment and sources]('+reviewrel.as_posix()+'/LITERATURE-SOURCES.json) · [retained-field verification]('+recordrel.as_posix()+'/VERIFIED-RETAINED-FIELDS.json).\n\n[Measured parameter curves]('+reviewrel.as_posix()+'/parameter-response.png) · [matched long continuation]('+reviewrel.as_posix()+'/matched-continuation.png) · [localized residual diagnostic]('+reviewrel.as_posix()+'/localized-residual.png). Full field arrays remain local and are listed with hashes.\n'
    append(pub/DOC/'README.md',addition,tag)
    link='[Completed Q21 conditioning results and scientific review]('+review.as_posix()+'/ASSESSMENT.html)';append(pub/'README.md',link,link)
    state.update(phase='staging',raw_path=raw.as_posix(),review_path=review.as_posix(),record_path=record.as_posix(),immutable_files=files,stage_paths=sorted(set(files)|{'README.md',(DOC/'README.md').as_posix(),attrs.as_posix()}));save(marker(pub),state)
    command(pub,['git','add','--',*state['stage_paths']]);checks(pub,state);state['phase']='applied';save(marker(pub),state);log('Complete results and scientific analysis staged',branch=state['branch'],immutable_files=len(files),assessment_browser=str(pub/review/'ASSESSMENT.html'),retained_field_files=len(frozen['fields']),new_optimizer_attempts=0);return state

def finalize_merge(pub,state,pr):
    need(pr['state']=='MERGED' and pr.get('mergeCommit') and pr['headRefOid']==state['commit'],'Merged PR identity differs');command(pub,['git','fetch','origin','main']);command(pub,['git','merge-base','--is-ancestor',pr['mergeCommit']['oid'],'origin/main']);count=published_bytes(pub,'origin/main',state['immutable_files'])
    for name,needle in [('README.md',state['review_path']+'/ASSESSMENT.html'),((DOC/'README.md').as_posix(),Path(state['review_path']).relative_to(DOC).as_posix()+'/ASSESSMENT.html'),((DOC/'README.md').as_posix(),Path(state['raw_path']).relative_to(DOC).as_posix()+'/REPORT.html')]:
        text=command(pub,['git','show','origin/main:'+name],True);need(needle in text,'Merged navigation link is missing: '+name)
    state.update(phase='merged',pr=pr,merged_verification={'recorded_at':stamp(),'immutable_payload_files':count,'all_published_bytes_match':True,'merge_ancestor_of_origin_main':True,'navigation_links_verified':True});save(marker(pub),state);log('Complete results and detailed scientific review merged and byte-verified',pr=pr,verified_payloads=count,assessment_browser=str(pub/state['review_path']/'ASSESSMENT.html'));return state

def execute(mode,repo,pub,run=None):
    if mode in ['install','record-results']:return prepare(repo,pub,run)
    package();need((pub/'.git').exists() and marker(pub).exists(),'Install this record package before publication');state=load(marker(pub));need(state['package_sha256']==sha(ROOT/'SHA256SUMS'),'Publication package identity differs')
    if state['phase']=='merged':return finalize_merge(pub,state,view(pub,state['pr']['url']))
    need(command(pub,['git','branch','--show-current'],True)==state['branch'],'Publication branch changed')
    if mode=='publish':
        local(repo,Path(state['source_run']),reuse=True)
        if state['phase']=='applied':
            working_bytes(pub,state);checks(pub,state)
            if command(pub,['git','diff','--cached','--name-only'],True):command(pub,['git','commit','-m','Record complete Q21 conditioning results and scientific review'])
            else:need(command(pub,['git','rev-parse','HEAD'],True)!=state['base'],'No publication content is committed')
            published_bytes(pub,'HEAD',state['immutable_files']);state.update(phase='committed',commit=command(pub,['git','rev-parse','HEAD'],True));save(marker(pub),state)
        need(state['phase'] in ['committed','published'],'Install before publish');need(not command(pub,['git','status','--porcelain'],True),'Publication checkout changed after commit');need(command(pub,['git','rev-parse','HEAD'],True)==state['commit'],'Publication head changed');published_bytes(pub,'HEAD',state['immutable_files']);command(pub,['git','push','-u','origin',state['branch']])
        probe=subprocess.run(['gh','pr','view',state['branch'],'--repo',REPOSITORY,'--json','url'],cwd=pub,text=True,capture_output=True)
        if probe.returncode==0:url=json.loads(probe.stdout)['url']
        else:url=command(pub,['gh','pr','create','--repo',REPOSITORY,'--base','main','--head',state['branch'],'--title','Record Q21 conditioning results, scientific assessment and Q2–Q32 recommendation','--body-file',str(ROOT/'PR-BODY.md')],True).splitlines()[-1]
        pr=view(pub,url);need(pr['headRefOid']==state['commit'] and pr['baseRefName']=='main','PR head/base differs');state.update(phase='published',pr=pr);save(marker(pub),state)
        if pr['state']=='MERGED':return finalize_merge(pub,state,pr)
        need(pr['state']=='OPEN','PR is not open or merged');log('Results and scientific review published',pr=pr);return state
    need(mode=='merge' and state['phase']=='published','Publish before merging');pr=view(pub,state['pr']['url']);need(pr['headRefOid']==state['commit'] and pr['baseRefName']=='main','PR head/base changed')
    if pr['state']!='MERGED':
        need(pr['state']=='OPEN','PR is not open or merged');checks_json=json.loads(command(pub,['gh','pr','view',pr['url'],'--repo',REPOSITORY,'--json','statusCheckRollup'],True))
        if checks_json['statusCheckRollup']:command(pub,['gh','pr','checks',pr['url'],'--repo',REPOSITORY,'--watch','--interval','10'])
        else:log('No remote checks registered; local checks passed and repository protections remain enforced')
        command(pub,['gh','pr','merge',pr['url'],'--repo',REPOSITORY,'--squash','--delete-branch','--match-head-commit',state['commit']]);pr=view(pub,pr['url'])
    return finalize_merge(pub,state,pr)
