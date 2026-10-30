# Requirements and acceptance criteria

Status for every requirement is initially planned, except the S0 documentation items recorded in STATUS.md. Requirement presence is not acceptance evidence.

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

## Acceptance rules

Set tolerances from analytical accuracy, discretisation order and truncation studies before evaluating candidate physics. Document absolute and relative errors, including near-zero reference values. No universal magic tolerance is prescribed here.

A correct zero-charge result may satisfy SCI-002 while failing a proposed charge-emergence hypothesis. Scientific outcomes must not be conflated with test pass/fail.

Requirements may change through a documented decision with rationale and impact, never silently to suit an attractive result. Stage completion needs evidence links in STATUS.md.
