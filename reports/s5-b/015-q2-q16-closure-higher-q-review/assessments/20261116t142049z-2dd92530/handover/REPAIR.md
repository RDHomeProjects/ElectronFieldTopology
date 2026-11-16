# CSV line-ending correction

The original package passed archive verification but its CSV writer used Python's default CRLF row terminator. Repository validation requires LF, so installation stopped before commit, push or PR creation. Three presentation tables were affected: SCREEN-LEDGER.csv, Q2-Q16-CLOSURE.csv and ENDPOINTS.csv.

Revision2 supplies LF copies, verifies byte-level LF endings before installation, and preserves every cell. All six original evidence archives, reports, scientific JSON, gates and source identities are byte-exact. The generator now declares `lineterminator='\n'` explicitly; checks cover the resulting tables.

For the observed failed installation, RUN.sh install verifies the exact original package identity, original report manifests, branch and HEAD; requires uncommitted phase applied, no PR, no unstaged or untracked work; and backs up both newly staged assessment folders, marker and staged patch under `.git/q-range-before-lf-repair-…`. It replaces the embedded handover, updates package provenance and regenerates enclosing manifests. It then reruns the actual repository record, documentation and whitespace checks before any publication.

An already repaired installation resumes normally. A committed, published, changed or differently identified installation stops with a diagnostic. No scientific run, Git reset, original run-tree cleanup or source-evidence rewrite is performed. The old Downloads package can remain untouched; run the commands using the new revision2 package path.

VALIDATION.json distinguishes the offline recovery tests from the actual repository validators, which run on the zbook. These tests are not a new scientific replay.
