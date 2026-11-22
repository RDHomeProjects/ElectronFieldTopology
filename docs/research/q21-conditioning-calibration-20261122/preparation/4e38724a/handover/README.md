# Q21 conditioning calibration — workstation handover

This adds the completed literature-campaign assessment and performs a read-only residual audit followed by a one-parameter conditioning study from the boundary-admitted larger-box endpoint. Existing graphics, measurements and reports remain in place. See [PROTOCOL.md](PROTOCOL.md) for frozen design, model-selection rules and interpretation.

Scientific starting point:Q21 domain-pad-16 iteration425;129³ grid,L30.72,h0.24. Boundary admission passes; stationarity does not. Vary only the numerical Sobolev shift, with the same initial field, alpha, restarted conjugacy convention, action and gates. A separate exact-memory reference is clearly labelled.

Seven initial values receive 30 attempts each; up to four adaptive measurements concentrate near response turns or an uncertain best region. Linear, quadratic and exponential fits must pass leave-one-out prediction checks against a constant model. The fitted or best measured value is rerun from the original field before a conditional120-attempt comparison against the baseline. Maximum 580 new optimizer attempts, zero physical-time steps. A failed fit does not force an optimum or consume the remaining budget.

All GitHub access is performed by Git/gh on the zbook. `check-merge` checks the actual previous PR, merged head, main ancestry and byte-identical published evidence and selected scientific records. No PR number or successful check is invented by the package. The numerical checkout remains pinned. Publication uses a separate clone and creates an additive documentation snapshot.

## Start

Run as rd in a normal terminal. `auto` qualifies one backend for the campaign; `cpu` or `cuda` may be chosen before launch. CUDA optimization includes independent CPU diagnostics. Preserve the same backend argument for resume. GPU arithmetic and the full129³ production field are qualified on the zbook; host controls in [HOST-VALIDATION.json](HOST-VALIDATION.json) are not production results.

```bash
unzip -n \
  "$HOME/Downloads/ElectronFieldTopology-Q21-conditioning-calibration-20261122.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-Q21-conditioning-calibration-20261122"
backend="auto"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" check-merge
  bash "$package/RUN.sh" preflight --backend "$backend"
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" run --backend "$backend"
  bash "$package/RUN.sh" status
)
```

The default numerical checkout is `$HOME/ElectronFieldTopology-adaptive-q-screen-20261117`. The existing source-results publication checkout is `$HOME/ElectronFieldTopology-stability-literature-record-20261122`. Override either with `--repo PATH` or `--source-publication PATH` on every relevant command if yours differs. The new publication clone defaults to `$HOME/ElectronFieldTopology-Q21-conditioning-record-20261122` and can be overridden with `--publication PATH`.

The preflight requires≥10GiB available RAM,≥1GiB free swap and≥56GiB free disk. Existing memory protection and sleep inhibition are retained. Run sequentially; keep Open WebUI stopped during this campaign as previously arranged. No automatic swap changes are made. There is no overall time cap.

## Monitor and recover

```bash
bash "$package/RUN.sh" status

# Request an orderly pause; then wait for runner_alive:false and service_active:false.
bash "$package/RUN.sh" stop
bash "$package/RUN.sh" status

# Resume the same campaign with its original backend, source, checkpoints and ledger.
bash "$package/RUN.sh" resume --backend "$backend"
bash "$package/RUN.sh" status
```

Do not repeat install/publish to restart a calculation. Do not remove the pointer or attempt ledgers. An attempt charged before a shutdown stays charged. The report and CSV files are updated between cases; the heartbeat reports the live operation between updates. Full restart/best/endpoint fields stay local. Readiness, early stops, excluded unmatched samples and unused allocation are all explicit.

## When complete

Wait for `complete_pending_review`, `runner_alive:false` and `service_active:false`. Open the reported `REPORT.html` directly in a browser. It contains actual sample points, validated response curves, fit selection, confirmation results, gate outcomes and links to complete CSV/JSON measurements. `RESIDUAL-AUDIT.json` contains the read-only localized/spectral and constrained-Hessian measurements.

To provide a uniquely named compact archive for assessment:

```bash
repo="$HOME/ElectronFieldTopology-adaptive-q-screen-20261117"
run_dir="$(python3 - "$repo" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])/'.git/q21-conditioning-last.json'
print(json.loads(p.read_text())['output'])
PY
)"

assessment_zip="$HOME/Downloads/ElectronFieldTopology-Q21-conditioning-completed-$(date -u +%Y%m%dT%H%M%SZ).zip"
cp --update=none -- "$run_dir/evidence.zip" "$assessment_zip"
sha256sum "$assessment_zip"
```

To record the entire compact result and analysis through the workstation:

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" record-results
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

The result snapshot includes every measured update, failed/deferred dispositions, fitted-model diagnostics, selected-value trial and longer comparison if allocated, plus field hashes and the repaired single-capture compact seal. Full fields remain on disk. The original source and its preserved pre-repair archive are unchanged.

No numerical success is claimed by installing or merging this plan. No stability or motion claim follows from a favorable conditioning curve. The next scientific decision depends on the actual measured force/acceleration, region/spectrum findings and unchanged admission gates.
