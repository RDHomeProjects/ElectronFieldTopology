# Matter Waves verified full-data archive and cleanup

## Scope and evidence

This handover uses the completed pause inventory `20261124t103512z-15f7851c`,
whose evidence ZIP SHA256 is
`d9e4328f19b913ef23f3648c7315b5702246cd2df0618c6cf3dc4441beaf9615`.
The inventory contains 85,573 regular files across 203 roots and 24 repositories,
139,111,438,759 logical bytes (129.56 GiB), with 107,955,078,539 unique file bytes
(100.54 GiB). It reports no missing required checkpoint, unresolved field reference
or inventory read error. All 17 recent checkpoint roles are present. These facts
are inventory findings; **full data upload was not yet confirmed**.

This handover runs entirely on the zbook. No GitHub operation is performed from
the chat environment. It performs no new scientific analysis, relaxation or motion.
The current publication branch is fetched in a separate archive-owned clone; the
scientific checkout is never reset, switched or pulled.

## Run

Use the inventoried `rd` account, without sudo. Keep the zbook on mains power and
disable automatic suspend during the transfer. Require Git, authenticated `gh`,
Python 3 and at least 20 GiB free for bounded staging. No GPU is needed.

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-pause-archive-20261124.zip" \
  -d "$HOME/Downloads"
package="$HOME/Downloads/ElectronFieldTopology-pause-archive-20261124"
(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" prepare
  bash "$package/RUN.sh" upload
  bash "$package/RUN.sh" verify-remote
  bash "$package/RUN.sh" cleanup
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" collect
  bash "$package/RUN.sh" status
)
```

The upload transfers roughly 100.5 GiB of unique file data before compression,
plus Git bundles, and downloads the complete compressed archive for verification.
It can take many hours. It uses separate content-addressed tar.gz parts capped at
1.5 GiB uncompressed each. GitHub Releases supports assets below 2 GiB and up to
1,000 assets per release, with no total release-size limit:
https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases

An existing exact asset is checked and reused. A conflicting asset stops the job;
no asset is overwritten. The release stays a draft until every part and metadata
file has passed download verification. The archive is public in the existing
public project repository. The final completion documentation uses a separate
checkout and a PR; checks and merged payload hashes are verified locally.

Default job directory:
`$HOME/MatterWaves-PauseArchive/20261124t103512z-15f7851c`.
It contains the frozen plan, transfer receipts, deletion journal, restore manifest
and completion evidence. Keep this small control directory and this new handover.
The prepared cleanup file list is `CLEANUP-PLAN.csv.gz`. Commands accept `--work`,
`--repo` and `--publication` overrides; use the same arguments throughout.

## Verification before deletion

1. Rehash one unchanged source for every unique inventoried content hash. Preserve
   all local Git refs and HEAD in verified bundles, plus a pinned main bundle.
2. Build bounded parts. Upload each missing part, freshly download it, verify its
   compressed SHA256, then rehash every individual member against the inventory.
3. From downloaded bytes, validate recent checkpoint CRCs and float64 field shape,
   the primary CG iteration 665, best iteration 663 and their continuation arrays.
   Clone the numerical code from a downloaded bundle and check its exact HEAD.
4. Upload and freshly download the restore manifest, original inventory, restore
   tools and verification receipt. Publish the completed release.
5. Before and during cleanup, confirm the same published asset IDs, sizes and
   available server digests. Require the original plan and transfer proof hashes.
6. Immediately rehash each deletion candidate and check its regular-file identity
   through non-symlink parent directories. Delete only an unchanged allowlisted
   file. Record every outcome in a flushed, resumable deletion journal.

This is a restoration integrity test, not a numerical metric replay. It does not
certify stability, admission or agreement with literature. Read [restart state](KNOWN-STATE.json)
and [restore instructions](RESTORE.md) before resuming science.

## Exact cleanup policy

Eligible files are **inventoried untracked project records** and **inventoried
project Downloads** whose archived bytes and current local hashes match. There
are 1,779 inventoried project Downloads files, about 0.66 GiB; eligibility and
actual deletion counts are reported by the generated plan and receipt.

Git-tracked files, `.git`, installed runtime/virtual environments and the three
browser environments are retained. Unrelated Downloads, new files, changed files,
unlisted files and the current archive handover remain. The script never follows
symlinks and never performs forced recursive directory deletion. It removes empty
subdirectories only. Git checkouts are retained even after their untracked result
files have been archived. Thus it may not reclaim all 129.56 GiB.

The transfer's generated verification checkpoint copies and bundle copies are
also pruned by exact hash after verified cleanup. Small receipts, source-code
restore checks and publication checkouts remain for restart and audit.

## Interrupted transfers and errors

Use `status` to inspect progress. If a transfer is interrupted, rerun `upload`,
then continue with `verify-remote`, `cleanup` and publication. Verified completed
parts are reused. Do not rerun the old scientific campaign and do not create a new
archive job unless the handover reports an identity conflict. A session lock
prevents concurrent archive/cleanup commands. Stop a foreground transfer with
Ctrl-C if needed; data cleanup has not begun until the explicit cleanup mode.

Cleanup is resumable. Changed or unsafe files are retained and listed; no broad
fallback deletion is attempted. If a network operation fails after some verified
files were deleted, the release and local journal remain; rerun the same cleanup
command to finish. Do not delete the job directory or handover while resolving an
error. The completion ZIP is `completion-evidence.zip` in the job directory.

The repository remains writable. Only after completion documentation is merged
and restoration records are available should the maintainer optionally mark the
GitHub repository archived; that repository setting is not changed by this pack.
