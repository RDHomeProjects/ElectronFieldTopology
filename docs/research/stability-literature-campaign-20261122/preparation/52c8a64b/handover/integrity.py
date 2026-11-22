"""Pinned completed scientific evidence and retained-field authentication."""
import fcntl,json,shutil,subprocess,zipfile
from pathlib import Path
from common import ROOT,load,need,sha,canonical,stamp,verify_manifest

def host():
    values={r.split(':')[0]:int(r.split()[1])*1024 for r in Path('/proc/meminfo').read_text().splitlines() if len(r.split())>1 and r.split()[1].isdigit()}
    return {k:values[n]/1024**3 for k,n in [('total_gib','MemTotal'),('available_gib','MemAvailable'),('swap_free_gib','SwapFree')]}

def process_identity(pid):
    try:
        raw=Path('/proc',str(pid),'stat').read_text();parts=raw[raw.rfind(')')+2:].split()
        if parts[0]=='Z':return None
        return {'pid':pid,'start_ticks':parts[19],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (FileNotFoundError,ProcessLookupError):return None

def alive(record):return bool(record and record.get('process_identity') and process_identity(record['pid'])==record['process_identity'])

def verify_sources(repo):
    expected=load(ROOT/'SOURCES.json');head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    need(head==expected['checkout_commit'],'Numerical checkout changed; retain the pinned checkout and publish through the separate clone')
    for name,digest in {**expected['complete_numerical_source_sha256'],**expected['source_sha256']}.items():
        need((repo/name).is_file() and sha(repo/name)==digest,'Numerical source/lock hash differs: '+name)
    return canonical(expected)

def checked_evidence(path):
    import hashlib
    from pathlib import PurePosixPath
    with zipfile.ZipFile(path) as z:
        names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Evidence duplicate/CRC failure');hashes={}
        for row in z.read('SHA256SUMS').decode().splitlines():
            digest,name=row.split('  ',1);pp=PurePosixPath(name)
            need(not pp.is_absolute() and '..' not in pp.parts and name not in hashes,'Unsafe evidence member')
            need(hashlib.sha256(z.read(name)).hexdigest()==digest,'Evidence member hash differs: '+name);hashes[name]=digest
        need(set(names)==set(hashes)|{'SHA256SUMS'},'Evidence checksum coverage differs')
    return hashes

def source_run(repo):return repo/load(ROOT/'SOURCE.json')['relative_path']

def authenticate(repo):
    spec=load(ROOT/'SOURCE.json');run=source_run(repo);archive=run/'evidence.zip'
    need(sha(ROOT/'data/completed-evidence.zip')==spec['evidence_sha256']==sha(archive),'Completed source evidence differs')
    hashes=checked_evidence(archive)
    for name in ['identity.json','record.json','q21/exact/record.json','q21/exact/control.json','q21/exact/endpoint.seal.json','FIELD-MANIFEST.json']:
        need(sha(run/name)==hashes[name],'Source compact/local metadata differs: '+name)
    r=load(run/'q21/exact/record.json');need(r['final_iteration']==335 and r['new_attempts_charged']==20 and r['accepted_new_steps']==20,'Wrong completed tranche')
    need(load(run/'status.json')['status']=='complete_pending_review','Source run is incomplete')
    endpoint=run/'q21/exact/endpoint.npz';need(sha(endpoint)==spec['endpoint_sha256'],'Exact335 field differs')
    seal=load(endpoint.with_suffix('.seal.json'));need(seal['identity_sha256']==spec['endpoint_identity'],'Exact335 optimizer identity differs')
    manifest=load(run/'FIELD-MANIFEST.json')['fields']
    for row in manifest:
        pp=Path(row['path']);need(not pp.is_absolute() and '..' not in pp.parts,'Unsafe field manifest path')
        need(sha(run/pp)==row['sha256'],'Retained source checkpoint differs: '+str(pp))
    q2=repo/spec['original_run']/spec['q2']['original_relative_path'];need(sha(q2)==spec['q2']['sha256'],'Q2 reference differs')
    return {'recorded_at':stamp(),'source_run':str(run),'endpoint':str(endpoint),'endpoint_sha256':sha(endpoint),'q2':str(q2),'compact_members':len(hashes),'retained_fields_verified':len(manifest),'source_modified':False}

def parent_state(path):
    import numpy as np
    spec=load(ROOT/'SOURCE.json')
    with np.load(path,allow_pickle=False) as z:
        need(int(z['iteration'])==335 and str(z['identity_sha256'])==spec['endpoint_identity'] and str(z['backend'])=='cuda','Parent checkpoint metadata differs')
        need(float(z['alpha'])==spec['source_alpha'],'Parent alpha differs')
        s={k:z[k].copy() if z[k].size else None for k in ['n','old_g','old_z','direction']}
        for k,a in s.items():need(a is not None and a.shape==(97,97,97,3) and a.dtype==np.float64 and np.isfinite(a).all(),'Parent full float64 memory differs: '+k)
        s.update(iteration=335,alpha=float(z['alpha']),pairs=[])
    return s

def reserves(out,launch=False):
    p=load(ROOT/'PLAN.json')['resources'];h=host()
    need(h['available_gib']>=(p['minimum_available_gib'] if launch else 6),'Host RAM reserve reached; close memory-heavy applications and retry')
    if launch:need(h['swap_free_gib']>=p['minimum_swap_free_gib'],'Require at least 1 GiB free swap; retain the temporary swap if still active')
    need(shutil.disk_usage(out).free>=(p['initial_disk_free_gib'] if launch else 40)*1024**3,'Disk reserve reached')
    return h
