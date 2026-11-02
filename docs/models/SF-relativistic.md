# Neutral relativistic Skyrme–Faddeev reference

Specified: 2026-11-02T08:48:53.481631+00:00 UTC; 2026-11-02T19:48:53.481631+11:00 Australia/Melbourne. Model ID: **SF-relativistic-neutral-v1**.
This is the explicit relativistic completion of the fixed-coefficient static reference,
not the deferred charged model in [ADR-0008](../decisions/ADR-0008-charged-model-audit.md).
The implementation delivered here evaluates its action/stress and static admission
diagnostics. **No nonlinear physical-time evolution solver is implemented here.**

## Sources and conventions

- Jennings, [arXiv:1412.8597v2](https://arxiv.org/html/1412.8597v2),
  Section 2 Eq. (2.1): precise static energy and normalization. Our
  [static equation map](SF-J2015-static.md) remains authoritative for existing fields.
- Hietarinta, Palmu, Jäykkä and Pakkanen,
  [arXiv:1108.5551v1](https://arxiv.org/pdf/1108.5551v1), 29 August 2011,
  Section 1.3 Eq. (3), Section 2, Section 3.2: Lorentzian unit-vector theory,
  constrained physical-time evolution, relaxed rest fields followed by Lorentz boosts,
  and boundary issues. The displayed Eq. (3) uses a compact sign/contraction notation.
  We specify the metric and every contraction below and derive the completion from
  Jennings' positive static energy; we do not silently import its shorthand signs,
  overall normalization, smoothing or reported CFL numbers.

Metric is eta=diag(+1,-1,-1,-1), right-handed Cartesian coordinates; x0=t and c=1
in dimensionless model units. A conversion to SI would need independently specified
length and energy scales; no seconds of simulated electron motion or electron mass
are inferred. The field n is a scalar under spacetime transformations and a unit
three-vector in an internal target sphere. There is no electromagnetic gauge field
and no imposed electric-charge interpretation of Hopf degree.

Let a_i=partial_i n, v=partial_t n, and H_mu_nu=n dot
(partial_mu n cross partial_nu n). For unit n and tangent derivatives,
|partial_mu n cross partial_nu n|²=H_mu_nu². Define

```math
S=K\int\left[\partial_\mu n\cdot\partial^\mu n
-\frac12 H_{\mu\nu}H^{\mu\nu}\right]d^4x,
\qquad K=(32\pi^2\sqrt2)^{-1},\quad n\cdot n=1.
```

Equivalently, writing V=sum_i|a_i|²+sum_(i<j)|a_i cross a_j|²,

```math
\mathcal L=K\left[|v|^2+\sum_i|v\times a_i|^2-V\right]
=K[v^TMv-V],\qquad
M=I+\sum_i(|a_i|^2I-a_i a_i^T).
```

At v=0, -L is exactly the established static density. The sigma term supplies a
nondegenerate vacuum kinetic matrix M=I. For a rest jet its two tangent eigenvalues
are 1+lambda_min/max of sum_i a_i a_i^T restricted to the tangent plane, hence positive.
This pointwise rest property does not prove hyperbolicity for arbitrary moving fields
or nonlinear global well-posedness. Those remain distinct solver/model gates.

## Equations and stress-energy derivation

Set

```math
B_i=a_i+\sum_{j\ne i}(|a_j|^2a_i-(a_i\cdot a_j)a_j)
-|v|^2a_i+(v\cdot a_i)v.
```

The currents are p=partial L/partial v=2K Mv and
q_i=partial L/partial a_i=-2K B_i. For tangent variations, the constrained
Euler–Lagrange equation is

```math
(I-nn^T)\left[\partial_t(Mv)-\sum_i\partial_i B_i\right]=0,
\qquad n\cdot v=0,\quad n\cdot\partial_t v=-|v|^2.
```

A physical-time solver must differentiate M consistently and enforce the acceleration
constraint. Dropping partial_t M, reusing the dissipative Sobolev preconditioner as a
physical inertial operator, or applying an unrelated nodal inverse to the static cell
gradient does not implement this equation. The initial solver must derive a consistent
discrete action or independently verify its continuum discretization.

The symmetric stress tensor is obtained from
T^(mu nu)=(partial L/partial(partial_mu n)) dot partial^nu n - eta^(mu nu)L.
Thus

```math
T^{00}=K[v^TMv+V],\qquad T^{0i}=-p\cdot a_i,
\qquad T^{ij}=-q_i\cdot a_j+\delta_{ij}\mathcal L.
```

At rest, let b_i=B_i evaluated at v=0. Then
Tij=K[2 b_i dot a_j-delta_ij V]. Its integrated trace is E4-E2, a useful
independent sign/factor check against the existing dilation test. Nonzero integrated
anisotropic stresses can remain even when this trace is small. Local conservation
partial_mu T^(mu nu)=0 requires an on-shell solution; an arbitrary static snapshot
does not acquire conservation merely through a coordinate boost.

## Boosted data and what the admission run measures

For a formally static n0 and boost along axis a with speed beta,
n_beta(x,t)=n0(x'_a=gamma(x_a-beta t),x'_b=x_b). At t=0 the full data are
n_beta(x,0)=n0(gamma x_a,x_b), v_beta=-gamma beta partial'_a n0, and
partial_a n_beta=gamma partial'_a n0. This includes contraction and time derivative.
It describes exact uniform translation only when n0 is an exact static solution on
the relevant unbounded domain. Our numerical endpoints are approximations.

The admission analysis integrates over the **Lorentz-contracted original rest box**,
using d³x=d³x'/gamma. If Sij=integral Tij_rest d³x', then

```math
E_\beta=\gamma(E_0+\beta^2S_{aa}),\quad
P_a=\gamma\beta(E_0+S_{aa}),\quad P_b=\beta S_{ab}\ (b\ne a).
```

These are tensor identities, also checked against direct boosted derivative densities;
they are not independently evolved trajectories. Familiar particle relations follow
when integrated stress vanishes. Finite-box stress, tails and imperfect stationarity
must be measured rather than erased by forcing E=gamma E0 in the code.

The run computes all 31 published endpoints without altering them. For six selected
endpoints (Q1, Q2, Q22 control and the finest Q17/Q18-baseline/Q19), four deterministic
smooth tangent nodal directions receive a geodesic perturbation n(epsilon)=
cos(epsilon|w|)n+epsilon sinc(epsilon|w|/pi)w. Fixed faces stay fixed. Three epsilon
values estimate directional second energy variation. The kinetic norm is 2K integral
delta n^T M delta n, using the variation of the normalized trilinear interpolant, so
the quotient has the formal squared-frequency normalization. At a nonstationary field
it is not an eigenfrequency. Four positive trial quotients do not prove full stability;
negative/epsilon-dependent values are retained for diagnosis, not suppressed.

## Numerical scope and predeclared checks

The independent Python integrator uses exactly the existing normalized-trilinear
field and 2x2x2 cell Gauss rule, processed in small slabs. It does not renormalize,
resample or silently repair checkpoint fields. Open-hemisphere cells, unit norm,
fixed faces, source config, model, Q label and file hash must agree.

Software checks: match published cell energy within 1e-9 relative; integrated stress
trace and direct-versus-tensor boost within 1e-10 relative; kinetic minimum at least
1-1e-10. These are consistency checks of identical quadrature and algebra, not physical
acceptance thresholds. Small controls additionally compare finite action derivatives,
independent Minkowski two-form contraction, generic nonzero-time-jet covariance,
great-circle light-speed waves, native static cell energy and vacuum kinetic limits.

Scientific outputs are numerical values/trends, not pass gates: integrated stress,
boost defects at beta=0,.1,.3,.5,.75,.9 in all three axes, localization/tail estimates,
conditioning and directional curvature at epsilon=.002,.001,.0005. Preserve existing
mesh/domain comparisons; no broad nonlinear stability conclusion is automated.

## Following physical-time implementation gates

| Gate | Required evidence before advancing |
|---|---|
| Discrete equations | Explicit action/constraint mapping; consistent mass operator and spatial force; no minimizer time |
| Simple evolution | Vacuum, small-amplitude waves and exact continuum great-circle traveling wave; at least three h and dt; measured expected order |
| Numerical control | Unit/tangency defects below 1e-10; energy and momentum balance below 1e-3 relative and decreasing under refinement; no unexplained smoothing or energy reset |
| Boundary | Unbounded analytic comparison or reflection/flux measurement; fixed-box and larger-box comparison over the same observation window |
| Rest soliton | Low-Q controls before a higher-Q field; distinguish residual-driven motion from instabilities; localization, topology and radiation diagnostics |
| Free flight | Event-consistent boosted data; numerical trajectory versus analytic boost of the rest solution; E/P and centroid-speed defects below 1% and shrinking with refinement |
| Perturbations | Multiple controlled seeds/amplitudes plus temporal/spatial/domain convergence; four trial static directions are insufficient |

The 1e-3/1% budgets are proposed numerical accuracy targets for a new implementation,
not evidence achieved here; order and finite-tail errors must also improve. Start
actual free flight at beta=.1 and .3; .5/.75/.9 are conditional later tests. A moving
lab grid needs h_parallel <= h_rest/gamma to preserve rest-direction resolution.
No high-speed instability claim follows merely from changing inertial frame. Box size
and observation time must leave a verified radiation/boundary margin; no universal
simulation duration follows from an optimization runtime. A fixed-face static field
does not validate absorbing boundaries.

## Requirement and decision mapping

SCI-001/003/004, MOD-001/002, REL-001/002, NUM-001/002/003/005 and REP-001/002 gain a
specified model and executable admission instrument. NUM-002/003 for physical-time
evolution remain open; no S6 interaction or S7 quantum gate is released. See
[ADR-0009](../decisions/ADR-0009-neutral-dynamics-admission.md) and the
[workstation plan](../plans/sf-dynamics-admission.md). AI assisted derivation and code;
independent scientific review remains necessary before stronger model claims.
