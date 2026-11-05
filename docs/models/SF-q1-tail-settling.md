# S5-B-009: paired Q1 stationary tail settling

UTC: 2026-11-05T20:58:49.887092+00:00; Australia/Melbourne: 2026-11-06T07:58:49.887092+11:00.

## Question and source map

Does the retained Q1/L20.16 endpoint change with deeper settling, and does an aligned L22.08 box mitigate its 0.120632% tail without unacceptable core changes? This implements the paired follow-up in [ADR-0015](../decisions/ADR-0015-stationary-tail-domain-assessment.md). It is stationary preparation, preceding the remaining S5-B-006 temporal sentinels. Q2's passing rest references, Q18/additional-Q negative results and later motion/quantization/probe milestones remain unchanged.

Use the unchanged [D4 physical-time action and energy](SF-physical-time.md), [neutral relativistic conventions](SF-relativistic.md), and [Jennings Eq.2.1 source map](SF-J2015-static.md). Parent metric +---, c=1, K=(32*pi^2*sqrt(2))^-1; dimensionless lengths/energies, CPU float64, zero field rate. This is an optimizer calculation, never elapsed physical time. Original sf_readmission/static_value_gradient, sf_time, sf_dynamics and skyrme files stay byte-identical. No cell-static GPU substitution or new physics. No new source equation is introduced.

## Paired experiment and overnight allocation

|Arm|Side|Nodes per axis|Spacing|Starting core|
|---|---:|---:|---:|---|
|Deeper settling control|20.16|127|0.16|Retained Q1/L20.16 endpoint, exact copy|
|Domain correction|22.08|139|0.16|Same endpoint, centred north extension by six nodes per face|

Input is S5-B-008 run `20261105t053203z-576d1edc`, checkpoint `readmission/q1-n127-L20.16/latest.npz`, SHA-256 `2eafd171bf4f8bb184b89cadb63435970d8eb8b8c44496d61e8d576c237dd343`; field-state SHA `5d56a1586f7bae19c1ee90e208a096556ba3d226eddc1d2b870bee924fb7d832`. Authenticate published config/model/scheme/code/geometry and unit/fixed-layer constraints. If missing locally, restore its authenticated 74-file root from GitHub Release `archive-workstation-20261105t063134z-4cd07212` using the existing restore engine and pinned Git catalog. No silent field regeneration or overwriting restored roots. Both arms start independently from the same published endpoint; the larger arm does not inherit a newly polished smaller arm.

Allocate up to 1200 actual projected-CG iterations per arm (2400 total), 200-iteration restart batches, latest checkpoint every 25 accepted iterations and a retained full-field observation every 100. The numerical CG update (objective, gradient, tangent projection, Sobolev preconditioner, Armijo/cone checks) is copied verbatim from the established optimizer. Only observation/controller/provenance rules differ. Tests compare first accepted steps bit-for-bit. There is no wall-time cutoff, idle padding or tolerance adjustment to consume the night. Stop earlier on qualified settling, numerical stagnation, a topology/constraint problem or user stop; attempt the other domain after a numerical qualification failure. Integrity failures stop the campaign.

The prior native n127 arm took 645.76seconds for 50 iterations. Simple scaling gives 4.31hours for1200 iterations at n127 and 5.63hours at n139 (volume ratio1.311), about 9.94hours before extra measurements/line searches. Allow roughly10–14hours if the allocation is consumed; this is a planning estimate, not a guaranteed finish time. Tight residuals may slow line search, or convergence/stagnation may finish substantially earlier. No longer physical-time evolution is implied. Iteration-budget exhaustion is retained as unresolved, not a pass; any extension requires a separately recorded study decision.

## Predeclared preparation settling criteria

All conditions below are separate from the original shell acceptance criterion:

