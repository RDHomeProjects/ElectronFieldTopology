# Experimental CUDA timing backend — validation record

31 October 2026 (Australia/Melbourne). User requested a GPU counterpart to the
local CPU timing harness after measuring 4/6/8/12-thread CPU scaling.
This change belongs to draft PR 36 / issue 35 and supports NUM-001, SCI-004,
REP-001/002 and SW-001. AI assisted implementation, tests and documentation.

## Scope and source map

The model is still [SF-J2015-static](../../../docs/models/SF-J2015-static.md):
Jennings arXiv:1412.8597v2 Eq. (2.1), the existing normalized trilinear cell
functional, 2x2x2 Gauss rule, analytic nodal gradient and existing constraints.
No physical coefficient, acceptance threshold or original CPU production source
was changed. The CUDA cell arithmetic is a port of `sf_energy.c:sf_cell`.
Device-array minimisation ports `sf_minimize.minimize_static`; DST-I is evaluated
through mathematically equivalent odd-extension FFTs rather than SciPy CPU calls.
Hopf diagnostics port the existing periodic FFT quadrature and fourth-order
differences. These remain separate from core knot identification.

The optional `gpu` extra pins `cupy-cuda12x[ctk]==14.2.0`, including hashed CUDA
12.9 component wheels. Existing numerical dependency versions were preserved;
the lockfile hash changes to record the additional optional packages.

## Completed checks

- Full locked suite, with optional topology instruments: **147 passed, 1 skipped**
  in 18.89 seconds. The skipped test requires an actual CUDA device.
- Targeted energy/minimisation/timing/backend checks: **21 passed, 1 skipped**.
- Exact CUDA cell-function body compiled as C++ host code: constant, random,
  Hopf and antipodal corner controls match the original C energy/gradient/guards
  and independent NumPy cell energy. A constrained finite variation verifies
  the gradient independently. This is host execution, not CUDA execution.
- FFT-based orthonormal DST-I matches SciPy and direct sine matrices and is
  self-inverse on selected noncubic/cubic, scalar/vector shapes.
- Array-protocol solver with NumPy matches the original SciPy solver over five
  steps, including status/counts/full field. Diagnostic values match separately.
- Paired harness orchestration exercised with an explicitly labelled NumPy test
  double. Missing-GPU control aborts, preserves an error record and emits no
  GPU speed ratio. No benchmark result from that test double is published.
- Offline **NVRTC 12.9.86 compilation to compute_75 PTX succeeded**, with the
  same `--std=c++11 --fmad=false` options used by the CuPy kernel. The
  [compiler record](offline-compile.json) records the source hash and PTX size.
  Compilation does not establish execution, memory-race freedom or performance.

Reproduction of host checks:

```bash
uv sync --frozen --all-groups --extra topology --python 3.12.14
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 uv run --frozen --extra topology pytest -q
python3 scripts/check_docs.py
```

## Pending on-device evidence

No accessible NVIDIA GPU exists in this execution environment. **No GPU timing,
speedup or successful on-device numerical result is reported.** The workload
on the user's RTX 2080 Super Max-Q remains to be measured. Every real-device
invocation first checks constant/random controls, independent gradient variation,
invalid cells, DST and a five-step solve, then repeats parity checks on the
selected target workload. A mismatch prevents timing ratios; it is not treated
as a reason to weaken the checks.

[The run guide](../../../docs/static-gpu-timing.md) provides installation and paired
Q22 129³ / Q18 97³ commands against the original twelve-thread CPU solver.
Timings use synchronised wall time and warm-ups, keep working fields on-device
and separately measure host/device transfers. Ratios are conditional on matching
step/evaluation counts and numerical agreement. They measure short optimisation
work, not convergence, knot identity or completed reproduction.

PR 36 remains draft and unmerged. Earlier interrupted target results are
unchanged; this work does not close issue 35. The seven older malformed workflow
filters remain outside the GPU harness change. Hosted CI tests the host checks;
it does not request GPU runners, install CUDA packages or run GPU workloads.
