# Q21 criteria assessment and explicit CPU resolution handover

This package records the completed run and detailed review, applies the measurement criteria actually reported by the primary authors where the data permit, and adds supplementary native-field diagnostics plus **177³ and 193³ CPU runs**. The current admission limits remain unchanged. See [the protocol](PROTOCOL.md) and [author-specific assessment](documentation/author-comparison/ASSESSMENT.md).

The raw completed evidence is included and already available for assessment; it does not need to be merged into GitHub for the assistant to read it. The zbook is required for full-field measurements and the two new CPU branches. No field arrays need to be uploaded here.

## 1. Record original results, assessment and supplementary plan

```bash
package="$HOME/Downloads/ElectronFieldTopology-Q21-criteria-and-CPU-resolution-20261123"
(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
)
```

Publication uses a new separate checkout at `~/ElectronFieldTopology-Q21-criteria-publication-20261123`, based on current origin/main. Existing results, images and analysis remain unchanged. All GitHub commands execute only on the zbook. Failure at any step stops the command block; rerun the failed mode after correcting its reported cause, without resetting the checkouts.

## 2. Run supplementary analysis and both CPU grids

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" preflight
  bash "$package/RUN.sh" run
  bash "$package/RUN.sh" status
)
```

The service runs in the background. Status prints the exact output, browser report, current operation, resource telemetry and charged attempts. The original numerical checkout defaults to `~/ElectronFieldTopology-adaptive-q-screen-20261117`. Source run defaults to `artifacts/q21-fixedbox-resolution-retained-audit/20261123t032942z-26dd4a7c`. Use `--repo`, `--source-run` and `--parent` only if their authenticated files were deliberately relocated. Changed scientific bytes are not accepted.

This is explicitly a CPU campaign: there is no `--backend auto` flag and no GPU-memory admission requirement. Each grid receives up to 80 attempts, 160 total. Read-only audits run first; the status distinguishes this from optimizer progress. No overall wall-time cutoff is imposed. The 193³ CPU diagnostics may dominate runtime; this host package does not claim a validated zbook runtime forecast.

To pause safely and later resume:

```bash
bash "$package/RUN.sh" stop
bash "$package/RUN.sh" status
# Wait until service_active and runner_alive are both false.
bash "$package/RUN.sh" resume
bash "$package/RUN.sh" status
```

If the workstation shuts down, check status and use resume rather than run. If a CPU geometry cannot meet the host reserve, free memory and resume; do not reduce the numerical gates or change the package. A resource interruption is not a rejected Q value.

## 3. Collect and publish completed supplementary results

Wait for `status=complete_pending_review`, `runner_alive=false` and `service_active=false` before this block:

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" collect
  bash "$package/RUN.sh" record-results
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

Attach the uniquely named evidence ZIP printed by collect for scientific review. An interrupted evidence ZIP can also be collected once the service stops, but record-results deliberately does not automatically publish an interrupted run as completed.

The completed supplement includes AUTHOR-METRICS.json/CSV, per-update energy changes, native field distributions, images, original gate results, matched spatial comparisons, validated response fits, new CPU histories and full-field manifests. It explicitly distinguishes unavailable paper checks, approximate equilibria, admission and physical stability. Perturbation-and-return and duration-specific dynamical calibration remain unperformed; a flat optimization curve is not relabelled as stability.
