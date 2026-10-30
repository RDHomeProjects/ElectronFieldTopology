# Literature assessment before S3

Review date: 2026-10-31 (Australia/Melbourne). S2 merged via [PR 4](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/4). No S3 implementation or new numerical experiment is included in this review.

## Recommendation

Proceed next with S3-A: event-consistent Lorentz transformations of the unbounded analytical solution, before extending periodic solver experiments. Split later work into centroid/localisation diagnostics and clearly classified perturbation tests. Do not start a broad topology scan or choose nonlinear binding dynamics yet.

The useful literature is not confined to proposed electron models. Methods, counterexamples and limitations matter at least as much as papers supporting the motivating idea.

## Search scope and evidence quality

Targeted public literature search covered covariant Bateman solutions; boosts and energy centroids; null-field topology and helicity; nonlinear electromagnetic knots; and open numerical boundaries. Both search engines were used, followed by primary publisher, arXiv and author records. Recent 2025/2026 publications were explicitly sought. Queries included:

- electromagnetic Hopfion Lorentz boosts energy localisation perturbation stability 2025 2026
- covariant Bateman construction complex conformal transformations
- linked knotted beams conservation helicity frozen field
- nonlinear electrodynamics null knots Born-Infeld
- stable electromagnetic structures Legendrian fields
- PML absorption electromagnetic waves Berenger

This is a scoped pre-stage assessment, not an exhaustive systematic review. Negative search coverage does not establish that a topic has no other papers. Nine new references L11-L19 are annotated in the [register](README.md), and existing L05 now has a verified 2026 journal publication. Papers were not copied into the repository. Review-depth and access limitations are explicit; no paper has been reproduced in full as part of this assessment.

## What should change in the plan

### 1. Relativity must act on spacetime events and full fields

L11 provides covariant Bateman definitions, conserved-quantity context and alternative Hopfion expressions. Use these as a cross-check rather than inventing transformations from a plot. The project inference is to evaluate inverse-mapped source events and transform fields/tensors consistently.

Proposed controls: identity; inverse boost; composition of collinear boosts; non-collinear test without assuming velocity addition is scalar; local Maxwell residuals; E dot B and E2-B2 invariants; comparison at common events. Declare passive/active convention, metric signature, tensor indices and c=1 choices first. A transformed constant-time slice samples different source times. A boosted periodic snapshot is not automatically an infinite-space solution.

### 2. Define the centre before measuring size or angular momentum

L13 and L14 motivate separate centroid definitions; L14's scalar approximation is not a substitute for a Maxwell derivation. Proposed project observables are energy centroid, energy-weighted covariance/width, and radii containing fixed energy fractions. Derive the stress-energy relation dR_energy/dt=P/U in our units under appropriate boundary assumptions.

For finite integrations report tail/domain corrections. A peak, geometric centre and energy centroid must not be silently interchanged. Evaluate angular momentum about a declared origin and about a declared centroid, retaining the extrinsic term. A centroid shift does not create intrinsic electron spin. Do not impose special paraxial coefficients on the Hopfion.

### 3. Separate several meanings of stability

Use distinct labels:

| Claim | Required evidence |
|---|---|
| Numerical stability | Convergence, constraint and conservation controls |
| Global norm stability of linear Maxwell fields | Difference-field energy balance with boundary terms |
| Null-family preservation | Both field invariants and appropriate null initial-data construction |
| Field-line topology persistence | Relevant theorem assumptions or explicit converged tracing/invariants |
| Energy confinement | Width/contained-energy diagnostics about a moving centre |
| Nonlinear particle-like stability | A separate model and analysis, not demonstrated by the preceding rows |

L12 supplies a counterexample to helicity-only topology inference; L15 clarifies the conditional use of stable topological structures. These do not establish robustness under arbitrary perturbations.

An additional project deduction follows directly from linearity: the difference between two source-free Maxwell solutions itself solves Maxwell's equations. With periodic boundaries, its integrated energy is conserved. Thus a non-growing global L2 difference is an expected linear control, not evidence of a restoring force or a self-bound particle. Perturbed energy may redistribute locally even while that norm stays fixed.

For S3-C compare two classes: perturbations generated within a known exact null family, and generic divergence-free perturbations which need not remain null. Measure both constraints and nullness. Keep numerical projection effects separate from physical perturbation amplitude. Do not label an untraced noisy field a preserved knot.

### 4. Add helicity only with appropriate gauge/boundary controls

L19 is a current September 2026 primary reference for conservation assumptions. Proposed implementation checks must state the potentials, normalisation, gauge, integration region and boundary terms. In a periodic box a periodic curl potential cannot represent a nonzero mean field: record zero modes and choose an explicit treatment rather than dropping them silently.

Do not require a complete helicity subsystem before S3-A. Helicity/topology instrumentation belongs in a separate S3-D/S4 task. A conserved helicity value will remain only one diagnostic, not a complete knot classifier.

### 5. Reassess nonlinear models before spending time implementing them

L16 and L17 show why an invariant-based nonlinear Lagrangian may leave a null Maxwell background unchanged. Project implication: increasing amplitude alone need not turn that exact background into a confined object. This does not exclude changed probe propagation, non-null configurations, derivative corrections or additional fields.

Before S5, substitute the intended background into proposed equations and identify the terms that actually survive. State the derivative/scale assumptions, well-posedness and weak-field limit. A change in probe behaviour is not a derivation of the background's charge. These papers do not validate an electromagnetic-only electron model.

### 6. Resolve isolated boundaries when the experiment needs them

L18 is an established absorbing-layer starting point, but its equations were not fully reviewed here. It supplies neither an implemented PML nor a direct modification of our global FFT solver. For S3-A use unbounded analytical evaluation. For short-time S3-C retain explicit domain studies; require an independently validated open-boundary implementation before interpreting long-time isolated persistence or escape.

### 7. Update and use the constructive-topology literature carefully

Existing L05 is published in Topology and its Applications 384 (May 2026), 109803. Its publisher abstract includes constructive advances and a limitation on indefinite containment for the field class considered. Journal/preprint details must be reconciled before coding S4; do not present the older preprint's candidate-construction wording as the final publication's complete result.

The [author's public research page](https://sites.google.com/view/benjaminbode/research) also links Mathematica materials for knot parametrisation/evolution. They are potential reference assets, not reviewed or licensed dependencies. Check relevance, version and reuse rights before importing any code. L15 offers another recent mathematical construction route, separate from our numerical perturbation analysis.

## Proposed next tasks

| Order | Task | Acceptance evidence before advancing |
|---|---|---|
| S3-A | Analytic Lorentz wrapper and independent controls | Event mapping, inverse/composition, invariants, residuals; finite-cutoff errors separated |
| S3-B | Energy centroid and localisation widths | Independent energy-momentum relation, increasing-domain convergence, peak vs centroid distinctions |
| S3-C | Bounded perturbation experiments | Reproducible perturbations, divergence/null controls, linear-norm baseline, finite-domain limits |
| S3-D / S4 | Helicity and topology instruments | Gauge/mean-mode handling, known link controls, tracing/closure/error criteria |

No new numerical tolerances are set by literature prose alone. Each implementation task must establish and justify its tolerances before its experiments. Review findings refine acceptance requirements; they do not retroactively change the S1/S2 measured results.

## What this review does not establish

It does not prove the electron hypothesis, identify a new charge mechanism, demonstrate a stable confined structure or certify an unimplemented diagnostic. It provides better source material and more discriminating tests for the next stage.
