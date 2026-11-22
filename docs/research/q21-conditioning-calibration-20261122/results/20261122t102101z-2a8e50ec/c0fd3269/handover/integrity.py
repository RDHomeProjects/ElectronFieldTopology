"""Authenticate the repaired merged source and the exact larger-box endpoint."""
import json,subprocess,zipfile,hashlib,shutil
from pathlib import Path,PurePosixPath
from common import ROOT,load,need,sha,canonical,save,stamp

def host():
    d={r.split(':')[0]:int(r.split()[1])*1024 for r in Path('/proc/meminfo').read_text().splitlines() if len(r.split())>1 and r.split()[1].isdigit()}
    return {k:d[n]/1024**3 for k,n in [('total_gib','MemTotal'),('available_gib','MemAvailable'),('swap_free_gib','SwapFree')]}
def reserves(path,launch=False):
    p=load(ROOT/'PLAN.json')['resources'];h=host();need(h['available_gib']>=(10 if launch else 6),'Host RAM reserve reached')
    if launch:need(h['swap_free_gib']>=1,'Require1GiB free swap before launch')
    need(shutil.disk_usage(path).free>=(56 if launch else 40)*1024**3,'Disk reserve reached');return h

def process_identity(pid):
    try:
        raw=Path('/proc',str(pid),'stat').read_text();v=raw[raw.rfind(')')+2:].split()
        if v[0]=='Z':return None
        return {'pid':pid,'start_ticks':v[19],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (FileNotFoundError,ProcessLookupError):return None

def alive(record):return bool(record and record.get('process_identity') and process_identity(record['pid'])==record['process_identity'])

def checked_evidence(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Compact CRC/duplicate failure');hashes={}
        for row in z.read('SHA256SUMS').decode().splitlines():
            h,n=row.split('  ',1);q=PurePosixPath(n);need(not q.is_absolute() and '..' not in q.parts and n not in hashes,'Unsafe compact member');need(hashlib.sha256(z.read(n)).hexdigest()==h,'Compact hash differs: '+n);hashes[n]=h
        need(set(hashes)|{'SHA256SUMS'}==set(names),'Compact checksum coverage differs')
    return hashes

def source_run(repo):return repo/load(ROOT/'SOURCE.json')['relative_run']

def verify_sources(repo):
    p=load(ROOT/'SOURCES.json');head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip();need(head==p['checkout_commit'],'Keep numerical checkout pinned; use the separate publication clone')
    for n,h in {**p['complete_numerical_source_sha256'],**p['source_sha256']}.items():need((repo/n).is_file() and sha(repo/n)==h,'Numerical source/lock differs: '+n)
    return canonical(p)

def authenticate(repo):
    p=load(ROOT/'SOURCE.json');out=source_run(repo);hashes=checked_evidence(out/'evidence.zip')
    need(load(out/'identity.json')['run_id']==p['run_id'] and load(out/'status.json')['status']=='complete_pending_review','Wrong/incomplete source run')
    with zipfile.ZipFile(out/'evidence.zip') as z:
        need('review/RESEAL-RECEIPT.json' in hashes,'Apply the reviewed seal repair before this campaign')
        receipt=json.loads(z.read('review/RESEAL-RECEIPT.json'));need(receipt['original_evidence_sha256']==p['original_uploaded_evidence_sha256'] and receipt['scientific_records_modified'] is False,'Unexpected repair provenance')
        need(hashlib.sha256(z.read('review/original-evidence.zip')).hexdigest()==p['original_uploaded_evidence_sha256'],'Original archived evidence differs')
        for n,h in load(ROOT/'BASELINE-HASHES.json').items():need(hashes.get(n)==h,'Scientific source payload differs: '+n)
    for n in ['record.json','FIELD-MANIFEST.json','arms/domain-pad-16/record.json','arms/domain-pad-16/control.json','arms/domain-pad-16/endpoint.seal.json']:
        need(sha(out/n)==hashes[n],'Local metadata differs from repaired evidence: '+n)
    endpoint=out/p['endpoint'];need(sha(endpoint)==p['endpoint_sha256'],'Larger-box endpoint hash differs')
    q2=repo/p['q2_relative'];need(sha(q2)==p['q2']['sha256'],'Q2 reference differs')
    return {'recorded_at':stamp(),'source_run':str(out),'endpoint':str(endpoint),'endpoint_sha256':sha(endpoint),'evidence_sha256':sha(out/'evidence.zip'),'q2':str(q2),'matching_compact_payloads':len(hashes),'original_scientific_hashes_checked':len(load(ROOT/'BASELINE-HASHES.json'))}

def read_parent(path):
    import numpy as np
    p=load(ROOT/'SOURCE.json')
    with zipfile.ZipFile(path) as z:need(z.testzip() is None,'Parent NPZ CRC differs')
    with np.load(path,allow_pickle=False) as z:
        need(str(z['identity_sha256'])==p['checkpoint_identity'] and int(z['iteration'])==425 and float(z['alpha'])==p['source_alpha'],'Parent scalar/identity differs')
        need(str(z['backend'])==p['source_backend'] and int(z['pair_count'])==0,'Parent backend/CG history differs')
        s={k:z[k].copy() for k in ['n','old_g','old_z','direction']}
        for k,a in s.items():need(a.shape==(129,129,129,3) and a.dtype==np.float64 and np.isfinite(a).all(),'Complete float64 parent memory required: '+k)
        s.update(iteration=425,alpha=float(z['alpha']),pairs=[])
    return s

def local_command(repo,args,json_result=False):
    r=subprocess.run(args,cwd=repo,capture_output=True,text=True);need(r.returncode==0,'Workstation command failed: '+repr(args)+'\n'+r.stderr);return json.loads(r.stdout) if json_result else r.stdout.strip()

def check_merge(repo,source_pub):
    p=load(ROOT/'SOURCE.json');receipt=authenticate(repo);state=load(source_pub/p['source_publication_marker'])
    need(state['phase'] in ['published','merged'] and state['kind']=='results','Source results publication must identify a published results PR')
    need(state['snapshot_sha256']==receipt['evidence_sha256'],'Merged snapshot and current repaired evidence differ')
    remote=local_command(source_pub,['git','remote','get-url','origin']);need(remote in ['https://github.com/RDHomeProjects/ElectronFieldTopology.git','https://github.com/RDHomeProjects/ElectronFieldTopology','git@github.com:RDHomeProjects/ElectronFieldTopology.git'],'Unexpected source publication remote')
    pr=local_command(source_pub,['gh','pr','view',state['pr']['url'],'--repo','RDHomeProjects/ElectronFieldTopology','--json','number,url,state,headRefOid,mergeCommit,baseRefName'],True)
    need(pr['state']=='MERGED' and pr['baseRefName']=='main' and pr['headRefOid']==state['commit'] and pr.get('mergeCommit'),'Source PR head/state/base differs')
    if state['pr'].get('mergeCommit'):need(pr['mergeCommit']==state['pr']['mergeCommit'],'Recorded source merge differs')
    local_command(source_pub,['git','fetch','origin','main']);local_command(source_pub,['git','merge-base','--is-ancestor',pr['mergeCommit']['oid'],'origin/main'])
    base=p['source_document_root']+'/results/'+p['run_id']+'/'+receipt['evidence_sha256'][:8]
    for name in ['record.json','FIELD-MANIFEST.json','arms/domain-pad-16/endpoint.seal.json','review/ASSESSMENT.json','evidence.zip']:
        r=subprocess.run(['git','show','origin/main:'+base+'/'+name],cwd=source_pub,capture_output=True);need(r.returncode==0 and hashlib.sha256(r.stdout).hexdigest()==sha(source_run(repo)/name),'Merged source bytes differ: '+name)
    result={'recorded_at':stamp(),'status':'merged_source_verified_on_workstation','pr':pr,'source_document':base,'evidence_sha256':receipt['evidence_sha256'],'package_sha256':sha(ROOT/'SHA256SUMS'),'verification':'Live gh state, exact PR head, merge ancestry and published scientific/evidence bytes'}
    save(repo/'.git/q21-conditioning-merge-check.json',result);return result
