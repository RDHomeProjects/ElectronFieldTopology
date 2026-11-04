# Staged development plan

Updated: UTC 2026-11-04T01:00:23.956083+00:00; Australia/Melbourne 2026-11-04T12:00:23.956083+11:00.

This is the current roadmap, generated from [the project register](project/roadmap.json). Study state and scientific acceptance are separate. An assessed run can retain an open or blocked gate.

## Current priority

Administrative reconciliation is prepared in this change. After it is merged, the next scientific task is **s5-b-005: boost initialization and field registration**, using retained fields before another production matrix. PR54 recorded the completed diagnostics; it did not close general motion acceptance.

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

1. [s0-002: Repository layout and plan reconciliation](plans/s0/002-repository-governance.md) — Apply in a separate clone, review the documentation-only diff, then publish one administrative PR.
2. [s5-b-005: Boost initialization and field registration](plans/s5-b/005-boost-initialization.md) — Start with retained fields and independent analytical controls at exact nodes, shifted points and boundary extensions. Compare old and new variants; add phase-invariant, initial-state and comoving-residual comparisons.
3. [s5-b-006: Focused motion, mesh and domain convergence](plans/s5-b/006-focused-motion-convergence.md) — After the initializer decision, run a small beta=.3 x/z comparison before selecting third-h and larger-Q1-box controls. Preserve action, precision and predeclared gates.
4. [s5-b-007: Q17/Q19 motion comparison](plans/s5-b/007-higher-q-motion.md) — Proceed conditionally after adequate low-Q control with matched physical resolution, domain and observation-window checks.
5. [s5-a-004: Q18 fresh fine-start and conditioning follow-up](plans/s5-a/004-q18-fresh-starts.md) — Return after the low-Q/higher-Q dynamics tranche; predeclare independent starts, topology and energy comparisons.
6. [s5-a-005: Additional-Q controls](plans/s5-a/005-additional-q.md) — Select a bounded comparison after Q18 follow-up; do not start an unbounded catalogue.

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
