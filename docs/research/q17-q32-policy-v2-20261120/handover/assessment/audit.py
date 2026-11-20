"""Replay saved policy decisions without running or changing numerical fields."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import zipfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = "1967a35025b750e89f52aa6d6ca6c34d525628c9573521e17e62dd01d63705d0"


def stamp():
    t = datetime.now(timezone.utc)
    return {"utc": t.isoformat(), "melbourne": t.astimezone(ZoneInfo("Australia/Melbourne")).isoformat()}


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def evidence():
    path = ROOT / "data/source-evidence.zip"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SOURCE_SHA
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        assert len(names) == len(set(names)) and z.testzip() is None
        hashes = {}
        for line in z.read("SHA256SUMS").decode().splitlines():
            h, n = line.split("  ", 1)
            p = PurePosixPath(n)
            assert not p.is_absolute() and ".." not in p.parts and n not in hashes
            assert hashlib.sha256(z.read(n)).hexdigest() == h
            hashes[n] = h
        assert set(hashes) == set(names) - {"SHA256SUMS"}
        objects = {n: json.loads(z.read(n)) for n in names if n.endswith(".json")}
        # Reconstruct the original handover manifest, omitted from compact payloads.
        payloads = sorted(n for n in names if n.startswith("handover/"))
        manifest = "".join(hashlib.sha256(z.read(n)).hexdigest() + "  " + n.removeprefix("handover/") + "\n" for n in payloads)
        identity = objects["identity.json"]
        assert len(payloads) == 34
        assert hashlib.sha256(manifest.encode()).hexdigest() == identity["package_sha256"]
        assert z.read("handover/science/fits.py") == (ROOT / "original/fits.py").read_bytes()
        for n, h in identity["complete_numerical_source_sha256"].items():
            assert hashlib.sha256(z.read("numerical-source/" + n)).hexdigest() == h
    return objects, {"recorded_at": stamp(), "archive_sha256": SOURCE_SHA, "zip_crc_pass": True,
                     "compact_payloads_verified": len(hashes), "numerical_source_copies_verified": len(identity["complete_numerical_source_sha256"]),
                     "original_handover_manifest_reconstructed": True,
                     "local_full_field_declarations": len(objects["field-manifest.json"]["fields"]),
                     "local_full_fields_verified_here": False, "solver_steps": 0}


@contextmanager
def saved_models(mod, recorded):
    original = mod.models
    mod.models = lambda rows, key, p: recorded["models"][key]
    try:
        yield
    finally:
        mod.models = original


def compare(original, saved):
    keys = ["iteration", "remaining_attempts", "fit_epoch_start", "recent_improvement", "recent_joint_progress", "energy_nonincreasing", "plateau_count", "action", "reason", "steps", "observe"]
    for key in keys:
        assert original[key] == saved[key], (key, original[key], saved[key])


def replay(objects):
    old = module("original_policy", "original/fits.py")
    new = module("corrected_policy", "corrected/policy_v2.py")
    p = objects["record.json"]["plan"]
    results = []
    traces = []
    for name in sorted(objects):
        if not name.startswith("broad/") or not name.endswith("/decisions.json"):
            continue
        ds = objects[name]
        history = objects[name.removesuffix("decisions.json") + "history.json"]
        seed = name.split("/")[1]
        old_count, new_count, previous_epoch = 0, 0, None
        reset_events, incomplete_events, terminal = [], [], None
        for saved in ds:
            prefix = [h for h in history if h["iteration"] <= saved["iteration"]]
            with saved_models(old, saved):
                observed = old.decide(prefix, p, saved["remaining_attempts"], old_count)
            compare(observed, saved)
            with saved_models(new, saved):
                corrected = new.decide(prefix, p, saved["remaining_attempts"], new_count, plateau_epoch=previous_epoch)
            if previous_epoch is not None and saved["fit_epoch_start"] != previous_epoch:
                reset_events.append({"iteration": saved["iteration"], "old_count_entering_epoch": old_count, "new_count_entering_epoch": new_count})
            if not corrected["progress_evidence_sufficient"] and saved["plateau_count"] > 0:
                incomplete_events.append({"iteration": saved["iteration"], "distinct_rows": corrected["distinct_epoch_observations"], "old_plateau_count": saved["plateau_count"], "old_action": saved["action"]})
            if saved["action"] == "stop":
                terminal = {"old_action": saved["action"], "corrected_action": corrected["action"], "old_count": saved["plateau_count"], "corrected_count": corrected["plateau_count"], "iteration": saved["iteration"], "remaining_attempts": saved["remaining_attempts"], "progress_evidence_sufficient": corrected["progress_evidence_sufficient"], "distinct_epoch_observations": corrected["distinct_epoch_observations"]}
            else:
                # The correction must not change allocations along the observed
                # pre-terminal trajectory in this supplied dataset.
                assert corrected["action"] == saved["action"] and corrected["steps"] == saved["steps"] and corrected["observe"] == saved["observe"], (seed, saved["iteration"])
            traces.append({"seed": seed, "iteration": saved["iteration"], "old_count": saved["plateau_count"], "corrected_count": corrected["plateau_count"], "old_action": saved["action"], "corrected_action": corrected["action"], "distinct_epoch_observations": corrected["distinct_epoch_observations"], "progress_evidence_sufficient": corrected["progress_evidence_sufficient"]})
            old_count, new_count, previous_epoch = saved["plateau_count"], corrected["plateau_count"], saved["fit_epoch_start"]
        assert terminal is not None
        results.append({"seed": seed, "decisions_verified": len(ds), "reset_events": reset_events, "short_window_votes": incomplete_events, "terminal": terminal})
    changed = [r for r in results if r["terminal"]["corrected_action"] != r["terminal"]["old_action"]]
    return {"recorded_at": stamp(), "scope": "Decision-logic replay on recorded trajectories using recorded fits; no new solver steps or extrapolated physical outcomes", "policy_v2": {"epoch_local_plateau_counter": True, "minimum_distinct_observations": p["fit_minimum"], "unchanged_minimum_iteration": p["minimum_before_plateau"], "unchanged_plateau_decisions": p["plateau_decisions"], "no_gate_change": True}, "branches_replayed": len(results), "original_decisions_reproduced": len(traces), "terminal_actions_changed": len(changed), "affected_unused_attempts": sum(r["terminal"]["remaining_attempts"] for r in changed), "results": results, "traces": traces}


def run(output):
    objects, verification = evidence()
    result = replay(objects)
    output.mkdir(parents=True, exist_ok=True)
    (output / "VERIFICATION.json").write_text(json.dumps(verification, indent=2) + "\n")
    (output / "REPLAY.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"recorded_at": stamp(), "status": "offline_audit_complete", "output": str(output), "decisions_reproduced": result["original_decisions_reproduced"], "terminal_actions_changed": result["terminal_actions_changed"], "solver_steps": 0}))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
