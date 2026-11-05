# ADR-0014: retain cubic as a candidate and separate convergence effects

UTC: 2026-11-05T04:12:28.812263+00:00; Australia/Melbourne: 2026-11-05T15:12:28.812263+11:00.

Status: adopt the next numerical workflow for maintainer review in PR58; scientific gate open.

## Evidence and decision

[The S5-B-006 assessment](../../reports/s5-b/006-focused-motion-convergence/assessments/20261105t041228z-a1c49633/ASSESSMENT.md) authenticates eight arms, 48 admissions and 24 milestones. Cubic improves common-reference and own-initial shape residuals in all 12 matched pairs, but all tail gates fail and some speed errors worsen. The 525 full-field files are retained in a [verified release catalog](../../data/archives/20261105t015855z-b7d90f43/README.md). This develops [ADR-0013](ADR-0013-conditional-cubic-initialization.md); it does not rewrite its earlier evidence or authorize general acceptance.

Retain cubic under explicit fixed-layer projection as the next convergence candidate. Keep the trilinear comparator and unchanged scientific limits. Complete assessment of the focused tranche; keep S5-B-006 assessed/open with convergence still outstanding.

## Ordered work

1. In new outputs distinguish old-baseline transport from method-specific raw/admitted diagnostics. Existing `raw_transport` in cubic rows contains the old trilinear baseline; preserve its original bytes and explain the label. Compare comoving fields on a fixed common region across times; separately refine diagnostic sampling.
2. First prepare a two-sentinel T=1 cubic temporal audit: Q1/x for the speed tradeoff, Q2/z for the best shape result, dt=.01/.005/.0025 with identical admitted n/v states and authenticated per-dt configuration. Reuse equivalent existing endpoints. Use full-state field/rate and centroid/stress comparisons; set acceptance tolerances before computation. Broaden only if indicated.
3. Then separate physical domain and mesh. A candidate matched-spacing domain pair is L16/n101 and L24/n151 at rest h=.16; readmit the larger-box rest field and record core/tail/stationarity changes plus a zero-speed control. A third fixed-L16 physical spacing can use n121 alongside authenticated n81/n101, with proper unequal-ratio analysis. These are proposed designs, not executed tests or acceptance thresholds.
4. Choose longer windows only after checking domain suitability. Revisit classical inertia and symmetry/quantization methods when their numerical sensitivity is bounded. Q17/Q19 motion, Q18 fresh starts/conditioning and additional Q remain downstream. Retain literature constraints on configuration-space quantization, justified coupling and detector models for later experiments.

## Alternatives and consequences

Immediate universal replacement of the old importer is not supported by the speed tradeoff. Discarding cubic would ignore consistent independent shape improvements. Another wide high-Q or long small-box matrix would mix unresolved initialization, boundary and discretization effects. A new damping, taper, fitted D4 rate or relaxed gate is not part of this decision.

This publication changes analysis and the current plan only. The action, solver, numerical arrays, configurations, historical reports and links are preserved. No physical model, quantum spectrum, emergent charge or electron is accepted. AI assisted the analysis; external scientific peer review has not occurred.
