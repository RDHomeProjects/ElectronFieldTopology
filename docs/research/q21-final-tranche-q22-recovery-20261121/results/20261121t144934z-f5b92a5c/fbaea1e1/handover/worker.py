"""Supervised Q22 recovery/native comparison followed by final Q21 tranche."""
import argparse
import fcntl
import gc
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
from integrity import check_file, original_run, process_identity, source_checkpoint, source_run, verify_sources
from evaluations import gate_result, metrics, q22_compare
from continuation import check_reserve, ledger_count, read_parent, run as run_continuation
from recovery import Search

STOP = threading.Event()

def backend_record(parent, original, requested, grid):
    from engine import Engine
    kind = original if requested == 'auto' else requested
    engine = Engine(kind)
    audit = engine.audit(engine.xp.asarray(parent['n']), grid)
    if kind == 'cuda':
        free, _ = engine.xp.cuda.runtime.memGetInfo()
        need(free >= 2*1024**3, 'CUDA reserve reached; choose cpu explicitly before creating a run or restore CUDA availability')
    result = {'recorded_at': stamp(), 'requested': requested, 'source_backend': original, 'selected_backend': kind, 'backend_transfer': original != kind,
              'initial_energy_gradient_audit': audit, 'cuda_identity': engine.port.identity() if kind == 'cuda' else None,
              'optimizer_memory_and_alpha_preserved': True, 'scope': 'auto retains source backend; an explicit CPU transfer is recorded, never a silent fallback or a bitwise CUDA-trajectory claim'}
    del engine
    gc.collect()
    return result

def history_plot(path, history, origin):
    rows = [row for row in history if row['iteration'] >= origin]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="460" viewBox="0 0 1100 460"><rect width="100%" height="100%" fill="white"/><style>text{font:14px Arial}</style>']
    for i, (key, gate, title) in enumerate([('relative_force_l2', .0001, 'Relative force / gate'), ('acceleration_max', .001, 'Maximum acceleration / gate')]):
        x0, y0, width, height = 70+i*540, 70, 440, 280
        maximum = max(1.2, max(row['metrics'][key]/gate for row in rows)*1.1)
        end = max(row['iteration'] for row in rows)
        points = ' '.join(f'{x0+width*(row["iteration"]-origin)/max(end-origin,1):.2f},{y0+height-height*row["metrics"][key]/gate/maximum:.2f}' for row in rows)
        yp = y0+height-height/maximum
        parts += [f'<text x="{x0}" y="30">{title}</text>', f'<path d="M{x0} {y0}V{y0+height}H{x0+width}" fill="none" stroke="#334155"/>',
                  f'<path d="M{x0} {yp}H{x0+width}" stroke="#15803d" stroke-dasharray="5 4"/>', f'<polyline points="{points}" fill="none" stroke="#2563eb" stroke-width="2"/>',
                  f'<text x="{x0}" y="380">Iteration {origin} to {end}; y range 0 to {maximum:.4g}</text>']
    parts += ['<text x="70" y="415">Every accepted step measured and retained as a full float64 optimizer checkpoint.</text><text x="70" y="442">Dashed green: admission limit 1. Optimizer iteration is not physical time; no fitted admission.</text></svg>']
    path.write_text('\n'.join(parts)+'\n')

