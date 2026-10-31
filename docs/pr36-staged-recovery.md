# PR 36 staged recovery

Source: `979a0996299a00d13523ef5277c9b02ef4ad747b`; original base: `5d95ca3f5b39539a55b2286c8623df320c83240c`.

The maintainer authorised public disclosure and ten staged PR merges on 1 November 2026. PR 36 is repurposed for stage 1; stages 2–9 each have a separate PR; stage 10 is split between the archive PR 45 and the final assessment PR. The original numerical and negative findings remain unchanged. Neither reproduction is certified complete by these merges.

The [machine ledger](pr36-staged-recovery.json) assigns all 191 original changed paths exactly once and records their original Git blob hashes. Percentages use changed text lines, so the indivisible original 2,714,167-byte evidence ZIP is counted separately and published through PR 45 as part of the final stage. Later records may be incomplete until their declared stage merges.

Run `python3 scripts/check_pr36_staged_recovery.py` to verify every file declared transferred against its immutable original blob. The final stage must verify all 191 paths. Administrative transfer records are additional and excluded from the source percentages. Scientific gates and the deferred level-4 review remain unchanged. AI assisted the recovery and verification.

Direct git push has no authenticated credential in this environment. The connected GitHub API publishes the staged file contents under new commit IDs; the recovered source commit is retained locally, and its self-contained Git bundle is published in stage 10 so its exact original history is recoverable.

## Complete transfer verification

Stages 1–9 merged through PRs 36–44. PR 45 published the unchanged original evidence archive; this final stage-10 tranche publishes the remaining assessment, records, milestone decision and complete-history source bundle. All 191 original changed files match their recovered Git blob hashes, with no scientific-text or scalar-result amendments. The evidence archive verifier confirms 163 hashed members and eleven internally consistent case results. The exact recovered commit is retained in the [complete-history Git bundle](../reports/s5-a/workstation-2026-11-01/source-979a099.bundle); its length and SHA-256 are recorded in the machine ledger and checked alongside `git bundle verify`.

To inspect the original recovered history from a local clone:

```bash
git bundle verify reports/s5-a/workstation-2026-11-01/source-979a099.bundle
git fetch ./reports/s5-a/workstation-2026-11-01/source-979a099.bundle HEAD:refs/remotes/recovered/pr36
git show 979a0996299a00d13523ef5277c9b02ef4ad747b
```

The API-created staged commits have different IDs from the preserved source commit. This environment did not publish the original commit as a GitHub branch ref, because direct authenticated Git push was unavailable. Its full Git object history remains recoverable from the verified bundle.

The [workstation assessment](../reports/s5-a/workstation-2026-11-01/README.md) and [ADR-0007](decisions/ADR-0007-tightened-milestones.md) retain the final scientific scope. Q18 is a stationary linked alternative, with the requested hyperbolic reproduction unresolved. Q22 has cable-compatible finite-diagram evidence, while finer-grid stationarity, larger-domain and stationary-comparator gates remain incomplete. No electron-model or reproduction-completion claim follows from publication. The historical reports keep their original contemporaneous draft/unmerged statements; this transfer record records their later publication.
