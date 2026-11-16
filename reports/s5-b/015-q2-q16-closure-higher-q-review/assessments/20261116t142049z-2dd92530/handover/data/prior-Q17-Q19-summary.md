# Q17/Q19 coarse-screen assessment

UTC: 2026-11-08T13:31:39.521682+00:00; Australia/Melbourne: 2026-11-09T00:31:39.521682+11:00.

The run took1h9m45.57s. Q2 passed its short moving-field reference. Q17 and Q19 each completed200 stationary preparation iterations without meeting the fixed limits; neither was evolved. These are unresolved preparation outcomes, not failed moving knots or a physical rejection of either Q value.

| Final result | Q17 | Q19 |
|---|---:|---:|
| Relative force /1e-4 limit |11.38×|21.82×|
| Maximum acceleration /1e-3 limit |25.86×|22.20×|
| Rest energy tail |0.027285%|0.057682%|
| Energy decrease |0.415444%|0.506623%|
| Signed Hopf quadrature |-16.754331|-18.741213|

Energy decreased through all retained batches, and neither optimizer reported a stall. Both retain positive cell-continuity diagnostics and Hopf-magnitude errors below5%; no new core-knot identification was performed. The acceleration hotspots are in the interior; much smaller residuals occur in the outer shell. Increasing the box alone is not the leading corrective action. More preparation, optimizer efficiency and coarse-grid/source conditioning remain possible causes; the present evidence cannot separate them.

Q2 passes all seven original criteria at T0.05/0.1/0.2. At T0.2: speed error0.844998%, original shape error0.209623%, maximum observed tail0.0274525%, Hamiltonian drift1.93e-13. All21 recorded tail observations pass. This short control does not close physical-mesh/domain convergence.

All79 full archive payloads were independently downloaded and verified, including23 NPZ files/12 distinct states. Full-field replay agrees across234 numerical comparisons; the maximum absolute difference is below1e-12. Independent energy/current expansions and scalar fits provide additional consistency checks. The original sources, fields, reports, hashes and Release assets are retained.

Recommendation: honor the inexpensive-screen fallback and return to Q2 numerical controls and physical-mesh/domain convergence. Q1 remains parked with its1.563660% speed failure preserved. Keep the Q17/Q19 endpoints for a separately specified stationary-only continuation/finer-grid diagnostic with original-source controls. Require strict stationarity and boosted boundary admission before fresh higher-Q motion.

The package installs the complete report, timestamped tables, three scientific figure pairs, replay scripts and archive receipts, plus aligned requirements, ADR-0019 and generated plan/status/navigation updates. See the installed `reports/s5-b/007-higher-q-motion/assessments/20261108t133139z-d11d12c1/ASSESSMENT.md` for the full analysis and reproduction commands. This summary and the full assessment were AI assisted.
