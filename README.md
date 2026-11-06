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

Updated: UTC 2026-11-06T13:27:41.408781+00:00; Australia/Melbourne 2026-11-07T00:27:41.408781+11:00.

Use [the roadmap](docs/06-development-plan.md), [status](docs/STATUS.md), [study plans](docs/plans/README.md) and [stage reports](reports/README.md). These derive from [one project register](docs/project/roadmap.json).

S5-B-008 stationary tail-domain screening is assessed. All six states meet the stricter preparation stationarity gates. Q2 passes the original 0.1% shell limit at L17.92 and L20.16; Q1 fails both. Full-field replay confirms the results and residual domain sensitivity. All74 run files are retained in a verified GitHub Release archive. S5-B-009 paired Q1 overnight settling is prepared; it has no native results yet. S5-B-009 paired Q1 tail-settling results are recorded pending scientific assessment; no motion acceptance follows.

A passing stationary shell is not domain independence or motion acceptance. The two larger boxes still differ in inner-field state by 2.93% for Q1 and 1.04% for Q2. The earlier24 moving tail failures and all shape/speed/momentum failures remain unchanged. Temporal/physical-mesh convergence, classical inertia, quantum spin, electric charge and electron acceptance remain open.

Next: **s5-b-009: Paired Q1 stationary tail settling**. Assess paired Q1 settling histories and the verified observation-field archive; retain unresolved outcomes and select any correction before returning to S5-B-006 time convergence.

See [the recording rules](docs/governance/repository-layout.md). Existing evidence paths and bytes are preserved; new runs and assessments use canonical stage/study folders.

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
