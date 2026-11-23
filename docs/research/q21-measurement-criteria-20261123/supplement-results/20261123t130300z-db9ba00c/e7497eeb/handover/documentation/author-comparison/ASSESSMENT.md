# Q21 measurement criteria, completed results and CPU resolution supplement

Review timestamps: UTC 2026-11-23T12:59:50.872027+00:00; Australia/Melbourne 2026-11-23T23:59:50.872027+11:00.

The original run completed with 480 updates and no new stationary Q21 field. The current force 1e-4 and maximum-acceleration 1e-3 limits are project preparation targets, tightened tenfold in S5-B-008. Their equivalence to the papers' criteria has not been established. They remain unchanged in both new CPU branches.

The comparison below separates each author's actual measure from project admission. A threshold is not invented where a paper reports only an accuracy estimate. Known-state recognition, perturbation/return and spatial convergence remain separate from a small energy change.

| Case | Backend | Updates | Final force | Final max acceleration | Median relative energy change, last 10 | Updates below 1e-9, last 10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| exact-control | cuda | 80 | 0.000940938 | 0.0153818 | 1.51e-08 | 1/10 |
| mesh-129 | cuda | 80 | 0.00124854 | 0.0129925 | 3.13e-08 | 0/10 |
| mesh-137 | cuda | 80 | 0.00206781 | 0.0175957 | 2.27e-07 | 0/10 |
| mesh-145 | cuda | 80 | 0.00143146 | 0.0322274 | 1.9e-07 | 0/10 |
| mesh-153 | cuda | 80 | 0.00213368 | 0.0296338 | 2.08e-07 | 0/10 |
| mesh-161 | cuda | 80 | 0.00209368 | 0.0298422 | 1.66e-07 | 0/10 |

### Hietarinta and Salo (2000)

Source: https://users.aalto.fi/~ala/pdf/081201R.pdf (PDF page 2, numerical methods; pages 3–4, terraces and finite-box/discretization checks).

Applied: Per-accepted-update relative energy changes at 1e-7 and 1e-9; persistence counts; neighbour-angle warning at 30 degrees. These reproduce a reported measure, not the original optimizer or stopping implementation.

Limit: No perturbation-and-return experiment, independent same-state literature identification, or fixed-spacing domain comparison is performed. Nonstationary Q21 endpoints cannot establish local-minimum stability from a return claim.

Assessment: **Energy-only diagnostic evaluated; full published convergence/stability procedure not reproduced.**

### Sutcliffe (2007)

Source: https://arxiv.org/pdf/0705.1468 (Numerical methods, PDF page 4).

Applied: Registered fixed-box energy and geometric comparisons; literature approximately 0.1% relative-energy accuracy shown only as context. Additional native residual/morphology diagnostics are supplied by the workstation supplement.

Limit: Approximately 1% absolute bias and 0.1% relative-energy accuracy are reported estimates, not stopping thresholds. The paper studies Q through 16; it has no Q21 target field. No matching absolute-energy target is inferred.

Assessment: **Refinement consistency assessed on unresolved endpoints; stationary continuum convergence and reproduction remain unestablished.**

### Jennings (2015)

Source: https://arxiv.org/pdf/1412.8597 (Section 4, numerical methods, PDF pages 9–10).

Applied: Report actual grid spacing against the published 301^3, spacing 0.06 setup; export display-only n3=-0.95 surfaces and compare measured energies and residuals across our grids.

Limit: The methods description supplies no equivalent normalized-force/maximum-acceleration cutoff. Knot/link preimage correspondence and identical-state energy comparison are not established; no published-stability pass is invented.

Assessment: **Method-informed diagnostics applied; exact published basin, spatial accuracy and local-minimum reproduction remain unverified.**

## Supplementary measurement and execution scope

The new executable plan measures all six retained Q21 endpoints, reconstructs the four original refined initial fields from the authenticated iteration-545 parent, and runs separate 177^3 and 193^3 CPU-float64 branches. Each new branch has at most 80 charged attempts, a 160-attempt total ceiling, the same box 30.72, shift 0.25, source alpha, native restart schedule and original gates. New branches reset conjugacy like the original resolution arms. No completed branch is transferred or overwritten. The first attempt after native iteration 599 triggers the same scheduled native restart at 600.

The CPU branches and existing endpoints are not compared as bit-identical backend trajectories. The unchanged D4 action and independent directional-derivative checks qualify the arithmetic; CPU repeat evaluations are explicitly not called independent implementations. No GPU package or device is needed for the new work.

Read-only field outputs include core/guard residual distributions, maxima, vector RMS and component RMS, energy components and a labelled continuum-inspired virial proxy. That proxy is not an exact fixed-lattice scaling derivative or a new admission gate. Images use authors' n3 isosurface levels as display conventions; neither connected-component counts nor pictures identify a knot or prove stability. Original field bytes are hashed before and after reading. Missing supplementary inputs remain explicit deferrals; changed hashes are faults.

The original 177^3 and 193^3 deferrals arose because auto pinned CUDA across grids, with no per-grid CPU fallback. The new explicit CPU branches repair coverage without relabelling the original deferrals. CPU resource qualification is repeated for each geometry. Memory pressure or an unqualified geometry pauses or defers work; no scientific threshold or host reserve is lowered.

## Interpretation and next decision

A relative-energy-change threshold is optimizer-step dependent. Flat energy can coexist with a nonzero core residual. The original refined endpoints have last-ten median changes around 1.7e-7 to 2.1e-7 and no final-ten update below 1e-9; they do not gain a Hietarinta–Salo convergence certificate. Some paper-inspired measurements are available now, while full-field and new-grid outcomes are added only after actual workstation execution.

Supplementary morphology, residual localization and CPU-grid outcomes should decide whether to continue, change an optimizer in a separately registered comparison, or investigate finite-box effects. A future duration-specific rest-evolution calibration may test whether the project preparation limits are unnecessarily restrictive. This handover performs no physical-time evolution, no perturbation-and-return relaxation, no model change and no blanket Q2–Q32 rerun.

See AUTHOR-METRICS.json, AUTHOR-METRICS.csv and ENERGY-CHANGE-PER-UPDATE.csv for all calculated values. The original evidence and the earlier detailed scientific review are retained unchanged elsewhere in the published package. In a completed supplement, FIELD-AUDIT-SUMMARY.json and record.json distinguish measured, deferred, interrupted and untested work.
