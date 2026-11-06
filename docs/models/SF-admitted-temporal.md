# S5-B-006: combined endpoint audit and admitted temporal refinement

Prepared UTC 2026-11-06T13:58:33.492062+00:00; Australia/Melbourne 2026-11-07T00:58:33.492062+11:00.

## Question, source and scope

Combine the small S5-B-009 endpoint/controller reporting audit and the next S5-B-006 temporal experiment in one unattended workstation workflow. Historical reports, native unresolved labels, thresholds and numerical kernels are immutable. The earlier eight-arm T3 findings remain authoritative. This new run is T1 temporal refinement of the selected cubic initializer; it does not rerun the old trilinear/cubic matrix or certify spatial/domain convergence.

The equations and conventions are those already verified in [SF physical time](SF-physical-time.md), [SF focused motion](SF-focused-motion.md), [SF relativistic](SF-relativistic.md) and the Jennings map in [SF-J2015](SF-J2015-static.md). Neutral unit-vector field, metric +---, c=1, dimensionless time/length/energy, CPU float64. The unchanged D4 nodal action and projected RK4 step are called; no electric coupling, damping, compression, shell penalty, taper or GPU-static functional is introduced. Preparation optimizer iterations are not physical time. Requirements NUM-001/002/003, BND-001, REL-002, REP-001/002 and SCI-003/004.

## Combined audit

Read the authenticated S5-B-009 compact records, separating four facts: strict measured final endpoint qualification; the preceding regularly sampled stable window; whether the final observation itself was regular; the historical regular-endpoint certificate. Keep the native stop label/reason. Good final residuals do not retroactively repair an unfulfilled sampling contract. For L22.08 this reports true/true/false/false; L20.16 fails strict endpoint qualification. No historical bytes are edited.

Independently exercise a closed-form uniform great-circle time solution (three time steps; measured fourth-order errors) and the existing thin-layer fixed-boundary/chain-rule controls before production. The new driver copies the old observer/IO bridge and calls the same numerical `step`; observer-on/off and old/new bridge tests must have bit-identical endpoints. A driver-side tail stop retains an accepted state; it does not alter an RK4 stage.

## Frozen production matrix

| Model/direction | First rest box | Fallback rest box | Rest spacing |
|---|---|---|---:|
| Q1, x | L24.32, n153 | L26.56, n167 | 0.16 |
| Q2, z | L20.16, n127 | L22.08, n139 | 0.16 |

Each selected domain runs beta=0.3 to T=1 at dt=0.01, 0.005, 0.0025 (100+200+400 steps). Six selected trajectories, 1400 accepted moving steps before any fallback. Longitudinal lab counts follow the existing gamma spacing rule: first Q1 161x153x153 and Q2 127x127x135, fixed side lengths as declared. This is an anisotropic fixed lab lattice with the established two held outer layers.

Warm starts: S5-B-009 Q1 n139/L22.08 (checkpoint f463a3975642593d8b36ecd984bf4f9fd5766aef5805154adc9017cce22f2255), and S5-B-008 Q2 n127/L20.16 (2172e56ee9357749ccfa5d30d42f319eede17158a15da39ceddd463686e0be0e). Both checkpoint and compact-publication digests are frozen in the new JSON configuration; source manifests/model/config/state hashes and exact constraints are authenticated. The handover reuses retained native fields or restores their verified Release roots automatically. No further local source dataset is assumed.

Extend each original field by exact centred north-vacuum copying, preserving h=.16, then freshly readmit using the unchanged projected Sobolev-CG optimizer. Even an unexpanded Q2 source is readmitted. Record initial and final fields separately; mere padding is not acceptance. Targets are the established S5-B-008 preparation values: force<=1e-4, max acceleration<=1e-3, Hopf quadrature within5%, positive corner cone and unit constraint<1e-10. Six completed 200-iteration batches are allocated per domain, checkpoint every25. Interrupted batches are not counted as completed. Existing Armijo/stagnation stops remain unresolved preparation outcomes. These are motion-preparation criteria, not a relabelling of S5-B-009's stricter settling certificate.

## Tail protection without changing the original criterion

Original measured outer shell: width2 model units, continuum diagnostic energy using the unchanged nodal predicate; fraction<=0.001 (0.1%). Keep absolute shell/total energy and the original flags. A pass is neither a reflection coefficient nor a complete isolation certificate.

