# Archive metadata asset recovery — 26 November 2026

The supplied log shows all 69 archive parts uploaded, freshly downloaded and
verified. A fresh numerical source clone reached its pinned HEAD. The stop at
03:18 Melbourne on 26 November (16:18 UTC on 25 November) occurred when uploading
`MATTER-WAVES-ARCHIVE.json.gz`: GitHub returned HTTP 422, asset name already exists.
No cleanup had started. Authentication was working at that point.

The log does not establish whether the collision was caused by an interrupted
previous upload, a stale listing or another concurrent operation. This repair
checks the actual asset rather than assuming any of those explanations.

## Recovery behavior

- Keep the existing release ID `456791881`, archive tag, frozen plan and all 69
  verified-part receipts. Keep the original package byte-for-byte unchanged.
- Retain the previous draft-aware release lookup and request fresh API responses.
- Find the existing manifest and download it by its numeric asset ID. Compare its
  size, SHA256 and actual downloaded bytes with the local manifest, then recheck
  the remote asset identity. Reuse only an exact match.
- If an upload reports a duplicate name after an initially absent listing, retry
  fresh reads briefly and apply the same full comparison. Do not retry credential
  failures as duplicate names.
- Stop if existing content differs, is incomplete, or changes during comparison.
  Do not overwrite, delete, rename or use `--clobber` on remote assets.
- Complete the original metadata/proof upload, publication, cleanup and final PR
  only after every original verification gate passes. Record the repair and
  asset-comparison evidence in the workstation PR and completion ZIP.

The completed data parts are reused using their existing verified receipts; the
roughly 103 GiB dataset does not need uploading again. Local restore-check copies
must remain available. If a retained verification copy has disappeared, the
original engine downloads only the relevant verified part again.

Official release-asset documentation:
https://docs.github.com/en/rest/releases/assets

## Run on the zbook

Keep the original package and the current archive work directory. Run as `rd`,
without sudo. Use this new launcher for all remaining operations. Do not rerun
preparation, remove an existing release asset, regenerate original checksums or
start another archive job.

```bash
unzip -n \
  "$HOME/Downloads/ElectronFieldTopology-pause-archive-asset-fix-20261126.zip" \
  -d "$HOME/Downloads"
repair="$HOME/Downloads/ElectronFieldTopology-pause-archive-asset-fix-20261126"
(
  set -euo pipefail
  bash "$repair/RUN.sh" verify
  bash "$repair/RUN.sh" preflight
  bash "$repair/RUN.sh" upload
  bash "$repair/RUN.sh" verify-remote
  bash "$repair/RUN.sh" cleanup
  bash "$repair/RUN.sh" install
  bash "$repair/RUN.sh" publish
  bash "$repair/RUN.sh" merge
  bash "$repair/RUN.sh" collect
  bash "$repair/RUN.sh" status
)
```

Preflight is read-only on GitHub. It compares the existing manifest when visible
and writes `ASSET-COLLISION-DIAGNOSTIC.json` into the archive control directory.
If it reports different content or an incomplete asset, stop and provide that
small JSON plus the terminal error for review. The repair preserves both versions
and does not bypass the deletion gates. If the manifest is not listed, upload mode
will attempt the normal upload and safely reconcile any duplicate response.

The default control directory remains:
`$HOME/MatterWaves-PauseArchive/20261124t103512z-15f7851c`.
`status` now also reports the number of verified parts. The small repair record
is kept under `asset-collision-repair-20261126`; it does not replace the earlier
draft repair record. No new scientific computation is performed.

## Validation

Offline tests cover exact existing asset reuse, duplicate-name recovery, fresh
upload confirmation, same-size/different-content rejection, digest mismatch,
incomplete assets, authentication errors, asset replacement during comparison,
read-only preflight, cache headers and the prior draft-release lookup safeguards.
The original integrity/restore/deletion tests also pass. The CLI rehearsal uses
local fake commands and never contacts GitHub. Actual asset comparison and final
restoration checks execute only on the workstation.
