# S5-B-010 — Fresh Q3/Q4/Q7 preparation and detailed neutral motion

UTC: 2026-11-08T21:38:22.662797+00:00; Australia/Melbourne: 2026-11-09T08:38:22.662797+11:00.

## Question and ordering

Does a broader set of freshly generated intermediate-Q fields provide reproducibly prepared moving candidates, and which results survive changes in initial family, physical mesh, time step and finite box? This is the maintainer-authorized next tranche after merged PR62, base `8bf6cf4cd7d8b02eca141b306b5cbf959a4c78ed`. Q1 stays parked with its original1.563660% speed failure retained. Q17/Q19 preparation is unresolved, not a demonstrated motion failure. Q2 remains an authenticated short reference while its broader mesh/domain programme stays open. [ADR-0020](../decisions/ADR-0020-intermediate-q-survey.md) records the priority change; Q18 and further-Q work are preserved.

Model **SF-relativistic-neutral-v1**, scheme **D4-action-projected-RK4-v1**, metric+---, c=1, fixed K=(32π²√2)^−1, dimensionless length/time/energy, CPU float64. [The physical-time specification](SF-physical-time.md) fixes the action, positive fourth-order sigma term, mass matrix, constraints and reflecting two-layer north walls. Existing action, gradient, kinetic operator, Sobolev optimizer, Hermite reconstruction and RK4 step files remain byte-exact. There is no GPU D4 time backend; the older CUDA cell-functional optimizer is not substituted. No damping or rescaling of a computed solution is introduced. This model has no electromagnetic-charge observable or quantum-spin calculation.

## Equation and seed map

Primary construction: Sutcliffe, arXiv:0705.1468v1, Section3, Eqs.(3.1)–(3.4), with the low-Q discussion in Section2. The continuum energy is Eq.(2.1). [The source review](../literature/intermediate-q-candidates.md) records applicability and the different numerical methods used in the papers.

For r=|x|, define Z1=(x+iy)sin(f)/r and Z0=cos(f)+iz sin(f)/r. We choose the existing smooth compact profile f=2atan2(s,r), multiplied by1−10t³+15t⁴−6t⁵ with t=clip((r−0.7R)/(0.3R),0,1). At r=0 use the analytic limit sin(f)/r=2/s. This profile is our declared initialization, not an exact published soliton.

Use homogeneous p,q rather than dividing by q. The unit field is n=(2Re(p conjugate(q)),2Im(p conjugate(q)),|q|²−|p|²)/(|p|²+|q|²). Common unresolved zeros are rejected. Axial p=A Z1^a,q=Z0^b has |Q|=ab. The trefoil seed p=A Z1²Z0,q=Z1³+Z0² has |Q|=2·2+3·1=7. The established right-handed numerical Hopf convention measures these maps with negative sign; signed values are never rounded or relabelled as electric charge.

A global shear x→x−bend·exp[−(y²+z²)/s²] has determinant1. A small deterministic SO(3) target rotation breaks additional symmetry and vanishes in north vacuum; its three angle components are0.005(1−nz)[sin(0.7x+0.3y),sin(0.5y−0.4z),sin(0.3z+0.2x)]. Rodrigues' formula is used without normalizing a zero rotation axis. These are smooth initial-condition choices. Subsequent optimization is unconstrained by the ansatz or imposed symmetry.

| Seed ID | Initial family | a,b or exponents | Profile s | Support R | Bend | W amplitude |
|---|---|---|---:|---:|---:|---:|
|q3-axial|near-axial|3,1|2.8|8.8|0|1|
|q3-bent|sheared axial|3,1|2.8|8.8|0.65|1|
|q4-axial41|axial|4,1|3.2|8.8|0.2|1|
|q4-axial22|axial|2,2|3.2|8.8|0.2|1|
|q7-axial|axial|7,1|4.0|8.8|0.25|1|
|q7-trefoil|trefoil32|α2,β1|3.8|8.8|0.25|2|

The Q7 trefoil initialization amplitude/profile were selected using recorded read-only topology-resolution probes, not an energy fit. All trial probes are retained, including the underresolved first choice. A W amplitude changes the initial field, not the energy coefficients or physical scale of a computed endpoint. The Q3 starts are perturbations of one family, not claimed independent knot types. Q4/Q7 use different families. Seed labels never certify the final core configuration.

## Staged work matrix

Configuration: `experiments/configs/s5-b/010-intermediate-q-survey/study.json`. One process runs sequentially; no automatic CPU worker farm is started.

