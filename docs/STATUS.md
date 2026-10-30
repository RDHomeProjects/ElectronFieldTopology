# Project status

Updated: 2026-10-31 (Australia/Melbourne).

## Current stage

S0 documentation foundation complete. S1-A analytical benchmark implemented and locally verified, awaiting maintainer review on the research branch. No merge is implied by completion of implementation.

Implemented: (1,1) Hopfion evaluator, energy/flow/flux/moment/localisation diagnostics, reproducible CLI, dependency lock, analytical plots and benchmark CI. No independent numerical evolution, topology search, charged electron model or quantum-spin derivation exists.

## Evidence

- [S1-A result and requirement evidence](../reports/s1-a/README.md)
- [Model B0-H11 and equation mapping](models/B0-H11.md)
- [Research issue 1](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/1)
- Local checks: 17 tests passed; documentation integrity and lock consistency passed.
- Hosted checks: [analytical benchmark](https://github.com/RDHomeProjects/ElectronFieldTopology/actions/runs/41063845596) and [documentation](https://github.com/RDHomeProjects/ElectronFieldTopology/actions/runs/41063845501) passed on code commit 7306700. Check the PR for final-head status.
- Null-field checks agree at round-off level; net electric flux is consistent with zero. Moving-sphere energy concentration decreases in the sampled interval.

## Next task

S2: independently evolve the known initial fields using a validated Maxwell scheme. Specify boundary treatment, field staggering/constraints and compute budget before implementing. Compare with S1 analytical fields, resolve boundary energy flux and demonstrate spatial/time-step/domain convergence. Do not broaden to topology searches yet.

## Open decisions

Evolution method/boundaries (S2), topology diagnostics and searches (S3-S4), any extended dynamics (S5), durable archive before research publication. No model extension has been selected.

## Handoff prompt

Read AGENTS.md, this status, B0-H11, S1-A report and the development plan. Review the S1-A PR and exact CI evidence. Continue with S2 only after acknowledging the benchmark's limits; preserve null results and provenance. Do not claim that a Maxwell knot is an electron.
