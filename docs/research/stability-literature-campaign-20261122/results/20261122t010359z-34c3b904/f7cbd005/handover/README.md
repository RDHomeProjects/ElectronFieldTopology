# Literature-guided stability campaign: Q21 assessment and controlled diagnostics

This additive handover records the scientific assessment of the completed iteration 315–335 tranche, whose raw results were merged in PR90. It then investigates the applicable numerical options from the focused literature review. Existing scientific records, negative findings, images and positive historical native-cell results stay intact.

The input evidence archive is frozen at SHA256 `fbaea1e1fac22151406f2393d3ff1c1066ef7499f45f7fbd5e68cd3001544f1a`. It has89 verified compact payload members and22 retained field declarations. Exact endpoint335 is SHA256 `e2a7d4e300f9f7e7e0993f42e56b7f33eacaba4c7b32f0a3ed91d108fca23da0`. Full field bytes remain on the workstation and must pass replay before any allocation.

Read [the scientific assessment](assessment/ASSESSMENT.html), [literature applicability](LITERATURE.md), [the option matrix](OPTIONS-PLAN.md) and [the frozen plan](PLAN.json). Optimizer iteration is not physical time. A failed numerical preparation is not a proof of physical nonexistence.

## Scope and limits

Nineteen declared independent arms cover exact continuation, optimizer alternatives, signed symmetry breaking, scale, resolution, box extent, alternative map families and qualified negative-curvature perturbations. All original force, acceleration, tail, guard, unit and representation gates remain unchanged. The maximum new optimizer allocation is2300 charged attempts across all arms; no unused budget is reassigned.

Each accepted update is measured. After a20-attempt initial probe, validated linear/quadratic/exponential fits constrain5–10-attempt decision blocks; measurements are dense even near turns. Three repeated joint-progress failures after at least 80 charged attempts can stop a branch. Resource, representation, line-search and measured-stationarity stops apply sooner. Longer literature iteration counts motivate a bounded slow-relaxation control, not an unbounded run or a direct conversion of published iteration counts.

Matched-step comparisons and dependency fits are saved in `RELATIONSHIPS.json`. Four signed bend values plus the unperturbed matched baseline allow leave-one-out curve validation. Three-point mesh/domain/scale relationships remain measured comparisons without a validated extrapolation. The static scale sweep measures up to two extra points around an interior fitted energy extremum.

Geometric diagnostics use a declared regular near-south preimage. Open/nonmanifold traces, singular framing and poorly converged writhe/twist quadrature remain unresolved. A matrix-free constrained Hessian is sampled in eight smooth tangent directions, at two epsilon values, with approximate translation and target-rotation modes removed. It is a tested-subspace landscape measurement at a nonstationary field, not a complete minimum eigenvalue or physical stability certificate.

Conditional physical-time checks run only if mesh129 and mesh161 endpoints pass all unchanged readiness gates and two-grid energy/field consistency. The admitted fine Q21 and Q2 control then receive paired rest/boost screens with dt0.01 and0.005, duration0.2. At most300 integration/qualification call allocations are charged; retries do not refund them. If no candidate qualifies, `MOTION.json` records a deferral and no physical-time integration is run. This is not long-time stability.

Internal rotation in a massive model, periodic-string buckling, TCGL supercurrent coupling and mathematical existence are assessed in the literature/option ledger. They do not silently change the neutral massless action or its gates. In particular, the cited isospinning frequency interval has no positive member at mu=0. Changed-potential/coupled models require separately qualified actions and controls.

Q22 recovery is not repeated over the same exhausted broad inventory. Its incomplete coverage is preserved. If you know the exact historical file, pass `--q22 /absolute/path/to/final.npz` to both preflight and run. Only SHA256 `1412f284fa0634519babc384329b10cebb924986c97ef7833d3ff8955abafcc1` is accepted for the original-grid native-cell/D4 evaluation; otherwise it remains explicitly deferred.

## Workstation preparation

Keep Open WebUI stopped and avoid concurrent rendering or other numerical jobs. Launch requires10 GiB available RAM,1 GiB free swap and56 GiB free disk; runtime retains a40 GiB disk reserve. The additional temporary swap file used previously is active only until reboot unless independently made persistent. This package does not change swap or system startup settings.

