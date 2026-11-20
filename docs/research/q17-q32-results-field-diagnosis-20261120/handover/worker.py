"""Supervised, restartable read-only retained-field diagnosis."""
import argparse
import csv
import fcntl
import gc
import hashlib
import html
import json
import os
from pathlib import Path
import signal
import sys
import threading
import traceback
import zipfile
import numpy as np
from common import ROOT, canonical, load, log, need, save, sha, stamp, verify_manifest
from integrity import baseline, check_file, completed, field_path, host, original, process_identity, verify_sources
from reconcile import collect_prior_records, history_analysis, reconcile

STOP = threading.Event()

def profile_svg(path, rows, title):
    x = np.array([r['nearest_face_distance'] for r in rows])
    maximum = max(float(np.max(x)), 1e-30)
    series = [('force_squared_fraction', '#2563eb', 'Force squared'), ('acceleration_squared_fraction', '#dc2626', 'Acceleration squared'),
              ('registered_energy_fraction', '#059669', 'Registered energy'), ('hamiltonian_energy_fraction_diagnostic', '#7c3aed', 'D4 Hamiltonian energy')]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="320" viewBox="0 0 1000 320"><rect width="100%" height="100%" fill="white"/>',
           '<style>text{font:13px Arial;fill:#172033}</style>', f'<text x="40" y="25">{html.escape(title)} — cumulative fractions from boundary inward</text>',
           '<path d="M70 55V255H950" fill="none" stroke="#334155"/>']
    for value in [0., .5, 1.]:
        y = 255 - 200 * value
        svg.append(f'<path d="M70 {y}H950" stroke="#dbe2ea"/><text x="35" y="{y+5}">{value:g}</text>')
    for value, label in [(2., 'tail 2'), (3., 'guard 3')]:
        xp = 70 + 880 * value / maximum
        svg.append(f'<path d="M{xp} 55V255" stroke="#64748b" stroke-dasharray="3 4"/><text x="{xp+3}" y="75">{label}</text>')
    for index, (key, color, label) in enumerate(series):
        ys = np.cumsum([r[key] or 0 for r in rows])
        points = ' '.join(f'{70+880*xx/maximum:.2f},{255-200*yy:.2f}' for xx, yy in zip(x, ys))
        svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/><text x="{70+index*220}" y="290" fill="{color}">{label}</text>')
    svg += [f'<text x="360" y="315">Nearest-face distance, 0 to {maximum:g} model units; every grid layer measured</text>', '</svg>']
    Path(path).write_text('\n'.join(svg) + '\n')

def case_paths(out, spec):
    return out / 'cases' / spec['id']

def run_case(repo, out, spec, gates):
    from electron_field_topology.sf_time import Grid
    from diagnostics import analyse
    folder = case_paths(out, spec)
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'DONE.json').exists():
        receipt = load(folder / 'DONE.json')
        need(receipt['source_sha256'] == spec['sha256'], 'Cached case source differs')
        for name, digest in receipt['files'].items():
            need(sha(folder / name) == digest, 'Cached diagnostic output differs: ' + name)
        return load(folder / 'record.json')
    path = field_path(repo, spec)
    check_file(path, spec['sha256'])
    need(host()['available_gib'] >= 6, 'Host reserve reached before field diagnosis; pause and close unrelated applications')
    with np.load(path, allow_pickle=False) as z:
        n = z[spec['key']].copy()
        need(n.dtype == np.float64, 'Retained field must be float64')
        if 'expected_q' in z:
            need(int(z['expected_q']) == spec['q'], 'Retained Q label differs')
    n.setflags(write=False)
    grid = Grid((spec['nodes'],) * 3, (spec['length'],) * 3, 'fixed')
    result = analyse(n, grid, spec, gates, folder)
    del n
    gc.collect()
    need(sha(path) == spec['sha256'], 'Source field changed during diagnosis')
    for source_name in ['shell-profiles', 'radial-profiles']:
        rows = load(folder / (source_name + '.json'))
        with (folder / (source_name + '.csv')).open('w', newline='') as stream:
            w = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            w.writeheader()
            w.writerows(rows)
    profile_svg(folder / 'shell-cumulative.svg', load(folder / 'shell-profiles.json'), spec['id'])
    outputs = {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name not in ('DONE.json', 'ERROR.json') and not p.name.endswith('.tmp')}
    save(folder / 'DONE.json', {'recorded_at': stamp(), 'source_sha256': spec['sha256'], 'files': outputs, 'optimizer_steps': 0, 'physical_time_steps': 0})
    return result

def completed_cases(out, plan):
    return {spec['id']: load(case_paths(out, spec) / 'record.json') for spec in plan['fields'] if (case_paths(out, spec) / 'DONE.json').exists()}

