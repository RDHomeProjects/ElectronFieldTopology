# Paired CPU and GPU timing on the ZBook

After successful timings, use the [checkpointed continuation workflow](static-gpu-continuation.md)
for the bounded remaining scientific analysis.

This experimental float64 CUDA/CuPy backend implements the existing
[SF-J2015 functional](models/SF-J2015-static.md), not a different energy model.
It supplies the requested GPU counterpart to the [CPU timing harness](static-timing.md)
under PR 36 / issue 35. Requirements: NUM-001, SCI-004, REP-001/002, SW-001.
No physical-time dynamics, completed target reproduction or GPU speedup is claimed.

## Update and install

In the existing timing checkout:

```bash
git pull --ff-only
uv sync --frozen --all-groups --extra gpu --python 3.12.14
```

The optional `gpu` extra pins CuPy CUDA 12.x 14.2.0 and CUDA component wheels in
`uv.lock`. This installs runtime/compiler/FFT dependencies into the environment;
it does not change the NVIDIA driver or require a system CUDA Toolkit install.
Use `--extra gpu` on subsequent uv commands to retain these optional packages.
The current 580-series driver meets the CUDA 12 driver requirement. Source:
[CuPy installation](https://docs.cupy.dev/en/stable/install.html) and
[NVIDIA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html).

An optional small first device check/benchmark is:

```bash
uv run --frozen --extra gpu --python 3.12.14 python -m electron_field_topology.sf_gpu_timing --case q1 --grids 33 --cpu-threads 12 --steps 1 --repeats 1 --output artifacts/gpu-smoke
```

## Compare the two targets to the fastest tested CPU setting

```bash
uv run --frozen --extra gpu --python 3.12.14 \
  python -m electron_field_topology.sf_gpu_timing \
  --case q22 --grids 129 --cpu-threads 12 --steps 10 --repeats 3 \
  --output "artifacts/gpu-q22-$(date +%Y%m%d-%H%M%S)"

uv run --frozen --extra gpu --python 3.12.14 \
  python -m electron_field_topology.sf_gpu_timing \
  --case q18 --grids 97 --cpu-threads 12 --steps 10 --repeats 3 \
  --output "artifacts/gpu-q18-$(date +%Y%m%d-%H%M%S)"
```

Each command reruns the original CPU harness at twelve threads, then runs CUDA
sequentially on the **same initial field**, grid, coefficients and step budget.
Q18 uses the original perturbed K(7,2) precursor; Q22 uses the original cable
precursor. Missing archived endpoints are not substituted. Initial resolution
guards and CPU field hashes are checked. Use mains power and consistent thermal
conditions, as both CPU and GPU load a laptop's cooling/power system.

## Correctness gates before timing ratios

Every invocation first executes real device checks: constant zero energy/gradient,
CPU and independent NumPy cell energy, complete CPU gradient, a constrained
finite variation, the invalid-cell control, orthonormal DST-I versus SciPy,
five-step field agreement and Hopf diagnostics. Native energy/gradient comparison
uses rtol 1e-11 and atol 1e-13; DST uses rtol 1e-12 and atol 1e-13; constrained
variation uses absolute error 1e-9. These are backend comparisons, not relaxed
production reproduction gates.

For each selected large workload, initial energy/gradient/cell guards and
diagnostics are checked again. An untimed complete short solve is compared to
the original CPU solver, including the entire final field (rtol 1e-9, atol 1e-10)
and final energy (rtol 1e-11, atol 1e-13). Timed repeats must have the same stop
status, iteration count, evaluation count and matching final energies. Ratios
are emitted only after these checks pass. A failure retains an error in
`timing.json`; it does not switch to the CPU or publish a GPU speed ratio.

## Implementation and timing boundaries

- CUDA uses the same normalized trilinear 2x2x2 Gauss functional and analytic
  gradient as `sf_energy.c`. One thread handles a cell. Eight disjoint cell
  colours avoid gradient races/atomics; double reductions combine cell scalars.
- The field, gradient, directions and transform arrays remain on the GPU during
  solves. Scalar line-search/guard decisions return to Python, as their timing
  is part of the solver. No float32/mixed precision or fast-math option is used;
  explicit compilation options are `--std=c++11 --fmad=false`.
- Preconditioning computes the same orthonormal DST-I with an odd-extension
  FFT on each spatial axis. Applying it twice with the same eigenvalue divisor
  gives the same Dirichlet Sobolev inverse. The implementation is compared to
  both SciPy and direct sine matrices on the CPU.
- Hopf derivatives/FFTs, neighbour-angle and norm reductions also run on the GPU.
- Timings use wall clock **with CUDA stream synchronisation before and after**
  each sample. They include host launch/scalar-decision costs, not just launch
  enqueue time. Setup, JIT compilation and warm-ups are excluded. See
  [CuPy timing guidance](https://docs.cupy.dev/en/stable/user_guide/performance.html).
- Resident energy/gradient time and short-solve time exclude the initial host
  upload, just as the CPU benchmark starts from a prepared field. Input-upload
  time and a separate complete host-to-device / energy-gradient / device-to-host
  round trip are retained so transfer costs can be assessed independently.
- Allocator pool used/reserved bytes are recorded after the workload. They are
  **not** a device peak-memory measurement. Kernel block sizes 64, 128 and 256
  are supported through `--block-size`; the default is 128. CPU thread count
  and CUDA threads per block describe different execution settings.

`CPU/GPU speed ratios` are CPU seconds / GPU seconds; values above one favour the
GPU. Use **short_solve** for the end-to-end optimisation comparison. Disk I/O,
field compression, knot extraction and convergence time are excluded. The new
optional dependency changes the universal lockfile hash; paired fresh CPU results
avoid mixing the older report's lock hash into this comparison.

## Validation status

The execution environment has no accessible NVIDIA GPU. Host arithmetic tests,
the CPU array-protocol solver and an offline NVRTC compilation targeting compute
capability 7.5 are recorded in [the validation report](../reports/s5-a/gpu-validation-2026-10-31/README.md).
These do not establish successful GPU execution. The first ZBook run must pass
the actual device checks above. This is a comparison harness, not an accepted
production GPU reproduction backend. AI assisted implementation and reporting.
