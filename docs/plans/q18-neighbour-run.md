# Q18 basin and Q17/Q19 workstation run

Prepared: 2026-11-01T15:07:15+00:00 UTC; 2026-11-02T02:07:15+11:00 Australia/Melbourne. Parent: PR49 merge `05aa61013712282421ffc5c2c0b27a20bb949446`. This implements the [post-audit plan](post-audit-q-assessment.md) under [ADR-0008](../decisions/ADR-0008-charged-model-audit.md). Preparation/seed tests are separate from future relaxed results; no research GPU solve was performed while preparing the package.

## Scientific controls

The model is [SF-J2015-static](../models/SF-J2015-static.md): unchanged dimensionless energy, two north-pole boundary layers, trilinear normalized cell quadrature, float64 GPU calculations and projected Sobolev-CG. Jennings 1412.8597v2 Eqs.2.1,2.4,2.7 and Table 1 are the primary map. For K(7,2), degree is 2 alpha + 7 beta: Q17 uses (5,1), Q18 (2,2), Q19 (6,1). These are Hopf labels, not electric charge. Positive alpha/beta imply that a common zero with the denominator on S3 would require both complex coordinates zero, which is impossible. Compact north-pole support and finite-grid resolution are tested separately.

| Branch | Seed radial scale | Fixed optimizer length | Purpose |
|---|---:|---:|---|
| q18-baseline | 4.0 | 0.5 | Reconstruct the original 97-grid seed, then refine |
| q17-neighbour | 4.0 | 0.5 | Adjacent-Q, same K(7,2) denominator; 129-grid start |
| q19-neighbour | 4.0 | 0.5 | Adjacent-Q, same denominator; 129-grid start |
| q18-scale35 | 3.5 | 0.5 | Change radial profile scale only |
| q18-scale45 | 4.5 | 0.5 | Change radial profile scale only |
| q18-ell025 | 4.0 | 0.25 | Change the fixed precondition length only |

All Q18 branches retain amplitude 4, cutoff 7.2, perturbation amplitude .005, seed 35 and the original eight-mode perturbation prescription. New Q17/Q19 use those conditioning choices with their declared numerator exponents. Coefficients, physical normalization and acceptance thresholds are not adjusted. Optimizer steps do not represent physical time. The original minimizer direction restarts at pass boundaries; exact historical optimizer trajectories are not reconstructed. The original 97-grid start and inherited fine-grid path are explicitly represented, alongside the alternative profiles.

## Stage order and convergence

The default frozen plan has **31 stages**. Q1/Q2 fresh controls precede a Q22 control; all six coarse screens then precede the expensive refinements. Q18 screens start at 97 cubed, h=.16. Q17/Q19 start at 129 cubed, h=.12. Every branch has 129/161/193 fine meshes at h=.12/.096/.08 with side length 15.36. Each also has a 193-grid domain at h=.096, side length 18.432, compared with its 161-grid h=.096 field. Domain branches originate from that matching-spacing field, not a different-Q state.

The Q22 control reuses a stationary, committed-hash-matched 129-grid cable field when found; otherwise it reconstructs the preserved Q22 seed explicitly. Q1/Q2/Q22 must pass stationary/charge/cell/unit/virial/CPU-audit controls before new research runs. Q22's existing source-energy gate also applies to its control. Q18 historical fields, if hash-matched, receive a separate optional audited stage: they never replace the fresh baseline. This makes 32 stages when such a retained Q18 field is available.

A resolved, independently audited coarse endpoint can initialize refinement even if its stationarity/virial gate fails; the failure remains visible. This tests whether refinement resolves it rather than declaring a coarse stall conclusive. Mesh/domain energy comparisons are eligible only when both endpoints are stationary and satisfy the existing scalar/CPU gates. The report separates those energy diagnostics from independent dilation and cross-mesh topology assessment. A small energy change cannot certify that the same basin was tracked.

## Historical fields, restart and provenance

The launcher searches known project artifacts folders on this workstation. Manifests and committed evidence ZIP metadata supply exact hashes; full fields are never assumed to be inside the small evidence ZIP. Unmatched files are listed and not automatically reused. No verified Q18 field means a clearly labeled fresh reconstruction, not a missing-path failure. The inventory is frozen with the plan and includes the original published source record.

Every completed pass has a CPU/GPU energy/gradient/Hopf audit, a float64 final field and rolling latest/previous checkpoints. On interruption, a valid audited final is preferred. If the last pass lacks its endpoint audit, a rolling checkpoint must match the stage's model, Q, geometry and configuration hash and pass finite/unit/boundary checks; the new pass then performs fresh CPU/GPU initial audits before optimization. A corrupt latest file can fall back to previous. Earlier files are preserved. A changed source commit or frozen plan is refused on resume; use the original run checkout.

The runner locks each campaign, writes atomic JSON/checkpoints, records source/config/lock hashes and retains every pass. The launcher avoids starting a second process for its current campaign. Disk space below twelve raw field copies pauses the run for a later resume. Full fields remain local; evidence.zip contains dated records, analysis, logs, extracted curves and hashes, excluding bulk case fields. Retain the complete campaign directory for future recovery and reanalysis.

## Time, stopping and analysis

There is **no two-hour or other overall wall-time cap**. Each pass has at most 3,000 iterations/1,800 solver seconds plus time for setup/audits. Further passes continue while progress is material. A three-pass window with less than .5% residual improvement and less than 1e-8 relative energy decrease records a stall, preserving its field. Each branch keeps its declared optimizer length; the ell=.25 branch is an independent path comparison, not an undisclosed fallback. Stationarity remains the independently measured 1e-3 residual. Original 5% charge, 5% scale/virial, 2% energy-convergence and applicable 3% source comparisons remain visible.

Topology and coordinate-dilation jobs run for each retained stage endpoint. Fresh screens examine both initial and final preimages; later stages examine final fields. Two regular targets, multiple polygon resolutions/projections, component invariants, complement checks, diagram linking and independent 256/384/512-segment Gauss-link quadrature remain in the existing instrument. Analysis jobs have a one-hour per-job guard and retain timeout/unresolved states; this is not a total campaign cap. Resume retries incomplete analysis, and collect regenerates the evidence without solving. No link or changed core is discarded merely for failing the desired knot label. Full hyperbolic identification, continuum isotopy and nonlinear/relativistic stability require separate evidence.

GPU history samples, checkpoints and result/manifest/error records now carry UTC and Australia/Melbourne timestamps. Analysis outputs get execution timestamps; exported raw file metadata records modification times. The launcher records dated start/stop/status logs. SUMMARY.md and summary.json report outcomes and accumulated solver wall time; duration depends on observed convergence, not a promised fixed finish time.

## Development and recovery verification

The preparation report contains measured CPU seed admission and targeted test results. The exact original 191 files are now verified from the complete-history recovery bundle, including source commit, fixed bundle SHA-256, tree path/blob mapping and rehashed original bytes in a temporary bare repository. Current development files can evolve; the archived originals, original manifest and bundle are unchanged.

The older Q22 preflight still pins all numerical kernels, optimizer, diagnostics and lock. It also recognizes three exact reviewed old/new infrastructure hash pairs for Q17/Q19 admission and timestamps. It rejects any subsequent unreviewed change. New runs record their complete current source hashes; existing campaigns still require their original source/commit when resuming. The old Q22 workstation checkout is not replaced by this new worktree.

Requirements: GOV-002, SCI-003/004, NUM-003, SRCH-001/002, REP-001/002 and SW-001. This preparation does not complete a numerical reproduction or release INT-001/QNT-001. AI assisted implementation and documentation.
