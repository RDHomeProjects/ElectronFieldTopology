# ADR-0013: conditional cubic initialization and fixed-layer readmission

UTC: 2026-11-04T13:35:35.703463+00:00; Australia/Melbourne: 2026-11-05T00:35:35.703463+11:00.

Status: adopt as a bounded next-method decision; scientific motion gate remains open.

## Context

[S5-B-005 assessment](../../reports/s5-b/005-boost-initialization/assessments/20261104t133535z-6a7e9b21/ASSESSMENT.md) verifies 30 retained cases. Cubic reconstruction lowers the analytic-rate/D4 mismatch in all 24 moving cases by 75.56–86.13%, but all 12 beta=.1 raw candidates violate fixed lab layers. Unit/tangency and smooth interpolation controls alone do not admit these data. The candidate has not been evolved.

## Decision

Keep the original action, solver and trilinear reference. Treat the cubic method as a conditional comparison candidate. In S5-B-006 first add thin-north-layer off-node lab-mask controls for beta=.1/.3 and x/z. Explicitly use the existing constrained state projection, or justify an alternative boundary-compatible reconstruction, and record every n/v correction, fixed-layer residual and free-node chain-rule check. Do not silently replace analytic rates by a D4 fit or taper the field.

After boundary readmission, prepare a focused beta=.3 x/z Q1/Q2 old-versus-cubic comparison, nominally eight arms at one fixed time-step/window, before selecting temporal refinements and a third physical mesh/larger matched-spacing domain. Record initial Hamiltonian, continuum observables, momentum, field/rate and boundary metrics. Preserve negative gates. A better reference fit alone is not improved evolution.

## Alternatives and limits

Immediate production replacement is rejected: the data have fixed-layer defects and no evolved candidate exists. Discarding the candidate is premature given its independent controls and consistent interior improvement. Another broad matrix is deferred until a focused comparison is assessed.

The original 60-case gates, source bytes, reports and thresholds remain unchanged. Q17/Q19 motion, Q18 fresh fine starts and further Q values keep their registered order. Spin/quantization and external-probe studies remain conditional on suitable numerics and justified physics. This decision changes numerical workflow, not the continuum action or physical assumptions. No electron acceptance follows. AI assisted the assessment; external peer review is not claimed.
