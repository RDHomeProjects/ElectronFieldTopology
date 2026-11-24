# Q21 footprint mapping and controlled minimizer assessment

This zbook handover records the completed Q21 CPU results and the detailed scientific review, then runs the next two assessment stages. All GitHub operations are executed by the workstation commands below. No GitHub operation or full-field Q21 run has been performed by the assistant.

The source is **20261123t130300z-db9ba00c**, specifically the final `cases/cpu-177/endpoint.npz` and `cases/cpu-193/endpoint.npz`. Best snapshots are retained but never silently selected instead. The numerical checkout defaults to `$HOME/ElectronFieldTopology-adaptive-q-screen-20261117`.

## Scope and budget

- Read-only native field mapping of both Q21 endpoints, plus the authenticated Q2 reference when available. Energy, angular variation and squared force/acceleration capture are measured as a buffered bounding box grows. Additional probes resolve steep changes and the capture-target crossing.
- A fixed **177³**, **30.72 model-unit** box comparison from the exact same final native iteration-625 field. One arm continues the inherited Sobolev conjugate-gradient algorithm with its retained memory. The other removes conjugacy memory at every step, giving projected Sobolev steepest descent. Shift, action, line search, alpha policy, restart schedule, precision and gates remain equal.
- **40 initial attempts per arm**, then measured-progress conditional extensions of 5–20 attempts, to **120 per arm / 240 total maximum**. Each arm also has a ceiling of 3,200 optimizer energy-gradient calls. Unused or interrupted attempts are not transferred or refunded.
- Every accepted update is measured. Recent joint force/acceleration progress is required for extension. Linear, quadratic and exponential curves use chronological holdout validation against a last-value baseline; only qualified joint fits can determine a longer next batch. A short five-attempt validation batch can proceed on measured progress without a qualified forecast. There is no overall wall-time cap.
- Native fixed-grid scientific gates are unchanged. No physical-time evolution is executed. A footprint capture target is an exploratory geometry-selection rule, not a new scientific gate or truncation-error estimate.

**This package does not implement coupled-grid evolution.** It produces the patch-footprint evidence and method comparison needed to qualify that later implementation. Treating a cropped region as an isolated system is deliberately not substituted for a coupled solve. The protocol registers the required next qualification decisions explicitly.

## Extract and publish the assessment and plan

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-Q21-footprint-minimizer-20261124.zip" -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-Q21-footprint-minimizer-20261124"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
)
```

Publication uses a separate checkout, `$HOME/ElectronFieldTopology-Q21-footprint-publication-20261124`, with an additive index under `docs/research/q21-footprint-minimizer-20261124`. It retains the received evidence, original source provenance, assessment, figures and entire execution package. It links the root README and the previous criteria supplement when present. Existing records are not rewritten. Repository record checks, documentation checks, staged whitespace checks, available PR CI checks and post-merge payload verification are required. A squash merge is verified by merge receipt and payload bytes; an old head commit need not be an ancestor of main.

If the numerical source directory was moved, use `--repo /actual/checkout` on **every** command. If the exact completed source run was moved, pass `--source-run /actual/run/directory` to preflight/run/resume. No search for a similarly named prior run is performed.

## Preflight and launch

Close unrelated heavy applications, keep Open WebUI stopped, connect AC power and use the existing pinned numerical environment. Start as the normal user; the service setup requests sudo.

```bash
backend="auto"

(
  set -euo pipefail
  bash "$package/RUN.sh" preflight --backend "$backend"
  bash "$package/RUN.sh" run --backend "$backend"
  bash "$package/RUN.sh" status
)
```

The campaign is supervised by `matter-waves-q21-footprint-minimizer.service`. Host limits remain 7 GiB MemoryHigh, 8 GiB MemoryMax and 1 GiB service swap. Launch requires at least 10 GiB available host RAM, 1 GiB free swap and 40 GiB free disk. The service inhibits sleep/idle/lid suspension. It does not prevent power loss or a system shutdown and does not modify global power settings.

Both method arms use the same backend. `auto` checks CUDA geometry against a 1 GiB device reserve and explicitly chooses CPU when CUDA is unavailable or cannot fit. Read-only footprint calculations use CPU. Explicit `--backend cuda` fails if CUDA admission is not met; choose `auto` or `cpu` to allow CPU execution. Backend is pinned for the lifetime of a branch; resume never silently transfers it. On this 8 GiB GPU, CPU selection for 177³ is expected if the reserve cannot be preserved.

Auto routing is based on admission and kernel qualification, not a fresh native-size speed benchmark. The comparison records actual runtime. Mapping the retained 193³ field also requires its conservative host-memory estimate to preserve the 6 GiB reserve; this can require slightly more than the basic 10 GiB available-RAM launch minimum.

Preflight checks actual source hashes, both endpoint CRCs/seals, the pinned Python 3.12.14 runtime and numerical source/locks. It never fetches or changes the scientific checkout. Native backend and independent directional-gradient checks occur before each arm's first update. Local test fixtures qualify code paths, not the full workstation fields or CUDA device.

## Monitor, pause and resume

```bash
bash "$package/RUN.sh" status
```

An orderly stop completes the current mapping task or measured accepted update before sealing evidence:

```bash
bash "$package/RUN.sh" stop
bash "$package/RUN.sh" status
```

Wait until service/worker are stopped before resuming or collecting. After an interruption:

```bash
bash "$package/RUN.sh" resume --backend auto
bash "$package/RUN.sh" status
```

If resume reports a backend difference, repeat with the original explicitly reported backend, normally `--backend cpu`. Do not rerun install/publish/merge as a recovery mechanism. Native optimizer counters, memory and alpha are restored from sealed alternating checkpoints; precharged attempts and objective calls remain spent. If the service failed before worker launch, inspect the service journal rather than deleting the run pointer.

```bash
sudo journalctl -u matter-waves-q21-footprint-minimizer.service -n 60 --no-pager
```

## Completion, collection and publication

```bash
bash "$package/RUN.sh" status
bash "$package/RUN.sh" collect
```

Open the reported `REPORT.html` directly in a browser. Collection prints a unique evidence ZIP in Downloads and its SHA256. The compact ZIP includes response curves, footprint maps, decisions, deferrals, timestamps, code and full-field seals. Full NPZ checkpoints stay on the zbook and must be retained; publication of compact evidence alone is not permission to delete them.

The raw completed experiment can be recorded using:

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" record-results
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

Then provide the uniquely named collected ZIP for scientific assessment. The generated summary reports measurements and stopping reasons; it does not manufacture a scientific winner or authorize another campaign. Failed or interrupted runs are collected for review rather than automatically published as completed experiments.

## Review materials

- [Detailed previous scientific assessment](assessment/ASSESSMENT.html)
- [Registered protocol and decision sequence](PROTOCOL.md)
- [Executable plan](PLAN.json)
- [Source identities](SOURCE.json)
- [Primary literature and method limitations](LITERATURE.md)
- [Host validation and remaining workstation checks](HOST-VALIDATION.json)

All run records use UTC and Australia/Melbourne timestamps. Fractions are not percentages; model units are not SI electron units.
