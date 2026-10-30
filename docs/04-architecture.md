# Architecture and folder responsibilities

## Repository map

| Path | Responsibility |
|---|---|
| docs/ | Research purpose, requirements, workflow and validation |
| docs/literature/ | Annotated source register and reading status |
| docs/decisions/ | Architecture and physical-assumption decisions |
| docs/templates/ | Model and experiment-report templates |
| src/electron_field_topology/ | Reusable analytical fields, independent periodic solver and diagnostics |
| tests/ | Independent analytical/symbolic/solver verification |
| experiments/configs/ | Versioned analytical and evolution experiment inputs |
| experiments/ | Experiment definitions and run protocol |
| notebooks/ | Explanatory exploration using package code |
| scripts/ | Small command-line helpers and current documentation checker |
| reports/ | Reviewed experiment summaries; no fabricated initial results |
| data/ | Data policy and provenance manifests |
| .github/workflows/ | Automated checks |
| .github/ISSUE_TEMPLATE/ | Research tasks |
| .github/ | PR template and AI tool entry guidance |

Git tracks files, not empty folders. Reserved folders contain explanatory README files. Implemented analytical and periodic-evolution modules are distinguished from planned capabilities in STATUS.md.

## Planned data flow

Versioned configuration -> field generator -> analytical evaluator or evolution solver -> diagnostics -> report and artifact manifest.

The generator must produce valid E/B fields, not merely an attractive curve. Distinguish time evaluation of an analytical solution from independent numerical evolution.

## Tool choices

Implemented environment: Python 3.11+, NumPy/SciPy, SymPy, pytest and Matplotlib, with versions resolved in uv.lock. Add PyVista only when 3D inspection is useful. S2 uses a collocated periodic Fourier propagator; see ADR-0002 for boundary limitations.

Dedalus is an option for custom PDEs. Meep can provide independent Maxwell/FDTD checks where its interfaces and initial conditions fit. Neither is automatically a quantum-field solver or a model of self-confined vacuum matter. Select an evolution method after analysing constraint preservation, boundaries and benchmark cost.

## Compute

Begin with analytical sampling and modest grids. Profile before acceleration. Numerical code should run locally and in small hosted CI jobs from the same configuration. GPU support, containers and workstation runners are optional later decisions.

Do not use periodic wraparound or a reflecting box as evidence of free-space confinement. Boundaries, finite tails and simulation duration are part of the physical and numerical specification.
