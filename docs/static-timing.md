# Quick local CPU timing harness

This harness times the existing SF-J2015 implementation described in the
[model specification](models/SF-J2015-static.md), supporting REP-001/002 and
SW-001 under [draft PR 36](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/36).
It changes no equations, energy coefficients, numerical kernels or reproduction
thresholds. AI assisted its implementation and reporting.

## Run on Ubuntu

From a checkout of `research/s5a-jennings-static`, with GCC/OpenMP and uv installed:

```bash
uv python install 3.12.14
uv sync --frozen --all-groups --python 3.12.14
uv run --frozen --python 3.12.14 python -m electron_field_topology.sf_timing --label zbook --output artifacts/timing-zbook
```

The reference uses **Python 3.12.14, NumPy 2.5.4 and SciPy 1.18.1**. Pin the
interpreter as above for a controlled comparison. The universal lockfile also
supports Python 3.11, which selects older compatible NumPy/SciPy versions;
`same_lock: true` therefore does not guarantee `same_versions: true`. A version
mismatch deliberately withholds ratios even when the numerical checks pass.

The default quick run uses a fixed Q=1 seed at 65³ and 97³, one and four OpenMP
threads, three repetitions and three optimisation steps. It needs no recovered
field archives, optional knot software or CUDA installation. Every invocation
requires a new output directory; completed cases are saved as they finish.

The two target precursor workloads can also be timed independently:

```bash
uv run --frozen --python 3.12.14 python -m electron_field_topology.sf_timing --case q22 --grids 129 --threads 4 --label zbook --output artifacts/timing-zbook-q22 --compare reports/s5-a/timing-2026-10-31/q22-timing.json
uv run --frozen --python 3.12.14 python -m electron_field_topology.sf_timing --case q18 --grids 97 --threads 4 --label zbook --output artifacts/timing-zbook-q18 --compare reports/s5-a/timing-2026-10-31/q18-timing.json
```

These use the committed perturbed cable/torus precursor configurations with
their original support and W amplitudes. Q=18 starts from its original 97³
precursor, not the missing 129³ continuation checkpoint. Q=22 requires at least
129³ because its old 97³ seed failed the cell-resolution gate. Seeds must pass
the positive cell-interpolant and 5% Hopf-resolution guards before short solves
are accepted for timing. These short runs do not reproduce either final knot.

## What is measured

- One float64 normalized-cell energy **and gradient** evaluation.
- A full short Sobolev-CG solve, including initial evaluation, preconditioning,
  projection, line search and field copies. Seconds per step divide the whole
  short solve by its step count, so startup overhead is included.
- Hopf diagnostics, including derivatives, FFTs and neighbour angles.
- Peak worker RSS across setup, warm-ups and timed work; not GPU memory or a
  prediction of full-production peak usage.

Compilation, seed construction, warm-ups, field archives and report I/O are
excluded from operation timings. Every repeat starts from the same field.
Every grid/thread pair runs in a separate process with OpenMP set before imports;
OpenBLAS/MKL/NumExpr are limited to one thread. SciPy transforms use their existing
default worker count. Thread counts are requested settings, not measured core
occupancy. One worker runs at a time, with a ten-minute timeout per pair.

`timing.json` records all samples and medians, initial diagnostics, solver
iterations/evaluations, final energies, source and lock hashes, compiler flags,
versions, CPU/memory/cgroup information and GPU inventory. **All work is CPU-only.**
No topology extraction or checkpoint-compression performance is measured.
Run on mains power with other heavy work paused; thermal and shared-host effects
can still change timings. Use matching command options for comparisons.

## Compare machines

Supply an earlier `timing.json` using `--compare`:

```bash
uv run --frozen --python 3.12.14 python -m electron_field_topology.sf_timing --label zbook --output artifacts/timing-zbook-comparison --compare reports/s5-a/timing-2026-10-31/timing.json
```

The checked-in reference is from the **replacement execution environment**, not
the one that crashed. Details and historical context appear in
[the reference report](../reports/s5-a/timing-2026-10-31/README.md).
Ratios are baseline seconds / local seconds: **2 means the local run is twice as
fast**. Ratios are withheld when work/configuration, source hashes, dependency
versions, iteration/evaluation counts or numerical outcomes do not match. Initial
field hashes are reported separately: cross-platform transcendental rounding need
not be bit-identical. Timing comparisons are not convergence acceptance.

The crashed environment cannot be rerun. Its retained histories contain only
whole-run timings, including periodic diagnostics/checkpoint overhead and a
changing optimisation workload. They support approximate historical context,
not an exact controlled speedup claim against this harness.
