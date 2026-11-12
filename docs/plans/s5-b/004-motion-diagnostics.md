# s5-b-004: Full-field motion diagnostics

Updated: UTC 2026-11-12T12:46:43.693315+00:00; Australia/Melbourne 2026-11-12T23:46:43.693315+11:00.

State: **assessed**. Scientific gate: **open**. State records workflow progress, not a physical claim.

## Question and scope

Separate timestep, initialization, mesh/domain and classical kinetic-metric effects in retained fields.

## Evidence and present finding

PR54 records zero mismatch in 540 endpoint comparisons, six rest metrics and 70 pairs. Initialization and domain sensitivity persist; inertia is not converged.

## Next action and exit evidence

Proceed to initialization and consistently registered initial/comoving comparisons.

Compact record integrity is confirmed; full fields remain local. Sampling grids do not replace physical resolutions.

## Traceability

Requirements: GOV-002, REP-001, REP-002.

Dependencies: [s5-b-003](003-lowq-motion.md).

[Evidence index](../../../reports/s5-b/004-motion-diagnostics/README.md).

- [docs/plans/sf-motion-diagnostics.md](../sf-motion-diagnostics.md)
- [docs/literature/soliton-quantization-methods.md](../../literature/soliton-quantization-methods.md)
