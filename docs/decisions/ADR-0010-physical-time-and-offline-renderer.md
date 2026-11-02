# ADR-0010 — Physical-time reference and offline renderer

Recorded: 2026-11-02T12:37:39.053069+00:00 UTC; 2026-11-02T23:37:39.053069+11:00 Australia/Melbourne. Status: maintainer-authorized implementation;
bounded numerical verification, not full soliton/electron acceptance.

After merged PR51 the maintainer requested a constrained physical-time solver, followed
by a basic external renderer reading a simple solver-generated wave. The maintainer
specified offline operation and renderer-owned export/presentation settings, with
calculation precision/resolution/steps unaffected.

Implement [the explicit neutral action discretization](../models/SF-physical-time.md)
and [the independent offline renderer](../offline-renderer.md). Keep source theory,
normalization and charged-model deferral unchanged. Use a CPU float64 reference with
verified waves, a manufactured nonlinear source, constraints and energy/flux controls.
Do not use minimizer iterations as time, or silently transfer static lattice stationarity
to a different dynamical discretization.

The renderer profile controls optional display exports; the physics configuration
controls every numerical decision and scientific diagnostic. Export-on/off trajectories
must match. The first GUI is a self-contained offline replay page; interactive 3D
inspection is available through standard VTK/PVD interchange in an external application.

Record the measured [verification and limitations](../../reports/sf-time-renderer-20261102/README.md).
Full stationary Q1/Q2 import/readmission, open boundaries and refined higher-Q free
flight remain subsequent scientific gates. Retain larger-domain Q17 as a provisional
first high-Q benchmark with Q19 comparison. Preserve linked Q18 and return later to
fresh fine starts/conditioning and additional-Q controls, including optional Q20/Q24.
No arbitrary two-hour overall cap is introduced. All results and analysis retain
UTC/Melbourne timestamps. GitHub publication continues from the local workstation.
