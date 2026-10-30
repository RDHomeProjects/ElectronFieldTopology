# B0-H11-Perturbations: bounded classified perturbation study

S3-C, [issue 10](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/10). NUM-005/006, NUM-003, SCI-002/003/004, BND-001, REP-001/002. Physics remains source-free Maxwell in the existing [periodic PSATD representation](B0-H11-PSATD.md). This is a short-time sensitivity benchmark, not a stability theorem for isolated knots or electrons.

## Primary equation sources and literature comparison

Equations/passages inspected before implementation:

- [Feynman II-20](https://www.feynmanlectures.caltech.edu/II_20.html), (20.1)/(20.12), linearity paragraph preceding (20.25), and Section 20-2 generalisation to three-dimensional superpositions. The homogeneous equations are linear in full E/B, not in energy density. Differences of solutions obey the same equations.
- [Feynman II-27](https://www.feynmanlectures.caltech.edu/II_27.html), Sections 27-1/27-3, (27.2), (27.14)-(27.15): local energy transport, energy density and Poynting vector. Apply these to the difference field as well as the full field.
- [Hoyos et al., arXiv:1502.01382v2](https://arxiv.org/abs/1502.01382v2), (2.1)-(2.6) and duality discussion after (2.9): complex Maxwell field, Bateman null conditions and constant electromagnetic duality.
- [Irvine, arXiv:1110.5408v1](https://arxiv.org/html/1110.5408v1), abstract and Sections 2-3: pointwise orthogonality/frozen-field assumptions are stronger than conserved helicity. We assess only relevant local invariants here; we neither reproduce its counterexample nor compute topology or helicity.

The [report](../../reports/s3-c/README.md) includes short exact attributed quotations next to measured agreements and explicit limits. A literature quotation supplies an expectation, not new experimental support for an electron model.

## Derivation and conventions

c=epsilon_0=mu_0=l0=1, arbitrary amplitude; real collocated vector fields. No new spacetime tensor or gauge choice. A vector potential is used solely to construct initial perturbations. Source-free constraints are div E=div B=0. With F=E+iB, null means both E.B=0 and E²-B²=0.

Let (E0,B0) and (E1,B1) solve the same periodic Maxwell problem. Then deltaE=E1-E0 and deltaB=B1-B0 solve it too, and:

```text
U_delta = integral (deltaE²+deltaB²)/2
S_delta = deltaE cross deltaB
partial_t u_delta + div S_delta = 0
periodic full-box dU_delta/dt = 0
fixed interior cube: change U_delta + integral outward S_delta dt = 0
```

This positive conserved norm is not total-energy change U1-U0, which also contains E0.deltaE+B0.deltaB. Neither conservation nor exact linear superposition establishes self-binding, asymptotic decay, null-family membership or preservation of field-line topology.

Controls and perturbations:

1. Amplitude: E1=(1+epsilon)E0, B1=(1+epsilon)B0. Analytically preserves the null family.
2. Constant duality: F1=exp(i theta)F0, theta=2 asin(epsilon/2), so ||deltaF||/||F0||=epsilon. Explicitly E1=cos(theta)E0-sin(theta)B0, B1=sin(theta)E0+cos(theta)B0. Analytically preserves nullness and local energy density. This is a field rotation, not a new inertial observer.
3. Generic electric spectral curl: deltaE=s epsilon curl(g a), deltaB=0. g is a product of three-image Gaussian sums of width .8; center in [-.5,.5]^3 and unit orientation a are seeded. The FFT interpolant is periodic and div curl vanishes mode by mode. Scale s is calibrated once for each seed on N61,L6.1 so the initial relative field norm equals epsilon; the same physical s/parameters are retained for domain/spatial comparisons. The changed equations do not impose null conditions, so they must be measured.
4. Negative control: an electric spectral gradient of the same Gaussian. Its divergence violates the vacuum constraint. It is diagnosed and explicitly projected for comparison; it is not evolved as accepted vacuum data.

The analytic Hopfion is sampled and transversely projected once to make the periodic base. The global projection correction is recorded. Combined/base/delta solvers then use project=False, avoiding hidden extra projection. A projected periodic sample is not exactly the unbounded null Hopfion. Analytic amplitude/duality null controls are therefore evaluated separately on the unbounded expression. Periodic control null scores must track the periodic base; they are not required to be zero.

## Diagnostics and fixed observation region

Report both RMS(E.B)/RMS(u) and RMS((E²-B²)/2)/RMS(u), plus their combined Euclidean score. There is no pointwise division by small tail energy. The change of the two invariant fields is separately normalised by RMS(base u); it is not substituted for the perturbed field's actual null score.

For each time, compare combined-base with the independently evolved delta, normalised by initial delta field norm. Measure global difference energy from real-space subtraction and record standalone delta energy too. These implement separate paths through the same independently validated propagator, not two different physical theories.

Native-grid interior Poynting diagnostics use the S2 nodal trapezoids. At the reference dx=.2 the half extent1.2 is exactly six cells. The resolution/domain comparison also evaluates Fourier fields on a common 17^3 cube [-1.2,1.2]^3. Phases account for the FFT origin at -floor(N/2)dx. Energy response is then computed on the same physical cube with the same trapezoidal quadrature in every case. This avoids mistaking a changed integration boundary for spatial convergence. Finite observation quadrature remains an approximation; native and fixed-cube observables are labelled separately.

## Acceptance declared before numerical experiments

Reference N61,L6.1, times0,.25,.5,.75; three seeds11/29/47 and relative norms .01/.05/.1. Two special-family controls at .1. Spatial N25/49/73,L6.1; domain N41/61/81,dx.2; canonical seed11,epsilon.1. No broad search or fit.

- All sampled periodic divergence maxima <1e-10.
- Superposition relative error and global difference-energy drift <1e-11.
- Reference initial relative perturbation norm within1e-12 of its target; quadratic difference-energy scaling across amplitudes within1e-11 relative.
- Analytic special-family null scores <1e-12; periodic combined null score agrees with its periodic base within1e-12 for amplitude/duality controls.
- Every generic trial's initial invariant-change score >1e-5. This tests classification, not a universal theorem about arbitrary perturbations.
- Longitudinal negative control raw divergence>.01 and explicit projection removes >99.9% of its field norm.
- Finest successive fixed-cube energy-response increments <.005 of initial core base energy for spatial and domain studies. Record both successive increments; do not infer an infinite-domain limit from three boxes.
- Delta-only interior Poynting balance at8/16/32 time intervals: finest absolute defect / initial interior delta energy <.02 and successive time-flux increment ratio3.5..4.5. This ratio tests flux-time quadrature, since modal evolution is analytically stepped. Space quadrature error is retained.

Any failed check must retain metrics and its numerical/physical scope. No thresholds will be loosened to obtain a desired hypothesis outcome. Local energy changes are scientific observations, not required evidence for self-confinement.

## Reproduction

```bash
uv sync --frozen --all-groups
uv run --frozen pytest -q
python scripts/check_docs.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --frozen python -m electron_field_topology.perturbation_benchmark --config experiments/configs/hopfion-s3c.json --output artifacts/s3c-local
```

Use a new/empty output directory. [Bounded workflow](../../.github/workflows/perturbations.yml): read-only token, 10-minute timeout, push/PR/manual, 14-day artifacts. No absorbing boundary, long-time isolation, helicity, field-line tracing, topology invariant, nonlinear interaction or quantum test is added.