def report(out, record):
    text = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Final Q21 tranche and native Q22 recovery</title><style>body{font:16px/1.5 system-ui;max-width:1200px;margin:30px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:100%}details{margin:20px 0}</style><h1>Q21 final bounded tranche and historical Q22 recovery</h1>'
    text += '<p>Q21 retains exact iteration-315 optimizer memory, grid, box and gates. Its new allocation is capped at 20 charged attempts. Q22 is a local inventory and same-field native cell/D4 evaluation, without relaxation, normalization or resampling. Historical positive static findings remain recorded within their original limits.</p><p><a href="handover/assessment/ASSESSMENT.html">Assessment of the completed comparison</a> · <a href="record.json">Full measured record</a> · <a href="recovery/INVENTORY.json">Q22 search coverage and deferral</a></p>'
    q21 = record.get('q21')
    if q21:
        history_plot(out/'q21-tranche.svg', q21['history'], q21['source_iteration'])
        text += '<h2>Measured Q21 progress</h2><img src="q21-tranche.svg" alt="Q21 measured force and acceleration gate ratios"/>'
        brief = {key: q21[key] for key in ['reason', 'source_iteration', 'final_iteration', 'new_attempts_charged', 'accepted_new_steps', 'final']}
        text += '<pre>'+html.escape(json.dumps(brief, indent=2))+'</pre><details><summary>Allocation decisions, fits and forecasts</summary><pre>'+html.escape(json.dumps(q21['decisions'], indent=2))+'</pre></details>'
    for key in ['status', 'q2', 'q22', 'deferred', 'error']:
        text += '<h2>'+html.escape(key)+'</h2><pre>'+html.escape(json.dumps(record.get(key), indent=2))+'</pre>'
    text += '<p>Boundary failure remains failure. A measured strict-stationarity result is not motion readiness when another gate fails. Formal curve crossings are scheduling diagnostics only. Search limits, permissions and omitted roots remain explicit; missing bytes are not a negative Q22 result.</p></html>\n'
    (out/'REPORT.html').write_text(text)
    (out/'SUMMARY.md').write_text('# Final Q21 tranche and Q22 recovery\n\n'+json.dumps(stamp())+'\n\nStatus: **'+record['status']+'**. New Q21 charged attempts: '+str(record.get('new_q21_attempts_charged',0))+' / 20. Q22 optimizer steps: 0. Physical-time steps: 0.\n\nRead REPORT.html for measured gates, adaptive decisions, recovery coverage and explicit deferrals. No further numerical campaign is launched automatically.\n')

def seal(out):
    transient = {'evidence.zip', 'SHA256SUMS', 'status.json', 'heartbeat.json', 'supervisor.json', 'worker-launch.json', 'telemetry-latest.json', 'STOP.json'}
    fields = [{'path': path.relative_to(out).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size} for path in sorted(out.rglob('*.npz'))]
    save(out/'FIELD-MANIFEST.json', {'recorded_at': stamp(), 'fields': fields, 'scope': 'Full optimizer states and recovered native Q22, if found, remain local. Compact evidence contains hashes, not array contents. Uncommitted orphan checkpoints are retained but never selected instead of the committed pointer.'})
    paths = [p for p in sorted(out.rglob('*')) if p.is_file() and p.suffix not in ['.npz', '.so', '.partial', '.tmp', '.lock'] and '__pycache__' not in p.parts and not (p.parent == out and p.name in transient)]
    sums = ''.join(sha(p)+'  '+p.relative_to(out).as_posix()+'\n' for p in paths)
    (out/'SHA256SUMS').write_text(sums)
    with zipfile.ZipFile(out/'evidence.tmp', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, p.relative_to(out).as_posix())
        z.writestr('SHA256SUMS', sums)
    with zipfile.ZipFile(out/'evidence.tmp') as z:
        need(z.testzip() is None, 'Compact evidence CRC failed')
    (out/'evidence.tmp').replace(out/'evidence.zip')

