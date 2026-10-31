"""Budget and scientific eligibility controls; no GPU or long numerical run."""
import copy
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from electron_field_topology import sf_q22_closure as closure


def reference():
    return copy.deepcopy(closure.published_case(closure.REFERENCE))


def test_energy_agreement_cannot_mask_nonstationarity_or_mismatched_spacing():
    a = reference(); b = copy.deepcopy(a)
    b['config'].update(n=193, h=.12)
    b['final']['energy'] *= 1.001
    assert closure.compare_energy(a, b, 'domain')['status'] == 'pass'
    b['final']['cpu_tangent_gradient_rms'] = .009
    assert closure.compare_energy(a, b, 'domain')['status'] == 'unresolved'
    b['config']['h'] = .08
    assert closure.compare_energy(a, b, 'domain')['reason'] == 'spacing mismatch'
    b['config'].update(n=129, h=.12)
    assert closure.compare_energy(a, b, 'ranking')['status'] == 'unresolved'
    b['final']['cpu_tangent_gradient_rms'] = .0009
    assert closure.compare_energy(a, b, 'ranking')['status'] == 'eligible'


def test_mesh_requires_equal_physical_boxes_and_preserves_failed_energy_gate():
    a = reference(); b = copy.deepcopy(a)
    b['config'].update(n=161, h=.096)
    assert closure.compare_energy(a, b, 'mesh')['status'] == 'pass'
    b['final']['energy'] *= 1.03
    assert closure.compare_energy(a, b, 'mesh')['status'] == 'fail'
    b['config']['h'] = .1
    assert closure.compare_energy(a, b, 'mesh')['reason'] == 'box mismatch'


def test_no_overall_cap_and_config_continues_existing_fields_without_new_seed():
    plan = closure.read(closure.PLAN); closure.validate_plan(plan)
    stage = plan['stages'][0]
    config = closure.prepare_config(stage, reference()['config'], '/retained/final.npz', plan, .25)
    assert plan['overall_wall_seconds'] is None
    assert config['initial_checkpoint'] == '/retained/final.npz'
    assert config['seconds'] == 1800 and config['n'] == 161 and config['h'] == .096
    assert config['published_energy'] == 12.509 and config['precondition_length'] == .25
    assert 'utc' in config['prepared_at'] and 'melbourne' in config['prepared_at']
    plan['overall_wall_seconds'] = 7200
    with pytest.raises(ValueError, match='no overall'): closure.validate_plan(plan)


def test_stall_controls_distinguish_slow_progress_from_a_plateau():
    plan = closure.read(closure.PLAN)
    assert not closure.stalled([{'energy': 12.5, 'residual': .01}], plan)
    plateau = [{'energy': 12.5, 'residual': .01}] * 3
    assert closure.stalled(plateau, plan)
    assert not closure.stalled([{'energy': 12.5, 'residual': x} for x in [.01, .0099, .0098]], plan)


def fake_archive(tmp_path, monkeypatch):
    record = tmp_path / 'records'; old = tmp_path / 'old'
    record.mkdir(); old.mkdir()
    monkeypatch.setattr(closure, 'RECORD', record)
    for stage in closure.read(closure.PLAN)['stages']:
        if 'source_case' not in stage: continue
        name = stage['source_case']; folder = record / 'cases' / name
        folder.mkdir(parents=True)
        case = old / 'cases' / name; case.mkdir(parents=True)
        checkpoint = case / 'final.npz'; checkpoint.write_bytes(('field-' + name).encode())
        r = reference_result()
        (folder / 'result.json').write_text(json.dumps(r))
        manifest = {'source_sha256': {}, 'lock_sha256': closure.sha(closure.ROOT / 'uv.lock'),
                    'source_unchanged_during_run': True,
                    'artifacts_sha256': {'final.npz': closure.sha(checkpoint)}}
        (folder / 'manifest.json').write_text(json.dumps(manifest))
    for name in ('q1-control-1', 'q2-control-1'):
        folder = record / 'cases' / name; folder.mkdir(parents=True)
        (folder / 'result.json').write_text(json.dumps(reference_result()))
    return old


def reference_result():
    # Load the immutable real coarse endpoint without depending on RECORD monkeypatches.
    folder = closure.ROOT / 'reports/s5-a/workstation-2026-11-01/records'
    return json.loads((folder / 'cases' / closure.REFERENCE / 'result.json').read_text())


