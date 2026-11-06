# s0-003: Full workstation archives and temporary-cache policy

Updated: UTC 2026-11-06T12:55:56.848597+00:00; Australia/Melbourne 2026-11-06T23:55:56.848597+11:00.

State: **assessed**. Scientific gate: **not-applicable**. State records workflow progress, not a physical claim.

## Question and scope

Can every surviving project dataset and local Git state be restored from GitHub before local copies are removed?

## Evidence and present finding

Archive 20261104t023917z-b0d06afa is published with 38 roots and verified full payloads. PR56 merged the compact catalog. The reviewed workstation log records successful cleanup of 36 obsolete roots at 2026-11-04T11:31:00Z / 22:31:00 AEDT; administrative checkout and low-Q input cache remain.

## Next action and exit evidence

Include the exact cleanup receipt in this preparation PR; retain one checkout and the low-Q input cache for S5-B-005. Archive and verify new unique results before future cleanup.

A versioned Git catalog anchors release assets; every file hash and Git graph is restore-verified; source changes block cleanup. No deletion from a size listing alone.

## Traceability

Requirements: GOV-001, GOV-002, REP-001, REP-002.

Dependencies: [s0-002](002-repository-governance.md).

[Evidence index](../../../reports/s0/003-workstation-archives/README.md).

- [docs/governance/workstation-archives.md](../../governance/workstation-archives.md)
