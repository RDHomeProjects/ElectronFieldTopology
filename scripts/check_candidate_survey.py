"""Standard-library audit of completed S5-B-010 source/compact/full-field seals.

No NumPy installation, relaxation or physical-time calculation is required.
Apache-2.0.
"""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
def need(ok,message):
    if not ok:raise ValueError(message)
def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while b:=f.read(8*1024**2):h.update(b)
    return h.hexdigest()
def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def audit(out,repo=ROOT):
    out=Path(out).resolve();repo=Path(repo).resolve();d=load(out/'campaign.json');c=load(out/'plan.json');exit=load(out/'exit.json')
    need(not d.get('test_fixture'),'Synthetic software fixtures cannot be published as production results')
    need(d['status'] in {'complete_pending_review','complete_reference_blocked'} and exit['status']==d['status'] and exit['exit_code']==0,'Campaign lacks a matching completed exit receipt')
    need(canonical(c)==d['config_sha256'] and c['format']=='EFT-intermediate-q-survey-v1','Configuration differs')
    need('q2-reference' in d['rest'],'Required Q2 reference record missing')
    if d['status']=='complete_pending_review':need(all(seed['id']+'-coarse-fresh' in d['rest'] for seed in c['seeds']) and set(d['selected'])=={'q3','q4','q7'},'Completed matrix lacks candidate outcomes')
    else:need('candidate-survey' in d['skips'] and d['cases'].get('q2-reference-dt0.01',{}).get('status')!='screen_pass','Reference-blocked disposition differs')
    labels={s['id']:s['q'] for s in c['seeds']};labels['q2-reference']=2
    for r in d['rest'].values():
        need(r['seed_id'] in labels and r['q']==labels[r['seed_id']],'Unexpected candidate/Q label')
        if r['status']=='stationary':
            v=r['final']['stationarity'];need(v['relative_force_l2']<=c['readmission']['relative_force_l2'] and v['acceleration_max']<=c['readmission']['acceleration_max'] and abs(abs(v['hopf_integral'])-r['q'])/r['q']<=.05 and v['minimum_corner_cone']>0 and v['unit_error']<1e-10,'Stationary label conflicts with recorded gates')
    for r in d['cases'].values():
        need(r['rest_id'] in d['rest'] and r['q']==d['rest'][r['rest_id']]['q'],'Motion lineage/Q differs')
        if r.get('physical'):need(d['rest'][r['rest_id']]['status']=='stationary','Unqualified rest state was evolved')
        if r['status']=='screen_pass':need(all(r['assessment']['legacy_motion']['checks'].values()) and r['assessment']['tail_pass_all_observations'] and r['final_time']>=r['duration']-1e-12 and r['assessment']['maximum_observed_tail_fraction']<=c['runtime_tail_reserve'],'Motion pass conflicts with retained criteria/window')
    commit=d['source_commit'];need(len(commit)==40 and all(x in '0123456789abcdef' for x in commit),'Invalid source commit')
    subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=repo,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for name,h in d['source_sha256'].items():
        need(Path(name).name==name and sha(repo/'src/electron_field_topology'/name)==h,'Current numerical source differs '+name)
        raw=subprocess.check_output(['git','show',commit+':src/electron_field_topology/'+name],cwd=repo);need(hashlib.sha256(raw).hexdigest()==h,'Source commit does not contain measured code '+name)
    for name,h in d['dependency_sha256'].items():
        need(name in {'pyproject.toml','uv.lock'} and sha(repo/name)==h,'Dependency lock/config changed')
        need(hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=repo)).hexdigest()==h,'Source commit dependency pin differs')
    need(sha(out/'sources/q2.npz')==c['reference_source']['sha256'],'Retained Q2 source differs')
    zip_path=out/'evidence.zip';ledger=load(out/'evidence-hashes.json')
    with zipfile.ZipFile(zip_path) as z:
        names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Evidence ZIP CRC/uniqueness failed')
        need(set(names)==set(ledger['sha256'])|{'evidence-hashes.json'},'ZIP ledger coverage differs')
        for name,h in ledger['sha256'].items():
            p=PurePosixPath(name);need(not p.is_absolute() and '..' not in p.parts and not (out/name).is_symlink(),'Unsafe evidence member')
            need(hashlib.sha256(z.read(name)).hexdigest()==sha(out/name)==h,'Compact evidence member changed '+name)
        need(z.read('evidence-hashes.json')==(out/'evidence-hashes.json').read_bytes(),'ZIP/disk ledger differs')
    seals={}
    def local(name):
        p=Path(name);need('..' not in p.parts,'Unsafe original path')
        if p.is_absolute():
            if p.is_relative_to(out):return p
            need(p.parts.count(d['record_id'])==1,'Unknown original absolute run path');p=Path(*p.parts[p.parts.index(d['record_id'])+1:])
        need('..' not in p.parts and not p.is_absolute(),'Unsafe run path');return out/p
    def check(name,h):
        p=local(name).relative_to(out)
        need('..' not in p.parts and not (out/p).is_symlink(),'Unsafe full-field path');need(sha(out/p)==h,'Retained field/metadata seal changed '+str(p));seals[p.as_posix()]=h
    for r in d['rest'].values():
        check('rest/'+r['id']+'/initial.npz',r['initial_checkpoint_sha256']);check(r['checkpoint'],r['checkpoint_sha256'])
        if 'core_diagnostics' in r:
            core=r['core_diagnostics'];check(core['path'],core['sha256'])
            for target in load(out/core['path'])['targets']:
                if target.get('curve_file'):check(target['curve_file'],target['curve_sha256'])
    for r in d['cases'].values():
        if r.get('initial_checkpoint_sha256'):check('cases/'+r['id']+'/admitted.npz',r['initial_checkpoint_sha256'])
        if r.get('final_checkpoint'):check(r['final_checkpoint'],r['final_checkpoint_sha256'])
        for v in r.get('milestones',{}).values():check(v['checkpoint'],v['checkpoint_sha256'])
        for old in r['attempts']:
            p=local(old)/'snapshots.json'
            for snap in load(p) if p.exists() else []:check(snap['path'],snap['sha256'])
    for path in out.rglob('*.npz'):
        with zipfile.ZipFile(path) as z:need(z.testzip() is None,'NPZ CRC failure '+str(path))
    return {'recorded_at':stamp(),'record_id':d['record_id'],'source_commit':commit,'status':d['status'],'config_sha256':d['config_sha256'],'evidence_sha256':sha(zip_path),'compact_hashed_members':len(ledger['sha256']),'sealed_field_or_curve_files':len(seals),'rest_records':len(d['rest']),'case_records':len(d['cases']),'scope':'Source commit/locks, all compact members, declared full-field/curve/snapshot hashes and NPZ CRCs checked; this is not a new scientific metric replay.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--output',type=Path);a=p.parse_args();r=audit(a.run,a.repo)
    if a.output:need(not a.output.exists(),'Audit output must be a new path');a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r))
if __name__=='__main__':main()
