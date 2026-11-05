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

Updated: UTC 2026-11-05T05:06:55.459022+00:00; Australia/Melbourne 2026-11-05T16:06:55.459022+11:00.

Use [the roadmap](docs/06-development-plan.md), [status](docs/STATUS.md), [study plans](docs/plans/README.md) and [stage reports](reports/README.md). These derive from [one project register](docs/project/roadmap.json).

S5-B-006 focused motion is assessed: 48 admissions passed and eight arms completed T=1/2/3. Cubic initialization improves matched shape residuals but introduces or retains speed failures; all 24 milestone tail checks fail. The focused tranche is complete; physical convergence remains under S5-B-006. All 525 native files are retained in a verified GitHub Release archive. The maintainer has requested a separate S5-B-008 stationary L17.92/L20.16 tail-domain screen before returning to the temporal audit; it is prepared, with no new native results yet.

No milestone passes every original gate: overlapping failures are 24 tail, 16 shape, six momentum and four speed. One dt/grid/box and reflecting long windows do not establish isolated motion. The earlier 60-case record and all negative findings remain intact. Classical inertia, quantum spin, electric charge and electron-model acceptance remain open.

Next: **s5-b-008: Stationary tail-domain screening**. Run the prepared stationary Q1/Q2 L16/17.92/20.16 screen, archive all new checkpoints, then assess moving-shell and fixed-region/core measurements. No physical-time trajectory or automatic acceptance.

See [the recording rules](docs/governance/repository-layout.md). Existing evidence paths and bytes are preserved; new runs and assessments use canonical stage/study folders.

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
