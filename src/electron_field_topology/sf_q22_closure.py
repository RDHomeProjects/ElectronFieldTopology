"""Checkpointed Q22 convergence study using published checkpoint hashes. Apache-2.0.

No solver, coefficient or scientific threshold changes. No automatic extension
of a historical budget. Collection can be repeated without starting computation.
"""
import argparse
import fcntl
from datetime import datetime, timezone
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time
import zipfile
from zoneinfo import ZoneInfo

from .sf_campaign import basic_gates, execute, analysis_signature
from .sf_checkpoints import atomic_json, sha
from .sf_relax import validate

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "reports/s5-a/workstation-2026-11-01/records"
PLAN = ROOT / "experiments/configs/sf-j2015/q22-closure.json"
DEFAULT_SOURCE = Path("/home/rd/ElectronFieldTopology-timing/artifacts/gpu-continuation-20261101-004351")
REFERENCE = "q22-129-cont-1"


def timestamp(epoch=None):
    instant = datetime.fromtimestamp(time.time() if epoch is None else epoch, timezone.utc)
    return {"utc": instant.isoformat(timespec="seconds"),
            "melbourne": instant.astimezone(ZoneInfo("Australia/Melbourne")).isoformat(timespec="seconds")}


def date_tag():
    return datetime.now(timezone.utc).astimezone(ZoneInfo("Australia/Melbourne")).strftime("%Y%m%dT%H%M%S%z")


def stamp_case(case, started, finished):
    """Add publication timestamps without changing any saved field values.

    The solver history retains its elapsed-time observations. Its sidecar records
    file timestamps; no retrospectively invented per-sample clock is supplied.
    """
    manifest_path = case / "manifest.json"
    original_manifest = read(manifest_path) if manifest_path.exists() else None
    if original_manifest and "artifacts_sha256" in original_manifest:
        if not all(sha(case / p) == h for p, h in original_manifest["artifacts_sha256"].items()):
            raise ValueError("Cannot timestamp an endpoint with mismatched solver artifact hashes")
    times = {"execution_started": started, "execution_finished": finished,
             "metadata_recorded": timestamp()}
    atomic_json(case / "timing.json", {"timestamps": times,
        "files": {p.name: {"modified_at": timestamp(p.stat().st_mtime)}
                  for p in sorted(case.iterdir()) if p.is_file()}})
    result_path = case / "result.json"; manifest_path = case / "manifest.json"
    if result_path.exists():
        r = read(result_path); r["record_timestamps"] = times; atomic_json(result_path, r)
    if manifest_path.exists():
        m = original_manifest; m["record_timestamps"] = times
        # Never turn an incomplete solver manifest into an audited endpoint.
        if "artifacts_sha256" in m:
            m["artifacts_sha256"] = {p.name: sha(p) for p in case.iterdir()
                if p.is_file() and p.name != "manifest.json"}
        atomic_json(manifest_path, m)


def read(path):
    return json.loads(Path(path).read_text())


def code_hashes():
    paths = [p for folder in (ROOT / "src", ROOT / "scripts") for p in folder.rglob("*")
             if p.suffix in (".py", ".c", ".cu")]
    paths += [ROOT / "uv.lock", PLAN]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def validate_plan(plan):
    """Pass controls bound checkpoint intervals, not the overall study duration."""
    if plan["model_id"] != "SF-J2015-static" or plan["overall_wall_seconds"] is not None:
        raise ValueError("Q22 study has no overall wall-time cap")
    if (not 1 <= plan["pass_seconds"] <= 1800 or not 1 <= plan["pass_iterations"] <= 3000
            or not 1 <= plan["analysis_job_seconds"] <= 3600 or plan["audit_grace_seconds"] < 1
            or plan["stall_window_passes"] < 3 or not plan["precondition_lengths"]
            or any(not 0 < x <= 2 for x in plan["precondition_lengths"])):
        raise ValueError("Invalid checkpoint/progress controls")
    seen = set()
    for stage in plan["stages"]:
        if stage["id"] in seen or bool(stage.get("from")) == bool(stage.get("source_case")):
            raise ValueError("Unique ordered stage with exactly one input required")
        if stage.get("from") and stage["from"] not in seen:
            raise ValueError("Dependency must precede its refinement")
        if stage["n"] not in (129, 161, 193) or stage["h"] not in (.08, .096, .12):
            raise ValueError("Reviewed Q22 meshes only")
        seen.add(stage["id"])


