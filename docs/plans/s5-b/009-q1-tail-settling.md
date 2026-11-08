# s5-b-009: Paired Q1 stationary tail settling

Updated: UTC 2026-11-08T13:31:39.521682+00:00; Australia/Melbourne 2026-11-09T00:31:39.521682+11:00.

State: **assessed**. Scientific gate: **open**. State records workflow progress, not a physical claim.

## Question and scope

Does deeper Q1/L20.16 settling or aligned L22.08 mitigate the rest tail failure while retaining comparable field state?

## Evidence and present finding

Paired Q1 full fields independently replayed. L20.16 remains a 0.120638% rest-tail failure; L22.08 passes at 0.081394% with tight final endpoint stationarity. Both native unresolved labels remain because the regular-endpoint settling certificate is unmet. Common-core raw-field domain difference is 1.66%; no isolated-motion acceptance.

## Next action and exit evidence

Retain the bounded L22.08 stationary reference and both native labels; use a versioned small controller/reporting audit before future reuse, then return to S5-B-006 temporal and matched-domain motion convergence. No repeated overnight stationary run is launched.

Both requested arms assessed, all 52 archived payload files and 12 NPZ checkpoints/eight unique states verified, settling/controller logic and three full-field domain regions replayed. Rest-shell correction is bounded; prescribed settling, domain independence and motion remain open.

## Traceability

Requirements: NUM-001, NUM-002, NUM-003, BND-001, REP-001, REP-002.

Dependencies: [s5-b-008](008-tail-domain-screening.md).

[Evidence index](../../../reports/s5-b/009-q1-tail-settling/README.md).

- [docs/models/SF-q1-tail-settling.md](../../models/SF-q1-tail-settling.md)
- [docs/models/SF-physical-time.md](../../models/SF-physical-time.md)
- [docs/decisions/ADR-0015-stationary-tail-domain-assessment.md](../../decisions/ADR-0015-stationary-tail-domain-assessment.md)
- [docs/decisions/ADR-0016-q1-tail-settling-assessment.md](../../decisions/ADR-0016-q1-tail-settling-assessment.md)
