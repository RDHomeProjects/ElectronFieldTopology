# Stationary low-Q readmission and bounded physical-time motion

Prepared: UTC 2026-11-02T15:29:15.448567+00:00; Australia/Melbourne 2026-11-03T02:29:15.448567+11:00.

## Question and scope

Can a stationary Q1/Q2 field for the physical-time lattice action persist at rest
and follow a controlled Lorentz boost as h, dt and box size are varied? This is the
next gate after [the solver controls](../models/SF-physical-time.md), before provisional
larger-domain Q17 free flight and Q19 comparison. Q18 retains its linked alternative;
fresh fine starts, conditioning and additional Q values (including optional Q20/Q24)
remain later tasks. Charged dynamics and electron acceptance stay deferred.

The action, +--- metric, c=1 model units, fixed K and event-consistent boost are
unchanged. Jennings/Sutcliffe supply the static/rational-map context; Hietarinta et al.
1108.5551v1 Sections 1.3, 2, 3.2 supply prior-art physical-time/boosted-field context.
The [explicit equations](../models/SF-relativistic.md) and discrete action remain
authoritative. These runs are not new-knowledge or stability certificates.

## Readmission is distinct from evolution

`sf_readmission.py` differentiates the **same discrete Hamiltonian** as `sf_time.py`.
Its Euclidean nodal gradient is -2 K DeltaV times the static nodal force. Normalization
projects that gradient to the S² tangent plane; the two fixed layers have zero gradient.
An independent finite-variation test compares this gradient against the physical-time
Hamiltonian, and the tangent M a identity against the dynamics.

Relaxation uses projected Sobolev nonlinear conjugate gradients with Armijo decrease.
The positive preconditioner is (-Delta2+.25)^-1 on free nodes with Dirichlet faces,
implemented by DST-I; tangent projection before/after inversion preserves positivity.
It is an optimizer only: it never appears in the physical-time acceleration. Retraction
is n -> n/|n|. Each trial nodal displacement is limited by .15 and one-quarter of the
current open-cell-hemisphere margin. No topology label is fixed by imposing a knot curve.

Restartable 200-iteration batches continue until the measured gates pass, the
topology diagnostic fails, Armijo search stalls, or three complete passes have relative
energy change below 1e-10 while residuals still fail. There is **no total wall-time or
pass-count cap**. Stagnation is an unresolved result, never automatic stationarity.
Optimizer restart discards conjugate-gradient memory; no bit-exact optimization-path
claim is made. Physical-time checkpoint continuation retains its exact-source/config
requirements. The latest complete state and all measured scalar histories are retained.

Default starting fields are self-contained fresh axial Q1/Q2 rational seeds, scale1.6,
compact seed cutoff .4 L. Optional `source_checkpoint` in a seed accepts a retained
static checkpoint `{path, sha256}` with matching Q, float64 geometry and fixed faces.
It is assessed then relaxed to the new lattice action; old cell-functional stationarity
is not transferred. No missing historical file is required for the default run.

Readmission targets, fixed before workstation production: relative tangent-force L2
versus full sigma-force L2 <=1e-3; maximum physical rest acceleration <=1e-2; Hopf
quadrature magnitude within5% of Q; positive minimum corner-cone margin; unit defect
<1e-10. The Fourier Coulomb integral is approximate, not an integer certificate.
All failed starts/final diagnostics remain in the ledger. An unadmitted candidate gets
rest diagnostics but its boosts are skipped, rather than mislabeled stationary motion.

## Default controlled matrix

For each Q1/Q2:

| Study member | Nodes | Side L | Rest spacing | Role |
|---|---:|---:|---:|---|
| Base |81³|16|.2|First spatial level|
| Fine |101³|16|.16|Same box, finer grid|
| Domain |101³|20|.2|Larger box at base spacing|

Each stationary member gets beta0 plus beta.1/.3 along x/z; each has dt.02/.01
through t=1 in dimensionless model units: up to60 time evolutions. A moving axis is
refined to the smallest odd count preserving h_parallel<=h_rest/gamma. Thus the lab
calculation is slightly anisotropic, with independently calibrated anisotropic Hopf
quadrature. The box is fixed north outside; it is **reflecting**, not absorbing.

