# Staged development plan

Stages are evidence gates, not promised dates. S5-S7 are conditional research paths, not guaranteed outcomes. Do not run a broad search before validating the diagnostics.

## Current analytical milestone and requested Q follow-up

Run preparation update: 2026-11-01T15:07:15+00:00 UTC; 2026-11-02T02:07:15+11:00 Australia/Melbourne. The [Q18 neighbour run specification](plans/q18-neighbour-run.md) now implements this follow-up. [CPU seed admission](../reports/q18-neighbour-preparation-20261102/README.md) passed all six proposed initial fields. The next outputs must come from the separately checkpointed workstation campaign; no new relaxed research result is claimed by preparation.

Recorded: 2026-11-01T02:02:43+00:00 (UTC); 2026-11-01T13:02:43+11:00 (Australia/Melbourne). Following merged PR 48, the [charge-capable relativistic equation audit](../reports/charged-model-audit-20261101/README.md) is complete as an analytical tranche: finite energy and charge flux checked; general Maxwell equivalence and unrestricted causal evolution not established, with explicit counterexamples/degeneracies recorded. [ADR-0008](decisions/ADR-0008-charged-model-audit.md) defers charged dynamics and does not accept an electron model. The [source supplement](literature/charged-model-audit-sources.md) includes restricted vibration evidence and a normalization discrepancy.

**Next requested work: return to Q18 basin diagnosis and assess more Q values.** The [post-audit plan](plans/post-audit-q-assessment.md) prioritizes Q17/Q19 same-family controls, the retained Q22 control and optional Q20/Q24 extensions. Preserve the Q18 linked alternative and failed hyperbolic reproduction. This is a specific next scientific comparison, not a blanket catalogue; it does not wait for resolution of the charged theory. All outputs require UTC/Melbourne timestamps and resumable work without an arbitrary two-hour overall cap. Historical stage descriptions below remain historical; no new Q simulation has been performed in this audit.

| Stage | Deliverables | Exit gate |
|---|---|---|
| S0 Documentation foundation | Folder structure, purpose, hypotheses, requirements, AI workflow, literature, templates and documentation CI | Navigable documents, checks pass, no simulated results claimed |
| S1 Analytical benchmark | Locked Python package; verified Hopfion expressions; analytical sampling; field/energy visualisations and diagnostics | Equation map, independent checks, zero-flux behaviour and provenance |
| S2 Independent evolution | Validated evolution method; finite-domain flux accounting; manual experiment workflow | Agreement with analytical evolution and resolution/domain/time-step studies |
| S3 Relativity and stability | Consistent boosts; centre-of-energy tracking; perturbation studies; localisation vs knot persistence | Verified transformations and bounded claims with error estimates |
| S4 Topology exploration | Valid field families, discrete topology choices, continuous searches and rejection ledger | Reproducible search, controlled budgets and convergence of shortlisted candidates |
| S5 Extended dynamics feasibility | Literature-supported model specification, changed assumptions, equations/action and scale mechanism | Maintainer-reviewed rationale; viable constraints, causal behaviour and stability checks |
| S6 Interaction assessment | Candidate pairs/probes, stress/energy balance, force-law and orientation studies | Consistent long-range fields and interactions; fitted properties identified |
| S7 Quantum and experimental assessment | Spin/statistics analysis, precision/scattering comparison and distinguishing predictions | Qualified review and testable claims; experimental support remains separate |

## First implementation task: S1-A

S1-A is merged; see [the report](../reports/s1-a/README.md). S2 periodic-reference implementation and verification are merged via PR 4; see [S2 findings](../reports/s2/README.md). S3-A covariance is merged via PR 7; see [S3-A findings](../reports/s3-a/README.md). S3-B energy-centroid/localisation diagnostics are merged via PR 9; see [S3-B findings](../reports/s3-b/README.md). S3-C classified perturbations are merged via PR 11; see [S3-C findings and literature alignment](../reports/s3-c/README.md). S3-D instruments are merged via PR 13; see [S3-D helicity and selected closed-pair findings](../reports/s3-d/README.md). S4-A bounded candidate-family work is merged via PR 15; see [its graphical report](../reports/s4-a/README.md). The bounded S4-B instrument tranche is merged via PR 31 under [ADR-0005](decisions/ADR-0005-s4b-resumption.md), with [off-core tracing and independent polygon invariants](models/B0-S4B-Offcore.md). The wider literature review remains incomplete and level 4 deferred. Open-boundary isolation remains a separate requirement before long-time isolated experiments.

