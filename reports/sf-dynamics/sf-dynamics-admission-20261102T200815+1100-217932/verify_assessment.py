"""Read-only arithmetic replay of archived SF admission records. Apache-2.0.

Standard library only. Does not replay bulk-field integration or physical time.
"""
import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCHIVE_SHA256 = 'd46a8daddc4c975c89e9dd757ff638b319281138376314d298965074ab785804'
RUN_COMMIT = 'c515631f4420bf5295ac52195cb9eb7b8b6142ca'
RUN_TREE = 'f0decf05a33947b8ebcc761e2e1838471b66cb4f'
SOURCE_REPORT = ROOT/'reports/q18-neighbours/q18-neighbours-20261102T022100+1100-165739'


def timestamp():
    now = datetime.now(timezone.utc)
    return {'utc': now.isoformat(), 'melbourne': now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def norm(values):
    return math.sqrt(sum(x*x for x in values))


def close(actual, expected, tolerance=1e-11):
    if not math.isfinite(actual) or abs(actual-expected) > tolerance*max(1., abs(expected)):
        raise ValueError(f'Arithmetic mismatch: {actual} versus {expected}')


def verify(archive=HERE/'evidence.zip'):
    started = timestamp()
    archive = Path(archive)
    if digest(archive.read_bytes()) != ARCHIVE_SHA256:
        raise ValueError('Original evidence archive SHA-256 mismatch')
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) != 36:
            raise ValueError('Unexpected or duplicate archive members')
        if sum(i.file_size for i in z.infolist()) > 20_000_000:
            raise ValueError('Unexpected archive size')
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or name.endswith('.npz'):
                raise ValueError('Unexpected archive path/type')
        ledger = json.loads(z.read('evidence-hashes.json'))['sha256']
        if set(names) != set(ledger)|{'evidence-hashes.json'}:
            raise ValueError('Archive ledger coverage mismatch')
        for name, value in ledger.items():
            if digest(z.read(name)) != value: raise ValueError('Member hash mismatch: '+name)
        manifest = json.loads(z.read('manifest.json')); summary = json.loads(z.read('summary.json'))
        instruments = json.loads(z.read('instruments.json'))
        for name in ('manifest.json', 'summary.json', 'SUMMARY.md', 'instruments.json', 'evidence-hashes.json'):
            if (HERE/name).exists() and (HERE/name).read_bytes() != z.read(name):
                raise ValueError('Readable copy differs: '+name)
        config = manifest['config']
        if manifest['commit'] != RUN_COMMIT: raise ValueError('Unexpected run commit')
        config_bytes = (ROOT/'experiments/configs/sf-dynamics/admission.json').read_bytes()
        if digest(config_bytes) != manifest['config_sha256'] or json.loads(config_bytes) != config:
            raise ValueError('Exact reviewed config differs')
        for name, expected in config['record_hashes'].items():
            if digest((SOURCE_REPORT/name).read_bytes()) != expected:
                raise ValueError('Original static record changed')
        source = json.loads((SOURCE_REPORT/'summary.json').read_text())['stages']
        if (summary['status'] != 'complete' or summary['completed_endpoints'] != 31
                or summary['expected_endpoints'] != 31 or summary['numerical_failures'] != 0
                or not instruments['passed']):
            raise ValueError('Recorded execution/instrument completeness mismatch')
        rows = {r['stage']: r for r in summary['stages']}
        if len(rows) != 31 or set(rows) != set(config['stages']) or set(rows) != set(source):
            raise ValueError('Endpoint coverage mismatch')
        inventory = {r['stage']: r for r in manifest['fields']}
        if set(inventory) != set(rows): raise ValueError('Inventory coverage mismatch')
        manifest_sha = digest(z.read('manifest.json'))
        maxima = {'published_energy_relative_error': 0., 'stress_trace_relative_error': 0.,
                  'direct_boost_relative_error': 0., 'tensor_symmetry_over_energy': 0.,
                  'mass_squared_identity_error': 0., 'curvature_difference_replay_absolute_error': 0.}
        curvatures = []; stage_metrics = []; boost_count = 0; fd_count = 0
        native_baselines = []; curvature_difference_count = 0
        for key, row in rows.items():
            original = source[key]; inv = inventory[key]
            case = json.loads(z.read('cases/'+key+'/result.json'))
            if case != row: raise ValueError('Summary/case mismatch: '+key)
            if (row['manifest_sha256'] != manifest_sha or not row['numerical_checks_passed']
                    or row['field_sha256'] != original['checkpoint_sha256']
                    or inv['status'] != 'verified' or inv['sha256'] != row['field_sha256']
                    or inv['expected_sha256'] != row['field_sha256']
                    or row['n'] != original['n'] or row['h'] != original['h'] or row['q_label'] != original['q']):
                raise ValueError('Endpoint provenance mismatch: '+key)
            g = row['integrals']; e = g['energy']; e2, e4 = g['energy_parts']; s = g['integrated_stress']
            close(e, e2+e4)
            energy_error = abs(e/original['final']['energy']-1)
            stress_trace = abs(sum(s[i][i] for i in range(3))-e4+e2)/e
            stress_norm = norm([v for line in s for v in line])/e
            close(stress_norm, g['stress_frobenius_over_energy'])
            symmetry = max(abs(s[i][j]-s[j][i]) for i in range(3) for j in range(3))/e
            direct = g['direct_boost_beta06_axis0']; gamma = 1.25; beta = .6
            pe = gamma*(e+beta*beta*s[0][0]); pp = [beta*s[0][j] for j in range(3)]
            pp[0] = gamma*beta*(e+s[0][0])
            direct_error = max(abs(pe-direct['energy']), norm([a-b for a,b in zip(pp, direct['momentum'])]))/e
            if energy_error >= 1e-9 or stress_trace >= 1e-10 or direct_error >= 1e-10:
                raise ValueError('Original numerical consistency gate failed')
            if (g['kinetic_tangent_min'] < 1-1e-10 or g['max_local_kinetic_condition'] < 1
                    or g['minimum_corner_cone'] <= 0 or not 0 <= g['outer_20_percent_energy_fraction'] <= 1):
                raise ValueError('Recorded metric/interpolation data invalid')
            for name, value in [('published_energy_relative_error', energy_error),
                                ('stress_trace_relative_error', stress_trace),
                                ('direct_boost_relative_error', direct_error),
                                ('tensor_symmetry_over_energy', symmetry)]:
                maxima[name] = max(maxima[name], value)
            close(row['numerical_checks']['published_energy_relative_error'], energy_error)
            close(row['numerical_checks']['trace_identity_relative_error'], stress_trace)
            close(row['numerical_checks']['direct_vs_tensor_boost_relative_error'], direct_error)
            if len(row['boosts']) != 18: raise ValueError('Boost coverage mismatch')
            pairs = set()
            for b in row['boosts']:
                a = b['axis']; beta = b['beta']; pairs.add((a,beta))
                gamma = 1/math.sqrt(1-beta*beta); pe = gamma*(e+beta*beta*s[a][a])
                pp = [beta*s[a][j] for j in range(3)]; pp[a] = gamma*beta*(e+s[a][a])
                close(b['gamma'], gamma); close(b['energy'], pe)
                for actual, expected in zip(b['momentum'], pp): close(actual, expected)
                close(b['energy_particle_relative_defect'], beta*beta*s[a][a]/e)
                ideal_p = [gamma*beta*e if j == a else 0 for j in range(3)]
                close(b['momentum_particle_scaled_defect'], norm([x-y for x,y in zip(pp,ideal_p)])/(gamma*e))
                # Independent cancellation formula: no term linear in integrated stress.
                mass2 = 1-beta*beta*sum(x*x for x in s[a])/e**2
                err = abs(b['mass_squared_over_rest_energy_squared']-mass2)
                maxima['mass_squared_identity_error'] = max(maxima['mass_squared_identity_error'],err)
                close(b['mass_squared_over_rest_energy_squared'], mass2)
                close(b['max_lab_parallel_spacing_for_same_rest_resolution'], row['h']/gamma)
                boost_count += 1
            if pairs != {(a,b) for a in range(3) for b in config['speeds']}:
                raise ValueError('Boost speed/axis mismatch')
            probes = row['curvature_probes']
            if len(probes) != (4 if key in config['curvature_stages'] else 0):
                raise ValueError('Curvature endpoint coverage mismatch')
            inferred_baselines = []
            for p in probes:
                variations = p['variations']; values = []
                if len(variations) != 3 or p['kinetic_norm'] <= 0: raise ValueError('Curvature probe data invalid')
                for index, (v, eps) in enumerate(zip(variations,config['curvature_epsilons'])):
                    close(v['epsilon'],eps)
                    # Native central E0 was not archived. Check base-free direction differences,
                    # not a fictitious absolute replay using a different summation backend.
                    reference = probes[0]['variations'][index]
                    delta = ((v['energy_plus']+v['energy_minus'])
                             -(reference['energy_plus']+reference['energy_minus']))/eps**2
                    err = abs(delta-v['second_variation']+reference['second_variation'])
                    if err > max(32*math.ulp(e)/eps**2,1e-8):
                        raise ValueError('Base-free curvature difference mismatch')
                    if p['direction'] != 0: curvature_difference_count += 1
                    maxima['curvature_difference_replay_absolute_error'] = max(
                        maxima['curvature_difference_replay_absolute_error'],err)
                    inferred_baselines.append((v['energy_plus']+v['energy_minus']-v['second_variation']*eps**2)/2)
                    close(v['rayleigh_frequency_squared'],v['second_variation']/p['kinetic_norm'])
                    values.append(v['second_variation']); fd_count += 1
                curvatures.append({'stage':key,'direction':p['direction'], 'first_variation':p['first_variation'],
                                   'second_variations':values,'finest_epsilon_curvature':values[-1],
                                   'rayleigh_frequency_squared':variations[-1]['rayleigh_frequency_squared'],
                                   'relative_epsilon_spread':(max(values)-min(values))/max(abs(x) for x in values)})
            if inferred_baselines:
                if max(inferred_baselines)-min(inferred_baselines) > 8*math.ulp(e):
                    raise ValueError('Native baseline is not common across probes/amplitudes')
                base = sum(inferred_baselines)/len(inferred_baselines)
                native_baselines.append({'stage':key,'inferred_native_baseline':base,
                    'native_baseline_spread':max(inferred_baselines)-min(inferred_baselines),
                    'difference_from_original_energy':base-original['final']['energy'],
                    'scope':'Inferred from recorded second variations, not an independent E0 calculation.'})
            stage_metrics.append({'stage':key,'n':row['n'],'h':row['h'],'energy':e,
                'stress_over_energy':stress_norm,'outer_energy_fraction':g['outer_20_percent_energy_fraction'],
                'max_beta09_energy_defect':max(abs(b['energy_particle_relative_defect']) for b in row['boosts'] if b['beta']==.9),
                'max_beta09_momentum_scaled_defect':max(b['momentum_particle_scaled_defect'] for b in row['boosts'] if b['beta']==.9),
                'kinetic_condition':g['max_local_kinetic_condition'],'rms_radius':g['rms_radius']})
        if len(curvatures) != 24 or fd_count != 72: raise ValueError('Probe counts differ')
        metrics = {r['stage']:r for r in stage_metrics}; domains = []
        for branch in ('q17-neighbour','q18-baseline','q18-scale35','q18-scale45','q18-ell025','q19-neighbour'):
            small = metrics[branch+'-161']; large = metrics[branch+'-domain']
            close(small['h'],.096);close(large['h'],.096)
            domains.append({'branch':branch,'spacing':.096,'small_side':15.36,'large_side':18.432,
                'small_stress_over_energy':small['stress_over_energy'],'large_stress_over_energy':large['stress_over_energy'],
                'stress_relative_reduction':1-large['stress_over_energy']/small['stress_over_energy'],
                'energy_relative_change':abs(large['energy']/small['energy']-1),
                'small_tail_fraction':small['outer_energy_fraction'],'large_tail_fraction':large['outer_energy_fraction']})
        start = datetime.fromisoformat(manifest['started_at']['utc'])
        finish = datetime.fromisoformat(summary['recorded_at']['utc'])
        return {'assessed_at':timestamp(),'verification_started_at':started,'archive_sha256':ARCHIVE_SHA256,
                'archive_members':36,'hashed_members':35,'run_commit':RUN_COMMIT,'expected_run_tree':RUN_TREE,
                'source_tree_verification':'Reconstructed from the exact saved handoff; UPDATE.sh compares the workstation run commit tree before applying.',
                'endpoint_count':31,'boost_rows_replayed':boost_count,'curvature_directions':24,
                'curvature_amplitude_records_checked':fd_count,'base_free_curvature_differences_replayed':curvature_difference_count,
                'native_baseline_consistency':native_baselines,
                'positive_trial_directions':sum(min(x['second_variations'])>0 for x in curvatures),
                'maximum_curvature_epsilon_relative_spread':max(x['relative_epsilon_spread'] for x in curvatures),
                'numerical_maxima':maxima,'metrics':stage_metrics,'matched_domain_comparisons':domains,'curvature_probes':curvatures,
                'kinetic_range':{'minimum_tangent_eigenvalue':min(r['integrals']['kinetic_tangent_min'] for r in rows.values()),
                                 'maximum_tangent_eigenvalue':max(r['integrals']['kinetic_tangent_max'] for r in rows.values()),
                                 'maximum_local_condition':max(r['integrals']['max_local_kinetic_condition'] for r in rows.values())},
                'runtime':{'started_at':manifest['started_at'],'finished_at':summary['recorded_at'],
                           'wall_seconds':(finish-start).total_seconds(),'endpoint_seconds_sum':sum(r['wall_seconds'] for r in rows.values())},
                'disposition':'numerical_admission_consistent; significant_finite_domain_sensitivity; physical_time_evolution_pending',
                'limits':['Bulk fields absent: field integrals, metric extrema, centroids and tails authenticated as records, not recomputed.',
                          'Native C curvature E0 omitted: base-free direction differences and quotient arithmetic replayed; no independent absolute second-variation replay or field perturbation rerun.',
                          'Boost curves are kinematic identities on contracted boxes, not evolved trajectories.',
                          'Four positive trial directions per selected endpoint do not establish full stability.',
                          'No electric charge, spin/statistics, electron-model acceptance or publication priority established.']}


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path)
    args = p.parse_args();result = verify()
    if args.output: args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('assessed_at','archive_members','hashed_members','endpoint_count',
        'boost_rows_replayed','curvature_directions','positive_trial_directions','disposition')},indent=2))


if __name__ == '__main__': main()
