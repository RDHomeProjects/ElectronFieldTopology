# Adaptive Q17–Q32 screening on the zbook

This is one integrated, restartable screening campaign: retained Q2 instrument control, authenticated native Q22/Q17 cell-versus-D4 comparison, 34 fresh starts across Q17–Q32, adaptive preparation, bounded mesh/domain checks and conditional short coasting screens. No previous Q2–Q16 work or failed outcome is replaced. Source equations, couplings and measured scientific gates remain fixed.

## Install, publish and start

Download the ZIP into Downloads. The default local clone source is the completed PR79 publication checkout. A new checkout is created at `$HOME/ElectronFieldTopology-adaptive-q-screen-20261117`. All GitHub operations, optional archived-field restoration and numerical work execute on the zbook.

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-adaptive-Q17-Q32-screen-20261117.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-adaptive-Q17-Q32-screen-20261117"
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

`merge` waits for hosted checks. The actual repository project-record and Markdown validators must pass before commit. Existing parent assessment content is authenticated without requiring the pre-squash source commit to be an ancestor of main. The new study is prepared, not represented as an already completed numerical result.

`preflight` runs small independent numerical instruments, replays retained Q2 and the native comparison, and qualifies the first required geometry. It can take several minutes. `run` starts a detached worker; the terminal can be closed after launch. Additional geometries are timed and qualified when actually required. No two-hour or overall wall-time cap is imposed.

## CPU, GPU and mixed execution

| Setting | Behaviour |
|---|---|
| `backend="auto"` | Recommended. Choose CPU or qualified CUDA for each geometry using measured synchronized optimizer cost, CPU audits and checkpoint overhead. Larger grids can use CPU while others use GPU. |
| `backend="cpu"` | CPU float64 throughout. The GPU dependency extra is not requested. |
| `backend="cuda"` | Require qualified CUDA for numerical branches; stop explicitly if the device or memory cannot support a requested geometry. CPU endpoint audits remain mandatory. |

The RTX 2080 Super Max-Q is not presumed faster in float64. Auto uses CUDA only after parity checks and at least a measured 1.15 cost advantage. Device identity is recorded. Each static branch and each trajectory retains its chosen backend on resume. A numerical mismatch never triggers a silent CPU fallback. Only GPU unavailability/resource failure during initial qualification can lead auto to choose CPU.

Default CPU threads: four. Use `--cpu-threads 8`, for example, consistently on preflight/run/resume if wanted. Runtime thread overrides are recorded. The CPU and GPU do not run competing candidate workers concurrently; mixed means GPU computation plus CPU auditing and geometry-specific backend choices.

## Controls and field recovery

The exact Q2 checkpoint from the completed intermediate survey is required. The native comparison first seeks the authenticated fresh-study Q22 129-cubed endpoint, then the archived Q17 129-cubed endpoint. It keeps field bytes, grid and box unchanged and reports separately normalized cell and D4 metrics. Failure of an individual native field's D4 readiness does not stop other families.

If neither native checkpoint is available locally, preflight restores the existing verified Q17/Q19 archive to the new run's `restored` directory using the repository restore tool. The original archive is about 1.41 GiB; this is data recovery, not a new solve. Source-field hashes and historical cell energy/residual replay are checked. Existing archives and local fields are read-only. A partial restore is retained if interrupted. A retry reuses any already verified native field or creates a new recovery directory; no directory is deleted or overwritten automatically. `--no-restore` records an explicit native-field deferral instead of downloading. A native byte/hash/operator inconsistency is a blocking fault, while an individual correctly measured D4 failure is not.

## Frozen resource allocation

