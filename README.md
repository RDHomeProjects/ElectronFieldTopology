# ElectronFieldTopology

Computational investigation of electromagnetic field topologies, relativistic dynamics, and emergent electron-like properties through reproducible simulations and automated validation.

## Purpose

Investigate whether field structure and energy distribution can explain interactions interpreted as electric charge, and whether suitable dynamics can support stable particle-like configurations. This is exploratory research, not a claim that electrons are confined light.

The first task is to reproduce known electromagnetic knots and establish reliable diagnostics. The project will distinguish mathematical existence, numerical evidence, and experimental support. A well-supported negative result is a successful research outcome.

## Start here

1. [Project purpose and scope](docs/01-purpose-and-scope.md)
2. [Physics baseline and hypotheses](docs/02-physics-and-hypotheses.md)
3. [Requirements and acceptance criteria](docs/03-requirements.md)
4. [Architecture and folders](docs/04-architecture.md)
5. [AI development workflow](docs/05-ai-development.md)
6. [Staged development plan](docs/06-development-plan.md)
7. [Validation and reproducibility](docs/07-validation.md)
8. [Literature register](docs/literature/README.md)
9. [Current status and next task](docs/STATUS.md)

## Current capability

Updated: UTC 2026-11-08T01:09:15.758801+00:00; Australia/Melbourne 2026-11-08T12:09:15.758801+11:00.

Use [the roadmap](docs/06-development-plan.md), [status](docs/STATUS.md), [study plans](docs/plans/README.md) and [stage reports](reports/README.md). These derive from [one project register](docs/project/roadmap.json).

The boundary-admitted T1 temporal tranche is assessed: six complete trajectories, zero failures across 126 recorded tail observations, near-fourth-order fixed-grid refinement. Q2 passes all seven original case gates; Q1 retains 1.563660% speed error against 1%. All 128 full archive files/52 NPZ records and matched-time fields were independently verified; historical failed milestones are retained.

Temporal refinement and the measured shell correction do not establish physical-mesh/domain convergence or isolated motion. Q1 speed still fails; endpoint/settling labels and earlier negative findings remain. Higher-Q motion, charged theory, quantum spin and apparatus milestones retain their prerequisites.

Next: **s5-b-006: Focused motion, mesh and domain convergence**. Freeze the next physical-grid/domain matrix: same-grid known-coasting and zero-speed centroid/initialization controls, at least three physical spacings at fixed admitted box, matched-spacing domain pairs, and crossed-direction controls as needed. Keep the original gates and analytic beta/rate; limited temporal confirmation on a future finest mesh rather than another broad dt sweep.

See [the recording rules](docs/governance/repository-layout.md). Existing evidence paths and bytes are preserved; new runs and assessments use canonical stage/study folders.

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
