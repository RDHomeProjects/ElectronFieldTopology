# Project status

Updated: 2026-11-01 (Australia/Melbourne).

## Recovered analysis publication

The written-analysis transfer is complete: all 5,217 words in the corpus defined for PRs 18 and 19 are published in approximately 10% increments. See [the reading index and verification record](literature/recovered-transfer/README.md). Original source hashes, review depths, negative findings and limitations are preserved; no new literature review was performed.

This completes publication of that prose corpus, not the scientific review or publication of the 113,295-ID citation dataset and supporting checkpoint implementation. PR 17 remains open for the wider checkpoint. The maintainer has now explicitly resumed bounded S4-B under [ADR-0005](decisions/ADR-0005-s4b-resumption.md); the larger review remains incomplete and level 4 deferred. PR 29 separately published a 1,133-ID citation-data sample.

## Current stage

S1-A merged via [PR 2](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/2), S2 via [PR 4](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/4), and the pre-S3 literature assessment via [PR 5](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/5), merge commit 34ab9bf. The maintainer accepted the recommendation to proceed with S3-A.

S3-A merged via [PR 7](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/7), merge commit 38e75ea, with all four final-head workflows successful. S3-B merged via [PR 9](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/9), merge commit 73900ad, with all five final-head workflows successful. S3-C merged via [PR 11](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/11), merge commit 1de7714, with all six final-head workflows successful. S3-D bounded helicity/linking instruments merged via PR 13: 76 tests and all 13 benchmark checks pass locally and in the clean evidence run. S4-A merged via PR 15. It admits four known monomial families, retains an explicit invalid/deferred request ledger, and includes four graphics with GitHub-formatted equations. 91 tests and 12 clean-run experiment checks pass locally. Broader S4 search and arbitrary-line topology work remain pending. No electron model or isolated long-time confinement simulation exists.

Implemented: analytical Hopfion, independent periodic Fourier Maxwell evolution, explicit initial projection, spatial/domain/time-quadrature studies, interior Poynting balance, event-consistent analytical Lorentz transformations, independent tensor/common-event controls, finite-cutoff four-momentum convergence, energy-centroid/width and observer-origin diagnostics, all-space moment quadrature with finite-tail controls, classified perturbations with constraint/null diagnostics, independent linear difference-energy controls, local transport and domain sensitivity, periodic Coulomb and unbounded Bateman helicity diagnostics, explicit mean/gauge controls, closed-curve Gauss linking and selected analytical B-fiber tracing, reproducible evidence and bounded workflows.

## Bounded S4-B merged result

The maintainer-authorised off-core tranche is merged via [PR 31](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/31), merge commit `0be60b6`, with all nine final-head CI workflows successful. It contains 24 family/seed/time cases: 12 refined closures and 12 unresolved budgets. All eight core controls close; off-core higher-family trajectories remain unresolved. Independent Fox determinant/projection and signed-link checks pass with stated polygon limits. 116 tests pass; see [the measured S4-B report](../reports/s4-b/README.md). Main bibliography L20–L35 and the correction/alias mapping are integrated. Complete knot identification and the wider literature review remain open; no confinement or electron claim follows.

## Bounded S4-C and feasibility decision for review

The authorised return-map diagnosis contains 33 independently controlled diagnostic runs, three replication seeds and manufactured/Maxwell controls. Results: 30 arclength-unresolved and 3 evaluation-limited diagnostic runs; 29 comparable prefixes match (including three self-checks). All ten instrument checks and 123 tests pass. See [the report](../reports/s4-c/README.md). [ADR-0006](decisions/ADR-0006-model-feasibility.md) records the no-go/conditional-go/defer model-feasibility decision. No extended physical dynamics or validated electron model is introduced.

## S5-A static reference — draft and interrupted