1. Run closed-form geodesic and fixed-layer/boost controls. Recover only the existing hash-pinned Q2 rest field using the established selective Release recovery. Copy the original into the new run and measure it without optimization. Run its existing beta0.3/z/dt0.01/T0.2 short reference. An unsuccessful Q2 preparation/admission/motion control blocks the candidate matrix and records the skips.
2. Generate **all six fresh seeds on97³/h0.24/L23.04**. Check positive cell continuity, unit constraint and signed Hopf magnitude within5% before optimization. Allow each rest problem at most **six calls of200 accepted-iteration capacity**, up to1200 iterations; actual native iteration/pass counts are retained separately. An interrupted call consumes allocation. Stop earlier on strict stationarity or native topology/stagnation/search failure. No optimizer error is rewritten as successful convergence. This is a declared work allocation, not an overall wall-time cap.
3. Give each strictly stationary seed a short beta0.3/z/dt0.01/T0.2 motion screen with original gates. All six coarse starts precede detailed refinement. If neither seed at a Q is stationary, permit exactly one declared **fresh121³/h0.192 retry** for each of that Q's two seeds. If both still fail, record preparation-unresolved and skip that Q's expensive matrix. There is no unbounded mesh ladder.
4. Select one seed per qualified Q. Prefer the stationary pool with successful boosted boundary admission; within the same mesh choose the lowest D4 energy, then seed ID as deterministic tie-breaker. Preserve both seed histories and motion outcomes. A coarse motion failure does not suppress spatial-refinement diagnosis. This ranking chooses work, not a global minimum or an electron candidate.
5. For the selected seed, prepare fixed-L23.04 grids **97³/h0.24,121³/h0.192,145³/h0.16**. At both finer levels independently prepare the original analytic seed and a cubic warm start from the preceding qualified mesh. Record both outcomes and raw full-field/energy differences; select the lower-energy strictly stationary endpoint on each mesh. Missing levels, route changes and basin ambiguities remain explicit. Equal Q or energy is not assumed to identify a basin.
6. On each qualified mesh, run a beta0 rest control toT0.2/dt0.01, and beta0.3/z toT0.5/dt0.01. At the finest qualified mesh, additionally run **dt0.02 and0.005 from identical admitted n/v**, giving three matched time steps; run a beta0.3/x/T0.2/dt0.01 orientation control. A qualified145³ fine parent also supplies the one matched-spacing **169³/h0.16/L26.88** exact north-extension/readmission and beta0.3/z/T0.5/dt0.01 domain comparison.

At most one detailed branch per Q is followed; a second coarse seed is not silently discarded or asserted equivalent. Fresh/warm states remain distinct. Any domain mitigation is a separate recorded case; it never turns an earlier rejected box into a pass. There can be up to22 distinct rest problems including the Q2 reference, and37 motion/admission records, before gate-dependent skips. These are maximum requested matrix counts, not promised completed cases. Q2 has no new optimization; up to21 fresh/warm/extension rest problems each have1200-iteration capacity.

## Boundary initialization, admission and motion decisions

Warm-start rest interpolation analytically normalizes the Hermite field, then explicitly sets the new grid's held two layers to north. The held-layer correction maximum is recorded in lineage; no free node is changed by this boundary projection. The original parent field is retained byte-exact. Different physical held-layer widths at different h are part of the finite-grid boundary closure and require domain comparisons. The projected new rest endpoint must independently pass all representation/stationarity checks; its continuity with a parent is not asserted from a label.

Strict rest targets remain relative tangent-force L2<=1e-4 and maximum physical acceleration<=1e-3, Hopf magnitude within5%, positive corner-cone margin and unit error<1e-10. A small energy change alone never admits motion. The unchanged optimizer's native termination criterion, restart memory reset at each200-iteration batch and messages are retained. Full histories/checkpoints permit a later separately specified continuation.

Before **each** moving/rest case: successful cubic fixed-layer/unit/tangency projection, original trilinear shape floor<=1%, width2 initial and predicted-coast endpoint tails<=0.075%, width3 guard<=0.1%. A failed admission is recorded with no time step. Original motion limits remain energy drift0.1%, momentum/E0 drift0.1%, shape1%, speed1% (or rest absolute speed0.001), topology5% with positive cone, tail0.1%, unit/tangency<1e-10. Additional cubic-reference error is recorded without replacing the historical shape criterion.

Screen endpoints areT0.1/0.2. Detailed endpoints areT0.1/0.2/0.5. Every original criterion is recorded at every endpoint; stop on a failure immediately except that moving-speed failure first becomes stop-eligible atT0.2. A rest-speed failure is immediately eligible. Width2 tail observations use physical cadence0.01 for short screens and0.02 for the three-dt detailed matrix; all time steps divide these cadences exactly. The existing0.09% observed-tail reserve stops before the original0.1% limit. This sampling is not a between-observation guarantee.

Full float64 snapshots occur every physical0.1 and at accepted segment ends. The same dt family starts from identical projected n/v, despite distinct dt-dependent configuration hashes. After any failure retain its last complete state, actual reached time, all original flags and native reason. No larger-box or finer-time result erases it. A first failure can stop a trajectory but does not stop independent seed/mesh diagnostics. An actual software/source/resource error stops the worker with a checkpointed error receipt for repair/resume.