def test_preflight_rejects_modified_field_and_missing_required_input(tmp_path, monkeypatch):
    old = fake_archive(tmp_path, monkeypatch)
    receipt = closure.preflight(old)
    assert all(v['status'] == 'verified' for v in receipt['inputs'].values())
    path = old / 'cases/q22-161-1/final.npz'; path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'): closure.preflight(old)
    path.unlink()
    with pytest.raises(ValueError, match='Required workstation field'): closure.preflight(old)


def test_missing_optional_comparator_does_not_block_required_closure(tmp_path, monkeypatch):
    old = fake_archive(tmp_path, monkeypatch)
    (old / 'cases/q22-comparison-1/final.npz').unlink()
    assert closure.preflight(old)['inputs']['q22-comparison-1']['status'] == 'optional_missing'


def test_new_output_cannot_overwrite_historical_campaign(tmp_path, monkeypatch):
    monkeypatch.setattr(closure, 'preflight', lambda _: {})
    with pytest.raises(ValueError, match='separate'):
        closure.run(tmp_path, tmp_path / 'new')


def test_stale_topology_never_counts_as_current_evidence(tmp_path):
    assert closure.topology_gate(tmp_path, 'current')['status'] == 'unresolved'
    (tmp_path / 'topology.json').write_text(json.dumps({'phases': {'final': {'checkpoint_sha256': 'stale'}}}))
    assert 'hash mismatch' in closure.topology_gate(tmp_path, 'current')['reason']


def fake_run(tmp_path, monkeypatch, executor, *, resume=False, old=None, out=None):
    old = old or tmp_path / 'original'; old.mkdir(exist_ok=True)
    receipt = {'source_campaign': str(old), 'inputs': {}}
    for stage in closure.read(closure.PLAN)['stages']:
        if 'source_case' not in stage: continue
        path = old / (stage['source_case'] + '.npz'); path.write_bytes(b'original')
        receipt['inputs'][stage['source_case']] = {'status': 'verified', 'path': str(path), 'sha256': closure.sha(path)}
    monkeypatch.setattr(closure, 'preflight', lambda _: receipt)
    def git_output(args, **kwargs):
        return '' if args[1] == 'status' else 'fixed-test-commit\n'
    monkeypatch.setattr(closure.subprocess, 'check_output', git_output)
    monkeypatch.setattr(closure, 'execute', executor)
    out = out or tmp_path / 'new'
    closure.run(old, out, resume=resume)
    return out


def test_campaign_exports_failures_without_rerunning_or_including_bulk_fields(tmp_path, monkeypatch):
    calls = []
    def failed(argv, log, seconds):
        calls.append((argv, seconds)); Path(log).write_text('retained failure\n')
        return {'status': 'failed', 'returncode': 1}
    out = fake_run(tmp_path, monkeypatch, failed)
    state = closure.read(out / 'campaign.json')
    assert len([a for a, _ in calls if '-m' in a]) == 4
    assert len(state['stages']) == 8
    report = closure.read(out / 'summary.json')
    assert all(v['status'] == 'unresolved' for v in report['comparisons'].values())
    assert report['disposition'] == 'partial_pending_scientific_review'
    with zipfile.ZipFile(out / 'evidence.zip') as archive:
        manifest = json.loads(archive.read('evidence-hashes.json'))
        hashes = manifest['files']
        assert 'utc' in manifest['generated_at']
        assert set(hashes) == set(archive.namelist()) - {'evidence-hashes.json'}
        for name, record in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == record['sha256']
            assert 'melbourne' in record['modified_at']
        assert any('q22-193-polish' in name for name in hashes)
        assert not any(name.startswith('cases/') and name.endswith('.npz') for name in hashes)
    before = len(calls)
    closure.summarize(out, state)
    assert len(calls) == before
    with pytest.raises(FileExistsError): closure.run(tmp_path / 'original', out)


