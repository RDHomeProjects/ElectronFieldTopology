"""Audit retained Q22 records; no full-field or physical-time calculation.

Software: Apache-2.0. Original scalar/diagram records remain unchanged.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/s5-a/q22-fresh-20261101T102757+1100'
SOURCE_MERGE = '31732a6b5c1558927fe47ae7fc7f6d81a4b30d2c'
ARCHIVE_BLOB = '790d3104850b5b6d32d97672dbcfe398a99fab92'
ARCHIVE_SHA256 = 'fe4f75db8d1823242e5448ee414d7f83d6e1301007f2f604f8e240a3c6eaa4c5'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition: raise ValueError(message)


def timestamps():
    now = datetime.now(timezone.utc)
    return {'utc': now.isoformat(timespec='seconds'),
            'melbourne': now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat(timespec='seconds')}


def gates(result):
    c, a, b = result['config'], result['initial'], result['final']
    q = c['expected_q']
    return {'initial_charge': abs(abs(a['hopf_integral'])-q)/q <= .05,
            'final_charge': abs(abs(b['hopf_integral'])-q)/q <= .05,
            'resolved_cells': min(a['minimum_corner_cone'], b['minimum_corner_cone']) > 0,
            'unit_norm': b['unit_error'] < 1e-12,
            'stationary': b['cpu_tangent_gradient_rms'] < 1e-3,
            'virial': b['virial_residual'] < .05,
            'endpoint_cpu_audit': all(x['passed'] for x in b['cpu_endpoint_audit'].values()),
            'source_energy': abs(b['energy']-c['published_energy'])/c['published_energy'] < .03
                             if 'published_energy' in c else None}


def audit(topology=False):
    records = REPORT / 'records'
    raw = (REPORT / 'evidence.zip').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA256, 'Archive SHA-256 mismatch')
    require(hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest() == ARCHIVE_BLOB, 'Archive Git blob mismatch')
    with zipfile.ZipFile(REPORT / 'evidence.zip') as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate archive member')
        manifest = json.loads(archive.read('evidence-hashes.json'))
        require(set(names) == set(manifest['files']) | {'evidence-hashes.json'}, 'Archive coverage mismatch')
        for name, entry in manifest['files'].items():
            data = archive.read(name)
            require(hashlib.sha256(data).hexdigest() == entry['sha256'], 'Member hash: '+name)
            require((records/name).read_bytes() == data, 'Readable copy: '+name)
        require((records/'evidence-hashes.json').read_bytes() == archive.read('evidence-hashes.json'), 'Manifest copy differs')
    for name in ('summary.json', 'campaign.json', 'plan.json', 'SUMMARY.md'):
        require((REPORT/name).read_bytes() == (records/name).read_bytes(), 'Root copy differs: '+name)
    summary, campaign, plan = [read(records/n) for n in ('summary.json', 'campaign.json', 'plan.json')]
    require(summary['source_unchanged'] is True, 'Campaign source-change flag')
    for name, expected in campaign['source_sha256'].items():
        require(digest(ROOT/name) == expected, 'Campaign code/lock/seed changed: '+name)
    require(campaign['initialization_mode'] == 'fresh_seed', 'Fresh mode expected')
    rows, statuses, missing_fields, endpoints = {}, Counter(), set(), {}
    pass_count = 0; worst_history_increase = 0.; scalar_audits = 0
    for stage in plan['stages']:
        key = stage['id']; job = campaign['stages'][key]
        previous = None
        for attempt in job['attempts']:
            folder = records/attempt['directory']; result = read(folder/'result.json')
            cfg, m, history = [read(folder/n) for n in ('config.json', 'manifest.json', 'history.json')]
            require(result['config'] == cfg and result['history'] == history, 'Config/history differs: '+folder.name)
            require(digest(folder/'config.json') == attempt['config_sha256'] == m['config_sha256'], 'Config hash mismatch')
            require(read(records/'configs'/(folder.name+'.json')) == cfg, 'Generated config differs')
            require((cfg['n'], cfg['h']) == (stage['n'], stage['h']), 'Planned geometry differs')
            require(m['git_commit'] == campaign['git_commit'] and not m['dirty_tree'], 'Unclean/different run source')
            require(m['source_unchanged_during_run'] and m['device_validation']['passed'], 'Device/source audit failed')
            require(m['backend'] == 'cuda-float64', 'Actual float64 CUDA backend required')
            require(all(x['passed'] for x in m['device_validation']['checks'].values()), 'Device check failed')
            require(m['lock_sha256'] == campaign['source_sha256']['uv.lock'], 'Lock mismatch')
            require(all(campaign['source_sha256'][p] == h for p,h in m['source_sha256'].items()), 'Numerical hash mismatch')
            for name, expected in m['artifacts_sha256'].items():
                path = folder/name
                if path.exists(): require(digest(path) == expected, 'Case artifact mismatch: '+str(path))
                else:
                    require(path.suffix == '.npz', 'Non-field artifact absent: '+str(path))
                    missing_fields.add(str(path.relative_to(records)))
            checkpoint = cfg.get('initial_checkpoint')
            if checkpoint:
                source_folder = records/'cases'/Path(checkpoint).parent.name
                source_manifest = read(source_folder/'manifest.json')
                require(m['initial_checkpoint_sha256'] == attempt['input_sha256'] == source_manifest['artifacts_sha256']['final.npz'], 'Checkpoint lineage mismatch')
                if previous:
                    require(Path(checkpoint).parent.name == previous.name, 'Pass skipped its own endpoint')
                else:
                    dependency = campaign['stages'][stage['from']]['directory']
                    require(source_folder.name == Path(dependency).name, 'Refinement skipped its dependency')
            else:
                require('seed_config' in stage and previous is None, 'Unexpected fresh seed')
                require(attempt['input_sha256'] is None, 'Unexpected input digest on fresh seed')
            for phase in ('initial','final'):
                require(all(x['passed'] for x in result[phase]['cpu_endpoint_audit'].values()), 'CPU endpoint audit failed')
                item=result[phase]
                require(abs(item['e2']+item['e4']-item['energy']) < 1e-12*max(1.,abs(item['energy'])), 'Energy split identity failed')
                require(abs(abs(item['e2']-item['e4'])/item['energy']-item['virial_residual']) < 1e-12, 'Virial identity failed')
                require(abs(item['cpu_tangent_gradient_rms']-item['tangent_gradient_rms']) < 1e-9, 'CPU/GPU residual disagreement')
                scalar_audits += 1
            values = [r['energy'] for r in history]
            require(values and result['final'] == history[-1], 'History endpoint differs')
            changes = [b-a for a,b in zip(values,values[1:])]
            worst_history_increase = max([worst_history_increase]+changes)
            require(all(d <= 1e-10*max(1.,abs(a)) for a,d in zip(values,changes)), 'Nonmonotone recorded history')
            if previous:
                prior = read(previous/'result.json')['final']['energy']
                require(abs(result['initial']['energy']-prior) < 1e-10*max(1.,abs(prior)), 'Restart energy discontinuity')
            statuses[result['status']] += 1; previous = folder; pass_count += 1
        require(job['status'] == 'stationary' and previous is not None, 'Final stationary endpoint absent: '+key)
        result = read(previous/'result.json'); endpoint = result['final']; endpoints[key] = result
        require(summary['stages'][key]['final'] == endpoint, 'Summary endpoint mismatch: '+key)
        measured = gates(result)
        require(all(value for value in measured.values() if value is not None), 'Scalar gate failed: '+key)
        require(summary['stages'][key]['artifact_audit'], 'Summary artifact audit failed')
        analysis = records/'analysis'/previous.name
        scale = read(analysis/'scaling.json')
        require(scale['checkpoint_sha256'] == read(previous/'manifest.json')['artifacts_sha256']['final.npz'], 'Scaling references different field')
        require(len(scale['rows']) == 5 and len(scale['finite_difference_comparisons']) == 2, 'Incomplete scaling audit')
        require(all(v['minimum_corner_cone'] > 0 for v in scale['rows']), 'Scaling cell failure')
        differences = scale['finite_difference_comparisons']
        require(all(abs(v['normalized_energy_derivative']) < .05 and abs(v['difference_from_e2_minus_e4']) < .05 for v in differences), 'Scaling gate failed')
        rows[key] = {'n': result['config']['n'], 'h': result['config']['h'], 'half_width': (result['config']['n']-1)*result['config']['h']/2,
                     'energy': endpoint['energy'], 'cpu_residual': endpoint['cpu_tangent_gradient_rms'],
                     'hopf_integral': endpoint['hopf_integral'], 'relative_hopf_error': abs(abs(endpoint['hopf_integral'])-result['config']['expected_q'])/result['config']['expected_q'],
                     'virial_residual': endpoint['virial_residual'], 'unit_error': endpoint['unit_error'],
                     'minimum_corner_cone': endpoint['minimum_corner_cone'], 'passes':len(job['attempts']),
                     'gates': measured, 'max_dilation_derivative': max(abs(v['normalized_energy_derivative']) for v in differences),
                     'max_dilation_identity_defect':max(abs(v['difference_from_e2_minus_e4']) for v in differences),
                     'relative_source_energy_error': abs(endpoint['energy']-12.509)/12.509 if key.startswith('q22') and not key.startswith('q22-comparison') else None}
    require(all(v['status']=='completed' and v['returncode']==0 for v in campaign['analysis'].values()), 'Analysis task failed')
    pairs = [('mesh_129_161','q22-129-fresh','q22-161-polish'),('mesh_161_193','q22-161-polish','q22-193-polish'),
             ('domain_129_161_h012','q22-129-fresh','q22-domain-161'),('domain_129_193_h012','q22-129-fresh','q22-domain-193'),
             ('domain_161_193_h012','q22-domain-161','q22-domain-193'),('domain_161_193_h0096','q22-161-polish','q22-domain-fine-193')]
    comparisons = {}
    for name,a,b in pairs:
        if name.startswith('mesh_'):
            require(abs(rows[a]['half_width']-rows[b]['half_width'])<1e-12, 'Mesh box mismatch')
        else:
            require(rows[a]['h']==rows[b]['h'] and rows[b]['half_width']>rows[a]['half_width'], 'Domain spacing/box mismatch')
        delta = abs(rows[b]['energy']-rows[a]['energy'])/rows[a]['energy']
        require(abs(delta-summary['comparisons'][name]['relative_energy_change']) < 1e-14, 'Summary difference mismatch')
        require(delta < .02, 'Energy gate failed')
        comparisons[name] = {'first':a,'second':b,'relative_change':delta,'limit':.02,'pass':True}
    for n, cable in [(129,'q22-129-fresh'),(161,'q22-161-polish'),(193,'q22-193-polish')]:
        other = 'q22-comparison-'+str(n); a,b=rows[cable],rows[other]
        require((a['n'],a['h'],a['half_width'])==(b['n'],b['h'],b['half_width']), 'Ranking geometry mismatch')
        comparisons['same_mesh_'+str(n)] = {'cable_energy':a['energy'],'comparator_energy':b['energy'],
            'absolute_gap':a['energy']-b['energy'],'relative_gap':(a['energy']-b['energy'])/a['energy'],
            'scope':'same geometry, independently audited stationary endpoints; not a global-minimum or Hessian proof'}
    start=datetime.fromisoformat(campaign['started_at']['utc']); finish=datetime.fromisoformat(summary['generated_at']['utc'])
    result = {'assessed_at':timestamps(),'source_merge':SOURCE_MERGE,'source_run_commit':campaign['git_commit'],
              'assessment_code_sha256':digest(Path(__file__)),
              'scope':'retained records/finite curves only; full-field endpoint quantities are reported workstation audits, not recomputed here',
              'archive':{'bytes':len(raw),'sha256':ARCHIVE_SHA256,'git_blob':ARCHIVE_BLOB,'hashed_members':len(manifest['files']),'entries':len(names)},
              'provenance':{'source_and_lock_hashes_checked':len(campaign['source_sha256']),'passes':pass_count,
                  'analysis_tasks':len(campaign['analysis']),'cpu_endpoint_audits':scalar_audits,'pass_solver_statuses':dict(statuses),
                  'bulk_checkpoint_files_absent':len(missing_fields),'worst_recorded_energy_increase':worst_history_increase,
                  'elapsed_to_final_summary_seconds':(finish-start).total_seconds()},
              'stages':rows,'comparisons':comparisons,'topology':{'checked':False},
              'disposition':'scalar_gates_verified; finite_diagram_review_required' }
    if topology: result['topology'] = topology_audit(records, campaign)
    if topology: result['disposition'] = 'bounded_Q22_numerical_benchmark_supported_with_finite_diagram_limits'
    return result


def topology_audit(records, campaign):
    import numpy as np
    from spherogram import Link
    from importlib.metadata import version
    from electron_field_topology.sf_topology import canonical_gauss, resample, jones_a
    from electron_field_topology.linking import gauss_link, closed_curve
    refs=read(records/'analysis/references/references.json')['cable']['diagrams']
    reference_polynomials={json.dumps(d['jones_A'],sort_keys=True) for d in refs}
    require(len(reference_polynomials)==1 and len(refs)==9, 'Inconsistent cable reference')
    trefoil_polys={json.dumps(jones_a(Link('3_1')),sort_keys=True),json.dumps(jones_a(Link('3_1').mirror()),sort_keys=True)}
    cable, comparator, witnesses, projections, pair_projections = {}, {}, 0, 0, 0
    for key,job in campaign['stages'].items():
        if not key.startswith('q22'): continue
        case=Path(job['directory']).name; folder=records/'analysis'/case
        data=read(folder/'topology.json')['phases']['final']
        manifest=read(records/'cases'/case/'manifest.json')
        require(data['checkpoint_sha256']==manifest['artifacts_sha256']['final.npz'],'Topology field hash mismatch')
        output={}
        for target,t in data['targets'].items():
            require(t['status']=='closed_components','Unresolved extracted curve')
            with np.load(folder/('final-'+target+'-curves.npz'),allow_pickle=False) as archive:
                curves=[archive[name] for name in sorted(archive.files,key=lambda n:int(n.split('_')[-1]))]
            require(len(curves)==t['components'],'Curve count mismatch')
            for curve,component in zip(curves,t['components_data']):
                closed_curve(curve); require(len(curve)-1==component['vertices'],'Vertex count mismatch')
            if key.startswith('q22-comparison'):
                require(t['components']==3,'Comparator is not the observed three-component link')
                classes=[]
                for comp in t['components_data']:
                    diagrams=comp['diagrams']; require(len(diagrams)==9,'Missing component projections')
                    if all(d.get('crossings')==0 for d in diagrams): classes.append('unknot_finite_diagram')
                    elif all(d.get('crossings')==3 and json.dumps(d.get('jones_A'),sort_keys=True) in trefoil_polys for d in diagrams): classes.append('trefoil_compatible_three_crossing_diagram')
                    else: raise ValueError('Comparator component classification unresolved')
                require(classes.count('unknot_finite_diagram')==2,'Comparator unknot count')
                require(classes.count('trefoil_compatible_three_crossing_diagram')==1,'Comparator trefoil count')
                pairs=[]
                for row in t['pairwise_link_checks']:
                    values=[v['linking_number'] for v in row['observations']]
                    require(len(values)==6 and len(set(values))==1,'Inconsistent pairwise diagram linking')
                    pair_projections+=len(values)
                    independent=[]
                    for n in (256,384):
                        value=gauss_link(resample(curves[row['first']],n),resample(curves[row['second']],n))
                        independent.append(value)
                    pairs.append({'first':row['first'],'second':row['second'],'signed_diagram_link':values[0],
                                  'gauss_cross_checks':independent,
                                  'maximum_gauss_difference':max(abs(v['linking_integral']-values[0]) for v in independent)})
                require(sorted(abs(x['signed_diagram_link']) for x in pairs)==[1,2,2],'Link magnitudes differ')
                output[target]={'components':classes,'pairwise':pairs,'scope':'finite polygons; orientation-dependent signs'}
            else:
                require(t['components']==1,'Cable endpoint changed component count')
                diagrams=t['components_data'][0]['diagrams']
                require(len(diagrams)==9 and all(d.get('components')==1 and json.dumps(d.get('jones_A'),sort_keys=True) in reference_polynomials for d in diagrams),'Cable projection/polynomial inconsistency')
                projections+=len(diagrams)
                witness=read(folder/('cable-witness-'+target+'.json'))
                require(witness['matched'],'Missing finite common-diagram witness')
                w=witness['witness']; word=tuple(map(tuple,w['canonical_gauss']))
                for name,pool in [('reference_path',refs),('candidate_path',diagrams)]:
                    path=w[name]
                    require(any(path['segments']==d['segments'] and path['view']==d['view'] and path['input_pd']==(d.get('simplified_pd') or d.get('pd')) for d in pool),'Witness input membership mismatch')
                    require(canonical_gauss(Link(path['output_pd']))==word,'Stored output Gauss word mismatch')
                witnesses+=1
                output[target]={'components':1,'projection_checks':len(diagrams),'stored_witness_inputs_and_output_words_verified':True,
                                'limit':'No explicit certified move trace; saved random seed is not a deterministic replay certificate'}
        (comparator if key.startswith('q22-comparison') else cable)[key]=output
    require(witnesses==12 and projections==108 and pair_projections==108,'Unexpected topology coverage')
    return {'checked':True,'software':{name:version(name) for name in ('numpy','scipy','snappy','spherogram')},'cable_endpoints':cable,'comparator_endpoints':comparator,
            'cable_witnesses':witnesses,'cable_projection_checks':projections,'comparator_pair_projection_checks':pair_projections,
            'scope':'stored input membership, recomputed common words and independent polygon Gauss linking; no field re-extraction or formal continuum isotopy'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--topology',action='store_true',help='Recompute finite diagram words and polygon Gauss linking; needs locked topology dependencies')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); result=audit(a.topology)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'assessed_at':result['assessed_at'],'disposition':result['disposition'],
          'archive_members':result['archive']['hashed_members'],'passes':result['provenance']['passes'],
          'stages':len(result['stages']),'topology':result['topology'].get('checked')},indent=2))


if __name__=='__main__': main()