[PR 36](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/36) integrates Jennings (L36) and supporting references, a separate SF-J2015 static unit-vector energy, independent gradient/analytic controls and three-mesh Q=1/Q=2 references. **136 local tests passed.** The first cable/hyperbolic target attempts are budget-limited; later reproduction work was interrupted when the execution environment became unavailable. Neither target is accepted as a completed reproduction. Read [the measured partial report](../reports/s5-a/README.md) and [the recovery record](../reports/s5-a/interruption-2026-10-31.md) before running further numerics. Preserve all failed/inconclusive results. No physical-time solver or electron model is introduced; level 4 stays deferred.

## Evidence

- [S4-C bounded return-map report and retained outputs](../reports/s4-c/README.md)
- [S4-C primary-equation feasibility audit](models/S5-feasibility-audit.md)
- [S4-B bounded off-core report](../reports/s4-b/README.md)
- [S4-B source and acceptance map](models/B0-S4B-Offcore.md)

- [S1-A report](../reports/s1-a/README.md)
- [S2 report and requirement mapping](../reports/s2/README.md)
- [S3-A report, scalar results and clean-run manifest](../reports/s3-a/README.md)
- [S3-A model and equation mapping](models/B0-H11-Lorentz.md)
- [S3-B report and retained coarse-resolution failure](../reports/s3-b/README.md)
- [S3-B model and derivation](models/B0-H11-Centroid.md)
- [S3-C report with primary-source quotations and measured alignment](../reports/s3-c/README.md)
- [S3-C model, derivations and acceptance](models/B0-H11-Perturbations.md)
- [S3-D report, traced curves and literature alignment](../reports/s3-d/README.md)
- [S3-D model and convention audit](models/B0-H11-Topology.md)
- [S4-A graphical report and equation displays](../reports/s4-a/README.md)
- [S4-A model/source mapping](models/B0-Bateman-PQ.md)
- [S4-A issue 14](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/14)
- [S3-D issue 12](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/12)
- [S3-C issue 10](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/10)
- [S3-B issue 8 and original acceptance](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/8)
- [S3-A issue 6 and predeclared acceptance](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/6)

S3-A clean code commit c371841: maximum common-event error 5.88e-15; Maxwell residual refinement ratios 3.9618..3.9981; worst finest four-momentum relative error 8.5027e-6; normalised electric flux 1.36e-15. The wrong-snapshot control fails the equations as intended. Consult the PR for final-head hosted checks.

S3-B clean code commit 73da3fc: maximum boosted centroid error 2.82e-12 and velocity error 1.41e-12. Source RMS radius grows 1 to 2. In the zero-momentum frame the centroid stays at the origin while RMS radius grows 1.291 to 2.380 and radius-2 contained energy drops 91.66% to 33.45%. Coarse radial quadrature failed four criteria and is retained; doubling radial nodes passes without changing tolerances.

S3-C clean code commit b70b565: maximum superposition error 6.62e-14, global difference-energy drift 9.77e-15, periodic divergence 1.81e-14. All nine generic seeded curl trials break null conditions while meeting source-free constraints. Analytic amplitude/duality controls remain null to roundoff; periodic controls track their nonzero projected base null score. Seed 11 local difference-energy fraction falls 68.24% to 58.03% while the global norm is conserved. Finest Poynting-balance defect is .484% of initial interior difference energy; time-flux refinement ratio4.015. The remaining diagnostic error is retained explicitly.

S3-D clean code commit 851c482: two selected unbounded analytical B fibers at t=0 close with maximum original gap 6.44e-14. Gauss-link estimates 1.001608577, 1.000401732 and 1.000100407 converge toward +1. Known signed/reversed/unlinked controls pass. Unbounded He=Hm=pi² is recovered to 7.55e-15 relative error; periodic gauge/optical-helicity checks pass at roundoff. Nonzero mean, longitudinal and open-trajectory controls are explicitly rejected. A factor-of-two mismatch in the printed non-null extension of Hoyos Eq.(2.12) is documented and independently checked; null conclusions are unaffected.

