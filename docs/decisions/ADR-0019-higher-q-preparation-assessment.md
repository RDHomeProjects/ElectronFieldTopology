# ADR-0019 — Assess coarse preparation and return to Q2 numerical controls

UTC: 2026-11-08T13:31:39.521682+00:00; Australia/Melbourne: 2026-11-09T00:31:39.521682+11:00.

Status: assessment decision for publication in existing PR62. Requirements NUM-001/002/003, BND-001, REL-002, SCI-003/004, REP-001/002.

## Evidence and decision

[The S5-B-007 assessment](../../reports/s5-b/007-higher-q-motion/assessments/20261108t133139z-d11d12c1/ASSESSMENT.md) independently authenticates all 79 full archive payloads and 23 NPZ files, replays three Q2 milestones and initial/final stationary fields, and preserves the native preparation outcomes. Q2 passes all seven original short-motion gates. Q17/Q19 complete four 50-iteration readmission calls each, but final relative force is11.38×/21.82× and maximum acceleration25.86×/22.20× the limits. No higher-Q motion or half-dt confirmation ran. Energy decreases, no native stall is reported, and the largest residuals are interior. These outcomes are unresolved preparation, not physical rejection or a demonstrated moving-knot instability.

Following ADR-0018's inexpensive-screen fallback, return primary work to **Q2 numerical controls and physical-mesh/domain convergence under S5-B-006**. Q1 corrective work remains parked, with the original 1.563660% speed failure intact. Use read-only centroid/initialization/stationarity controls before specifying the smallest fresh-readmitted Q2 physical-mesh and matched-spacing domain matrix. Do not automatically launch a long higher-Q run or unbounded preparation.

Keep S5-B-007 open for a conditional bounded stationary-only diagnosis: additional same-grid iterations versus a finer representation, original 129-source starts versus retained warm starts, and an explicit optimizer-cadence control if needed. Preserve the same action, source fields, scientific thresholds and native termination statuses. Both strict stationarity and boosted boundary reserves must pass before fresh higher-Q motion from t0, optional two-dt consistency, then detailed convergence. No scientific parameter change is authorized by this administrative/report patch.

## Alternatives and limits

- Longer same-grid readmission is cheap enough to test later and could reduce residuals; these 200 iterations neither prove convergence nor an irreducible coarse-grid floor.
- A finer grid may improve representation but costs more and does not itself make an old cell-functional endpoint stationary under D4. It needs fresh readmission and a source-start control.
- Increasing L alone has weak support here: the blocking residual is interior and rest tails are already below 0.1%; moving boundary admission remains untested.
- Ignoring stationary residuals, weakening gates or declaring higher-Q motion failed would conflate preparation and dynamics.

Earlier report paths/bytes, failed gates, all binary assets and configuration/source hashes are retained. Q18 fresh-start/conditioning, further-Q and later experimental/symmetry studies remain conditional. Q2 temporal evidence does not close spatial/domain or isolated-motion requirements. AI assisted analysis and reporting; this is a numerical planning decision, not external scientific peer review.
