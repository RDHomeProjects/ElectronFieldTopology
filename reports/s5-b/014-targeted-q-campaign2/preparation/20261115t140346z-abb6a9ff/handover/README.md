# Campaign2 — publication plus controlled Q analysis

This handover first records the completed targeted600-step evidence and assessment, then publishes the next prepared campaign through your local workstation. It subsequently runs the campaign in a separate checkout. No GitHub operation was performed while preparing this package.

## Local publication and launch

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-campaign2-20261115-r2.zip" -d "$HOME/Downloads"
package="$HOME/Downloads/ElectronFieldTopology-campaign2-20261115-r2"
(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" preflight --backend auto
  bash "$package/RUN.sh" run --backend auto
  bash "$package/RUN.sh" status
)
```

Defaults: source checkout `$HOME/ElectronFieldTopology-rapid-q-followup`; new publication/calculation checkout `$HOME/ElectronFieldTopology-campaign2`. The existing calculation checkouts and fields remain at their original locations. Python3, git and authenticated gh are required for publication; uv supplies the existing locked Python3.12.14 scientific environment for local preflight and execution. No scientific source or dependency lock is changed by publication.

`install` clones locally, fetches main, records the completed results under the existing bounded follow-up study, and registers a separate prepared campaign study with frozen plan and handover. It renders navigation and runs actual project-record/documentation/whitespace checks before staging is accepted. `publish` commits, pushes a dedicated branch and creates a PR; `merge` waits for PR checks and pins the merge to that head. No automatic destructive reset or force push is used. If main advances, checks fail or the checkout changes, preserve it and provide the output for reconciliation.

Numerical preflight is blocked until this campaign preparation is recorded as merged. The source checkout has not been fast-forwarded or switched by these commands; numerical source hashes and the actual selected checkout commit are recorded. Preflight runs in the foreground. Production then runs in the background.

## Frozen allocation

| Branch | Starting state | Maximum new production steps |
|---|---|---:|
| Q8 | completed121³ iteration600,box23.04 | first150,then up to two conditional50-step batches; **250** |
| Q10 | completed145³ iteration300,box23.04 | **150**,then read-only behavior diagnosis |
| Q4 exact control | original121³ iteration1300,box23.04 | **50** |
| Q4 memory-clear trial | same field,alpha and native count; only old_g/old_z/direction cleared | **50** |
| Q5 domain control | completed fine121³ iteration100,box23.04 | **50** |
| Q5 expanded domain | same parent,145³,box27.648,spacing0.192 | **50** |

Total maximum **600 additional accepted production steps**. Q6 receives zero relaxation pending review of the Q4 comparison; Q7/Q9 remain explicitly deferred. No automatic motion, mesh campaign or changed scientific gate follows. A scientific stop can use fewer than its allocation; unused steps are not redistributed.

Q8’s first150 steps are one initial logical allocation. After that, each additional50-step batch requires recent-window progress: median joint force/acceleration gate multiple over the recent50 steps must improve at least5% versus the preceding50, and median acceleration must not worsen over10%. Values are uniformly sampled at five-step positions using log interpolation, so dense adaptive observations do not dominate the medians. Improvement measured from the original start cannot override a recent plateau. The cap is250, not450. Q10 has its own requested150-step allocation without Q8's progress cutoff.

Every branch stops on representation loss, solver stall or measured strict stationarity. Tail failure remains a boundary follow-up. Gates are unchanged: force≤1e-4; acceleration≤1e-3; approximate Hopf-magnitude error≤5%; corner cone>0; unit error<1e-10; rest-tail≤0.00075 with shell width2.0. These dimensionless model quantities are not physical electron time, charge or spin.

Q4 changes exactly one treatment: clear conjugacy memory once while preserving alpha. Field, mesh, box, native count, action, preconditioner, normal200-step restart rule and measurement schedule stay equal. Pair members use a common qualified backend. Q4's paired output is reported for review; the script does not automatically spend a Q6 budget or declare the trial superior from one measurement.

Q5 uses an aligned domain extension, not interpolation: the121³ parent samples are copied bitwise into indices12:133 of the145³ grid, with unit-vacuum padding. Both grids have spacing0.192. Both arms restart conjugacy and alpha=1 at native100. The former held boundary layers can evolve as interior layers in the larger box; that is part of moving the domain boundary. Initial representation, tail metrics and embedding identity are recorded before evolution. No seed rescaling or simultaneous resolution change is introduced. Passing a tail gate immediately after embedding is not a stationarity certificate.

Paired Q4/Q5 cases use common five-step observations and stop gates. Q8/Q10 keep adaptive observations near reversals, log-curve inflections, prediction discrepancies and gate margins. Full optimizer checkpoints are retained at measured observations; independent milestone fields are retained every50 steps even within the initial150-step Q8/Q10 allocations. The observer changes no optimizer step formula.

## CPU/GPU preflight and performance

All completed20 parent fields and the selected original Q4 field are verified. CPU metrics replay the selected endpoints. Every actual treatment receives independent CPU/device energy/gradient checks and three disposable CPU plus up to three CUDA continuation steps. Auto selects qualified CUDA at step speedup≥1.2; otherwise CPU is recorded. If automatic selections differ within a Q4 or Q5 pair, a common qualified CPU backend is selected for the pair. `--backend cuda` requires CUDA qualification; it does not silently fall back. No backend changes within a branch.

To choose CPU explicitly, use `--backend cpu` on both preflight and run/resume. Changing backend requests requires a fresh output allocation. Keep at least12GiB free disk and4GiB available host RAM. Four CPU threads are fixed. Avoid concurrent analysis campaigns. There is no wall-time cap.

Component timings record synchronized optimizer steps, CPU stationarity/Hopf, CPU tail, independent CPU/device audits and checkpoint compression. Other startup, hash verification and I/O remain unallocated wall time. These measurements do not automatically reduce scientific checks or claim whole-run GPU speedups.

## Path overrides

Use `--source-repo /absolute/path` for a different original checkout, and `--repo /absolute/path/to/new-campaign-checkout` consistently for a different publication/run checkout. The default completed parent is discovered by its exact evidence hash beneath the known original checkout's `artifacts/targeted-q-diagnostic` directory. The original Q4 run path is taken from that compact evidence.

If a parent was moved, supply both explicitly on numerical commands:

```bash
bash "$package/RUN.sh" preflight --backend auto --source-run "/path/to/completed-targeted-run" --prior-run "/path/to/20261114t132254z-9e6c35d4"
bash "$package/RUN.sh" run --backend auto --source-run "/path/to/completed-targeted-run" --prior-run "/path/to/20261114t132254z-9e6c35d4"
```

A new output is created below the campaign checkout's `artifacts/targeted-q-campaign2`. Later commands reuse its campaign-specific latest pointer. For an independent allocation, supply an unused `--output /absolute/path` on preflight and all subsequent numerical commands. A destination or output with an unrelated marker is preserved and rejected.

## Monitor and recover

```bash
bash "$package/RUN.sh" status
bash "$package/RUN.sh" stop
bash "$package/RUN.sh" resume --backend auto
```

Status includes heartbeat, log/report/evidence paths and UTC/Melbourne timestamps. Stop requests an optimizer checkpoint through SIGTERM. Wait for the matching worker to stop before resuming with the same configuration. A power loss can require replay from the last sealed checkpoint; no cap is enlarged. If a history/checkpoint seal is incomplete, preserve the output for reconciliation.

`REPORT.html` opens directly in a browser with measured plots and Q10 diagnostic maps. Compact `evidence.zip` includes campaign code, controls, qualification, performance components, explicit deferrals and results. Full NPZ files remain local with their hash manifest; this ZIP is not their backup. Upload the new evidence.zip when status is `complete_pending_review`.

Host tests cover array diagnostics, recent-window decisions, the actual branch control flow under a deterministic substitute engine, bitwise121→145 embedding, matching alpha/memory treatments, resume and a synthetic publication rehearsal. They do not replace full-field/actual D4/CUDA tests. The zbook preflight and real repository validators must pass locally before production or publication respectively.

## Revision2 repair

The first package omitted the nested handover SHA256SUMS from the preparation record's checksum inventory. Revision2 excludes only the preparation's own checksum file and includes every nested checksum file. It recognizes the exact original failed, uncommitted installation, verifies its existing record hashes and the original nested checksum identity, saves the preparation/marker/roadmap/staged diff under `.git/campaign2-before-nested-checksum-repair`, refreshes the nested handover to this revision and reseals the preparation without creating a second study or changing the existing valid record ID. Then it reruns the repository checks before any commit or push. Numerical code, budgets, gates and source evidence are unchanged. Retain the existing campaign2 checkout; no deletion or reset is required.
