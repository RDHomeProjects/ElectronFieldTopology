"""Checkpoint integrity, continuation, interrupted fields and bounded plan."""
import json
from pathlib import Path
import zipfile
import numpy as np
import pytest
from electron_field_topology.skyrme import Energy, coordinates, rational_field, set_boundary
from electron_field_topology.sf_checkpoints import checkpoint, load_field, atomic_json
from electron_field_topology.sf_gpu_relax import run
from electron_field_topology.sf_campaign import PLAN, CONFIGS, read, bundle
from electron_field_topology.sf_relax import validate


def config(tmp_path):
    c = {"model_id": "SF-J2015-static", "case": "test", "n": 33, "h": .2,
         "expected_q": 1, "iterations": 2, "seconds": 30, "record_every": 1,
         "solver": "sobolev_cg", "discretisation": "cell",
         "seed": {"kind": "axial", "alpha": 1, "beta": 1, "scale": 1., "cutoff": 2.8}}
    path = tmp_path/"config.json"; atomic_json(path, c)
    return path


def test_float64_atomic_rolling_checkpoint_and_wrong_charge_rejection(tmp_path):
    u = set_boundary(rational_field(coordinates(33, .2), scale=1., cutoff=2.8))
    path = tmp_path/"latest.npz"
    checkpoint(path, u, .2, 1, 2, 1., "test")
    first = path.read_bytes()
    checkpoint(path, u, .2, 1, 3, 2., "test")
    assert (tmp_path/"previous.npz").read_bytes() == first
    with np.load(path) as d:
        assert d["field"].dtype == np.float64
        np.testing.assert_array_equal(d["field"], u)
    with pytest.raises(ValueError, match="Hopf-label"):
        load_field(path, 33, .2, 2)
    assert load_field(path, 41, .16, 1).shape == (41, 41, 41, 3)
    assert not list(tmp_path.glob("*.tmp"))


def test_checkpointed_runner_and_resume_with_explicit_cpu_test_double(tmp_path):
    cfg = config(tmp_path)
    factory = lambda n, h: Energy(n, h, tmp_path/"native")
    result = run(cfg, tmp_path/"first", _runtime=(np, factory))
    assert result["iterations"] == 2
    assert result["final"]["cpu_endpoint_audit"]
    assert (tmp_path/"first/previous.npz").exists()
    resumed = run(cfg, tmp_path/"second", tmp_path/"first/final.npz", _runtime=(np, factory))
    assert resumed["initial"]["energy"] == pytest.approx(result["final"]["energy"], rel=1e-12)
    assert resumed["final"]["energy"] < resumed["initial"]["energy"]
    assert read(tmp_path/"second/manifest.json")["backend"] == "host-test-double"
    with pytest.raises(FileExistsError):
        run(cfg, tmp_path/"second", _runtime=(np, factory))


def test_keyboard_interrupt_preserves_latest_accepted_field(tmp_path, monkeypatch):
    from electron_field_topology import sf_gpu_relax
    def interrupted(engine, initial, maximum, callback, expired, xp, **kwargs):
        callback(initial, 1)
        raise KeyboardInterrupt
    monkeypatch.setattr(sf_gpu_relax, "minimize_array", interrupted)
    result = run(config(tmp_path), tmp_path/"stop", _runtime=(np, lambda n, h: Energy(n, h, tmp_path/"native")))
    assert result["status"] == "interrupted" and result["iterations"] == 1
    assert (tmp_path/"stop/final.npz").exists()
    assert read(tmp_path/"stop/result.json")["status"] == "interrupted"


def test_campaign_plan_dependencies_budgets_and_repeatable_evidence_hashes(tmp_path):
    plan = read(PLAN); known = set()
    assert plan["wall_seconds"] == 7200
    for stage in plan["stages"]:
        if "from" in stage: assert stage["from"] in known
        known.add(stage["id"])
        c = read(CONFIGS/stage["config"])
        for k in ("n", "h", "iterations", "seconds"):
            if k in stage: c[k] = stage[k]
        validate(c)
    state = {"campaign_id": "test", "stages": {}, "analysis": {}}
    bundle(tmp_path, state); bundle(tmp_path, state)
    with zipfile.ZipFile(tmp_path/"evidence.zip") as z:
        assert len(z.namelist()) == len(set(z.namelist()))
        manifest = json.loads(z.read("evidence-hashes.json"))
        import hashlib
        assert all(hashlib.sha256(z.read(k)).hexdigest() == v for k, v in manifest.items())


def test_rejected_trial_cannot_replace_accepted_continuity_margin(tmp_path):
    from electron_field_topology.sf_gpu import minimize_array
    u = set_boundary(rational_field(coordinates(17, .2), scale=.6, cutoff=1.3))
    class TrialControl:
        h = .2
        def __init__(self, path):
            self.native = Energy(17, self.h, path); self.calls = 0
        def evaluate(self, field):
            self.calls += 1; p, g = self.native.evaluate(field)
            self.minimum_corner_cone = self.native.minimum_corner_cone
            if self.calls == 2:
                # Deliberately rejected candidate: its cell margin must not poison
                # the remaining line search about the last accepted field.
                self.minimum_corner_cone = -.1; p = p*1e6
            return p, g
    _, old = minimize_array(TrialControl(tmp_path/"old"), u, 1, lambda f, i: None, lambda: False, np)
    field, strict = minimize_array(TrialControl(tmp_path/"strict"), u, 1, lambda f, i: None, lambda: False, np, strict_continuity=True)
    assert old["status"] == "line_search_limit"
    assert strict["iterations"] == 1 and strict["status"] == "iteration_budget"
    assert not np.array_equal(field, u)


def test_subprocess_log_retention_and_timeout(tmp_path):
    import sys
    from electron_field_topology.sf_campaign import execute
    log = tmp_path/'job.log'
    result = execute([sys.executable, '-c', 'print("completed")'], log, 2)
    assert result['status'] == 'completed' and 'completed' in log.read_text()
    result = execute([sys.executable, '-c', 'import time; time.sleep(5)'], log, 1)
    assert result['status'] == 'timeout'


def test_analysis_cache_changes_when_checkpoint_or_attempt_changes(tmp_path):
    from electron_field_topology.sf_campaign import analysis_signature
    p = tmp_path/'field.npz'; p.write_bytes(b'first test input')
    argv = ['python', 'test.py', '--checkpoint', str(p), '--output', str(tmp_path/'analysis')]
    first = analysis_signature(argv)
    p.write_bytes(b'changed test input')
    assert analysis_signature(argv) != first
