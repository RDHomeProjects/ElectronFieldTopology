# Q17–Q32 corrected-policy continuation — 20 November 2026

This handover records the completed policy audit and continues **only the six affected retained branches**. Each branch has a **500 total attempted-step ceiling**, including work already spent. This is not 500 additional steps, and it does not reopen the other 28 cases. At most **1,738 additional attempts** are authorized by this package. Corrected plateau, representation, resource and numerical checks may stop earlier.

| Branch | Already spent | Additional maximum | Grid | Backend |
|---|---:|---:|---:|---|
| Q18 axial 6–3 | 217 | 283 | 97³ | Retained CUDA |
| Q21 axial 7–3 | 210 | 290 | 97³ | Retained CUDA |
| Q22 cable source family | 200 | 300 | 161³ | Retained CUDA |
| Q24 torus72 5–2 | 210 | 290 | 97³ | Retained CUDA |
| Q30 axial 6–5 | 210 | 290 | 129³ | Retained CUDA |
| Q30 torus72 8–2 | 215 | 285 | 161³ | Retained CUDA |

The 23.04 box, grids, optimizer, CG memory, alpha, float64 precision and scientific gates remain unchanged. CUDA performs optimizer steps; CPU diagnostics and energy/gradient audits govern acceptance. All six parents already qualified on the zbook's RTX 2080 Super Max-Q. Device/runtime identity must match; this handover does not silently substitute CPU or benchmark a new trajectory. CPU thread allocation remains four. The CPU/GPU combination is inherited from the recorded run.

## Before starting

Keep the original campaign interrupted. Do not resume the old screening or recovery launchers. Keep Open WebUI stopped and avoid simultaneous large numerical or rendering jobs. Require 10 GiB available RAM, at least 1 GiB free swap and 40 GiB free disk before launch. The service retains the successful recovery limits: 7 GiB memory.high, 8 GiB memory.max and 1 GiB maximum swap. Sleep, idle and lid-triggered suspension are inhibited while the service runs. A sustained host-pressure condition requests an orderly checkpoint pause. No overall wall-time cap is imposed.

Original numerical checkout (kept at its pinned commit):

```text
~/ElectronFieldTopology-adaptive-q-screen-20261117
```

Original input run:

```text
artifacts/adaptive-q17-q32-screen/20261117t133953z-d6617788
```

All timestamps contain UTC and Australia/Melbourne. Original files are read and locked, never overwritten. A new policy-versioned run copies exact parent checkpoint bytes and verifies every migrated optimizer array and scalar. Retained measurements are replayed on CPU and CUDA gradients are checked before that branch takes a continuation step. The same numerical sources and dependency locks are required.

## Install, publish and run

Run as the normal `rd` user. Only service creation asks for sudo. GitHub actions occur exclusively through these local workstation commands. Publication uses a separate clone, `~/ElectronFieldTopology-policy-v2-record-20261120`; the numerical checkout is not switched, pulled or merged.

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-policy-v2-continuation-20261120.zip" -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-policy-v2-continuation-20261120"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" preflight
  bash "$package/RUN.sh" run
  bash "$package/RUN.sh" status
)
```

Preflight hashes and CRC-checks the six retained optimizer checkpoints and six endpoint fields. The supervised worker then verifies actual float64 arrays, optimizer memory, CPU metrics and CUDA parity. Startup alone is not evidence of optimizer progress. The first CPU replay on a 161³ field can take several minutes; status names the current seed and the heartbeat continues during diagnostics.

Publication records live under `docs/research/q17-q32-policy-v2-20261120/`, with a root README link and the audit, frozen plan and runnable package. Existing reports and graphics are retained. This additive documentation path avoids changing the protected identities of earlier studies. Local documentation/project-record and whitespace checks run before publication; the merge helper requires passing PR checks and the exact committed head. Squash merges are recognized without assuming original commit ancestry or relying on a missing PR number.

## Status, pause and resume

```bash
package="$HOME/Downloads/ElectronFieldTopology-policy-v2-continuation-20261120"
bash "$package/RUN.sh" status
bash "$package/RUN.sh" stop
```

Stop requests wait for a safe optimizer boundary, diagnostic and checkpoint; do not force-kill the process. Check status until `runner_alive` is false and the service is inactive. Then resume the same run:

```bash
bash "$package/RUN.sh" resume
bash "$package/RUN.sh" status
```

After an OOM or abrupt power loss, a retained `working` record can resume only when no service/worker remains. Every attempted step remains charged even if its execution was interrupted. The last sealed accepted state is restored. A pending allocation retains its original target and decision, so the same plateau vote is not counted twice. A scientific/numerical `failed` record is not automatically resumed: provide its log and evidence for assessment.

```bash
journalctl -u matter-waves-q17-q32-policy-v2.service -n 50 --no-pager
```

## Interpretation and next-stage limits

Open the new run's `REPORT.html` in a browser. It shows measured force and acceleration normalized by their gates, with optimizer iteration on the horizontal axis. These are not physical-time animations. The report distinguishes accepted checkpoint iteration, measured iteration, total attempts and additional attempts. `decisions.json` records fits, forward validation, model disagreement, slope/curvature turns, plateau evidence and resulting dynamic allocation/observation spacing. Fits guide measurements and allocations; they cannot certify a pass or guarantee convergence.

The corrected policy resets plateau memory at every 200-iteration CG epoch and requires at least eight distinct current-epoch observations before a stagnation vote. It retains the original 150-iteration minimum and three supported decisions to stop. Both the iteration-200 and iteration-400 transitions are covered by regression tests.

This package stops after preparation reassessment. It explicitly defers new mesh, domain and motion work until the corrected endpoints are reviewed. The interrupted Q18 refinement remains tied to its old parent: **33 charged attempts, checkpoint iteration 32, last measured iteration 30**. Its 33 spent attempts remain part of the original refinement allocation; they are not reset or attached to a changed parent.

All old negative findings remain valid measurements: no measured broad endpoint passed stationarity, and the 29 representation-admitted endpoints failed boundary admission. Correcting six premature stops does not retrospectively pass a gate or reject a Q sector. The 500-step extension tests additional preparation opportunity without asserting that motion or long-term stability will follow.

## Completed results and local publication

At `complete_pending_review`, the run contains sealed `evidence.zip`, `REPORT.html`, `record.json`, decision histories and a full-field hash manifest. Full float64 fields and CG memory stay local; compact evidence contains their declarations. This package does not claim a remote full-field archive exists.

To record the completed results locally and publish them through a separate PR:

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" record-results
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

Copy a uniquely named compact evidence ZIP for assessment:

```bash
repo="$HOME/ElectronFieldTopology-adaptive-q-screen-20261117"
run_dir="$(python3 - "$repo" <<'PY'
import json,sys
from pathlib import Path
print(json.loads((Path(sys.argv[1])/'.git/policy-v2-last-run.json').read_text())['output'])
PY
)"
assessment_zip="$HOME/Downloads/ElectronFieldTopology-policy-v2-results-$(date -u +%Y%m%dT%H%M%SZ).zip"
cp --update=none -- "$run_dir/evidence.zip" "$assessment_zip"
sha256sum "$assessment_zip"
```

The included [policy assessment](assessment/ASSESSMENT.html) and [validation record](HOST-VALIDATION.json) distinguish tests executed here from full-field/CUDA checks that must run on the zbook. There were no new production solver steps or GitHub operations during package creation.
