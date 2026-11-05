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


## Physical-time reference and visualization separation

Recorded: 2026-11-02T12:37:39.053069+00:00 UTC; 2026-11-02T23:37:39.053069+11:00 Australia/Melbourne.

[The solver specification](models/SF-physical-time.md) and
[measured report](../reports/sf-time-renderer-20261102/README.md) add bounded numerical
SCI-001/004, MOD-001/002, NUM-001/002/003 and REP-001/002 evidence from actual time
integration, independent wave/manufactured references, flux refinement and constraints.
No stationary/high-Q full stability or open-boundary acceptance is implied. The
[renderer contract](offline-renderer.md) requires:

| ID | Requirement | Acceptance evidence |
|---|---|---|
| VIS-001 | Display/export configuration cannot change physics calculations | Identical float64 final states and diagnostics with exports on/off |
| VIS-002 | Support separate offline rendering and external interchange | Solver completion followed by authenticated NPZ replay and VTI/PVD files |
| VIS-003 | Configure frames, preview resolution, palette and camera | Basic/economy profiles and independent rerendering of the same data |
| VIS-004 | Identify simulation/model time and provenance | Frame overlays and UTC/Melbourne manifests; previews not scientific inputs |

The basic renderer supports these bounded controls; a diagnostic animation does not
close TOP-001/NUM-005 or any electron-model requirement.

## S5-B-005 retained-field reconstruction assessment

UTC: 2026-11-04T13:35:35.703463+00:00; Australia/Melbourne: 2026-11-05T00:35:35.703463+11:00.

[The immutable assessment](../reports/s5-b/005-boost-initialization/assessments/20261104t133535z-6a7e9b21/ASSESSMENT.md) supplies bounded NUM-001/003, REL-002, REP-001/002 and VIS-001 instrument evidence: authenticated compact results, independent interpolation/event controls, restricted field registration and preserved negative findings. It also records raw candidate fixed-layer failures relevant to BND-001. This does not close physical-mesh/domain convergence, isolated motion, inertia, quantum spin, charge or electron requirements. No existing threshold or earlier gate is changed. [ADR-0013](decisions/ADR-0013-conditional-cubic-initialization.md) requires boundary readmission before the focused S5-B-006 comparison.

## S5-B-006 focused motion assessment

UTC: 2026-11-05T04:12:28.812263+00:00; Australia/Melbourne: 2026-11-05T15:12:28.812263+11:00.

[The immutable assessment](../reports/s5-b/006-focused-motion-convergence/assessments/20261105t041228z-a1c49633/ASSESSMENT.md) records 48 admitted states, eight focused trajectories and 24 milestone evaluations. NUM-002/003, BND-001, REL-002 and REP-001/002 gain bounded evidence and retained failures: cubic improves shape in all 12 pairs, while every tail check fails and speed/momentum tradeoffs persist. Full fields are in a verified GitHub Release archive. This does not close temporal, physical-grid/domain, isolated-motion or quantum/electron requirements. [ADR-0014](decisions/ADR-0014-focused-motion-assessment.md) orders the remaining convergence work; all original thresholds and earlier records remain unchanged.

## S5-B-008 stationary tail-domain assessment

UTC: 2026-11-05T06:49:56.783673+00:00; Australia/Melbourne: 2026-11-05T17:49:56.783673+11:00.

[The immutable assessment](../reports/s5-b/008-tail-domain-screening/assessments/20261105t064956z-339196d8/ASSESSMENT.md) provides bounded NUM-002/003, BND-001 and REP-001/002 evidence from six stationary domain states, independent verification of74 archived files and replay of12 NPZ checkpoints. Q2 passes the original shell criterion at L17.92/L20.16; Q1 fails both. Inner-field domain sensitivity remains. This does not close physical-grid/time convergence or isolated-motion requirements. Original gates, earlier motion failures and quantum/electron limits remain unchanged. [ADR-0015](decisions/ADR-0015-stationary-tail-domain-assessment.md) records the remaining corrective-action plan.