1. Verify a primary Hopfion formula and document conventions and normalisation.
2. Create pyproject.toml, dependency lock and importable package.
3. Evaluate E and B on a grid and at arbitrary points/times.
4. Test Maxwell residuals against an independent reference or derivation.
5. Produce electric flux, energy density, energy-flow and localisation outputs.
6. Save config, commit and environment provenance; run small PR checks.

Keep this task limited to analytical evaluation. Independently evolving fields belongs in S2.

## Stop and reassess rules

- A source-free charge result inconsistent with zero triggers numerical investigation.
- Boundary-dependent persistence does not pass a free-space confinement gate.
- If a theorem excludes the intended behaviour, record its assumptions and stop searching that class.
- A classical candidate with attractive J does not bypass S7.
- Poorly conditioned or unconverged results are inconclusive, not discoveries.
- Any changed physical theory receives its own model ID and decision before coding.

S4 may catalogue valid but unconfined knots. Progress to S5 is a decision based on constraints, not a reward for running more candidates.

## Pre-S3 literature checkpoint

[Assessment](literature/pre-s3-review.md) completed before S3 implementation. [ADR-0003](decisions/ADR-0003-pre-s3-literature.md) records the accepted scope refinement. The literature assessment itself introduced no numerical code. S3-A implementation and evidence are now available separately; S3-B/C are merged; S3-D instrumentation and selected closed-pair evidence are merged via PR 13. S4-A provides a bounded regular monomial catalogue and request ledger, with selected core traces and graphical reports; broader S4 search and arbitrary-line topology work remain pending.

| Substage | Purpose | Evidence gate |
|---|---|---|
| S3-A | Lorentz-transform the unbounded analytical field at consistent events | Conventions, inverse/composition, local invariants and Maxwell residuals |
| S3-B | Energy centroid, width and contained-energy diagnostics | Stress-energy relation and domain/tail convergence; distinguish peaks and centroids |
| S3-C | Bounded, classified perturbations | Constraint/null controls, linear difference-norm baseline, local redistribution and domain limits |
| S3-D / S4 | Helicity and topology instrumentation | Gauge/boundary/mean handling and validated tracing or invariants |

Use L11-L14 immediately, L15/L19 for topology diagnostic design, L16-L17 before nonlinear extension selection, and L18 before implementing open numerical boundaries. Existing L05 now has a 2026 journal version requiring version reconciliation before S4 construction work.

Global norm conservation or a persistent helicity value alone cannot satisfy a self-confinement/stability gate. No nonlinear binding term is selected merely by adding these references.

## Post-S4-B priority assessment

See [the direction assessment](post-s4b-direction.md). Recommend a bounded return-map/control-sensitivity follow-up (proposed S4-C) before broader sampling or more families, followed by a focused S5 model-feasibility decision for the particle objective. Preserve S4 as the Maxwell reference; more knot examples alone do not supply a binding or charge mechanism. This recommendation does not authorise a broad search, new dynamics, level 4, or progression to S6/S7.

## S4-C diagnosis and model-feasibility decision

The maintainer authorised [the bounded return-map diagnosis](models/B0-S4C-ReturnMap.md) followed by [ADR-0006](decisions/ADR-0006-model-feasibility.md). The candidate comparison is [equation-mapped](models/S5-feasibility-audit.md). The decision retains B0 as a reference, rejects the unchanged/null-preserving route as an electron-binding fix, conditionally advances only a small static-energy mechanism reference, and defers a charged internal-field solver. No extended dynamics are implemented; physical charge, causal/stability and quantum gates remain explicit.
