# ADR-0012: Canonical stage catalogs and preserved evidence paths

Recorded: UTC 2026-11-04T01:00:23.956083+00:00; Australia/Melbourne 2026-11-04T12:00:23.956083+11:00.
Status: proposed in this administrative change; effective on merge.

## Context

PR54 completes the latest diagnostic review, while root navigation still schedules
it as the next run. Nineteen report roots mix stages, dates, preparations and campaigns.
Published report paths and bytes are inputs to replay and integrity checks.

## Decision

Use [the layout policy](../governance/repository-layout.md), one machine-readable
roadmap and generated current status, study plans and stage/report catalogs. Assign
stable study IDs to existing and upcoming activities. New data uses stage/study/role/run
paths. Preserve all existing report, scientific source, configuration, test and lockfile
bytes and paths. Map legacy locations rather than renaming or copying evidence.

Keep exactly one current priority. Archive exact earlier navigation documents with
path/hash metadata and keep former heading anchors on live pages. Add a cheap
standard-library validator to documentation CI. Scientific workflows and gates stay intact.

## Alternatives and consequences

An in-place mass rename or history rewrite risks old URLs, hardcoded paths and hashes.
Local symlinks do not guarantee GitHub URL compatibility. Duplicating evidence creates
competing copies. Leaving all navigation unchanged perpetuates drift. The selected
additive approach retains irregular legacy roots visibly, but makes canonical browsing
and every new record consistent without threatening existing consumers.

The local handoff uses a separate clone, pinned baseline, complete-history bundle,
repeat-install validation and independent byte checks. Publication uses an ordinary PR;
rollback uses a revert, not deletion or reset of scientific working folders.

## Scope

GOV-001/002 and REP-001/002. No physical equations, thresholds, results or acceptance
decisions are changed. Q18/additional-Q and conditional spin/probe work stay in the
roadmap. AI-assisted administrative audit; no scientific peer review is implied.
