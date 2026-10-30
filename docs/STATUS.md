# Project status

Updated: 2026-10-31 (Australia/Melbourne).

## Current stage

S1-A merged via [PR 2](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/2).
S2 periodic-reference implementation and validation complete, awaiting maintainer review on research/s2-maxwell-evolution. No merge of S2 is implied.

Implemented: analytical Hopfion, independent source-free Fourier Maxwell evolution, explicit initial transverse projection, spatial/domain/time-quadrature studies, energy/momentum/divergence diagnostics, interior Poynting balance, reproducible evidence and bounded manual workflow. No electron model or isolated long-time confinement simulation exists.

## Evidence

- [S1-A report](../reports/s1-a/README.md)
- [S2 report and requirement mapping](../reports/s2/README.md)
- [S2 equation/domain specification](models/B0-H11-PSATD.md)
- [S2 method decision](decisions/ADR-0002-s2-solver.md)
- [Issue 3](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/3)
- 26 tests passed locally. All 10 bounded S2 experiment acceptance checks passed.
- [Hosted evolution study](https://github.com/RDHomeProjects/ElectronFieldTopology/actions/runs/41065519771), [analytical benchmark](https://github.com/RDHomeProjects/ElectronFieldTopology/actions/runs/41065519388) and [documentation](https://github.com/RDHomeProjects/ElectronFieldTopology/actions/runs/41065519763) passed on code commit 1ba64a9. Consult the PR for final-head checks.

Central error decreases with resolution and larger domain, with a finite-box floor. Periodic energy/momentum conservation does not imply confinement; interior energy loss and surface flux are recorded with diagnostic errors.

## Next task

S3 after review: consistent Lorentz transformations of analytical spacetime fields, localisation/width diagnostics and bounded perturbation studies. Separate coordinate transformations from deformations; quantify boundary and initial-projection effects before drawing stability conclusions.

## Open decisions

Open/absorbing boundary treatment before isolated long-time studies; topology invariants and candidate families (S3-S4); any extended dynamics (S5); durable archive before research publication. No model extension has been selected.

## Handoff prompt

Read AGENTS.md, this status, S1/S2 reports, model specifications and ADR-0002. Review exact CI and approximation limits. Continue S3 in a focused PR with primary equations and independent tests. Preserve negative results and do not equate periodic conservation or classical angular momentum with an electron.
