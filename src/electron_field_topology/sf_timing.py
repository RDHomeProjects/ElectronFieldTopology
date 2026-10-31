"""Bounded CPU timing of the unchanged SF-J2015 instruments (Apache-2.0).

No GPU backend, convergence test or physical-time evolution. Each grid/thread
pair runs in a fresh process so OpenMP sees its settings before library loading.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ["src/electron_field_topology/" + name for name in
           ("sf_timing.py", "sf_energy.c", "skyrme.py", "sf_minimize.py")]
THREAD_ENV = {"OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
              "OMP_DYNAMIC": "FALSE", "OMP_PROC_BIND": "FALSE",
              "OMP_THREAD_LIMIT": "64", "OMP_MAX_ACTIVE_LEVELS": "1",
              "NUMEXPR_NUM_THREADS": "1"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(*args):
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL, timeout=10).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def hardware():
    def read(path):
        try:
            return Path(path).read_text().strip()
        except OSError:
            return None
    info = read("/proc/cpuinfo") or ""
    cpu = next((line.split(":", 1)[1].strip() for line in info.splitlines()
                if line.startswith("model name")), platform.processor())
    memory = read("/proc/meminfo") or ""
    return {"platform": platform.platform(), "cpu_model": cpu,
            "logical_cpus": os.cpu_count(),
            "affinity_cpus": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
            "memory": [line for line in memory.splitlines()
                       if line.startswith(("MemTotal:", "MemAvailable:", "SwapTotal:"))],
            "cgroup_cpu_max": read("/sys/fs/cgroup/cpu.max"),
            "cgroup_memory_max": read("/sys/fs/cgroup/memory.max"),
            "gpu_inventory_only": command("nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                                          "--format=csv,noheader"),
            "load_average": list(os.getloadavg())}


def workload(case, n):
    if case == "q1":
        return {"case": case, "n": n, "h": 8 / (n - 1),
                "seed": {"kind": "axial", "alpha": 1, "beta": 1,
                         "scale": 1., "cutoff": 3.6},
                "perturbation_amplitude": 0., "perturbation_seed": 35}
    config_name = "q18-97.json" if case == "q18" else "q22-129.json"
    c = json.loads((ROOT / "experiments/configs/sf-j2015" / config_name).read_text())
    return {"case": case, "n": n, "h": 15.36 / (n - 1), "seed": c["seed"],
            "perturbation_amplitude": c["perturbation_amplitude"],
            "perturbation_seed": c["perturbation_seed"]}


def measured(function, repeats):
    times = []
    value = None
    for _ in range(repeats):
        start = time.perf_counter()
        value = function()
        times.append(time.perf_counter() - start)
    return {"samples_seconds": times, "median_seconds": statistics.median(times),
            "minimum_seconds": min(times), "maximum_seconds": max(times)}, value


def worker(args):
    # Imports deliberately follow process startup and thread-environment setup.
    import numpy as np
    from .skyrme import Energy, K, coordinates, rational_field, set_boundary, normalize, diagnostics
    from .sf_minimize import minimize_static

    c = workload(args.case, args.grids[0])
    n, h = c["n"], c["h"]
    xyz = coordinates(n, h)
    u = set_boundary(rational_field(xyz, **c["seed"]))
    if c["perturbation_amplitude"]:
        rng = np.random.default_rng(c["perturbation_seed"])
        noise = np.zeros_like(u)
        for _ in range(8):
            wave = rng.normal(size=3)
            phase = rng.uniform(-np.pi, np.pi)
            polar = rng.normal(size=3)
            noise += np.sin(xyz @ wave + phase)[..., None] * polar
        noise *= np.exp(-(np.linalg.norm(xyz, axis=-1) / 5)**4)[..., None]
        noise /= max(float(np.max(np.linalg.norm(noise, axis=-1))), 1e-15)
        u = set_boundary(normalize(u + c["perturbation_amplitude"] * noise))
    del xyz
    with tempfile.TemporaryDirectory(prefix="eft-timing-") as build:
        start = time.perf_counter()
        eng = Energy(n, h, build, method="cell")
        build_seconds = time.perf_counter() - start
        parts, g = eng.evaluate(u)  # Compile and warm-up excluded from samples.
        if eng.minimum_corner_cone <= 0:
            raise ValueError("Unresolved seed: increase grid; no relaxation timing accepted")
        initial_cone = eng.minimum_corner_cone
        energy0 = float(sum(parts))
        tangent = g - u * np.sum(u * g, axis=-1, keepdims=True)
        gradient0 = float(np.sqrt(np.mean(tangent[2:-2, 2:-2, 2:-2]**2)) / (K*h**3))
        del g, tangent
        evaluation, _ = measured(lambda: eng.evaluate(u), args.repeats)
        diagnostics(u, h)  # Warm transform plans/caches, without saving fields.
        diagnostic, diag = measured(lambda: diagnostics(u, h), args.repeats)
        if abs(abs(diag["hopf_integral"]) - int(args.case[1:])) / int(args.case[1:]) > .05:
            raise ValueError("Unresolved seed Hopf integral; increase grid")

        def solve():
            return minimize_static(eng, u, args.steps, lambda field, iteration: None,
                                   lambda: False, length=.5)

        solve()  # Optimiser warm-up; every measured solve restarts from u.
        solver_times, endpoints, solvers = [], [], []
        for _ in range(args.repeats):
            start = time.perf_counter()
            final, result = solve()
            solver_times.append(time.perf_counter() - start)
            endpoints.append(float(sum(eng.evaluate(final)[0])))
            solvers.append(result)
            if result["iterations"] != args.steps or result["status"] != "iteration_budget":
                raise ValueError("Short solve stopped early; not a fixed-work timing")
        if max(endpoints) - min(endpoints) > 1e-10 * max(1., abs(endpoints[0])):
            raise ValueError("Repeated solve energies disagree")
        row = {"workload": c, "threads": args.threads[0], "steps": args.steps,
               "repeats": args.repeats, "backend": "CPU float64 cell/OpenMP + SciPy DST",
               "initial_field_sha256": hashlib.sha256(u.tobytes()).hexdigest(),
               "initial_energy": energy0, "initial_gradient_rms": gradient0,
               "initial_diagnostics": diag, "initial_minimum_corner_cone": initial_cone,
               "build_seconds_excluded": build_seconds,
               "energy_gradient": evaluation, "hopf_diagnostics": diagnostic,
               "short_solve": {"samples_seconds": solver_times,
                               "median_seconds": statistics.median(solver_times),
                               "seconds_per_step": statistics.median(solver_times) / args.steps,
                               "results": solvers, "final_energies": endpoints},
               "worker_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
               "thread_environment": {k: os.environ.get(k) for k in ["OMP_NUM_THREADS", *THREAD_ENV]}}
    Path(args.output).write_text(json.dumps(row, indent=2, allow_nan=False) + "\n")


def compare(report, baseline):
    """Only provide ratios for matching work, code, dependencies and numerics."""
    comparisons = []
    same_code = report["source_sha256"] == baseline.get("source_sha256")
    same_lock = report["lock_sha256"] == baseline.get("lock_sha256")
    same_versions = report["versions"] == baseline.get("versions")
    for row in report["cases"]:
        for old in baseline.get("cases", []):
            if (row["workload"], row["threads"], row["steps"], row["repeats"]) != (
                    old["workload"], old["threads"], old["steps"], old["repeats"]):
                continue
            numeric = (row["short_solve"]["results"] == old["short_solve"]["results"]
                       and all(math.isclose(row[k], old[k], rel_tol=1e-9, abs_tol=1e-12)
                               for k in ("initial_energy", "initial_gradient_rms"))
                       and math.isclose(row["initial_diagnostics"]["hopf_integral"],
                                        old["initial_diagnostics"]["hopf_integral"],
                                        rel_tol=1e-9, abs_tol=1e-10)
                       and all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
                               for a, b in zip(row["short_solve"]["final_energies"],
                                               old["short_solve"]["final_energies"])))
            valid = same_code and same_lock and same_versions and numeric
            item = {"case": row["workload"]["case"], "n": row["workload"]["n"],
                    "threads": row["threads"], "comparable": valid,
                    "same_code": same_code, "same_lock": same_lock,
                    "same_versions": same_versions, "same_numerics": numeric,
                    "same_initial_field_bytes": row["initial_field_sha256"] == old["initial_field_sha256"]}
            if valid:
                item["baseline_seconds_divided_by_this_run"] = {
                    key: old[key]["median_seconds"] / row[key]["median_seconds"]
                    for key in ("energy_gradient", "hopf_diagnostics", "short_solve")}
            comparisons.append(item)
    return comparisons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("q1", "q18", "q22"), default="q1")
    parser.add_argument("--grids", nargs="+", type=int, default=[65, 97])
    parser.add_argument("--threads", nargs="+", type=int, default=[1, 4])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--label", default="workstation")
    parser.add_argument("--output", required=True, help="New directory; never overwrites existing results")
    parser.add_argument("--compare", type=Path, help="Previously generated timing.json")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if (any(n < 17 or n > 193 or n % 2 != 1 for n in args.grids)
            or any(t < 1 or t > 12 for t in args.threads)
            or not 1 <= args.repeats <= 10 or not 1 <= args.steps <= 20):
        parser.error("Require odd grids 17..193, threads 1..12, repeats 1..10, steps 1..20")
    if args.case != "q1" and min(args.grids) < (97 if args.case == "q18" else 129):
        parser.error("Target timing requires q18 >=97 or q22 >=129; use q1 for a quick test")
    if args.worker:
        worker(args)
        return
    baseline = json.loads(args.compare.read_text()) if args.compare else None
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    report = {"schema": "sf-cpu-timing-v1", "label": args.label,
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "CPU timings; excludes file I/O, knot extraction and convergence acceptance",
              "command": sys.argv, "hardware": hardware(),
              "git_commit": command("git", "rev-parse", "HEAD"),
              "dirty_tree": bool(command("git", "status", "--porcelain")),
              "source_sha256": {p: digest(ROOT / p) for p in SOURCES},
              "lock_sha256": digest(ROOT / "uv.lock"),
              "compiler": command("gcc", "--version"),
              "compile_flags": ["-O3", "-std=c99", "-shared", "-fPIC", "-fopenmp", "-lm"],
              "python": sys.version,
              "versions": {k: importlib.metadata.version(k) for k in ("numpy", "scipy")},
              "cases": []}

    def save():
        (out / "timing.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")

    save()
    print("case grid threads energy+gradient(s) short-solve/step(s) diagnostic(s) peakRSS(MiB)", flush=True)
    for n in args.grids:
        for threads in args.threads:
            target = out / f"{args.case}-{n}-t{threads}.json"
            env = os.environ.copy()
            env.update(THREAD_ENV, OMP_NUM_THREADS=str(threads))
            argv = [sys.executable, "-m", "electron_field_topology.sf_timing", "--worker",
                    "--case", args.case, "--grids", str(n), "--threads", str(threads),
                    "--steps", str(args.steps), "--repeats", str(args.repeats), "--output", str(target.resolve())]
            try:
                subprocess.run(argv, check=True, env=env, timeout=600)
            except (subprocess.SubprocessError, OSError) as error:
                report["error"] = str(error)
                save()
                raise
            row = json.loads(target.read_text())
            report["cases"].append(row)
            save()
            print(f"{args.case} {n} {threads} {row['energy_gradient']['median_seconds']:.6f} "
                  f"{row['short_solve']['seconds_per_step']:.6f} "
                  f"{row['hopf_diagnostics']['median_seconds']:.6f} {row['worker_peak_rss_mib']:.1f}", flush=True)
    if baseline:
        report["comparison"] = compare(report, baseline)
        save()
        print("Comparison (>1 means this run is faster):")
        print(json.dumps(report["comparison"], indent=2))
    print(f"Saved {out / 'timing.json'}", flush=True)


if __name__ == "__main__":
    main()
