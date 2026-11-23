# Next scientific run: retained-field audit and Q21 fixed-box resolution

This package follows the merged Q21 conditioning results and review (PR94). It performs a read-only Q2–Q32 endpoint audit, replays Q21's actual final baseline at native545, and conditionally tests resolution while holding box30.72 and the original action/gates fixed. It does not repeat the conditioning sweep across all charges. The scientific design and interpretation limits are in PROTOCOL.md; exact source identities are in SOURCE.json.

## Run on the zbook

Keep Open WebUI and other large workloads stopped. The completed storage cleanup left about220GiB free and did not remove the required computational/source folders. This package does not delete or move any prior data.

```bash
unzip -n \
  "$HOME/Downloads/ElectronFieldTopology-Q21-resolution-and-retained-audit-20261123.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-Q21-resolution-and-retained-audit-20261123"
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

`auto` qualifies one backend at launch: normally CUDA float64 relaxation with independent CPU measurements/audits if faster and qualified, otherwise CPU. `backend="cpu"` selects CPU explicitly; `backend="cuda"` requires CUDA. The backend remains fixed through all branches and resume. Larger grids that do not fit are deferred rather than silently switched to another backend or box. CPU mode may admit grids that exceed VRAM bounds. No new source field or seed is synthesized to conceal a missing retained candidate.

The package uses the existing numerical checkout and its uv/CPython3.12.14 environment:

```text
~/ElectronFieldTopology-adaptive-q-screen-20261117
```

It uses the retained PR94 checkout to verify published source bytes:

```text
~/ElectronFieldTopology-Q21-conditioning-results-record-20261123
```

Publication uses a separate, reusable checkout rather than creating a new dated publication clone every time:

```text
~/ElectronFieldTopology-scientific-publication
```

All GitHub actions are performed through Git/gh on the zbook. Installation adds a new docs/research study, protocol and immutable preparation snapshot; it preserves existing reports, administrative records, images and videos. The numerical checkout stays pinned to its prior source commit. Essential local record/document checks and exact post-merge payload verification are included. Ignored runner.log payloads are explicitly staged when recording completed evidence.

## What will run

1. Authenticate the completed conditioning compact archive and the final baseline, earlier best, selected-shift contrast and unchanged Q2 reference. Replay the native measurements and localize the final residual. No old source is re-relaxed at this stage.
2. Inspect the finite189-state endpoint/milestone catalogue spanning Q2–Q32. Qualifying native D4 fields receive read-only gate, regional and residual-quantile measurements. Full spectral diagnostics are limited to the registered representative subset. Missing fields, unknown geometry/operators, unsupported legacy schemas and unavailable memory are explicitly deferred. Original and secondary rapid-screen runs remain separate.
3. If Q21 remains an admitted but unresolved core-dominated field, run an exact-memory129³ control and reset-memory fixed-box trials at129,145,161,177,193³, subject to geometry/resource admission. Each has at most80 newly charged attempts, with responses at30 and80 accepted updates. The native restart at update55 is recorded.
4. Allocate up to two adaptive intermediate meshes, using validated within-support predictions where possible or measured slope changes/gaps when fits are unsupported. Measure every accepted update; preserve failed fits. At least five distinct matched spacings are required to qualify a response model.
5. Only a measured joint benefit persisting at both30 and80, without excessive component worsening, can trigger matched baseline/candidate continuation to120. The total ceiling is720 charged optimizer attempts. Stops, failures and unspent budget remain explicit. There are no physical-time steps.

The first resampling measurement is separate from each relaxed result. Finer-grid interpolation alone is not proof of a stationary solution. New optimizer methods, domain/seed changes, perturbation tests, motion and blanket Q2–Q32 relaxation remain deferred for assessment of these results.

## Resources and progress

The service uses MemoryHigh7GiB, MemoryMax8GiB, MemorySwapMax1GiB, four CPU threads and sleep/lid inhibition. Launch requires10GiB MemAvailable,1GiB SwapFree and56GiB free disk; ongoing reserves are6GiB host RAM and40GiB disk. These retain the previous recovery policy. The temporary extra swap from the earlier session may need reactivation after a reboot; a failing check is reported rather than relaxed.

There is no two-hour or other total runtime cutoff. Up to720 measured attempts across different meshes, plus read-only replays of189 registered files, can take materially longer than the previous129³-only study. Resource deferrals and early stops can reduce work. Component timings are collected so later estimates can use measured throughput instead of just the attempt count. Full float64 checkpoints stay local; this is not a 31-charge full relaxation sweep or a310GiB retention allocation.

```bash
bash "$package/RUN.sh" status
```

The status prints the run directory, live phase/heartbeat, resource telemetry, report and evidence paths. REPORT.html is browser-readable. The Q2–Q32 ledger, all measured updates, curve fits, component timings, initialization corrections, deferrals and full-field hash manifest form the compact evidence. Live telemetry files are excluded from final checksums; a frozen telemetry snapshot is included.

For an orderly pause and subsequent resume:

```bash
bash "$package/RUN.sh" stop
bash "$package/RUN.sh" status
# Wait until the worker and service have stopped before resuming.
bash "$package/RUN.sh" resume --backend "$backend"
```

Do not rerun run after a run has been created. Resume retains package identity, selected backend, native phase, accepted checkpoints and all charged attempts, including interrupted work. An OOM or failed scientific instrument requires review; do not repeatedly restart it without examining the recorded reason.

## Return completed evidence

When status is complete_pending_review and both worker/service are inactive, copy the printed evidence.zip to a unique name in Downloads and attach it for scientific assessment. Keep all full fields in their original locations. The generated compact archive does not contain them, and recording hashes is not an archive of the arrays.

After review, the available record-results, publish and merge commands can publish the completed raw evidence additively. An assessment of new outcomes must accompany any subsequent interpretation; preparation publication alone does not certify scientific success.

## Host validation

HOST-VALIDATION.json records actual local fixture tests and limitations. The tests exercise CPU numerical identities, one-factor resampling, curve eligibility, budget/accounting and recovery behavior, legacy metadata handling, output sealing and local Git publication. The real129³ Q21 fields and the zbook GPU are not available to the build host; their replay/qualification is enforced on the zbook before run creation. No GitHub interaction or scientific production run is performed while building this package.
