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

Updated: UTC 2026-11-08T01:48:14.439097+00:00; Australia/Melbourne 2026-11-08T12:48:14.439097+11:00.

Use [the roadmap](docs/06-development-plan.md), [status](docs/STATUS.md), [study plans](docs/plans/README.md) and [stage reports](reports/README.md). These derive from [one project register](docs/project/roadmap.json).

PR61 is merged. Q1 correction is parked with its 1.563660% speed failure retained. Q2 passed the prior bounded case gates; its spatial/domain work remains open. A staged coarse Q17/Q19 motion screen is prepared: short Q2 reference, bounded preparation and T=0.2 early stops, then half-dt confirmations for passing candidates only. No higher-Q production trajectory has been run by this preparation.

A coarse screen selects follow-up work and separates representation, preparation and moving-field failures. Detailed physical-grid/domain and long-time qualification remains open. Original 129-cubed sources and full coarse states are retained for finer restart/re-readmission; Q18 fresh-start and additional-Q studies remain registered.

Next: **s5-b-007: Q17/Q19 motion comparison**. Run the Q2 short reference first, then bounded Q17/Q19 readmission and T=0.2 coarse motion with early original-gate stops. Assess both coarse arms before half-dt confirmations for passes only. Retain original fields and coarse checkpoints for a separately specified finer follow-up.

See [the recording rules](docs/governance/repository-layout.md). Existing evidence paths and bytes are preserved; new runs and assessments use canonical stage/study folders.

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