- **34 starts:** one balanced axial and one K(7,2)-family rational map per Q, plus source-family Q22 cable and K(5,4)-seeded comparator. Fresh labels are initialization families, not final knot identities. Profile choices are frozen; fits are within a branch over optimizer iterations, not an inferred law across different Q values.
- **Representation ladder:** fresh evaluations at 97, 129, 161 and, if needed, 193 cubed, all at full side 23.04. Failed coarse representations are retained. A fresh seed is evaluated again at the next resolution; a lost-topology coarse state is not silently prolonged.
- **Fair bootstrap:** every represented start receives up to 40 steps with five-step observations before any receives deeper work. Strict admission, representation loss or optimizer failure can stop it sooner.
- **Adaptive continuation:** at most 300 attempted optimizer steps per broad branch, including bootstrap and interrupted/replayed attempts. Batches normally span 5–75 iterations, with observations every 2–20 iterations. Recent linear, quadratic and exponential-with-nonzero-floor models are checked against strictly later withheld observations. Near thresholds, turns, disagreement or unreliable fits, batches shorten. Forecasts never pass a gate. Repeated absence of measured joint progress can defer a route after at least 150 accepted iterations, allowing some scope for delayed improvement.
- **Mesh checks:** at most four Q-diverse measured candidates, 300 attempts each. Full side stays 23.04; use 193 cubed, or 225 if the parent already needed 193. Only two stationary endpoints support the declared less-than-2% energy comparison. Candidates outside capacity are explicitly deferred.
- **Domain checks:** at most two mesh-confirmed candidates, 150 attempts each. Add eight nodes on each side at identical spacing: 193→209 or 225→241. No interpolation or field compression is used for the initial centered embedding.
- **Motion:** at most two candidates after measured static, mesh, domain and boundary checks. A fresh Q2 short-flight control precedes them. Beta 0.3, z direction, T=0.2, dt=0.01; only a passing candidate receives dt=0.005 from the identical admitted initial data. At most 140 accepted trajectory steps, plus separately recorded qualification/recovery work. This is not long-time stability. Long runs remain a later decision.

The maximum static work is **11,700 attempted optimizer steps**, often much less after gates, plateaus and deferrals. No fit automatically enlarges that budget. CPU/GPU speed and required grids determine elapsed time; the local qualification receipts report actual timings. Reserve at least 40 GiB free disk and 6 GiB available host RAM throughout; full retained states can require many additional GiB. Resource stops retain resumable data.

## Monitor, stop and resume

```bash
bash "$package/RUN.sh" status
bash "$package/RUN.sh" stop
# Wait until status reports the worker stopped before resuming:
bash "$package/RUN.sh" resume --backend "$backend"
```

Status prints the exact output directory, heartbeat, report, log and evidence paths. Open `REPORT.html` locally in a browser; `record.json`, `screening.csv`, individual histories and planner decisions supply the details. An optional `benchmark --backend "$backend"` qualifies the full declared geometry set in advance and can be expensive; normal execution qualifies lazily.

Use the same backend/thread options on resume. `--new-run` preserves the old directory and explicitly creates another run; do not use it merely to recover an interruption. Source/plan/backend identities are bound to each run. Another detected numerical worker blocks launch.

## Return and retention

On completion upload the printed **evidence.zip** and, if useful, SUMMARY.md. The compact archive includes every candidate's status/deferral, fits and validation errors, controls, device/timing qualifications, source snapshots, motion outcomes and hashes of local full states. CSV values are fractions/model units, not percentages or SI electron units. Initial fields at every sampled grid, bootstrap/endpoints, two selected turn fields per optimizer epoch, before/after conjugacy-reset states, recovery states and moving checkpoints remain local. Every scalar turn observation is retained even when its full-field snapshot allocation is exhausted. These bulk fields are excluded from the compact ZIP and must be archived and download-verified before cleanup. No automated field deletion is performed.

The prepared campaign is published first. Completed results are not automatically declared scientifically accepted or merged; return the evidence for assessment and its subsequent results publication handover. [MODEL.md](MODEL.md), [PLAN.json](PLAN.json), [HOST-VALIDATION.json](HOST-VALIDATION.json) and [retrospective checks](validation/BACKTEST.json) record scope, limits and tests.
