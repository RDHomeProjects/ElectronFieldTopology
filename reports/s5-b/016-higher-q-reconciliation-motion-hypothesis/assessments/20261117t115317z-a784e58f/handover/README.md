# Record the completed higher-Q reconciliation

This publication-only pack records the completed source reconciliation, Q2/Q8 frozen-field motion probes, linked-document completion and consolidated Q22/Q17/Q18/Q19 assessment. It includes the unchanged final evidence ZIP, which contains the unchanged original diagnostic evidence and all recovered records. Full 3D fields remain in their original workstation locations or verified archives.

All GitHub operations run from the zbook. A separate publication checkout is created at `$HOME/ElectronFieldTopology-reconciliation-results-20261117`; the existing research checkouts and numerical fields are preserved. No CPU/GPU analysis or new numerical campaign runs.

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-reconciliation-results-record-20261117-r2.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-reconciliation-results-record-20261117-r2"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

`install` fetches main, appends a canonical measurement and assessment to existing study S5-B-016, updates its assessed finding while keeping the scientific gate open, appends the outcome to its model-scope document and regenerates navigation. Existing result files, study findings and the Q2–Q16 closure are preserved. The current-summary pointer advances only if it still refers to this study or its direct predecessor; an unrelated newer pointer is preserved.

Before committing, the script runs the actual repository `project_records.py render`, `project_records.py check --compare-ref`, `check_docs.py`, and staged whitespace checks. Checksums include every nested checksum file; the new CSV uses LF. Original archive bytes are never rewritten to normalize historical CSVs.

`publish` commits, pushes one branch and creates or reuses its exact matching PR. `merge` waits for hosted checks and uses a head-commit guard before squash-merging. It confirms the merged state and records the merge commit. It does not bypass checks or force-push. Default branch: `analysis/reconciliation-results-20261117`.

If network resolution or a check fails, the command stops with the checkout and evidence retained. After the cause is resolved, rerun the same sequence. No diagnostic or solver is repeated. If upstream main changes before publication, the script stops to preserve the prepared branch; `--publication` can select a new directory for a fresh install against current main.

Optional paths follow the mode:

```bash
bash "$package/RUN.sh" install \
  --repo "$HOME/ElectronFieldTopology-higher-q-reconciliation-20261117" \
  --publication "$HOME/ElectronFieldTopology-reconciliation-results-20261117"
```

Use the same overrides for publish, merge and status. Defaults use the existing reconciliation checkout as the local clone source, which must have the expected GitHub origin. Only Python 3 standard-library modules, Git and the workstation's authenticated `gh` are needed by the handover. Repository validators may enforce their normal local requirements.

## Repair of the original ancestry stop

The original pack required scientific source commit `dfcdd9ef3509cf0b3e6970986c8458d69f084b27` to be an ancestor of main. A squash merge can publish its exact content under a different commit ID, so that requirement incorrectly blocked publication. R2 keeps the scientific source identity and verifies the registered S5-B-016 preparation by exact Git tree equality and the pinned handover-manifest hash. A changed preparation is rejected; matching content needs no ancestry substitution.

The existing stopped publication directory is reused. Only the recognized original package stopped before results were applied can be adopted. Its marker is backed up inside `.git`, the checkout must be clean, and its branch/HEAD must match the stopped baseline. No reset, field change, new analysis or evidence rewrite occurs. The same commands above resume install and then publish/merge the completed results. Original assessment IDs, numerical findings and evidence hashes are unchanged.

Open [ASSESSMENT.html](ASSESSMENT.html) in a browser. [RESULTS.json](RESULTS.json) freezes the two source-run identities; [REVIEW-VALIDATION.json](REVIEW-VALIDATION.json) records the completed evidence/scalar review; [HOST-VALIDATION.json](HOST-VALIDATION.json) records offline handover tests. Actual repository validators and hosted checks run on the workstation, not in the report-building environment.
