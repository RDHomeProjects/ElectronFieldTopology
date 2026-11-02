# Constrained neutral SF physical-time reference

Prepared: 2026-11-02T12:37:39.053069+00:00 UTC; 2026-11-02T23:37:39.053069+11:00 Australia/Melbourne; measured timestamps are retained in
the [control report](../../reports/sf-time-renderer-20261102/README.md).
Continuum model: **SF-relativistic-neutral-v1**. Numerical scheme:
**D4-action-projected-RK4-v1**. CPU float64 reference; no CUDA time-evolution backend.

## Scope and primary equation map

This implements the action and conventions in [the relativistic specification](SF-relativistic.md),
not the dissipative Sobolev minimizer. Jennings [arXiv:1412.8597v2](https://arxiv.org/html/1412.8597v2)
Eq. (2.1) fixes the continuum static normalization. Hietarinta et al.
[arXiv:1108.5551v1](https://arxiv.org/pdf/1108.5551), Sections 1.3, 2 and 3.2,
provide the primary physical-time/boosted-data reference. We derive the explicit
contractions and discrete equations rather than importing the source's compact sign
notation, smoothing or CFL choices. That paper's soliton scattering is not reproduced here.

The metric is +---, x0=t and c=1 in model units; n has three internal components with
n dot n=1 and v=partial_t n tangent to S². K=(32 pi² sqrt(2))^-1 stays fixed. There is
no electromagnetic gauge field or electric-charge observable. Model time is not SI
electron seconds. A periodic plane-wave control has finite box energy and is not an
isolated finite-energy particle on R³. Charged dynamics remains deferred under ADR-0008.

## Explicit discrete action

Spatial indices refer to a uniform Cartesian grid, with separate axis spacings h_i.
Periodic grids have n_i points on side L_i with h_i=L_i/n_i. A singleton axis is
constant and has zero derivative. Fixed boxes have h_i=L_i/(n_i-1), two fixed north-pole
layers and constant north exterior. These walls are reflecting, not absorbing.

Use the fourth-order centered first derivative D_i for the nonlinear terms and its
exact negative transpose for variational divergence. Periodic and zero-exterior D_i
are skew-adjoint under the uniform nodal sum. Define a_i=D_i(n−north) and

```math
M=I+\sum_i(|a_i|^2 I-a_i a_i^T).
```

The sigma spatial energy uses a **positive fourth-order action**, not |D_i n|²:

```math
E_{2,h}=\sum_{x,i}\left(|D_i^+(n-n_\infty)|^2
+\frac{h_i^2}{12}|D_i^{(2)}(n-n_\infty)|^2\right)\Delta V.
```

Its exact interior force is the standard fourth-order Laplacian
(-u_(i+2)+16u_(i+1)−30u_i+16u_(i−1)−u_(i−2))/(12h_i²).
The implemented local positive density averages forward/backward edge energies;
their global sums agree for these boundaries. This avoids the spurious zero of
D4^T D4 at the alternating grid mode, exposed during the reflecting-pulse control.
It is a fourth-order discretization of the same continuum sigma energy, not a new
physical coupling. The fixed two-layer constraints make the action/force transpose
consistent for free nodes at the boundary closure.

With E4,h=sum_(x,i<j)|a_i cross a_j|² DeltaV, the finite-dimensional action is

```math
L_h=K\left[\sum_x v^TMv\,\Delta V-E_{2,h}-E_{4,h}\right].
```

Let C_i=sum_(j!=i)(|a_j|² a_i−(a_i dot a_j)a_j)−|v|²a_i+(v dot a_i)v.
For a test-only force f in units divided by 2K, the nodal equation is

```math
M\dot v=\Delta_h^{(4)}n+\sum_i D_iC_i-\dot Mv+f+\lambda n,
\qquad \dot n=v.
```

Here b_i=D_i v and
Mdot=sum_i[2(a_i dot b_i)I−b_i a_i^T−a_i b_i^T].
For r=Delta4 n+sum D_i C_i−Mdot v+f, solve z=M^-1 r and w=M^-1 n, then

```math
\lambda=\frac{-|v|^2-n\cdot z}{n\cdot w},\qquad \dot v=z+\lambda w.
```

This explicitly enforces n dot vdot=−|v|² and includes Mdot. M is positive even for
off-tangent discrete derivatives. Its invertibility does not establish global causal
well-posedness of every continuum configuration. A finite-variation energy identity
independently checks the full nonlinear periodic and fixed-box equations.

## Time integration and observables

Classical RK4 evaluates a smooth off-manifold extension: stage inputs are normalized
and their velocities projected into the tangent plane. Accepted endpoints receive
the same explicit retraction. The maximum n/v projection corrections are recorded.
This is not an energy minimization or reset; energy drift and temporal order are
measured. There is no artificial damping, smoothing, adaptive accuracy reduction or
overall wall-time cap. The reference validator bounds requested dt/min(h) by .2;
this is a conservative admission guard, not a universal nonlinear stability theorem.
Users choose physical steps and dt; renderer settings never change them.

The recorded `energy` is the discrete Hamiltonian of L_h, used for conservation checks.
`continuum_energy` and preview `energy_density` use the original continuum T00 evaluated
with D4 derivatives. Their totals differ by a fourth-order discretization error and
must not be silently identified at finite h. Centroids and RMS widths use continuum
energy density. In a periodic box those moments depend on the chosen cut and are not
unbounded localization measurements. The positive Hamiltonian density is separately
available as `hamiltonian_density`.

Momentum/energy flux and stress use the continuum currents evaluated on the full grid.
Their local finite-difference values are not an exact discrete Noether flux for the
sigma edge action. The control suite therefore measures regional continuum energy
and momentum balance, including face flux, with spatial/time quadrature refinement.
Fixed walls do no energy work but supply impulse; a reflected pulse reverses momentum.
No absorbing-boundary or isolated long-time stability acceptance follows.

Manufactured forcing is available only in an explicitly named periodic test. It is
derived independently in theta/phi coordinates from
L/K=X+sin²(theta)[(1−X)Y+Z²], with Minkowski X=theta_mu theta^mu,
Y=phi_mu phi^mu, Z=theta_mu phi^mu. Analytic sine jets give the force without calling
the numerical acceleration routine. The recorded work/impulse use trapezoidal time
quadrature, whose error is distinct from RK4's fourth-order field evolution.

## Initial data, checkpoints and motion

Supported data: exact great-circle waves, a compact one-dimensional pulse, uniform
vacuum/geodesic, an explicitly forced 3D manufactured field, fresh unrelaxed Q1/Q2
rational seeds, and authenticated existing static rest/boosted checkpoints. A static
checkpoint requires exact SHA-256, model/Q metadata, float64 unit field and declared
geometry. A rest import does not silently resample or change fixed faces.

An explicitly requested boosted import uses n_beta(x,0)=n0(gamma x_a,x_b) and
v_beta=−gamma beta partial'_a n0. The derivative is taken analytically through the
normalized trilinear static interpolant, rather than assigning a velocity to a
translated image. An independent event-difference test checks that time derivative.
Data outside the original rest box are north. The chosen lab grid/box remain physical
configuration inputs; longitudinal resolution, tails, unit/tangency, boundaries and
initial residuals must be readmitted before accepting a moving soliton experiment.

The old static cell functional and this time solver share a continuum theory, not an
identical discrete energy. An old stationary checkpoint can move initially because it
is not stationary for the new lattice action. Full Q1/Q2 stationarity/refinement and
high-Q free flight are still scientific gates; the short fresh-seed tests do not close them.

Atomic initial/latest/final float64 checkpoints retain n, v, actual step/time, model,
scheme, physical configuration and numerical-source hashes plus UTC/Melbourne dates.
Resume uses a new output directory and requires the exact physical config/source;
it preserves the trajectory bit-for-bit in the controlled test. A renderer profile
can change on resume without changing physics. Resume does not reread the original
static field. If a run fails, latest.npz remains the last complete checkpoint.

## External renderer contract and acceptance

See [the offline renderer specification](../offline-renderer.md). The solver imports
no plotting package. The renderer owns a profile with `export` and `presentation`
sections. The solver reads only export selections; all numerical diagnostics and
scientific checkpoints are governed independently. Profiles can select cases,
calculation resolutions, cadence, exported arrays and coarser preview grids. An
excluded preview never excludes its requested physics calculation.

Export preparation reads full-precision states without modifying them. Preview fields
are derived at the calculation resolution before interpolation to display samples.
Optional Float32 NPZ/VTI/PVD files are explicitly not scientific checkpoints or
topology certificates. Changed frame/palette/camera settings affect only these outputs.
An export-on/off comparison must give identical full-precision final state hashes
and diagnostics; the automated test enforces this. Rendering is performed after the
solver exits and has no solver import or callback.

Predeclared checks: field convergence orders >3.5 (waves/nonlinear spatial RHS), >3.9
(exact temporal geodesic), >3.4 (forced 3D evolution); unit/tangency <1e-10; wave
energy/momentum drift <1e-3; finest regional energy/momentum flux defect <1e-3; refined
reflecting-pulse energy drift <1e-6 with momentum reversal. The coarse flux/wall cases
and all failures are retained in the measured report. These controls establish this
reference implementation's bounded scope, not an electron model or general stability.

SCI-001/003/004, MOD-001/002, NUM-001/002/003 and REP-001/002 receive this implementation
and its recorded controls. BND-001 for open boundaries, full NUM-005 soliton stability,
S6 interactions and S7 quantum/experimental acceptance remain open. AI assisted
derivation, software and reporting; external scientific peer review is not claimed.
