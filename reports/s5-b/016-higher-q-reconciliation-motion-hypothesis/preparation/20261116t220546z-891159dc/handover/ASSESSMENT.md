# Higher-Q reconciliation and the role of motion in stability

UTC: 2026-11-16T22:05:46.045609+00:00; Australia/Melbourne: 2026-11-17T09:05:46.045609+11:00.

## Decision and scope

Proceed with the proposed reconciliation of Q22/Q18 before a new high-Q campaign. Preserve the merged Q2–Q16 closure and its original failed, unresolved and deferred outcomes. This tranche collects the relevant published records and numerical sources from a pinned local Git commit, compares them with retained admission evidence, and optionally evaluates a frozen-field internal-rotation balance on Q2/Q8. It takes zero relaxation and zero physical-time steps.

Motion must be split into uniform translation, internal/spatial rotation, and genuinely time-dependent localized states. The present evidence does not establish that motion is required for stability. It also does not justify using static stationarity as a universal exclusion rule for every possible time-dependent object.

| Hypothesis | Assessment now | What would determine it |
|---|---|---|
|Uniform translation stabilizes a truly unstable massive rest state|Not an intrinsic stabilization mechanism under Lorentz covariance|Compare the same perturbed solution in its rest and genuinely boosted frames at matched proper time.|
|Internal rotation selects a robust configuration that is absent at zero internal charge|A legitimate separate hypothesis in suitable models; unsupported by our present results|Use the correct fixed-charge or rotating-frame variational problem, verify radiation/localization and test perturbations.|
|A persistent periodic object exists despite failing zero-rate preparation|Not excluded by our static screen; no such object has been demonstrated|Identify actual periodic/relative-periodic balance and orbital stability under the declared equations.|
|The Q2–Q16 failures imply motion must be necessary|Unsupported|They are mostly unresolved numerical preparation or admission outcomes, not measured physical instability.|

No credible success percentage can be estimated from the current sparse, adaptively allocated and partly unresolved data.

## What the retained evidence already says

The final audit confirmed consistent static-gradient and kinetic-acceleration calculations on Q2 and Q8. Q8's final two50-step optimizer arms still did not meet joint static readiness. An optimizer trace is not physical time: oscillating force/acceleration during CG or L-BFGS is not evidence of a physical oscillation, rotation or unstable normal mode.

The older neutral-dynamics archive contains the following directly retained measurements. All35 manifested payloads and the archive CRC were checked in preparing this pack. These are legacy admission instruments and are not automatically current D4 readmission results.

| Retained legacy endpoint | Grid / spacing | Energy | Integrated stress / energy | Curvature information |
|---|---|---:|---:|---|
| q22-control | 129³ / 0.12 | 12.59137975 | 0.0222404 | Four positive trial directions; not a spectrum |
| q18-baseline-193 | 193³ / 0.08 | 10.90555105 | 0.0149946 | Four positive trial directions; not a spectrum |
| q18-baseline-domain | 193³ / 0.096 | 10.87843620 | 0.0056279 | Not measured in this endpoint |
| q18-ell025-193 | 193³ / 0.08 | 10.91089724 | 0.0199154 | Not measured in this endpoint |

These four positive curvature trials on Q22 and the fine Q18 baseline are useful controls. They do not exclude an untested negative Hessian direction, and they do not establish stability at a noncritical field. Nonzero stress and the changed stress ratio on the larger Q18 domain require source/mesh/domain reconciliation. The old report explicitly says physical-time evolution was pending. None of this establishes that the configurations physically collapse at rest or are rescued by motion.

The source collector therefore gathers the original Q22/Q18 studies, higher-Q motion and admission reports, observer/initialization controls, current model code, and available historical code at the old admission commit. Missing historical Git objects, local fields and size-limited binary members are reported as explicit deferrals. It does not silently replace an endpoint with a nearby seed or assert that an unavailable field failed physics.

## Uniform translation: why speed is not a repair for intrinsic instability

This conclusion is an inference from the Lorentz-covariant continuum action used for the neutral dynamics, not a new numerical result. For a localized solution with timelike total four-momentum, an inertial rest frame exists. A genuine boost maps the entire solution, including perturbations and initial rate, into another description of the same physical evolution. It cannot remove an instability of that solution.

