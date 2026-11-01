# ADR-0008 — Charged-model audit and return to Q comparisons

Recorded: 2026-11-01T02:02:43+00:00 (UTC); 2026-11-01T13:02:43+11:00 (Australia/Melbourne). Status: analytical audit completed; recommendations recorded for maintainer review. This does not accept a new physical theory or authorize charged dynamics.

## Context

PR 48 closes the fresh Q22 assessment as a bounded finite-grid/diagram benchmark, not a charged particle or continuum stability result. [ADR-0007](ADR-0007-tightened-milestones.md) makes the next task an equation audit. The maintainer then explicitly requested a return to additional Q values after that audit, because the Q18 hyperbolic attempt produced a linked alternative. Preserve both findings.

## Disposition

The [audit and executable algebra](../../reports/charged-model-audit-20261101/README.md) reproduce the candidate's finite-energy m=3 profile and charge-to-flux normalization. The supplied e0 and r0 remain inputs. The literal electrodynamic map fails general Maxwell equivalence; the quartic theory has degenerate vacuum kinetics and a local derivative configuration with non-real characteristic frequencies. Restricted radial energy positivity is useful but not full stability. A factor-two discrepancy in the inspected vibration source is recorded explicitly.

1. Complete this analytical tranche without adopting a three-dimensional charged dynamics solver. Require a physical finite-core observable/probe map, justified electromagnetic sector, admissible constrained evolution sector and broader stability review before such a solver.
2. Keep B0 and the neutral static Skyrme–Faddeev reference as distinct instruments. Do not relabel Hopf degree as electric charge, fit r0 and call the mass predicted, or infer quantum spin/statistics.
3. **Return next to Q18 basin diagnosis and additional Q comparisons**, as requested. The [post-audit plan](../plans/post-audit-q-assessment.md) defines Q17/Q19 adjacent-family controls, Q22 regression control and optional source-grounded extensions. This refines ADR-0007 item 5 for a specified scientific question; it does not start a generic knot catalogue or require completion of charged dynamics first.
4. Retain every linked, changed-core, failed, budget-limited and inconclusive outcome. No arbitrary two-hour overall cap: use resumable checkpoints, per-pass controls and scientific stopping conditions, with timestamps on results and analysis.

## Consequences

No existing solver, boundary condition, physical coupling, dependency, threshold or CI workflow changes. The next numerical implementation must explicitly admit its new Q values; the current validator admits only 1, 2, 18 and 22. This plan is not a claim those extra cases have run. INT-001 and QNT-001 remain unreleased. GOV-002, SCI-003/004, MOD-001/002 and REP-001/002 receive analytical evidence, not completed physical acceptance. AI assisted the audit; primary sources are [version-mapped](../literature/charged-model-audit-sources.md).
