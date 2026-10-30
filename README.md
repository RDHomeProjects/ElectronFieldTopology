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

S1-A adds an analytical (1,1) Hopfion evaluator, energy/flux/localisation diagnostics, independent polynomial and symbolic checks, and a reproducible benchmark. It samples a known solution at chosen times. S2 adds an independent periodic Fourier Maxwell solver, measured initial projection, spatial/domain studies and interior Poynting balance. Neither implementation models an electron.

See [the equation mapping and conventions](docs/models/B0-H11.md). Measured evidence and interpretation are kept in [reports](reports/README.md).

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run from the repository root:

```bash
uv sync --frozen --all-groups
uv run --frozen pytest -q
python3 scripts/check_docs.py
uv run --frozen eft-benchmark --config experiments/configs/hopfion-s1.json --output artifacts/s1-local
```

For S2, run:

```bash
uv run --frozen python -m electron_field_topology.evolution_benchmark --config experiments/configs/hopfion-s2.json --output artifacts/s2-local
```

See [the S2 solver specification](docs/models/B0-H11-PSATD.md). The periodic box is a controlled approximation, not an absorbing free-space boundary. The [evolution workflow](.github/workflows/evolution.yml) also offers a bounded manual run.

Use a new or empty output directory. Outputs include metrics, a provenance manifest, field/energy-flow slices and localisation plots. Bulk outputs remain ignored. [Benchmark CI](.github/workflows/benchmark.yml) runs small checks and uploads evidence; documentation checks remain separate.

The [pre-S3 literature assessment](docs/literature/pre-s3-review.md) identifies additional sources and refines the next stage. S3-A adds event-consistent Lorentz transformations with independent tensor and Maxwell controls; see [the specification](docs/models/B0-H11-Lorentz.md) and [evidence report](reports/s3-a/README.md). S3-B/C remain pending.

For S3-A, run:

```bash
uv run --frozen python -m electron_field_topology.relativity_benchmark --config experiments/configs/hopfion-s3a.json --output artifacts/s3a-local
```

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