For a perturbation growing as exp(σt′) in the rest frame, the soliton worldline has t′=t/γ in a frame moving at speed v. Its growth there is exp(σt/γ). A longer laboratory lifetime is time dilation, not restored stability. Any comparison must use matched proper time, equivalent perturbations and observables, and adequate contracted resolution. Published neutral-Hopfion scattering studies prepare minima and then boost them before evolving the fields [4].

On a finite mesh, a moving configuration can behave differently because of grid pinning, interpolation, anisotropy, boundary location or unequal effective resolution. Those are important numerical effects to measure. They are not evidence that the continuum rest instability disappears. Simply assigning a velocity to an uncontracted field changes the initial state and is not the required Lorentz comparison.

Internal circulation of energy at light speed also does not require a massive composite's energy centroid to move at light speed. Distinguish local electromagnetic nullness from the invariant of the integrated energy and momentum; pointwise null fields do not automatically imply null total four-momentum. First measure the latter before deciding whether a rest-frame comparison is meaningful.

## Internal motion: a separate state, with a model compatibility condition

Harland and collaborators construct internal rotations n(t,x)=R(ωt)ψ(x) using Fω=V−ω²Λ/2, or fixed-charge energy EJ=V+J²/(2Λ). Their action includes a potential with excitation mass μ; localized rotating minima have a restricted frequency range, with a radiation threshold at μ and a further model-dependent limit [2]. Battye and Haberichter report isospin-driven changes of shape and favored configurations in a massive model [3]. These support studying another constrained branch, not importing a rotating solution into a different action.

Our audited neutral action lacks a potential. Its vacuum linearization is a massless wave equation; harmonic perturbations have generic oscillatory Helmholtz tails rather than exponential localization. Inference: a sustained localized isorotating branch faces a radiation obstruction. Adding a potential would change the model. This does not exclude every exceptional periodic or spatially rotating state; published frequency limits cannot be copied into our units.

A genuine rotating or periodic state normally has nonzero acceleration. Therefore failure of a zero-rate acceleration test cannot, by itself, exclude it. The relevant equation residual is n̈−A(n,ṅ), with the appropriate constraint, boundary and radiation conditions. The original static gates remain mandatory for the static branch. A separate dynamic branch needs its own prespecified equation-balance and stability tests; an arbitrary velocity is not a waiver of the existing gates.

There is also a representation question for the overall project: a static neutral unit-vector texture need not mean that an underlying electromagnetic carrier or its internal energy flow would be static. That physical mapping has not been established here. Carrier-dependent stabilization in a fuller electromagnetic theory cannot be decided solely from failures of this surrogate's static optimizer; it needs declared field equations and observables connecting the two descriptions.

## How this handover builds on retained fields

The optional CPU diagnostic reads only the exact Q2 reference and Q8 native750 checkpoint identified by [ANCHORS.json](ANCHORS.json). It checks field/archive hashes, float64 geometry, original source/lock hashes and static metric replay first. It does not use unavailable old Q22/Q18 fields as newly admitted D4 states.

The diagnostic evaluates ṅ=ω(e3×n) and the expected ansatz acceleration n̈=ω²[e3×(e3×n)]. The axis preserves the north-vacuum boundary. For this action the acceleration is quadratic in the assigned rate at fixed n; evaluation at0, +0.01, −0.01 and +0.02 checks that dependence, rate-evenness and CPU/array parity. A bounded nonnegative least-squares fit in ω², capped atω=0.05, is then evaluated directly. These frequencies are diagnostic probe choices in model units, not existence thresholds or simulation commitments.

The output records RMS and peak equation residuals separately. A lower RMS with a worse peak must not be called improved admission. Evenness, quadratic prediction, sphere-acceleration constraints and the final residual replay are recorded. A clipped optimum or a nearly unidentifiable fit is explicit. No field is relaxed, rewritten, evolved or promoted to a stability pass.

This inexpensive probe asks whether a particular internal-rotation ansatz can balance part of the residual at a retained field. It does not determine a self-consistent radiation-free branch, infer physical frequency from optimizer iterations, or prove stability. A favorable result would motivate a model-compatible constrained construction; an unfavorable result rejects only this ansatz on these fields within the stated probe range.

## Tests that would establish stability more directly

