# S5-B-007: staged coarse Q17/Q19 motion screen

UTC: 2026-11-08T01:48:14.439097+00:00; Australia/Melbourne: 2026-11-08T12:48:14.439097+11:00.

## Decision, question and unchanged model

The maintainer parked Q1 correction after merged PR61 (73bce2144de270cf21a077a30f5ae35709447301) and authorized exploratory Q17/Q19 motion before completing every Q2 physical-grid/domain check. [ADR-0018](../decisions/ADR-0018-coarse-higher-q-screen.md) records the ordering change. Q1's 1.563660% speed failure stays recorded. Q2 remains a bounded reference with outstanding spatial/domain work; a fresh short Q2 control precedes higher-Q preparation.

Question: do the retained Q17/Q19 branches justify a finer motion investigation, or does a short inexpensive screen expose a numerical/preparation/motion issue that should return priority to low-Q methods? A coarse failure is classified by stage; unresolved representation/preparation is not a physical rejection of a Q value.

Reuse [the existing neutral physical-time action](SF-physical-time.md), [relativistic conventions](SF-relativistic.md), [static source map](SF-J2015-static.md), cubic boost and unchanged projected Sobolev readmission. Metric+---, c=1, dimensionless physical time/length/energy, CPU float64, fixed two-layer north walls. Physical-time RK4, energy coefficients, source configurations and published records are unchanged. GPU static preparation is a different discretization; its stationary status cannot be imported as nodal D4 stationarity. No new field equation, coupling, damping, taper or energy rescaling is introduced.

## Authenticated inputs and small first matrix

| Arm | Original retained input | Rest grid for this screen | Motion |
|---|---|---|---|
| Q2/z control | Admitted D4 n127/L20.16 rest field from PR61 | Same 127³, h=0.16, L20.16; measured again |beta=0.3; dt=0.01; T=0.2 |
| Q17/z | Original129³/h=0.12 selected branch, pass0002 |97³, h=0.24, L23.04 |beta=0.3; dt=0.01; T=0.2 |
| Q19/z | Original129³/h=0.12 selected branch, pass0002 |97³, h=0.24, L23.04 |beta=0.3; dt=0.01; T=0.2 |

Q17/Q19 use exactly every second source node at unchanged physical coordinates, giving 65³ over the original L15.36. Centered north extension gives97³/L23.04. This reduces sampling density; it does not compress the physical knot. The original full129³ fields are retained alongside the coarse inputs. The moving lab grid uses the established gamma spacing rule:97×97×103 for higher Q and127×127×135 for Q2, same declared side lengths.

Read-only development probes of the authenticated higher-Q fields gave signed Hopf quadratures -16.784466/-18.772881 and positive minimum corner cones 0.797771/0.793132 at the coarse grid. Initial cubic/trilinear reference differences were 0.222575%/0.245004%, below the original 1% shape criterion. The initial force/acceleration residuals are substantial, so these fields are **not stationary D4 inputs yet**. Their zero padded shell is not evidence of a relaxed isolated solution. All production preparation and moving outcomes must be measured locally. Probe arrays were not relaxed or evolved by this preparation.

Input recovery is selective: the Git-anchored index and root manifest identify exact tar-member offsets and per-file SHA-256 values. The helper reads about 89 MB for both original higher-Q fields, plus the Q2 rest file, rather than restoring the 14.5 GB old workstation root. If the server ignores HTTP Range, it downloads and hashes only the necessary at-most 1 GiB part. Requested file sizes, hashes, model/Q/geometry, unit norms and held faces are checked before use. This verifies selected members, not a new verification of every historical archive file. Existing Release assets are read-only.

## Work allocation and early decisions

1. Run the small closed-form geodesic and fixed-layer/boost event controls. Recover/hash-check the three inputs. All source originals are copied into the new run for complete later archival.
2. Re-measure Q2 stationary admission, constraints and boundary reserves. Run its short control first. If it fails an applicable preparation or motion decision, complete the campaign as reference-blocked and skip higher-Q optimization and evolution.
3. For each higher-Q source, reject an unresolved coarse topology representation immediately. Otherwise allow at most **four 50-iteration readmission calls**, including interrupted calls. Targets stay force<=1e-4, maximum acceleration<=1e-3, Hopf magnitude within 5%, positive corner cone and unit error<1e-10. Native optimizer statuses/reasons, actual iteration/pass counts and partial work are retained. Budget exhaustion is preparation-unresolved. No endless stationary continuation, larger-box ladder or automatic spatial refinement is launched.
4. Before motion require successful cubic fixed-layer projection, original trilinear shape floor<=1%, initial width 2 tail<=0.075%, initial width 3 guard<=0.1%, and the projected known-coasting T=0.2 width 2 tail<=0.075%. Failed boundary admission is recorded and skips that trajectory. Limits do not change to get a pass.
5. Evolve in checkpointed segments ending T=0.05,0.1,0.2. At each endpoint evaluate all original shape, speed, energy, momentum, constraints, topology and tail gates. Stop on any failed criterion immediately, except that the first T=0.05 speed flag is recorded and becomes stop-eligible at T=0.1 to avoid making the decision from the shortest fit. The original speed flag remains false whenever measured false. At all times keep the original width 2 tail limit 0.1% and the earlier 0.09% safety stop. Tail is sampled every physical 0.01, identically across dt; it is not asserted continuously between samples.
6. Assess **both cheap higher-Q arms before any confirmation**. Only a full original-gate pass through T=0.2 receives a same-grid dt=0.005 rerun from the identical admitted field and rate. It has the same early stops. Compare full lab-grid field/rate at T=0.2 with predeclared consistency limits 1e-4/1e-3. Two dt values support a screening comparison, not a measured convergence order.

