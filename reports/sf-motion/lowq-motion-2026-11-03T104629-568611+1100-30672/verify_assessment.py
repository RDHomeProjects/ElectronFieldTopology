#!/usr/bin/env python3
"""Replay compact low-Q records; does not recompute diagnostics requiring fields."""
import argparse, collections, csv, hashlib, itertools, json, math
from datetime import datetime
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo
import numpy as np

EXPECTED_SHA256 = '780cfff1d5be5fe9e61b238206aceb6a6f47a82350e8ce257c76cc79f56d8784'

def stamp():
    now = datetime.now(ZoneInfo('UTC'))
    return {'utc': now.isoformat(), 'melbourne': now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(x):
    return sha(json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())

def close(a, b, label):
    assert np.allclose(a, b, rtol=1e-10, atol=3e-14), (label, a, b)

def fit(rows):
    t = np.array([r['time'] for r in rows]); x = np.array([r['centroid'] for r in rows])
    return np.linalg.lstsq(np.stack([t-t[0], np.ones(len(t))], axis=-1), x, rcond=None)[0][0]

def analyze(archive, summary=None):
    import zipfile
    archive = Path(archive)
    assert sha(archive.read_bytes()) == EXPECTED_SHA256, 'Unexpected evidence archive'
    z = zipfile.ZipFile(archive); names = z.namelist()
    assert len(names) == len(set(names)), 'Duplicate archive members'
    assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names)
    assert z.testzip() is None, 'CRC failure'
    read = lambda n: json.loads(z.read(n))
    hashes = read('evidence-hashes.json')['sha256']
    assert set(names) == set(hashes) | {'evidence-hashes.json'}
    assert all(sha(z.read(n)) == h for n, h in hashes.items())
    if summary is not None:
        assert Path(summary).read_bytes() == z.read('SUMMARY.md')
    c = read('campaign.json'); plan = read('plan.json'); limits = plan['limits']
    assert canonical(plan) == c['config_sha256']
    assert c['status'] == 'complete_pending_review'
    assert len(c['seeds']) == 6 and len(c['cases']) == 60
    expected = set()
    for s in plan['seeds']:
        sid = f"q{s['q']}-n{s['nodes']}-L{s['length']:g}"
        for (beta, axis), dt in itertools.product([(0.,0)]+list(itertools.product(plan['betas'],plan['axes'])),plan['time_steps']):
            expected.add(f'{sid}-b{beta:g}-a{axis}-dt{dt:g}')
    assert expected == set(c['cases']), 'Unexpected/incomplete matrix'
    source_verified = []
    for name, h in c['source_sha256'].items():
        p = Path(__file__).parent/'source-snapshots'/name
        assert p.exists() and sha(p.read_bytes()) == h, ('Source mismatch', name)
        source_verified.append(name)
    failures = collections.Counter(); rows_out = []; histories = {}; gates_replayed = 0
    commits = set(); history_rows = 0; seeds_out = []
    for sid,s in c['seeds'].items():
        assert read(f'readmission/{sid}/result.json') == s
        m = read(f'readmission/{sid}/manifest.json')
        assert canonical(m['config']) == m['config_sha256']
        assert canonical(m['code_hashes']) == m['code_sha256']
        assert all(c['source_sha256'][k] == h for k,h in m['code_hashes'].items())
        f = s['final'];q=s['q_label']
        assert s['status']=='stationary' and f['relative_force_l2']<=plan['readmission']['relative_force_l2']
        assert f['acceleration_max']<=plan['readmission']['acceleration_max']
        assert abs(abs(f['hopf_integral'])-q)/q<=plan['readmission']['charge_relative_error']
        assert f['minimum_corner_cone']>0 and f['unit_error']<1e-10
        ref=c['cases'][f'{sid}-b0-a0-dt0.01'];initial=ref['initial'];a=ref['assessment']
        seeds_out.append({'seed_id':sid,'q':q,**c['seed_configs'][sid],**f,
            'continuum_energy':initial['rest_continuum_energy'],
            'stress_frobenius_over_energy':float(np.linalg.norm(initial['rest_integrated_stress'])/initial['rest_continuum_energy']),
            'rest_tail_initial':initial['boundary_shell_energy_fraction'],
            'rest_tail_final':a['final']['boundary_shell_energy_fraction'],
            'iterations':s['iterations'],'wall_seconds':s['wall_seconds']})
    for name, case in c['cases'].items():
        assert case['status']=='complete' and len(case['attempts'])==1
        prefix=f'cases/{name}/';a=read(prefix+'assessment.json');a0={k:v for k,v in a.items() if k!='assessed_at'}
        assert a0==case['assessment']
        manifest=read(prefix+'attempt-001/manifest.json');result=read(prefix+'attempt-001/result.json')
        physics=read(prefix+'attempt-001/physics.json');hist=read(prefix+'history-combined.json')
        assert result==case['result'] and physics==case['physical']==manifest['physics']
        assert hist==read(prefix+'attempt-001/history.json')
        assert canonical(physics)==manifest['physics_sha256']==result['physics_sha256']
        assert canonical(manifest['physics_source_sha256'])==manifest['code_sha256']
        for k,h in manifest['physics_source_sha256'].items():
            if k in c['source_sha256']:assert c['source_sha256'][k]==h
        assert not manifest['git_worktree_dirty'];commits.add(manifest['git_commit'])
        assert manifest['model_id']=='SF-relativistic-neutral-v1'
        assert manifest['scheme']=='D4-action-projected-RK4-v1'
        assert physics['initial']['sha256']==c['seeds'][case['seed_id']]['field_sha256']
        expected_steps=list(range(0,physics['steps']+1,physics['diagnostic_every']))
        assert [r['step'] for r in hist]==expected_steps
        assert len(hist)>2 and hist[-1]['time']==plan['duration']==result['time']
        for r in hist:
            close(r['time'],r['step']*physics['dt'],name+' time')
            assert r['source_work_since_start']==0 and r['source_power']==0
            assert r['source_impulse_since_start']==[0.,0.,0.] and r['source_force']==[0.,0.,0.]
            assert r['boundary']=='fixed_reflecting'
        history_rows+=len(hist); histories[name]=hist
        e0=hist[0]['energy']; p0=np.array(hist[0]['momentum'])
        edrift=max(abs(r['energy']-e0)/abs(e0) for r in hist)
        pdrift=max(float(np.linalg.norm(np.array(r['momentum'])-p0))/abs(e0) for r in hist)
        velocity=fit(hist);target=np.zeros(3);target[case['axis']]=case['beta']
        speed=float(np.linalg.norm(velocity-target));speedrel=speed/abs(case['beta']) if case['beta'] else None
        close(edrift,a['max_energy_relative_drift'],name+' energy')
        close(pdrift,a['max_momentum_drift_over_initial_energy'],name+' momentum')
        close(velocity,a['fitted_centroid_velocity'],name+' velocity')
        close(speed,a['speed_absolute_error'],name+' speed')
        if speedrel is not None:close(speedrel,a['speed_relative_error'],name+' relative speed')
        close(hist[-1]['continuum_energy'],a['final']['continuum_energy'],name+' continuum E')
        close(hist[-1]['centroid'],a['final']['centroid'],name+' centroid')
        initial=case['initial'];b=case['beta'];axis=case['axis'];g=1/math.sqrt(1-b*b)
        restE=initial['rest_continuum_energy'];S=np.array(initial['rest_integrated_stress'])
        partP=np.zeros(3);partP[axis]=g*b*restE
        partEdef=abs(hist[0]['continuum_energy']/(g*restE)-1)
        partPdef=float(np.linalg.norm(np.array(hist[0]['momentum'])-partP)/(g*restE))
        tensorE=g*(restE+b*b*S[axis,axis]);tensorP=b*S[axis,:].copy();tensorP[axis]=g*b*(restE+S[axis,axis])
        tensorEdef=abs(hist[0]['continuum_energy']/tensorE-1)
        tensorPdef=float(np.linalg.norm(np.array(hist[0]['momentum'])-tensorP)/(g*restE))
        for label,x in [('initial_particle_energy_relative_defect',partEdef),('initial_particle_momentum_scaled_defect',partPdef),('initial_tensor_energy_relative_defect',tensorEdef),('initial_tensor_momentum_scaled_defect',tensorPdef)]:close(x,a[label],name+' '+label)
        margin=initial['initial_light_cone_clearance']-plan['duration']
        close(margin,a['initial_light_cone_margin_after_observation'],name+' clearance')
        f=a['final'];q=case['q']
        checks={'energy':edrift<=limits['energy_relative'],'momentum':pdrift<=limits['momentum_scaled'],
          'constraints':max(max(r['unit_error'],r['tangency_error']) for r in hist)<1e-10,
          'shape':a['translated_static_field_relative_l2']<=limits['shape_relative'],
          'speed':speedrel<=limits['speed_relative'] if b else speed<=limits['rest_speed_absolute'],
          'topology':abs(abs(f['hopf_integral'])-q)/q<=limits['charge_relative_error'] and f['minimum_corner_cone']>0,
          'tail':f['boundary_shell_energy_fraction']<=limits['tail_fraction'],
          'initial_particle_relations':max(partEdef,partPdef)<=limits['particle_relative'],
          'initial_boundary_clearance':margin>0}
        assert checks==a['checks']
        assert bool(all(checks.values()) and a['rest_admitted'])==a['bounded_case_gates_pass']
        gates_replayed+=len(checks);failures.update(k for k,v in checks.items() if not v)
        rows_out.append({'case_id':name,'seed_id':case['seed_id'],'q':q,'beta':b,'axis':axis,
          'dt':physics['dt'],'energy_drift':edrift,'continuum_energy_drift':max(abs(r['continuum_energy']/hist[0]['continuum_energy']-1) for r in hist),
          'momentum_drift_over_E0':pdrift,'speed_relative_error':speedrel,'speed_absolute_error':speed,
          'shape_relative_l2':a['translated_static_field_relative_l2'],'tail_initial':initial['boundary_shell_energy_fraction'],
          'tail_final':f['boundary_shell_energy_fraction'],'hopf_final':f['hopf_integral'],
          'hopf_relative_change':abs(f['hopf_integral']-initial['hopf_integral'])/q,
          'corner_cone_final':f['minimum_corner_cone'],'clearance_margin':margin,
          'initial_particle_energy_defect':partEdef,'initial_particle_momentum_defect':partPdef,
          'initial_tensor_energy_defect':tensorEdef,'initial_tensor_momentum_defect':tensorPdef,
          'max_n_projection':max(r['n_projection_max'] for r in hist),
          'max_v_projection':max(r['v_projection_max'] for r in hist),
          'wall_seconds':result['wall_seconds'],'pass':a['bounded_case_gates_pass'],
          'failed_checks':','.join(k for k,v in checks.items() if not v)})
    comparisons=read('comparisons.json');pair_out=[]
    for p in comparisons['pairs']:
        a=c['cases'][p['a']]['assessment'];b=c['cases'][p['b']]['assessment']
        ea=a['final']['continuum_energy'];eb=b['final']['continuum_energy']
        de=abs(ea-eb)/max(abs(ea),abs(eb));dv=float(np.linalg.norm(np.array(a['fitted_centroid_velocity'])-b['fitted_centroid_velocity']))
        close(de,p['energy_relative_difference'],'pair energy');close(dv,p['centroid_velocity_difference'],'pair velocity')
        close(a['translated_static_field_relative_l2'],p['shape_error_a'],'pair shape a');close(b['translated_static_field_relative_l2'],p['shape_error_b'],'pair shape b')
        row=dict(p)
        ca=c['cases'][p['a']];cb=c['cases'][p['b']]
        sa=c['seed_configs'][ca['seed_id']];sb=c['seed_configs'][cb['seed_id']]
        kind=p['kind']
        assert (ca['q'],ca['beta'],ca['axis'])==(cb['q'],cb['beta'],cb['axis'])
        if kind=='temporal':assert ca['seed_id']==cb['seed_id'] and ca['physical']['dt']!=cb['physical']['dt']
        elif kind=='spatial':assert ca['physical']['dt']==cb['physical']['dt'] and sa['length']==sb['length'] and sa['nodes']!=sb['nodes']
        elif kind=='domain':assert ca['physical']['dt']==cb['physical']['dt'] and sa['length']!=sb['length'] and abs(sa['length']/(sa['nodes']-1)-sb['length']/(sb['nodes']-1))<1e-12
        else:raise AssertionError('Unexpected pair kind')
        if p['kind']=='temporal':
            ha={round(r['time'],12):r for r in histories[p['a']]};hb={round(r['time'],12):r for r in histories[p['b']]};common=sorted(ha.keys()&hb.keys())
            va=fit([ha[t] for t in common]);vb=fit([hb[t] for t in common])
            row['matched_time_velocity_difference']=float(np.linalg.norm(va-vb))
            row['matched_time_count']=len(common)
            row['matched_centroid_max_difference']=max(float(np.linalg.norm(np.array(ha[t]['centroid'])-hb[t]['centroid'])) for t in common)
        pair_out.append(row)
    # Independently enumerate the expected controlled pairs, including their labels.
    expected_pairs=set()
    for na,nb in itertools.combinations(sorted(c['cases']),2):
        a=c['cases'][na];b=c['cases'][nb]
        if (a['q'],a['beta'],a['axis'])!=(b['q'],b['beta'],b['axis']):continue
        sa=c['seed_configs'][a['seed_id']];sb=c['seed_configs'][b['seed_id']]
        dta=a['physical']['dt'];dtb=b['physical']['dt'];kind=None
        if a['seed_id']==b['seed_id'] and dta!=dtb:kind='temporal'
        elif dta==dtb and sa['length']==sb['length'] and sa['nodes']!=sb['nodes']:kind='spatial'
        elif dta==dtb and sa['length']!=sb['length'] and abs(sa['length']/(sa['nodes']-1)-sb['length']/(sb['nodes']-1))<1e-12:kind='domain'
        if kind:expected_pairs.add((na,nb,kind))
    assert expected_pairs=={(p['a'],p['b'],p['kind']) for p in pair_out}
    assert len(pair_out)==len(expected_pairs)==70
    started=datetime.fromisoformat(c['started_at']['utc']);finished=datetime.fromisoformat(c['updated_at']['utc'])
    result={'assessed_at':stamp(),'disposition':'bounded_low_speed_Q2_case_passes; global_motion_gate_unreleased',
      'archive_sha256':EXPECTED_SHA256,'archive_members':len(names),'hashed_members_verified':len(hashes),
      'summary_byte_identical':summary is not None,'source_snapshots_matched':source_verified,'run_commits':sorted(commits),
      'campaign_started_at':c['started_at'],'campaign_finished_at':c['updated_at'],
      'campaign_elapsed_seconds':(finished-started).total_seconds(),'rest_candidates':len(seeds_out),
      'completed_cases':len(rows_out),'history_rows_replayed':history_rows,'case_check_flags_replayed':gates_replayed,
      'case_passes':sum(r['pass'] for r in rows_out),'failed_check_counts':dict(failures),
      'comparison_pair_counts':dict(collections.Counter(p['kind'] for p in pair_out)),
      'limits':limits,'seeds':seeds_out,'cases':rows_out,'comparisons':pair_out,
      'verification_scope':'Independent replay of retained scalar histories, algebra and check flags; field-derived shape, Hopf, cone, tail, radii and stress not independently recalculated without full fields.',
      'provenance_scope':'Eight campaign source files match retained handoff/main snapshots; run commit recorded by clean manifests, not authenticated by a complete submitted Git repository.'}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--summary',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=analyze(a.archive,a.summary);a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'assessment-verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for key,name in [('cases','case-metrics.csv'),('comparisons','comparison-metrics.csv')]:
        fields=list(dict.fromkeys(k for r in result[key] for k in r))
        with (a.output/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(result[key])
    print(json.dumps({k:v for k,v in result.items() if k not in ['seeds','cases','comparisons','limits']},indent=2))

if __name__=='__main__':main()
