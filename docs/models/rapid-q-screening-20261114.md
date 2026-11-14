# Bounded rapid Q screening — 14 November 2026

## Scope and scientific disposition

Prepare a conservative static Skyrme–Faddeev (SF) candidate funnel over Q2–Q16. Q1 remains parked. Q2 is an authenticated prior reference. This is a separate SF task; it does not replace the active Maxwell observer/calibration analysis or transfer Maxwell measurement calibration into SF acceptance. AI assisted implementation and assessment are not scientific peer review.

Topological charge magnitude Q is an integer sector label, not electric charge and not a unique knot type. This catalogue samples two constructed variants per Q, not all configurations. Seed labels do not certify the final relaxed knot. The range is a bounded first campaign, not a mathematical upper bound on Q.

## Equation/source mapping

The objective and raw gradient are exactly the repository's float64 D4 neutral SF action in `sf_readmission.static_value_gradient`, built from `sf_time` and `skyrme.K`. Fixed north-pole exterior and the held two-layer boundary are retained. CPU stationarity uses `sf_readmission.stationarity`; the approximate finite-grid Coulomb-gauge Hopf integral uses the existing diagnostic, not an exact integer certificate. Tail fraction uses `sf_temporal_metrics.tail_band`, width 2 in model units. Source files and dependency locks are frozen by the handover's `SOURCE.json`.

The CUDA objective/gradient comes from `sf_time_gpu.CUDATime.static_value_gradient`, an array port of this same D4 action. The earlier `sf_gpu_relax` cell-based functional is deliberately excluded: energies from those different discrete functionals cannot be ranked as if identical. The new optimizer mirrors the projected Sobolev conjugate-gradient/Armijo preparation in `sf_readmission`, with its fixed sine-transform preconditioner, unit normalization and 200-iteration conjugacy resets. CUDA implements the orthonormal DST-I using an odd extension and FFT. These are optimizer iterations, not physical time, and the preconditioner shift is numerical, not a mass prediction.

