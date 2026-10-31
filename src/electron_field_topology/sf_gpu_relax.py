"""Checkpointed GPU static relaxation with independent CPU endpoint audits.

No physical-time evolution or automatic reproduction claim. Apache-2.0.
"""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import numpy as np
from .sf_checkpoints import atomic_json, checkpoint, load_field, sha
from .sf_relax import validate
from .sf_gpu import cupy_module, GPUEnergy, minimize_array, diagnostics_array
from .sf_gpu_timing import make_seed, agreement, validate_device
from .sf_timing import hardware
from .skyrme import Energy, K, NORTH, diagnostics


def run(config, output, resume_checkpoint=None, _runtime=None):
    c = json.loads(Path(config).read_text()); validate(c)
    if c.get("solver") != "sobolev_cg" or c.get("discretisation") != "cell":
        raise ValueError("GPU continuation requires the validated cell/Sobolev-CG method")
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    atomic_json(out/"config.json", c); config_sha = sha(out/"config.json")
    root = Path(__file__).resolve().parents[2]
    sources = lambda: {str(p.relative_to(root)): sha(p) for p in sorted((root/"src").rglob("*"))
                       if p.suffix in (".py", ".c", ".cu")}
    source_hashes = sources()
    manifest = {"model_id": "SF-J2015-static", "backend": "cuda-float64" if _runtime is None else "host-test-double",
                "source_sha256": source_hashes, "config_sha256": config_sha,
                "lock_sha256": sha(root/"uv.lock"), "hardware": hardware(),
                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "dirty_tree": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()),
                "versions": {k: importlib.metadata.version(k) for k in ("numpy", "scipy")},
                "strict_accepted_margin": True, "checkpoint_dtype": "float64",
                "cuda_compile_options": ["--std=c++11", "--fmad=false"],
                "cpu_audit_compiler": subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0],
                "threads": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")},
                "resume_scope": "field continuation; conjugate-gradient directions restart"}
    atomic_json(out/"manifest.json", manifest)
    start = time.monotonic(); history = []; last = None; iteration = 0; evaluations = 0
    try:
        if _runtime is None:
            xp = cupy_module(); device = xp.cuda.Device(); manifest["cupy"] = xp.__version__
            manifest["cuda_device"] = device.id; manifest["compute_capability"] = device.compute_capability
            manifest["cuda_runtime"] = xp.cuda.runtime.runtimeGetVersion()
            manifest["cuda_driver"] = xp.cuda.runtime.driverGetVersion()
            with tempfile.TemporaryDirectory(prefix="eft-device-check-") as build:
                manifest["device_validation"] = validate_device(xp, build)
            factory = GPUEnergy; to_host = xp.asnumpy
        else:
            xp, factory = _runtime; to_host = np.asarray
            manifest["device_validation"] = {"passed": False, "scope": "CPU test double only"}
        atomic_json(out/"manifest.json", manifest)
        n, h, q = c["n"], c["h"], c["expected_q"]
        source = resume_checkpoint or c.get("initial_checkpoint")
        if source:
            u = load_field(source, n, h, q)
            manifest["initial_checkpoint"] = str(Path(source).resolve())
            manifest["initial_checkpoint_sha256"] = sha(source)
        else:
            seed = {"n": n, "h": h, "seed": c["seed"],
                    "perturbation_amplitude": c.get("perturbation_amplitude", 0),
                    "perturbation_seed": c.get("perturbation_seed", 35)}
            u = make_seed(seed)
        eng = factory(n, h); cpu = Energy(n, h, out/"native")
        last = xp.asarray(u); previous = last; previous_margin = None; last_saved = start
        def row(field, index, audit=False):
            p, g = eng.evaluate(field)
            tangent = g-field*xp.sum(g*field, axis=-1, keepdims=True)
            residual = float(xp.sqrt(xp.mean(tangent[2:-2, 2:-2, 2:-2]**2))/(K*h**3))
            diag = diagnostics_array(field, h, xp)
            rec = {"iteration": index, "elapsed_seconds": time.monotonic()-start,
                   "e2": float(p[0]), "e4": float(p[1]), "energy": float(sum(p)),
                   "virial_residual": float(abs(p[0]-p[1])/sum(p)) if float(sum(p)) else None,
                   "tangent_gradient_rms": residual, "minimum_corner_cone": eng.minimum_corner_cone,
                   "minimum_quadrature_interpolant_norm": eng.minimum_interpolant_norm, **diag}
            if audit:
                host = to_host(field); pc, gc = cpu.evaluate(host); checks = {}
                agreement("endpoint_energy", to_host(p), pc, checks)
                agreement("endpoint_gradient", to_host(g), gc, checks)
                dc = diagnostics(host, h)
                agreement("endpoint_hopf", diag["hopf_integral"], dc["hopf_integral"], checks, rtol=1e-9, atol=1e-10)
                tc = gc-host*np.sum(gc*host, axis=-1, keepdims=True)
                rec["cpu_tangent_gradient_rms"] = float(np.sqrt(np.mean(tc[2:-2, 2:-2, 2:-2]**2))/(K*h**3))
                rec["cpu_endpoint_audit"] = checks
                if abs(rec["cpu_tangent_gradient_rms"]-residual) > 1e-9*max(1., residual):
                    raise ValueError("Independent final residual mismatch")
                for axis in range(3):
                    sl = [slice(None)]*4; sl[axis] = [0, 1, n-2, n-1]
                    if np.max(abs(host[tuple(sl)]-NORTH)) > 1e-12:
                        raise ValueError("Fixed boundary changed")
            history.append(rec); atomic_json(out/"history.json", history)
            print(json.dumps(rec), flush=True)
            return rec
        initial = row(last, 0, audit=True)
        checkpoint(out/"initial.npz", to_host(last), h, q, 0, time.monotonic()-start, config_sha)
        checkpoint(out/"latest.npz", to_host(last), h, q, 0, time.monotonic()-start, config_sha)
        previous_margin = eng.minimum_corner_cone
        status = "iteration_budget"; message = "Bounded GPU continuation"
        if abs(abs(initial["hopf_integral"])-q)/q > .05 or initial["minimum_corner_cone"] <= 0:
            status = "initial_charge_unresolved"
        else:
            def callback(field, index):
                nonlocal last, previous, previous_margin, iteration, last_saved
                step = float(xp.max(xp.linalg.norm(field-previous, axis=-1)))
                if step > min(.2, .5*previous_margin)+1e-14:
                    raise ValueError("Accepted-step continuity guard rejected; previous accepted field retained")
                last = field; previous = field; previous_margin = eng.minimum_corner_cone; iteration = index
                if index % c.get("record_every", 50) == 0 or time.monotonic()-last_saved >= 60:
                    checkpoint(out/"latest.npz", to_host(last), h, q, index, time.monotonic()-start, config_sha)
                    rec = row(last, index); last_saved = time.monotonic()
                    if index in (200, 500):
                        checkpoint(out/f"iteration-{index}.npz", to_host(last), h, q, index, time.monotonic()-start, config_sha)
                    if abs(abs(rec["hopf_integral"])-q)/q > .10:
                        raise RuntimeError("charge_resolution_lost")
            try:
                last, result = minimize_array(eng, last, c["iterations"], callback,
                    lambda: time.monotonic()-start >= c["seconds"], xp,
                    length=c.get("precondition_length", .5), strict_continuity=True)
                status = result["status"]; evaluations = result["evaluations"]
            except KeyboardInterrupt:
                status = "interrupted"; message = "Interrupted; accepted field preserved"; evaluations = None
            except (ValueError, RuntimeError) as error:
                status = "charge_resolution_lost" if str(error) == "charge_resolution_lost" else "numerical_rejected"
                message = str(error)
                evaluations = None
        # Preserve the accepted field before potentially expensive independent audits.
        checkpoint(out/"latest.npz", to_host(last), h, q, iteration, time.monotonic()-start, config_sha)
        checkpoint(out/"final.npz", to_host(last), h, q, iteration, time.monotonic()-start, config_sha)
        final = row(last, iteration, audit=True)
        if status == "gradient_stationary" and final["cpu_tangent_gradient_rms"] >= 1e-3:
            status = "residual_not_stationary"
        report = {"status": status, "message": message, "config": c, "initial": initial, "final": final,
                  "iterations": iteration, "evaluations": evaluations, "elapsed_seconds": time.monotonic()-start,
                  "history": history, "reproduction_status": "not_certified: remaining topology, scaling and convergence gates",
                  "scope": "static unit-vector minimisation; no physical time or electric charge"}
        manifest["source_unchanged_during_run"] = source_hashes == sources()
        if not manifest["source_unchanged_during_run"]:
            report["status"] = "source_changed"
        atomic_json(out/"result.json", report)
        manifest["artifacts_sha256"] = {p.name: sha(p) for p in out.iterdir() if p.is_file() and p.name != "manifest.json"}
        atomic_json(out/"manifest.json", manifest); print("FINAL", status, flush=True)
        return report
    except BaseException as error:
        # An existing latest/previous pair survives setup/audit faults or a second interrupt.
        atomic_json(out/"error.json", {"type": type(error).__name__, "message": str(error),
                    "iteration": iteration, "elapsed_seconds": time.monotonic()-start})
        raise