def synthetic_endpoint(argv, log, seconds, *, residual=.0008, status=None):
    Path(log).write_text('Synthetic executor, not CUDA execution.\n')
    if '-m' not in argv: return {'status': 'completed', 'returncode': 0}
    case = Path(argv[argv.index('--output') + 1]); case.mkdir()
    config = closure.read(argv[argv.index('--config') + 1])
    closure.atomic_json(case / 'config.json', config)
    r = reference_result(); r['config'] = config
    r['final']['cpu_tangent_gradient_rms'] = residual
    r['final']['tangent_gradient_rms'] = residual
    r['status'] = status or ('gradient_stationary' if residual < .001 else 'time_budget')
    closure.atomic_json(case / 'result.json', r)
    closure.atomic_json(case / 'history.json', [])
    (case / 'initial.npz').write_bytes(b'not-a-real-field-in-test')
    (case / 'final.npz').write_bytes(b'not-a-real-field-in-test')
    manifest = {'source_unchanged_during_run': True, 'device_validation': {'passed': True},
        'source_sha256': {p: h for p, h in closure.code_hashes().items() if p.startswith('src/')},
        'lock_sha256': closure.sha(closure.ROOT / 'uv.lock'), 'git_commit': 'fixed-test-commit',
        'initial_checkpoint_sha256': closure.sha(config['initial_checkpoint']),
        'artifacts_sha256': {p.name: closure.sha(p) for p in case.iterdir()}}
    closure.atomic_json(case / 'manifest.json', manifest)
    return {'status': 'completed', 'returncode': 0}


def test_full_study_can_exceed_two_hours_and_resume_without_repeating_finished_passes(tmp_path, monkeypatch):
    calls = []; clock = [1000.]
    monkeypatch.setattr(closure.time, 'time', lambda: clock[0])
    def executor(argv, log, seconds):
        if '-m' in argv:
            calls.append(argv)
            clock[0] += 1800
            case = Path(argv[argv.index('--output') + 1])
            residual = .002 if 'pass001' in case.name else .0008
            return synthetic_endpoint(argv, log, seconds, residual=residual)
        return synthetic_endpoint(argv, log, seconds)
    out = fake_run(tmp_path, monkeypatch, executor)
    state = closure.read(out / 'campaign.json')
    assert clock[0] > 1000 + 7200
    assert len(calls) == 16
    assert all(v['status'] == 'stationary' for v in state['stages'].values())
    assert all(v['passes'] == 2 for v in closure.read(out / 'summary.json')['stages'].values())
    assert all(v['artifact_audit'] for v in closure.read(out / 'summary.json')['stages'].values())
    for job in state['stages'].values():
        for attempt in job['attempts']:
            case = out / attempt['directory']
            assert '+1100' in case.name
            assert 'record_timestamps' in closure.read(case / 'result.json')
            assert 'record_timestamps' in closure.read(case / 'manifest.json')
            assert 'timing.json' in closure.read(case / 'manifest.json')['artifacts_sha256']
    before = len(calls)
    fake_run(tmp_path, monkeypatch, executor, resume=True, out=out)
    assert len(calls) == before


def test_stalled_solver_tries_each_declared_option_and_preserves_negative_results(tmp_path, monkeypatch):
    def executor(argv, log, seconds):
        return synthetic_endpoint(argv, log, seconds, residual=.002)
    out = fake_run(tmp_path, monkeypatch, executor)
    state = closure.read(out / 'campaign.json')
    for job in state['stages'].values():
        assert job['status'] == 'stalled_after_options'
        assert len(job['attempts']) == 9
        assert {x['precondition_length'] for x in job['attempts']} == {.5, .25, 1.}
    assert all(v['status'] == 'unresolved' for v in closure.read(out / 'summary.json')['comparisons'].values())


def test_interrupted_audited_endpoint_can_resume_without_restarting_from_old_field(tmp_path, monkeypatch):
    first = [True]
    def executor(argv, log, seconds):
        if '-m' in argv and first[0]:
            first[0] = False
            return synthetic_endpoint(argv, log, seconds, residual=.002, status='interrupted')
        return synthetic_endpoint(argv, log, seconds)
    out = fake_run(tmp_path, monkeypatch, executor)
    state = closure.read(out / 'campaign.json')
    assert state['interrupted'] is True
    original = out / state['stages']['q22-161-polish']['directory'] / 'final.npz'
    fake_run(tmp_path, monkeypatch, executor, resume=True, out=out)
    state = closure.read(out / 'campaign.json')
    second = out / state['stages']['q22-161-polish']['directory'] / 'config.json'
    assert closure.read(second)['initial_checkpoint'] == str(original)
    assert state['stages']['q22-161-polish']['status'] == 'stationary'


