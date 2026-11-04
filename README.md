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

Updated: UTC 2026-11-04T14:17:45.414426+00:00; Australia/Melbourne 2026-11-05T01:17:45.414426+11:00.

Use [the roadmap](docs/06-development-plan.md), [status](docs/STATUS.md), [study plans](docs/plans/README.md) and [stage reports](reports/README.md). These derive from [one project register](docs/project/roadmap.json).

S5-B-005 assessed 30 retained Q1/Q2 cases. Cubic analytic-rate/D4 mismatch falls from 5.99–10.98% to 0.83–2.67% across all 24 moving cases (75.56–86.13% reduction). Twelve raw beta=.1 candidates violate the fixed layers; they require explicit readmission before a focused motion comparison. S5-B-006 software/synthetic controls have passed; native focused Q1/Q2 trajectories await workstation execution.

The original 60-case record retains 6 bounded passes and overlapping 50 tail, 18 shape and 4 momentum failures. Sampling, physical-mesh/domain and classical-inertia sensitivity remain unresolved. No general isolated-motion, full stability, quantum-spin, electromagnetic-charge or electron-model acceptance follows.

Next: **s5-b-006: Focused motion, mesh and domain convergence**. Authenticate retained fields; readmit 48 initial combinations, then execute eight matched beta=.3 Q1/Q2 x/z trilinear/cubic arms at dt=.01 through T=3 with T=1/2/3 checkpoints. Archive every new full field before cleanup; assess this tranche before temporal/third-mesh/domain expansion.

See [the recording rules](docs/governance/repository-layout.md). Existing evidence paths and bytes are preserved; new runs and assessments use canonical stage/study folders.

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
