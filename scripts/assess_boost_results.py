"""Verify compact S5-B-005 evidence and recompute scalar assessment. Apache-2.0.

No NPZ fields are supplied here: initial-state replay and field-derived diagnostics
are retained workstation measurements, not re-executed by this verifier.
"""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import zipfile
from zoneinfo import ZoneInfo

EXPECTED='321a46ae81be7d799b7a392d1a94b573405c0fe9582babe9395a650c21be15e4'
RUN='20261104t131812z-4e8c880c'
SOURCE='461c9bc41d1979bf9d5f20a584eafa530d1999d8'
FIXED_LIMIT=1e-10


def need(ok,message):
    if not ok:raise ValueError(message)


def sha_bytes(data):return hashlib.sha256(data).hexdigest()


def canonical(value):return sha_bytes(json.dumps(value,sort_keys=True,separators=(',',':')).encode())


def timestamp():
    now=datetime.now(timezone.utc)
    return {'utc':now.isoformat(),'melbourne':now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}


def bounds(values):return {'min':min(values),'max':max(values),'median':statistics.median(values)}


def verify(path, source_dir=None):
    path=Path(path);digest=sha_bytes(path.read_bytes());need(digest==EXPECTED,'Unexpected evidence archive SHA-256')
    with zipfile.ZipFile(path) as z:
        names=z.namelist();need(len(names)==len(set(names)),'Duplicate ZIP members')
        need(all(not Path(n).is_absolute() and '..' not in Path(n).parts and '\\' not in n for n in names),'Unsafe ZIP member')
        need(sum(i.file_size for i in z.infolist())<20_000_000,'Unexpected archive expansion')
        need(z.testzip() is None,'Corrupt ZIP member')
        hashes=json.loads(z.read('evidence-hashes.json'))['sha256']
        need(set(names)==set(hashes)|{'evidence-hashes.json'},'Member coverage differs')
        for name,h in hashes.items():need(sha_bytes(z.read(name))==h,'Member digest differs: '+name)
        get=lambda name:json.loads(z.read(name))
        ledger=get('study.json');manifest=get('manifest.json');cfg=get('config.json');inv=get('inventory.json');controls=get('controls.json')
        need(ledger['record_id']==RUN and manifest['source_commit']==SOURCE,'Run/source identity differs')
        need(ledger['status']=='complete_pending_review' and not manifest['tracked_worktree_dirty'],'Run completion/provenance differs')
        need(canonical(cfg)==ledger['config_sha256']==manifest['config_sha256'] and cfg==manifest['config'],'Configuration digest differs')
        need(ledger['source_sha256']==manifest['source_sha256'],'Code maps differ')
        need(controls==ledger['controls'] and controls['passed'] and all(controls['checks'].values()),'Control record differs')
        need(inv['ready'] and not inv['missing_or_changed'],'Input inventory not ready')
        need(len(inv['files'])==66 and len(inv['selected_seeds'])==6,'Input inventory coverage differs')
        fingerprint=canonical({'evidence':cfg['evidence_sha256'],'files':{r['relative_path']:r.get('sha256') for r in inv['files']}})
        need(fingerprint==ledger['input_fingerprint']==manifest['input_fingerprint']==inv['input_fingerprint'],'Input fingerprint differs')
        cases=list(ledger['cases'].values());need(len(cases)==ledger['expected_cases']==30,'Case count differs')
        need(set(inv['selected_cases'])==set(ledger['cases']),'Selected case coverage differs')
        case_names={f"cases/{r['case_id']}.json" for r in cases}
        need(case_names=={n for n in names if n.startswith('cases/')},'Case member coverage differs')
        for r in cases:
            need(get(f"cases/{r['case_id']}.json")==r,'Case/ledger mismatch')
            need(r['dt']==.01 and r['time']==1. and r['initial']['old_replay_bit_exact'],'Observation/replay flag differs')
        expected={(f'q{q}-n{n}-L{l}',beta,axis) for q in [1,2] for n,l in [(81,16),(101,16),(101,20)]
                  for beta,axis in [(0,0),(.1,0),(.1,2),(.3,0),(.3,2)]}
        need({(r['seed_id'],r['beta'],r['axis']) for r in cases}==expected,'Scientific matrix coverage differs')
        csv_rows=list(csv.DictReader(io.StringIO(z.read('case-metrics.csv').decode())))
        need(len(csv_rows)==30 and len({r['case_id'] for r in csv_rows})==30,'CSV coverage differs')
        for line in csv_rows:
            r=ledger['cases'][line['case_id']];i=r['initial'];c=r['comoving']['evolved_vs_own_initial']
            pairs=[('old_rate_relative',i['old_transport']['full']['rate_relative_l2']),('new_rate_relative',i['new_transport']['full']['rate_relative_l2']),
                   ('comoving_raw',c['raw_relative_l2']),('comoving_phase_registered',c['phase_registered_relative_l2'])]
            for key,value in pairs:need((line[key]=='' if value is None else float(line[key])==value),'CSV scalar differs: '+key)
        if source_dir is not None:
            for name,h in manifest['source_sha256'].items():need(sha_bytes((Path(source_dir)/name).read_bytes())==h,'Source hash differs: '+name)
    moving=[r for r in cases if r['beta']];rest=[r for r in cases if not r['beta']]
    def rate(r,kind,region='full',metric='rate_relative_l2'):return r['initial'][kind+'_transport'][region][metric]
    reductions=[1-rate(r,'new')/rate(r,'old') for r in moving]
    rows=[]
    for r in cases:
        initial=r['initial'];obs=r['comoving']['evolved_vs_own_initial']
        rows.append({'case_id':r['case_id'],'seed_id':r['seed_id'],'q':r['q'],'beta':r['beta'],'axis':r['axis'],
            'old_rate':rate(r,'old'),'new_rate':rate(r,'new'),'old_core_rate':rate(r,'old','core'),'new_core_rate':rate(r,'new','core'),
            'raw_comoving':obs['raw_relative_l2'],'registered_comoving':obs['phase_registered_relative_l2'],
            'phase_angle':obs['global_internal_phase_radians'],'new_initial_field_change':initial['new_vs_old']['raw_relative_l2'],
            'fixed_field_deviation':initial['new_transport']['fixed_face_field_deviation'],
            'fixed_rate_max':initial['new_transport']['fixed_face_rate_max'],
            'fixed_layers_need_readmission':bool(initial['new_transport']['fixed_face_field_deviation']>FIXED_LIMIT or initial['new_transport']['fixed_face_rate_max']>FIXED_LIMIT),
            'original_failed_checks':[k for k,v in r['original_case_checks'].items() if not v]})
    groups=[]
    for q in [1,2]:
        for beta in [.1,.3]:
            selected=[r for r in moving if r['q']==q and r['beta']==beta]
            groups.append({'q':q,'beta':beta,'cases':len(selected),'old_rate_mean':statistics.mean(rate(r,'old') for r in selected),
                'new_rate_mean':statistics.mean(rate(r,'new') for r in selected),
                'raw_comoving':bounds([r['comoving']['evolved_vs_own_initial']['raw_relative_l2'] for r in selected])})
    phase={}
    for axis in [0,2]:
        selected=[r for r in moving if r['axis']==axis]
        phase['xz'[axis//2]]={'angle':bounds([r['comoving']['evolved_vs_own_initial']['global_internal_phase_radians'] for r in selected]),
            'relative_l2_reduction':bounds([1-r['comoving']['evolved_vs_own_initial']['phase_registered_relative_l2']/r['comoving']['evolved_vs_own_initial']['raw_relative_l2'] for r in selected])}
    failed={}
    for r in cases:
        for k,v in r['original_case_checks'].items():
            if not v:failed[k]=failed.get(k,0)+1
    refinements=[];domain_pairs=[]
    lookup={(r['seed_id'],r['beta'],r['axis']):r for r in moving}
    for q in [1,2]:
        for beta in [.1,.3]:
            for axis in [0,2]:
                a=lookup[(f'q{q}-n81-L16',beta,axis)];b=lookup[(f'q{q}-n101-L16',beta,axis)];c=lookup[(f'q{q}-n101-L20',beta,axis)]
                refinements.append({'q':q,'beta':beta,'axis':axis,'new_rate_ratio_fine_to_coarse':rate(b,'new')/rate(a,'new')})
                domain_pairs.append({'q':q,'beta':beta,'axis':axis,'new_rate_ratio_L20_to_L16_matched_h':rate(c,'new')/rate(a,'new')})
    result={'verified_at':timestamp(),'archive_sha256':digest,'archive_members':len(names),'hashed_members':len(hashes),
        'record_id':RUN,'source_commit':SOURCE,'source_hashes_checked':len(manifest['source_sha256']) if source_dir is not None else 0,
        'cases':30,'moving_cases':24,'rest_cases':6,'source_input_files_recorded':66,'old_initial_replay_flags_true':30,
        'independent_full_field_replay_performed':False,'old_rate':bounds([rate(r,'old') for r in moving]),
        'new_rate':bounds([rate(r,'new') for r in moving]),'rate_relative_reduction':bounds(reductions),
        'absolute_rms_reduction':bounds([1-rate(r,'new',metric='rate_absolute_rms')/rate(r,'old',metric='rate_absolute_rms') for r in moving]),
        'core_rate_reduction':bounds([1-rate(r,'new','core')/rate(r,'old','core') for r in moving]),
        'improved_moving_cases':sum(rate(r,'new')<rate(r,'old') for r in moving),'phase':phase,
        'raw_comoving':bounds([r['comoving']['evolved_vs_own_initial']['raw_relative_l2'] for r in moving]),
        'registered_comoving':bounds([r['comoving']['evolved_vs_own_initial']['phase_registered_relative_l2'] for r in moving]),
        'native_initial_field_change':bounds([r['initial']['new_vs_old']['raw_relative_l2'] for r in moving]),
        'candidate_fixed_field_max':max(r['initial']['new_transport']['fixed_face_field_deviation'] for r in cases),
        'candidate_fixed_rate_max':max(r['initial']['new_transport']['fixed_face_rate_max'] for r in cases),
        'fixed_layer_cases':[r['case_id'] for r in rows if r['fixed_layers_need_readmission']],
        'fixed_layer_observational_threshold':FIXED_LIMIT,
        'unit_max':max(r['initial']['new_transport']['unit_error'] for r in cases),
        'tangency_max':max(r['initial']['new_transport']['tangency_error'] for r in cases),
        'original_selected_case_passes':sum(all(r['original_case_checks'].values()) for r in cases),
        'original_selected_failures':failed,'groups':groups,'case_metrics':rows,'mesh_pairs':refinements,'matched_spacing_domain_pairs':domain_pairs,
        'disposition':'conditional_cubic_candidate; fixed_layer_readmission_required; no_new_dynamics_acceptance'}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--source-directory',type=Path)
    a=p.parse_args();r=verify(a.evidence,a.source_directory);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['verified_at','archive_members','cases','improved_moving_cases','disposition']},indent=2))
