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

Updated: UTC 2026-11-10T13:31:16.111336+00:00; Australia/Melbourne 2026-11-11T00:31:16.111336+11:00.

Use [the roadmap](docs/06-development-plan.md), [status](docs/STATUS.md), [study plans](docs/plans/README.md) and [stage reports](reports/README.md). These derive from [one project register](docs/project/roadmap.json).

S5-B-007 is assessed: Q2 passes the short motion reference; Q17/Q19 exhaust 200 preparation iterations each without stationary admission, so higher-Q motion is untested. All 79 archive payloads and 23 NPZ states are independently verified. Q1 remains parked with its original failure retained.

Stationary residuals, rather than the measured rest tails, block the coarse higher-Q arms. Return to Q2 numerical controls and physical-mesh/domain convergence; any additional higher-Q preparation/finer restart is a new conditional tranche with preserved original-source controls. No general isolated motion, curve identity, charge or quantum-spin conclusion follows.

Next: **s5-b-006: Focused motion, mesh and domain convergence**. Resume Q2 numerical controls after both coarse higher-Q preparations remain unresolved: isolate centroid/initialization and stationarity measurement effects, then specify fixed-box physical meshes and matched-spacing larger domains with fresh readmission and original tail reserves. Q1 correction stays parked; do not repeat completed temporal work without a new diagnostic reason.

See [the recording rules](docs/governance/repository-layout.md). Existing evidence paths and bytes are preserved; new runs and assessments use canonical stage/study folders.

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
