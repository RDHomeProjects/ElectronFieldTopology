# Registered Q21 numerical assessment protocol

## Scientific question

Determine whether the retained Q21 discrepancy is more responsive to conjugacy handling at fixed geometry, and measure what fine-region extent a later coupled coarse/fine discretization would need. These are separate questions. Energy concentration alone is not an error estimator, and a near-stationary finite-lattice field is not automatically a continuum solution, stable soliton or electron model.

## Completed evidence retained

The two final CPU branches each made 80 accepted updates from the same coarse parent, ending at native iteration 625. At 177³ and 193³ the core neighbourhood occupies about 2.82% and 2.87% of nodes but contains 99.29% and 99.54% of squared acceleration and 99.89% and 99.92% of squared force. Both fail the current stationarity gates. Whole-box averages and similar endpoint energies do not repair this. The 193³ acceleration peak needs interpretation alongside distributions and geometry. The full prior assessment and unchanged received evidence are included.

## Stage 1: read-only footprint mapping, implemented now

Authenticate the final endpoints, not their best snapshots. Replay their energy, force, acceleration, tail and guard measurements. Mark the n3<0 region together with maximum energy-density, angular-variation and residual hotspots. Grow its axis-aligned bounding box with physical buffers, measuring capture of total energy, angular variation and squared force/acceleration. Record face-adjacent band contributions, actual node fractions, bounds, native spacing and contact with the outer held layers.

Begin with buffers 0, 0.25, 0.5, 1, 2, 3, 4 and 6 model units. Add probes across steep capture changes and bisect the exploratory 99.9% joint-capture crossing to roughly a native cell. The resulting measured value is the candidate setting; it is not accepted solely from interpolation. No extrapolation beyond the measured buffer range is used. A region touching the outer held layers is not proposed as an interior refinement patch. A missing qualifying region is recorded, not replaced by an isolated cropped solve.

The two-to-one coarse exterior cell-count calculation is a geometry proxy only. It omits ghost layers, overlap, nesting, solver conditioning, topology evaluation, checkpoints and diagnostics. It is not a speedup prediction. A Q2 reference map is generated when its exact full-field file is available; otherwise its replay is explicitly deferred.

Footprint energy uses the native static Hamiltonian density and is checked to integrate to the minimizer objective. The inherited tail/guard metrics retain their original density convention. These densities differ on the finite lattice and must not be silently interchanged or used to rewrite prior gates.

## Stage 2: matched minimizer comparison, implemented now

Use the final 177³, length-30.72 checkpoint at native iteration 625. The exact arm inherits all n, old_g, old_z, direction, alpha and iteration values. The alternative clears conjugacy memory before and after each step. Both retain the same Sobolev shift 0.25, tangent projection, normalization, Armijo rule, alpha growth/capping, boundary layers and iteration-based restart policy. This isolates conjugacy handling. It does **not** compare unpreconditioned L2 descent or claim an exact Hietarinta–Salo implementation.

Before updates, replay the source and qualify the native energy gradient against centered constrained directional differences at three perturbation sizes. An independently implemented CPU/CUDA energy-gradient audit is required when using CUDA; CPU repeats are accurately labelled same-implementation checks. An audit failure stops the arm before further work.

Every accepted step receives the full original metric and gate evaluation. A representation or boundary failure stops allocation at the observed field and is retained. Passing every readiness gate stops the arm; it does not automatically start motion. The original thresholds remain force <=1e-4, maximum acceleration <=1e-3, relative approximate charge error <=0.05, positive corner cone, unit error <1e-10, tail <=0.00075 and guard <=0.001, with inherited physical shell widths. Neighbor angle remains a sampling diagnostic, not a newly invented admission gate.

Allocate 40 charged attempts per arm before the first progress decision. Then require at least 0.5% improvement in **both** force and maximum acceleration across the last ten accepted updates. A qualified joint fit can choose a next horizon of 5–20 attempts, bounded by predicted crossings or the 20-update forecast range. If measured progress qualifies but curve validation does not, use only five more attempts to obtain validation data. At a measured turning response shorten to five. Stop if recent joint progress is absent; record unresolved rather than infer physical rejection.

Fit linear, quadratic and exponential responses on the last up to 30 distinct observations. Reserve the final quarter, at least three points, as chronological holdout. Require relative RMSE <=0.25 and at least 10% skill against the last training value, for **both** response components. Require positive forecast values. Rank qualified models by their worst component error. Fits guide local allocation only, with maximum 120 attempts per arm and 3,200 optimization value-gradient calls per arm; no ceiling is enlarged by extrapolation. Each actual next batch remeasures the prediction. All model candidates, rejected fits, decisions and measured turning points are retained.

Compare common accepted-update coordinates, gradient-call counts and measured optimizer/diagnostic time. Method iterations are not universal work units. Native counter 625 does not mean 625 fine-grid updates. Keep best and final checkpoints distinct. A good energy-change number is not used instead of force or acceleration gates.

## Stage 3: fixed nested-grid qualification, registered but deferred

Implement a discrete composite-domain energy with one physical domain, consistent coarse/fine transfers, a single count of overlap energy and a gradient derived from that exact discrete energy. Reusing two separately cropped uniform-grid energies is insufficient. Boundary and transfer operators, physical volume weighting, unit-vector constraint, interface forces, topology diagnostics and the nonuniform preconditioner need independent qualification first.

Use analytic/manufactured checks and Q2 controls before applying the coupled method to Q21. Then freeze fine spacing and vary patch extent only, retaining an outer field that can respond. Demonstrate agreement with the uniform-grid reference and adequate interface residuals. Test resource cost and full analysis cost, not just cell counts. Failure of any qualification records a deferral and blocks Q21 composite evolution.

This package does not silently build or execute an unqualified composite operator. Its output supplies measured patch candidates, baseline controls and a qualified numerical-method comparison for that next development decision.

## Stage 4: adaptive zoom, registered but deferred

Only after stage 3 passes, keep a qualified patch extent fixed and vary fine spacing. Subsequently permit regridding between frozen-mesh measurement windows, with buffers large enough for deformations and topology changes. Exchange information both ways between outer and inner fields. Examine reference-grid or independently qualified whole-domain metrics so coarsening cannot create a false gate pass. Preserve old fields and transfer provenance. No isolated-crop stability or knot-identification claims are permitted.

## Resource and evidence decisions

Read-only mapping is CPU-only; both matched arms share one admitted backend. Auto explicitly falls back to CPU before launch if CUDA geometry does not fit. Do not migrate a branch after a failure. The 193³ field is mapped but receives no further relaxation in this campaign. Q4 domain comparisons, other Q sectors, physical-time evolution and bulk reanalysis remain outside this budget.

Atomic checkpoints and precharged attempt/call records prevent a restart from refunding work. The service is supervised and memory-limited. Preserve all native fields and their seals, including both final and best states. Compact evidence retains nested SHA256SUMS rather than excluding them recursively. All later publication occurs from the zbook, with repository checks and byte verification.