The existing SF literature bibliography and model specification remain authoritative for the physics. This change adds no new physical term or external theorem assumption. Implementation references: [SciPy DST](https://docs.scipy.org/doc/scipy/reference/generated/scipy.fft.dst.html), [CuPy FFT](https://docs.cupy.dev/en/stable/reference/generated/cupy.fft.fft.html), and [CuPy timing guidance](https://docs.cupy.dev/en/stable/user_guide/performance.html).

## Frozen candidate design and budgets

Thirty variants cover fifteen Q magnitudes. Balanced axial factors and a second unbalanced/bent or trefoil-family seed provide a small, declared sample. For the trefoil construction degree is 2 alpha + 3 beta; axial degree is alpha beta. Known Q3/Q4/Q7 seed parameters reproduce the previous survey exactly. New scales follow the explicit heuristic `2.8*(Q/3)**0.25`; this is an input, not an inferred optimal scale. Cutoff is 8.8 and the box side is 23.04 throughout new branches. No automatic scale, domain or damping search is mixed into this campaign.

The broad budget is 50 accepted steps per seed on the first representation-admitted grid. Declared grids are 97, 121 and 145 cubed at fixed box size. A representation failure triggers the next grid at fixed seed parameters; it never rejects the whole Q. At most one new early-priority branch per Q continues to 200 steps total. At most six new strict static survivors receive one finer-grid, same-box warm-start confirmation, also capped at 200 steps. Confirmation capacity is spread across surviving Q values; capacity omissions are explicit deferrals. Without reuse, the upper bound is 7,950 accepted steps across these stages, excluding benchmark steps; line searches and diagnostics add work. There is no promised wall-time limit.

Known matching Q3/Q4/Q7 endpoints and Q2 are authenticated and copied from the completed local survey, then independently remeasured on CPU. Previously unresolved preparations are preserved without automatically repeating their exhausted budget. Prior static survivors do not silently gain a new motion certificate or enter the new-confirmation queue. Existing Q3 motion failures and Q4 boundary failure remain visible in the retained historical evidence.

## Decisions and measurements

Representation requires finite measured force, positive minimum corner cone, unit error below 1e-10, and approximate Hopf magnitude within 5% of the imposed Q. Strict static stationarity additionally requires relative force at most 1e-4 and maximum acceleration at most 1e-3. A static survivor additionally needs rest-tail fraction at most 0.00075. These preserve the previous gates. Passing rest-tail is only a prerequisite for later boost admission, not boosted-boundary admission itself.

| Decision | Meaning | Next action |
| --- | --- | --- |
| priority_continue | Force fell to at most 5% of its initial value within the broad budget | Allocate bounded extra static work; no prediction of final success |
| defer_slow / prior_unresolved | Current budget did not establish strict stationarity | Retain endpoint/history for later rescue; no Q rejection |
| refine_representation / defer_resolution | A declared grid does not resolve the imposed construction adequately | Try next declared grid or retain unresolved result |
| boundary_followup | Strict stationary endpoint exceeds the rest-tail gate | Separate domain/boundary study before motion |
| static_survivor | Measured finite-grid stationarity and rest-tail gates pass | Conditional same-box refinement; boost/motion gates remain pending |

Observation intervals adapt from 5 to 25 accepted steps. Force reversals and errors in a previously fitted log-linear prediction narrow the next interval; smooth trends widen it. Each next observation is recorded before it occurs. Constant, linear, quadratic and exponential force-history descriptions are compared using leave-one-out residuals. Those fits are descriptive and do not extrapolate acceptance or establish causation. Sparse observations can miss short features; this is an adaptive diagnostic cadence, not a certified search for all inflection points. Solver steps and acceptance tolerances remain unchanged.

## Retrospective evidence and limits

The exact original compact archive SHA-256 is `c066b7f2bab8308cf68945b0b6e5de837585775647634ffd721b3e84bee87517`. Its 18 preparation records include eight later-stationary endpoints and ten unresolved endpoints. The frozen early rule retains 14 records, including all eight later-stationary endpoints and six unresolved ones. All records were previously inspected; several share ancestry. Consequently these results demonstrate retrospective retention only. They are not a held-out accuracy estimate, a validated low false-negative rate, or evidence that unresolved cases are unsuitable physical sectors.

## CPU/CUDA qualification and controls

Host controls compare the FFT sine transform with independent SciPy DST, the NumPy D4 array port with the CPU reference, a directional finite variation, energy decrease and exact checkpoint continuation. Host NumPy tests do not exercise CUDA.

Before production, the workstation benchmarks every declared geometry. Actual CUDA must pass its own DST comparison, independent CPU energy/raw-gradient audits and an eight-step CPU/CUDA trajectory comparison. Timings synchronize CUDA and include CPU diagnostics and checkpoint I/O in the estimated 50-step comparison. Auto selection uses CUDA per geometry only when estimated end-to-end speedup is at least 1.20. The short benchmark is a workload sample, not a campaign-time prediction. CUDA can be explicitly requested only after passing accuracy qualification. Runtime CUDA errors stop the branch; there is no silent change of backend or precision. Rebenchmark after hardware, source, lock, package, thread or environment changes.

A separate checkout and artifact tree protect the current analysis. A read-only process guard blocks benchmark/screen while recognized EFT jobs run. It is an additional check, not a general workload scheduler. Four CPU threads are the default, no existing worker is killed, 4 GiB available host RAM is required at startup and 8 GiB disk reserve is checked during stepping. Several additional GiB may be needed for checkpoints; keep at least 30 GiB disk free and preferably 16 GiB host RAM available. Actual GPU allocation is tested on the workstation.

## Reproducibility and exit evidence

Run identity seals source, policy, package, dependency versions, threads, backend receipt and source archive. Initial/latest/stage states are float64; optimizer history and conjugacy state survive restart, together with adaptive observation scheduling. Stage-50 decisions are frozen before stage-200 outcomes, preventing later observations from leaking into early decisions. Interrupted branches resume from the last sealed checkpoint; changed identities or hashes stop. A sudden power loss between replacing a checkpoint and its seal requires manual recovery; the runner will stop on mismatch.

Browser `REPORT.html`, decision CSV, per-branch histories/fits, retained deferrals and conditional motion queue form the compact evidence. Full fields remain local and are listed with hashes; the compact ZIP excludes them. No field deletion or remote upload is automatic. Completing this screen is `complete_pending_review`; assessment/publication of the resulting evidence is a later handover. Original scientific outcomes and active roadmap priority stay unchanged by preparation.

Requirements: SCI-001, SCI-003, SCI-004, NUM-001, NUM-003, SRCH-001, SRCH-002, REP-001, REP-002.

## Handover revision 2 — missing adapter installation

The workstation comparison at 2026-11-14T09:09:39.620066+00:00 UTC / 2026-11-14T20:09:39.620066+11:00 Melbourne established that all seven CPU source files and both dependency locks match, but `sf_time_gpu.py` is missing from both checkout and fetched main. Revision 1 incorrectly assumed this module was already published.

Revision 2 bundles the exact prepared adapter bytes with SHA-256 `c6771c9a6bf69cbe3397ff8db718f4c10994a1025852d5159c3d45e589c18af3`. This is an additive source dependency, installed only in the new publication clone after its git bundle backup, included in the same PR, then strictly verified and tested. A missing adapter is allowed only in the baseline verification/installation phase; a nonmatching existing adapter always stops. Benchmark, screening and resume verify the installed clone and original retained fields, without requiring this optional adapter in the unchanged original checkout. No CPU/action/gate/policy/catalogue or dependency-lock byte is changed. The module contains array-port motion helpers, but this pack invokes only the static D4 action/gradient; it does not install or activate the separate GPU motion drivers or run a motion campaign.

Tests compare the newly installed adapter with the independent CPU implementation for fixed anisotropic, periodic and singleton grids, including derivatives, sigma action, raw static gradient, acceleration, densities and a short RK4 path. This is NumPy host execution, not CUDA evidence. The actual zbook device qualification remains mandatory before CUDA selection.
