# ADR-0002: independent source-free Fourier propagation

Date: 2026-10-31. Status: adopted for S2 verification. Related: issue 3, SCI-002, NUM-002/003, CI-003.

## Decision

Use a collocated periodic Fourier PSATD solver with exact source-free modal time updates. Initialise once from S1, explicitly project sampled fields onto transverse Fourier modes, and measure that modification. The solver itself has no analytical-field dependency.

## Reasons and alternatives

Yee FDTD with PML is a useful later cross-check, but requires staggered initialisation, PML auxiliary variables and a separate absorption assessment. A simple periodic spectral reference is faster to verify against known waves and conservation identities. It independently propagates data even though each modal update is solved analytically; it does not evaluate the analytical Hopfion at later times.

## Boundaries and limitations

The domain is periodic, not isolated space. Sampled tails are periodically continued and then transverse-projected. This changes the initial problem and must be measured, not hidden. Increasing the box at fixed spacing reduces its central effect; increasing resolution at fixed box eventually reaches that boundary/initialisation error floor.

Full-box energy conservation reflects a closed periodic system, not free-space self-confinement. For a physically useful local check, separately integrate energy change and six-face outward Poynting flux through a central cube. Report diagnostic quadrature errors and actual grid-aligned cube size.

No PML, free-space radiation condition or long-time isolation claim is supplied. S2 validates short-time central evolution and accounting. Longer-time or nonlinear experiments require a new boundary assessment.

## Time and spatial staggering

All E/B components occupy the same nodes and times. Odd grids avoid the ambiguous single Nyquist mode of even real FFT grids. Exact-in-time vacuum updates have no time truncation error for resolved modes. Therefore test time-step subdivision invariance; separately demonstrate second-order convergence of temporal flux quadrature. Do not manufacture a temporal-order claim for an exact update.

## Acceptance established before the experiment

Plane-wave relative/absolute errors <1e-12; global periodic energy/momentum drift <1e-12; endpoint divergence <1e-10; finest central relative field error <0.005; finest interior energy-balance defect <0.01 of initial interior energy, with spatial improvement. Require spatial/domain refinement and time-subdivision agreement. Retain failures and approximation floors.