def published_case(name):
    return read(RECORD / "cases" / name / "result.json")


def preflight(source):
    """Verify immutable published provenance before touching large fields."""
    source = Path(source).resolve()
    plan = read(PLAN); validate_plan(plan)
    inputs = {}
    for stage in plan["stages"]:
        if "source_case" not in stage: continue
        name = stage["source_case"]
        manifest = read(RECORD / "cases" / name / "manifest.json")
        for path, expected in manifest["source_sha256"].items():
            if sha(ROOT / path) != expected:
                raise ValueError("Historical numerical source changed: " + path)
        if sha(ROOT / "uv.lock") != manifest["lock_sha256"]:
            raise ValueError("Historical dependency lock changed")
        result = published_case(name)
        gates = basic_gates(result)
        required = ("initial_charge", "final_charge", "resolved_cells", "unit_norm",
                    "endpoint_cpu_audit", "completed_without_numerical_fault")
        if not all(gates[g] for g in required) or not manifest["source_unchanged_during_run"]:
            raise ValueError("Published source audit unsuitable: " + name)
        checkpoint = source / "cases" / name / "final.npz"
        if not checkpoint.exists() and stage.get("optional"):
            inputs[name] = {"status": "optional_missing", "path": str(checkpoint)}
            continue
        if not checkpoint.is_file():
            raise ValueError("Required workstation field is missing: " + str(checkpoint))
        expected = manifest["artifacts_sha256"]["final.npz"]
        if sha(checkpoint) != expected:
            raise ValueError("Published checkpoint hash mismatch: " + str(checkpoint))
        inputs[name] = {"status": "verified", "path": str(checkpoint), "sha256": expected,
                        "n": result["config"]["n"], "h": result["config"]["h"]}
    if not all(basic_gates(published_case(REFERENCE)).values()):
        raise ValueError("Published coarse cable reference is not stationary/audited")
    for name in ("q1-control-1", "q2-control-1"):
        if not all(basic_gates(published_case(name)).values()):
            raise ValueError("Published low-Q control failed: " + name)
    return {"source_campaign": str(source), "inputs": inputs, "controls": "published controls pass",
            "scope": "hash verification; CPU/GPU endpoint audits repeat in each new solve"}


def prepare_config(stage, template, checkpoint, plan, length):
    c = dict(template)
    c.update(case=stage["id"], n=stage["n"], h=stage["h"], iterations=plan["pass_iterations"],
             seconds=plan["pass_seconds"], precondition_length=length,
             initial_checkpoint=str(checkpoint), prepared_at=timestamp())
    validate(c)
    return c


def stalled(records, plan):
    """Stall controls decide whether another optimiser option is worth trying.

    They never replace the scientific stationarity or convergence thresholds.
    """
    if len(records) < plan["stall_window_passes"]: return False
    window = records[-plan["stall_window_passes"]:]
    first = window[0]
    reduction = (first["residual"] - min(x["residual"] for x in window)) / max(first["residual"], 1e-30)
    energy_drop = (first["energy"] - min(x["energy"] for x in window)) / max(abs(first["energy"]), 1e-30)
    return reduction < plan["stall_relative_residual_improvement"] and energy_drop < plan["stall_relative_energy_drop"]


def eligible(result):
    gates = basic_gates(result)
    return all(gates[k] for k in ("stationary", "initial_charge", "final_charge", "resolved_cells",
                                  "unit_norm", "virial", "endpoint_cpu_audit", "completed_without_numerical_fault"))


