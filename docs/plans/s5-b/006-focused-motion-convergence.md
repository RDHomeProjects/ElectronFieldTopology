# s5-b-006: Focused motion, mesh and domain convergence

Updated: UTC 2026-11-04T13:35:35.703463+00:00; Australia/Melbourne 2026-11-05T00:35:35.703463+11:00.

State: **planned**. Scientific gate: **open**. State records workflow progress, not a physical claim.

## Question and scope

Which residuals survive improved initialization, a third physical mesh and a larger matched-spacing box?

## Evidence and present finding

S5-B-005 supports a conditional cubic comparison but found fixed-layer deviations in all 12 beta=.1 raw candidates. New candidate trajectories and motion/convergence acceptance remain untested.

## Next action and exit evidence

First implement thin-north-layer x/z controls and explicit candidate fixed-layer readmission, recording pre/post n/v corrections and free-node chain-rule consistency. Only then prepare a focused beta=.3 Q1/Q2 x/z old-versus-cubic comparison before temporal, third-mesh and larger matched-spacing box decisions.

Boundary-consistent initial data with recorded corrections; matched rest states, model action, precision, observation windows and predeclared gates; eight nominal method-comparison arms assessed before any wider sweep. Separate initialization, temporal, physical-grid, domain, tail and inertia effects. No silent D4-fitted velocity, gate changes or automatic isolation claim.

## Traceability

Requirements: NUM-002, NUM-003, BND-001, REL-002, REP-001, REP-002.

Dependencies: [s5-b-005](005-boost-initialization.md).

[Evidence index](../../../reports/s5-b/006-focused-motion-convergence/README.md).

- [docs/models/SF-physical-time.md](../../models/SF-physical-time.md)
- [docs/decisions/ADR-0013-conditional-cubic-initialization.md](../../decisions/ADR-0013-conditional-cubic-initialization.md)
