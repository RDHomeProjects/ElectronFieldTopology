# Neutral SF dynamics admission: preparation report

Prepared: 2026-11-02T08:48:53+00:00 UTC;
2026-11-02T19:48:53+11:00 Australia/Melbourne.

## Finding and scope

PR50 merged the stationary Q18/neighbour campaign at 4193a72. The requested
motion-at-speed assessment requires a new physical-time solver: none is present in
that merged static campaign. This tranche supplies its explicit neutral action,
constraints, stress tensor and admission analysis, then leaves full evolution as the
next implementation gate. The [model specification](../../docs/models/SF-relativistic.md)
defines what is and is not measured. It does not reopen the deferred charged solver.

The [small instrument record](instrument-validation.json) verifies action derivatives,
independent spacetime two-form contraction, tensor covariance, an independent static
cell energy, the stress-trace identity and direct versus tensor-integrated boosts.
These are measured software controls on manufactured inputs. The record contains
the actual UTC/Melbourne start/end timestamps and numerical errors.

The new automated tests also cover generic nonzero-time jets and target rotations,
the exact great-circle light-speed wave limit, vacuum kinetics, slab independence,
native C/independent NumPy energy agreement, resolved interpolation, geodesic nodal
variations, source metadata/hashes, missing fields, partial publication and retention
of negative scientific results. Test counts/timing and handoff installation checks
are recorded in validation.json when the handoff is finalized.

## Workstation analysis prepared

All 31 original endpoint hashes, run commit and published raw-record hashes are
frozen in the configuration. Six endpoints receive four smooth directional-curvature
probes at three amplitudes; all endpoints receive stress, kinetic, localization and
18 speed/axis comparisons. The read-only source field must be original float64 with
matching model, Q label, config hash, grid, spacing, unit norm and fixed faces. Full
fields remain local. Missing inputs are explicit partial outcomes rather than new
initial data or hidden recomputations.

No new scientific workstation results are claimed in this preparation. In particular,
no pointwise rest kinetic bound, four positive trial curvatures, or exact tensor boost
identity establishes full dynamical stability, a moving electron or a new physical
discovery. The complete local outputs must be assessed before choosing a higher-Q
moving candidate. Do not rank different Q sectors by raw energy as if they were the
same constrained minimization problem.

## Runtime and recovery

Synthetic timings on the preparation host were 0.770 s for 33³ and 5.962 s for 65³,
with the timestamped command output recorded during preparation, using the same
NumPy slab integral without curvature. These are synthetic fields and not RTX/GPU or
workstation timings. Larger integrations and perturbations add work; no workstation
duration is asserted from them. CPU throughput and laptop temperature can change
runtime substantially. There is no two-hour overall stop condition.

Each endpoint is atomically saved and can be retained on resume. A background lock
prevents duplicate launches. A complete/partial marker and separate worker exit record
distinguish stopped, successful, partial and unexpected-failure cases. Evidence collection
includes timestamps, source/config identity, numerical checks and explicit limitations;
it excludes bulk NPZ fields. See the [local plan](../../docs/plans/sf-dynamics-admission.md).

## Following gates and retained Q work

Next: independently validated physical-time equations and low-Q controls, then one
converged higher-Q free-flight benchmark. Compare multiple grids, time steps and
domains; include energy/momentum/flux, centroid motion, tails, constraint defects,
perturbations and topology. Speeds .75/.9 require stronger longitudinal resolution
and validated boundaries, not merely a compressed image.

Return to Q18 fresh 129/193 amplitude-4 starts and the incomplete amplitude-1 fine-grid
conditioning test, followed by additional source-grounded Q values. Existing linked
Q18 findings and failed hyperbolic reproduction stay recorded. S6 interactions and
S7 quantum/experimental gates remain separate. AI assisted the derivation and code;
no external scientific peer review is claimed.