def compare_energy(a, b, kind):
    """A small energy change cannot excuse nonstationarity or mismatched boxes."""
    ca, cb = a["config"], b["config"]
    equal = lambda x, y: abs(x - y) < 1e-12
    if ca["expected_q"] != cb["expected_q"]:
        return {"status": "unresolved", "reason": "different Hopf labels"}
    if kind in ("domain", "ranking") and not equal(ca["h"], cb["h"]):
        return {"status": "unresolved", "reason": "spacing mismatch"}
    if kind in ("mesh", "ranking") and not equal((ca["n"]-1)*ca["h"], (cb["n"]-1)*cb["h"]):
        return {"status": "unresolved", "reason": "box mismatch"}
    if kind == "domain" and not (cb["n"] > ca["n"]):
        return {"status": "unresolved", "reason": "domain is not larger"}
    ea, eb = a["final"]["energy"], b["final"]["energy"]
    delta = abs(eb-ea)/ea
    ready = eligible(a) and eligible(b)
    status = ("pass" if delta < .02 else "fail") if ready else "unresolved"
    if kind == "ranking":
        status = "eligible" if ready else "unresolved"
    return {"status": status, "relative_energy_change": delta,
            "first_energy": ea, "second_energy": eb,
            "reason": "stationary scalar comparison; core topology assessed separately" if ready
                      else "retain trial energies; stationary/audited endpoints required"}


def topology_gate(folder, checkpoint_sha):
    path = folder / "topology.json"
    if not path.exists(): return {"status": "unresolved", "reason": "analysis absent or timed out"}
    try: phase = read(path).get("phases", {}).get("final", {})
    except (OSError, ValueError, AttributeError):
        return {"status": "unresolved", "reason": "incomplete topology output"}
    if phase.get("checkpoint_sha256") != checkpoint_sha:
        return {"status": "unresolved", "reason": "topology checkpoint hash mismatch"}
    targets = phase.get("targets", {})
    details = {}
    for name in ("primary", "secondary"):
        target = targets.get(name, {})
        components = target.get("components_data", [])
        diagrams = components[0].get("diagrams", []) if len(components) == 1 else []
        resolved = (target.get("status") == "closed_components" and target.get("components") == 1
                    and len(diagrams) == 9 and all(d.get("components") == 1 and "jones_A" in d for d in diagrams))
        witness_path = folder / ("cable-witness-" + name + ".json")
        try: witness = read(witness_path) if witness_path.exists() else {}
        except (OSError, ValueError): witness = {}
        details[name] = {"single_component_nine_diagrams": resolved,
                         "consistent_jones": resolved and len({json.dumps(d["jones_A"], sort_keys=True) for d in diagrams}) == 1,
                         "common_diagram_found": witness.get("matched", False)}
    compatible = all(all(v.values()) for v in details.values())
    return {"status": "finite_diagram_candidate_requires_review" if compatible else "unresolved",
            "targets": details, "reason": "stored diagram words/membership require review; random-seed replay is limited; no continuum certificate"}


