# B0-Bateman-PQ: bounded S4-A catalogue

[Issue 14](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/14). SRCH-001/002, SCI-004/005, NUM-003, TOP-001, REP-001/002. This work is stacked on unmerged [PR 13](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/13); no prerequisite PR is merged by this task.

## Sources inspected and version pinning

[Kedia et al., arXiv:1302.0342v1](https://arxiv.org/abs/1302.0342v1), PDF pages 2–4: holomorphic family Eq. (5), coordinates Eq. (9), stereographic map Eq. (10), field Eq. (11), core parametrisation in the following paragraph, and straight-geodesic flow discussion. These equations/parametrisations were visually inspected in the versioned PDF. The core formula is unnumbered; it must not be cited as Eq. (11), which is the field construction. Only the coprime branch index zero is used here, avoiding interpretation of the noncoprime branch formula.

[Hoyos et al., arXiv:1502.01382v2](https://arxiv.org/abs/1502.01382v2), Eqs. (2.21)–(2.22), the following conserved-quantity list and Eq. (4.48): family construction, momentum/energy ratio and helicity formula. Angular momentum signs from that paper are not imported. The report distinguishes numerical agreement, explicit derivation and literature labels.

[GitHub's math guide](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions) was read. New mathematical displays use `math` fences; inline formulas use dollar delimiters. Scientific plots are computed from fields/curves and embedded with relative image links.

## Model and normalisation

The unbounded source-free baseline remains [B0-H11](B0-H11.md), with $c=\epsilon_0=\mu_0=\ell_0=1$, raw unit amplitude, no cavity, sources or new dynamics. Define

```math
D=r^2-(t-i)^2,\qquad
\alpha=\frac{r^2-t^2-1+2iz}{D},\qquad
\beta=\frac{2(x-iy)}{D}.
```

For positive integer powers,

```math
\mathbf F_{p,q}=\nabla\alpha^p\times\nabla\beta^q
=pq\,\alpha^{p-1}\beta^{q-1}\mathbf F_{1,1},\qquad
\mathbf F=\mathbf E+i\mathbf B.
```

Retain the full $pq$ multiplier. No family is fitted to an electron energy, mass or charge. The baseline evaluator is reused; independent power-gradient and polynomial references check the construction. Positive integer powers avoid poles at zeros of $\alpha$ or $\beta$; non-integer/negative powers are outside this regular generator.

For helicity, the decaying Bateman gauge is

```math
\mathbf V_{p,q}=\alpha^p\nabla(\beta^q)=\mathbf C+i\mathbf A,
\qquad \mathbf B=\nabla\times\mathbf A,
\quad \mathbf E=\nabla\times\mathbf C.
```

All-space integration uses the existing radial compactification with independent angular/radial refinements. References, in this amplitude convention, are

```math
H_m=H_e=2\pi^2pq\frac{p!q!}{(p+q)!},\qquad
U=(p+q)H_m,\qquad
\frac{P_z}{U}=-\frac{p}{p+q},\quad P_x=P_y=0.
```

Energy and helicity depend on amplitude and length conventions; they are not integer knot counts. Nullness and Maxwell constraints are tested separately from finite integral convergence.

## Bounded catalogue and rejection ledger

The admitted requests are $(1,1),(2,1),(2,3),(3,2)$. The general reusable regular generator supports integer powers 1–5, while this catalogue's budget is powers at most 3 and coprime pairs. Requests $(0,1),(-1,2),(1.5,2)$ and boolean powers are invalid for this generator. $(4,5)$ is a regular family deferred by budget. $(2,2)$ is a valid link family deferred by the current coprime-core policy, not rejected by Maxwell theory. Record every request and its reason. There is no optimiser or ranking fitted to a target electron property.

## Parameterised cores versus field-line integration

For coprime $p,q$, use the inspected core loci, with $\theta\in[0,2\pi]$:

```math
\alpha_0=\sqrt{\frac p{p+q}}e^{iq\theta},\qquad
\beta_0=\sqrt{\frac q{p+q}}e^{-ip\theta+i\delta},
\qquad \delta\in\left\{0,-\frac\pi q\right\}.
```

The inverse stereographic map gives the initial curve and analytic $\theta$ derivative:

```math
\mathbf r_0=\frac{(\Re\beta_0,-\Im\beta_0,\Im\alpha_0)}{1-\Re\alpha_0}.
```

Transport it by the straight null Poynting flow from the published construction:

```math
\mathbf r(t)=\mathbf r_0+t\mathbf v_0(\mathbf r_0),\qquad
\mathbf v_0=\frac{\mathbf E_{1,1}\times\mathbf B_{1,1}}{u_{1,1}},
\qquad u=\frac{E^2+B^2}{2}.
```

The code differentiates this rational map analytically; it does not estimate tangents from the same sampled polygon used by the field check. Verify $\mathbf r_\theta\times\mathbf B=0$, the transported coordinates and the complex core level

```math
\alpha^p\beta^q=\pm M_{p,q},\qquad
M_{p,q}=\left(\frac p{p+q}\right)^{p/2}
\left(\frac q{p+q}\right)^{q/2}.
```

The plotted reference curves are labelled parameterised, not independently traced. A separate adaptive $\mathbf B$ ODE starts at phase .17 on each core at each time. It scans all positive tangent-section returns in a fixed arclength budget and accepts the first return satisfying both position and tangent closure. A knot can cross that section away from its seed, so the S3-D first-return rule is insufficient in general. Missed returns and failed budgets remain in the trace ledger; distant endpoints are never joined. Accepted ODE curves must retain the expected complex core level.

The two parallel torus-core components have the independent winding-product expectation $\lvert\operatorname{Lk}\rvert=pq$ in our S3-D Gauss convention. This is a selected-pair check, not a knot-polynomial classification. The v1 preprint's special-case prose gives $2q$ or $2p$ for linked rings; that numerical convention is not substituted for the independently calibrated Gauss integral. The $(1,1)$ Hopf control fixes unit linking; any mismatch is reported rather than changing the normalisation after measurement.

## Prospective acceptance and budgets

Times 0 and .75; quadrature angular 24/40/64 and radial 48/80/128; differences .04/.02/.01; polygons 128/256/512. Baseline and independent power-gradient relative errors below $10^{-12}$; normalised null score below $10^{-12}$; second-order Maxwell ratios 3.5–4.5 and finest normalised RMS residual below .01. All-space reference errors and finest increments below $10^{-5}$. Analytic core tangent error below $10^{-10}$ and transported coordinate/level errors below $10^{-10}$.

Each admitted core trace must close with position/tangent mismatch below $10^{-6}$ and core-level error below $10^{-5}$. Positive/negative-core link relative error and finest increment below .005. Default DOP853 tolerance $10^{-9}$, max step .15, max arclength 80; independent trefoil refinement uses $10^{-11}$. A separate regression control at trefoil phase .8 and arclength budget 30 must retain an early nonclosing section crossing and accept a later valid closure; default phase .17 cases are not claimed to exhibit that miss. All misses are retained even when later refinement resolves them. No claim is made about untested seeds or perturbed lines.

Plot a two-time 3D core gallery with common fixed $[-4,4]^3$ limits and equal coordinate scaling, fixed-plane energy-density maps with explicitly per-panel peak normalisation, and numerical convergence/reference comparisons. Image plotting limits are observation windows, not simulation boundaries. These graphics do not demonstrate self-confinement.

## Reproduction

```bash
uv sync --frozen --all-groups
uv run --frozen pytest -q
python scripts/check_docs.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --frozen python -m electron_field_topology.candidate_benchmark --config experiments/configs/bateman-s4a.json --output artifacts/s4a-local
```

Use a new/empty directory. [Workflow](../../.github/workflows/candidates.yml) is bounded push/PR/manual CPU work with read-only token, ten-minute timeout and 14-day artifacts. [Report](../../reports/s4-a/README.md) retains metrics, ledger, selected curves, graphics and interpretation.
