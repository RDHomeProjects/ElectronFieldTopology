# Requirements and acceptance criteria

S0/S1-A are complete. [S1-A evidence](../reports/s1-a/README.md) and [S2 periodic-evolution evidence](../reports/s2/README.md) map implementation to requirements. [S3-A covariance evidence](../reports/s3-a/README.md) is merged; [S3-B centroid/localisation evidence](../reports/s3-b/README.md) is merged. [S3-C classified-perturbation evidence](../reports/s3-c/README.md) is merged. [S3-D helicity and selected linking evidence](../reports/s3-d/README.md) is merged via PR 13. [S4-A bounded family and request-ledger evidence](../reports/s4-a/README.md) is merged via PR 15. This supplies SRCH-001 and SRCH-002 admission-ledger infrastructure; no optimiser or broad search has run. Open-boundary isolation, arbitrary-line topology persistence, broader candidate search and later-model requirements remain unimplemented. Requirement presence is not acceptance evidence.

| ID | Requirement | Acceptance evidence | Stage |
|---|---|---|---|
| GOV-001 | Maintain purpose, hypotheses, requirements, roadmap and literature | Navigable reviewed documentation | S0 |
| GOV-002 | Trace changes to requirements, sources and decisions | Issue/PR and report references | All |
| SCI-001 | Declare full fields, equations, sources, domain and boundaries | Completed model specification | S1+ |
| SCI-002 | Preserve source-free constraints in the baseline | Divergence residual and surface-flux convergence | S1-S2 |
| SCI-003 | Separate charge, topology, angular momentum and quantum spin | Distinct named diagnostics and explicit report limits | All |
| SCI-004 | Specify units, normalisation and relativistic conventions | Equation-to-code map and unit checks | S1 |
| SCI-005 | Reproduce an independently published analytical solution | Pointwise comparisons and numerical residuals | S1 |
| NUM-001 | Implement reusable numerical components outside notebooks | Importable package and automated tests | S1 |
| NUM-002 | Check energy/momentum balance including boundary flux | Closed or open-system balance tests as appropriate | S2 |
| NUM-003 | Demonstrate numerical convergence | At least three resolutions plus domain/time-step study where applicable | S2 |
| NUM-004 | Distinguish knot persistence from confinement | Topology evidence plus independent energy localisation curves | S1-S3 |
| NUM-005 | Assess perturbation sensitivity | Repeated controlled perturbation trials and convergence checks | S3 |
| REL-001 | Verify Lorentz transformations of a known solution | Field residuals, invariants and common-event comparisons | S3 |
| SRCH-001 | Generate constraint-compatible candidates by discrete family | Family definition, admissibility checks and parameters | S4 |
| SRCH-002 | Search transparently and retain rejected candidates | Seed, bounds, budget, metrics and rejection ledger | S4 |
| MOD-001 | Justify any non-Maxwell dynamics before implementation | Model specification and maintainer decision record | S5 |
| INT-001 | Measure interactions without supplying the desired charge law | Separation/orientation study, stress/energy balance and uncertainty | S6 |
| QNT-001 | Assess spin/statistics beyond classical circulation | Explicit quantum analysis and qualified scientific review | S7 |
| REP-001 | Make runs reproducible from immutable provenance | Commit, config hash, environment, hardware, seeds, commands and artifacts | S1+ |
| REP-002 | Preserve null, negative and inconclusive findings | Versioned report with applicability and uncertainty | All |
| SW-001 | Lock numerical dependencies and document local setup | pyproject.toml, lockfile and clean-environment run | S1 |
| CI-001 | Check documentation in GitHub Actions | Passing local checker and hosted workflow | S0 |
| CI-002 | Run small benchmark tests on PRs | CI results tied to commit | S1 |
| CI-003 | Offer bounded manually dispatched experiments | Validated inputs, timeout, artifacts and job summary | S2 |
| LIC-001 | Mark software/documentation licensing and third-party terms | LICENSE, documentation notice and source notices | S0+ |

