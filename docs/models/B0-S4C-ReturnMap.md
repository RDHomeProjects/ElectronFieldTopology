# B0-S4C-ReturnMap — bounded diagnosis before a model decision

[Issue 33](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/33). Requirements TOP-001, NUM-003, SCI-003/004/005, REP-001/002. Implements the authorised [post-S4-B assessment](../post-s4b-direction.md), without level-4 acquisition, a broad search or new physical dynamics.

## Fixed scope and independent controls

Use t=0 and the phase-.17 positive-core seed plus x-offset .15 in each of (2,1), (2,3), (3,2). Baseline: tolerance 1e-11, max step .075, length 80, 128 output samples, near-zero floor 1e-8, observation radius 12, 20,000 RHS evaluations. Change exactly one setting per variant:

| Control | Additional values | Others |
|---|---|---|
| Arclength budget | 20, 40 | Baseline |
| ODE tolerance | 1e-9, 1e-10 | Baseline |
| Maximum step | .15, .0375 | Baseline |
| Near-zero ratio floor | 1e-6, 1e-10 | Baseline |
| Observation radius | 6, 24 | Baseline |

Eleven settings including the baseline produce 33 diagnostic runs. Add the three z-offset-.2 seeds at baseline for replication, an off-core Hopfion closure control and a positive trefoil core control. The [frozen configuration](../../experiments/configs/returnmap-s4c.json) cannot silently expand these choices. The original S4-B closure criteria and physical-field convention are unchanged. Output sample count is not an ODE step size.

## Section coordinates and comparisons

The existing tracer retains every positive crossing after the .05 departure. It now also records actual event positions, the unit section normal and evaluated arclength. Default sections retain the original initial-tangent normal. Optional explicit normals must be finite, nonzero and transverse; orientation is chosen so the initial crossing is positive.

Choose a deterministic orthonormal basis $u,v$ in the seed-centred section and record

```math
\xi_k=(x_k-x_0)\cdot u,\qquad \eta_k=(x_k-x_0)\cdot v.
```

Check the normal residual independently. Compare position and arclength of the common event prefix against baseline, and require equal counts within the shared evaluated interval, with absolute comparison threshold 1e-5. Shorter budgets can legitimately have fewer total events. Missing/failed solves return `insufficient_returns`, not zero numerical error. Keep every status, including evaluation-budget failures; a smaller max step can exhaust a fixed evaluation cap without implying a change in physical orbit behaviour.

There is no assigned Maxwell rotation number, invariant torus or proof of quasiperiodicity. These coordinates are observations in a plane, not certified action-angle variables. Consecutive plot markers indicate return order, not a field-line segment between them. A sequence from a few seeds does not reconstruct the full return map on an entire section.

## Manufactured analytic torus controls

These are our explicit geometric test fields, not electromagnetic models or new physical equations. Set $R=2,r=.5$, $\rho=\sqrt{x^2+y^2}$ and parameterise

```math
x=(R+r\cos\phi)\cos\theta,\quad
y=(R+r\cos\phi)\sin\theta,\quad z=r\sin\phi,
\qquad \dot\theta=1,\quad\dot\phi=\omega.
```

Differentiation gives the Cartesian test vector

```math
V=(-y-\omega zx/\rho,\ x-\omega zy/\rho,\ \omega(\rho-R)).
```

It preserves $(\rho-R)^2+z^2=r^2$. Unit-speed reparameterisation changes return times/arclengths but not orbits or section locations. At $y=0$ with positive crossing, $\theta=2\pi k$ and $\phi_k=\phi_0+2\pi k\omega$ modulo $2\pi$. Use $\phi_0=.3$, $\omega=1/2$ (periodic) and $\sqrt2$ (nonperiodic by the analytic frequency ratio). The latter is an irrational-frequency analytic target represented approximately in floating point, not a claim that a binary float is irrational. Its known type follows from the construction, not a finite numerical classifier.

Predeclared instrument checks: both torus controls have at least three returns; wrapped angle error below 1e-6 and torus-equation residual below 1e-7; the rational control and both Maxwell closure controls close; the irrational control is not falsely closed; all section-plane residuals below 1e-9; every event position retained; unresolved endpoints never corrected. Sensitive or unresolved physical cases are findings, not failed acceptance checks. No tolerance is relaxed to obtain closure.

## Source and model decision mapping

The Maxwell trace equations and source map remain [B0-S4B](B0-S4B-Offcore.md). The new plane-coordinate and manufactured-control expressions are explicit geometric derivations above. Existing L05/L15 topology statements do not turn these finite returns into a general periodicity theorem.

The model-feasibility decision follows the measured diagnosis and targeted primary-source inspection: L16 Goulart, arXiv:1602.05071v1 Eqs. (1)–(3), null-field lemma and Eq. (11); L27 Faddeev–Niemi, hep-th/9610193v1 pp.2–3, Eqs. (2)–(4); L07 Faber–Kobushkin, hep-th/0207167v4 Section II, Eqs. (11)–(20). Their own conventions are retained in the [decision record](../decisions/ADR-0006-model-feasibility.md); no new action is implemented. Final journal/preprint reconciliation remains explicitly unfinished where relevant.

## Reproduction and evidence

```bash
uv sync --frozen --all-groups
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --frozen pytest -q
python3 scripts/check_docs.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 uv run --frozen python -m electron_field_topology.returnmap_benchmark --config experiments/configs/returnmap-s4c.json --output artifacts/s4c-local
```

Use a new/empty output directory. See [the measured diagnosis](../../reports/s4-c/README.md), [the decision](../decisions/ADR-0006-model-feasibility.md) and [the bounded CI workflow](../../.github/workflows/returnmap.yml). Source, configuration, dependency and artifact hashes accompany the clean evidence. Historical S4-B output/source hashes remain unchanged at their original commit; this additive trace-metadata extension does not rewrite them. AI assistance is disclosed; numerical control success is not independent expert certification.