def execute(repo, out):
    from electron_field_topology.sf_time import Grid
    verify_manifest(ROOT)
    verify_sources(repo)
    plan = load(ROOT/'PLAN.json')
    identity = load(out/'identity.json')
    need(identity['package_sha256'] == sha(ROOT/'SHA256SUMS'), 'Frozen final-tranche package differs')
    phase = {'name': 'controls-and-source-replay'}
    finished = threading.Event()
    record = {'recorded_at': stamp(), 'identity': identity, 'status': 'working', 'q21': None, 'q22': None, 'deferred': plan['deferred'][:], 'error': None, 'physical_time_steps': 0, 'q22_optimizer_steps': 0}
    def heartbeat():
        while not finished.is_set():
            save(out/'heartbeat.json', {'recorded_at': stamp(), 'pid': os.getpid(), 'process_identity': process_identity(os.getpid()), 'operation': dict(phase)})
            finished.wait(15)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    def update(final=False):
        record['new_q21_attempts_charged'] = ledger_count(out/'q21/exact')
        need(record['new_q21_attempts_charged'] <= plan['q21']['maximum_additional_attempts'], 'Final Q21 allocation exceeded')
        if (out/'q21/exact/DONE.json').exists():
            record['q21'] = load(out/'q21/exact/record.json')
        save(out/'record.json', record)
        save(out/'status.json', {'recorded_at': stamp(), 'status': record['status'], 'phase': dict(phase), 'new_q21_attempts_charged': record['new_q21_attempts_charged'], 'maximum_new_q21_attempts': 20, 'q22_status': record['q22'].get('status') if record['q22'] else None, 'physical_time_steps': 0, 'error': record['error']})
        report(out, record)
        if final:
            seal(out)
    try:
        check_reserve(out)
        control = plan['q2']
        path = original_run(repo)/control['original_relative_path']
        check_file(path, control['sha256'])
        with np.load(path, allow_pickle=False) as z:
            n = z['field'].copy()
        grid = Grid((control['nodes'],)*3, (control['length'],)*3, 'fixed')
        m = metrics(n, grid, plan['registered_gates'])
        for key in ['energy', 'relative_force_l2', 'acceleration_max', 'tail_fraction', 'guard_fraction']:
            need(np.isclose(m[key], control['expected'][key], rtol=1e-6, atol=1e-10), 'Q2 retained control replay differs: ' + key)
        record['q2'] = {'recorded_at': stamp(), 'metrics': m, 'gates': gate_result(m, 2, plan['registered_gates']), 'source_sha256': control['sha256']}
        need(record['q2']['gates']['all_readiness_gates'], 'Q2 control fails; no Q21 optimizer allocation')
        del n
        gc.collect()
        update()
        phase.update(name='q22-local-inventory')
        search = load(out/'SEARCH-CONFIG.json')
        need(canonical(search) == identity['search_configuration_sha256'], 'Recovery configuration identity differs')
        inventory = Search(out, plan['recovery'], plan['q22']['sha256'], STOP.is_set, phase).run(search['extra_roots'], search['explicit_q22'])
        save(out/'Q22-INVENTORY.json', inventory)
        record['q22'] = inventory
        update()
        if STOP.is_set() or (out/'STOP.json').exists():
            raise KeyboardInterrupt('Orderly pause after recovery inventory')
        if inventory['status'] == 'authenticated_recovered':
            phase.update(name='q22-native-cell-d4-comparison', candidate=None)
            folder = out/'q22'
            folder.mkdir(exist_ok=True)
            if (folder/'DONE.json').exists():
                need(load(folder/'DONE.json')['sha256'] == sha(folder/'record.json'), 'Cached native Q22 record changed')
                record['q22'] = load(folder/'record.json')
            else:
                check_reserve(out)
                path = Path(inventory['path'])
                check_file(path, plan['q22']['sha256'])
                record['q22'] = q22_compare(path, plan['q22'], plan['registered_gates'], folder)
                record['q22']['recovery_source'] = inventory
                check_file(path, plan['q22']['sha256'])
                save(folder/'record.json', record['q22'])
                save(folder/'DONE.json', {'recorded_at': stamp(), 'sha256': sha(folder/'record.json')})
        else:
            record['deferred'].append('Native Q22 operator comparison: exact field not recovered within declared local coverage/limits')
        update()
        if STOP.is_set() or (out/'STOP.json').exists():
            raise KeyboardInterrupt('Orderly pause before Q21 final tranche')
        phase.update(name='q21-exact-315-replay', candidate=None)
        parent, original = read_parent(repo, plan['q21'])
        grid = Grid((plan['q21']['nodes'],)*3, (plan['q21']['length'],)*3, 'fixed')
        receipt_path = out/'BACKEND.json'
        if receipt_path.exists():
            backend = load(receipt_path)
            need(backend['requested'] == identity['requested_backend'], 'Resume backend differs')
        else:
            backend = backend_record(parent, original, identity['requested_backend'], grid)
            save(receipt_path, backend)
        record['q21'] = run_continuation(repo, out, parent, backend, grid, plan, STOP.is_set, phase)
        del parent
        gc.collect()
        source_checkpoint(repo)
        record.update(status='complete_pending_review', finished_at=stamp())
        phase.update(name='complete')
        update(True)
        log('Final Q21 tranche and Q22 recovery complete', output=str(out), new_q21_attempts=record['new_q21_attempts_charged'], q22_status=record['q22']['status'], evidence=str(out/'evidence.zip'))
    except BaseException as error:
        resource = isinstance(error, MemoryError) or any(t in str(error).lower() for t in ['reserve reached', 'out of memory', 'outofmemory'])
        record.update(status='interrupted' if isinstance(error, KeyboardInterrupt) or resource else 'failed', error=str(error))
        update(True)
        if record['status'] == 'failed':
            traceback.print_exc()
            raise
    finally:
        finished.set()
        thread.join(timeout=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo/'src'))
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    with (original_run(args.repo)/'.worker.lock').open('r') as a, (source_run(args.repo)/'.worker.lock').open('r') as b, (args.output/'.worker.lock').open('a') as c:
        for lock in [a,b,c]:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        execute(args.repo.resolve(), args.output.resolve())

if __name__ == '__main__':
    main()
