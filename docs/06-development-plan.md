# Staged development plan

Updated: UTC 2026-11-14T02:53:01.801788+00:00; Australia/Melbourne 2026-11-14T13:53:01.801788+11:00.

This is the current roadmap, generated from [the project register](project/roadmap.json). Study state and scientific acceptance are separate. An assessed run can retain an open or blocked gate.

## Current priority

Registered administrative activities are assessed. The next scientific task is **s2-004: Saved-state observer quadrature and alignment calibration**. Run the read-only calibration on the archived 35-state follow-up, then assess quadrature readiness and held-out observer prediction separately.

## Stage map

| Stage | Responsibility | Current scope |
|---|---|---|
| [S0](../reports/s0/INDEX.md) | Repository governance | Administrative foundation; no scientific acceptance implied. |
| [S1-A](../reports/s1-a/INDEX.md) | Analytical Maxwell benchmark | Bounded analytical instruments and recorded evidence. |
| [S2](../reports/s2/INDEX.md) | Independent Maxwell evolution | Periodic numerical reference; isolated-boundary claims remain limited. |
| [S3-A](../reports/s3-a/INDEX.md) | Lorentz covariance | Bounded common-event transformation controls. |
| [S3-B](../reports/s3-b/INDEX.md) | Centroid and localization | Energy distribution and finite-tail diagnostics. |
| [S3-C](../reports/s3-c/INDEX.md) | Classified perturbations | Controlled perturbation observations, not a full stability proof. |
| [S3-D](../reports/s3-d/INDEX.md) | Helicity and linking | Selected fibers and finite instruments, not a whole-topology certificate. |
| [S4-A](../reports/s4-a/INDEX.md) | Candidate catalogue | Bounded family admission and request ledger. |
| [S4-B](../reports/s4-b/INDEX.md) | Off-core topology | Bounded closure and polygon invariants. |
| [S4-C](../reports/s4-c/INDEX.md) | Return-map diagnosis | Bounded recurrence controls and model-feasibility decision. |
| [S5-A](../reports/s5-a/INDEX.md) | Static neutral-model references | Static benchmarks, Q22 and Q18/neighbour studies; reproduction limits retained. |
| [S5-B](../reports/s5-b/INDEX.md) | Neutral physical-time dynamics | Active dynamics track; general isolated-motion acceptance remains open. |
| [S5-C](../reports/s5-c/INDEX.md) | Charged-model feasibility | Analytical feasibility audit; charged dynamics deferred. |
| [S6](../reports/s6/INDEX.md) | Interactions and external probes | Conditional on suitable dynamics and justified coupling. |
| [S7](../reports/s7/INDEX.md) | Spin, quantum and experimental assessment | Conditional methods and apparatus tests; no electron acceptance. |

## Ordered work and dependencies

1. [s2-004: Saved-state observer quadrature and alignment calibration](plans/s2/004-saved-state-observer-calibration.md) — Run the read-only calibration on the archived 35-state follow-up, then assess quadrature readiness and held-out observer prediction separately.
2. [s5-b-011: Controlled dependency transfer to Q2 Q3 and other Q results](plans/s5-b/011-controlled-q-dependencies.md) — After Maxwell spacing assessment, qualify Q2 then measure one Q3 variable with fresh validation. Run the supplied Qx audit now without new SF evolution or altered gates.
3. [s5-b-010: Fresh Q3 Q4 Q7 survey and detailed motion](plans/s5-b/010-intermediate-q-survey.md) — Apply the separately registered controlled Q-dependency transfer; preserve all earlier preparation, admission and motion outcomes.
4. [s5-b-006: Focused motion, mesh and domain convergence](plans/s5-b/006-focused-motion-convergence.md) — Keep Q2 numerical/physical-mesh/domain controls available alongside the authorized S5-B-010 fresh-candidate survey. A failed short reference blocks that survey. Q1 correction stays parked; do not repeat completed temporal work without a diagnostic reason.
5. [s5-b-007: Q17/Q19 motion comparison](plans/s5-b/007-higher-q-motion.md) — Retain higher-Q endpoints for conditional stationary-only diagnosis after Q2 numerical controls: additional same-grid preparation versus finer readmission, with original-source and warm-start controls. Require strict stationarity and boosted boundary admission before fresh motion; no automatic expensive rerun. Q1 stays parked.
6. [s5-a-004: Q18 fresh fine-start and conditioning follow-up](plans/s5-a/004-q18-fresh-starts.md) — Return after the low-Q/higher-Q dynamics tranche; predeclare independent starts, topology and energy comparisons.
7. [s5-a-005: Additional-Q controls](plans/s5-a/005-additional-q.md) — Use the S5-B-010 assessment to select a bounded next set, including Q5/Q6 links or Q8 if informative. Preserve Q18 conditioning follow-up; do not start an unrestricted catalogue.

## Parallel and conditional work

Charged-theory feasibility may proceed analytically in parallel. Q1/Q2 symmetry and collective-coordinate methods require converged kinetic metrics; quantization assumptions are explicit, and are separate from a classical-emergence claim. External-field, Stern–Gerlach and wavefunction-observable tests require justified coupling, state preparation and detector models. Energy density is not automatically a Born position probability. Renderer profiles affect display data only.

## Stop and reassess rules

Preserve negative findings. Do not relax gates to obtain a pass. A missing input or integrity mismatch blocks dependent claims. Do not launch a new 60-case matrix automatically. Three diagnostic sampling grids do not constitute three physical solver resolutions. No arbitrary overall two-hour limit is imposed; use checkpointed, documented local work.

## Plan maintenance

Edit the register and the applicable study specification in the same PR as a scope or priority change. Run `python3 scripts/project_records.py render`, then `python3 scripts/project_records.py check`. Historical decisions stay in ADRs and immutable reports; do not prepend another competing current plan.

## Historical section links

[Exact pre-reconciliation document](history/layout-20261104/docs__06-development-plan.md.txt). The following anchors retain former section links; use the current roadmap above.

<a id="current-priority-diagnose-low-q-motion-before-new-production"></a>
<a id="current-gate-stationary-low-q-readmission-after-verified-wave-evolution"></a>
<a id="current-gate-physical-time-solver-after-assessed-admission"></a>
<a id="current-priority-neutral-physical-time-dynamics-admission"></a>
<a id="current-analytical-milestone-and-requested-q-follow-up"></a>
<a id="first-implementation-task-s1-a"></a>
<a id="pre-s3-literature-checkpoint"></a>
<a id="post-s4-b-priority-assessment"></a>
<a id="s4-c-diagnosis-and-model-feasibility-decision"></a>
