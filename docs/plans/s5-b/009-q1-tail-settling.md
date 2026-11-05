# s5-b-009: Paired Q1 stationary tail settling

Updated: UTC 2026-11-05T20:58:49.887092+00:00; Australia/Melbourne 2026-11-06T07:58:49.887092+11:00.

State: **prepared**. Scientific gate: **open**. State records workflow progress, not a physical claim.

## Question and scope

Does deeper Q1/L20.16 settling or aligned L22.08 mitigate the rest tail failure while retaining comparable field state?

## Evidence and present finding

Overnight-capable paired preparation is ready; no native campaign result yet. Both arms start from the same authenticated S5-B-008 Q1 endpoint. Existing Q2 passes and Q1 failures remain unchanged.

## Next action and exit evidence

Execute the paired Q1 L20.16/n127 and L22.08/n139 settling study at h=.16, preserve all observation fields in a verified Release archive and assess tail/core histories before motion. Up to1200 optimizer iterations per arm; no wall-time cutoff or automatic downstream matrix.

Authenticated source; separated100-iteration observations with tighter force/core/tail settling; original0.1% shell gate; matched-region comparisons; all failures/budget endpoints retained and full fields download-verified; later scientific assessment.

## Traceability

Requirements: NUM-001, NUM-002, NUM-003, BND-001, REP-001, REP-002.

Dependencies: [s5-b-008](008-tail-domain-screening.md).

[Evidence index](../../../reports/s5-b/009-q1-tail-settling/README.md).

- [docs/models/SF-q1-tail-settling.md](../../models/SF-q1-tail-settling.md)
- [docs/models/SF-physical-time.md](../../models/SF-physical-time.md)
- [docs/decisions/ADR-0015-stationary-tail-domain-assessment.md](../../decisions/ADR-0015-stationary-tail-domain-assessment.md)