def test_keyboard_interrupt_retains_logs_and_explicit_unrun_stages(tmp_path, monkeypatch):
    def interrupted(argv, log, seconds):
        Path(log).write_text('checkpoint preserved by child')
        raise KeyboardInterrupt
    out = fake_run(tmp_path, monkeypatch, interrupted)
    state = closure.read(out / 'campaign.json')
    assert state['interrupted'] is True
    assert state['stages']['q22-193-polish']['status'] == 'not_started'
    assert (out / 'evidence.zip').exists()


def test_timestamp_has_correct_melbourne_zone_and_tampering_cannot_be_hidden(tmp_path):
    stamp = closure.timestamp(1793491200)
    assert stamp['utc'].endswith('+00:00') and stamp['melbourne'].endswith('+11:00')
    case = tmp_path / 'case'; case.mkdir()
    (case / 'result.json').write_text('{}')
    closure.atomic_json(case / 'manifest.json', {'artifacts_sha256': {'result.json': 'wrong-hash'}})
    with pytest.raises(ValueError, match='mismatched solver artifact'):
        closure.stamp_case(case, stamp, stamp)


def test_corrupted_endpoint_is_excluded_from_energy_comparisons(tmp_path, monkeypatch):
    out = fake_run(tmp_path, monkeypatch, synthetic_endpoint)
    state = closure.read(out / 'campaign.json')
    case = out / state['stages']['q22-161-polish']['directory']
    (case / 'final.npz').write_bytes(b'corrupted')
    report = closure.summarize(out, state)
    assert report['stages']['q22-161-polish']['artifact_audit'] is False
    assert report['comparisons']['mesh_129_161']['status'] == 'unresolved'


def test_all_analysis_json_is_timestamped_and_references_cache_is_reused(tmp_path, monkeypatch):
    def executor(argv, log, seconds):
        if '-m' in argv: return synthetic_endpoint(argv, log, seconds)
        Path(log).write_text('Synthetic analysis')
        output = Path(argv[argv.index('--output') + 1])
        script = argv[1]
        if script.endswith('match_static_cable_diagrams.py'):
            output.parent.mkdir(parents=True, exist_ok=True)
            closure.atomic_json(output, {'matched': False})
        else:
            output.mkdir(parents=True, exist_ok=True)
            if script.endswith('static_knot_references.py'):
                closure.atomic_json(output / 'references.json', {'cable': {}})
            elif script.endswith('analyse_static_fields.py'):
                checkpoint = Path(argv[argv.index('--case') + 1]) / 'final.npz'
                closure.atomic_json(output / 'topology.json', {'phases': {'final': {'checkpoint_sha256': closure.sha(checkpoint)}}})
            else:
                checkpoint = Path(argv[argv.index('--checkpoint') + 1])
                closure.atomic_json(output / 'scaling.json', {'checkpoint_sha256': closure.sha(checkpoint),
                    'finite_difference_comparisons': [{'normalized_energy_derivative': 0., 'difference_from_e2_minus_e4': 0.}] * 2})
        return {'status': 'completed', 'returncode': 0}
    out = fake_run(tmp_path, monkeypatch, executor)
    paths = list((out / 'analysis').rglob('*.json'))
    assert paths
    assert all('record_timestamps' in closure.read(p) for p in paths)
    report = closure.read(out / 'summary.json')
    assert all(v['independent_scaling'] == 'pass' for v in report['stages'].values())
    assert len(list((out / 'logs').glob('references-*.log'))) == 1


def test_low_disk_space_pauses_without_starting_or_deleting_a_pass(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(closure.shutil, 'disk_usage', lambda _: SimpleNamespace(free=0))
    def never(*_): raise AssertionError('A low-space study must not start a subprocess')
    out = fake_run(tmp_path, monkeypatch, never)
    state = closure.read(out / 'campaign.json')
    assert state['interrupted']
    assert state['stages']['q22-161-polish']['status'] == 'disk_space_pause'
    assert not list((out / 'cases').iterdir())


def test_concurrent_resume_is_rejected(tmp_path, monkeypatch):
    import fcntl
    out = fake_run(tmp_path, monkeypatch, synthetic_endpoint)
    with (out / 'run.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ValueError, match='already running'):
            fake_run(tmp_path, monkeypatch, synthetic_endpoint, resume=True, out=out)
