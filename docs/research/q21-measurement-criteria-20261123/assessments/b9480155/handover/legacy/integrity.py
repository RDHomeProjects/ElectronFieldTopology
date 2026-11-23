"""Authenticate immutable parents and the unchanged numerical checkout."""
import os,subprocess,zipfile,hashlib,shutil
from pathlib import Path,PurePosixPath
from common import ROOT,load,need,sha,canonical,stamp

def host():
    d={r.split(':')[0]:int(r.split()[1])*1024 for r in Path('/proc/meminfo').read_text().splitlines() if len(r.split())>1 and r.split()[1].isdigit()}
    return {k:d[n]/1024**3 for k,n in [('total_gib','MemTotal'),('available_gib','MemAvailable'),('swap_free_gib','SwapFree')]}
def reserves(path,launch=False):
    h=host();need(h['available_gib']>=(10 if launch else 6),'Host RAM reserve reached')
    if launch:need(h['swap_free_gib']>=1,'Require 1 GiB free swap before launch')
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

def verify_sources(repo):
    p=load(ROOT/'NUMERICAL-SOURCE.json');head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip();need(head==p['checkout_commit'],'Keep numerical checkout pinned; use the separate publication clone')
    for n,h in {**p['complete_numerical_source_sha256'],**p['source_sha256']}.items():need((repo/n).is_file() and sha(repo/n)==h,'Numerical source/lock differs: '+n)
    return canonical(p)

def source_run(repo):return repo/load(ROOT/'SOURCE.json')['relative_run']
def authenticate(repo):
    p=load(ROOT/'SOURCE.json');out=source_run(repo);need(sha(out/'evidence.zip')==p['evidence_sha256'],'Completed conditioning evidence differs');hashes=checked_evidence(out/'evidence.zip')
    need(load(out/'status.json')['status']=='complete_pending_review' and load(out/'identity.json')['run_id']==p['run_id'],'Source is not the completed declared run')
    names=['record.json','FIELD-MANIFEST.json','cases/scan-baseline/control.json','cases/scan-baseline/endpoint.seal.json','cases/scan-baseline/record.json','cases/optimal-validation/endpoint.seal.json']
    for n in names:need(sha(out/n)==hashes[n],'Local scientific metadata differs: '+n)
    paths={'endpoint':out/p['endpoint'],'best':out/p['best']['path'],'contrast':out/p['contrast']['path'],'q2':repo/p['q2_relative']}
    for k,expected in [('endpoint',p['endpoint_sha256']),('best',p['best']['sha256']),('contrast',p['contrast']['sha256']),('q2',p['q2']['sha256'])]:need(sha(paths[k])==expected,'Retained field differs: '+k)
    return {'recorded_at':stamp(),'source_run':str(out),'evidence_sha256':p['evidence_sha256'],**{k:str(v) for k,v in paths.items()},'endpoint_sha256':p['endpoint_sha256'],'best_sha256':p['best']['sha256'],'contrast_sha256':p['contrast']['sha256'],'matching_compact_payloads':len(hashes)}

def read_parent(path):
    import numpy as np
    p=load(ROOT/'SOURCE.json')
    with zipfile.ZipFile(path) as z:need(z.testzip() is None,'Parent NPZ CRC differs')
    with np.load(path,allow_pickle=False) as z:
        need(str(z['identity_sha256'])==p['checkpoint_identity'] and int(z['iteration'])==545 and float(z['alpha'])==p['source_alpha'],'Final parent scalar/identity differs')
        need(str(z['backend'])==p['source_backend'] and int(z['pair_count'])==0,'Parent backend/history differs')
        s={k:z[k].copy() if z[k].size else None for k in ['n','old_g','old_z','direction']}
        for k,a in s.items():need(a is not None and a.shape==(129,129,129,3) and a.dtype==np.float64 and np.isfinite(a).all(),'Complete float64 parent memory required: '+k)
        s.update(iteration=545,alpha=float(z['alpha']),pairs=[])
    return s

def merged_source(pub):
    p=load(ROOT/'SOURCE.json');remote=subprocess.check_output(['git','-C',str(pub),'remote','get-url','origin'],text=True).strip();need(remote in ['https://github.com/RDHomeProjects/ElectronFieldTopology.git','https://github.com/RDHomeProjects/ElectronFieldTopology','git@github.com:RDHomeProjects/ElectronFieldTopology.git'],'Unexpected publication repository')
    subprocess.run(['git','-C',str(pub),'fetch','origin','refs/heads/main:refs/remotes/origin/main'],check=True)
    subprocess.run(['git','-C',str(pub),'merge-base','--is-ancestor',p['required_merge'],'origin/main'],check=True)
    matches=[]
    for line in subprocess.check_output(['git','-C',str(pub),'ls-tree','-r','origin/main',p['required_published_document']],text=True).splitlines():
        meta,name=line.split('\t',1)
        if name.endswith('/evidence.zip'):
            oid=meta.split()[2];b=subprocess.check_output(['git','-C',str(pub),'cat-file','blob',oid])
            if hashlib.sha256(b).hexdigest()==p['evidence_sha256']:matches.append(name)
    need(matches,'Published main does not contain the exact reviewed source evidence')
    return {'recorded_at':stamp(),'required_merge':p['required_merge'],'published_exact_evidence_paths':matches,'main':subprocess.check_output(['git','-C',str(pub),'rev-parse','origin/main'],text=True).strip()}