Physical-time integration uses the established nonlinear projected RK4, with no
relaxation, smoothing or forced particle energy. All physical settings are separate
from the renderer profile. Every5 physical steps record diagnostics; every10 retain
an atomic checkpoint. Profile case/grid/cadence/field selections affect only display
exports. All other numerical settings and scientific checkpoints stay unchanged.

## Recorded motion diagnostics and predeclared targets

Full-grid histories measure discrete Hamiltonian drift and continuum momentum/energy,
centroid velocity, constraints and widths. Endpoint diagnostics include normalized
field L2 difference from n0(gamma(x_a-beta t),x_b), approximate Hopf integral, corner
margin, 99%-energy radius and energy fraction in an outer shell of width2.

Case targets: energy drift<=1e-3; momentum change/E0<=1e-3; unit/tangency<1e-10;
field error<=1%; centroid-speed vector error<=1% of nonzero beta (rest absolute speed
<=1e-3); Hopf error<=5%; shell energy<=1e-3; and positive initial 99%-energy light-cone
clearance after the observation window. That radius/tail check is a bounded diagnostic,
not a rigorous no-boundary-influence theorem: nonzero exterior tails remain.

The lab t0 continuum energy/momentum are compared separately with particle expectations
gamma E0/gamma beta E0 (1% target) and the finite-box stress-corrected tensor relations.
Initial rest integrated stress is retained; particle relations are never imposed.
Interpolation and different lab sampling prevent demanding algebraic equality at
machine precision for independently sampled finite-grid fields.

`comparisons.json` pairs temporal, spatial and matched-spacing domain results at the
same observation time. Two levels supply controlled differences, **not a measured
order**. Case gates alone do not release global motion acceptance: source-state
differences, tail/stress trends and field convergence need scientific review. An
optional `extended.json` adds a third h and dt plus a longer window for that review;
it is deliberately not an automatic release of Q17/Q19 or arbitrary-speed testing.

## Local operation and analysis records

The handoff INSTALL.sh creates a separate checkout and stages a cumulative patch,
including the verified time-solver/renderer baseline if it has not yet been published.
Run tests and commit locally, then RUN.sh start. It returns immediately and records
a background PID plus process-start identity. RUN.sh status prints timestamps, paths,
ledger state and recent log entries. RUN.sh stop requests checkpoint stop; wait until
status says stopped, then RUN.sh resume continues the same campaign/config/source.
Changed physical config or numerical source requires a new output, preserving old data.
Linux PID/start/boot/namespace identity checks prevent signalling a reused PID or a process from another boot/namespace.

`SUMMARY.md`, `campaign.json`, `comparisons.json` and `evidence.zip` are the review
entry points. Compact evidence includes manifests/configs, readmission histories,
physical-time histories and assessments with hashes; full fields/previews stay local.
A complete runner status means processing finished, not scientific gates passed.
After stopping, RUN.sh render makes an offline HTML/GIF/PNG of a completed case.
Its output lists the ParaView PVD too: choose energy_density and **Outline -> Volume**,
then Play. A rendered moving image never overrides failed scientific gates.

Requirement mapping: SCI-001/003/004, MOD-001/002, NUM-001/002/003/005,
REL-001/002, REP-001/002 and VIS-001..004. No new field/coupling or physical charge
is introduced. AI assisted implementation/analysis; independent scientific review
is not claimed.

## Assessed production and next diagnostic (UTC 2026-11-03T23:43:39.658706+00:00; Melbourne 2026-11-04T10:43:39.658706+11:00)

PR52 publishes the [60-case assessment](../../reports/sf-motion/lowq-motion-2026-11-03T104629-568611+1100-30672/ASSESSMENT.md). Six bounded cases pass;
global motion acceptance remains unreleased. Production is complete. Follow the
[full-field diagnostic plan](sf-motion-diagnostics.md) before additional production
refinement. Classical kinetic metrics now prepare the separately conditional quantum
method route; they do not supply spin/electric-charge assignments.
