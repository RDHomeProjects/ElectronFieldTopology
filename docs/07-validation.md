# Validation and reproducibility

## Separate verification from physical interpretation

Verification asks whether code solves the specified equations accurately. Physical validation asks whether those equations and their solutions explain observations. Passing CI establishes neither a new electron nor experimental proof.

## Benchmark hierarchy

1. Symbolic identities or independent derivations.
2. Known analytical fields evaluated at independent points and times.
3. Numerical residuals and expected order of convergence.
4. Independent evolution compared with analytical time dependence.
5. Conservation and boundary-flux balance.
6. Perturbation, boost and interaction checks.
7. Comparison with empirical electron properties only when applicable.

## Diagnostics

Measure E/B divergence, Faraday/Ampere residuals, U, P, J, external energy flux, and Q_flux on several enclosing surfaces. Report quadrature and finite-domain errors separately.

For localisation measure energy inside fixed radii about both the initial location and tracked centre of energy. Include changing radius/width measures. These distinguish translation from spreading; neither a streamline animation nor a constant knot label proves confinement.

For topology record what is knotted, seed placement, tracing tolerances and closure criteria. Apparent crossings in projections or numerically near-closed lines do not prove a knot invariant. Use analytical labels where available and justify any computed invariant.

For magnetic moment specify the valid current-based or far-field definition and conditions. Do not invent an effective current by omitting Maxwell's displacement-current term. For forces define a subsystem, boundary stress flux and momentum balance; energy cross terms alone are not a force-law derivation.

## Convergence protocol

Use at least three spatial resolutions where applicable. Vary domain size and integration time step independently, respect stability limits, and account for absorbing-boundary losses. Report errors relative to the reference and their scaling. Ensure a smaller error does not merely reflect a changed physical configuration.

Choose tolerances in the experiment specification, with rationale. Changes require retained prior results and explanation.

## Run manifest

Every numerical report must link a machine-readable manifest containing:

- Experiment/model IDs, complete configuration and hash.
- Repository URL, exact commit, dirty-tree flag.
- Dependency lock hash, interpreter and library versions.
- Operating system, CPU/GPU, precision and thread count.
- Grid, domain, time step, duration, boundaries and units.
- Initial conditions, seed, parameter bounds and optimiser stopping rules.
- Commands, run identifier, artifact locations and checksums.
- Diagnostics, estimated numerical errors and scientific outcome.

Use UTF-8 JSON for metrics/manifests and a documented array format for fields. Keep large outputs outside source history. GitHub artifacts expire; releases or archival services need explicit durable preservation decisions before publication.

## Scientific outcome labels

Supported within tested assumptions; not supported within tested assumptions; inconclusive; excluded by stated mathematical constraints. Record separate software verification status. Never convert a negative scientific outcome into a failing implementation test merely to force another search.
