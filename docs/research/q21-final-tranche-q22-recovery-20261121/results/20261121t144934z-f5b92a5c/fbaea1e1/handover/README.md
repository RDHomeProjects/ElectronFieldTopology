# Final Q21 exact tranche and historical Q22 recovery

This handover records the completed comparison assessment, searches retained local project files and supported archives for the exact historical Q22 field, evaluates it if recovered, and runs the final bounded Q21 continuation from the retained exact iteration-315 optimizer state. Existing reports, graphics and historical positive cell-functional results remain intact. All GitHub operations run on the workstation through local Git and gh in a separate publication clone.

## Authorized scope

| Activity | Bound and interpretation |
|---|---|
| Record assessment | Add the included browser/Markdown assessment and frozen plan under `docs/research/q21-final-tranche-q22-recovery-20261121`; preserve the raw outcomes already recorded under PR 85. |
| Q22 recovery | Search local `ElectronFieldTopology*` and `Matter-Waves*` project directories, Q22-labelled Download candidates first, then matching Download archives and NPZs. Support ZIP, tar, tar.gz, tgz, tar.bz2, tar.xz and nesting up to depth three. Accept only the exact historical SHA256. |
| Q22 evaluation | If authenticated, restore only that NPZ to the new run directory and evaluate native cell and D4 operators on the original 129³ grid, spacing 0.12, length 15.36. No normalization, resampling or relaxation. Record source dtype and archival precision limitations. |
| Q21 continuation | Exact iteration 315, including old gradient, old preconditioned gradient, direction, alpha, backend by default and all original scientific gates. Same 97³ grid and 23.04 box. First five-attempt probe; at most 20 new charged attempts, native iteration at most 335. |
| Q21 scheduling | Require at least 0.5% improvement in both recent eight-point medians versus the preceding eight before another block. Use 16-point linear/quadratic/exponential fits with three chronological holdout points to choose blocks of 5–10 attempts. Fit disagreement permits only a minimum probe when measured joint progress still passes. No fitted admission or budget extension. |
| Retention | Measure every accepted update and retain its complete float64 optimizer checkpoint. Interrupted/uncommitted attempts remain charged. Both existing source runs and all original fields stay unchanged. |
| Explicit deferral | Report search roots, filters, permissions, skipped formats/nesting, byte/member/entry limits and missing-field status. Missing bytes are not a negative Q22 result. No automatic mesh/domain change, new Q sweep or physical-time simulation. |

Q21's existing boundary admission fails. It remains a diagnostic continuation, and every failed gate remains visible. No gate threshold is relaxed to call a result ready. No further same-grid tranche is launched automatically after this final allocation.

## Run on the zbook

Keep Open WebUI stopped and avoid concurrent memory-heavy numerical jobs. Launch requires 10 GiB available RAM, 1 GiB free swap and 40 GiB free disk. The service has MemoryHigh 7 GiB, MemoryMax 8 GiB, maximum swap 1 GiB, four CPU threads and a sleep/lid inhibitor. It cannot prevent shutdown, reboot or power loss.

```bash
unzip -n \
  "$HOME/Downloads/ElectronFieldTopology-Q21-final-tranche-Q22-recovery-20261121.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-Q21-final-tranche-Q22-recovery-20261121"
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

`auto` retains the source CUDA backend and validates its energy/gradient against CPU before creating a run. To intentionally use CPU, set `backend="cpu"` before starting; the backend transfer is explicit and does not claim a bitwise continuation of the previous CUDA floating-point path. Recovery and Q22 evaluation use CPU. Work is sequential to control memory use. There is no silent CUDA fallback.

The completed comparison being recorded as source is `20261120t114719z-48b7d4cf`. Only its exact-arm endpoint `q21/exact/endpoint.npz` with SHA256 `ad5e13216a4271a212c6a67c810d4394666dc570c33c3a48ff0dc005b01cf7b0` is eligible. The memory-reset endpoint and the unretained best iteration-312 observation cannot be substituted.

## Add a known backup or archive location

Default recovery stays within declared project roots and filtered Download files. Add an external backup directory or a particular supported archive by repeating `--search-root` on the `run` command before creating a run:

```bash
bash "$package/RUN.sh" run --backend "$backend" \
  --search-root "/absolute/path/to/project-backup" \
  --search-root "/absolute/path/to/full-field-archive.zip"
