# s5-b-005: Boost initialization and field registration

Updated: UTC 2026-11-04T11:59:20.718361+00:00; Australia/Melbourne 2026-11-04T22:59:20.718361+11:00.

State: **prepared**. Scientific gate: **open**. State records workflow progress, not a physical claim.

## Question and scope

Can a smoother, consistently differentiated reconstruction improve boost consistency without changing the action?

## Evidence and present finding

Independent reconstruction controls and targeted software tests passed. The existing 5.99–10.98% field-rate mismatch remains a prior observation; retained-field old/candidate measurements await local execution.

## Next action and exit evidence

Run the checkpointed read-only 30-case dt=.01 initialization/registration study on the retained Q1/Q2 fields, preserving the original solver and gates; assess before S5-B-006.

Document the interpolant and its derivatives, normalization/tangency, independent accuracy/order and preserved old reference. Do not replace velocity with a fitted D4 derivative merely to erase the residual. Register field symmetries consistently without hiding x/z dependence.

## Traceability

Requirements: NUM-001, NUM-003, REL-002, REP-001, REP-002, VIS-001.

Dependencies: [s5-b-004](004-motion-diagnostics.md).

[Evidence index](../../../reports/s5-b/005-boost-initialization/README.md).

- [docs/models/SF-boost-reconstruction.md](../../models/SF-boost-reconstruction.md)
- [docs/models/SF-physical-time.md](../../models/SF-physical-time.md)
- [docs/literature/soliton-quantization-methods.md](../../literature/soliton-quantization-methods.md)
