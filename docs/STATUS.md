# Project status

Updated: 2026-10-30 (UTC).

## Current stage

S1-A merged via [PR 2](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/2), S2 via [PR 4](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/4), and the pre-S3 literature assessment via [PR 5](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/5), merge commit 34ab9bf. The maintainer accepted the recommendation to proceed with S3-A.

S3-A is implemented on research/s3a-lorentz-covariance for review. All seven bounded acceptance checks and 41 tests pass locally. The full S3 stage is incomplete: centroid/width, perturbation and topology tasks remain pending. No electron model or isolated long-time confinement simulation exists.

Implemented: analytical Hopfion, independent periodic Fourier Maxwell evolution, explicit initial projection, spatial/domain/time-quadrature studies, interior Poynting balance, event-consistent analytical Lorentz transformations, independent tensor/common-event controls, finite-cutoff four-momentum convergence, reproducible evidence and bounded workflows.

## Evidence

- [S1-A report](../reports/s1-a/README.md)
- [S2 report and requirement mapping](../reports/s2/README.md)
- [S3-A report, scalar results and clean-run manifest](../reports/s3-a/README.md)
- [S3-A model and equation mapping](models/B0-H11-Lorentz.md)
- [S3-A issue 6 and predeclared acceptance](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/6)

S3-A clean code commit c371841: maximum common-event error 5.88e-15; Maxwell residual refinement ratios 3.9618..3.9981; worst finest four-momentum relative error 8.5027e-6; normalised electric flux 1.36e-15. The wrong-snapshot control fails the equations as intended. Consult the PR for final-head hosted checks.

These validate selected transformations, not particle self-binding or electron properties. Periodic S2 conservation does not imply confinement. Source-free charge remains zero.

## Literature checkpoint

[Assessment](literature/pre-s3-review.md): nine additional references L11-L19, updated 2026 publication details for L05, source-specific review depth and S3 subdivisions. [ADR-0003](decisions/ADR-0003-pre-s3-literature.md) is accepted. S3-A maps the inspected Feynman component tables and Hoyos et al. covariant/conserved-quantity passages; S1/S2 numerical findings are unchanged.

## Next task

After S3-A review/merge, S3-B: derive Maxwell stress-energy energy-centroid/localisation diagnostics. Verify dR_energy/dt=P/U for the unbounded solution, distinguish energy centroid from intensity peaks, derive boost comparisons under declared conventions, and separate tail/finite-domain error from physical redistribution. Set acceptance and inspect primary equations before implementation. No perturbation sweep in this task.

S3-C later classifies perturbations by divergence and null-family membership. S3-D/S4 adds helicity/topology instrumentation with explicit gauge, boundaries and tracing controls.

## Open decisions

Open/absorbing boundaries before isolated long-time numerical studies; topology instruments and candidate families (S3-D/S4); any extended dynamics (S5); durable archive before research publication. No model extension has been selected.

## Handoff prompt

Read AGENTS.md, this status, reports S1/S2/S3-A, model specifications and ADR-0002/0003. Review the final S3-A PR checks and the literature assessment. Continue S3-B in a focused PR with primary equations, independent centroid controls and error estimates. Preserve negative results; do not equate periodic conservation, field-line knots or classical angular momentum with an electron.
