# B0-S4B-Offcore — bounded off-core tracing and independent polygon invariants

[Issue 30](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/30). Requirements SCI-003/004/005, TOP-001, SRCH-001/002, NUM-003, REP-001/002. The maintainer resumed S4-B on 31 October 2026; the larger literature review is incomplete and level 4 remains deferred. See [ADR-0005](../decisions/ADR-0005-s4b-resumption.md).

## Model, sources and equations

The [S4-A Bateman monomials](B0-Bateman-PQ.md) and source-free Maxwell equations are unchanged. Units are $c=\epsilon_0=\mu_0=\ell_0=1$, $\mathbf F=\mathbf E+i\mathbf B$, with the original $pq$ amplitude. There is no physical boundary, new action, scale fitting or electron model.

| Source | Inspected mapping | Use and limit |
|---|---|---|
| L02 / L11, Kedia 2013 v1 and Hoyos 2015 v2 | Existing S4-A equation map | Reuse the validated field and core controls; no new generator |
| L24, Kedia et al. 2018 | Journal Sections 2–3, Eqs. (4), (9)–(10); Eq. (10) re-inspected in the original journal PDF, journal p.6 | Sample initial null and complex-curl conditions; retain analytic and smooth-flow hypotheses |
| L15, Bode–Peralta-Salas, arXiv:2302.01043v2 | Section 1.1, non-vanishing hypotheses and invariant-torus discussion; historical targeted Section 7 audit retained | Separate closed-orbit existence from all-orbit periodicity; field zeros and finite budgets remain explicit |
| L21, Moffatt 1969 | Original pp.118–121, Gauss/winding discussion; 2017 correction retained separately | Independent signed link check; linking is not a complete knot classifier |
| L35, Kılıç et al. 2025 | Publisher full text, Definition 2.6, Eq. (1), Definition 3.5, Proposition 3.7, Definition 3.10 | Regular diagrams and Fox matrix at $t=-1$; determinants do not identify every knot |

