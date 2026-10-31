"""Paired CPU/CUDA float64 timing with mandatory numerical checks (Apache-2.0)."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
from .sf_timing import ROOT, SOURCES, THREAD_ENV, command, digest, hardware, workload


def make_seed(c):
    import numpy as np
    from .skyrme import coordinates, rational_field, set_boundary, normalize
    xyz = coordinates(c["n"], c["h"])
    u = set_boundary(rational_field(xyz, **c["seed"]))
    if c["perturbation_amplitude"]:
        rng = np.random.default_rng(c["perturbation_seed"]); noise = np.zeros_like(u)
        for _ in range(8):
            wave = rng.normal(size=3); phase = rng.uniform(-np.pi, np.pi); polar = rng.normal(size=3)
            noise += np.sin(xyz@wave+phase)[..., None]*polar
        noise *= np.exp(-(np.linalg.norm(xyz, axis=-1)/5)**4)[..., None]
        noise /= max(float(np.max(np.linalg.norm(noise, axis=-1))), 1e-15)
        u = set_boundary(normalize(u+c["perturbation_amplitude"]*noise))
    return u


def agreement(name, actual, expected, checks, rtol=1e-11, atol=1e-13):
    import numpy as np
    a, b = np.asarray(actual), np.asarray(expected)
    np.testing.assert_allclose(a, b, rtol=rtol, atol=atol, err_msg=name)
    checks[name] = {"passed": True, "rtol": rtol, "atol": atol,
                    "maximum_absolute_error": float(np.max(abs(a-b)))}


def validate_device(cp, build):
    """Actual CUDA execution: independent cell energy, adjoint, DST and solver."""
    import numpy as np
    from scipy.fft import dstn
    from .skyrme import Energy, NORTH, normalize, numpy_cell_energy, set_boundary, coordinates, rational_field, diagnostics
    from .sf_minimize import minimize_static
    from .sf_gpu import GPUEnergy, dst1n, minimize_array, diagnostics_array
    checks = {}; n = 9; h = .3
    gpu = GPUEnergy(n, h); cpu = Energy(n, h, Path(build)/"native")
    north = np.broadcast_to(NORTH, (n, n, n, 3)).copy()
    p, g = gpu.evaluate(cp.asarray(north))
    agreement("constant_energy", cp.asnumpy(p), [0., 0.], checks, atol=1e-28)
    agreement("constant_gradient", cp.asnumpy(g), np.zeros_like(north), checks, atol=1e-14)
    rng = np.random.default_rng(35)
    u = set_boundary(normalize(NORTH+.12*rng.normal(size=north.shape)))
    p, g = gpu.evaluate(cp.asarray(u)); pc, gc = cpu.evaluate(u)
    agreement("native_energy", cp.asnumpy(p), pc, checks)
    agreement("independent_numpy_cell_energy", cp.asnumpy(p), numpy_cell_energy(u, h), checks)
    agreement("native_gradient", cp.asnumpy(g), gc, checks)
    agreement("cell_guards", [gpu.minimum_interpolant_norm, gpu.minimum_corner_cone],
              [cpu.minimum_interpolant_norm, cpu.minimum_corner_cone], checks)
    v = np.zeros_like(u); v[2:-2, 2:-2, 2:-2] = rng.normal(size=(5, 5, 5, 3))
    v -= u*np.sum(u*v, axis=-1, keepdims=True); v /= np.linalg.norm(v); eps = 1e-4
    finite = (sum(numpy_cell_energy(normalize(u+eps*v), h))-
              sum(numpy_cell_energy(normalize(u-eps*v), h)))/(2*eps)
    agreement("independent_constrained_variation", np.sum(cp.asnumpy(g)*v), finite, checks, rtol=0, atol=1e-9)
    bad = north.copy(); bad[4, 4, 4] = -NORTH; gpu.evaluate(cp.asarray(bad))
    if gpu.minimum_corner_cone > 0:
        raise ValueError("CUDA failed to identify the unresolved-cell control")
    checks["nonpositive_cell_cone_detected"] = {"passed": True}
    a = rng.normal(size=(5, 6, 7, 3))
    agreement("gpu_dst_vs_scipy", cp.asnumpy(dst1n(cp.asarray(a), cp)),
              dstn(a, axes=(0, 1, 2), type=1, norm="ortho"), checks, rtol=1e-12)
    n = 17; h = .2
    u = set_boundary(rational_field(coordinates(n, h), scale=.6, cutoff=1.3))
    cpu = Energy(n, h, Path(build)/"native"); gpu = GPUEnergy(n, h)
    a, sa = minimize_static(cpu, u, 5, lambda f, i: None, lambda: False)
    b, sb = minimize_array(gpu, cp.asarray(u), 5, lambda f, i: None, lambda: False, cp)
    if sa != sb:
        raise ValueError(f"CUDA/CPU small-solve work differs: {sa} / {sb}")
    agreement("five_step_field", cp.asnumpy(b), a, checks, rtol=1e-9, atol=1e-10)
    da, db = diagnostics(a, h), diagnostics_array(cp.asarray(a), h, cp)
    for key in ("hopf_integral", "unit_error", "max_neighbour_angle", "mean_topological_b"):
        # arccos amplifies roundoff near aligned neighbours; angles are diagnostics.
        agreement("diagnostic_"+key, db[key], da[key], checks, rtol=1e-9, atol=1e-10)
    return {"passed": True, "checks": checks, "scope": "CUDA device execution, not host emulation"}


def measured_cuda(function, repeats, cp):
    times = []; value = None
    stream = cp.cuda.get_current_stream()
    for _ in range(repeats):
        stream.synchronize(); start = time.perf_counter()
        value = function()
        stream.synchronize(); times.append(time.perf_counter()-start)
    return {"samples_seconds": times, "median_seconds": statistics.median(times),
            "minimum_seconds": min(times), "maximum_seconds": max(times)}, value


def run_grid(args, n, out, cp):
    import numpy as np
    from .skyrme import Energy
    from .sf_minimize import minimize_static
    from .sf_gpu import GPUEnergy, minimize_array, diagnostics_array
    cpu_dir = out/f"cpu-{n}"
    env = os.environ.copy(); env.update(THREAD_ENV, OMP_NUM_THREADS=str(args.cpu_threads))
    subprocess.run([sys.executable, "-m", "electron_field_topology.sf_timing", "--case", args.case,
                    "--grids", str(n), "--threads", str(args.cpu_threads), "--steps", str(args.steps),
                    "--repeats", str(args.repeats), "--label", args.label+"-cpu",
                    "--output", str(cpu_dir.resolve())], env=env, check=True, timeout=600)
    cpu_report = json.loads((cpu_dir/"timing.json").read_text()); cpu_row = cpu_report["cases"][0]
    c = workload(args.case, n); u = make_seed(c); h = c["h"]; checks = {}
    if digest_bytes(u) != cpu_row["initial_field_sha256"]:
        raise ValueError("CPU/GPU input generation differs; paired timing aborted")
    upload, ug = measured_cuda(lambda: cp.asarray(u), args.repeats, cp)
    gpu = GPUEnergy(n, h, args.block_size)
    parts, grad = gpu.evaluate(ug)  # First compilation/evaluation excluded.
    with tempfile.TemporaryDirectory(prefix="eft-gpu-reference-") as build:
        cpu = Energy(n, h, build)
        pc, gc = cpu.evaluate(u)
        agreement("initial_energy", cp.asnumpy(parts), pc, checks)
        agreement("initial_gradient", cp.asnumpy(grad), gc, checks)
        agreement("initial_cell_guards", [gpu.minimum_interpolant_norm, gpu.minimum_corner_cone],
                  [cpu.minimum_interpolant_norm, cpu.minimum_corner_cone], checks)
        if gpu.minimum_corner_cone <= 0:
            raise ValueError("Unresolved CUDA initial cells")
        diagnostic = lambda: diagnostics_array(ug, h, cp)
        dg = diagnostic()
        for key in ("hopf_integral", "unit_error", "max_neighbour_angle", "mean_topological_b"):
            agreement("initial_"+key, dg[key], cpu_row["initial_diagnostics"][key], checks, rtol=1e-9, atol=1e-10)
        solve = lambda: minimize_array(gpu, ug, args.steps, lambda f, i: None, lambda: False, cp)
        final_cpu, cpu_work = minimize_static(cpu, u, args.steps, lambda f, i: None, lambda: False)
        final_gpu, gpu_work = solve()  # Optimiser warm-up, excluded from timings.
        if gpu_work != cpu_work or any(result != cpu_work for result in cpu_row["short_solve"]["results"]):
            raise ValueError(f"CUDA/CPU iteration/evaluation counts differ: {gpu_work} / {cpu_work}")
        agreement("short_solve_final_field", cp.asnumpy(final_gpu), final_cpu, checks, rtol=1e-9, atol=1e-10)
        agreement("final_energy", cp.asnumpy(gpu.evaluate(final_gpu)[0]), cpu.evaluate(final_cpu)[0], checks)
        del final_cpu, final_gpu, gc, grad
    energy, _ = measured_cuda(lambda: gpu.evaluate(ug), args.repeats, cp)
    diag, _ = measured_cuda(diagnostic, args.repeats, cp)
    times, works, energies = [], [], []
    for _ in range(args.repeats):
        sample, (final, result) = measured_cuda(solve, 1, cp)
        times.append(sample["median_seconds"]); works.append(result)
        energies.append(float(sum(gpu.evaluate(final)[0])))
        if result != cpu_work or result["iterations"] != args.steps or result["status"] != "iteration_budget":
            raise ValueError("CUDA timed solve has unequal work or stopped early")
    agreement("timed_final_energies", energies, cpu_row["short_solve"]["final_energies"], checks, rtol=1e-9, atol=1e-10)
    short = {"samples_seconds": times, "median_seconds": statistics.median(times),
             "seconds_per_step": statistics.median(times)/args.steps, "results": works, "final_energies": energies}
    def roundtrip():
        p, g = gpu.evaluate(cp.asarray(u))
        return cp.asnumpy(p), cp.asnumpy(g)
    roundtrip()  # Warm allocation/copy paths.
    transfers, _ = measured_cuda(roundtrip, args.repeats, cp)
    pool = cp.get_default_memory_pool()
    gpu_row = {"energy_gradient": energy, "short_solve": short, "hopf_diagnostics": diag,
               "energy_gradient_with_transfers": transfers, "input_upload": upload,
               "pool_reserved_mib": pool.total_bytes()/2**20, "pool_used_mib": pool.used_bytes()/2**20}
    ratios = {key: cpu_row[key]["median_seconds"]/gpu_row[key]["median_seconds"]
              for key in ("energy_gradient", "short_solve", "hopf_diagnostics")}
    return {"workload": c, "steps": args.steps, "repeats": args.repeats,
            "cpu_threads": args.cpu_threads, "cuda_block_size": args.block_size,
            "validation": {"passed": True, "checks": checks}, "cpu": cpu_row, "gpu": gpu_row,
            "cpu_seconds_divided_by_gpu_seconds": ratios,
            "gpu_transfer_inclusive_energy_speedup": cpu_row["energy_gradient"]["median_seconds"]/transfers["median_seconds"]}


def digest_bytes(a):
    import hashlib
    return hashlib.sha256(a.tobytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case", choices=("q1", "q18", "q22"), default="q1")
    p.add_argument("--grids", type=int, nargs="+", default=[65, 97])
    p.add_argument("--cpu-threads", type=int, default=12)
    p.add_argument("--steps", type=int, default=10)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--block-size", type=int, choices=(64, 128, 256), default=128)
    p.add_argument("--device", type=int, default=0)
    p.add_argument("--label", default="zbook-gpu")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    if (any(n < 33 or n > 193 or n % 2 != 1 for n in a.grids) or not 1 <= a.cpu_threads <= 12
            or not 1 <= a.steps <= 20 or not 1 <= a.repeats <= 10 or a.device < 0):
        p.error("Require odd grids 33..193, CPU threads 1..12, steps 1..20, repeats 1..10")
    if a.case != "q1" and min(a.grids) < (97 if a.case == "q18" else 129):
        p.error("Target seeds require q18 >=97 or q22 >=129")
    out = Path(a.output); out.mkdir(parents=True, exist_ok=False)
    os.environ.update(THREAD_ENV, OMP_NUM_THREADS=str(a.cpu_threads))
    sources = SOURCES + ["src/electron_field_topology/"+name for name in
                         ("sf_gpu.py", "sf_gpu_timing.py", "sf_energy_gpu.cu")]
    report = {"schema": "sf-gpu-timing-v1", "label": a.label, "command": sys.argv,
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "experimental float64 CUDA comparison, not a production reproduction",
              "git_commit": command("git", "rev-parse", "HEAD"),
              "dirty_tree": bool(command("git", "status", "--porcelain")),
              "hardware": hardware(), "python": sys.version,
              "source_sha256": {s: digest(ROOT/s) for s in sources}, "lock_sha256": digest(ROOT/"uv.lock"),
              "cuda_compile_options": ["--std=c++11", "--fmad=false"],
              "versions": {k: importlib.metadata.version(k) for k in ("numpy", "scipy")}, "cases": []}
    def save():
        (out/"timing.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    save()
    try:
        from .sf_gpu import cupy_module
        cp = cupy_module(); cp.cuda.Device(a.device).use()
        device = cp.cuda.runtime.getDeviceProperties(a.device)
        name = device["name"].decode() if isinstance(device["name"], bytes) else device["name"]
        report["cuda"] = {"cupy_version": cp.__version__, "device_id": a.device, "name": name,
                          "compute_capability": cp.cuda.Device().compute_capability,
                          "runtime_version": cp.cuda.runtime.runtimeGetVersion(),
                          "driver_version": cp.cuda.runtime.driverGetVersion(),
                          "device_memory_total_mib": device["totalGlobalMem"]/2**20,
                          "timing": "synchronized wall clock, including host dispatch/scalar synchronizations"}
        print(f"CUDA device: {name}; float64; CPU reference: {a.cpu_threads} threads", flush=True)
        with tempfile.TemporaryDirectory(prefix="eft-cuda-check-") as build:
            report["device_validation"] = validate_device(cp, build)
        save(); print("CUDA independent numerical checks passed.", flush=True)
        for n in a.grids:
            row = run_grid(a, n, out, cp); report["cases"].append(row); save()
            print(f"GPU {a.case} {n}: energy+gradient={row['gpu']['energy_gradient']['median_seconds']:.6f}s "
                  f"solve/step={row['gpu']['short_solve']['seconds_per_step']:.6f}s "
                  f"diagnostics={row['gpu']['hopf_diagnostics']['median_seconds']:.6f}s", flush=True)
            print("CPU/GPU speed ratios (>1 means GPU faster): " +
                  json.dumps(row["cpu_seconds_divided_by_gpu_seconds"]), flush=True)
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        save()
        raise
    print(f"Saved {out/'timing.json'}", flush=True)


if __name__ == "__main__":
    main()