Require before evolving a domain: projected cubic fixed-layer/constraint admission, initial width2 tail<=0.00075 (0.075%), initial width3 guard<=0.001 (0.1%), and projected known-coasting T1 reference width2 tail<=0.00075. Width3 is an extra reserve test, not a redefinition of the historical shell. A read-only native-source probe found Q1/L22.08 boosted tail0.0708512%, but width3 guard0.1314231%; this is why Q1 starts at L24.32. Q2/L20.16 gave 0.0274452% and 0.0591484%. The probe has not relaxed or evolved the proposed larger Q1 box.

Observe original width2 tail at identical physical times every0.05 for all dt. If it exceeds0.0009 (0.09%), stop at the accepted endpoint, preserve all checkpoints/metrics and reject this domain family for selection. An observed jump beyond0.001 is recorded as an original tail failure, never hidden. Then try the next declared box, freshly readmit and rerun all three dt from identical initial data. Never splice time-step results from different domains or shrink the analysis region. Initial admission rejection is also retained. If both declared boxes fail, report complete_admission_blocked_pending_review and retain any completed other model. There is no endless enlargement loop or guarantee between observations; avoiding failures is a measured engineering policy, not a promised scientific outcome.

Only the boundary reserve and hard numerical completion select a family. Other original shape, speed, momentum, energy, constraints and topology failures are still measured and retained, never tuned away. The original 1% shape gate remains explicitly a trilinear static-reference comparison. Additional projected-cubic/coasting and own-admitted fixed comoving-cube comparisons are separately labelled. No fitted centroid, rotation, speed or deformation hides error; the optional target-phase comparison is identified as such.

## Convergence, recovery and retention

Save full fields/rates at matching T=.25,.5,.75,1, plus admitted/latest/final checkpoints. Compute all three pairwise temporal differences on one fixed central 73-cubed lab-node region per selected family; field normalization is against reference minus north, rate against reference rate. Observed log2 error ratios are descriptive; differences<=1e-12 yield no reliable order. The separate own-admitted comoving cube has fixed rest side8, no shrinking mask. This is a temporal comparison on one finite grid, not a third physical mesh, domain convergence, persistent isolated motion, emergent spin/charge or electron result.

One Linux background worker, identity checked by PID/start/boot, heartbeats every30seconds. Atomic latest states and snapshots bind code/config/input hashes; stop requests retain accepted states, resume replays the same physical trajectory bit-exact where sealed checkpoints exist. Hard-kill recovery validates embedded model/config/code/constraints and CRC, without falsely calling an unsealed state externally hash-verified. Original rest preparation can reset conjugate-gradient memory on resume as before; stationary optimizer paths need not be bit-exact. Completed campaigns are immutable. Integrity errors stop rather than silently substituting inputs. All result, analysis, CSV and log metadata carry UTC and Australia/Melbourne timestamps.

Run without renderer exports to avoid IO overhead; full physics precision is unchanged. Renderer development remains separate. The first matrix is roughly16–24 hours on zbook by scaling prior n101/L16 timings to these larger grids and 1400 steps; preparation/load/diagnostics may add time. Fallbacks can extend into another day. No wall-time cap, forced idle work or automatic dt/precision reduction. Keep at least16GiB free; 32GiB or more is recommended with fallback and download-verification staging.

The handover installs only on main 4e4ff50657fa312a4e764a0ec53a42e422a183da, backs up local Git before additive application, stages a focused branch and runs validation. No native production trajectory is performed by the installer. New compact runs append under this study's `runs/<id>`; full run fields, snapshots and the runnable handover must be uploaded and independently download/hash verified by the unchanged workstation archive engine, with its catalog registered, before merge/cleanup. Nothing is deleted. Publication remains on the user's workstation. The wrapper retries only transient read-side HTTP5xx and permits a public fallback only for hash-pinned archive assets; uploads and scientific failures are never bypassed.

After assessment, choose physical mesh/domain tests and longer observation windows as evidence warrants. Keep conditional higher-Q Q17/Q19, fresh Q18 and additional-Q assessment, symmetry/spin and external apparatus milestones in their registered order. Literature/quantization ideas are not substituted for these numerical checks. AI-assisted implementation; software controls and read-only probes are not new candidate acceptance.
