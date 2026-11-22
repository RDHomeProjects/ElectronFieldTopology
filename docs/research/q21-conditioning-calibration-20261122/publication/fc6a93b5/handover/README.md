# Record Q21 conditioning results and the detailed scientific review

This handover records the complete compact output of run `20261122t102101z-2a8e50ec` and the subsequent scientific review dated 23 November 2026. It creates, checks, publishes and merges one documentation/results PR through Git and gh on the zbook. No new optimizer updates, physical-time integration, field transformation or gate changes are performed. Python's standard library is sufficient; neither uv, NumPy, CUDA nor sudo is required for this recording activity.

The recorded outcome remains a completed unresolved Q21 preparation: 580 accepted updates across 13 cases, no stationarity pass, passing Q2 and backend controls, no validated fitted optimum, and an early conditioning benefit that did not persist. The review's Q2–Q32 recommendation is a staged diagnostic audit and pilot, not an automatic new bulk campaign.

## Contents recorded

The PR adds the original evidence ZIP byte-for-byte, every compact member in readable form, every measured update and response/fit/selection record, exact and restarted controls, source/derivative/Q2/backend checks, residual/spectral/curvature diagnostics, timing/telemetry snapshot, and all field seals and inventories. It also adds the complete scientific assessment in HTML/Markdown/JSON, literature alignment and source notes, high-resolution PNG and SVG charts, independent verification, endpoint and matched-horizon tables, and the portable compact-review program.

All 52 retained NPZ files, approximately 9.98 GiB, are verified locally against their declared SHA256 hashes, sizes and ZIP CRCs. Their verification receipt and inventory are published. These full arrays remain on the zbook under the established retention arrangement; they are not inserted into Git. Their scientific metrics are not recomputed by this publication-only tool. Existing results, charts, images and navigation text are preserved.

## Commands

```bash
unzip -n \
  "$HOME/Downloads/ElectronFieldTopology-Q21-conditioning-results-record-20261123.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-Q21-conditioning-results-record-20261123"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

`verify` reads and checks all 52 retained files. It can take several minutes while reading about 10 GiB for hashing and again for CRC verification. Later commands reuse that complete verification only after rechecking the scientific metadata and every file's size, timestamps, inode and device identity; any change triggers a fresh verification. All outputs include UTC and Australia/Melbourne timestamps.

The numerical checkout defaults to `$HOME/ElectronFieldTopology-adaptive-q-screen-20261117`. The exact run is selected by its pinned ID and archive hash, never by a generic latest pointer. If the verified run was moved, add `--run /exact/path/to/20261122t102101z-2a8e50ec` to verify/install; its identity must still match. For another numerical checkout, add `--repo PATH` consistently.

A new separate publication clone is created at `$HOME/ElectronFieldTopology-Q21-conditioning-results-record-20261123`. Override it consistently with `--publication PATH` if needed. The prior publication clone and numerical branch are not switched or reset. Preparation PR93 is checked live on the zbook for exact head, merge commit, main ancestry and published preparation bytes before staging the completed record.

The fixed completed result may already have been recorded through the previous package. Identical existing result bytes are accepted and retained. A differing immutable payload stops the handover for review; it is not overwritten. The new detailed assessment is recorded in its own versioned snapshot either way.

## Publication and recovery

The package uses a separate Git marker from the earlier campaign, so the old preparation marker cannot be mistaken for this completed-results publication. Repeating verify/install/publish/merge resumes or checks the same publication; it does not create another scientific run. No force push, reset, deletion of existing scientific files, or administrator bypass is used.

If a command fails, retain its log, correct the stated condition, then repeat that command and the remaining commands. Examples:

```bash
# Publication/network retry after a successful install:
bash "$package/RUN.sh" publish
bash "$package/RUN.sh" merge
bash "$package/RUN.sh" status

# A manual GitHub merge is recognised and verified by either command:
bash "$package/RUN.sh" merge
bash "$package/RUN.sh" status
```

Local checks include staged whitespace, the repository's project-record validation and documentation checks when present. The merge waits for registered remote checks and retains repository protections. After merge, the tool fetches main and verifies every newly published immutable payload byte, including the original evidence and all review charts. A MERGED label alone is insufficient for the final success receipt.

`status` reports the PR URL, merged byte-verification outcome and local browser paths for the original report and detailed assessment. Open the reported `ASSESSMENT.html` in a browser to read the full review. Existing GitHub HTML file links may display source; the same reports open normally from the cloned local directory with their adjacent charts.

## Repository destinations

Everything is added beneath the existing `docs/research/q21-conditioning-calibration-20261122` study:

- `results/20261122t102101z-2a8e50ec/c0fd3269/`: complete original compact evidence and readable members.
- `assessments/<pinned-review-id>/`: the unchanged detailed assessment bundle and charts.
- `publication/<package-hash>/`: local field verification, source-plan merge verification and this recording handover.

The study README and repository README receive additive links. Existing files in immutable snapshots must match byte-for-byte. The review's limitations and unsuccessful scientific findings remain explicit.

For download-only verification on a computer without retained fields:

```bash
bash "$package/RUN.sh" verify --package-only
```

That mode does not certify local field availability and cannot replace the full verify/install requirements for publication. See [HOST-VALIDATION.json](HOST-VALIDATION.json) for host tests and their limits. The actual zbook field checks, source PR verification and final GitHub publication checks occur when the commands above run.
