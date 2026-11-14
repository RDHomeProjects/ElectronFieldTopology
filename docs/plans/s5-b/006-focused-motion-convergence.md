# s5-b-006: Focused motion, mesh and domain convergence

Updated: UTC 2026-11-14T09:25:42.642598+00:00; Australia/Melbourne 2026-11-14T20:25:42.642598+11:00.

State: **assessed**. Scientific gate: **open**. State records workflow progress, not a physical claim.

## Question and scope

Which residuals survive improved initialization, a third physical mesh and a larger matched-spacing box?

## Evidence and present finding

The boundary-admitted T1 temporal tranche is assessed: six complete trajectories, zero failures across 126 recorded tail observations, near-fourth-order fixed-grid refinement. Q2 passes all seven original case gates; Q1 retains 1.563660% speed error against 1%. All 128 full archive files/52 NPZ records and matched-time fields were independently verified; historical failed milestones are retained.

## Next action and exit evidence

Keep Q2 numerical/physical-mesh/domain controls available alongside the authorized S5-B-010 fresh-candidate survey. A failed short reference blocks that survey. Q1 correction stays parked; do not repeat completed temporal work without a diagnostic reason.

Temporal tranche assessed on Q1 L24.32/Q2 L20.16 at beta=0.3/T=1. S5-B-006 remains open for independent physical-mesh/domain and observation-window convergence, speed/momentum/shape gates and qualified classical-inertia sensitivity before higher-Q/quantum work. Original focused-motion and stationary-tail failures remain unchanged.

## Traceability

Requirements: NUM-002, NUM-003, BND-001, REL-002, REP-001, REP-002.

Dependencies: [s5-b-005](005-boost-initialization.md).

[Evidence index](../../../reports/s5-b/006-focused-motion-convergence/README.md).

- [docs/models/SF-focused-motion.md](../../models/SF-focused-motion.md)
- [docs/models/SF-physical-time.md](../../models/SF-physical-time.md)
- [docs/decisions/ADR-0013-conditional-cubic-initialization.md](../../decisions/ADR-0013-conditional-cubic-initialization.md)
- [docs/decisions/ADR-0014-focused-motion-assessment.md](../../decisions/ADR-0014-focused-motion-assessment.md)
- [docs/decisions/ADR-0016-q1-tail-settling-assessment.md](../../decisions/ADR-0016-q1-tail-settling-assessment.md)
- [docs/models/SF-admitted-temporal.md](../../models/SF-admitted-temporal.md)
- [docs/decisions/ADR-0017-admitted-temporal-assessment.md](../../decisions/ADR-0017-admitted-temporal-assessment.md)
- [docs/decisions/ADR-0019-higher-q-preparation-assessment.md](../../decisions/ADR-0019-higher-q-preparation-assessment.md)
