"""Checkpointed workstation admission for future neutral SF dynamics. Apache-2.0."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import time
import zipfile
import numpy as np
from .sf_checkpoints import atomic_json, timestamp
from .sf_dynamics import (boost_integrals, cell_integrals, perturbation, sphere_step,
                          currents, lagrangian, stress_energy, boost_jet)
from .skyrme import K, NORTH, Energy, numpy_cell_energy, rational_field, coordinates, set_boundary

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/'reports/q18-neighbours/q18-neighbours-20261102T022100+1100-165739'
CONFIG = ROOT/'experiments/configs/sf-dynamics/admission.json'
SCOPE = ('Neutral static-field dynamics admission only; no physical-time evolution, '
         'full stability proof, electric charge or electron-model acceptance.')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''): digest.update(chunk)
    return digest.hexdigest()


def event(message, **values):
    print(json.dumps({'recorded_at': timestamp(), 'message': message, **values}), flush=True)


def published(config):
    """Authenticate immutable committed raw records before resolving local paths."""
    for name, digest in config['record_hashes'].items():
        if sha(REPORT/name) != digest:
            raise ValueError('Published record changed: '+name)
    summary = read(REPORT/'summary.json'); campaign = read(REPORT/'campaign.json')
    if campaign['git_commit'] != config['run_commit']:
        raise ValueError('Original run commit mismatch')
    selected = config['stages']
    if len(set(selected)) != len(selected) or set(selected) != set(summary['stages']):
        raise ValueError('All 31 published endpoints must be accounted for')
    return {key: {'stage': key, **summary['stages'][key],
                  'directory': campaign['stages'][key]['directory'],
                  'config_sha256': campaign['stages'][key]['config_sha256']}
            for key in selected}


def inventory(source, config):
    source = Path(source).resolve(); rows = []
    for key, row in published(config).items():
        path = source/row['directory']/'final.npz'
        item = {'stage': key, 'path': str(path), 'expected_sha256': row['checkpoint_sha256']}
        if not path.is_file(): item['status'] = 'missing'
        else:
            item['sha256'] = sha(path)
            item['status'] = 'verified' if item['sha256'] == item['expected_sha256'] else 'hash_mismatch'
        rows.append(item)
    return {'recorded_at': timestamp(), 'source_campaign': str(source), 'fields': rows,
            'scope': 'Read-only inventory; missing or modified fields are never reconstructed.'}


def verify_instruments():
    """Deterministic independent action, covariance and static-cell controls."""
    start = timestamp(); rng = np.random.default_rng(51102)
    n = np.array([0., 0., 1.]); d = rng.normal(size=(20, 3, 3)); d[..., 2] = 0
    v = rng.normal(size=(20, 3)); v[..., 2] = 0
    p, q = currents(d, v); eps = 1e-6; fd = 0.
    for i in range(3):
        dv = np.zeros_like(v); dv[..., i] = eps
        fd = max(fd, float(np.max(abs((lagrangian(d, v+dv)-lagrangian(d, v-dv))/(2*eps)-p[..., i]))))
        for j in range(3):
            dd = np.zeros_like(d); dd[..., i, j] = eps
            fd = max(fd, float(np.max(abs((lagrangian(d+dd, v)-lagrangian(d-dd, v))/(2*eps)-q[..., i, j]))))
    # Independent metric contraction of spacetime two-form H, including generic time jets.
    jets = np.concatenate((v[:, None], d), axis=1); metric = np.array([1., -1., -1., -1.])
    form = np.einsum('a,...mna->...mn', n, np.cross(jets[..., :, None, :], jets[..., None, :, :]))
    contraction = np.einsum('m,n,...mn,...mn->...', metric, metric, form, form)
    scalar = np.sum(jets*jets*metric[None, :, None], axis=(-2, -1))-.5*contraction
    metric_error = float(np.max(abs(scalar-lagrangian(d, v))))
    rest = stress_energy(d, np.zeros_like(v)); covariance = 0.; symmetry = 0.
    for axis in range(3):
        for beta in (-.9, -.3, 0., .3, .9):
            bd, bv = boost_jet(d, beta, axis); actual = stress_energy(bd, bv)
            gamma = 1/np.sqrt(1-beta*beta); matrix = np.eye(4)
            matrix[0, 0] = matrix[axis+1, axis+1] = gamma
            matrix[0, axis+1] = matrix[axis+1, 0] = gamma*beta
            expected = np.einsum('im,...mn,jn->...ij', matrix, rest, matrix)
            covariance = max(covariance, float(np.max(abs(actual-expected))/np.max(abs(expected))))
            symmetry = max(symmetry, float(np.max(abs(actual-np.swapaxes(actual, -1, -2)))))
    xyz = coordinates(9, .6)
    angle = .3*np.exp(-np.sum(xyz*xyz, axis=-1))
    u = set_boundary(np.stack((np.sin(angle), np.zeros_like(angle), np.cos(angle)), axis=-1))
    cells = cell_integrals(u, .6, slab=2)
    independent_energy = float(sum(numpy_cell_energy(u, .6)))
    e = cells['energy']; s = np.array(cells['integrated_stress'])
    boost = boost_integrals(e, s, [.6])[0]
    direct = cells['direct_boost_beta06_axis0']
    checks = {'action_derivative_max_absolute_error': fd, 'metric_contraction_max_absolute_error': metric_error,
              'tensor_covariance_max_relative_error': covariance, 'tensor_symmetry_max_absolute_error': symmetry,
              'independent_cell_energy_relative_error': abs(e/independent_energy-1),
              'integrated_trace_identity_relative_error': abs(cells['trace_identity_error'])/e,
              'direct_vs_tensor_boost_relative_error': max(abs(direct['energy']-boost['energy']),
                  float(np.linalg.norm(np.array(direct['momentum'])-boost['momentum'])))/e}
    passed = (fd < 2e-7 and metric_error < 2e-12 and covariance < 2e-12 and symmetry < 2e-10
              and all(checks[key] < 2e-12 for key in (
                  'independent_cell_energy_relative_error', 'integrated_trace_identity_relative_error',
                  'direct_vs_tensor_boost_relative_error')))
    return {'started_at': start, 'finished_at': timestamp(), 'passed': passed, 'checks': checks,
            'scope': 'Small deterministic instruments, not workstation-field or evolution results.'}


def audit_field(path, expected, config, build, progress=None):
    """Read-only field authentication, cell integration and selected variations."""
    path = Path(path); digest = sha(path)
    if digest != expected['checkpoint_sha256']: raise ValueError('Field SHA-256 mismatch')
    with np.load(path, allow_pickle=False) as data:
        if data['field'].dtype != np.dtype('float64'): raise ValueError('Expected original float64 field')
        u = data['field']; h = float(data['h'])
        if (str(data['model_id']) != 'SF-J2015-static'
                or int(data['expected_q']) != expected['q']
                or str(data['config_sha256']) != expected['config_sha256']):
            raise ValueError('Checkpoint model/Q/config metadata mismatch')
    if u.shape != (expected['n'],)*3+(3,) or h != expected['h']:
        raise ValueError('Checkpoint grid/spacing mismatch')
    for axis in range(3):
        sl = [slice(None)]*4; sl[axis] = [0, 1, len(u)-2, len(u)-1]
        if np.max(abs(u[tuple(sl)]-NORTH)) > 1e-12: raise ValueError('Fixed-face mismatch')
    use_curvature = expected['stage'] in config['curvature_stages']
    directions = [perturbation(u, h, k) for k in range(4)] if use_curvature else []
    integrated = cell_integrals(u, h, slab=config['slab_cells'], directions=directions, progress=progress)
    del directions
    e = integrated['energy']; reference = expected['final']['energy']
    numerical = {'published_energy_relative_error': abs(e/reference-1),
                 'trace_identity_relative_error': abs(integrated['trace_identity_error'])/e}
    s = np.array(integrated['integrated_stress'])
    boosts = boost_integrals(e, s, config['speeds'])
    for row in boosts:
        row['max_lab_parallel_spacing_for_same_rest_resolution'] = h/row['gamma']
    target = next(r for r in boost_integrals(e, s, [.6]) if r['axis'] == 0)
    direct = integrated['direct_boost_beta06_axis0']
    numerical['direct_vs_tensor_boost_relative_error'] = max(abs(direct['energy']-target['energy']),
        float(np.linalg.norm(np.array(direct['momentum'])-target['momentum'])))/e
    probes = []
    if use_curvature:
        engine = Energy(len(u), h, build)
        parts, gradient = engine.evaluate(u); base = float(sum(parts))
        for k in range(4):
            w = perturbation(u, h, k); slope = float(np.sum(gradient*w)); variations = []
            for epsilon in config['curvature_epsilons']:
                values = []
                for sign in (-1, 1):
                    trial = sphere_step(u, w, sign*epsilon)
                    parts, _ = engine.evaluate(trial)
                    if engine.minimum_corner_cone <= 0: raise ValueError('Perturbed field lost cell resolution')
                    values.append(float(sum(parts)))
                second = (sum(values)-2*base)/epsilon**2
                metric_norm = integrated['direction_kinetic_norms'][k]
                variations.append({'epsilon': epsilon, 'energy_minus': values[0], 'energy_plus': values[1],
                                   'second_variation': second,
                                   'rayleigh_frequency_squared': second/metric_norm if metric_norm > 0 else None})
            probes.append({'direction': k, 'first_variation': slope,
                           'kinetic_norm': integrated['direction_kinetic_norms'][k], 'variations': variations,
                           'scope': 'Four trial directions only; not a Hessian eigenspectrum or stability proof.'})
            if progress: progress('curvature', k+1)
        del engine
    if sha(path) != digest: raise ValueError('Source field changed during analysis')
    passed = (numerical['published_energy_relative_error'] < 1e-9
              and numerical['trace_identity_relative_error'] < 1e-10
              and numerical['direct_vs_tensor_boost_relative_error'] < 1e-10
              and integrated['kinetic_tangent_min'] >= 1-1e-10)
    return {'field_sha256': digest, 'stage': expected['stage'], 'q_label': expected['q'],
            'n': len(u), 'h': h, 'integrals': integrated, 'boosts': boosts,
            'curvature_probes': probes, 'numerical_checks': numerical, 'numerical_checks_passed': passed,
            'admission': 'static_diagnostics_only; physical_time_solver_pending', 'scope': SCOPE}


def collect(output):
    out = Path(output); manifest = read(out/'manifest.json'); rows = []
    for item in manifest['fields']:
        path = out/'cases'/item['stage']/'result.json'
        if path.is_file():
            value = read(path)
            if (value.get('manifest_sha256') != sha(out/'manifest.json')
                    or value.get('field_sha256') != item['expected_sha256']):
                raise ValueError('Case provenance mismatch: '+item['stage'])
            rows.append(value)
        else:
            error = out/'cases'/item['stage']/'error.json'
            rows.append({'stage': item['stage'], 'status': 'failed' if error.exists() else item['status'],
                         'detail': read(error) if error.exists() else 'No finished result'})
    finished = sum('integrals' in row for row in rows)
    failed = sum(row.get('numerical_checks_passed') is False for row in rows)
    status = 'complete' if finished == len(rows) and not failed else 'partial_or_failed'
    summary = {'recorded_at': timestamp(), 'status': status, 'completed_endpoints': finished,
               'expected_endpoints': len(rows), 'numerical_failures': failed, 'stages': rows,
               'scope': SCOPE, 'next_gate': 'Implement and independently validate physical-time evolution.'}
    atomic_json(out/'summary.json', summary)
    lines = ['# Neutral SF dynamics admission', '', json.dumps(summary['recorded_at']), '',
             f"Execution: **{status}**; {finished}/{len(rows)} endpoints; {failed} numerical-check failures.", '',
             SCOPE, '', '| Stage | E | ||integrated stress|| / E | Kinetic condition | Curvature probes |',
             '|---|---:|---:|---:|---:|']
    for row in rows:
        if 'integrals' in row:
            m = row['integrals']
            lines.append(f"| {row['stage']} | {m['energy']:.9g} | {m['stress_frobenius_over_energy']:.6g} | "
                         f"{m['max_local_kinetic_condition']:.6g} | {len(row['curvature_probes'])} |")
        else: lines.append(f"| {row['stage']} | {row['status']} | — | — | — |")
    lines += ['', 'Inspect mesh/domain trends in summary.json. Nonzero stress or negative trial curvature is retained,',
              'not suppressed. Particle-boost relations require negligible integrated stress.',
              'No passing result authorises electron or full stability claims.', '',
              'Q18 fresh fine-start/conditioning and broader Q controls remain planned separately.']
    (out/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    members = [out/'manifest.json', out/'instruments.json', out/'summary.json', out/'SUMMARY.md']
    members += sorted((out/'cases').glob('*/*.json')) if (out/'cases').exists() else []
    hashes = {str(p.relative_to(out)): sha(p) for p in members}
    atomic_json(out/'evidence-hashes.json', {'recorded_at': timestamp(), 'sha256': hashes})
    with zipfile.ZipFile(out/'evidence.zip.tmp', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in members+[out/'evidence-hashes.json']:
            archive.write(path, str(path.relative_to(out)))
    os.replace(out/'evidence.zip.tmp', out/'evidence.zip')
    atomic_json(out/'RUN_COMPLETE.json', {'recorded_at': timestamp(), 'status': status,
                'completed_endpoints': finished, 'expected_endpoints': len(rows),
                'evidence_sha256': sha(out/'evidence.zip'), 'scope': SCOPE})
    event('SUMMARY', status=status, completed=finished, expected=len(rows), path=str(out/'SUMMARY.md'))
    return summary


def run(source, output):
    out = Path(output).resolve(); out.mkdir(parents=True, exist_ok=True)
    config = read(CONFIG); fields = inventory(source, config)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise ValueError('Commit the prepared tooling before running; source must be clean')
    if (out/'manifest.json').exists():
        manifest = read(out/'manifest.json')
        if (manifest['commit'] != commit or manifest['config_sha256'] != sha(CONFIG)
                or manifest['source_campaign'] != str(Path(source).resolve())):
            raise ValueError('Resume source/commit/config mismatch; use original checkout')
    else:
        manifest = {'started_at': timestamp(), 'commit': commit, 'config_sha256': sha(CONFIG),
                    **fields, 'config': config, 'python': sys.version, 'platform': platform.platform(),
                    'versions': {k: importlib.metadata.version(k) for k in ('numpy', 'scipy')},
                    'scope': SCOPE}
        atomic_json(out/'manifest.json', manifest)
    instruments = verify_instruments(); atomic_json(out/'instruments.json', instruments)
    if not instruments['passed']: raise ValueError('Independent instrument checks failed')
    expected = published(config); manifest_hash = sha(out/'manifest.json')
    if (out/'RUN_COMPLETE.json').exists(): (out/'RUN_COMPLETE.json').unlink()
    try:
        for item in fields['fields']:
            stage = item['stage']; case = out/'cases'/stage; case.mkdir(parents=True, exist_ok=True)
            result_path = case/'result.json'
            if result_path.exists():
                previous = read(result_path)
                if (previous.get('manifest_sha256') != manifest_hash
                        or previous.get('field_sha256') != item['expected_sha256']):
                    raise ValueError('Finished case provenance mismatch')
                event('RETAIN verified finished endpoint', stage=stage); continue
            if item['status'] != 'verified':
                atomic_json(case/'error.json', {'recorded_at': timestamp(), **item})
                event('UNAVAILABLE endpoint', **item); continue
            event('START endpoint', stage=stage); started = timestamp(); clock = time.monotonic()
            last = [0.]
            def progress(a, b):
                if isinstance(a, str) or time.monotonic()-last[0] > 30:
                    event('WORKING '+stage, progress=[a, b]); last[0] = time.monotonic()
            try:
                result = audit_field(item['path'], expected[stage], config, out/'build', progress)
                result.update(started_at=started, finished_at=timestamp(), manifest_sha256=manifest_hash,
                              wall_seconds=time.monotonic()-clock)
                atomic_json(result_path, result)
                if (case/'error.json').exists(): (case/'error.json').unlink()
                event('FINISHED endpoint', stage=stage, numerical_checks_passed=result['numerical_checks_passed'])
            except (ValueError, OSError, KeyError) as error:
                atomic_json(case/'error.json', {'recorded_at': timestamp(), 'stage': stage,
                                              'error': str(error), 'wall_seconds': time.monotonic()-clock})
                event('FAILED endpoint', stage=stage, error=str(error))
    except KeyboardInterrupt:
        event('PAUSED; rerun to retain completed endpoints'); collect(out); return 130
    summary = collect(out)
    return 0 if summary['status'] == 'complete' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    verify = subs.add_parser('verify'); verify.add_argument('--output', type=Path)
    inv = subs.add_parser('inventory'); inv.add_argument('--source', type=Path, required=True)
    inv.add_argument('--output', type=Path, required=True)
    execute = subs.add_parser('run'); execute.add_argument('--source', type=Path, required=True)
    execute.add_argument('--output', type=Path, required=True)
    gather = subs.add_parser('collect'); gather.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        result = verify_instruments()
        if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); atomic_json(args.output, result)
        print(json.dumps(result, indent=2)); return 0 if result['passed'] else 1
    if args.command == 'inventory':
        result = inventory(args.source, read(CONFIG)); args.output.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(args.output, result)
        counts = {key: sum(r['status'] == key for r in result['fields'])
                  for key in ('verified', 'missing', 'hash_mismatch')}
        event('INVENTORY', **counts, path=str(args.output)); return 0
    if args.command == 'collect': collect(args.output); return 0
    return run(args.source, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
