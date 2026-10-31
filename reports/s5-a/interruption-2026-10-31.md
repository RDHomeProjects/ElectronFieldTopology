# S5-A interruption and recovery record — 31 October 2026

## What happened

The execution environment became unavailable during an attempt to save a larger checkpoint archive. A subsequent read-only shell attempt returned: “No usable execution environment is available.” The cause is unknown; no out-of-memory or GPU diagnosis is established. Background job completion after the last observed output could not be inspected.

This is a compute interruption, not an approval rejection. [PR 36](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/36) remains a draft. Issue 35 remains open because the requested cable and hyperbolic numerical reproductions are unfinished.

## Confirmed durable material

- Repository code, pinned dependencies, bibliography/source audits, configurations and replay scripts on `research/s5a-jennings-static`.
- Eleven complete case records under [cases](cases): eight simple mesh/domain controls, one Q=18 first pass, one rejected coarse cable seed and one Q=22 first pass.
- The [measured report](README.md), original clean-run source/config/artifact hashes and numerical statuses.
- A separately supplied 39,275,371-byte `S5A-field-checkpoints.zip` containing the finest Q=1 and Q=2 reference fields. The attempted 82,223,333-byte replacement containing target fields was **not confirmed**; file metadata still showed the earlier archive. Do not assume those additional binaries are available.

The last locally observed source snapshot was `5bbba7d` when the main evidence was pushed, with further supported analysis scripts/configurations already included in that evidence tree. Local commit IDs in manifests are local provenance, not claims that those exact commits exist publicly. Compare the recorded source hashes to the published files.

## Observed but incompletely recovered

[interruption-observations.json](interruption-observations.json) distinguishes tool-output observations from complete result files. Q=18 129³ and cable polishing reached their time caps with gradient residuals above acceptance. The published hyperbolic 10_139 state was not established. A finite cable-diagram match was reported, but the full replay witness was not confirmed saved durably.

Same-charge comparator runs had started or were queued, followed by the unscaled Q=18 193³ alternative and cable 193³ continuation. No completed result for these stages was confirmed. Do not mark them passed or failed merely from this absence.

## Recovery order

1. Inspect any restored workspace and active job state before starting new computation. Recover existing manifests, results, initial/final NPZ files, intermediate fields and diagram witnesses first; do not overwrite them.
2. Retrieve the confirmed checkpoint archive supplied with this task. Its fields are float32 arrays named `field`, with spacing `h`; normalize on reload. These preserve the simple references, not confirmed target endpoints.
3. Read AGENTS.md, [STATUS](../../docs/STATUS.md), [SF-J2015](../../docs/models/SF-J2015-static.md), the bibliography L36–L38 and the retained case records. Keep the positive cell-interpolant and independent-gradient checks.
4. If target checkpoints cannot be recovered, regenerate Q=18 97³ then 129³, and Q=22 129³ then bounded polishing, using the committed configurations/scripts. The rejected Q=22 97³ result is evidence to retain, not a seed to optimize.
5. Run same-charge comparisons and the explicitly configured unscaled Q=18 193³ alternative only within a recorded resource budget. The latter is a different W-amplitude initial condition, not an independent mesh-convergence point for the amplitude-four trajectory. Coefficients and acceptance criteria remain fixed.
6. Refine the cable from a recovered/polished 129³ field according to `q22-193.json`. If its referenced checkpoint is missing, regenerate the dependency rather than substituting an unrelated field.
7. Use the preserved `analyse_static_fields.py`, `static_knot_references.py`, `match_static_cable_diagrams.py` and `check_static_scaling.py` scripts. Retain every core component and unresolved classification. Compare energies at the same Hopf magnitude and account for incomplete minimisation and mesh/domain errors.
8. Do not claim reproduction until the declared charge, stationarity, scale, source-energy, topology and convergence gates pass. Keep PR 36 unmerged until the maintainer reviews the scientific interpretation.

## GPU/local-workstation question

The current implementation uses CPU NumPy/SciPy and a C/OpenMP kernel. A GPU alone does not accelerate it. Energy/gradient integration and transform-based preconditioning are plausible GPU targets; knot-diagram and exact-polynomial work largely remains CPU work. A GPU port must preserve the validated energy/gradient and be benchmarked with accurate timing and sufficient device memory. No GPU backend, speedup measurement, hardware purchase or new causal dynamics is claimed by this tranche.
