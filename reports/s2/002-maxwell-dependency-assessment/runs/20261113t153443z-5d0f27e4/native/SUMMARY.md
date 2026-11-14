# Bounded Maxwell validation extension

{"utc": "2026-11-13T15:43:33.512867+00:00", "melbourne": "2026-11-14T02:43:33.512867+11:00"}

Status: complete_pending_review; role: local-bounded-validation.

Cases: 61; all periodic numerical controls pass: True.

Hopfion boundaries remain analytically driven; the interior Poynting cube is not an isolated outer boundary. Common-grid linear interpolation and magnetic time synchronization contribute diagnostic error. Periodic packet and driven Hopfion are separate numerical problems. Cubic packet rotations preserve periodicity and test axis permutations, not arbitrary-angle isotropy. Flux uses nested temporal quadrature on the same trajectory; a flux defect is not solely an integration-time error. Fixed grid and box do not establish spatial/domain convergence. The dt-dependent analytic half-step startup is retained and qualified. No SF, topology, confinement, charge, spin or electron gate is closed.

Open REPORT.html for curves, coefficients via blocks/*/result.json, and validation outcomes. Full fields remain local; compact evidence excludes arrays.