```

If the exact historical field is already known, use `--q22 /absolute/path/to/final.npz` on both preflight and run instead. Its complete SHA256 must be `1412f284fa0634519babc384329b10cebb924986c97ef7833d3ff8955abafcc1`; a wrong explicit file is refused. Do not run a second `run` command after a campaign exists. Choose additional roots before initial launch; resume reuses the saved configuration.

The search is bounded by 120,000 filesystem entries, 200,000 archive members, 64 GiB of charged candidate/archive-identity/nested-stream bytes and an 8 GiB nested-archive spool limit. Repeated work after interruption remains charged. Temporary spools preserve the 40 GiB disk reserve. There is no wall-time cap or runtime promise. Archive decompression/header traversal and CRC checks are not claimed to be a universal physical-I/O byte cap. Git object databases, caches, unsupported formats and unlisted external backups are outside the default inventory; exclusions and coverage gaps are reported. The search stops after the first authenticated match.

No archive is unpacked wholesale, no original file is changed or removed, and no remote archive is downloaded. Only the authenticated Q22 NPZ is restored to `recovered/q22-native.npz` in the new run directory. If it cannot be recovered within recorded coverage, Q22 remains explicitly deferred and the Q21 tranche can still complete.

## Status, stop and resume

```bash
bash "$package/RUN.sh" status
bash "$package/RUN.sh" stop
```

Stop waits for the current chunk/evaluation or accepted optimizer update. Confirm both worker and service are inactive before resuming:

```bash
bash "$package/RUN.sh" resume --backend "$backend"
bash "$package/RUN.sh" status
```

Use the same package and requested backend. Resume preserves recovery budget, charged optimizer attempts, committed optimizer memory and pending adaptive blocks. It does not refund interrupted work, repeat a decision at the same observation or silently reopen a completed campaign. The maximum is 20 attempted updates including interrupted/replayed attempts, not 20 guaranteed accepted updates. If an interrupted block yields too few new committed observations for the next decision, it stops explicitly rather than extending the block without authorization.

## Review and publish completed outcomes

When status is `complete_pending_review`, `runner_alive` is false and `service_active` is false:

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" record-results
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

Copy the sealed compact evidence under a unique filename for review:

```bash
repo="$HOME/ElectronFieldTopology-adaptive-q-screen-20261117"
run_dir="$(python3 - "$repo" <<'PY'
import json, sys
from pathlib import Path
print(json.loads((Path(sys.argv[1]) / '.git/q21-final-tranche-last.json').read_text())['output'])
PY
)"
assessment_zip="$HOME/Downloads/ElectronFieldTopology-Q21-final-tranche-completed-$(date -u +%Y%m%dT%H%M%SZ).zip"
cp --update=none -- "$run_dir/evidence.zip" "$assessment_zip"
sha256sum "$assessment_zip"
```

Open `REPORT.html` in a browser. It includes measured Q21 graphs, allocation decisions, gate results, historical Q22 comparison or deferral, and search coverage. Full float64 optimizer checkpoints remain local; allow about 2 GiB for Q21 states plus any recovered Q22 field and temporary archive spool. Every accepted point is retained so subsequent assessment and imagery can use exact field bytes. Full-field remote archival is not claimed.

Read [PLAN.json](PLAN.json), [MODEL.md](MODEL.md), the [completed comparison assessment](assessment/ASSESSMENT.html) and [HOST-VALIDATION.json](HOST-VALIDATION.json). Host checks use synthetic controls, not the actual retained Q21/Q22 fields; workstation preflight and runtime replay authenticate those fields and the requested backend.