## Pre-S3 review additions and implementation status

These refine acceptance in response to [the literature assessment](literature/pre-s3-review.md). REL-001/002 and the analytical unbounded part of BND-001 have merged [S3-A evidence](../reports/s3-a/README.md). REL-003 and the energy-localisation part of NUM-004 have merged [S3-B evidence](../reports/s3-b/README.md). NUM-005/006 have merged bounded [S3-C evidence](../reports/s3-c/README.md); this is not an isolated long-time stability theorem. TOP-001 has [S3-D instrument and selected closed-pair evidence](../reports/s3-d/README.md) merged via PR 13, with whole-fibration/perturbed persistence unverified. Bounded S4-B now adds [off-core closure/budget/zero outcomes and independent polygon invariants](../reports/s4-b/README.md); this does not certify continuum isotopy or complete knot identification. MOD-002 remains pending. S3-A does not complete open numerical boundary validation or the full S3 stage.

| ID | Requirement | Acceptance evidence | Stage |
|---|---|---|---|
| REL-002 | Transform spacetime events and full fields consistently | Declared conventions; common-event, inverse/composition, Maxwell and invariant checks | S3-A |
| REL-003 | Distinguish energy centroid, peak and origin-dependent angular momentum | Stress-energy derivation, tail convergence and independent centroid/width checks | S3-B |
| NUM-006 | Classify perturbations by constraints and null-family membership | Divergence and both null invariants; conserved difference-energy baseline; local redistribution | S3-C |
| TOP-001 | Avoid helicity-only topology claims | Gauge/boundary/mean-mode treatment plus explicit tracing or theorem assumptions | S3-D/S4 |
| MOD-002 | Check whether nonlinear terms alter the selected background | Substitution into stated equations, surviving terms, scale and well-posedness assumptions | S5 |
| BND-001 | Establish boundary suitability for the claimed experiment | Analytical unbounded evaluation or quantified finite-domain limits; open-boundary reflection/loss tests before isolated long-time claims | S3+ |

## Acceptance rules

Set tolerances from analytical accuracy, discretisation order and truncation studies before evaluating candidate physics. Document absolute and relative errors, including near-zero reference values. No universal magic tolerance is prescribed here.

A correct zero-charge result may satisfy SCI-002 while failing a proposed charge-emergence hypothesis. Scientific outcomes must not be conflated with test pass/fail.

Requirements may change through a documented decision with rationale and impact, never silently to suit an attractive result. Stage completion needs evidence links in STATUS.md.

## Bounded S4-B evidence scope

See [the model/source map](models/B0-S4B-Offcore.md) and [measured report](../reports/s4-b/README.md). TOP-001 gains explicit off-core tracing, zero guards, closure/refinement statuses and independent polygon determinant/link checks. NUM-003 gains three polygon invariant resolutions, three spatial-difference steps and two trace tolerance/step/budget levels; the existing S4-A Gauss refinement remains separate. This is bounded evidence, not a complete domain/refinement proof for arbitrary curves. SRCH-001/002 retain four fixed families and every outcome, without optimisation or a new generator. REP-001/002 are supported by configuration, source/dependency hashes and retained outputs. No S5–S7 or comprehensive literature-review completion is claimed.

## Bounded S4-C and feasibility decision

[The return-map specification](models/B0-S4C-ReturnMap.md) adds actual section positions and independently varied length, tolerance, step, nodal and observation controls (TOP-001, NUM-003). Manufactured periodic/irrational torus targets validate the instrument without assigning Maxwell rotation numbers. [The equation audit](models/S5-feasibility-audit.md) and [ADR-0006](decisions/ADR-0006-model-feasibility.md) provide MOD-001/002 feasibility dispositions, not an implemented extension or completed physical-model acceptance. Fixed configuration, source hashes, explicit resource-limited cases and clean measured outputs support SCI-003/004/005 and REP-001/002.
