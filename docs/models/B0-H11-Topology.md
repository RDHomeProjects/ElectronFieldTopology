# B0-H11-Topology: bounded helicity and linking instruments

S3-D, [issue 12](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/12). TOP-001, SCI-003/004, NUM-003, REP-001/002. This implements known controls, potentials, selected field-line tracing and linking. It does not search candidate knots or certify the complete field-line topology of a solution.

## Inspected primary sources and equation mapping

- [Irvine, arXiv:1110.5408v1](https://arxiv.org/html/1110.5408v1): Eq.(4) magnetic helicity, Eq.(5) Gauss linking integral, Eq.(9) helicity exchange, the Hopf-fibration paragraph following Eqs.(1)-(3), and the Section5 counterexample. The printed triple-product order in Eq.(5) has the opposite oriented sign from our explicit convention below; absolute linking is compared to its Hopf claim. Our signed controls use independent disk-piercing orientation.
- [Hoyos et al., arXiv:1502.01382v2](https://arxiv.org/abs/1502.01382v2): Eqs.(2.7)-(2.10), potentials and helicities; null-field argument (2.12); Section2.2 gives Hopfion He=Hm=U/2. The last equality printed in (2.12) has a factor-of-two mismatch when extended away from the null case under definitions (2.10). Its stated null result is unaffected. We derive the non-null coefficient explicitly and verify it against an independent Beltrami solution below; we do not silently import that printed coefficient.
- L19 (Diglio/Ricca) and L15 (Bode/Peralta-Salas) remain relevant reviewed context. Their full texts could not be retrieved again for this implementation (PMC/publisher access wall and unavailable arXiv version). No newly verified equation, theorem or quote is attributed to them here. We implement from the accessible primary passages above and independent derivations, rather than silently claiming a fresh audit of inaccessible texts.

## Units, gauges and distinct domains

Units c=epsilon_0=mu_0=l0=1, arbitrary amplitude; E/B conventions remain [B0-H11](B0-H11.md). No new spacetime metric or dynamics. Distinguish three computations:

1. Periodic zero-mean fields on T^3: Coulomb potentials, Fourier inversion and periodic gauge transformations.
2. Unbounded analytical Hopfion: Bateman potentials V=alpha grad(beta)=C+iA, decaying at infinity, without imposing Coulomb gauge.
3. Unbounded analytical fixed-time B-field curves: no periodic seam, no volume-boundary closure.

A periodic helicity of mean-removed fields is not the unbounded original Hopfion helicity. Likewise the helicity scalar is not an integer link count or electric charge.

## Periodic potentials and conservation

For the inverse FFT exp(+ik.x), a transverse zero-mean B has:

```text
Ahat(k) = i k cross Bhat(k)/|k|², k!=0; Ahat(0)=0
B=curl A; div A=0; mean A=0
Chat(k) = i k cross Ehat(k)/|k|², k!=0; Chat(0)=0
Hm = integral A.B; He = integral C.E; Hopt=(Hm+He)/2
```

A nonzero mean cannot be represented as the curl of a periodic potential. Input with relative mean>1e-12 or spectral divergence norm/field norm>1e-10 is rejected. These are nondimensional diagnostic thresholds in the declared length units, not a hidden projection. A separate explicit mean-removal operation returns the removed vector. For real periodic Hopfion samples, first perform the existing measured transverse projection, then explicitly remove/report E/B means and removed energy before computing helicity. Modal tests have zero means analytically.

Under a smooth periodic scalar gauge phi, integral grad(phi).B = integral div(phi B)=0 because opposite faces cancel and div B=0. Constant potential shifts also leave zero-mean-field helicity unchanged. Test a nontrivial periodic gradient and potential reconstruction separately; no unbounded gauge argument is substituted for periodic boundary accounting.

With these normalisations, E=-partial_t A-grad phi and B=partial_t C+grad chi. Integration by parts gives:

```text
Hm' = integral (-E).B + A.(-curl E) = -2 integral E.B
He' = integral B.E + C.(curl B) = +2 integral E.B
Hopt' = 0
```

Thus optical helicity can be conserved in non-null fields while the separate electric/magnetic quantities exchange. It does not imply that field lines remain knotted. Test the exchange signs and factor using an independent modal solution, and retain temporal quadrature defects.

## Independent references

Period2pi, volume V=(2pi)^3, nonzero signed integer q. Set b0=(sin(qz),cos(qz),0), curl b0=q b0. With E0=0:

```text
B(t)=cos(qt)b0; E(t)=sin(qt)b0
A=B/q; C=E/q
Hm=V cos²(qt)/q; He=V sin²(qt)/q; Hopt=V/(2q)
integral E.B=V sin(qt)cos(qt)
```

Controls q=-2,-1,1,2 verify both signs and the length factor. Opposite q modes with equal amplitude give cancellation despite nonzero energy. No field-line knot type is inferred from either example.

For the unbounded Hopfion, use the inspected V=alpha grad beta without Fourier inversion; derive grad beta from the quotient rule. Independently verify curl A=B and curl C=E using central differences. All-space radial compactification from S3-B integrates He/Hm. Expect each pi²=U/2 for this amplitude; times0,.75 and angular24/40/64 with radial48/80/128 distinguish this from a finite periodic inference.

## Curve orientation, closure and linking

Our oriented Gauss convention is:

```text
L = (1/(4pi)) double_integral (dr1 cross dr2).(r1-r2)/|r1-r2|³
```

Use polygon segment midpoints and edge vectors; do not round the answer to an integer. Reversing one curve reverses L. Curve1=(cos u,sin u,0), curve2=(1+cos v,0,sin v): curve2 pierces the oriented spanning disk downward once, so L=-1. Reversal gives+1; shifting curve2's x-center from1 to3 gives0. Reject open, zero-length, self-intersecting or mutually intersecting/unresolved polygons. Pairwise segment distances, including nonadjacent self segments, check the sampled polygons. They are not a rigorous lower bound for an unsampled smooth curve.

For fixed-time field lines solve dr/ds=B/|B| with adaptive ODE integration and no periodic wrapping. Depart .05 in arclength, then detect the first positive return through the seed's tangent-normal section. A return alone does not prove closure: require position gap<1e-6 and unit-tangent mismatch<1e-6. Retain solver status, arclength, evaluations and any endpoint correction. Only after these checks may a tiny closing gap be corrected for polygon quadrature. A finite-budget open trajectory must remain open and be rejected by linking.

Trace selected analytical t=0 B fibers from (1,0,0) and (.5,0,0). The first is independently a unit circle in y=0 with negative z tangent at x=1. The second is integrated, not imposed. Compare their |L| with1. Selected pairs do not certify every fiber, perturbed topology or persistence at later times.

## Acceptance before numerical runs

The issue predeclares modal helicity, reconstruction, Coulomb and gauge errors<1e-11 in the recorded field/energy normalisations; optical-helicity drift/initial energy<1e-11. Reference modal grid17, q=±1,±2, times0,.25,.5,.75. Exchange integral at8/16/32 intervals must show second-order ratio3.5..4.5; generic seed11 curl exchange balance/initial energy<1e-4 at the finest count. Explicit mean/divergence controls must be rejected.

Use mean-removed projected Hopfion domain grids41/61/81 at dx=.2, separately labelled. Unbounded He/Hm relative errors and finest increments<1e-6. Independent central-difference potential curl checks use h=.04,.02,.01, requiring second-order ratios3.5..4.5 and finest normalised residual<.01.

Known and traced Gauss-link values use64/128/256 segments: finest signed control or unsigned traced error<5e-4 and finest increment<5e-4. Trace tolerances1e-8/1e-10/1e-12 with max steps.1/.05/.025; max arclength40. Retain a uniform-field finite-budget failure. All scientific/numerical outcomes are written before any failed acceptance exit; thresholds are not loosened to suit results.

## Reproduction

```bash
uv sync --frozen --all-groups
uv run --frozen pytest -q
python scripts/check_docs.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --frozen python -m electron_field_topology.topology_benchmark --config experiments/configs/hopfion-s3d.json --output artifacts/s3d-local
```

Use a new/empty output directory. [Workflow](../../.github/workflows/topology.yml) is bounded push/PR/manual CPU validation, read-only token,10-minute timeout and14-day artifacts. [Report](../../reports/s3-d/README.md) retains measured results, primary-source quotes and limits. No broad candidate search, open-boundary evolution, modified dynamics or electron interpretation is added.
