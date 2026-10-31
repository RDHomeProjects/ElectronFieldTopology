# PR 36 staged recovery

Source: `979a0996299a00d13523ef5277c9b02ef4ad747b`; original base: `5d95ca3f5b39539a55b2286c8623df320c83240c`.

The maintainer authorised public disclosure and ten staged PR merges on 1 November 2026. PR 36 is repurposed for stage 1; stages 2–10 each have a separate PR. The original numerical and negative findings remain unchanged. Neither reproduction is certified complete by these merges.

The [machine ledger](pr36-staged-recovery.json) assigns all 191 original changed paths exactly once and records their original Git blob hashes. Percentages use changed text lines, so the indivisible original 2,714,167-byte evidence ZIP is counted separately and published in the final stage. Later records may be incomplete until their declared stage merges.

Run `python3 scripts/check_pr36_staged_recovery.py` to verify every file declared transferred against its immutable original blob. The final stage must verify all 191 paths. Administrative transfer records are additional and excluded from the source percentages. Scientific gates and the deferred level-4 review remain unchanged. AI assisted the recovery and verification.

Direct git push has no authenticated credential in this environment. The connected GitHub API publishes the staged file contents under new commit IDs; the recovered source commit is retained locally, and its self-contained Git bundle is published in stage 10 so its exact original history is recoverable.