- Relative force <= 1e-9 and maximum acceleration <= 1e-8, rather than the earlier preparation 1e-4/1e-3; Hopf magnitude within 5% of 1, positive corner cone and unit error <1e-10.
- Three successive **distinct 100-iteration intervals**, each with tail-fraction change <=1e-7 (absolute fraction), absolute shell-energy change <=1e-7 model units, central73-cubed raw-field relative L2 change <=1e-5, and relative Hamiltonian change <=1e-9.
- No identical zero-iteration sampling may satisfy settling. A final irregular stop sample is retained but cannot stand in for a100-iteration observation. Qualify only at the iteration of the latest regular observation.

These are conservative optimizer-settling diagnostic thresholds, not new physical domain-independence tolerances. Very tight residuals may encounter float64/line-search limits; this is an unresolved finding, not grounds to weaken them. Retain the existing Armijo stall and three stagnant full-batch stop rule, with predeclared1e-14 relative-energy change for this deeper preparation. No tail penalty enters the minimized Hamiltonian. A stable tail can still fail0.1%; a shell pass can still lack settled force/core measurements.

## Measurements and interpretation

Keep the original shell width2 and fraction <=0.001 (0.1%), using the established continuum energy diagnostic and original nodal shell predicate. Record initial extension separately from all relaxed observations. Report absolute shell energy, denominator, Hamiltonian, stress, centroid, r95/r99, Hopf/unit/cone/force, and original 1e-4/1e-3 preparation status as well as tighter qualification. Fixed-coordinate outside-cube profiles at 4/5/6/7/8/9 use canonical integer offsets times0.16, avoiding a floating-point face-plane mismatch in L22.08/138. The moving-shell predicate is retained unchanged.

Compare final domains in the same central73-cubed (side11.52), original 101-cubed (side16), and127-cubed source footprint (side20.16). Derivatives are evaluated on each full domain before cropping. No fitted scale/translation/phase/rotation. Preserve raw field differences and density L1/energy differences; no automatic domain-independence threshold. Report settling histories against the original archived endpoint so a lower moving-shell fraction cannot conceal core drift.

A settled stationary shell pass is a potential correction only. It does not measure reflections, a physical-grid limit, isolated transport, stability, electromagnetic charge, quantum spin or electron behavior. After assessment, return to the planned T=1 cubic Q1/x and Q2/z dt=.01/.005/.0025 temporal sentinels; further motion domains/physical meshes require their own readmission and controls. This run does not launch those downstream matrices.

## Lifecycle, preservation and publication

Use consolidated checkout `~/ElectronFieldTopology-repository-admin`, branch `work/s5-b-009-q1-tail-settling`, outputs `artifacts/s5-b/009-q1-tail-settling/<UTC-id>/`. Installer verifies pinned main, makes a complete-history Git bundle and stages only this preparation. No reset, deletion, old report edit or GitHub write is part of installation. Existing untracked artifacts survive.

Background worker records Linux process identity, heartbeat 30seconds, timestamps in UTC and Australia/Melbourne, start/exit/status and immutable source/config hashes. Stop retains state; resume revalidates inputs/code/config/checkpoint CRC/metadata and constraints, with CG history reset as in the established optimizer. It is not a bit-exact uninterrupted restart. Completed runs are immutable. Same observation history cannot qualify changed fields or a newer-than-checkpoint observation. A hard kill may leave a newer atomic checkpoint with no external seal; embedded identities apply and it is not described as externally sealed.

Publish compact evidence and generated plan/status changes into canonical `reports/s5-b/009-q1-tail-settling/runs/<id>/`. Archive the **entire new run**, including initial/latest and every 100-iteration observation field, logs and verified runnable handover, using the existing one-root GitHub Release archive/download-verification engine. Register its verified Git catalog before merge. No local cleanup is automatic. PR metadata uses REST; merge waits for hosted checks and exact head. Completion means all declared arms recorded pending scientific assessment, including unresolved arms.

Requirements: NUM-001/002/003, BND-001, REP-001/002, SCI-003/004. AI-assisted software/preparation; controls are not native overnight results or external scientific peer review.
