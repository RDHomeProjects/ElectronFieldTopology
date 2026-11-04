"""Prepare an append-only S5-B-005 Git record, without network writes. Apache-2.0."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
STUDY='s5-b-005'
PREFIX=Path('reports/s5-b/005-boost-initialization/runs')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def stamp():
    now=datetime.now(timezone.utc)
    return {'utc':now.isoformat(),'melbourne':now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}


def prepare(out):
    subprocess.run(['git','diff','--quiet'],cwd=ROOT,check=True)
    subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT,check=True)
    out=Path(out).resolve();ledger=json.loads((out/'study.json').read_text())
    if (out/'launch.json').exists():
        launch=json.loads((out/'launch.json').read_text())
        try:
            pid=launch['pid'];parts=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
            identity=Path('/proc/sys/kernel/random/boot_id').read_text().strip()+':'+os.readlink(f'/proc/{pid}/ns/pid')+':'+parts[19]
            if parts[0]!='Z' and identity==launch['process_identity']:raise ValueError('Study runner is still active')
        except (FileNotFoundError,ProcessLookupError):pass
    manifest=json.loads((out/'manifest.json').read_text());exit_=json.loads((out/'exit.json').read_text())
    rid=ledger['record_id']
    if not re.fullmatch('[0-9]{8}t[0-9]{6}z-[0-9a-f]{8}',rid):raise ValueError('Noncanonical record ID')
    if (ledger['status']!='complete_pending_review' or exit_['status']!='complete_pending_review'
            or len(ledger['cases'])!=ledger['expected_cases']):raise ValueError('Study is not completely recorded')
    if manifest['tracked_worktree_dirty']:raise ValueError('Run used tracked uncommitted code; preserve it and review before publication')
    for name,digest in manifest['source_sha256'].items():
        if sha(ROOT/'src/electron_field_topology'/name)!=digest:raise ValueError('Source changed since this run: '+name)
    with zipfile.ZipFile(out/'evidence.zip') as z:
        names=z.namelist();hashes=json.loads(z.read('evidence-hashes.json'))['sha256']
        if len(names)!=len(set(names)) or set(names)!=set(hashes)|{'evidence-hashes.json'} or z.testzip() is not None:
            raise ValueError('Evidence coverage/corruption failure')
        for name,digest in hashes.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=digest:raise ValueError('Evidence hash mismatch: '+name)
        if json.loads(z.read('study.json'))!=ledger or json.loads(z.read('manifest.json'))!=manifest:
            raise ValueError('Evidence and current study metadata differ')
    target=ROOT/PREFIX/rid
    if target.exists():raise ValueError('Published/staged record path exists; preserve its immutable bytes')
    target.mkdir(parents=True)
    try:
        for name in ['evidence.zip','SUMMARY.md','case-metrics.csv','manifest.json','controls.json','exit.json']:
            shutil.copy2(out/name,target/name)
        record={'study_id':STUDY,'record_id':rid,'role':'measurement','recorded_at':stamp(),
            'source_commit':manifest['source_commit'],'outcome':'complete_pending_scientific_review',
            'config_sha256':{'study':ledger['config_sha256']},'input_sha256':{'fingerprint':ledger['input_fingerprint']},
            'evidence_sha256':{'evidence.zip':sha(target/'evidence.zip')},
            'commands':['bash RUN.sh start','bash RUN.sh status','bash RUN.sh prepare-results'],
            'environment':{k:manifest[k] for k in ['python','numpy','scipy','platform']},
            'model_and_units':'Unchanged SF-relativistic-neutral-v1; c=1; dimensionless model units',
            'field_retention':'Original full fields: GitHub release archive-workstation-20261104t023917z-b0d06afa, root r031. No new evolved fields.',
            'limitations':['Cubic candidate has not been evolved','Comoving sampling is not a solver refinement',
                'Restricted phase fit is reported beside raw vectors','Original failed gates retained','No automatic acceptance'],
            'supersedes':None}
        (target/'record.json').write_text(json.dumps(record,indent=2)+'\n')
        (target/'README.md').write_text('# S5-B-005 retained-field measurements\n\nUTC: '+record['recorded_at']['utc']+
            '; Melbourne: '+record['recorded_at']['melbourne']+'.\n\n'+
            '[Summary](SUMMARY.md), [control results](controls.json), [compact evidence](evidence.zip), '+
            '[provenance](record.json).\n\n'+
            'Reconstruction and restricted field registration only. Original trajectories are unchanged; '+
            'the cubic candidate has not been evolved. Completion awaits scientific review.\n')
        (target/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(target.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
        path=ROOT/'docs/project/roadmap.json';registry=json.loads(path.read_text());registry['updated_at']=record['recorded_at']
        study=next(s for s in registry['studies'] if s['id']==STUDY)
        study['state']='recorded';study['gate']='open'
        study['finding']='The workstation reconstruction/registration measurements are recorded, pending scientific assessment. No new trajectory or gate acceptance.'
        study['next_action']='Assess old/candidate initialization and raw/phase-registered comoving residuals before deciding the focused S5-B-006 evolution.'
        study['records'].append({'role':'measurement','path':(PREFIX/rid/'README.md').as_posix(),'label':'Retained-field initialization and registration measurements'})
        path.write_text(json.dumps(registry,indent=2)+'\n')
        subprocess.run(['python3','scripts/project_records.py','render'],cwd=ROOT,check=True)
        subprocess.run(['python3','scripts/project_records.py','check'],cwd=ROOT,check=True)
        subprocess.run(['python3','scripts/check_docs.py'],cwd=ROOT,check=True)
        names=subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0')
        navigation=[p for p in names if p and (p.startswith('docs/') or p.startswith('reports/'))]
        subprocess.run(['git','add','--',str(PREFIX/rid),*navigation],cwd=ROOT,check=True)
        print(json.dumps({'recorded_at':stamp(),'staged_report':str(target),'scientific_review_pending':True},indent=2))
    except Exception:
        # Preserve partial output for diagnosis; never erase a staged/registered scientific record.
        print('Publication preparation stopped. Partial files are retained at '+str(target));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    prepare(p.parse_args().output)
