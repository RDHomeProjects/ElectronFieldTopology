# s0-003: Full workstation archives and temporary-cache policy

Updated: UTC 2026-11-04T09:13:37.867474+00:00; Australia/Melbourne 2026-11-04T20:13:37.867474+11:00.

State: **assessed**. Scientific gate: **not-applicable**. State records workflow progress, not a physical claim.

## Question and scope

Can every surviving project dataset and local Git state be restored from GitHub before local copies are removed?

## Evidence and present finding

Archive 20261104t023917z-b0d06afa contains 38 workstation roots, 12873 payload files and 32,272,522,204 bytes. All remote payload hashes were checked. Compact catalog is staged for Git publication; no source deletion was performed.

## Next action and exit evidence

Publish the compact catalog and review unchanged local candidates while retaining one active checkout and datasets needed for the next study.

A versioned Git catalog anchors release assets; every file hash and Git graph is restore-verified; source changes block cleanup. No deletion from a size listing alone.

## Traceability

Requirements: GOV-001, GOV-002, REP-001, REP-002.

Dependencies: [s0-002](002-repository-governance.md).

[Evidence index](../../../reports/s0/003-workstation-archives/README.md).

- [docs/governance/workstation-archives.md](../../governance/workstation-archives.md)
