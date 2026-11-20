"""Independent compact integrity, scalar identities, partitions and gate audit."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import zipfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = 'c2d762d46422ae6c27647feb46dd76d4df7a98c3ccf1bfad1714cfe381b87bc7'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def stamp():
    t = datetime.now(timezone.utc)
    return {'utc': t.isoformat(), 'melbourne': t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}

def checked(z):
    names = z.namelist()
    assert len(names) == len(set(names)) and z.testzip() is None
    hashes = {}
    for row in z.read('SHA256SUMS').decode().splitlines():
        sha, name = row.split('  ', 1)
        p = PurePosixPath(name)
        assert not p.is_absolute() and '..' not in p.parts and name not in hashes
        assert digest(z.read(name)) == sha, name
        hashes[name] = sha
    assert set(hashes) == set(names) - {'SHA256SUMS'}
    return hashes

def run():
    path = ROOT / 'data/diagnostic-evidence.zip'
    assert digest(path.read_bytes()) == SOURCE_SHA
    case_checks, endpoint_rows = [], []
    with zipfile.ZipFile(path) as z:
        hashes = checked(z)
        record = json.loads(z.read('record.json'))
        plan = record['plan']
        gates = plan['registered_gates']
        identity = record['identity']
        assert record['status'] == 'complete_pending_review' and len(record['cases']) == 5
        assert record['optimizer_steps'] == record['physical_time_steps'] == 0
        manifest = z.read('handover/SHA256SUMS')
        assert digest(manifest) == identity['package_sha256']
        delivered_files = {}
        for row in manifest.decode().splitlines():
            sha, name = row.split('  ', 1)
            assert digest(z.read('handover/' + name)) == sha
            delivered_files[name] = sha
        assert len(delivered_files) == 30
        assert digest(z.read('handover/PLAN.json')) == identity['plan_sha256']
        sources = json.loads(z.read('handover/SOURCES.json'))
        canonical = digest(json.dumps(sources, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
        assert canonical == identity['source_identity']
        preflight = json.loads(z.read('PREFLIGHT.json'))
        assert preflight['full_field_hashes_and_crcs'] == 37 and len(preflight['retained_continuation_fields']) == 36
        retained = {r['path']: r for r in preflight['retained_continuation_fields']}
        prior = json.loads(z.read('PRIOR-RECORDS.json'))
        assert not prior['missing_study_prefixes']
        for doc in prior['documents']:
            assert digest(z.read(doc['collected_path'])) == doc['sha256']
        for spec in plan['fields']:
            case = record['cases'][spec['id']]
            folder = 'cases/' + spec['id'] + '/'
            done = json.loads(z.read(folder + 'DONE.json'))
            assert done['source_sha256'] == case['source_sha256'] == spec['sha256']
            for name, sha in done['files'].items():
                assert digest(z.read(folder + name)) == sha
            assert case['field_array_sha256_before'] == case['field_array_sha256_after']
            assert case['optimizer_steps'] == case['physical_time_steps'] == 0
            if spec['kind'] != 'control':
                assert retained[spec['relative_path']]['sha256'] == spec['sha256']
            else:
                assert preflight['q2_control_hash'] == spec['sha256']
            m, f, e = case['reference_metrics'], case['force_decomposition'], case['energy_definition_check']
            for key, value in spec['expected'].items():
                if isinstance(value, (int, float)) and not isinstance(value, bool) and key in m:
                    assert math.isclose(m[key], value, rel_tol=1e-6, abs_tol=1e-10), (spec['id'], key)
            assert math.isclose(f['projected_force_numerator_l2'] / f['registered_sigma_denominator_l2'], m['relative_force_l2'], rel_tol=1e-11)
            assert math.isclose(e['d4_hamiltonian_energy'], m['energy'], rel_tol=1e-12)
            count = math.prod(case['shape'])
            for filename in ['shell-profiles.json', 'radial-profiles.json']:
                rows = json.loads(z.read(folder + filename))
                assert sum(row['nodes'] for row in rows) == count
                for key in ['volume_fraction', 'force_squared_fraction', 'acceleration_squared_fraction', 'registered_energy_fraction', 'hamiltonian_energy_fraction_diagnostic']:
                    assert math.isclose(sum(row[key] for row in rows), 1., abs_tol=2e-12)
                assert math.isclose(sum(row['force_l2'] ** 2 for row in rows), f['projected_force_numerator_l2'] ** 2, rel_tol=1e-11)
                assert math.isclose(sum(row['acceleration_l2'] ** 2 for row in rows), 3 * count * m['acceleration_rms'] ** 2, rel_tol=1e-11)
                assert math.isclose(max(row['acceleration_max'] for row in rows), m['acceleration_max'], rel_tol=1e-12)
            strict = m['relative_force_l2'] <= gates['force_limit'] and m['acceleration_max'] <= gates['acceleration_limit'] and abs(abs(m['hopf_integral']) - case['q']) / case['q'] <= gates['charge_relative_error'] and m['minimum_corner_cone'] > 0 and m['unit_error'] < gates['unit_limit']
            boundary = m['tail_fraction'] <= gates['initial_tail_limit'] and m['guard_fraction'] <= gates['tail_guard_limit']
            alternate = e['hamiltonian_tail_fraction_diagnostic'] <= gates['initial_tail_limit'] and e['hamiltonian_guard_fraction_diagnostic'] <= gates['tail_guard_limit']
            assert strict == case['strict_stationary'] and boundary == case['boundary_admitted']
            assert alternate == boundary  # Density choice changes no tested pass/fail.
            if spec['kind'] == 'control':
                assert strict and boundary
            case_checks.append({'id': spec['id'], 'source_receipts_and_scalar_replay_match': True, 'complete_profile_partitions_pass': True,
                                'force_and_energy_identities_pass': True, 'gate_reconstruction_pass': True, 'boundary_outcome_same_for_two_densities': True})
            if spec['kind'] == 'endpoint':
                guard = case['regions']['registered_guard']
                interior = case['regions']['interior_outside_guard']
                endpoint_rows.append({'id': spec['id'], 'force_gate_multiple': m['relative_force_l2'] / gates['force_limit'],
                                      'acceleration_gate_multiple': m['acceleration_max'] / gates['acceleration_limit'],
                                      'guard_force_squared_ppm': guard['force_squared_fraction'] * 1e6,
                                      'guard_acceleration_squared_ppm': guard['acceleration_squared_fraction'] * 1e6,
                                      'interior_force_squared_percent': interior['force_squared_fraction'] * 100,
                                      'interior_acceleration_squared_percent': interior['acceleration_squared_fraction'] * 100,
                                      'guard_peak_acceleration_gate_multiple': guard['acceleration_max'] / gates['acceleration_limit'],
                                      'force_peak_distance_from_face': case['force_peaks'][0]['nearest_face_distance'],
                                      'acceleration_peak_distance_from_face': case['acceleration_peaks'][0]['nearest_face_distance'],
                                      'registered_tail_gate_multiple': m['tail_fraction'] / gates['initial_tail_limit'],
                                      'registered_guard_gate_multiple': m['guard_fraction'] / gates['tail_guard_limit']})
        comparisons = []
        for seed in ['q21-axial-7-3', 'q22-cable-source-family']:
            first = record['cases'][seed + '-parent']['force_decomposition']
            last = record['cases'][seed + '-endpoint']['force_decomposition']
            numerator = last['projected_force_numerator_l2'] / first['projected_force_numerator_l2']
            denominator = last['registered_sigma_denominator_l2'] / first['registered_sigma_denominator_l2']
            comparisons.append({'seed': seed, 'numerator_change_percent': 100 * (numerator - 1), 'denominator_change_percent': 100 * (denominator - 1),
                                'registered_force_ratio_change_percent': 100 * (numerator / denominator - 1)})
    return {'recorded_at': stamp(), 'source_sha256': SOURCE_SHA, 'zip_crc_pass': True, 'compact_payload_hashes_verified': len(hashes),
            'executed_handover_payloads_verified': len(delivered_files), 'prior_documents_verified': len(prior['documents']),
            'cases_checked': case_checks, 'workstation_full_field_hash_crc_receipt': 37, 'workstation_source_fields_independently_reread_here': False,
            'new_optimizer_steps_here': 0, 'new_physical_time_steps_here': 0, 'endpoint_summary': endpoint_rows,
            'normalization_changes': comparisons, 'scope': 'Independent audit of compact receipts, partitions, scalar algebra and gates; not a new full-field replay'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['recorded_at', 'compact_payload_hashes_verified', 'executed_handover_payloads_verified', 'prior_documents_verified', 'new_optimizer_steps_here']}))