def seal(out):
    allowed = {'.json', '.csv', '.md', '.html', '.py', '.sh', '.png', '.svg', '.zip', '.txt'}
    excluded = {'evidence.zip', 'heartbeat.json', 'telemetry-latest.json', 'supervisor.json', 'worker-launch.json', 'status.json', 'STOP.json'}
    payload = {}
    for path in sorted(out.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.name in excluded:
            continue
        if path.suffix in allowed or path.name in ('SHA256SUMS', 'COLLECTED-SHA256SUMS'):
            if path == out / 'SHA256SUMS':
                continue
            payload[path.relative_to(out).as_posix()] = path.read_bytes()
    text = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n' for name, data in sorted(payload.items()))
    (out / 'SHA256SUMS').write_text(text)
    tmp = out / 'evidence.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(payload.items()):
            z.writestr(name, data)
        z.writestr('SHA256SUMS', text)
    with zipfile.ZipFile(tmp) as z:
        need(z.testzip() is None, 'Diagnostic compact evidence CRC failed')
    tmp.replace(out / 'evidence.zip')

def report(out, record):
    rows, sections = [], []
    for case in record['cases'].values():
        m = case['reference_metrics']
        rows.append('<tr>' + ''.join('<td>' + html.escape(str(value)) + '</td>' for value in [case['id'], m['relative_force_l2'], m['acceleration_max'], m['tail_fraction'], m['guard_fraction'], case['strict_stationary'], case['boundary_admitted']]) + '</tr>')
        folder = 'cases/' + case['id'] + '/'
        peak = case['acceleration_peaks'][0]
        sections.append('<details><summary>' + html.escape(case['id']) + '</summary><p>Maximum acceleration location: ' + html.escape(str(peak['coordinates'])) + '; nearest face distance: ' + str(peak['nearest_face_distance']) + ' model units.</p>' +
                        '<p><a href="' + folder + 'record.json">Full spatial metrics</a> · <a href="' + folder + 'shell-profiles.csv">Every cube-shell layer</a> · <a href="' + folder + 'radial-profiles.csv">Radial profiles</a></p>' +
                        '<img src="' + folder + 'shell-cumulative.svg" alt="Cumulative shell profiles"/><img src="' + folder + 'central-slices.svg" alt="Central static diagnostic slices"/><img src="' + folder + 'acceleration-peak-slices.svg" alt="Planes through acceleration hotspot"/></details>')
    reconciliation = record['reconciliation']
    claim_rows = ''.join('<tr><td>' + html.escape(c['comparison']) + '</td><td>' + html.escape(c['status']) + '</td><td>' + html.escape(c['reason']) + '</td></tr>' for c in reconciliation['claims'])
    intro = 'This read-only diagnosis evaluates five authenticated retained fields: Q2 control, Q21 parent/endpoint and Q22 parent/endpoint. It takes zero optimizer steps and zero physical-time steps, preserves all gates, and does not normalize, resample or enlarge input fields. Static acceleration is an instantaneous operator evaluation, not a motion simulation.'
    interpretation = 'The same Q2 positive result must reproduce before candidate diagnosis proceeds. Different operators, fields, grids and metric definitions are compared explicitly. A prior positive result is not withdrawn merely because another configuration fails. Tail/guard admission continues to use the registered continuum energy density; D4 Hamiltonian-density tails are separate diagnostics. Localization and normalization changes are measured associations, not proof of boundary causation.'
    text = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Q21/Q22 field diagnosis and prior-result reconciliation</title><style>body{font:15px/1.5 system-ui;max-width:1400px;margin:30px auto;padding:0 20px}table{border-collapse:collapse;width:100%}th,td{padding:8px;border-bottom:1px solid #ddd;text-align:left}img{max-width:100%}pre{white-space:pre-wrap}details{margin:20px 0}</style><h1>Retained-field diagnosis and reconciliation</h1><p>' + html.escape(record['status']) + '</p><p>' + intro + '</p><p>' + interpretation + '</p><p><a href="record.json">Full diagnosis record</a> · <a href="RECONCILIATION.json">Claim comparison</a> · <a href="OPTIMIZER-HISTORY.json">Optimizer history</a> · <a href="PRIOR-RECORDS.json">Pinned prior documents</a> · <a href="handover/assessment/ASSESSMENT.html">Completed-run assessment</a></p>'
    text += '<h2>Measured same-field replay</h2><table><tr><th>Field</th><th>Force ratio</th><th>Acceleration max</th><th>Tail</th><th>Guard</th><th>Stationary</th><th>Boundary</th></tr>' + ''.join(rows) + '</table>'
    text += '<h2>Why earlier results can differ</h2><table><tr><th>Comparison</th><th>Disposition</th><th>Reason</th></tr>' + claim_rows + '</table><p>' + html.escape(reconciliation['unresolved']) + '</p>'
    text += '<h2>Parent-to-endpoint force normalization</h2><pre>' + html.escape(json.dumps(reconciliation['parent_endpoint_comparisons'], indent=2)) + '</pre><h2>Spatial evidence</h2>' + ''.join(sections)
    text += '<h2>Next decision</h2><p>Inspect whether force-squared mass and the acceleration maximum lie inside the guard region or in the interior. A larger-domain test is justified only by a stated boundary hypothesis; an optimizer-memory comparison is a separate question. This diagnosis starts neither test. An unexplained same-field replay mismatch blocks further candidate work and is reported as a failure.</p><h2>Errors</h2><pre>' + html.escape(str(record.get('error'))) + '</pre></html>\n'
    (out / 'REPORT.html').write_text(text)
    (out / 'SUMMARY.md').write_text('# Retained-field diagnosis\n\n' + json.dumps(stamp()) + '\n\nStatus: **' + record['status'] + '**. Completed static field diagnoses: ' + str(len(record['cases'])) + ' / 5.\n\nOptimizer steps: 0. Physical-time steps: 0. Original fields, gates and source checkout are unchanged. Read REPORT.html for localization, normalization and prior-claim comparisons.\n')

def execute(repo, out):
    identity = load(out / 'identity.json')
    need(identity['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Frozen diagnostic package identity differs')
    verify_manifest(ROOT)
    source_identity = verify_sources(repo)
    need(source_identity == identity['source_identity'], 'Numerical source identity differs')
    sys.path.insert(0, str(repo / 'src'))
    plan = load(ROOT / 'PLAN.json')
    phase = {'name': 'prior-record-collection', 'field': None}
    done = threading.Event()
    record = {'recorded_at': stamp(), 'identity': identity, 'plan': plan, 'status': 'working', 'cases': {},
              'completed_source_run': plan['source_run_id'], 'completed_continuation_attempts': 225, 'optimizer_steps': 0, 'physical_time_steps': 0,
              'deferred': ['Additional relaxation', 'Larger-domain run', 'Optimizer-memory intervention', 'Mesh confirmation', 'Motion simulation'], 'error': None}
    def heartbeat():
        while not done.is_set():
            save(out / 'heartbeat.json', {'recorded_at': stamp(), 'pid': os.getpid(), 'process_identity': process_identity(os.getpid()), 'operation': dict(phase)})
            done.wait(15)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    def update(final=False):
        record['cases'] = completed_cases(out, plan)
        record['reconciliation'] = reconcile(record['cases'])
        save(out / 'RECONCILIATION.json', record['reconciliation'])
        save(out / 'record.json', record)
        save(out / 'status.json', {'recorded_at': stamp(), 'status': record['status'], 'phase': dict(phase), 'completed_fields': len(record['cases']), 'declared_fields': 5,
                                   'optimizer_steps': 0, 'physical_time_steps': 0, 'error': record['error']})
        report(out, record)
        if final:
            seal(out)
    try:
        collect_prior_records(repo, out)
        save(out / 'OPTIMIZER-HISTORY.json', history_analysis())
        save(out / 'RETENTION.json', {'recorded_at': stamp(), 'original_continuation_full_fields': baseline()[0]['field-manifest.json'],
                                     'preflight_receipt': load(out / 'PREFLIGHT.json'), 'remote_full_field_archive_claimed': False,
                                     'scope': '37 retained full-field hashes/CRCs checked locally: all 36 continuation NPZs and Q2 control. Diagnosis never writes to these fields.'})
        update()
        for spec in plan['fields']:
            if STOP.is_set() or (out / 'STOP.json').exists():
                raise KeyboardInterrupt('Orderly pause between static field diagnoses')
            phase.update(name='static-metric-replay-and-spatial-diagnosis', field=spec['id'], nodes=spec['nodes'])
            update()
            log('Starting retained static field diagnosis', field=spec['id'], nodes=spec['nodes'], optimizer_steps=0, physical_time_steps=0)
            run_case(repo, out, spec, plan['registered_gates'])
            log('Completed retained static field diagnosis', field=spec['id'])
            update()
        record.update(status='complete_pending_review', finished_at=stamp())
        phase.update(name='complete', field=None)
        update(True)
        log('Retained-field diagnosis complete', output=str(out), evidence=str(out / 'evidence.zip'), completed_fields=5)
    except BaseException as error:
        resource = isinstance(error, RuntimeError) and 'reserve reached' in str(error).lower()
        record.update(status='interrupted' if isinstance(error, KeyboardInterrupt) or resource else 'failed', error=str(error))
        if phase.get('field'):
            save(out / 'cases' / phase['field'] / 'ERROR.json', {'recorded_at': stamp(), 'error': str(error), 'input_modified': False})
        update(True)
        if record['status'] == 'failed':
            traceback.print_exc()
            raise
    finally:
        done.set()
        thread.join(timeout=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    with (original(args.repo) / '.worker.lock').open('r') as old_lock, (completed(args.repo) / '.worker.lock').open('r') as result_lock, (args.output / '.worker.lock').open('a') as lock:
        for handle in [old_lock, result_lock, lock]:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        execute(args.repo.resolve(), args.output.resolve())

if __name__ == '__main__':
    main()
