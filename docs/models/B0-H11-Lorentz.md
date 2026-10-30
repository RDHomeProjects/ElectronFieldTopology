# B0-H11-Lorentz: analytical observer transformations

S3-A, issue [6](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/6). Requirements REL-001/002, SCI-001/002/004, BND-001, REP-001/002. The underlying solution remains [B0-H11](B0-H11.md). No equations of motion, sources or physical assumptions are added.

## Sources and equation mapping

- [Feynman Lectures II, Chapter 26](https://www.feynmanlectures.caltech.edu/II_26.html), Tables 26-2 and 26-4: coordinate boosts and component E/B transformations. The explicit x-axis sign control in `tests/test_relativity.py` uses the latter table with c=1.
- [Hoyos, Sircar and Sonnenschein, arXiv:1502.01382v2](https://arxiv.org/abs/1502.01382v2), Section 4.1: mostly-plus signature and contravariant electromagnetic tensor. Section 2.1 gives the Hopfion construction; Section 2.2 gives Pz/U=-p/(p+q), hence -1/2 for p=q=1. The scale of U=2 pi^2 comes from our unit-amplitude S1 integral, not from borrowing another paper's normalisation. No angular-momentum sign or centroid coefficient is imported.
- L13 is motivation for treating simultaneity carefully. Its paraxial centroid examples are not used as numerical references here; centroid/width work is S3-B.

These equation passages were inspected before implementation. Links are primary sources, not copied software. The following equations specify the repository's exact convention.

## Conventions and derivation

Units c=epsilon_0=mu_0=l0=1; real coordinates, arbitrary unit field amplitude. Events x=(t,x,y,z), metric eta=diag(-1,1,1,1). A passive boost expresses the same event in a frame moving at velocity v relative to the source frame:

```text
x' = Lambda(v) x; gamma = 1/sqrt(1-v.v)
Lambda00 = gamma; Lambda0i = Lambdai0 = -gamma vi
Lambdaij = deltaij + gamma^2/(gamma+1) vi vj
F^(0i) = Ei; F^(ij) = epsilon_ijk Bk
F' = Lambda F Lambda^T
E' = gamma(E + v cross B) - gamma^2/(gamma+1) v(v.E)
B' = gamma(B - v cross E) - gamma^2/(gamma+1) v(v.B)
```

Indices in the F expressions are both contravariant. The stable gamma coefficient equals (gamma-1)/|v|^2 with a finite v=0 limit. The implementation uses the vector formulas; a separately assembled antisymmetric tensor checks them. Feynman's tensor notation need not match these index conventions; the component field transformations do.

For each requested target event (t',r'), compute x=Lambda(-v)x', evaluate the analytical Hopfion at the resulting source coordinates **and source time**, then transform E/B at that event. A constant target-time sphere generally maps to different source times. A single source-time snapshot is insufficient. The evaluator therefore supports time arrays broadcasting with point leading axes.

Gauge: no potential is used; diagnostics use E/B. Space is unbounded ordinary R^3; there is no periodicity, imposed cavity, projection or numerical evolution. Spheres truncate diagnostic integrals only. This wrapper is not a new independent time integrator; S2 remains the independent evolution check.

## Independent controls and acceptance

The issue predeclares <1e-12 local errors, second-order residual refinement and <2e-4 finest four-momentum relative error. Standard config: four boosts of speed <=0.6, 96 deterministic random points/events, h=.04,.02,.01, radii 4/8/12, orders 24/40/64. No tolerance was relaxed after a failure.

- Metric preservation, inverse boosts, common-event mapping and generic non-null field invariants. Null Hopfion invariants alone could conceal a wrong boost.
- Identity, collinear velocity composition and noncollinear full-matrix composition. Noncollinear boosts include a rotation; the product is not replaced by a pure boost.
- Central differences of all four source-free Maxwell residuals in target coordinates. RMS norms avoid dividing by a near-zero reference. Both successive ratios must lie in 3.7..4.3, consistent with second order. A separately defined plane wave verifies the callback diagnostic.
- An intentionally incorrect wrapper discards inverse-mapped source time. Its finest RMS residual must exceed .01. It is retained as a negative control, not a candidate model.
- At t'=0 integrate (u,E cross B) over target-frame spheres. For the full field the independent reference is Lambda(v)(2 pi^2,0,0,-pi^2). Compare the Euclidean four-component error divided by the Euclidean reference norm, not a Lorentz norm of an error vector. All-space M^2=U^2-|P|^2=3 pi^4. This dimensional normalisation is arbitrary and is not an electron mass prediction.
- Separate domain enlargement at order 64 from quadrature refinement at radius 12. Require a finest quadrature increment <2e-5 in the reference norm; tail error remains explicitly measured. A finite-radius integral is not itself a conserved four-vector across different slices.
- Electric flux through an off-centre target sphere at t'=.3, radius 2, centre (.2,-.1,.3). Retain raw signed and absolute-flux integrals; finest signed/absolute ratio <1e-10. Zero charge is expected.

These are bounded regression criteria for the selected cases, not rigorous global error bounds or validation arbitrarily close to light speed. Negative results and all raw scalar cases remain in metrics.json even if acceptance fails. The CLI writes evidence before returning a failure exit code.

## Reproduction

```bash
uv sync --frozen --all-groups
uv run --frozen pytest -q
python scripts/check_docs.py
uv run --frozen python -m electron_field_topology.relativity_benchmark --config experiments/configs/hopfion-s3a.json --output artifacts/s3a-local
```

Use a new or empty output directory. The bounded [workflow](../../.github/workflows/relativity.yml) runs on push/PR or manual dispatch with read-only permissions, a 10-minute timeout and 14-day artifacts. The [report](../../reports/s3-a/README.md) links measured evidence separately from this specification.
