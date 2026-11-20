# Q21 controlled preparation and historical Q22 evaluation

This handover records the completed diagnosis assessment, then runs the focused next evaluations on the zbook. Existing reports, graphics and positive cell-functional static results remain intact. All GitHub commands run locally through Git and gh in a separate publication clone. The numerical checkout is never pulled, reset or switched.

## Scope

| Activity | Allocation and controls |
|---|---|
| Record assessment and plan | Add the included assessment and this frozen handover under `docs/research/q21-q22-controlled-evaluation-20261120`; append a repository README link. Run essential local checks before publishing and merging. |
| Q2 control | Re-evaluate its exact retained field and require the original gates and metric replay before any Q21 optimization. |
| Q21 derivative validation | Two tangential directions and three centered-difference sizes on the exact iteration-295 endpoint; no optimizer updates. A failure blocks both optimizer arms. |
| Q21 paired optimizer test | Exact continuation versus clearing `old_g`, `old_z` and `direction` only. Same initial field, alpha, 97³ grid, length 23.04, action, precision and line-search policy. At most 20 charged attempted updates per arm, 40 in total. |
| Q21 measurement | Full metrics after every accepted update, with objective-call accounting, source hashes, gate outcomes and descriptive linear/quadratic/exponential fits with chronological holdout. Every accepted point is measured, including turns and spikes. Fits never grant admission or extend the allocation. |
| Historical Q22 comparison | Authenticate the original 129³, spacing 0.12, length 15.36 checkpoint by exact SHA256, then evaluate cell and D4 operators on identical stored field values. Zero relaxation, normalization, resampling or physical-time steps. |
| Explicit deferral | If the exact Q22 field is absent, record the searched locations and expected hash and finish Q21. Never replace it with the fresh 161³ preparation or a regenerated seed. |

The initial Q21 boundary gates fail; this is a diagnostic optimizer comparison, not motion admission. All gate failures remain visible. Accepted line-search alphas may diverge naturally after the controlled initial condition. A memory reset is not presumed to be a remedy.

## Record the assessment and start the evaluations

Keep Open WebUI stopped and avoid other numerical jobs. The run requires at least 10 GiB available RAM, 1 GiB free swap and 40 GiB free disk at launch. It runs sequentially in an isolated system service with MemoryHigh 7 GiB, MemoryMax 8 GiB and at most 1 GiB swap. The sleep/lid inhibitor protects the service from ordinary sleep; it cannot prevent shutdown, power loss or reboot.

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-Q21-Q22-evaluation-20261120.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-Q21-Q22-evaluation-20261120"
backend="auto"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" preflight --backend "$backend"
  bash "$package/RUN.sh" run --backend "$backend"
  bash "$package/RUN.sh" status
)
```

`auto` keeps the retained Q21 optimizer checkpoint's backend. If that is CUDA, CUDA must be available and pass the independent CPU energy/gradient check; there is no silent fallback. To intentionally use CPU for both arms, set `backend="cpu"` before starting. That shared backend transfer is recorded and is not claimed to reproduce the previous CUDA floating-point path bit for bit. Both choices retain float64 and use four CPU threads for diagnostics; Q22 uses the CPU cell kernel and D4 diagnostics. No benchmark spends candidate steps outside the 40-attempt allocation. Backend audit occurs in preflight before creating a run, before the paired arms and after each accepted update. If preflight cannot use CUDA, choose CPU and repeat preflight/run; no candidate attempt has been spent and no run has yet been created.

The Q22 default search checks its declared original study location and sibling `final.npz` files in that same study. An exact copy stored elsewhere can be supplied explicitly to both `preflight` and `run` with `--q22 /absolute/path/to/final.npz`. A wrong explicit file is refused. Nothing is downloaded or restored automatically.

## Monitor, stop and resume

```bash
bash "$package/RUN.sh" status
bash "$package/RUN.sh" stop
```

Stop is orderly: wait for the current accepted update or static evaluation and then confirm the worker and service are inactive. To resume an interrupted run using the same package and requested backend:

```bash
bash "$package/RUN.sh" resume --backend "$backend"
bash "$package/RUN.sh" status
```

The run reuses committed optimizer memory and measurements. Every attempted update is charged before execution; interruption cannot refund budget. An uncommitted attempt can be replayed only while consuming another remaining attempt. Completed arms are verified and reused. A completed or failed run is not silently restarted or duplicated. Re-running install/publish/merge is unnecessary for recovery.

## Review and record completed results

The status output provides the exact run directory, browser report, log and compact evidence ZIP. Wait for `complete_pending_review` and both `runner_alive: false` and `service_active: false`. Then record the measured results, including failures and Q22 deferral if applicable:

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" record-results
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

Upload the uniquely named completed evidence for assessment:

```bash
repo="$HOME/ElectronFieldTopology-adaptive-q-screen-20261117"
run_dir="$(python3 - "$repo" <<'PY'
import json, sys
from pathlib import Path
print(json.loads((Path(sys.argv[1]) / '.git/q21-q22-evaluation-last.json').read_text())['output'])
PY
)"
assessment_zip="$HOME/Downloads/ElectronFieldTopology-Q21-Q22-completed-$(date -u +%Y%m%dT%H%M%SZ).zip"
cp --update=none -- "$run_dir/evidence.zip" "$assessment_zip"
sha256sum "$assessment_zip"
```

Full fields and optimizer memory remain local and are listed with SHA256 values in the compact evidence. Their remote archival is not claimed. The evidence contains the assessment, frozen handover, measurements, fits, paired histories, source inventory, logs and telemetry. Open `REPORT.html` after extraction to inspect the measured graphs and interpretations in a browser.

## Interpretation and validation

Read [MODEL.md](MODEL.md), [PLAN.json](PLAN.json), the [diagnosis assessment](assessment/ASSESSMENT.html) and [HOST-VALIDATION.json](HOST-VALIDATION.json). The historical Q22 file may be stored as float32: values are preserved on promotion to float64, and no normalization is used to conceal unit error or recover lost precision. The original solver's full-precision metrics and the stored-field replay are reported separately. A replay discrepancy prompts review; it does not retroactively erase the historical static result.

Host validation uses real pinned CPU kernels on small synthetic controls, including checkpoint recovery and cell/D4 comparison. Actual Q21/Q22 fields, CUDA execution, system-service limits and the current repository's full administrative checks are validated on the workstation. This is a bounded diagnosis of preparation and operator compatibility, not a proof of stability or an electron model.
