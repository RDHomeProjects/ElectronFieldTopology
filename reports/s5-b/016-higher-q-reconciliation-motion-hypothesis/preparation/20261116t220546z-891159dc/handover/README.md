# Q22/Q18 reconciliation and motion hypothesis — local handover

Open [ASSESSMENT.html](ASSESSMENT.html) in a browser for the motion/stability assessment. The [frozen scope](PLAN.json), [conditional pilot contract](PILOT.json), [legacy endpoint ledger](LEGACY-ENDPOINTS.json) and [primary bibliography](BIBLIOGRAPHY.md) retain the distinctions and provenance.

This tranche records the assessment, reconciles existing higher-Q records and optionally probes the instantaneous equations on retained Q2/Q8 fields. It performs zero relaxation and zero physical-time integration. Uniform translation, internal rotation and periodic states are treated separately. A favorable frozen-field fit is not a stability pass. The full Q17–Q32 campaign remains deferred; the proposed Q22 pilot is a conditional contract, not an executable relaxation campaign in this pack.

## Execute on the zbook

Requires Python3, Git and authenticated gh for publication; existing uv/Python3.12.14 and frozen numerical environment for the optional CPU probes. No GPU or new numerical dependency is required. Timestamps use UTC and Australia/Melbourne.

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-higher-q-reconciliation-20261117.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-higher-q-reconciliation-20261117"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" collect
  bash "$package/RUN.sh" diagnose
  bash "$package/RUN.sh" status
)
```

The preparation clones the local administrative checkout into `~/ElectronFieldTopology-higher-q-reconciliation-20261117`, fetches current main from that workstation, requires the merged Q2–Q16 closure and appends a prepared study. It runs the actual repository record, documentation and whitespace checks before publication. Existing reports, kernels, locks and full fields remain untouched. Publication and merge pin the prepared head; a changed main or failed check stops the process without a forced reset.

Collection reads pinned Git objects without network access and includes available historical numerical sources. It writes a report and evidence.zip under the new checkout's `artifacts/higher-q-reconciliation/` directory. Text/source snapshots are prioritized; any8MiB per-member or64MiB total limit, absent historical object or missing local field is reported explicitly. It does not automatically restore old Release assets. Existing restore references are collected for review.

The diagnostic runs five CPU acceleration evaluations per retained field plus one NumPy-array parity evaluation, with additional source/static replay checks. It reads exact Q2 and Q8-native750 fields only. Memory, hash, source or environment problems produce explicit blocked/deferred receipts; they do not become physical failures or replacement seeds. Probe output is resealed into the same evidence.zip.

At completion, upload the single evidence.zip printed in the terminal for review. This contains the newly collected reconciliation/probe results. The publication steps above record the assessment and preparation; they do not publish unreviewed local probe outcomes as scientific acceptance.

## Repeat or use alternate paths

Repeating collect retains the matching sealed output; repeating diagnose retains its prior receipt. To make another read-only collection after restoring missing fields, run `collect --new-collection`, then diagnose. Older outputs remain retained. `run` is shorthand for collect followed by diagnose; it is not a relaxation or motion simulation.

Optional `--repo` and `--publication` select local checkout paths. Optional `--q2-run` and `--q8-run` select the original retained run directories and must be supplied consistently to collect and diagnose; archive/field hashes remain fixed. Defaults match the previously completed audit. A different field is rejected rather than silently accepted.

All GitHub operations occur only when these commands run on the workstation. [VALIDATION.json](VALIDATION.json) distinguishes actual offline checks from the full repository validators and retained-field replay that run locally. Full-field backups are not created by this pack. AI assisted the analysis and scripts; physical stability and electron-model acceptance remain unestablished.