A systemd service enforces MemoryHigh7 GiB, MemoryMax8 GiB, MemorySwapMax1 GiB, four numerical CPU threads and a sleep/lid inhibitor. Shutdown and power loss can still interrupt it. Work is sequential. `auto` qualifies CUDA per grid when available and within the declared VRAM estimate; otherwise it explicitly records CPU selection before that arm starts. A failed CPU/CUDA parity audit never triggers a fallback. A running arm retains its selected backend and full optimizer memory on resume. Exact-CG means complete optimizer-memory continuation; an explicitly recorded CPU/CUDA transfer is not a claim of a bitwise-identical floating-point trajectory.

The numerical checkout stays pinned at commit `1437dd367a833fe0047dbd249beb7f098a23b700`. All numerical source and lock hashes are checked against the previously validated source manifest. Publication uses a separate clone, local Git and gh on the zbook. No GitHub operation has been performed from the assistant environment.

## Publish assessment and run

```bash
unzip -n \
  "$HOME/Downloads/ElectronFieldTopology-stability-literature-campaign-20261122.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-stability-literature-campaign-20261122"
backend="auto"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" preflight --backend "$backend"
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" run --backend "$backend"
  bash "$package/RUN.sh" status
)
```

Use `backend="cpu"` to force CPU throughout, or `backend="cuda"` to require CUDA. Qualification and diagnostic measurements still use the independent CPU reference. `preflight` replays Q2 and exact335 and checks all22 retained source field hashes; it creates no analysis run. Publication adds the reviewed assessment, bibliography supplement, plan and reproducible handover under `docs/research/stability-literature-campaign-20261122` and links it from project/literature navigation. It does not duplicate PR90 or change the source numerical checkout.

## Monitor, stop and resume

```bash
bash "$package/RUN.sh" status
```

An immediate starting status may precede the first heartbeat. Inspect service logs if it stays there:

```bash
sudo journalctl -u matter-waves-stability-literature.service -n 80 --no-pager
```

Request an orderly pause:

```bash
bash "$package/RUN.sh" stop
bash "$package/RUN.sh" status
```

Wait for both runner and service to be inactive before resuming with the same requested backend:

```bash
bash "$package/RUN.sh" resume --backend "$backend"
bash "$package/RUN.sh" status
```

Do not start a second `run` after a campaign exists. Completed campaigns are not reopened automatically. Interrupted/uncommitted attempts remain charged. A branch keeps two alternating complete restart slots, its best joint-residual checkpoint and endpoint. Every accepted update is measured, but intermediate unretained fields are not claimed available. The retained best point and last endpoint are identified separately; a best-force observation is not confused with a best-acceleration state.

## Review and record completed outcomes

After `complete_pending_review`, with runner and service inactive:

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" record-results
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

Open `REPORT.html` in the output directory. It links measured branch histories, `OPTIONS.json`, `RELATIONSHIPS.json`, `MODEL-AUDIT.json`, `CURVATURE.json`, `SCALE-SWEEP.json`, `MOTION.json`, the field manifest and explicit failures/deferrals. Full NPZ arrays and native build products stay local. Compact evidence contains their SHA256 records and scientific measurements.

To make a uniquely named evidence copy:

```bash
repo="$HOME/ElectronFieldTopology-adaptive-q-screen-20261117"
run_dir="$(python3 - "$repo" <<'PY'
import json,sys
from pathlib import Path
print(json.loads((Path(sys.argv[1])/'.git/stability-literature-last.json').read_text())['output'])
PY
)"
assessment_zip="$HOME/Downloads/ElectronFieldTopology-stability-literature-completed-$(date -u +%Y%m%dT%H%M%SZ).zip"
cp --update=none -- "$run_dir/evidence.zip" "$assessment_zip"
sha256sum "$assessment_zip"
```

All recorded events include UTC and Australia/Melbourne timestamps. There is no overall wall-time cap or completion-time promise. The included host validation covers small-grid CPU mechanics and local publication control flow, not the unseen workstation fields, real CUDA hardware or a guarantee that any candidate will become stable.
