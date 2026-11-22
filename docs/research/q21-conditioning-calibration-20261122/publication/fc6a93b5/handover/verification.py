"""Standard-library-only archive and retained-field verification; no solver calls."""
from contextlib import contextmanager
from pathlib import Path,PurePosixPath
import fcntl,hashlib,json,math,statistics,subprocess,zipfile
from common import ROOT,canonical,load,log,need,save,sha,stamp,verify_manifest
EVIDENCE=ROOT/'assessment/data/completed-evidence.zip'
UNIT='matter-waves-q21-conditioning.service'

def safe_name(name):
    p=PurePosixPath(name);need(name and not p.is_absolute() and '..' not in p.parts and '\\' not in name and '\n' not in name and '\r' not in name,'Unsafe relative path: '+name);return p

def archive(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Evidence CRC/duplicate failure');sums={};members={}
        for n in names:safe_name(n);need(not n.endswith(('.npz','.so')),'Full fields/binaries do not belong in compact evidence')
        for row in z.read('SHA256SUMS').decode().splitlines():
            h,n=row.split('  ',1);safe_name(n);need(n not in sums,'Duplicate checksum member');data=z.read(n);need(hashlib.sha256(data).hexdigest()==h,'Evidence checksum differs: '+n);sums[n]=h;members[n]=data
        need(set(sums)|{'SHA256SUMS'}==set(names),'Evidence checksum coverage differs');members['SHA256SUMS']=z.read('SHA256SUMS')
    return members,sums

def package():
    count=verify_manifest(ROOT);spec=load(ROOT/'SOURCE.json');need(sha(EVIDENCE)==spec['evidence_sha256'],'Reviewed evidence identity differs');need(sha(ROOT/'assessment/SHA256SUMS')==spec['review_manifest_sha256'],'Reviewed assessment identity differs');verify_manifest(ROOT/'assessment');members,sums=archive(EVIDENCE);get=lambda n:json.loads(members[n]);r=get('record.json');plan=get('handover/PLAN.json');g=plan['registered_gates'];identity=get('identity.json')
    need(identity['run_id']==spec['run_id'] and identity['package_sha256']==spec['handover_manifest_sha256'],'Wrong completed run/package');need(hashlib.sha256(members['handover/SHA256SUMS']).hexdigest()==spec['handover_manifest_sha256'],'Embedded handover differs')
    hand_sums={}
    for row in members['handover/SHA256SUMS'].decode().splitlines():
        h,n=row.split('  ',1);safe_name(n);need(n not in hand_sums and hashlib.sha256(members['handover/'+n]).hexdigest()==h,'Embedded handover payload differs: '+n);hand_sums[n]=h
    need({'handover/'+n for n in hand_sums}|{'handover/SHA256SUMS'}=={n for n in members if n.startswith('handover/')},'Embedded handover coverage differs')
    need(r['status']=='complete_pending_review' and r['error'] is None,'Source run is not a completed reviewed result');total=accepted=observations=admitted=0
    for c in r['cases']:
        folder='cases/'+c['case']['id'];safe_name(folder);history=c['history'];cp=get(folder+'/control.json');ledger=get(folder+'/attempt-ledger.json')
        need(c==get(folder+'/record.json') and get(folder+'/record.seal.json')['sha256']==sums[folder+'/record.json'],'Case record/seal differs: '+folder)
        need(cp['history']==history and cp['history_sha256']==canonical(history),'Case history differs: '+folder);need(len(history)==c['accepted_steps']+1 and len(ledger)==c['charged_attempts']==c['accepted_steps'],'Attempt accounting differs: '+folder)
        need(all(x['attempt']==i+1 and x['charged_before_execution'] for i,x in enumerate(ledger)),'Charge sequence differs');total+=len(ledger);accepted+=c['accepted_steps']
        previous=None
        for row in history:
            m=row['metrics'];finite=all(math.isfinite(m[k]) for k in ['relative_force_l2','acceleration_max','hopf_integral','minimum_corner_cone','unit_error','tail_fraction','guard_fraction']);rep=bool(finite and abs(abs(m['hopf_integral'])-21)/21<=g['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<g['unit_limit']);st=rep and m['relative_force_l2']<=g['force_limit'] and m['acceleration_max']<=g['acceleration_limit'];bd=finite and m['tail_fraction']<=g['initial_tail_limit'] and m['guard_fraction']<=g['tail_guard_limit'];need(row['gates']=={'representation':rep,'strict_stationary':st,'boundary_admitted':bd,'all_readiness_gates':st and bd},'Recorded gate decision differs')
            need(rep and bd,'Unexpected representation/boundary disposition');observations+=1;admitted+=int(st and bd)
            if row['accepted_step']:need(row['backend_audit']['passed'],'Backend audit failed in source')
            need(previous is None or m['energy']<=previous+1e-13,'Energy sequence differs');previous=m['energy']
        win=history[21:31];f=statistics.median(x['metrics']['relative_force_l2'] for x in win);a=statistics.median(x['metrics']['acceleration_max'] for x in win);rr=c['response'];need(math.isclose(rr['median_force'],f,rel_tol=1e-13) and math.isclose(rr['median_acceleration'],a,rel_tol=1e-13) and math.isclose(rr['score'],max(f/g['force_limit'],a/g['acceleration_limit']),rel_tol=1e-13),'Matched-window response differs')
    fields=get('FIELD-MANIFEST.json')['fields'];need(len(fields)==len({f['path'] for f in fields})==spec['expected_fields'],'Field inventory differs')
    for f in fields:
        safe_name(f['path']);need(get(f['path'].replace('.npz','.seal.json'))['sha256']==f['sha256'],'Field seal differs: '+f['path'])
    need(len(r['cases'])==spec['expected_cases'] and total==accepted==r['charged_optimizer_attempts']==spec['expected_attempts'] and observations==spec['expected_observations'] and admitted==0,'Reviewed outcome/count differs');need(sum(f['bytes'] for f in fields)==spec['expected_field_bytes'],'Retained field byte count differs');need(get('Q2-CONTROL.json')['gates']['all_readiness_gates'] and get('DERIVATIVE-CHECK.json')['passed'],'Instrument checks differ');need(get('SELECTION.json')['mode']=='best_measured_value_without_validated_optimum','Selection disposition differs')
    need(all(not model['validated'] for curve in get('CURVE-FITS.json').values() for model in curve['models']),'Unexpected fitted optimum');need(r['physical_time_steps']==0,'Unexpected physical-time steps')
    return spec,members,sums,{'recorded_at':stamp(),'status':'package_and_complete_results_verified','package_files':count,'compact_hashes':len(sums),'cases':len(r['cases']),'accepted_updates':accepted,'q21_observations':observations,'q21_readiness_passes':0,'new_optimizer_attempts':0,'physical_time_steps':0}

def gitdir(repo):
    result=subprocess.run(['git','-C',str(repo),'rev-parse','--absolute-git-dir'],text=True,capture_output=True);need(result.returncode==0,'Repository Git metadata unavailable: '+str(repo));return Path(result.stdout.strip())

def process_identity(pid):
    try:
        raw=Path('/proc',str(pid),'stat').read_text();v=raw[raw.rfind(')')+2:].split()
        if v[0]=='Z':return None
        return {'pid':pid,'start_ticks':v[19],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (FileNotFoundError,ProcessLookupError):return None

def inactive(run):
    if Path('/run/systemd/system').exists():
        p=subprocess.run(['systemctl','is-active',UNIT],text=True,capture_output=True);need(p.stdout.strip() not in ['active','activating','deactivating'],'Wait for the conditioning worker/service to become inactive')
    for name in ['heartbeat.json','supervisor.json','worker-launch.json']:
        if (run/name).exists():
            r=load(run/name);need(not (r.get('process_identity') and process_identity(r['pid'])==r['process_identity']),'Recorded campaign process is still active')

@contextmanager
def retained_lock(run):
    need((run/'.worker.lock').exists(),'Completed-run worker lock is missing')
    with (run/'.worker.lock').open('r') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Completed-run worker lock is held; wait for the campaign to stop')
        yield

def fingerprint(path):
    s=path.stat();return {'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'inode':s.st_ino,'device':s.st_dev}

def check_field(run,row):
    safe_name(row['path']);path=run/row['path'];need(path.is_file() and not path.is_symlink(),'Retained field missing or symlinked: '+row['path']);before=fingerprint(path);need(before['size']==row['bytes'] and sha(path)==row['sha256'],'Retained full-field hash/size differs: '+row['path'])
    with zipfile.ZipFile(path) as z:need(z.testzip() is None,'Retained NPZ CRC failed: '+row['path'])
    need(fingerprint(path)==before,'Retained field changed while verifying: '+row['path']);return {'path':row['path'],'sha256':row['sha256'],'bytes':row['bytes'],'npz_crc':'pass','fingerprint':before}

def local(repo,run=None,reuse=True):
    spec,members,sums,summary=package();run=(run or repo/spec['relative_run']).resolve();need(run.is_dir(),'Completed run not found: '+str(run)+'; use --run for its exact retained location')
    inactive(run)
    with retained_lock(run):
        need(load(run/'status.json')['status']=='complete_pending_review' and load(run/'identity.json')['run_id']==spec['run_id'],'Wrong or incomplete retained run');need(sha(run/'evidence.zip')==spec['evidence_sha256'],'Local evidence differs from reviewed archive')
        # Supervisor/log snapshots can outgrow their compact prefix; scientific
        # records, code and seals must remain byte-identical.
        for n,h in sums.items():
            if n in ['telemetry.jsonl','runner.log']:continue
            safe_name(n);need((run/n).is_file() and sha(run/n)==h,'Retained scientific metadata differs: '+n)
        rows=json.loads(members['FIELD-MANIFEST.json'])['fields'];cache=gitdir(repo)/'q21-conditioning-results-record-verification.json';old=load(cache) if cache.exists() else None
        valid=bool(reuse and old and old['package_sha256']==sha(ROOT/'SHA256SUMS') and old['source_run']==str(run) and old['evidence_sha256']==spec['evidence_sha256'] and len(old['fields'])==len(rows))
        if valid:
            for row,checked in zip(rows,old['fields']):
                path=run/row['path']
                if checked['path']!=row['path'] or checked['sha256']!=row['sha256'] or not path.is_file() or path.is_symlink() or fingerprint(path)!=checked['fingerprint']:valid=False;break
        if valid:
            log('Reused complete field verification; scientific metadata and every field fingerprint rechecked',fields=len(rows),verified_at=old['recorded_at']);return old
        checked=[]
        for i,row in enumerate(rows):
            checked.append(check_field(run,row))
            if (i+1)%4==0 or i+1==len(rows):log('Retained full fields verified',completed=i+1,total=len(rows))
        result=summary|{'recorded_at':stamp(),'source_run':str(run),'evidence_sha256':spec['evidence_sha256'],'package_sha256':sha(ROOT/'SHA256SUMS'),'fields':checked,'retained_field_bytes':sum(x['bytes'] for x in rows),'full_field_bytes_uploaded':False,'scope':'Complete local NPZ SHA256, sizes and CRCs; original compact bytes and scientific records preserved. This is not a fresh scientific metric replay.'};save(cache,result);return result
