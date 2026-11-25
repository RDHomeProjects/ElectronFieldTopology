# Final Matter Waves folder cleanup — 26 November 2026

This is the folder-level pass after the successful 69-part pause archive and
PR #101. It checks remaining project files, preserves additional records and Git
metadata, removes redundant whole folders, and publishes the outcome. It runs
entirely on the zbook. No new optimizer or physical-time work is performed.

## What it covers

Immediate children of your home directory and Downloads whose names start with
`ElectronFieldTopology`, `Matter-Waves`, `MatterWaves` or `EFT-` are examined.
Matching children inside `~/git-recovery` are also examined. This includes the
previously omitted `EFT-admin-backups`, `EFT-admin-logs` and `EFT-archive-work`.
Unrelated items such as Library, JoplinBackup, Clearable and esp are untouched.
Ambiguous generic filenames are retained; the plan reports the out-of-scope list.

Three home-directory locations remain:

- `~/MatterWaves-Workspace`: one working Git checkout, seeded locally and fetched
  to include the merged pause record. An existing checkout here is preserved;
  local working files are never reset.
- `~/MatterWaves-PauseArchive`: the original archive receipts and restart controls.
- `~/MatterWaves-FinalCleanup`: this toolset, supplemental archive receipts,
  folder report, restore checks and final publication controls.

The scan hashes all eligible remaining regular files. Content already in the
verified base archive is referenced by hash. New regular records, including raw
Git metadata, are added to a separate supplemental release. Each discovered Git
repository also receives an independent all-refs/HEAD bundle with a fresh-clone
restore check. This preserves local histories, working files and index metadata
before a redundant checkout is removed.

Recognised virtual environments with `pyvenv.cfg`, node_modules with a parent
package lock, and `__pycache__` contents are recorded as rebuildable and omitted
from upload. Their files are still hashed before removal. Other cache-named
folders are preserved as ordinary data unless their contents already match the
archive. System Python, global packages, Docker and unrelated applications are
not removed.

## Run from the home directory, without sudo

Have Git, authenticated GitHub CLI, Python 3 and at least 20 GiB free. Stop project
analysis/rendering jobs first and keep mains power and suspend disabled during
any transfer. There is no arbitrary wall-time limit.

```bash
cd "$HOME"

unzip -n \
  "$HOME/Downloads/ElectronFieldTopology-final-folder-cleanup-20261126.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-final-folder-cleanup-20261126"
bash "$package/RUN.sh" verify
bash "$package/RUN.sh" setup

handover="$HOME/MatterWaves-FinalCleanup/RUN.sh"
(
  set -euo pipefail
  bash "$handover" scan
  bash "$handover" archive
  bash "$handover" verify-remote
  bash "$handover" cleanup
  bash "$handover" install
  bash "$handover" publish
  bash "$handover" merge
  bash "$handover" collect
  bash "$handover" status
)
```

**Use the retained `handover` launcher after setup.** The Downloads copy and its ZIP
are eligible for verified removal along with older handovers. The retained toolset
is sealed and remains available after that removal. Setup does not contact GitHub
or delete research data.

`scan` writes a frozen `PLAN.json.gz`, `STATUS.json` and human-readable `REPORT.md`
under `~/MatterWaves-FinalCleanup`. The report lists candidate folders, retained
items, new data volume, recognised rebuildable files and supplemental part count.
If no unexpected condition is found, the authorised sequence continues through
archive verification and removal without another confirmation prompt.

## Verification and deletion rules

The base release is checked against the exact merged completion record at commit
`2eda3eb022e66fad56ca03d562edca092164e957`. Its proof and manifest are freshly
downloaded and matched to that Git record; all 69 base asset IDs/sizes/digests
are checked. The base 103 GiB of data are not uploaded again.

Additional content is chunked, deduplicated and packed into bounded parts. Large
previously unlisted backup files are supported through 256 MiB chunks. Every new
part is freshly downloaded and every member SHA256 checked. Git bundles are
reconstructed from those downloaded chunks and cloned at their exact HEADs.
Supplemental metadata, standalone restore tools and the verification proof are
also uploaded/downloaded and matched before the new release is published.

Only then may removal run. Each whole candidate folder is rechecked for the same
files, directories, link targets and hashes. Active project processes, changed or
new files, special files, external links/worktree pointers, unreadable/incomplete
Git histories, and credential-bearing local configuration cause that root to be
retained with an explicit reason. Such local credentials are not uploaded.

An unchanged eligible root is renamed into this job's quarantine on the same
filesystem. Its regular files are rehashed and individually unlinked, links are
unlinked without following their targets, and empty directories are removed from
the bottom up, including the original root. There is no wildcard recursive purge
and no `rm -rf`. A different filesystem is retained rather than force-copied or
recursively removed. The original archive is never deleted or overwritten.

The final cleanup receipt records which roots actually disappeared, bytes removed,
what remains and why. It is published through a separate clone under the control
directory, with essential project/documentation checks and merged-payload hash
verification. The working checkout and unrelated Downloads remain available.

## Interrupted work and retained items

Use `bash "$handover" status` to inspect local state. A failed transfer resumes by
repeating `archive`, `verify-remote` and the remaining sequence. Already verified
parts are reused. The draft-aware API uses release IDs and reconciles duplicate
asset names only when their content matches; it never uses `--clobber`.

If authentication expires, restore `gh` authentication locally and repeat the
failed mode. Never delete the control directory or regenerate the frozen plan.

A failed cleanup can resume with `cleanup`: renamed roots remain under
`~/MatterWaves-FinalCleanup/quarantine/root-ID`, and per-file deletion receipts
allow the partial prune to continue. Do not move quarantined roots yourself while
the job is running. Unknown or changed content is retained and reported.

A status ending in `with_retained_items` is a partial cleanup, not permission to
force-delete what remains. Read `REPORT.md` and `CLEANUP-RECEIPT.json`. A subsequent
scan for changed/new material should use a fresh sub-job directory under the same
protected final-cleanup area; do not rewrite this job's identity or receipts.

`completion-evidence.zip` is created in the control directory for assessment. The
publication record contains the supplemental release URL, restoration information
and deletion outcome. GitHub itself remains writable.

## Validation limits

Host tests use small synthetic home/Downloads trees, real temporary Git histories
and a local fake release store. They cover additional data, base-archive reuse,
chunk reconstruction, complete-root removal, omitted EFT folders, environment
rebuilding, internal links, external-link/credential retention, changed/new data,
interrupted rename and partial deletion, remote-asset replacement, restoration
and repeat cleanup. No zbook file or GitHub repository is accessed by those tests.
