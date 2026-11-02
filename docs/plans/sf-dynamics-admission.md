# Workstation neutral-dynamics admission

Prepared: 2026-11-02T08:48:53.481631+00:00 UTC; 2026-11-02T19:48:53.481631+11:00 Australia/Melbourne. See the
[equations and numerical scope](../models/SF-relativistic.md).

## What runs

Read all 31 original Q18/neighbour endpoints from the campaign recorded in PR50,
authenticate exact hashes/metadata, then independently integrate their static energy,
rest stress, kinetic conditioning, centroid/width and outer-box energy fraction.
Evaluate tensor-consistent boost integrals at six speeds along three axes, and four
directional curvature probes at three perturbation sizes for six selected endpoints.
Every mesh, domain and Q18 basin alternative is retained. Curvature probes cover only
four smooth directions, not an eigenspectrum. This run does not evolve physical time.

No GPU dependency or topology package is needed: this is CPU NumPy quadrature and
the existing independently checked C energy accelerator for perturbations (gcc needed).
The static relaxation kernels, frozen campaign source and original fields stay unchanged.
Temporary memory is bounded by slab integration plus nodal arrays; selected curvature
cases can use approximately 2–3 GB, depending on NumPy temporaries. No new large field
outputs are written. There is no overall wall-clock cutoff.

## Run and restart

Install the handoff into a separate checkout at ~/ElectronFieldTopology-dynamics.
Run only the new tests, docs check and small instrument verification, then commit the
tooling locally before starting. The source must be clean. The provided RUN.sh starts
a background worker with an inherited flock lock and writes its exact output path to
artifacts/SF-DYNAMICS-CURRENT. Reissuing start while locked cannot create a duplicate.
Status reports the lock, completion status and last log lines. Resume retains completed
endpoint records and restarts only unfinished endpoints at the same code/config.

```bash
cd "$HOME/ElectronFieldTopology-dynamics"
uv sync --frozen --all-groups --python 3.12.14
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 uv run --frozen pytest -q tests/test_sf_dynamics.py
python3 scripts/check_docs.py
git commit -m "Specify neutral SF dynamics and add workstation admission diagnostics"
bash "$HOME/Downloads/ElectronFieldTopology-SF-dynamics-20261102/RUN.sh" start
```

RUN.sh status and RUN.sh resume are safe to repeat. The default source is the original
~/ElectronFieldTopology-q18-study/artifacts/q18-neighbours-20261102T022100+1100-165739.
If deliberately moved, set SOURCE_CAMPAIGN to its full new path before start; only
the original field hashes are accepted. The source location must remain stable for
resume. Missing/modified fields are recorded as unavailable; the available endpoints
are still analyzed. Completion is then explicitly partial, not success.

## Results and next action

The output has SUMMARY.md, summary.json, per-case result.json/error.json,
manifest.json, instruments.json, evidence-hashes.json and evidence.zip. RUN_COMPLETE.json
contains execution status and completed/expected counts; RUN_EXIT.json records the
worker exit even if an unexpected error prevented aggregation. Both use UTC/Melbourne.
All result JSON and summary documents carry timestamps; log progress events carry
both time zones. Keep the checkout and original field campaign for reproducibility.

After it stops, run status and collect, and transfer evidence.zip for scientific
assessment. A finished status alone does not mean all 31 endpoints passed: require
status=complete, completed_endpoints=31 and numerical_failures=0 for execution completeness.
Scientific stress/curvature findings remain data regardless of those software checks.

Only then choose the first higher-Q moving candidate and finish the physical-time
solver validation gates. This instrument does not establish a run duration in physical
seconds, a new solution, causality for arbitrary data, or electron behaviour.
