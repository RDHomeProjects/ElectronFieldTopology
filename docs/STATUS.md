# Project status

Updated: 2026-10-31 (Australia/Melbourne).

## Current stage

S1-A merged via [PR 2](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/2), S2 via [PR 4](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/4), and the pre-S3 literature assessment via [PR 5](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/5), merge commit 34ab9bf. The maintainer accepted the recommendation to proceed with S3-A.

S3-A merged via [PR 7](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/7), merge commit 38e75ea, with all four final-head workflows successful. S3-B merged via [PR 9](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/9), merge commit 73900ad, with all five final-head workflows successful. S3-C merged via [PR 11](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/11), merge commit 1de7714, with all six final-head workflows successful. S3-D bounded helicity/linking instruments merged via PR 13: 76 tests and all 13 benchmark checks pass locally and in the clean evidence run. S4-A merged via PR 15. It admits four known monomial families, retains an explicit invalid/deferred request ledger, and includes four graphics with GitHub-formatted equations. 91 tests and 12 clean-run experiment checks pass locally. Broader S4 search and arbitrary-line topology work remain pending. No electron model or isolated long-time confinement simulation exists.

Implemented: analytical Hopfion, independent periodic Fourier Maxwell evolution, explicit initial projection, spatial/domain/time-quadrature studies, interior Poynting balance, event-consistent analytical Lorentz transformations, independent tensor/common-event controls, finite-cutoff four-momentum convergence, energy-centroid/width and observer-origin diagnostics, all-space moment quadrature with finite-tail controls, classified perturbations with constraint/null diagnostics, independent linear difference-energy controls, local transport and domain sensitivity, periodic Coulomb and unbounded Bateman helicity diagnostics, explicit mean/gauge controls, closed-curve Gauss linking and selected analytical B-fiber tracing, reproducible evidence and bounded workflows.

## Evidence

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

Continue [the level-3 applicability review](literature/depth4/LEVEL3_REVIEW.md) under [the updated protocol](literature/depth4/PROTOCOL.md), tracked by draft PR 17 and issue 16. Level 4 is deferred: no collection, screening or substantive review. Preserve the reported earlier corpus and reconcile its unavailable checkpoint; the new acquisition supplement is explicitly partial.

S4-B remains paused until the level-3 review and development-impact report identify proposed changes and their disposition for maintainer review. Add influential papers to both the main register and BibTeX without changing the frozen seeds. L20–L23 and a relevant correction are added with qualified review depths; this batch does not complete either review pass. Only after this gate may controlled off-core seed/time sampling, trajectory classification and independent topology gates be reconsidered.

## Open decisions

Open/absorbing boundaries before isolated long-time numerical studies; topology instruments and candidate families (S3-D/S4); any extended dynamics (S5); durable archive before research publication. No model extension has been selected.

## Handoff prompt

Read AGENTS.md, this status, the active literature protocol and LEVEL3_REVIEW.md, the acquisition manifest, applicability notes, and S1–S4-A model/report evidence. PRs 13 and 15 are merged. Continue applicability work only through level 3. Recover/reconcile the reported earlier large checkpoint without replacing it with the partial supplement. No level-4 work. Keep S4-B paused until the review and impact assessment are complete and proposed changes are presented for maintainer review. Promote influential papers and corrections to the main bibliography. Preserve access gaps, negative results and the distinction between topology, helicity, energy confinement, electric charge and quantum spin.
