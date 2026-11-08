# ADR-0017: admitted temporal assessment and the remaining physical-grid tests

UTC: 2026-11-08T01:09:15.758801+00:00; Australia/Melbourne: 2026-11-08T12:09:15.758801+11:00.

Status: proposed for maintainer publication with PR61. Study: S5-B-006.

## Evidence

[The new immutable assessment](../../reports/s5-b/006-focused-motion-convergence/assessments/20261108t010058z-672ebb4c/ASSESSMENT.md) independently checks the compact measurements and all 128 full archived files,52 NPZ records, six final motion states and matched-time field/rate refinements. Larger admitted boxes give zero failures in126 recorded width 2 tail observations. Original thresholds and historical failures remain.

At beta 0.3/T=1, Q2 passes all seven case gates at dt=0.01/0.005/0.0025. Q1 retains a1.563660% speed error against the1% limit while its other six gates pass. Reportable temporal orders are near4; below-floor Q2 quarter-time field order remains unreported. Temporal refinement changes Q1 centroid speed by only about 1.14e-10.

## Decision

Record the boundary-admitted temporal tranche as assessed, while keeping the S5-B-006 scientific gate open. Preserve the009 native unresolved labels and distinguish strict endpoint qualification, preceding regular stability and final-observation regularity. Make no numerical, threshold or historical-record edits.

Next prioritize same-grid known-coasting/zero-speed centroid controls and consistent initialization diagnostics; then at least three physical spacings at fixed box, plus matched-spacing domain pairs and conditional crossed-direction controls. Use the present temporal result to avoid an unnecessary broad repeated dt sweep, with a limited confirmation at the future finest spatial mesh. Freeze the feasible new matrix before launching it.

Do not infer spatial accuracy from energy drift or temporal order, and do not infer absent boundary influence from low shell energy. Retain the historical trilinear shape gate, separately label cubic/comoving references, and keep analytic beta/rate unchanged. No taper, compression, fitted-speed correction or relaxed gate is used.

## Consequences and plan

The admitted Q1 L24.32 and Q2 L20.16 states become bounded references for this next test, with preparation and discretization authenticated. Higher-Q Q17/Q19 motion remains conditional; fresh Q18 and additional-Q investigation remains registered. Quantum/spin/probe milestones retain their stated prerequisites. ADR0014/0016 remain as historical decisions; this adds evidence and selects the next numerical question without superseding their measurements.

The roadmap register, generated status/plans/indexes and requirement evidence mapping are updated in the same publication. The full run stays in its verified Release and Git catalog. This change adds reports and documentation; it does not modify the solver, physical assumptions or archived assets.
