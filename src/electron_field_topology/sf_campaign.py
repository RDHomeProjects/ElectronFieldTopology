"""Bounded, restartable GPU continuation plus evidence collection. Apache-2.0."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile
from .sf_checkpoints import atomic_json, sha
from .sf_relax import validate

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT/"experiments/configs/sf-j2015"
PLAN = CONFIGS/"gpu-continuation.json"


def read(path):
    return json.loads(Path(path).read_text())


def analysis_signature(argv):
    inputs = {}
    for flag in ("--case", "--checkpoint", "--reference", "--topology"):
        if flag not in argv: continue
        path = Path(argv[argv.index(flag)+1])
        paths = [path/"config.json", path/"initial.npz", path/"final.npz"] if flag == "--case" else [path]
        for p in paths:
            inputs[str(p)] = sha(p) if p.is_file() else None
    return hashlib.sha256(json.dumps({"argv": argv, "inputs": inputs}, sort_keys=True).encode()).hexdigest()


def basic_gates(result):
    c, a, b = result["config"], result["initial"], result["final"]
    q = c["expected_q"]
    return {"initial_charge": abs(abs(a["hopf_integral"])-q)/q <= .05,
            "final_charge": abs(abs(b["hopf_integral"])-q)/q <= .05,
            "resolved_cells": min(a["minimum_corner_cone"], b["minimum_corner_cone"]) > 0,
            "unit_norm": b["unit_error"] < 1e-12,
            "stationary": b.get("cpu_tangent_gradient_rms", b["tangent_gradient_rms"]) < 1e-3,
            "virial": b["virial_residual"] is not None and b["virial_residual"] < .05,
            "source_energy": (abs(b["energy"]-c["published_energy"])/c["published_energy"] < .03) if "published_energy" in c else True,
            "endpoint_cpu_audit": bool(b.get("cpu_endpoint_audit")),
            "completed_without_numerical_fault": result["status"] in ("gradient_stationary", "iteration_budget", "time_budget", "residual_not_stationary")}


def execute(argv, log, seconds):
    """No shell; logs survive subprocess failure and bounded analysis timeouts."""
    with Path(log).open("w") as f:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        deadline = time.monotonic()+max(1, seconds)
        try:
            while True:
                left = deadline-time.monotonic()
                if left <= 0: raise subprocess.TimeoutExpired(argv, seconds)
                try:
                    code = process.wait(timeout=min(30, left)); break
                except subprocess.TimeoutExpired:
                    print("WORKING", Path(log).stem, "remaining", round(max(0, deadline-time.monotonic())), "s", flush=True)
            return {"returncode": code, "status": "completed" if code == 0 else "failed"}
        except subprocess.TimeoutExpired:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            return {"returncode": None, "status": "timeout"}
        except KeyboardInterrupt:
            # The terminal also delivers SIGINT to the child. Give it time to
            # save the accepted field rather than sending a second interrupt.
            try: process.wait(timeout=30)
            except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=10)
            raise


def bundle(out, state):
    """Small replay evidence ZIP; bulk float64 fields remain on the workstation."""
    domain_limit = read(out/"plan.json").get("domain_relative_energy_limit", .02) if (out/"plan.json").exists() else .02
    summary = {"campaign_id": state["campaign_id"], "stages": {}, "analysis": state.get("analysis", {}),
               "reproduction_status": "not_certified: review every gate and unresolved result",
               "fields_location": str(out.resolve()), "scope": "checkpointed local computation; no automatic scientific acceptance"}
    for key, job in state["stages"].items():
        row = {"status": job["status"], "directory": job.get("directory"), "alias": job.get("alias")}
        path = Path(job["directory"])/"result.json" if job.get("directory") else None
        if path and path.exists():
            r = read(path); row.update(final=r["final"], initial=r["initial"], config=r["config"], gates=basic_gates(r))
        analysis_dir = out/"analysis"/Path(job["directory"]).name if job.get("directory") else out/"analysis"/key
        topology = analysis_dir/"topology.json"
        if topology.exists():
            targets = read(topology).get("phases", {}).get("final", {}).get("targets", {})
            resolution = {}
            for target, data in targets.items():
                components = data.get("components_data", [])
                diagrams = components[0].get("diagrams", []) if len(components) == 1 else []
                resolved = (data.get("status") == "closed_components" and data.get("components") == 1
                            and len(diagrams) == 9 and all(d.get("components") == 1 and "jones_A" in d for d in diagrams))
                resolution[target] = {"all_nine_diagrams_resolved": resolved,
                    "consistent_jones": resolved and len({json.dumps(d["jones_A"], sort_keys=True) for d in diagrams}) == 1,
                    "all_match_hyperbolic_10_139": resolved and all(d.get("matches_10_139") for d in diagrams),
                    "components": data.get("components")}
                witness = analysis_dir/f"cable-witness-{target}.json"
                if witness.exists(): resolution[target]["finite_cable_witness"] = read(witness).get("matched", False)
            row["topology_checks"] = resolution
        scaling = analysis_dir/"scaling.json"
        if scaling.exists():
            scale = read(scaling); differences = scale.get("finite_difference_comparisons", [])
            row["independent_scaling_gate"] = bool(differences) and all(
                abs(d["normalized_energy_derivative"]) < .05 and abs(d["difference_from_e2_minus_e4"]) < .05 for d in differences)
        summary["stages"][key] = row
    for q, meshes, domain in [(22, ["q22-129-cont", "q22-161", "q22-193"], "q22-domain"),
                              (18, ["q18-97", "q18-129", "q18-193"], "q18-domain")]:
        values = [summary["stages"].get(k, {}).get("final", {}).get("energy") for k in meshes]
        mesh = [abs(b-a)/b for a, b in zip(values, values[1:])] if all(v is not None for v in values) else None
        base = summary["stages"].get("q22-129-cont" if q == 22 else "q18-129", {}).get("final", {}).get("energy")
        other = summary["stages"].get(domain, {}).get("final", {}).get("energy")
        summary[f"q{q}_convergence"] = {"meshes": meshes, "successive_energy_changes": mesh,
            "mesh_energy_gate": all(x < .02 for x in mesh) if mesh is not None else None,
            "domain_energy_change": abs(other-base)/base if base and other else None,
            "domain_energy_gate": abs(other-base)/base < domain_limit if base and other else None,
            "scope": "energy convergence alone does not establish consistent core topology"}
    summary["same_charge_comparisons"] = {}
    for q, target in [(22, "q22-193"), (18, "q18-193")]:
        a = summary["stages"].get(target, {}); b = summary["stages"].get(f"q{q}-comparison", {})
        # Rankings require equal meshes; retain the coarse target comparison separately.
        target = "q22-129-cont" if q == 22 else "q18-129"
        a = summary["stages"].get(target, {})
        summary["same_charge_comparisons"][str(q)] = {"target_stage": target, "comparator_stage": f"q{q}-comparison",
            "target_energy": a.get("final", {}).get("energy"), "comparator_energy": b.get("final", {}).get("energy"),
            "ranking_eligible": bool(a.get("gates", {}).get("stationary") and b.get("gates", {}).get("stationary")
                                     and a.get("gates", {}).get("final_charge") and b.get("gates", {}).get("final_charge")),
            "scope": "same-Q same-mesh stationary comparisons; topology separately identified"}
    atomic_json(out/"summary.json", summary)
    lines = ["# GPU continuation summary", "", "No reproduction is automatically certified.", "",
             "| Stage | Status | Energy | CPU residual | Hopf integral |", "|---|---|---:|---:|---:|"]
    for key, row in summary["stages"].items():
        b = row.get("final", {})
        lines.append(f"| {key} | {row['status']} | {b.get('energy', '')} | {b.get('cpu_tangent_gradient_rms', '')} | {b.get('hopf_integral', '')} |")
    (out/"SUMMARY.md").write_text("\n".join(lines)+"\n")
    files = [p for p in out.rglob("*") if p.is_file() and p.name != "evidence-hashes.json"
             and (p.suffix in (".json", ".md", ".log", ".svg")
                  or (p.suffix == ".npz" and p.relative_to(out).parts[0] == "analysis"))]
    manifest = {str(p.relative_to(out)): sha(p) for p in files}
    atomic_json(out/"evidence-hashes.json", manifest)
    with zipfile.ZipFile(out/"evidence.zip.tmp", "w", zipfile.ZIP_DEFLATED) as z:
        for p in files+[out/"evidence-hashes.json"]:
            z.write(p, p.relative_to(out))
    os.replace(out/"evidence.zip.tmp", out/"evidence.zip")
    return summary


def run(out, resume=False, plan_path=PLAN, skip_analysis=False):
    plan = read(plan_path); out = Path(out).resolve()
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT/"src").rglob("*")) if p.suffix in (".py", ".c", ".cu")}
    hashes.update({str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT/"scripts").glob("*.py"))})
    hashes.update({str(p.relative_to(ROOT)): sha(p) for p in sorted(CONFIGS.glob("*.json"))})
    hashes["uv.lock"] = sha(ROOT/"uv.lock")
    if resume:
        state = read(out/"campaign.json")
        if state["plan_sha256"] != sha(plan_path) or state["source_sha256"] != hashes:
            raise ValueError("Campaign code/plan changed; preserve old campaign and use a new bounded directory")
    else:
        out.mkdir(parents=True, exist_ok=False)
        state = {"campaign_id": plan["campaign_id"], "started_epoch": time.time(),
                 "started_utc": datetime.now(timezone.utc).isoformat(), "plan_sha256": sha(plan_path),
                 "source_sha256": hashes, "stages": {}, "analysis": {}}
        atomic_json(out/"plan.json", plan)
    for directory in ("cases", "configs", "analysis", "logs"):
        (out/directory).mkdir(exist_ok=True)
    def save():
        atomic_json(out/"campaign.json", state)
    def remaining(analysis=False):
        reserve = 0 if analysis else plan["analysis_reserve_seconds"]
        return plan["wall_seconds"]-reserve-(time.time()-state["started_epoch"])
    def result_path(name):
        job = state["stages"].get(name, {})
        return Path(job["directory"]) if job.get("directory") else None
    try:
        save()
        # Dependency stages are ordered in the frozen plan; failed numerical gates are retained.
        for stage in plan["stages"]:
            key = stage["id"]; old = state["stages"].get(key, {})
            if any(sha(ROOT/p) != h for p, h in hashes.items()):
                raise ValueError("Campaign source/configuration changed during execution")
            old_dir = Path(old["directory"]) if old.get("directory") else None
            if old_dir and (old_dir/"result.json").exists():
                manifest = read(old_dir/"manifest.json")
                if not manifest.get("source_unchanged_during_run"):
                    raise ValueError("Cached stage source audit failed")
                for name, digest in manifest["artifacts_sha256"].items():
                    if sha(old_dir/name) != digest: raise ValueError("Cached artifact hash mismatch: "+name)
                r = read(old_dir/"result.json")
                if r["status"] != "interrupted" and not old.get("alias"): old["status"] = "completed"; save()
            if old.get("status") in ("completed", "alias"):
                continue
            if key not in ("q1-control", "q2-control"):
                controls = [result_path(k) for k in ("q1-control", "q2-control")]
                if not all(p and (p/"result.json").exists() and all(basic_gates(read(p/"result.json")).values()) for p in controls):
                    state["stages"][key] = {"status": "skipped_control_failure"}; save(); continue
            if remaining() < 30:
                state["stages"][key] = {"status": "campaign_budget"}; save(); continue
            source_dir = result_path(stage.get("from"))
            if stage.get("from") and (not source_dir or not (source_dir/"final.npz").exists()):
                state["stages"][key] = {"status": "blocked", "reason": "Missing dependency field"}; save(); continue
            if source_dir:
                if not (source_dir/"result.json").exists():
                    state["stages"][key] = {"status": "blocked", "reason": "Dependency lacks endpoint audit"}; save(); continue
                gates = basic_gates(read(source_dir/"result.json"))
                required = ("initial_charge", "final_charge", "resolved_cells", "unit_norm", "endpoint_cpu_audit", "completed_without_numerical_fault")
                if not all(gates[k] for k in required):
                    state["stages"][key] = {"status": "blocked", "reason": "Dependency resolution/audit failed"}; save(); continue
            if stage.get("skip_if_source_stationary") and all(basic_gates(read(source_dir/"result.json")).values()):
                state["stages"][key] = {"status": "alias", "directory": str(source_dir), "alias": stage["from"]}; save(); continue
            config = read(CONFIGS/stage["config"]); config.pop("initial_checkpoint", None)
            for name in ("n", "h", "iterations", "seconds"):
                if name in stage: config[name] = stage[name]
            config["case"] = key; config["seconds"] = max(1, min(config["seconds"], int(remaining())))
            if source_dir: config["initial_checkpoint"] = str(source_dir/"final.npz")
            # Only this campaign's same-stage checkpoint may resume an interrupted job.
            attempts = int(old.get("attempts", 0))+1
            latest = None
            if old.get("directory"):
                for name in ("latest.npz", "previous.npz", "initial.npz"):
                    path = Path(old["directory"])/name
                    if path.exists():
                        from .sf_checkpoints import load_field
                        try: load_field(path, config["n"], config["h"], config["expected_q"])
                        except (ValueError, OSError, zipfile.BadZipFile, EOFError): continue
                        latest = path; break
            validate(config); cfg = out/"configs"/f"{key}-{attempts}.json"; atomic_json(cfg, config)
            case = out/"cases"/f"{key}-{attempts}"
            job = {"status": "running", "directory": str(case), "attempts": attempts,
                   "config_sha256": sha(cfg), "resume_checkpoint": str(latest) if latest else None}
            state["stages"][key] = job; save(); print("RUN", key, config["n"], "budget", config["seconds"], flush=True)
            argv = [sys.executable, "-m", "electron_field_topology.sf_relax", "--backend", "gpu",
                    "--config", str(cfg), "--output", str(case)]
            if latest: argv += ["--resume-checkpoint", str(latest)]
            started = time.monotonic()
            outcome = execute(argv, out/"logs"/f"{key}-{attempts}.log", min(config["seconds"]+90, remaining(True)))
            job.update(outcome, wall_seconds=time.monotonic()-started)
            if (case/"result.json").exists():
                result = read(case/"result.json"); job["solver_status"] = result["status"]
                if result["status"] == "interrupted": job["status"] = "interrupted"; save(); break
            save(); bundle(out, state)
        if not skip_analysis:
            references = out/"analysis"/"references"
            tasks = [("references", [sys.executable, "scripts/static_knot_references.py", "--output", str(references)])]
            for key in state["stages"]:
                source = result_path(key)
                if not source or not (source/"final.npz").exists() or key.endswith("control") or state["stages"][key].get("alias"):
                    continue
                target = out/"analysis"/source.name
                tasks += [(key+"-topology", [sys.executable, "scripts/analyse_static_fields.py", "--case", str(source), "--output", str(target)]),
                          (key+"-scaling", [sys.executable, "scripts/check_static_scaling.py", "--checkpoint", str(source/"final.npz"), "--output", str(target)])]
                if key.startswith("q22") and key != "q22-comparison":
                    for name in ("primary", "secondary"):
                        tasks.append((key+"-witness-"+name, [sys.executable, "scripts/match_static_cable_diagrams.py",
                            "--reference", str(references/"references.json"), "--topology", str(target/"topology.json"),
                            "--target", name, "--output", str(target/f"cable-witness-{name}.json")]))
            for name, argv in tasks:
                signature = analysis_signature(argv)
                cached = state["analysis"].get(name, {})
                if cached.get("status") == "completed" and cached.get("signature") == signature: continue
                if remaining(True) < 5: state["analysis"][name] = {"status": "campaign_budget"}; continue
                print("ANALYSE", name, flush=True)
                state["analysis"][name] = execute(argv, out/"logs"/(name+".log"), min(plan["analysis_job_seconds"], remaining(True)))
                state["analysis"][name]["signature"] = signature
                save()
    except KeyboardInterrupt:
        state["interrupted"] = True; save()
    finally:
        save(); summary = bundle(out, state)
        print("SUMMARY", out/"SUMMARY.md", "EVIDENCE", out/"evidence.zip", flush=True)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--output", required=True)
    p.add_argument("--resume", action="store_true"); p.add_argument("--skip-analysis", action="store_true")
    a = p.parse_args()
    os.environ['OMP_NUM_THREADS'] = '12'; os.environ['OPENBLAS_NUM_THREADS'] = '1'
    run(a.output, a.resume, skip_analysis=a.skip_analysis)


if __name__ == "__main__": main()