Public equation sources: [Kedia journal PDF](https://irvinelab.uchicago.edu/papers/Kedia_2018_J._Phys._A__Math._Theor._51_025204.pdf), [Bode–Peralta-Salas v2](https://arxiv.org/html/2302.01043v2), [Moffatt original](https://www.damtp.cam.ac.uk/user/hkm2/PDFs/Moffatt_1969_JFM_35_117.pdf), [Kılıç et al. publisher](https://doi.org/10.1007/s10623-025-01615-x). Source-specific limitations are retained in [the main bibliography](../literature/README.md). No equation is imported from an abstract-only source.

## Initial conditions and nodal policy

The initial-condition sample checks

```math
\mathbf F\cdot\mathbf F=0,\qquad
\mathbf F\cdot(\nabla\times\mathbf F)=0.
```

The second quantity is evaluated by centred spatial differences with steps .02/.01/.005 at 32 deterministic sample points. Its normalisation is $\|\mathbf F\|\,\|\nabla\times\mathbf F\|$. A finite sample is not verification of global analytic hypotheses. Predeclared acceptance: sampled null residual below $10^{-12}$ and finest complex-curl residual below .002. No tolerance is adjusted after looking at a result.

For the already implemented family $\mathbf F=g\mathbf F_{1,1}$, $g=pq\alpha^{p-1}\beta^{q-1}$. Complex multiplication directly gives $u=|g|^2u_0$ and $\mathbf S=|g|^2\mathbf S_0$. Thus

```math
\frac{\mathbf S}{u}=\frac{\mathbf S_0}{u_0}\quad(g\ne0).
```

The known baseline flow supplies a smooth extension through these scalar-factor zeros, but the physical higher-order field is still zero there. At $t=0$, $\alpha=0$ on $z=0,x^2+y^2=1$ and $\beta=0$ on the $z$ axis. Do not apply a non-vanishing-field theorem to the whole higher-order family. The tracer refuses magnetic directions when $\|\mathbf B_{p,q}\|/\|\mathbf F_{1,1}\|<10^{-8}$. This is a declared numerical guard, not a new physical cutoff. Exact zero, near-zero and invalid fields have explicit outcomes.

## Fixed sampling and closure

Four families $(1,1),(2,1),(2,3),(3,2)$; times $0,.75$; initial positive core phase .17 plus offsets $(0,0,0),(.15,0,0),(0,0,.2)$. These are 24 fixed cases, including eight core controls and sixteen off-core cases, not a random ensemble. Seed transport is $\mathbf x(t)=\mathbf x_0+t\mathbf v_0(\mathbf x_0)$ using the established straight baseline flow; an independent coordinate-transport check is retained. Each trace is a snapshot of the magnetic field at its specified time, not a material trajectory or independent Maxwell evolution.

Trace $d\mathbf x/ds=\mathbf B/\|\mathbf B\|$ by DOP853. Coarse/fine settings are tolerances $10^{-9}/10^{-11}$, max steps .15/.075, arclength budgets 40/80 and polygons 128/256. Observation radius 12 and 20,000 RHS evaluations are hard budgets; they are not reflecting/absorbing walls. All outcomes are retained. Only this frozen configuration is admitted by the experiment driver.

After a .05 departure, scan **all** positive returns to the initial tangent section. Require arclength above .5, position gap below $10^{-6}$ and tangent mismatch below $10^{-6}$. An early nonclosing crossing does not terminate the scan. Correct the final point only after both closure checks pass, and record the correction. On unresolved traces the actual endpoints remain separate. Failed solver/evaluation-budget runs are recorded without claiming a valid partial interpolant.

`closed_refined` additionally requires agreement of the two accepted lengths and paired arclength samples within $10^{-5}$ (length comparison relative to $\max(1,L)$). Closure appearing only at the extended budget is separately provisional. `unresolved_budget` does not mean open for infinite time or quasiperiodic. Domain and near-zero guards, solver failure and refinement disagreement remain distinct.

## Independent topology gates

Closed, nondegenerate, non-self-intersecting polygons only. Project along three fixed, non-axis-aligned normals. Find transverse projected segment intersections, preserve over/under depth, and reject crossings near vertices, ambiguous depth, overlapping parallel projections, triple crossings and diagrams above 64 crossings. No projection is silently repaired. At least two regular projections must agree.

For a single component, split arcs at undercrossings and specialise the inspected Fox relation to $t=-1$:

```math
2c_{\rm over}-c_{\rm under,in}-c_{\rm under,out}=0,\qquad
d=|\det M_{ij}^{*}(-1)|.
```

Use exact integer Bareiss elimination; two cofactors must agree in absolute value. Repeated arc contributions are accumulated, including Reidemeister-I cases. Compare determinants on 64, 128 and 256 segment polygons sampled from the fine trace. Independent standard torus parametrisations at all three resolutions, orientation reversal, reflection and exact symbolic determinant controls test the implementation. A determinant above one detects a nontrivial **polygon**; determinant one does not prove an unknot, and matching determinants do not establish equal knot types. All returned `knot_type` values remain `not_identified`. This is an independent invariant gate, not a complete knot-identification or continuum-isotopy algorithm.

For two disjoint components, independently compute half the signed intercomponent crossing sum. In our right-handed projection basis each crossing sign is $\operatorname{sgn}[\det(\mathbf a'_{xy},\mathbf b'_{xy})(a_z-b_z)]$. Compare it to the existing signed Gauss integral at both polygon resolutions, with absolute discrepancy below .02. Known Hopf, reversed and unlinked controls set orientation independently. Selected positive/negative core pairs are controls, not samples of arbitrary pairs.

## Disposition of the other recovered findings

| Sources | S4-B disposition |
|---|---|
| L20 Newcomb | Preserve transport/observer distinction; abstract-only source supplies no new equation |
| L22 Berger–Field, L25 Whitehead | No open-window helicity or integer Hopf claim; retain existing gauges, amplitudes and domains |
| L23 Woltjer, L26 Derrick, L27 Faddeev–Niemi, L29 Chui–Moffatt | No new energy-minimisation or binding model; constraint/scaling analyses remain S5 gates |
| L28 Fuller | Writhe remains an optional geometry diagnostic; it cannot replace knot invariants; no writhe code added |
| L30 Yakovenko, L31 Tze–Ezawa, L32 Finkelstein–Rubinstein | No imported charge/spin/statistics conclusion or changed field content |
| L33 Lekner, L34 RS review/correction | No equations imported before full-text/version/correction audit |
| R32 cold-atom pump | Negative/out-of-scope assessment preserved; no working-bibliography promotion |

The earlier energy-localisation and field-transport non-containment results retain their separate observables/hypotheses. Nothing here establishes energy confinement from persistent topology. Primary-author results are distinct from project interpretations and finite numerical observations. AI assisted implementation and documentation; specialist certification is not claimed.

## Reproduction

```bash
uv sync --frozen --all-groups
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --frozen pytest -q
python3 scripts/check_docs.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --frozen python -m electron_field_topology.offcore_benchmark --config experiments/configs/offcore-s4b.json --output artifacts/s4b-local
```

Use a new/empty output directory. Results and limitations are retained in [the S4-B report](../../reports/s4-b/README.md). The [bounded workflow](../../.github/workflows/offcore.yml) runs numerical checks because this stage changes numerical code; prose-only paths remain excluded from numerical workflows.
