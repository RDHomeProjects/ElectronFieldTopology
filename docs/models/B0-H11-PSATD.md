# B0-H11-PSATD: independent periodic Maxwell initial-value benchmark

Status: implemented S2 reference. Physics remains source-free Maxwell; the numerical domain and projected initial condition differ from infinite-space B0-H11.

## Equation sources and conventions

Godfrey, Vay and Haber, *Numerical stability analysis of the Pseudo-Spectral Analytical Time-Domain PIC algorithm*, arXiv:1305.7375v2, Section 2, PDF page 3, Eqs. (1)-(2):
[versioned primary PDF](https://arxiv.org/pdf/1305.7375v2).
Their wave-vector sign is reversed (stated below those equations) relative to the inverse transform used here. Set current J=0 and convert the signs. The implementation is derived from Maxwell's equations rather than copied software.

With the numpy/scipy forward FFT exp(-ikx), inverse exp(+ikx), c=1:

```text
dE_hat/dt = +i k cross B_hat
dB_hat/dt = -i k cross E_hat
f_L = k (k dot f) / |k|^2
f_T = f - f_L
E_hat_new = cos(|k|dt) E_hat + i sin(|k|dt)/|k| (k cross B_hat)
            + [1-cos(|k|dt)] E_L
B_hat_new = cos(|k|dt) B_hat - i sin(|k|dt)/|k| (k cross E_hat)
            + [1-cos(|k|dt)] B_L
```

At k=0 the mean is unchanged. The longitudinal terms also preserve unprojected initial longitudinal fields; the source-free benchmark removes them once at initialisation. Implement sin(k dt)/k as dt*sinc(k dt/pi) for the continuous zero limit. Both updates use the old fields, not an already updated component.

This exact vacuum update is the modal solution of a numerical Fourier representation, not a query of the known Hopfion formula. No currents, particles, beams or PIC instability claims from the source paper are reproduced.

## Domain and initial data

Odd N^3, collocated real fields, spacing dx=2L/N; nodes (j-floor(N/2))*dx, period 2L. k=2 pi fftfreq(N,dx). No gauge potential or spacetime tensor is used. Units and amplitude follow [B0-H11](B0-H11.md).

At t=0 only: sample E/B from S1, FFT, remove longitudinal modes for source-free constraints. Record global relative L2 projection correction and central initial discrepancy. The periodic continuation plus projection can alter the core. Comparing to infinite-space analytical fields has this finite-box error in addition to spatial sampling error.

## Independent checks and diagnostics

Periodic plane wave E_y=B_z=cos(x-t) tests propagation direction, amplitude and phase. A constant zero mode tests mean handling; a longitudinal wave tests explicit projection; forward/backward and subdivided steps test the propagator independently of Hopfion data.

Parseval yields periodic energy; real-space E cross B gives periodic momentum. Fourier divergence must remain small. None establishes self-binding.

Interior cube energy uses nodal trapezoidal quadrature of (E2+B2)/2. Flux uses six outward-oriented surface integrals of E cross B, and trapezoidal time integration. Compare delta U plus integrated flux. Cube half extent is the nearest node to requested extent, with ties rounded upward; actual extent is reported. Full-domain normalisation does not hide relative error in the transported energy: both normalisations are retained.

## Studies and limitations

Spatial: N=25,49,73 at L=6.1. Domain: dx=.2 and N=41,61,81 (L=4.1,6.1,8.1). Duration .75. Refinement is judged inside a central cube, not across the non-smooth periodic seam.

Time subdivision: 1,2,4,8 modal updates to the same endpoint. Flux time quadrature: 8,16,32 intervals at fixed grid. For an exact modal update, changes in flux integration can converge even when field-time error is only round-off.

Nine bounded CPU cases, no topology search or parameter fitting. No absorption or infinite-space boundary condition; no stability theorem, boost, charge-emergence or quantum result. See [ADR-0002](../decisions/ADR-0002-s2-solver.md).
