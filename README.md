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

The [workstation GPU continuation record](reports/s5-a/workstation-2026-11-01/README.md) preserves the exact evidence and partial scientific outcome. Q22 retains a cable-compatible core but needs finer-grid stationarity and domain checks. Q18 reaches a stationary linked alternative rather than the target hyperbolic knot. Neither target is a completed reproduction. The [tightened milestone decision](docs/decisions/ADR-0007-tightened-milestones.md) prioritises bounded Q22 closure, then a charged relativistic equation audit.

S5-A provides a [static Skyrme–Faddeev reference](docs/models/SF-J2015-static.md), independent simple controls, a [paired CPU/GPU timing harness](docs/static-gpu-timing.md) and a [checkpointed local campaign](docs/static-gpu-continuation.md). Maintainer-reported RTX 2080 Super Max-Q float64 timings show about 4.5x short-solve speedup over twelve CPU threads after numerical checks; raw timing artifacts have not been independently retrieved. No physical-time solver or electron model is claimed.

S4-C adds [bounded return-section diagnosis](docs/models/B0-S4C-ReturnMap.md), followed by [a source-mapped model-feasibility decision](docs/decisions/ADR-0006-model-feasibility.md). No extended physical dynamics or electron-model claim is introduced.

S4-B now adds [bounded off-core tracing and independent polygon invariants](docs/models/B0-S4B-Offcore.md), integrating the recovered literature findings. See [the report](reports/s4-b/README.md). The comprehensive literature review remains incomplete and level 4 deferred; the maintainer explicitly authorised this bounded continuation.

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

The [pre-S3 literature assessment](docs/literature/pre-s3-review.md) identifies additional sources and refines the next stage. S3-A adds event-consistent Lorentz transformations with independent tensor and Maxwell controls; see [the specification](docs/models/B0-H11-Lorentz.md) and [evidence report](reports/s3-a/README.md). S3-B adds [energy-centroid and width diagnostics](docs/models/B0-H11-Centroid.md), including boost offsets, origin controls, all-space quadrature and finite-tail studies; see [the S3-B report](reports/s3-b/README.md). S3-C adds [classified perturbation and difference-energy controls](docs/models/B0-H11-Perturbations.md); see [measured results and literature alignment](reports/s3-c/README.md). S3-D adds [declared-domain helicity and selected closed-fiber linking instruments](docs/models/B0-H11-Topology.md); see [the S3-D report](reports/s3-d/README.md). S4-A adds a [bounded Bateman candidate catalogue](docs/models/B0-Bateman-PQ.md), with [graphical results and GitHub-rendered equations](reports/s4-a/README.md). Broader searches and arbitrary-line topology certificates remain pending.

For S3-A, run:

```bash
uv run --frozen python -m electron_field_topology.relativity_benchmark --config experiments/configs/hopfion-s3a.json --output artifacts/s3a-local
```

For S3-B, run:

```bash
uv run --frozen python -m electron_field_topology.localisation_benchmark --config experiments/configs/hopfion-s3b.json --output artifacts/s3b-local
```

For S3-C, run:

```bash
uv run --frozen python -m electron_field_topology.perturbation_benchmark --config experiments/configs/hopfion-s3c.json --output artifacts/s3c-local
```

For S3-D, run:

```bash
uv run --frozen python -m electron_field_topology.topology_benchmark --config experiments/configs/hopfion-s3d.json --output artifacts/s3d-local
```

For S4-A, run:

```bash
uv run --frozen python -m electron_field_topology.candidate_benchmark --config experiments/configs/bateman-s4a.json --output artifacts/s4a-local
```

## Development

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing this project. Software implementation should use small pull requests tied to requirement IDs and explicit experiments.

The research distinguishes field-line knots, energy-flow paths, optical vortices, and topology of space. These are not interchangeable. Maxwell's equations already incorporate special relativity; it is not an optional correction applied after a simulation.

## Licensing and citation

Code, executable notebook cells, scripts, configuration and workflows: [Apache License 2.0](LICENSE).
Original explanatory prose and figures: [CC BY 4.0](LICENSE-DOCS.md).
Third-party works retain their own terms; this repository links to papers rather than relicensing them.

See [NOTICE](NOTICE) and [CITATION.cff](CITATION.cff). Please cite the project and the primary papers used when publishing results.
