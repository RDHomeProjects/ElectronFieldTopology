# Equation-level model-feasibility audit after S4-C

31 October 2026 (Australia/Melbourne). This is a targeted action/constraint audit for [issue 33](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/33), not a new simulator or completed theory review. [The decision](../decisions/ADR-0006-model-feasibility.md) follows the [measured return-map diagnosis](../../reports/s4-c/README.md). Primary source equations, our algebra and project dispositions are distinguished below.

## Source and convention register

| Candidate | Primary source inspected | Convention and limitation |
|---|---|---|
| Maxwell B0 | Existing [baseline](../02-physics-and-hypotheses.md), [S3-B evidence](../../reports/s3-b/README.md) | Simulator uses c=epsilon_0=mu_0=l0=1; smooth source-free fields on ordinary space |
| Invariant NLED | L16, [Goulart arXiv:1602.05071v1](https://arxiv.org/html/1602.05071v1), Eqs.(1)–(3), null-field lemma and Eq.(11) | Source tensor conventions retained; null-invariant argument needs no metric-sign conversion; no NLED evolution implemented |
| Skyrme–Faddeev | L27, [hep-th/9610193v1](https://arxiv.org/pdf/hep-th/9610193v1), printed pp.2–3, Hamiltonian Eq.(2), virial Eq.(3), relaxation Eq.(4); Hamiltonian page visually inspected | Static Euclidean energy only; positive coefficients below absorb source normalization/index factors; journal/preprint reconciliation pending |
| Charged internal-field model | L07, [Faber–Kobushkin hep-th/0207167v4](https://arxiv.org/html/hep-th/0207167v4), Section II Eqs.(11)–(20) | Source metric +---, internal SO(3) field encoded by SU(2); no tensor/sign conversion or dynamical implementation |

No equations are imported from abstract-only assessments. These targeted inspections do not certify complete papers, perturbative stability or global well-posedness. Versions and limitations are also recorded in [the main bibliography](../literature/README.md).

## B0: useful reference, no charge/binding inference

For a smooth source-free field, integrating div E=0 over an ordinary enclosed volume yields zero net electric flux. The measured Hopfion energy spreads in S3-B. S4-C diagnoses snapshot field lines, not energy confinement; finite recurrence does not change either constraint. Keep B0 for validation. Restrict any no-go conclusion to the stated assumptions and the proposed route to an electron, not every field theory.

## Invariant NLED: substitution is required before adding computation

Goulart uses invariants $I=F_{ab}F^{ab}$ and $J={}^\star F_{ab}F^{ab}$ and the source-free equation

```math
\nabla_a(\mathcal L_I F^{ab}+\mathcal L_J{}^\star F^{ab})=0.
```

For the retained null fields, I=J=0 everywhere. Smooth L makes both coefficients constant there; the Maxwell equation and Bianchi identity then annihilate the two terms. This is the inspected null-field lemma's argument. A nonlinear action that retains this sector does not automatically bind these same configurations. This does not exclude new non-null sectors, source/topology changes, or different perturbation dynamics. Any future candidate needs a separate sector and well-posedness analysis.

## Skyrme–Faddeev: a binding-mechanism reference with extra fields

The inspected Hamiltonian contains positive quadratic and quartic derivative terms for a unit three-vector n approaching a constant at infinity. Write its static structure, without identifying its couplings with electric charge, as

```math
E[n]=E_2+E_4=\int\!\left(c_2\sum_i|\partial_i n|^2+
c_4\sum_{i,j}[n\cdot(\partial_i n\times\partial_j n)]^2\right)d^3x,
\qquad |n|=1,\quad c_2,c_4>0.
```

**Our dilation calculation:** for $n_\lambda(x)=n(x/\lambda)$, the volume element contributes lambda cubed and each derivative one inverse lambda. Thus

```math
E(\lambda)=\lambda E_2+\lambda^{-1}E_4,\qquad
E'(1)=E_2-E_4,\qquad E''(\lambda)=2E_4/\lambda^3.
```

A stationary scale along this restricted variation has E2=E4. This removes one simple collapse/expansion channel; it is not a proof of a solution or stability under all variations. The length scale depends on the coefficients and field profile, not an electron prediction. Hopf charge of n is not electric charge. The source's parabolic minimisation parameter is not physical time; adjusting a coupling to enforce a virial relation is not evidence of dynamical self-organization. A future reference calculation must fix couplings and measure the virial residual independently.

## Charged internal-field model: charge relevance with explicit inputs

Faber–Kobushkin's Section II defines Q, its internal connection and curvature, with

```math
\mathcal L=-\frac{\alpha_f\hbar c}{4\pi}
\left(\frac14 R_{\mu\nu}\cdot R^{\mu\nu}+\Lambda(q_0)\right),
\qquad \Lambda(q_0)=q_0^{2m}/r_0^4.
```

The inspected definitions put the elementary charge inside alpha_f and supply a dimensional r0. Its additional internal field and boundary sector differ from B0; these inputs cannot be relabelled emergent charge or electron size. Its charged-soliton claims motivate further review, not adoption here. Defer a solver until the finite-size energy/charge map, characteristic well-posedness, stability and parameter dependence have independent checks. This audit does not certify the paper's spin/statistics claims or identify its electrodynamic limit with a reproduced finite-size electron.

## Decision gates

The [decision record](../decisions/ADR-0006-model-feasibility.md) supplies explicit no-go/conditional-go/defer dispositions. No field content, action, charge definition, dynamics, coupling or dependency in the existing Maxwell numerical model is changed by this audit. Future modified dynamics require their own model ID, full normalization and conservation map, independent variational/gradient checks, energy/boundary controls and reviewed causal/stability assumptions. S6 interactions and S7 quantum predictions remain separate gates. AI assistance is disclosed; cited works are primary sources, not certification of this project's interpretation.
