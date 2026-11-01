# Post-audit Q18 diagnosis and additional Q assessment

Recorded: 2026-11-01T02:02:43+00:00 (UTC); 2026-11-01T13:02:43+11:00 (Australia/Melbourne). Status: explicit next-work plan requested by the maintainer; no new Q computation has run. This follows the [charged-model audit](../../reports/charged-model-audit-20261101/README.md) and [ADR-0008](../decisions/ADR-0008-charged-model-audit.md).

## Question and preserved baseline

Why did the Q18 K(7,2) attempt enter a three-component linked basin instead of the source's hyperbolic local minimum? Is this behavior sensitive to seed profile, minimization controls, discretization or domain, and how does it compare with neighboring Q values built from the same knot-family denominator?

Keep the measured Q18 linked outcome and failed hyperbolic reproduction as evidence. The fresh Q22 bounded benchmark is a control, not proof that every other Q pipeline or basin is correct. A core preimage may reconnect while full-field Hopf degree is retained. A link is a possible valid outcome, not a reason to force a target knot or adjust coefficients.

## Initial comparison matrix

Published labels and rounded energies below come from Jennings 1412.8597v2 Table 1 (existing L36), with the existing static normalization. They describe selected local outcomes, not global minima or mandatory targets.

| Q | Source seed/outcome | Source E | Purpose in our next study |
|---:|---|---:|---|
| 17 | K(7,2) to K(7,2) | 10.952 | Lower adjacent-Q control with the same denominator family |
| 18 | K(7,2) to H4.851 / 10_139 | 10.838 | Central basin-reproduction question; retain our linked alternative |
| 19 | K(7,2) to K(7,2) | 12.008 | Upper adjacent-Q same-family control; also source has lower-energy other seeds |
| 22 | Cable and linked comparator | 12.509 / 12.446 | Existing checkpoint/diagnostic regression control, reuse before recomputing |

For the existing monomial K(7,2) family, the algebraic degree rule is $Q=2\alpha+7\beta$. Candidate exponents are (5,1), (2,2), (6,1) for Q17, Q18, Q19 respectively. This is a seed proposal requiring admission checks, not proof that a discretized field has the declared Hopf degree or a prescribed final topology. Hold the family denominator, conventions and radial profile definition fixed when comparing Q. Full-field charge and geometry must be measured independently.

An optional second tranche can add Q20 (source K(7,2) branch at E=12.517 and a cable-seeded linked branch at E=11.753) and Q24 (source two-trefoil linked outcome at E=13.282). Confirm each exact source construction/charge before implementation. These distinguish reconnection/branch behavior; they are not assumed to reproduce the Q18 hyperbolic mechanism. Do not use an arbitrary numerator shift to create an odd-Q cable. Escalate to other Q only when the first tranche identifies a concrete unresolved comparison.

## Work sequence

1. Inventory retained Q18 final fields, logs, configurations and full provenance; verify hashes and bundle contents before a fresh run. If a checkpoint is missing, explicitly label a fresh restart. Never pretend a log or bundle alone is a directly resumable field. Preserve the original campaign and checkpoints.
2. Extend only the necessary seed/config admission for Q17/Q19, after symbolic degree checks, regularity and boundary checks. Current `sf_relax.py` admits only 1, 2, 18 and 22: this documentation does not change that. Verify gradients against independent directional differences; use low-Q controls and a Q22 regression before new research runs. Keep physical coefficients and energy normalization fixed.
3. Reproduce a baseline Q18 run from its exact available settings, or state every reconstruction difference. Then vary one control at a time: initial radial scale/profile, damping/step schedule, mesh spacing and domain extent. Specify parameter values before running; do not sweep blindly until the desired knot appears. Separate the same-seed numerical-convergence series from a multi-seed basin study.
4. Run Q17/Q19 at comparable resolved scales. Use repeated deterministic perturbations/seeds only where they answer the basin question. Validate actual Hopf degree, preimage regularity and orientation before assigning a label. Keep stationary links and knots with their own measured energies; do not score success solely by visual resemblance.
5. For shortlisted stationary outcomes, perform a three-resolution series and a larger domain at matched spacing; retain independent CPU endpoint checks, energy components, residual, scale/virial data and boundary estimates. Record whether each is a new result, a retained control or an unevaluated case. The prior two-grid Q22 benchmark does not satisfy a universal three-resolution requirement for new cases.
6. Reuse the finite-diagram evidence pipeline with multiple regular values and projections, mesh/curve refinement, independent Gauss linking, component invariants and complement checks when admissible. Knot polynomial agreement is not unique identification; a finite diagram does not certify continuum isotopy. Explicitly diagnose failed regular-value, closure and projection cases.
7. Compare outcomes and energy ordering only after common-grid/stationarity checks. Distinguish numerical error from different basins; source rounded energies are references, not exact tuning targets. If the source basin remains unreproduced, publish that result and the explored controls. Do not force preservation of a seed's core knot type.

## Reporting, stop conditions and scope

Keep the original fixed gates as diagnostics: residual 1e-3, same-state mesh/domain energy differences 2%, scale/virial 5%, and source-energy comparison 3% where the state/normalization comparison is meaningful. A gate is not automatically transferred to an unreviewed new configuration. Meeting scalar gates cannot identify a knot. Do not weaken them to match a published picture.

There is **no arbitrary two-hour overall cap**. Before each run choose memory-safe meshes, per-pass limits and restart cadence. Stop a pass for hardware/resource failure or numerical corruption; retain a checkpoint and timestamped reason. Stop the scientific tranche when the specified comparisons are resolved or further work needs a materially different hypothesis. A result may close as partial or unreproduced rather than run indefinitely. Report elapsed wall time, active solver time, restart time and hardware; estimate further duration from observed throughput instead of promising a fixed completion time.

Every run/result/analysis records UTC and Australia/Melbourne timestamps, code commit, exact config and hash, environment/hardware, seed/profile, artifact hashes, field checkpoint path, pass/stage, numerical gates and topology disposition. Preserve machine-readable and human-readable versions. No output is evidence of physical-time stability, electric charge, electron mass, spin or statistics. The charged candidate's deferred dynamics is a separate track; its unresolved gates must not indefinitely postpone this requested neutral-Q assessment.

Publish the next implementation and results from the workstation in reviewable PRs. Prioritize the Q18 diagnosis plus Q17/Q19, then assess whether Q20/Q24 or other Q values are justified. This is the recorded return to additional Q values, not a claim that the investigation is complete.
