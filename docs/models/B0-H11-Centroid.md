# B0-H11-Centroid: energy moments and localisation

S3-B, [issue 8](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/8). Requirements REL-003, NUM-003/004 (localisation only), SCI-003/004, BND-001 and REP-001/002. The source-free analytical field and passive observer conventions remain [B0-H11](B0-H11.md) and [B0-H11-Lorentz](B0-H11-Lorentz.md).

## Primary source mapping

- [Bliokh and Nori, arXiv:1112.5618v2](https://arxiv.org/html/1112.5618v2), Eq. (1) and surrounding angular-momentum-tensor discussion: energy centroid, boost charge and centroid velocity. Its subsequent paraxial examples do not supply coefficients for our Hopfion.
- [Bliokh, arXiv:2412.11115v1](https://arxiv.org/html/2412.11115v1), Eqs. (7)-(9): energy weighting and conserved boost momentum. Its scalar/fixed-polarisation examples are contextual; the Maxwell derivation below handles the full vector field.
- [Hoyos et al., arXiv:1502.01382v2](https://arxiv.org/abs/1502.01382v2), Appendix A, (A.5)-(A.8): stress-energy components, conservation and trace. We explicitly raise both indices: T^(0i)=+(E cross B)i, whereas the covariant component T_(0i) has the opposite sign. Their (A.11)-(A.14) charge ordering uses the opposite sign from our M below. Their p cross x must not replace our x cross p.
- [Feynman II-27](https://www.feynmanlectures.caltech.edu/II_27.html), (27.5), (27.14)-(27.15): local energy balance and field energy/Poynting densities.

The cited passages and equations were inspected before numerical implementation. Width and initial J references below are repository derivations from the already verified Cartesian fields, not coefficients copied from paraxial models.

## Definitions and Maxwell derivation

c=epsilon_0=mu_0=l0=1; unit field amplitude; eta=diag(-1,1,1,1). No potential/gauge is needed. All integrals defining conserved quantities are over unbounded ordinary space, assuming finite moments and vanishing weighted surface terms.

```text
T00 = u = (E²+B²)/2; T0i = Ti0 = Si = (E cross B)i
Tij = u deltaij - Ei Ej - Bi Bj
partial_mu T^(mu nu)=0; -T00 + sum_i Tii=0
U = integral u; P = integral S; R = integral r u / U
Cij = integral (ri-Ri)(rj-Rj)u / U
sigma² = trace C; RMS radius = sqrt(sigma²)
I = integral |r|²u; q = integral r.S
J_about_a = integral (r-a) cross S = J_about_0 - a cross P
M^(0i) = t Pi - U Ri; M^(ij) = epsilon_ijk Jk
```

Integrating continuity with weights 1 and r gives constant U and d(UR)/dt=P. Momentum conservation and the traceless stress give I'=2q and q'=integral trace(Tij)=U, hence I''=2U. With w=P/U:

```text
sigma²(t) = sigma²(0) + 2(q(0)/U - R(0).w)t + (1-|w|²)t²
```

This controls spreading about the moving energy centroid. In a zero-momentum frame the quadratic coefficient is 1. A stationary centroid therefore need not imply fixed spatial width.

For a passive boost, P4'=Lambda P4 and M'=Lambda M Lambda^T; at target time t', R'=(t'P'-M'^(0i))/U'. This is an equal-time field integral, not generally the Lorentz image of the source centroid worldline. The tensor is evaluated about the declared coordinate origin. J about the energy centroid is separately integrated and compared with J0-R cross P; it is classical angular momentum, not a quantum-spin measurement.

## Independent Hopfion references

At t=0, u=16/(1+r²)^4 and direct Cartesian reduction gives:

```text
S/u = (-2(xz-y), -2(x+yz), x²+y²-z²-1)/(1+r²)
(r cross S)z = -32(x²+y²)/(1+r²)^5
```

Angular integration leaves Jz=-(256 pi/3) integral_0^infinity r^4/(1+r²)^5 dr = -pi² (the radial integral is 3 pi/256); Jx=Jy=0 by parity. U=2 pi², P=(0,0,-pi²), R(0)=0, I(0)/U=1, q(0)=0. Therefore R=(0,0,-t/2), I/U=1+t² and sigma²=1+3t²/4. A beta-function radial integral supplies I(0), independently of 3D quadrature. Our source M has only M12=-pi², M21=+pi² nonzero. Transform this fixed tensor for boost references without fitting numerically measured centroids.

For v=(.6,0,0), the predicted equal-time centroid at t'=0 is (0,-.3,0). Boosting the source centroid's origin event gives zero, providing a deliberately incorrect reference. For v=(0,0,-.5), P'=0: use this frame to measure spreading independently of bulk motion.

A separate scalar reduction, used only as a pointwise test reference, is:

```text
u(r,t)=16(r²+t²-2tz+1)² / ((r²-t²+1)²+4t²)^3
```

A bounded Cartesian-grid search followed by local refinement reports an energy-density maximum candidate. It does not prove a global maximum, establish a photon path, or represent cycle-averaged detector intensity. Its location is compared with the integral energy centroid explicitly.

## Integration and acceptance set before experiments

Use angular Gauss-Legendre mu and 2n azimuthal nodes. For all-space moments, map s in (0,1) to r=s/(1-s), dr/ds=1/(1-s)^2 with Gauss-Legendre radial nodes. This samples arbitrarily large radii without imposing an outer boundary; it still has finite quadrature error. Angular orders 24/40/64 are compared. An initial run using the same radial orders failed the predeclared tolerance for the t=2 transverse boost. Independent radial-only versus angular-only refinement isolated the radial error: centroid error 6.03e-6 at (radial,angular)=(64,64), 6.24e-9 at (96,64), and 6.03e-6 at (64,96). The standard configuration therefore uses twice as many radial nodes: 48/80/128. The original thresholds are unchanged; the original 1x-radial configuration and a clean-code rerun are retained as failed-resolution evidence. This is a documented accuracy refinement, not a change in physical assumptions. Independent finite spheres of radii 4/8/12 at order 64 retain tail bias separately. No tail is filled with an assumed answer.

Default source/observer times 0,1,2; boosts 0, (.6,0,0), (.2,-.3,.4), (0,0,-.5). Exact criteria from issue 8: local stress-tensor covariance/origin identities <1e-12; source R and sigma² errors <1e-6; direct boosted centroid errors <1e-6; measured centroid velocity vs P/U <1e-6; angular tensor error divided by reference U <1e-6; finest quadrature increments of centroid and sigma² <1e-6; zero-momentum-frame quadratic growth relative error <1e-5. Require finite-sphere centroid/width errors to reduce overall with increasing radius, without claiming their cutoff errors meet all-space tolerances.

Supplementary bounded controls: density-peak grids 17/25/33 on [-4,4]^3, four top starts per grid, box-constrained local refinement; finest two peak positions differ by <1e-4 and peak-centroid separation at source t=2 exceeds .2. The x-boost centroid-worldline negative reference must miss by >.1, and constant central width must fail by >1 between source t=0 and t=2. Contained energies use radius-2 spheres at the origin and predicted energy centroid, for source and zero-momentum frames, normalised to exact transformed all-space U; retain orders 24/40/64.

These are bounded verification criteria, not rigorous global error estimates, physical measurement uncertainties or evidence of a stable particle. Raw outcomes are written before any experiment failure exit. No tolerance is relaxed to meet an attractive physical result.

## Reproduction

```bash
uv sync --frozen --all-groups
uv run --frozen pytest -q
python scripts/check_docs.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --frozen python -m electron_field_topology.localisation_benchmark --config experiments/configs/hopfion-s3b.json --output artifacts/s3b-local
```

Use an empty/new output directory. See [workflow](../../.github/workflows/localisation.yml) and [report](../../reports/s3-b/README.md). CPU only, bounded cases, read-only workflow token, 10-minute timeout, no scheduled sweeps. No new dependency or physical dynamics is introduced.
