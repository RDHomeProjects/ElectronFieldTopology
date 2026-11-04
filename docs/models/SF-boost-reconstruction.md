# S5-B-005 reconstruction and registration contract

Prepared: UTC 2026-11-04T11:59:20.718361+00:00; Australia/Melbourne 2026-11-04T22:59:20.718361+11:00.
Implementation: `sf_reconstruction.py`, `sf_boost_study.py` and `sf_boost_local.py`.
Model: SF-relativistic-neutral-v1, metric +---, c=1 and dimensionless model time.
Requirements: NUM-001, NUM-003, REL-002, REP-001, REP-002 and VIS-001.

## Equation map and unchanged reference

The physical action, K, constraints, fixed walls, float64 precision and projected
RK4 remain those of [the physical-time specification](SF-physical-time.md) and
[the relativistic derivation](SF-relativistic.md), including the primary sources
mapped there. This study adds no evolution equation or coupling. The old
`sf_time_initial.sample_static` and `boosted_static` are unchanged and still used
by the production time driver. Published report bytes and failed gates stay intact.

The candidate is a locally derived numerical reconstruction, not a new physical
model attributed to those papers. It uses tensor cubic Hermite interpolation with
centered nodal slopes. For fractional coordinate t in a cell, the four weights at
nodes i-1,i,i+1,i+2 are

```math
w(t)=(-t/2+t^2-t^3/2,\ 1-5t^2/2+3t^3/2,\ t/2+2t^2-3t^3/2,\ -t^2/2+t^3/2).
```

The raw vector F is the product-weighted sum over 4 cubed nodes. Its coordinate
derivative differentiates these polynomials and divides by that axis spacing.
Return n=F/|F| and

```math
\partial_a n=(\partial_a F-n(n\cdot\partial_a F))/|F|.
```

This interpolates nodes and is C1 across cells, with generically third-order values
and second-order first derivatives. It is **not** a fourth-order reconstruction.
Cubic overshoot is possible; a raw norm below 1e-8 is rejected. Normalization is
applied only to the reconstructed candidate/reference, never to an evolved checkpoint
in place. Report unit/tangency and fixed-face deviations without editing the inputs.

Outside the input box, return north with zero derivative. Ghost samples are also
north. Continuity at an exterior face requires the first two nodal layers to be
north; retained fixed-face data satisfy this convention. Controls explicitly check
the join. An arbitrary non-north boundary has no claimed smooth north extension.

## Boost and independent controls

For each boost along spatial axis a, rest coordinates are
xi_a=gamma(x_a-beta*t), xi_b=x_b and gamma=(1-beta squared)^(-1/2).
The candidate initial rate is v=-gamma beta partial_a n0, differentiated through
the same normalized interpolant. A fitted D4 rate is never substituted for this
expression. Full-grid D4 transport mismatch is an observable, not a fit target
that may silently modify the data.

Before workstation measurements, separately supplied analytic theta/phi fields
and exact coordinate jets test nodes and shifted points on actual 17/33/65 input
meshes. Declared minimum convergence orders are 2.6 for off-node field values and
1.7 for first derivatives; node value error <2e-14, unit/tangency <2e-13,
constant-north join error <1e-13, derivative difference across a cell face at
epsilon=1e-8 <1e-7, and event-difference rate error <1e-8. These are instrument
controls, not physical-motion acceptance gates. Analytic jets and centered
event differences are independent of the candidate's polynomial differentiation.

## Retained-field measurements

Authenticate the original evidence archive and its complete member ledger, source
map, static field hashes and final field hashes. Replay each selected initial field
bit-exact against the original initializer. Select the dt=.01 member of each pair:
30 cases across six Q1/Q2 rest states, beta=0/.1/.3 and x/z moving directions.
This avoids repeating time-step comparisons already recorded in S5-B-004. No input
file is changed and no new trajectory is generated. Missing/corrupt data block the
dependent measurement; no reconstruction from a renderer or fresh solve is attempted.

Record old/candidate initial differences and analytic-rate/D4 mismatch over the full
lab grid and a separately labelled core excluding the original 2-unit shell. Fixed
faces are measured as generated rather than silently projected into a pass.

Comoving comparisons use one identical central rest-coordinate cube at t=0 and T,
with x_a=xi_a/gamma+beta*t and unchanged transverse axes. Its bounds stay inside
both original boxes with the declared margin. Both retained states are sampled by
the same candidate reconstruction; this introduces a sampling error and does not
refine the solver grid. Report the cube, node count and known coordinate map.

For both the original and candidate rest reference, record initial-reference and
final-reference differences. Separately compare evolved versus its own initial
comoving field. This separates a changed reference from actual retained evolution.
Keep raw full-vector residuals beside a restricted global internal phase registration:
the single SO(2) rotation about north maximizing transverse complex overlap. Record
the angle and degeneracy. Do not rotate spatial axes, refit a speed/centroid or fit
an unrestricted deformation. x/z direction and rest-state identity remain explicit.

## Interpretation and next decision

Completion is `complete_pending_review`, even if candidate controls or scientific
comparisons fail. An error means missing/corrupt inputs or failed execution. No
automatic motion gate promotion is implemented. The candidate has not been evolved;
its smaller initial residual, if observed, cannot establish better conservation,
shape persistence, boundary isolation or inertia convergence. A reference-only
improvement cannot be counted as a dynamics improvement.

The next decision selects whether a candidate deserves a focused beta=.3 x/z
evolution comparison in S5-B-006, then a third physical mesh/larger-domain study.
Preserve the Q17/Q19, Q18 fresh-start and additional-Q sequence in the register.
The [quantization-paper assessment](../literature/soliton-quantization-methods.md)
remains conditional on converged metrics; this study does not supply a quantum
spectrum, electromagnetic charge, an experiment model or electron acceptance.
Renderer settings are not inputs to any of these measurements. AI assisted the
derivation, software and report preparation; no external peer review is claimed.
