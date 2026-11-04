# s5-b-006: Focused motion, mesh and domain convergence

Updated: UTC 2026-11-04T11:59:20.718361+00:00; Australia/Melbourne 2026-11-04T22:59:20.718361+11:00.

State: **planned**. Scientific gate: **open**. State records workflow progress, not a physical claim.

## Question and scope

Which residuals survive improved initialization, a third physical mesh and a larger matched-spacing box?

## Evidence and present finding

No new production run is claimed. Q1 tail and inertia remain domain-sensitive; Q2 low-speed results are provisional bounded references.

## Next action and exit evidence

After the initializer decision, run a small beta=.3 x/z comparison before selecting third-h and larger-Q1-box controls. Preserve action, precision and predeclared gates.

Separate starting-state, temporal, spatial and domain effects; quantify tails, momentum, shape and inertia. A tail pass alone does not validate inertia or isolation.

## Traceability

Requirements: NUM-002, NUM-003, BND-001, REL-002, REP-001, REP-002.

Dependencies: [s5-b-005](005-boost-initialization.md).

[Evidence index](../../../reports/s5-b/006-focused-motion-convergence/README.md).

- [docs/models/SF-physical-time.md](../../models/SF-physical-time.md)