def summarize(out, state):
    rows = {}; results = {}
    for key, job in state.get("stages", {}).items():
        row = {"execution": job["status"], "passes": len(job.get("attempts", [])),
               "attempts": job.get("attempts", []), "option_index": job.get("option_index", 0)}
        case = out / job.get("directory", "cases/" + key)
        if (case / "result.json").exists() and (case / "manifest.json").exists():
            try:
                r = read(case / "result.json"); m = read(case / "manifest.json")
                artifacts = m["artifacts_sha256"]
                numerical = {p: h for p, h in state["source_sha256"].items() if p.startswith("src/")}
                valid = (m.get("source_unchanged_during_run") and m.get("device_validation", {}).get("passed")
                         and m.get("source_sha256") == numerical
                         and m.get("lock_sha256") == state["source_sha256"]["uv.lock"]
                         and m.get("git_commit") == state["git_commit"]
                         and m.get("initial_checkpoint_sha256") == job.get("input_sha256")
                         and sha(case / "config.json") == job.get("config_sha256")
                         and r["config"] == read(case / "config.json")
                         and {"final.npz", "result.json", "config.json", "history.json"} <= artifacts.keys()
                         and all(sha(case / p) == digest for p, digest in artifacts.items()))
                checkpoint_sha = sha(case / "final.npz")
                row.update(solver_status=r["status"], final=r["final"], gates=basic_gates(r), artifact_audit=bool(valid))
            except (OSError, ValueError, KeyError, TypeError) as error:
                row.update(execution="incomplete_or_invalid_artifacts", audit_error=str(error))
                rows[key] = row
                continue
            if valid and job["status"] in ("stationary", "stationary_with_failed_scalar_gates", "stalled_after_options", "running", "interrupted"):
                results[key] = r
            else: row["execution"] = "audit_or_execution_unresolved"
            analysis = out / "analysis" / case.name
            row["topology"] = topology_gate(analysis, checkpoint_sha)
            scaling = analysis / "scaling.json"
            try: scale = read(scaling) if scaling.exists() else {}
            except (OSError, ValueError): scale = {}
            differences = scale.get("finite_difference_comparisons", [])
            scale_valid = scale.get("checkpoint_sha256") == checkpoint_sha and len(differences) == 2
            row["independent_scaling"] = (("pass" if all(abs(d["normalized_energy_derivative"]) < .05
                 and abs(d["difference_from_e2_minus_e4"]) < .05 for d in differences) else "fail")
                 if scale_valid else "unresolved")
        rows[key] = row
    base = published_case(REFERENCE)
    comparisons = {}
    specifications = [
        ("mesh_129_161", base, results.get("q22-161-polish"), "mesh"),
        ("mesh_161_193", results.get("q22-161-polish"), results.get("q22-193-polish"), "mesh"),
        ("domain_129_161_h012", base, results.get("q22-domain-161"), "domain"),
        ("domain_129_193_h012", base, results.get("q22-domain-193"), "domain"),
        ("domain_161_193_h012", results.get("q22-domain-161"), results.get("q22-domain-193"), "domain"),
        ("domain_161_193_h0096", results.get("q22-161-polish"), results.get("q22-domain-fine-193"), "domain"),
        ("same_mesh_comparator_129", base, results.get("q22-comparison-129"), "ranking"),
        ("same_mesh_comparator_161", results.get("q22-161-polish"), results.get("q22-comparison-161"), "ranking"),
        ("same_mesh_comparator_193", results.get("q22-193-polish"), results.get("q22-comparison-193"), "ranking")]
    for name, a, b, kind in specifications:
        comparisons[name] = compare_energy(a, b, kind) if a and b else {"status": "unresolved", "reason": "missing audited endpoint"}
    report = {"campaign_id": state["campaign_id"], "stages": rows, "comparisons": comparisons,
              "historical_reference": {"case": REFERENCE, "final": base["final"]},
              "disposition": "partial_pending_scientific_review",
              "source_unchanged": state["source_sha256"] == code_hashes(),
              "scope": "Q22 static closure only; no reproduction automatically certified; Q18 retained unchanged",
              "topology_limit": "finite diagrams only; witness inputs/words need review; no deterministic move trace or continuum proof",
              "generated_at": timestamp(), "study_started_at": state.get("started_at"),
              "timestamp_policy": "UTC and Australia/Melbourne ISO 8601; file times cover raw fields/curves/history; elapsed history samples remain unchanged"}
    atomic_json(out / "summary.json", report)
    lines = ["# Checkpointed Q22 convergence study", "", "Generated: " + report["generated_at"]["melbourne"] + " (Melbourne); " + report["generated_at"]["utc"] + " (UTC).", "", report["disposition"], "",
             "| Stage | Execution | Solver | Energy | CPU residual |", "|---|---|---|---:|---:|"]
    for key, row in rows.items():
        f = row.get("final", {})
        lines.append(f"| {key} | {row['execution']} | {row.get('solver_status', '')} | {f.get('energy', '')} | {f.get('cpu_tangent_gradient_rms', '')} |")
    lines += ["", "| Comparison | Status |", "|---|---|"]
    lines += [f"| {name} | {value['status']} |" for name, value in comparisons.items()]
    lines += ["", report["scope"], "", report["topology_limit"],
              "", "Full field checkpoints remain on the workstation. Retain this output directory and its source campaign."]
    (out / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    files = [p for p in out.rglob("*") if p.is_file() and p.name != "evidence-hashes.json"
             and (p.suffix in (".json", ".md", ".log", ".svg")
                  or (p.suffix == ".npz" and p.relative_to(out).parts[0] == "analysis"))]
    atomic_json(out / "evidence-hashes.json", {"generated_at": timestamp(), "files": {
        str(p.relative_to(out)): {"sha256": sha(p), "modified_at": timestamp(p.stat().st_mtime)} for p in files}})
    with zipfile.ZipFile(out / "evidence.zip.tmp", "w", zipfile.ZIP_DEFLATED) as z:
        for p in files + [out / "evidence-hashes.json"]: z.write(p, p.relative_to(out))
    os.replace(out / "evidence.zip.tmp", out / "evidence.zip")
    return report


def endpoint(case):
    """Only complete, independently audited endpoints feed the next pass."""
    result = read(case / "result.json"); manifest = read(case / "manifest.json")
    artifacts = manifest["artifacts_sha256"]
    required = ("initial_charge", "final_charge", "resolved_cells", "unit_norm", "endpoint_cpu_audit")
    if (result["status"] not in ("interrupted", "gradient_stationary", "iteration_budget", "time_budget", "residual_not_stationary")
            or not manifest.get("source_unchanged_during_run")
            or not manifest.get("device_validation", {}).get("passed")
            or not {"final.npz", "result.json", "config.json", "history.json"} <= artifacts.keys()
            or not all(sha(case / p) == h for p, h in artifacts.items())
            or not all(basic_gates(result)[k] for k in required)):
        raise ValueError("Unresolved endpoint audit: " + str(case))
    return result


def analyse(out, state, plan, key):
    job = state["stages"][key]
    case = out / job["directory"]; folder = out / "analysis" / case.name
    refs = out / "analysis" / "references"
    tasks = [("references", [sys.executable, "scripts/static_knot_references.py", "--output", str(refs)]),
             (case.name + "-topology", [sys.executable, "scripts/analyse_static_fields.py", "--case", str(case),
                 "--phases", "final", "--output", str(folder)]),
             (case.name + "-scaling", [sys.executable, "scripts/check_static_scaling.py", "--checkpoint", str(case / "final.npz"), "--output", str(folder)])]
    if not key.startswith("q22-comparison"):
        for target in ("primary", "secondary"):
            tasks.append((case.name + "-witness-" + target, [sys.executable, "scripts/match_static_cable_diagrams.py",
                "--reference", str(refs / "references.json"), "--topology", str(folder / "topology.json"),
                "--target", target, "--output", str(folder / ("cable-witness-" + target + ".json"))]))
    for name, argv in tasks:
        if code_hashes() != state["source_sha256"]: raise ValueError("Source changed during analysis")
        signature = analysis_signature(argv)
        cached = state["analysis"].get(name, {})
        if cached.get("status") == "completed" and cached.get("signature") == signature: continue
        print("ANALYSE", name, flush=True)
        started = timestamp(); log = out / "logs" / (name + "-" + date_tag() + ".log")
        before = {p: sha(p) for folder in (folder, refs) if folder.exists() for p in folder.glob("*.json")}
        outcome = {"status": "interrupted", "returncode": None}
        state["analysis"][name] = {"status": "running", "signature": signature, "started_at": started,
                                    "log": str(log.relative_to(out))}
        atomic_json(out / "campaign.json", state)
        try:
            outcome = execute(argv, log, plan["analysis_job_seconds"])
        finally:
            finished = timestamp()
            for directory in (folder, refs):
                if not directory.exists(): continue
                for path in directory.glob("*.json"):
                    if path in before and sha(path) == before[path]: continue
                    try: data = read(path)
                    except (ValueError, OSError): continue
                    if isinstance(data, dict):
                        data["record_timestamps"] = {"execution_started": started, "execution_finished": finished}
                        atomic_json(path, data)
            state["analysis"][name] = {**outcome, "signature": signature, "started_at": started,
                                        "finished_at": finished, "log": str(log.relative_to(out))}
            state["updated_at"] = timestamp()
            atomic_json(out / "campaign.json", state)


def run(source, output, resume=False):
    receipt = preflight(source)
    out = Path(output).resolve(); old = Path(source).resolve()
    if out.is_relative_to(old) or old.is_relative_to(out):
        raise ValueError("Use a new output tree separate from the original campaign")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("Commit the reviewed run tooling before computation to record clean provenance")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    plan = read(PLAN); validate_plan(plan)
    if not resume: out.mkdir(parents=True, exist_ok=False)
    with (out / "run.lock").open("a") as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError("This study is already running; do not start a second process") from None
        if resume:
            state = read(out / "campaign.json")
            if (state["source_sha256"] != code_hashes() or state["git_commit"] != commit
                    or state["source_inputs"] != receipt or read(out / "plan.json") != plan):
                raise ValueError("Source, plan, commit or original checkpoint provenance changed")
        else:
            for folder in ("cases", "configs", "logs", "analysis"): (out / folder).mkdir()
            state = {"campaign_id": plan["campaign_id"], "started_utc": datetime.now(timezone.utc).isoformat(),
                     "started_at": timestamp(), "overall_wall_seconds": None, "git_commit": commit, "source_sha256": code_hashes(),
                     "source_inputs": receipt, "stages": {}, "analysis": {}}
            atomic_json(out / "plan.json", plan)
        def save():
            state["updated_at"] = timestamp()
            atomic_json(out / "campaign.json", state)
        try:
            state.pop("interrupted", None); save()
            for stage in plan["stages"]:
                key = stage["id"]
                job = state["stages"].setdefault(key, {"status": "not_started", "attempts": [], "option_index": 0, "progress": []})
                if job["status"] in ("stationary", "stationary_with_failed_scalar_gates", "stalled_after_options"):
                    if job.get("directory"): analyse(out, state, plan, key)
                    continue
                if job["status"] in ("numerical_fault", "audit_incomplete", "optional_checkpoint_missing", "dependency_unresolved"):
                    continue
                if stage.get("from"):
                    dependency = state["stages"].get(stage["from"], {})
                    if not dependency.get("directory"):
                        job["status"] = "dependency_unresolved"; save(); continue
                    try: previous = endpoint(out / dependency["directory"])
                    except (OSError, ValueError, KeyError):
                        job["status"] = "dependency_unresolved"; save(); continue
                    checkpoint = out / dependency["directory"] / "final.npz"
                    template = previous["config"]
                else:
                    entry = receipt["inputs"][stage["source_case"]]
                    if entry["status"] != "verified":
                        job["status"] = "optional_checkpoint_missing"; save(); continue
                    checkpoint = Path(entry["path"])
                    template = published_case(stage["source_case"])["config"]
                if job.get("directory"):
                    # An interrupted child normally writes an audited endpoint on SIGINT.
                    # Incomplete rolling fields remain preserved but need explicit review.
                    try: previous = endpoint(out / job["directory"])
                    except (OSError, ValueError, KeyError):
                        job["status"] = "audit_incomplete"; save(); continue
                    checkpoint = out / job["directory"] / "final.npz"
                    if previous["final"]["cpu_tangent_gradient_rms"] < 1e-3:
                        job["status"] = "stationary" if eligible(previous) else "stationary_with_failed_scalar_gates"
                        save(); analyse(out, state, plan, key); summarize(out, state); continue
                while True:
                    if code_hashes() != state["source_sha256"]: raise ValueError("Source changed during study")
                    required_space = 8 * stage["n"]**3 * 3 * 8
                    if shutil.disk_usage(out).free < required_space:
                        job.update(status="disk_space_pause", reason="Free space below eight raw field copies; preserve outputs and free space before --resume")
                        state["interrupted"] = True; save(); break
                    index = len(job["attempts"]) + 1
                    case = out / "cases" / f"{key}-{date_tag()}-pass{index:03d}"
                    config = out / "configs" / (case.name + ".json")
                    length = plan["precondition_lengths"][job["option_index"]]
                    c = prepare_config(stage, template, checkpoint, plan, length); atomic_json(config, c)
                    attempt = {"status": "running", "directory": str(case.relative_to(out)),
                               "input_sha256": sha(checkpoint), "config_sha256": sha(config), "precondition_length": length,
                               "started_at": timestamp()}
                    job["attempts"].append(attempt); job.update(attempt); job["status"] = "running"; save()
                    print("RUN", case.name, "precondition length", length, "checkpoint interval", c["seconds"], "s; no overall time cap", flush=True)
                    argv = [sys.executable, "-m", "electron_field_topology.sf_relax", "--backend", "gpu",
                            "--config", str(config), "--output", str(case)]
                    began = time.monotonic()
                    outcome = execute(argv, out / "logs" / (case.name + ".log"), c["seconds"] + plan["audit_grace_seconds"])
                    attempt.update(outcome, wall_seconds=time.monotonic() - began, finished_at=timestamp())
                    if case.exists(): stamp_case(case, attempt["started_at"], attempt["finished_at"])
                    save()
                    try: result = endpoint(case)
                    except (OSError, ValueError, KeyError) as error:
                        job.update(status="audit_incomplete", reason=str(error)); save(); break
                    if result["status"] == "interrupted":
                        job["status"] = "interrupted"; state["interrupted"] = True; save(); break
                    if outcome["status"] != "completed":
                        job["status"] = "numerical_fault"; save(); break
                    f = result["final"]; residual = f["cpu_tangent_gradient_rms"]
                    attempt.update(solver_status=result["status"], energy=f["energy"], residual=residual)
                    job["progress"].append({"energy": f["energy"], "residual": residual, "recorded_at": timestamp()})
                    if residual < 1e-3:
                        job["status"] = "stationary" if eligible(result) else "stationary_with_failed_scalar_gates"
                    elif stalled(job["progress"], plan):
                        if job["option_index"] + 1 < len(plan["precondition_lengths"]):
                            job["option_index"] += 1; job["progress"] = []
                            print("STALLED", key, "trying next recorded optimiser length", flush=True)
                        else: job["status"] = "stalled_after_options"
                    checkpoint = case / "final.npz"
                    save(); summarize(out, state)
                    if job["status"] != "running": break
                if job.get("directory") and (out / job["directory"] / "final.npz").exists():
                    analyse(out, state, plan, key)
                summarize(out, state)
                if state.get("interrupted"): break
        except KeyboardInterrupt:
            state["interrupted"] = True
            for job in state["stages"].values():
                if job["status"] == "running":
                    job["status"] = "interrupted"
                    if job.get("directory"):
                        case = out / job["directory"]
                        if case.exists(): stamp_case(case, job["started_at"], timestamp())
        except Exception as error:
            state["error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        finally:
            for stage in plan["stages"]:
                state["stages"].setdefault(stage["id"], {"status": "not_started", "attempts": [], "option_index": 0, "progress": []})
            save(); summarize(out, state)
            print("SUMMARY", out / "SUMMARY.md", "EVIDENCE", out / "evidence.zip", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-campaign", type=Path, default=DEFAULT_SOURCE)
    p.add_argument("--output", type=Path)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="Verify original field hashes; no solver run")
    mode.add_argument("--collect", action="store_true", help="Rebuild evidence only; no solver run")
    mode.add_argument("--resume", action="store_true", help="Continue the same study from audited pass endpoints")
    a = p.parse_args()
    os.environ["OMP_NUM_THREADS"] = "12"; os.environ["OPENBLAS_NUM_THREADS"] = "1"
    if a.preflight:
        print(json.dumps({"verified_at": timestamp(), **preflight(a.source_campaign)}, indent=2)); return
    if not a.output: p.error("--output is required for a run or collection")
    if a.collect:
        with (a.output / "run.lock").open("a") as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: p.error("Study is running; use its current evidence snapshot")
            summarize(a.output.resolve(), read(a.output / "campaign.json"))
        return
    run(a.source_campaign, a.output, a.resume)


if __name__ == "__main__": main()