S4-A clean code commit ff0d6ea: families (1,1),(2,1),(2,3),(3,2) pass null/Maxwell and independent all-space integral references at times 0/.75. Sixteen default core traces, two trefoil refinements and a separate return-section guard close; the guard retains an early .817 gap before a later closure. Largest integral reference error is 5.37e-13. Parameterised core-pair absolute Gauss estimates converge toward 1,2,6,6 under the calibrated convention. The report retains a v1 preprint linked-ring count discrepancy and distinguishes parameterised curves from independent ODE samples. Four graphics were visually inspected.

These validate selected transformations, energy, perturbation, topology and bounded family instruments, not particle self-binding or electron properties. Periodic S2 conservation does not imply confinement. Source-free charge remains zero.

## Literature checkpoint

[Assessment](literature/pre-s3-review.md): nine additional references L11-L19, updated 2026 publication details for L05, source-specific review depth and S3 subdivisions. [ADR-0003](decisions/ADR-0003-pre-s3-literature.md) is accepted. S3-A maps the inspected Feynman component tables and Hoyos et al. covariant/conserved-quantity passages; S1/S2 numerical findings are unchanged.

## Next task

The user supplied successful RTX 2080 Super Max-Q device checks and paired
Q22/Q18 short-solve speedups around 4.5x against twelve CPU threads. A
[checkpointed GPU continuation campaign](static-gpu-continuation.md) is now
prepared with float64 atomic fields, restart, endpoint CPU audits and bounded
topology/scaling/mesh/domain/same-charge evidence collection. Read the
[preparation and recovery record](../reports/s5-a/gpu-continuation-2026-11-01/README.md).
Actual long-run workstation execution and the final scientific assessment remain
pending. No reproduction is accepted on the strength of timing measurements.

A bounded CPU [timing harness](static-timing.md) now supports the requested local
workstation comparison. It uses the unchanged energy/minimisation implementation;
the replacement-environment reference and approximate older history rates are
recorded in [the timing report](../reports/s5-a/timing-2026-10-31/README.md).
It supplies no GPU backend or additional reproduction acceptance.

The requested experimental [GPU timing counterpart](static-gpu-timing.md) now
adds float64 CUDA energy/gradient, device-array minimisation and diagnostics, with
mandatory on-device CPU parity checks before timing ratios. CPU validation and
offline compilation are recorded in [the validation report](../reports/s5-a/gpu-validation-2026-10-31/README.md).
No actual GPU execution or speedup was measured in this environment; first-device
validation remains pending on the workstation. Production reproductions remain
unfinished.

Restore and audit S5-A checkpoint/job state using the [recovery record](../reports/s5-a/interruption-2026-10-31.md), then complete bounded source-mapped cable/hyperbolic attempts and energy comparisons. The static functional/simple references are validated to their stated limits; non-torus reproductions remain unfinished. GPU acceleration requires a separately validated backend and benchmark. No blanket exclusion of other models or acceptance of an electron theory follows.

## Open decisions

Open/absorbing boundaries before isolated long-time numerical studies; topology instruments and candidate families (S3-D/S4); any extended dynamics (S5); durable archive before research publication. No model extension has been accepted as an electron model. A static-energy mechanism reference is proposed in ADR-0006; no new physical dynamics are implemented.

## Handoff prompt

Read AGENTS.md, this status, the post-S4-B direction assessment, ADR-0005/0006, the S4-C return-map report and S5 equation audit, the B0-S4B-Offcore source/acceptance map, its merged report, the main bibliography and S1–S4-A evidence. The maintainer explicitly resumed bounded S4-B despite the unfinished comprehensive literature review. Keep level 4 deferred and do not claim that corpus publication closes the scientific review. Preserve field-zero and finite-budget outcomes, distinguish polygon invariants from knot identification, and retain energy/charge/quantum gates.
