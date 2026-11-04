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

Recorded: UTC 2026-11-04T01:00:23.956083+00:00; Australia/Melbourne 2026-11-04T12:00:23.956083+11:00.

Use [the current roadmap](docs/06-development-plan.md), [status](docs/STATUS.md),
[study plans](docs/plans/README.md) and [stage report indexes](reports/README.md).
These pages derive from one [project register](docs/project/roadmap.json).

PR54 publishes the completed retained-field motion diagnostic assessment: endpoint
replay agrees, while initialization, spatial/domain and classical-inertia sensitivity
remain unresolved. The next scientific study is **s5-b-005, boost initialization and
field registration**, before a focused new motion/convergence run. Six bounded low-speed
passes remain; general isolated motion, quantum spin, electric charge and an electron
model are not accepted.

S1–S4 baseline instruments and S5-A static references remain available through the
stage indexes. S5-B contains neutral physical-time dynamics; S5-C covers deferred
charged feasibility. Q17/Q19 motion, Q18 fresh fine starts and additional-Q comparisons
remain explicitly sequenced. Conditional quantum/probe work does not bypass numerical
convergence or supply emergent properties by assumption.

See [the repository layout and recording rules](docs/governance/repository-layout.md).
Existing report folders and scientific bytes are preserved compatibility records;
new work uses stable stage/study paths. Renderer exports remain separate from science.

```bash
uv sync --frozen --all-groups
python3 scripts/project_records.py check
python3 scripts/check_docs.py
```

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
