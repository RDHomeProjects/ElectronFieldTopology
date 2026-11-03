# Full-field diagnostic preparation

Recorded UTC 2026-11-03T23:43:39.658706+00:00; Australia/Melbourne 2026-11-04T10:43:39.658706+11:00.

The [diagnostic plan](../../docs/plans/sf-motion-diagnostics.md) follows the merged
PR52 low-Q assessment and the maintainer-supplied soliton quantization papers.
It authenticates and reuses all six rest and 60 initial/final field states, performs
60 endpoint replays and 70 full-field comparisons, and measures six classical kinetic
matrices. The real 60-case full-field analysis has not run in this environment; its
bulk checkpoints remain on the workstation.

## Measured controls

The solver/renderer/readmission/motion/diagnostic suite passed 62 tests in 19.01 seconds
before addition of the independent compact one-dimensional wave test. The final
11-test diagnostic suite also passes, including the new wave's transport-rate and
acceleration refinement control. The exact final validation record is retained separately.
Tests cover affine sampling on anisotropic meshes; equal-time fits with analytic cubic
centroids; vacuum and exact continuum great-circle wave controls; the kinetic Gram matrix
against direct Hamiltonian energy; corrupted/missing field guards; preservation of every
source file; full endpoint replay; original negative gates; resume identity; and safe
cooperative stop requests. New CSV output uses LF explicitly, including timestamp columns.

The [command validation](command-validation.json) executes an actual preflight plus the
foreground launcher against a generated 9-cubed, t=.2 numerical control. Its two rest
trajectories intentionally fail the original topology acceptance gate. One seed, two cases
and one pair are audited; the endpoint diagnostics replay successfully. This validates
the instrument path, not Q1 soliton physics. The retained [control summary](control-SUMMARY.md),
[case table](control-case-metrics.csv) and [manifest](control-manifest.json) keep the distinction.
The test source is generated deterministically by the automated test fixture and is retained
only under ignored artifacts in preparation; no bulk-field publication is implied.

Linux process-start identity checks and cooperative stop behavior have instrument tests.
The preparation host has isolated PID namespaces, so persistent native background execution
was not validated here. Foreground mode was executed successfully. The wrapper stops a
new background child if its identity cannot be verified and provides foreground fallback.
On an ordinary workstation, start/status/stop/resume use the same PID identity mechanism
as the prior low-Q launcher. No process-group killing or guessed PID signaling is used.

No physical model/action, threshold, normalization, production grid, timestep or renderer
setting is changed. Classical kinetic matrices do not assign electric charge, quantum
spin/statistics or an electron interpretation. The new L41-L43 register entries distinguish
the papers' quantization framework from a classical-emergence hypothesis. Q18 fresh fine
starts/conditioning and additional-Q work remain in the plan after the motion tranche.
AI assisted the implementation and analysis; independent scientific review is not claimed.
