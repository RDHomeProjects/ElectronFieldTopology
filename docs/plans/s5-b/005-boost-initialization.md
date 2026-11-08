# s5-b-005: Boost initialization and field registration

Updated: UTC 2026-11-08T01:09:15.758801+00:00; Australia/Melbourne 2026-11-08T12:09:15.758801+11:00.

State: **assessed**. Scientific gate: **open**. State records workflow progress, not a physical claim.

## Question and scope

Can a smoother, consistently differentiated reconstruction improve boost consistency without changing the action?

## Evidence and present finding

S5-B-005 assessed 30 retained Q1/Q2 cases. Cubic analytic-rate/D4 mismatch falls from 5.99–10.98% to 0.83–2.67% across all 24 moving cases (75.56–86.13% reduction). Twelve raw beta=.1 candidates violate the fixed layers; they require explicit readmission before a focused motion comparison. No cubic-initialized trajectory has been evolved.

## Next action and exit evidence

Use the assessment and ADR-0013 to implement fixed-layer readmission before the focused S5-B-006 method comparison. Preserve original gates and all candidate boundary failures.

Authenticated 30-case compact evidence, independent control replay, raw/registered residuals and fixed-layer findings recorded in a separate immutable assessment. Candidate promotion remains conditional; no new dynamics acceptance.

## Traceability

Requirements: NUM-001, NUM-003, REL-002, REP-001, REP-002, VIS-001.

Dependencies: [s5-b-004](004-motion-diagnostics.md).

[Evidence index](../../../reports/s5-b/005-boost-initialization/README.md).

- [docs/models/SF-boost-reconstruction.md](../../models/SF-boost-reconstruction.md)
- [docs/models/SF-physical-time.md](../../models/SF-physical-time.md)
- [docs/literature/soliton-quantization-methods.md](../../literature/soliton-quantization-methods.md)
- [docs/decisions/ADR-0013-conditional-cubic-initialization.md](../../decisions/ADR-0013-conditional-cubic-initialization.md)
