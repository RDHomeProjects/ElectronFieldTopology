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

Updated: UTC 2026-11-12T07:52:19.488261+00:00; Australia/Melbourne 2026-11-12T18:52:19.488261+11:00.

Use [the roadmap](docs/06-development-plan.md), [status](docs/STATUS.md), [study plans](docs/plans/README.md) and [stage reports](reports/README.md). These derive from [one project register](docs/project/roadmap.json).

Q3 has three strictly prepared meshes and near-fourth-order temporal differences over common T0.1/T0.2 windows; small-box z motion fails speed while x short motion and the larger-box z/T0.5 case pass. Q4 medium stationarity does not pass boundary admission and both fine routes remain unresolved. Q7 preparation remains unresolved. The workstation frozen-instrument replay reports 1588 numeric comparisons with zero difference; full fields were archived and PR63 merged.

Only finite reflecting-box windows were tested. Q3 T0.5 temporal/mesh/domain comparisons remain partial, direction/domain sensitivity persists, and Q4/Q7 motion is unqualified or untested. Same-instrument replay agreement is reproducibility evidence, not independent theory validation, spatial/domain closure, unique knot identity, isolated stability, electric charge or quantum spin.

Next: **s5-b-010: Fresh Q3 Q4 Q7 survey and detailed motion**. Prepare the bounded Q3 mesh/domain/initialization/centroid diagnosis described in the new assessment plan; preserve failed small-box cases and original gates. Keep Q4 boundary/preparation and a separately registered Q7 checkpoint continuation as targeted follow-ups. Q1 stays parked and Q2 remains the reference; new evolution requires its own recorded preparation.

See [the recording rules](docs/governance/repository-layout.md). Existing evidence paths and bytes are preserved; new runs and assessments use canonical stage/study folders.

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
