# S5-B-006: fixed-layer readmission and focused overnight motion

Prepared: UTC 2026-11-04T14:15:15.924068+00:00; Australia/Melbourne 2026-11-05T01:15:15.924068+11:00.
Model: SF-relativistic-neutral-v1; +--- metric; c=1; dimensionless model time.
Scheme: unchanged D4-action-projected-RK4-v1, CPU float64.
Requirements: NUM-002/003, BND-001, REL-002, REP-001/002 and VIS-001.

## Scope and source mapping

[The physical-time action and equation map](SF-physical-time.md), including its
Jennings and Hietarinta primary sources, remain unchanged. This tranche implements
[ADR-0013](../decisions/ADR-0013-conditional-cubic-initialization.md). It preserves
the original `sf_time.py`, `sf_time_initial.py`, `sf_time_run.py` and all prior
scientific records byte-for-byte. There is no new coupling, damping, artificial
smoothing, D4-fitted velocity, GPU evolution backend or relaxed acceptance gate.

The opt-in `sf_focused_motion.py` driver creates a new constrained initial state
and calls the existing physical-time runner through its exact checkpoint
continuation interface. A new, explicitly named external-initializer kind is used
only with an authenticated step-zero checkpoint. Physical configuration binds
the reconstruction method, admitted state digest, external numerical source digest
and input fingerprint. The old runner separately binds its original numerical
source map. Reproduction uses this driver; the old importer is not extended to
silently accept a new initializer.

## Boundary and event readmission

For each raw trilinear/cubic construction use exactly the existing `retract`:
normalize n, project v tangent to n, and set both fixed lab layers to north/zero.
Apply it to both methods. Record raw/admitted state hashes and n/v correction
maxima and RMS, including separate maxima on free nodes, with pre/post D4
transport measurements for the trajectory inputs. The old raw trilinear state
must replay bit-exact against the authenticated original initial checkpoint.

A new matched trilinear trajectory includes the common projection and can differ
from an earlier trajectory at roundoff; it is not relabelled as a bit-exact replay
of the earlier evolved state. Free-node corrections must remain below 1e-12,
unit/tangency below 1e-10, and fixed layers must be exactly north/zero. The
projection is an explicit constrained finite-box initialization, not a theorem
that boosted continuum data satisfy reflecting walls.

Independent controls include the old three-input-mesh interpolation tests and
an adversarial n81/L16 field with only two north layers and one interior
perturbation. Test beta=.1/.3 and x/z; expose the raw cubic lab-mask leakage,
then enforce the exact fixed layers. A separately evaluated time-event difference
checks the constrained candidate rate at free and held nodes to <1e-8. No
derivative is replaced with a D4 fit.

Before any trajectory, readmit every retained Q1/Q2 rest grid (n81/L16,
n101/L16, n101/L20), both directions, beta=.1/.3, and both methods: 48 data
admission records. A failed hard constraint/control stops dependent evolution;
all raw failures and corrections are retained. Existing tail/shape/momentum
failures do not become passes merely because input constraints are satisfied.

## Predeclared overnight tranche

Use the retained stationary n101/L16 Q1 and Q2 fields, beta=.3 along x/z, and
trilinear/cubic with the same projector: **eight physical arms**. Transverse
spacing is .16; the longitudinal lab count follows the original
2 ceil((n-1) gamma / 2)+1 rule. The fixed lab side is L=16.

The maintainer requested a long overnight execution. The observation window is
therefore extended to **T=3** at unchanged dt=.01 (300 RK4 steps per arm), with
sealed checkpoints and assessments at **T=1,2,3**. T=1 retains the prior comparison
window; T=2,3 measure accumulated discrepancy. This adds observation time within
the eight-arm method experiment; it does not automatically start additional
meshes, domains, time steps or Q values before that experiment is assessed.

Past matching original T=1 runs took 1558–1628 seconds per arm on zbook.
Two methods times three model-time units gives a nominal **38076 seconds
(10.58 hours)**, plus admission/IO and machine-load variation. There is no
wall-time cap, deliberate idle work, padding or automatic accuracy reduction.
A finite-box long-time result can be wall-sensitive. Record the 99%-energy-radius
geometric light-cone indicator, tails and flux-related diagnostics; a clear
radius indicator does not prove all exterior tails are causally irrelevant.

## Evolution, metrics and renderer separation

The RK4 and action kernels are the existing code. Original motion thresholds are
read from the authenticated old campaign, not copied into adjustable new gates.
At every milestone report the original full-grid trilinear-reference shape,
energy/momentum drift, speed, topology quadrature, tail, unit and tangency checks.
These common-reference gates remain separate from a restricted-phase,
known-comoving comparison with the method's own admitted initial field.
The sampled comoving core is identical between methods at each matched time,
but shrinks across times; do not infer time convergence from that moving mask.

Record direct full-state differences between methods at identical milestone
times. No centroid, velocity, spatial rotation or deformation is fitted away.
No isolated-motion, inertia convergence or quantum acceptance follows from a
bounded pass. Physical third-mesh/domain and temporal refinement decisions
remain after the method assessment.

Display settings are renderer-owned. The economy profile exports field and
energy density on a 25-cubed Float32 grid every 25 solver steps, plus segment
endpoints. Physics/checkpoints remain full-resolution float64, with diagnostics
every 5 steps and numerical recovery checkpoints every 25 steps. Export-on/off
tests must leave scientific endpoint hashes identical. The external renderer
runs after calculation; per-case PVD collects segment frames for ParaView.
Use energy_density and change Outline to Volume.

## Stop, recovery and provenance

Each T=1/2/3 segment gets a fresh attempt directory. Source/config hashes and
full initial/latest/final checkpoints are retained. Graceful stop uses the
existing runner's independently complete latest checkpoint; up to 24 steps
after that checkpoint may be recomputed. Truncate combined histories at the
next attempt's actual resume step, including after an unclean stop. Never
combine observations beyond the recovered state with the resumed trajectory.

Resume verifies original inputs, numerical source/config identity and sealed
checkpoint hashes. A hard kill can leave an unsealed newest checkpoint; the
existing model/code/config, float64, shape, CRC and constraint checks still
apply on resume. This case is not described as a previously externally sealed
hash verification. Partial attempts and leftover temporary files are preserved.

All timestamps use UTC and Australia/Melbourne. Hardware/environment and Git
provenance are recorded by the unchanged attempt runner; the campaign binds its
external initialization version. Software/synthetic-fixture results do not count
as native Q1/Q2 motion evidence. Tests using unresolved coarse fields preserve
their unresolved labels and negative gates; no research tolerance is weakened.

## Retention and publication

Compact JSON evidence and summaries go in a canonical S5-B-006 run record.
Full fields, recovery checkpoints and previews remain in that run's local
artifacts until a one-root GitHub Release archive is uploaded and independently
download-verified with the existing archive engine. Register its catalog in the
same PR before merge. Do not archive the whole retained low-Q cache again.
No local source data are deleted by this handover.

After assessment, decide temporal refinement, third physical mesh and larger
matched-spacing boxes, then retain the registered Q17/Q19, Q18 fresh-start and
additional-Q sequence. AI assisted implementation and reporting; no external
scientific peer review or electron-model acceptance is claimed.

Repository-only execution, after committing code and authenticating the source:

```bash
uv sync --frozen --all-groups --python 3.12.14
uv run --frozen python -m electron_field_topology.sf_focused_local start --source /path/to/retained/lowq-campaign
uv run --frozen python -m electron_field_topology.sf_focused_local status
```
