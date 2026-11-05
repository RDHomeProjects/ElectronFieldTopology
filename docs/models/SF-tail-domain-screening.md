# S5-B-008: stationary tail-domain screening

UTC: 2026-11-05T05:06:55.459022+00:00; Australia/Melbourne: 2026-11-05T16:06:55.459022+11:00.

## Aim and model

Sole question: can L=17.92 or L=20.16 mitigate the original outer-shell energy failure while retaining a comparable stationary core? The user requested this diagnostic before the previously planned temporal audit. This does not launch motion, a timestep/physical-mesh sweep, an L24 test, a new Q catalogue, charge or spin work.

Use the established [neutral time-lattice action](SF-physical-time.md), [relativistic conventions](SF-relativistic.md) and Jennings static source map in [SF-J2015](SF-J2015-static.md). The same continuum coefficients and D4 nodal Hamiltonian/gradient are used. The `sf_readmission.relax` projected Sobolev-CG optimizer is reused unchanged. Optimizer iterations are not physical time. Metric +--- for the parent theory, c=1; these stationary measurements use dimensionless model lengths/energies, CPU float64, zero field rate. The GPU cell-static optimizer uses a different discrete functional and is not substituted here.

## Declared experiment

|Role|Side|Rest nodes per axis|Spacing|
|---|---:|---:|---:|
|Matched control|16.00|101|0.16|
|Requested test|17.92|113|0.16|
|Requested test|20.16|127|0.16|

Run Q1 and Q2 for all three domains: six stationary readmissions. Attempt both requested larger domains regardless of whether the smaller passes. No scaling of the source field, energy values or coefficients. No interpolation, fitted translation, phase registration or smoothing. The source is the retained original low-Q campaign, evidence SHA-256 `780cfff1d5be5fe9e61b238206aceb6a6f47a82350e8ce257c76cc79f56d8784`, using only its two n101/L16 stationary checkpoints.

Create each initial field by exact centred copying of every original float64 node into the new equal-spacing grid and north vacuum outside. The two original fixed layers become free where they are interior to a larger domain. Hold only the two outer layers of the new domain. Record the initial measurement before relaxation: the outer shell has moved, so an initial lower fraction is a geometric control, not an equilibrated larger-box solution. This exact continuation can retain old finite-box deformation until it relaxes; the experiment explicitly measures that adjustment. It is not an independent fresh-seed basin study or a guarantee of a global energy minimum.

The same operation at L16 supplies a contemporaneously readmitted control. Every new optimization uses stricter **preparation** targets: relative force <=1e-4 and maximum acceleration <=1e-3 (original targets 1e-3 and 1e-2). This helps distinguish the domain change from the fairly loose stationarity of the retained inputs. The original thresholds are also reported, not replaced. Q quadrature remains within 5%, cell-corner cone positive, unit error <1e-10. These constraints do not certify exact topology or stability. There is no requirement to minimize the tail fraction: relaxation minimizes the original Hamiltonian, not a shell penalty.

Initialize the unchanged optimizer via a model-correct iteration-zero continuation checkpoint and its ordinary manifest/history format. Config binds the source rest hash and full initial-state hash. This avoids falsely labelling a time-lattice field as a cell-static checkpoint. Direct-control tests compare an externally initialized optimizer run to its normal rational-seed entry on the same field, without changing its numerical code.

## Measurements and decision boundary

The original criterion is unchanged: energy in the outer **two model-length units** divided by total continuum diagnostic energy <=0.001 (0.1%). Use the original `sf_time.densities` continuum diagnostic and nodal predicate any(abs(x_i)>=L/2-2), including the original discretization convention. It is not Hamiltonian drift, missing energy outside the box, a reflection coefficient or a complete isolation test. Also report absolute shell energy and total discrete Hamiltonian so a changing denominator is visible.

For each initial/final state record:

- Hamiltonian, continuum energy, absolute/fractional moving-shell energy, unit/fixed-layer constraints, stationarity, Hopf quadrature, corner cone, radius95/radius99, energy centroid and integrated stress.
- Energy outside fixed original coordinates abs(x_i)>=6, and outside the original L16 footprint abs(x_i)>8, plus fixed-coordinate cumulative cube profiles. These separate moving the shell from changing the field distribution.
- All final pairwise comparisons per Q on the identical central 73-cubed nodes (side11.52) and original 101-cubed footprint (side16). Compute derivatives on each full domain before cropping density. No new coordinate/phase fit removes differences. Report full-state field differences, common-region energies and density L1 differences descriptively.

A tail pass is meaningful only alongside stationary/constraint/topology qualification. No new automatic domain-independence tolerance is invented for a convenient pass. Compare old input, newly readmitted L16 control and larger boxes in the later scientific assessment. A post-relaxation pass identifies a potential boundary correction; moving-grid trials still need their own initialization, time-window and convergence checks. A rest pass cannot authorize motion automatically. Failed/stagnant/unresolved cases remain evidence.

## Execution and recovery

Readmission batches are 200 optimization iterations, with atomic checkpoints/diagnostics every25 and the existing three-stagnant-pass/Armijo/topology stop rules. No overall wall-time or pass cap; numerical stagnation is an unresolved result. Preserve and continue other declared domains after a numerical qualification failure. Integrity failures stop the campaign. Linux PID/start/boot identity protects background status/stop; heartbeat every30seconds. Resume checks original inputs, code/config identity and checkpoint metadata/constraints. A hard kill can leave a new unsealed checkpoint; atomic NPZ CRC and embedded identity checks apply, without claiming prior external hash sealing. Resuming resets conjugate-gradient memory as in the original optimizer and may change the optimization path; it is not bit-exact uninterrupted optimization.

All result/analysis metadata, CSV rows, logs and figures have UTC and Australia/Melbourne stamps. SUMMARY.md and evidence.zip indicate complete_pending_review or complete_with_unresolved_pending_review; a stopped process alone is not completion. No renderer or preview arrays are required for this diagnostic. The final tail plot is an analysis product, not solver input.

## Retention and publication

One checkout `~/ElectronFieldTopology-repository-admin`, branch `work/s5-b-008-tail-domain`; artifacts under `artifacts/s5-b/008-tail-domain-screening/<UTC-id>/`. Original fields are read-only and rehashed after the run. New compact runs use `reports/s5-b/008-tail-domain-screening/runs/<id>/`; assessments append separately. Do not edit original run or assessment bytes. A one-root GitHub Release archive of this new run, using the existing archive engine, retains all initial/latest checkpoints, logs and a verified copy of the runnable handover; register the verified catalog before merge or cleanup. No local deletion is performed. PR metadata updates use REST, avoiding the obsolete Projects Classic query in older `gh pr edit`.

After this tail-specific assessment, return to S5-B-006 temporal sentinels and the remaining physical convergence decisions. Higher-Q, Q18/additional-Q and quantum/probe ordering remains unchanged. Requirements NUM-001/002/003, BND-001, REP-001/002, SCI-003/004. AI-assisted preparation; no native result or scientific acceptance is claimed by software tests.