At most 140 moving RK4 steps are requested:20 for Q2,20+20 for initial Q17/Q19, and optional40+40 confirmations. Early failures reduce this. Readmission uses a declared finite work allocation for this coarse question; there is no overall two-hour or other wall-clock cap. Logs and heartbeats report genuine measured progress. Rendering and preview exports are disabled; all computational arrays remain float64.

Original case thresholds remain energy drift 0.1%, momentum/E0 drift 0.1%, shape 1%, speed 1%, shell 0.1%, Hopf magnitude error 5% with positive cone, and unit/tangency<1e-10. The shape gate remains the historical trilinear reference. A projected-cubic raw comparison is recorded separately. No fitted speed, rotation, translation, changing mask or phase correction manufactures a passing original gate. This screen does not repeat expensive curve classification or a Hessian/kinetic-metric study; retain arrays for those after selection.

## Retention, restart and finer follow-up

Keep original129³ inputs; coarse initial and readmitted rest states; manifests/optimizer history; admitted n/v; full accepted milestone snapshots; sealed latest/final states; diagnostics, stop reasons, controls, code/config/input hashes and the runnable handover. A completed run is immutable. Atomic recovery binds code/config/model/constraints and Linux PID/start/boot identity. An unsealed optimizer endpoint recovered after a hard kill is explicitly labelled embedded-metadata/CRC/constraint checked, not falsely described as externally hash-sealed. Interrupted optimizer calls consume one of the four allocations; native completed-pass counters are never forged.

`followup.json` records each candidate's original source, coarse rest and moving parent hashes, failures and a proposed finer ladder at fixed L23.04: h=0.192/n121, h=0.16/n145, h=0.12/n193, longer T1 and crossed x/z directions as warranted. These are future options, **not work silently queued by this handover**. A promising coarse rest can warm-start a finer rest field through declared cubic sampling and fresh D4 readmission; rerun the matched physical-time experiment from t0 at the new resolution. A coarse trajectory cannot simply be resumed on a finer mesh as the identical calculation. Include an original129-source-start control to expose inherited-basin effects, particularly in light of Q18. If coarse representation/preparation fails, retain the original129 source for a justified finer attempt instead of prolonging a failed coarse state.

A failed screen therefore leaves reusable evidence and a clear decision: return to Q2 numerical-method controls, extend preparation only through a new specified tranche, or test a finer representation. It does not erase the candidate or close the scientific question. Higher-resolution details, domain independence, longer motion, curve identification, and any symmetry/spin/probe interpretation retain separate checks.

Local artifacts stay under the one administrative checkout. Compact results, plans and source enter Git; full inputs/rest/trajectory fields and the handover enter a verified GitHub Release before cleanup. The publication helper supplies a human-readable release title, file guide, measured outcomes and reproduction/restore commands. It preserves every payload asset and all existing historical releases. Every report, scalar table, log and receipt carries UTC and Australia/Melbourne timestamps. AI assisted orchestration and preparation; production findings will be assessed after the local run.

## Runtime planning

PR61 measured Q2 dt=0.01 at 35.52 seconds per step on zbook. Scaling only by lab-node count gives about 15.8 seconds per higher-Q97³ step. This suggests roughly 22 minutes for all three initial trajectories, and another 21 minutes if both confirmations run, before additional IO/assessment and stationary preparation. Preparation and thermal behavior are uncertain. Allow approximately 1–4 hours for the complete screen, with early stops often finishing sooner; this is an estimate, not a time limit or a promised upper bound. Native status reports actual progress.

Requirements NUM-001/002/003, BND-001, REL-002, SCI-003/004 and REP-001/002. The sole roadmap register selects S5-B-007 exploratory screening now and retains S5-B-006 as the numerical fallback. Q18 fresh starts and additional-Q work remain registered. No earlier measurement or threshold is rewritten.