1. **Separate equilibrium from stability.** First establish equation readiness for the branch being tested. Then study the constrained Hessian and physical kinetic metric. Near a genuine static critical point, a reproducible negative generalized mode Hξ=λMkinξ is evidence of linear instability; four positive trial directions are not a full spectral certificate. Recompute with the correct action and tangent/fixed constraints, distinguishing symmetry modes and discretization effects.
2. **Test translation in matched frames.** After a static control is properly admitted, use identical small physical perturbations at rest and after a genuine boost. Compare growth and localization at matched proper time, with temporal and domain/spacing controls. Initially keep the direction and perturbation fixed and vary speed only. A faster laboratory decay time comparison alone cannot decide intrinsic stability.
3. **Test an internal-charge branch explicitly.** Establish whether the chosen action admits localized radiation-compatible relative equilibria before assigning a nonzero internal rate. Optimize the appropriate constrained functional, allow deformation, and track conserved charge, size, radiation and perturbation growth. If a mass term is required, record that as a different theory and requalify its operators and thresholds.
4. **For a periodic candidate, test the orbit.** Use the dynamical equation residual, localization envelope, conserved quantities and a return map after quotienting translations/rotations. Compare perturbed and unperturbed trajectories at equal phase. A Floquet or return-map calculation can distinguish orbital stability from a long transient. A changing picture or conserved Hopf quadrature alone is insufficient.
5. **Use adaptive observations and bounded fits.** Keep one physical control variable changing at a time. Compare linear, low-order polynomial and exponential fits on measured windows with held-out prediction checks. Add samples near curvature changes, rapid residual growth or phase-fit disagreement. Separate observation cadence, timestep, spatial spacing and physical duration. Retain rejected fits, uncertainty, null results and deferrals; never turn an extrapolated crossing into a gate pass.

Electromagnetic topology-preserving evolution is already available as a different reference family [5]. For that branch, measure energy width, centroid transport, outward radiation and relevant fluxes along with field topology. It does not justify equating the neutral model's Hopf integer with electric charge or concluding that a coherent knot of field lines has bounded size or electron properties.

## Q22/Q18 reproduction contract

The paper now checked directly uses301³ points at spacing0.06 with fixed vacuum edges, and an energy-decreasing artificial kinetic relaxation; that relaxation is not full physical dynamics [1]. This is a major distinction from labeling our coarser retained endpoints as completed reproductions. Table1 reports Q22 cable C(3,2)^(2,3) at energy12.509 and a competing link at12.446; Q18's hyperbolic H4.851 at10.838 arises from a K(7,2) start [1]. These rounded values are reference markers, not acceptance tolerances for another discretization. Final curve identity must be measured rather than inherited from the seed name.

The [conditional pilot contract](PILOT.json) specifies two Q22 families, the retained Q2 instrument control, an initial50-step allocation per new arm, and at most four50-step batches per arm—400 accepted steps total if entry conditions and measured continuation rules support them. Grid/box and seed construction must be reconciled and frozen first; no hidden production defaults are supplied. Spatial resolution and domain comparisons remain separate, with original gates preserved and knot changes allowed. No pilot relaxation is executed by this pack.

Q18 is secondary. Reconcile its old scale/ellipticity and domain lineages and establish whether the relaxed curve ever matched the paper's hyperbolic case. Directly calling the inherited field “hyperbolic” or locking it to the initial torus knot would miss the intended experiment. Motion follows only after the appropriate branch's readiness and robustness conditions. A broad Q17–Q32 long campaign remains deferred until the small benchmark route demonstrates value.

## Execution and interpretation limits

The preparation and desk assessment can be published through the provided local-workstation commands. The subsequent collection is metadata/source work; optional frozen-field probes use the existing frozen Python environment and four CPU threads. No GPU is required for this tranche. Future CPU/GPU selection should use measured end-to-end cost, including diagnostics and I/O.

The complete old Q22/Q18 assessment packages were not available in the current saved-file set. The collector therefore obtains their published records from the workstation's existing Git objects rather than pretending to have read unseen results or downloading GitHub from this environment. The old admission archive and final Q2/Q8 audit are explicitly retained inputs. After the local run, return its single evidence.zip, which includes a pinned source inventory, explicit deferrals and any completed or blocked probe receipts.

This is AI-assisted analysis and tooling, not independent scientific peer review. Local field/source verification and any numerical probe have not been performed here on the full workstation fields. No percentage likelihood, new stable moving soliton, full-field backup or electron acceptance is claimed.
