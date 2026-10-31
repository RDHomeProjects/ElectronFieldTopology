# Resume the unfinished static analysis on the local GPU

The workstation's user-reported paired runs passed the GPU comparison gates and
measured about 4.5x short-solve speedup against twelve CPU threads. The
[continuation record](../reports/s5-a/gpu-continuation-2026-11-01/README.md)
separates those observations from the unfinished reproduction work.
This workflow continues issue 35 / draft PR 36; it does not automatically accept
a model, knot identification, stationary solution or completed reproduction.

## One bounded local campaign

From the existing timing checkout:

```bash
cd ~/ElectronFieldTopology-timing
git pull --ff-only
uv sync --frozen --all-groups --extra gpu --extra topology --python 3.12.14

eft_campaign_dir="artifacts/gpu-continuation-$(date +%Y%m%d-%H%M%S)"
uv run --frozen --extra gpu --extra topology --python 3.12.14 \
  python -m electron_field_topology.sf_campaign --output "$eft_campaign_dir"
```

The immutable [campaign plan](../experiments/configs/sf-j2015/gpu-continuation.json)
runs sequentially, with a **two-hour overall wall-clock budget**, reserving the
last twenty minutes for analysis. Each solve keeps the established maximum
3,000 iterations / 1,800 seconds and the same coefficients/acceptance thresholds.
Unused time is not a reason to start an unbounded sweep. The overall budget
includes setup, audits and analysis; it can expire before every planned case
finishes. The run remains an incomplete result in that event.
Checkpoint/audit shutdown and final evidence packaging can finish just after the
compute/analysis deadline; numerical work is not extended to obtain a pass.

The sequence covers Q1/Q2 controls; Q22 129³ and an explicitly bounded CG
continuation; Q18 97³ then 129³; Q22 161³ then 193³; Q18 193³; the separately
configured amplitude-one Q18 193³ alternative; same-charge competitor seeds;
and larger boxes at unchanged spacing. These are deliberate separate
trajectories/controls, not interchangeable mesh-convergence points. A stationary
Q22 continuation is reused without reoptimising it. A failed control blocks the
targets; failed charge/cell/endpoint audits block dependent refinements.

The previously rejected Q22 97³ seed is never used. Original committed configs
and interrupted result records remain unchanged. Missing archived targets are
regenerated from their specified precursors. Existing workstation timing fields
are not relaxation checkpoints and are not substituted as target endpoints.

## Evidence produced

- `campaign.json`: frozen source/config hashes, phase status and dependency paths.
- Each case has config, history, provenance, independent CPU initial/final
  audits, and **float64** `initial.npz`, rolling `latest.npz` / `previous.npz`,
  and `final.npz`. Additional iteration-200/500 fields are retained when reached.
- `analysis/`: all initial/final preimage components, nine polygon observations
  per component/target, primary/secondary cable diagram witnesses and independent
  coordinate-dilation audits. The reference diagrams are regenerated first.
- `SUMMARY.md` and `summary.json`: scalar outcomes, charge/cell/norm/stationarity
  gates, source-energy checks, mesh/domain energy changes, same-charge
  comparisons, and resolved/unresolved topology/scaling observations.
- `evidence.zip`: configs, results, histories, logs, hashes and small extracted
  curves for review. **Bulk field checkpoints stay on the workstation** to avoid
  repeatedly building large archives. This small bundle can be attached to the
  conversation for the remaining source-mapped assessment.

The terminal prints phase starts and a heartbeat every thirty seconds. Detailed
energy/residual rows are in `logs/`. Evidence is refreshed after each completed
solve and at exit. Numerical failure, analysis timeout and absent witnesses are
retained. Completed execution is not the same as passing a reproduction gate.
The amplitude-one Q18 alternative requires its own convergence evidence before
acceptance, even if it finds a promising single fine-grid state.

## Interrupt and restart safely

Use Ctrl-C for a clean interruption. The GPU runner preserves the last accepted
field before endpoint auditing; atomic writes protect the rolling checkpoint
pair against a process failure during compression. Uncatchable kills/power loss
may lose work since the latest periodic checkpoint (normally fifty iterations
or sixty seconds). Existing phase directories are never overwritten.

To resume the same campaign **within its remaining original wall-clock budget**:

```bash
uv run --frozen --extra gpu --extra topology --python 3.12.14 \
  python -m electron_field_topology.sf_campaign \
  --output "$eft_campaign_dir" --resume
```

If the terminal was reopened, replace `$eft_campaign_dir` with the exact printed
directory. Completed artifact hashes and frozen sources/configuration are
checked; changed code cannot silently resume an older campaign. The campaign
clock includes time while paused and is not reset by `--resume`. An exhausted
campaign requires a separately recorded continuation decision, not automatic
budget resets. Field restarts reset CG directions; they preserve the saved field,
not a bitwise identical optimiser trajectory.

For an individually configured bounded solve into a new directory:

```bash
uv run --frozen --extra gpu --extra topology --python 3.12.14 \
  python -m electron_field_topology.sf_relax --backend gpu \
  --config experiments/configs/sf-j2015/q22-129.json \
  --resume-checkpoint PATH_TO_VALID_FIELD.npz \
  --output artifacts/q22-individual-continuation
```

## Numerical and interpretation gates

The model/source mapping remains [SF-J2015](models/SF-J2015-static.md).
Each GPU solve executes device controls and independently compares endpoint
energy, full gradient, Hopf integral and tangent residual with the CPU backend.
Initial/final Hopf error must be within 5%; nonpositive cell cones are rejected;
the periodic 10% charge-loss stop remains. Stationarity uses the independently
measured final residual below 1e-3, never a minimiser flag alone.

The production continuation freezes the **last accepted cell margin** throughout
each line search. A deliberately rejected trial cannot replace that margin.
An independent callback verifies the accepted nodal step. This corrects mutable
trial-state bookkeeping without changing the bound `min(.2, .5*accepted_margin)`.
The earlier CPU/GPU timing defaults retain their previous behaviour so their
published comparison is not silently redefined. The manifest records the strict
continuity option. Time expiry is also checked inside production line searches.

The original 2% mesh-energy, 5% independent scale/virial, 3% source-energy,
topology-consistency and 1e-3 residual gates remain. A **new predeclared 2% target
domain-energy sensitivity check** is recorded in the plan; it is an additional
finite-box check, not a published source tolerance or a replacement for topology.
Consistent Jones polynomials alone are insufficient: finite cable witnesses or
numerical hyperbolic-complement comparisons remain separate evidence. The
summary does not certify continuum isotopy or general stability.

The review of the uploaded evidence should decide whether each target meets all
gates, changes knot/link type or remains inconclusive, and compare energies only
at matching charge/mesh with stationarity and uncertainty qualifications. No
electron/charge claim follows. AI assisted the workflow and reporting.
