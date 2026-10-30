# Staged development plan

Stages are evidence gates, not promised dates. S5-S7 are conditional research paths, not guaranteed outcomes. Do not run a broad search before validating the diagnostics.

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

S1-A is merged; see [the report](../reports/s1-a/README.md). S2 periodic-reference implementation and verification are complete pending review; see [S2 findings](../reports/s2/README.md). S3 is next. Open-boundary isolation remains a separate requirement before long-time isolated experiments.

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
