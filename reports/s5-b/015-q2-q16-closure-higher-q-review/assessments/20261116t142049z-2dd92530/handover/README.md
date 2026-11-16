# Q2–Q16 closure and higher-Q feasibility — local handover

Revision2 repairs the original handover's CRLF CSV endings. It recognizes the exact uncommitted `phase: applied` installation that failed `CSV must use LF`, backs up both new assessment folders, the publication marker and staged patch, and updates the existing checkout before retrying the repository checks. CSV cell values, six source archives and scientific assessments remain unchanged. See [REPAIR.md](REPAIR.md).

Open [ASSESSMENT.html](ASSESSMENT.html) in a browser for the full closure and feasibility assessment. [ASSESSMENT.md](ASSESSMENT.md), [Q2-Q16-CLOSURE.csv](Q2-Q16-CLOSURE.csv), [SCREEN-LEDGER.csv](SCREEN-LEDGER.csv) and [BIBLIOGRAPHY.md](BIBLIOGRAPHY.md) provide readable and machine-accessible records. Timestamps are included in UTC and Australia/Melbourne.

The completed numerical allocations are assessed and the unchanged route is parked. Q2 and Q3 controls are retained; no Q sector is physically rejected. Q17–Q32 have published structural interest, but a full long campaign is deferred pending a benchmark-first pilot and model-purpose decision. This package starts no CPU/GPU solver work.

## Workstation commands

Requires Python3 with zoneinfo, Git and an authenticated gh. No numerical dependencies or uv environment are needed for this administrative handover. The existing campaign2 preparation must already be merged into origin/main.

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-Q2-Q16-closure-20261117-r2.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-Q2-Q16-closure-20261117-r2"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

Install clones your local administrative checkout to `~/ElectronFieldTopology-q-range-closure-20261117`, fetches main from that workstation, and appends the records on a new branch. It preserves original run trees and existing reports. It renders navigation and runs actual repository record/link/whitespace validation before publication. Publish commits, pushes and creates the PR. Merge waits for checks and pins the exact head. A network or check failure stops the sequence; preserve the output and rerun the same command after resolving it. No forced reset or branch deletion occurs. No GitHub operation was executed while creating this pack.

The optional `--repo /path/to/local/repo` and `--publication /path/to/new/checkout` apply to install/publish/merge/status. Use the same overrides throughout. If main advances after installation, the handover stops before push so its prepared record can be reconciled. It never silently rewrites existing published assessments.

## Preservation and verification limits

Six original compact evidence archives and full-field manifests are included. The correct rapid-screen parent is `20261114t094318z-7800d5c4`. Full float64 fields remain in their original run trees; compact evidence is not a full-field backup. [RETENTION.json](RETENTION.json) records the campaign2/final-audit inventories and source anchors. Keep the original run directories and an independently verified full-field copy. The handover does not upload or delete those fields.

The extracted historical Q17/Q19 assessment is a text archival copy; its image/replay references belong to its original repository folder, identified in the accompanying provenance file. Scientific source reports retain their original timestamps, outcomes and limits. [VALIDATION.json](VALIDATION.json) distinguishes checks actually run while building this package from the repository checks that run on the workstation. All analysis and handover code are AI assisted; this is not independent scientific peer review.