## Detailed comparisons and topology diagnostics

Three-dt comparisons use complete, matchedT0.5 whole-lab-grid n/v arrays, exact shared initial-state hashes, relative field/rate differences and measured log2 orders. Earlier commonT0.1/T0.2 windows are retained if T0.5 is not reached, explicitly marked partial; missing endpoints never become full-window acceptance. Orders near the numerical floor can be unresolved. Case gates and convergence evidence remain separate.

Physical-mesh and domain trajectory comparisons use a fixed world-coordinate cube of side16 sampled on41³ analysis nodes: normalized Hermite field and raw cubic-interpolated field rate, no fitted shift/rotation or shrinking mask. This is explicitly a regional diagnostic, not a whole-domain error or automatic spatial order. Raw energies, centroid speed, tails and full fields are retained for independent assessment. The two different h ratios do not justify applying a uniform-ratio log2 formula. Fresh/warm rest comparison is full-grid raw field difference and energy difference; no phase or position fit manufactures agreement.

For each selected strictly stationary primary rest endpoint, extract piecewise-linear preimages at both fixed near-south targets. All closed components are retained with no joining or small-component deletion. Keep full polygons,128-node analysis polygons, three-projection Fox determinants and pair linking. Budget300000 candidate tetrahedra,40 crossings per determinant projection and16 components for combinatorial comparisons; larger outputs are retained with unresolved/budget statuses. Determinant3 is compatible with a trefoil but does not uniquely identify one. Unresolved adjacency/projection, changing components or mismatched targets remain evidence. The full moving fields support later independent curve analysis; anisotropic moving data are not incorrectly passed to the isotropic rest extractor.

## Recovery, offline display and retention

The local runner supplies preflight/start/status/stop/resume/foreground. Linux PID/start/namespace/boot identity prevents signaling an unrelated reused PID. Atomic checkpoints bind model, config, code, geometry, float64 constraints and actual native counters. Sealed SHA mismatches stop. A hard-kill recovery of an unsealed complete checkpoint is labelled embedded-metadata/CRC/constraint checked, never falsely claimed externally hash-sealed. Restored absolute attempt/snapshot provenance is read through a guarded record-ID-relative mapping without rewriting original JSON. A completed run is immutable.

Native artifacts use `artifacts/s5-b/010-intermediate-q-survey/<UTC-record-id>`. Full inputs, initial/latest/admitted/milestone/failed states, histories, source/lock/config hashes, environment, actual commands and runnable handover are retained. Compact evidence and tables enter canonical Git run folders. **The supplied ARCHIVE command uploads and download/hash-verifies the complete new run in descriptive Release assets before merge/cleanup**; no original data or old Release is deleted.

The solver's previews are disabled during calculation. `RUN.sh preview --case CASE_ID` separately reads authenticated retained snapshots after completion and creates a renderer-profile-controlled41³ Float32 NPZ/VTI/PVD series under a separate preview directory. Change display grid/arrays/palette independently; physics arrays, steps and diagnostics are unchanged. ParaView must use Volume rather than Outline to show energy density. Previews are rebuildable; the exact float64 source states and profile remain archived/versioned.

The optional `RUN.sh replay` command re-evaluates retained rest and motion fields and matched comparisons into a new separate folder, without optimization/evolution. `--case CASE_ID` limits field re-evaluation; the whole run seals are still audited. This reproduces the frozen instruments, rather than supplying an independent theory validation. No output is written into the immutable completed run.

Every report/result/CSV/log receipt carries UTC and Australia/Melbourne timestamps. Dependency lock and model kernels remain unchanged. Run preparation tests on the workstation before committing and starting. The small control report identifies host package versions separately from the locked production environment.

## Runtime and interpretation

This is a detailed conditional campaign, not another four-call high-Q screen. PR61 measured35.52 seconds per Q2 step on the127×127×135 lab grid; node-count scaling alone suggests roughly15.8/30.7/52.8 seconds for97/121/145 transverse grids, before thermal/memory and diagnostic differences. A169³ domain is more expensive. Preparation, core extraction and repeated field IO add substantial variable time. Plan for **roughly1–4 days if several candidates qualify**, with longer runs possible when many rest problems use their full allocation; early gate failures may finish in hours. This is a planning range, not a runtime cap or promised upper bound. Status and per-batch/per-segment receipts provide actual measured costs. At least60 GiB free initial headroom is required; leave more if retaining a full successful matrix and its temporary archive staging. A later<2 GiB guard stops safely instead of deleting fields.

Completion means all requested or skipped cells were recorded. It does not by itself close finite-box isolation, long-time stability, unique knot identification, electromagnetic charge or quantum/experimental requirements. Q1 stays parked; Q2 method work, Q17/Q19 follow-up, Q18 fresh starts and later Q5/Q6/Q8 studies remain in the sole register. AI assisted implementation/preparation; scientific findings await local execution and independent assessment.
