# s5-b-002: Physical-time solver and independent renderer controls

Updated: UTC 2026-11-14T02:53:01.801788+00:00; Australia/Melbourne 2026-11-14T13:53:01.801788+11:00.

State: **assessed**. Scientific gate: **bounded**. State records workflow progress, not a physical claim.

## Question and scope

Validate the time solver independently and keep renderer sampling separate from science.

## Evidence and present finding

Wave/manufactured controls, checkpoint/resume and export invariance are recorded. An animation is not physical acceptance.

## Next action and exit evidence

Preserve the reference controls and renderer contract during future initializer work.

Scientific grid, precision and integration remain independent of optional display exports.

## Traceability

Requirements: GOV-002, REP-001, REP-002.

Dependencies: [s5-b-001](001-dynamics-admission.md).

[Evidence index](../../../reports/s5-b/002-solver-renderer-controls/README.md).

- [docs/models/SF-physical-time.md](../../models/SF-physical-time.md)
- [docs/offline-renderer.md](../../offline-renderer.md)
