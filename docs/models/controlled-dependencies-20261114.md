# Controlled dependency publication and transfer contract

Prepared with AI assistance. Code: Apache-2.0; original prose/figures: CC BY 4.0. Software controls and publication do not constitute independent scientific peer review.

## Measured baseline and interpretation

The bounded Maxwell run `20261113t153443z-5d0f27e4` at source commit `50a1337739f5063bfb459c8d7111077b9ccffd33` completed 61 cases. Five frozen empirical models passed their withheld prediction checks; periodic numerical controls passed. Hopfion-duration refinement remained open because its tracked feature bracket was 3.646% of the tested span against 3%, despite a satisfactory last prediction residual. Source evidence SHA-256 is `bff7958ed749a887b334a2e2c4d3d5a03f7cb27e1341ab144f4760e1780c5b51`.

The exact earlier 33/49/65 Maxwell study is retained as coupled h/dt refinement, not an independent spatial-order determination. The host time-step/adaptive pilots are explicitly preparation on the assistant host. Earlier Q3 observation, initial-field, initialization and sampling/boundary evidence retains its own read-only scope and original outcomes. No absent method-alignment or Qx trajectory is called executed.

The baseline's primitive Yee `derivative`, `curl` and `points` functions are retained. Source-free Maxwell equations, c=epsilon0=mu0=1, real float64 fields and their existing evaluator/PSATD sign conventions follow the registered source specifications [B0-H11](B0-H11.md) and [B0-H11-PSATD](B0-H11-PSATD.md). No potential or spacetime tensor is evolved. The numerical source files are SHA-256 checked, not inferred from a commit label alone. Native E lies on cell edges at n*dt, B on cell faces at (n-1/2)*dt. Update:

    B_plus = B_half - dt*curl_forward(E)
    E_next = E + dt*curl_backward(B_plus)

The Hopfion retains analytically driven two-layer boundaries and an interior observation region; it is not an isolated outer-boundary evolution. The eight-mode periodic packet retains transverse analytical initial data with no hidden projection. Packet cubic rotations remain narrow axis-permutation controls, not arbitrary rotational isotropy. The original half-step analytical startup depends on dt and remains qualified. Native divergence preservation, an initially nonzero divergence residual, the periodic leapfrog modified invariant, synchronized physical energy and Poynting quadrature are separate diagnostics. Their equations and source maps remain in the preserved baseline archive.

## Corrected feature classification

Derivative roots are clustered within a scale-relative distance to avoid treating numerical splits of a repeated root as separate extrema. A turning point requires the first derivative to change sign across the cluster above a numerical floor. A stationary inflection of x³ must therefore be labelled a possible inflection and must not be called a turning point. Inflection targets require a change in the second derivative or adjacent divided-difference curvature. Nonuniform divided differences use the mean of each supporting triplet as their approximate location. No algebraic root or finite bracket certifies an exact physical inflection.

Qualification retains independent discrete travelling-wave, Fourier finite-mode, central-difference Maxwell, quadratic acquisition and inflection tests and adds explicit rejection of false extrema at a stationary inflection. Published measurement files are not rewritten by correcting labels in future code.

## Localized duration continuation

Keep the old N=65, box side 8, dt=1/240, phase zero, unrotated Hopfion, startup and driven-boundary prescription. Previously reviewed development and validation values now form development context. Reserve new validation counts 133, 139 and 145 before adaptation; T=count/240. Allow at most three sequential adaptive additions from counts 130–146, excluding prior and reserved levels, concentrating near the unresolved curvature feature. This does not repeat the whole duration sweep. The response remains the synchronized native relative field L2 used by the old duration study, so it is not mixed with the new spatial observer response. The earlier tolerance values remain unchanged.

## Isolated physical spacing study

The only independent numerical variable in each spatial block is h=8/N for odd N=49–129. Seed grids are 49,65,97,129; reserved validation grids are 57,81,113. Hopfion has at most nine adaptive additions, periodic packet six, retaining the prior 50% increase for Hopfion. Fix box side 8, T=1, dt=1/960, phase zero, orientation zero, mode/field scale, startup prescription and boundary rule. The original verified N65/T1/dt1/960 fields may be reused with a source receipt and exact field hash/CRC check; reused arrays are copied to the new run, not altered in place. No precision/grid/backend reduction occurs on a resource failure.

Use one common physical observation cube [-2,2]^3 with 33 nodes on each axis. Every Yee component is mapped from its actual native location to these points by componentwise linear interpolation. Nodal tensor trapezoidal weights provide one fixed quadrature. Temporary B_plus is generated at T+dt/2, with its prescribed guard values for Hopfion, and B_sync=(B_half+B_plus)/2 is formed without modifying native E/B_half.

Let I_h be this observer, F_h the synchronized numerical native fields, F_exact,h the exact fields sampled at their corresponding native locations and T, and F_exact,obs the exact fields on the fixed observer. Define vector differences:

    total         = I_h(F_h) - F_exact,obs
    evolution     = I_h(F_h) - I_h(F_exact,h)
    interpolation = I_h(F_exact,h) - F_exact,obs
    total         = evolution + interpolation

Use the same exact-observer L2 denominator and quadrature for all three. The squared total includes the explicit cross term 2<evolution,interpolation>. Scalar norms are not subtracted or added to fabricate a decomposition. The primary spatial response is `evolution_observed_error`; interpolation baseline, total observed error, cross term, native errors and vector-identity closure are separate recorded values. The observer is a numerical instrument, not a new electromagnetic equation.

At the coarse/fine anchors, refine observer nodes to 49 and 65 using the same saved physical state. Separately repeat physical evolution at dt=1/480 with grid, boundary and observer fixed to check temporal subordination. These are separate controls, not additional free variables inside the fitted spacing curve. Native cube flux regions can move with h and remain auxiliary; they are not the primary spatial comparison.

The complete extension is bounded by 39 case configurations: at most six new duration points, 29 spatial configurations and four time-anchor configurations, with exact N65 cases reusable. There is no arbitrary two-hour wall cap. Full float64 states, hashes, NPZ CRCs, code/config, actual source commit/locks, environment and UTC/Melbourne times are recorded. Full arrays stay local and are excluded from compact evidence until separately archived.

## Fits and validation

Compare constant, linear, quadratic, exponential and, after sufficient development data, cubic models using development leave-one-out residuals. For spacing also compare an offset power law a+b*(h/h_scale)^p, with an explicitly bounded exploratory p in [0.2,6]. Its presence is a candidate numerical model, not a preaccepted order. Record scaled coefficients and units. Early stopping uses the predeclared new-point residual (1e-6 in fractional response), feature bracket (3% of tested span), two successive qualifying rounds and minimum two additions. A maximum budget is recorded as exhausted if those conditions have not passed. Fresh validation maximum error uses 5e-6; it does not replace a physical field-error budget.

Acquisition changes point placement, not other case controls. Choices are recorded before measurement. Models are frozen before new validation, and validation does not choose a replacement primary model. Old inspected withheld points are development data for an updated model. A new accuracy/cost objective remains undeclared, so no optimal mesh or operating point is selected automatically. No extrapolation beyond the tested interval or physical-model claim is licensed by a fitted polynomial.

## Application to Qx evidence

The executable Qx audit applies the dependency rules to the existing S5-B-010 Q2/Q3/Q4/Q7 compact campaign. It matches initial state hash, rest identity, physical mesh/box, velocity, direction, endpoint, boundary and model-time diagnostic cadence. Original failed trajectories are retained; rejected admissions do not enter motion fits. Different fresh/warm stationary states are not pooled as a clean one-variable mesh response. Existing three-level Q3 temporal data remain descriptive because they have been inspected and lack fresh reserved validation. The audit produces an explicit missing-measurement ledger rather than a manufactured validated fit.

New SF dynamics do not launch automatically from a Maxwell check. Following the spatial assessment, qualify the Q2 reference, then prepare one Q3 variable with an unchanged rest representation, physical observer and original gates. Q4/Q7 need original preparation/admission gates first; Q1 remains parked. Maxwell and neutral SF actions are different equations, and their errors/acceptance criteria are not interchanged. This staged transfer is part of the registered roadmap, with unresolved conditions preserved.

## Publication and preservation

All GitHub operations occur only when this handover is executed on the workstation. The scoped archive verifies the 61 local states and compact payloads, creates split full-run TAR assets, downloads them and verifies every member before publishing its release and committing a catalog. Original fields are not deleted. The installer uses an isolated clone, complete-history bundle backup, additive canonical records, existing layout validators and dynamically allocated study numbers from the actual current registry. It references already-present byte-identical evidence rather than rewriting old reports. New record-scoped Git attributes treat rendered HTML/SVG as assets in diffs, preserving their original path-data whitespace and hashes; Python, documentation, record and payload checks still run normally. Generated navigation is rendered from the register. The measured assessment is published before the follow-up begins; new production status is never inferred from a preparation test or a merge.
