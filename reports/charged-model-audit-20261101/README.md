# Charge-capable relativistic model: equation audit

Recorded: 2026-11-01T02:02:43+00:00 (UTC); 2026-11-01T13:02:43+11:00 (Australia/Melbourne). Parent: main at `42376b46fb52771a7d22138c29689d519c290619` (PR 48). Scope: the analytical next step in [ADR-0007](../../docs/decisions/ADR-0007-tightened-milestones.md), following the [fresh Q22 assessment](../s5-a/q22-fresh-20261101T102757+1100/ASSESSMENT.md). This is an audit of a candidate, not selection of a new physical model.

**Disposition:** the finite-energy mechanism and charge-to-flux normalization are reproducible at the analytical level. The literal electrodynamic map does not represent general Maxwell fields. The quartic derivative theory also has degenerate vacuum kinetics and an allowed local derivative configuration with non-real characteristic frequencies. These restrict any claim of general causal evolution. Defer a three-dimensional charged dynamics solver. Retain the neutral static benchmark and proceed next to the specifically planned [additional-Q and Q18 basin assessment](../../docs/plans/post-audit-q-assessment.md).

The accompanying [verification ledger](verification.json) records 32 passed algebra/quadrature checks and zero failures. A successful check confirms the specified calculation, including counterexamples; it does not turn a negative physics result into an acceptance. No GPU solve, new Q run, experiment, or field evolution was performed. AI assisted the derivations and review; independent scientific review remains necessary.

## Evidence and source register

Labels used below: **source definition**, **independent reproduction** of a published result, **our derivation**, **interpretation**, and **unresolved**. Exact paper versions and the new bibliography supplement are in [the source register](../../docs/literature/charged-model-audit-sources.md). The wider literature review remains incomplete.

| Primary source | Inspected scope | Use here |
|---|---|---|
| Faber–Kobushkin, hep-th/0207167v4 (21 February 2004) | Eqs.11–20, 21–47, 61–76, 88–96; Appendix connection identities | Candidate definitions; charge/limit and interaction claims to audit |
| Faber–Kobushkin–Pitschmann, 0812.4225v1 (22 December 2008) | Eqs.2–6, 13–24, 30, 36; PDF pages 5–6 visually inspected | Restricted profile fluctuations; normalization discrepancy below |
| Wong, 1011.3029v2 (16 May 2011) | Introduction, Theorem 9/Corollary 10, Section 4.4 and Section 5 | Framework separating energy positivity, hyperbolicity and causality; no automatic theorem transfer |
| Jennings, 1412.8597v2 (21 July 2015) | Table 1; existing L36 equation map | Source-grounded next Q comparisons, in a different, neutral theory |

## Fields, conventions and changed assumptions

**Source definitions, in compact form:**

```math
Q=q_0+i\boldsymbol\sigma\cdot\mathbf q
=\cos\alpha+i\boldsymbol\sigma\cdot\mathbf n\sin\alpha,
\quad q_0^2+|\mathbf q|^2=1,
\quad\boldsymbol\Gamma_\mu={1\over2i}\operatorname{Tr}
(\boldsymbol\sigma\partial_\mu QQ^\dagger),\quad
\mathbf R_{\mu\nu}=\boldsymbol\Gamma_\mu\times\boldsymbol\Gamma_\nu,
```

```math
\mathcal L=-\kappa\left({1\over4}\mathbf R_{\mu\nu}\cdot\mathbf R^{\mu\nu}
+{q_0^{2m}\over r_0^4}\right),\quad
\kappa={\alpha_f\hbar c\over4\pi},\quad
\alpha_f={e_0^2\over4\pi\epsilon_0\hbar c},\quad m\in\mathbb N_{>0}.
```

These are the paper's local SU(2) encoding of an internal rotation field. There is no quadratic derivative term. Its electrodynamic restriction uses

```math
q_0=0,\qquad H_{\mu\nu}=\mathbf n\cdot(\partial_\mu\mathbf n\times\partial_\nu\mathbf n),
\qquad {}^*f_{\mu\nu}=-{e_0\over4\pi\epsilon_0c}H_{\mu\nu}.
```

**Our conventions:** $x^0=ct$, metric $\eta=\mathrm{diag}(+1,-1,-1,-1)$, right-handed physical and internal bases, oriented $\epsilon^{0123}=+1$. Read the dual field components as ${}^*f_{0i}=B_i$, ${}^*f_{ij}=\epsilon_{ijk}E_k/c$; raise/lower indices with the metric rather than moving stars informally. SI $\mathcal L$ has energy-density units, so the action convention is $S=c^{-1}\int\mathcal L\,d^4x$. This overall constant does not alter the equations. Cross products refer to internal vectors unless E/B are explicitly named. The degree orientation below fixes the charge sign. No independent arbitrary Maxwell potential is added to the candidate. Local lift, internal-frame and residual gauge conventions must be fixed before global sector/quantization claims; no spin/statistics conclusion is drawn.

**Interpretation:** this supplies extra internal fields, a potential, a length parameter and angular boundary data. It changes both the theory and its charged boundary sector. The smooth source-free Maxwell zero-net-flux result is therefore not evaded within its original assumptions. Static Skyrme–Faddeev Hopf charge $Q_{\rm H}$ and the boundary degree $Z$ below are different invariants; neither a label Q18 nor Q22 denotes electric charge.

## Finite energy and scale: independent reproduction

Set $\mathbf n=\hat{\mathbf r}$, $\rho=r/r_0$, $u=\cos\alpha$, $u(0)=1$, $u(\infty)=0$. With orthonormal spatial derivatives, the three connection lengths are $|\alpha'|,\sin\alpha/r,\sin\alpha/r$. Angular integration of the defined curvature gives

```math
{E\over\alpha_f\hbar c/r_0}
=\int_0^\infty\left[(u')^2+{(1-u^2)^2\over2\rho^2}
+\rho^2u^{2m}\right]d\rho,
\qquad
u''+{u(1-u^2)\over\rho^2}-m\rho^2u^{2m-1}=0.
```

For $m=3$, substitution of $u=(1+\rho^2)^{-1/2}$ makes the ODE residual identically zero. This reproduces the published hedgehog, not a newly discovered solution. The separate integrals, checked symbolically and by independent one-dimensional quadrature, are

| Term | Dimensionless integral |
|---|---:|
| Profile derivative | $\pi/16$ |
| Angular curvature | $\pi/8$ |
| Potential | $\pi/16$ |
| Total | $\pi/4=0.7853981633974483\ldots$ |

Thus $E_4=3\pi/16$, $E_0=\pi/16$, with the common energy unit understood. For the dilation $Q_\lambda(x)=Q(x/\lambda)$, our scaling calculation gives

```math
E(\lambda)=\lambda^{-1}E_4+\lambda^3E_0,\qquad
E'(1)=0\ \Longleftrightarrow\ E_4=3E_0,\qquad
E''(1)=12E_0>0.
```

This controls one scale direction. It is not a proof of stability against every field perturbation. The neutral benchmark instead balances quadratic and quartic spatial derivatives; its virial relation cannot be substituted here.

Our Cartesian expression for the hedgehog is $q_0=r_0/\sqrt{r^2+r_0^2}$, $\mathbf q=\mathbf r/\sqrt{r^2+r_0^2}$. It is smooth at the origin even though its auxiliary unit direction $\mathbf n=\hat{\mathbf r}$ is undefined there.

**Inputs versus predictions:** $E_1=\pi\alpha_f\hbar c/(4r_0)$ depends on the supplied coupling and length. Using the illustrative rounded values $\alpha_f\hbar c=1.44\,\mathrm{MeV\,fm}$ and $E_1=0.511\,\mathrm{MeV}$ gives $r_0=2.2132551\,\mathrm{fm}$. This is a calibration, not a new measurement or independent prediction of electron mass/size. Fixing $r_0$ first is required before an energy comparison can be predictive. The logarithmic sensitivity is $\partial\log E_1/\partial\log r_0=-1$. At fixed coupling the zero-core limit has divergent self-energy; a finite-mass point limit needs an additional specified prescription.

## Electric flux, and what remains undefined in the core

**Our flux derivation from the stated map:**

```math
E_i=-{e_0\over8\pi\epsilon_0}\epsilon_{ijk}H_{jk},\qquad
Z(S)={1\over4\pi}\int_S\mathbf n\cdot
(\partial_u\mathbf n\times\partial_v\mathbf n)\,du\,dv,
\qquad Q_{\rm el}(S)=\epsilon_0\oint_S\mathbf E\cdot d\mathbf S=-e_0Z(S).
```

The oriented hedgehog has $Z=1$, hence charge $-e_0$. An opposite degree reverses that sign. This quantizes the ratio $Q_{\rm el}/e_0$; the magnitude $e_0$ was already supplied. The angular boundary $\mathbf n(\Omega)$ can carry degree, whereas a constant north-pole boundary used in the neutral Hopf model cannot carry this particular flux degree.

**Diagnostic, not an adopted observable:** suppose one extends the asymptotic internal radial projection of the color electric field through the finite core. Algebra then yields

```math
\mathbf E_{\rm proj}=-{e_0\over4\pi\epsilon_0(r^2+r_0^2)}\hat{\mathbf r},\qquad
Q_{\rm enc}(R)=-e_0{R^2\over R^2+r_0^2},\qquad
\rho_{\rm proj}(r)=-{e_0r_0^2\over2\pi r(r^2+r_0^2)^2}.
```

Its integrated charge is correct, but this projected vector has no unique direction at the origin and its density has an integrable $1/r$ singularity. Smoothness of the full internal field does not establish smoothness of this chosen projection. We do not identify it as the model's unique physical finite-core charge density. A coupling to probes and a globally defined observable, with transformation and conservation laws, are unresolved requirements before finite-size interaction/scattering claims.

## Electromagnetic sector: an explicit limitation

**Our local geometric calculation:** in coordinates $(\theta,\phi)$ on the target two-sphere, $H=\sin\theta\,d\theta\wedge d\phi$. Consequently $H\wedge H=0$, which forces $\mathbf E\cdot\mathbf B=0$ for the literal pointwise electrodynamic map. This is kinematic, not a numerical tolerance or an equation-of-motion approximation.

For comparison, define two counterpropagating ordinary Maxwell plane waves, with $f=\cos k(z-ct)$, $g=\cos k(z+ct)$:

```math
\mathbf E=(a f,b g,0),\qquad
\mathbf B=(b g/c,a f/c,0),\qquad
\mathbf E\cdot\mathbf B={2ab\over c}fg.
```

All four source-free Maxwell equations hold exactly, as the verification script checks. The dot product is generally nonzero. These waves are a local counterexample to general Maxwell equivalence, not an isolated finite-energy particle example. Individual transverse waves do not establish closure under their superposition in the internal-field map. A restricted sector might remain useful, but general equivalence requires a different observable, extra fields or a demonstrated coarse-graining construction. Proposed averaging is not accepted as that demonstration.

Another source-level warning is that its electrodynamic equations allow a magnetic-current quantity $g^\mu=c\partial_\nu{}^*f^{\nu\mu}$ subject to ${}^*f_{\mu\nu}g^\nu=0$; this does not algebraically set $g^\mu=0$. A proposed Maxwell limit must recover the homogeneous equations as well as charge flux. No change to the working Maxwell simulator follows from this audit.

## Evolution: local characteristic checks

**Our principal-symbol derivation:** at a point on a static background, put $\mathbf g_i=\boldsymbol\Gamma_i$ and $\boldsymbol\Gamma_0=0$. Use a local orthonormal tangent frame for Q. Connection-frame terms without derivatives of the perturbation do not affect the principal symbol. The time-derivative Hessian, after dividing out the positive factor $\kappa$, is

```math
M=\sum_i\left(|\mathbf g_i|^2I-\mathbf g_i\mathbf g_i^T\right),\qquad
\mathbf a^TM\mathbf a=\sum_i|\mathbf a\times\mathbf g_i|^2.
```

It is positive definite when the spatial connection vectors span at least two directions, and is degenerate if they are all collinear. For a plane-wave covector $(\omega/c,\mathbf k)$, set $\mathbf b=\sum_i k_i\mathbf g_i$, $N(\mathbf b)=|\mathbf b|^2I-\mathbf b\mathbf b^T$. Direct second variation of the quartic density gives

```math
P/\kappa=\left[(\omega/c)^2-|\mathbf k|^2\right]M+N(\mathbf b).
```

For each internal vector a, Cauchy–Schwarz gives

```math
\mathbf a^TN(\mathbf b)\mathbf a
=\left|\sum_i k_i(\mathbf a\times\mathbf g_i)\right|^2
\le |\mathbf k|^2\mathbf a^TM\mathbf a.
```

Hence $0\preceq |\mathbf k|^2M-N(\mathbf b)\preceq |\mathbf k|^2M$. Where M is positive definite on a static background, the frozen characteristic squared speeds lie in $[0,c^2]$. For $\mathbf g_i=g\mathbf e_i$ they are $c^2,c^2/2,c^2/2$. The script verifies the general polynomial identity and 128 deterministic numerical crosschecks; the inequality is the proof, not the random samples.

This is a conditional local result. At a constant vacuum $M=0$. For m=3 the derivative term starts at fourth perturbative order and the potential at sixth, so there is no ordinary quadratic small-wave action around that constant vacuum. For the charged hedgehog the tangential connection decays as $1/r$; M tends to zero at infinity and has no uniform positive lower bound there. A rank-two static connection can also have a zero-speed branch. These facts call for constraint/reduced-variable and boundary analysis; they alone do not prove that every nonconstant sector is ill-posed or exclude finite-amplitude waves.

**A stronger, time-dependent local test:** choose allowed first derivatives at one point

```math
\boldsymbol\Gamma_0=h\mathbf e_3,\quad
\boldsymbol\Gamma_1=g\mathbf e_1,\quad
\boldsymbol\Gamma_2=g\mathbf e_2,\quad
\boldsymbol\Gamma_3=0,\qquad g\ne0.
```

For propagation along $x^3$, differentiating the full quartic Lagrangian gives

```math
P/\kappa=\operatorname{diag}\left(
g^2[(\omega/c)^2-k^2]+h^2k^2,
g^2[(\omega/c)^2-k^2]+h^2k^2,
2g^2[(\omega/c)^2-k^2]\right).
```

The squared characteristic speeds divided by $c^2$ are $\{1-h^2/g^2,1-h^2/g^2,1\}$. They include two negative values for (|h|>|g|), despite positive M. At $h=2g$ they are ({-3,-3,1}). Such a first jet can be assigned to a smooth local Q map; Maurer–Cartan compatibility constrains its subsequent derivatives, not these four tangent vectors at one point. This is a local principal-symbol counterexample to an unconditional all-background hyperbolicity claim. It is not a constructed global on-shell background, proof that a permitted solution reaches it, or a measured instability of the static soliton. An admissible evolution sector would have to exclude it consistently and retain that exclusion dynamically.

The potential has no derivative terms and cannot repair this principal-symbol issue by itself. Adding an ordinary quadratic kinetic term changes the model; with a nontrivial angular charged boundary it also introduces a divergent radial integral at infinity unless the boundary/field content is changed. No such repair is silently adopted. Lorentz-invariant notation and positive energy do not substitute for a causal initial-value formulation. Wong supplies relevant conditional machinery, not a blanket certificate or rejection of this particular model.

## Restricted stability and a source discrepancy

The vibration paper examines alpha/profile fluctuations with the unit-direction sector fixed, then separates spatial angular modes. Its continuous spectrum for $m\ge2$ is relevant evidence; it does not cover the coupled internal-direction modes or nonlinear stability of the full theory.

**Our radial energy Hessian**, for $u\mapsto u+\epsilon v$, fixed n and boundary-preserving perturbations, has the quadratic form

```math
\int_0^\infty[(v')^2+W(\rho)v^2]d\rho,\qquad
W={-1+3u^2\over\rho^2}+15\rho^2u^4
={2+\rho^2+14\rho^4\over\rho^2(1+\rho^2)^2}>0.
```

This establishes positivity in that restricted radial sector. It does not establish full three-dimensional energetic or dynamical stability, nor a uniform spectral gap on the infinite domain.

**Normalization discrepancy, retained rather than hidden:** direct m=3 substitution into Eq.20 of 0812.4225v1 yields $v_{20}=W/2$, whereas the printed Eq.21 labels $v_{21}=W$. We visually checked the PDF and symbolically verified $v_{21}=2v_{20}$. The Schrödinger operator in Eq.23 uses $-\Delta/2+V$. Separately, deriving motion from its Eq.19 action gives the physical operator $-\Delta+2V$. The positive sign and continuous/non-confining asymptotic behavior survive these factors; absolute frequencies must be rederived consistently before using the printed spectrum quantitatively. We do not assert an author-intended correction or certification of other versions. No published eigenfrequency is used to set a tolerance or claim agreement here.

## Predictivity, falsifiable interactions and remaining gates

| Gate | Audit outcome | Evidence still required |
|---|---|---|
| Fields/action and changed assumptions | Defined for analytical inspection | Reviewed global/lift, boundary and observable specification before implementation |
| Finite energy and length balance | m=3 hedgehog reproduced; restricted dilation minimum | Independent nonradial and radiation/boundary stability analysis |
| Charge flux | Integer ratio follows from boundary degree | Physical finite-core EM/probe map and full conservation equations |
| General electromagnetic limit | Literal pointwise map fails general Maxwell equivalence | Restricted-domain justification or independently demonstrated extension/coarse-graining |
| Causal evolution | Conditional static bound; vacuum degeneracy and adverse local jet identified | Consistent constrained admissible sector, preserved hyperbolicity and suitable estimates |
| Independent electron properties | Not demonstrated; coupling and r0 supplied | Fixed-parameter predictions compared with observation; no tuning to each target |
| Interaction assessment (INT-001) | Protocol specified below, not executed | Well-defined probes/two-body states, stress and energy balance, converged force law |
| Quantum gate (QNT-001) | Unreleased | Separate quantization, spin/statistics and experimental assessment |

If the earlier gates are resolved, fix one parameter set and derive the same physical charge from flux and probe coupling. For two well-separated cores test

```math
E_{12}(R)-E_1-E_2\sim {Z_1Z_2e_0^2\over4\pi\epsilon_0R},\qquad
F_R=-\partial_RE_{\rm int}.
```

Vary separation, orientation, equal/opposite degrees, mesh and domain; integrate stress over enclosing surfaces and compare with the energy derivative, including outgoing radiation during motion. Fix self-energy subtraction and outer-boundary conventions before comparing R. An imposed Coulomb boundary/probe law cannot count as an independently generated interaction law. Extract finite-size corrections with the same r0 rather than refitting it. The source's point-limit force argument motivates this test; it does not replace a finite-core two-body result. These are falsification conditions, not authorization for a large new run now.

## Decision, next work and reproducibility

The [decision record](../../docs/decisions/ADR-0008-charged-model-audit.md) records the completed audit and deferred charged dynamics. The user's follow-up instruction is explicit: return to more Q values after this audit because Q18 did not reproduce the proposed hyperbolic basin. The [next plan](../../docs/plans/post-audit-q-assessment.md) prioritizes Q18 diagnosis, adjacent Q17/Q19 controls and a retained Q22 control. That neutral-model study does not require solving the charged candidate's open problems first. No acceptance gate or failed Q18 result is removed.

Run from the repository, using the existing lock:

```bash
uv sync --frozen --all-groups --python 3.12.14
uv run --frozen --python 3.12.14 python \
  reports/charged-model-audit-20261101/verify_algebra.py
python3 scripts/check_docs.py
python3 scripts/check_pr36_staged_recovery.py
python3 scripts/check_workstation_evidence.py
python3 scripts/check_recovered_text_transfer.py --allow-incomplete
```

The verifier prints UTC/Melbourne start/end stamps. To retain a new ledger, supply `--output PATH` with a new filename; existing evidence is not overwritten. The retained ledger records Python, dependency versions, parent commit, script SHA-256, numerical seed and check timestamps. The original 191-file recovery manifest remains intact. Historical STATUS and bibliography files in that manifest are not rewritten; the dated development-plan entry and source supplement expose this audit without weakening recovery checks. General CI behavior is unchanged; no workflow, production solver, coupling, dependency or numerical threshold is changed.

Requirements supported: GOV-002, SCI-003/004, MOD-001/002 and REP-001/002. MOD/INT/QNT physical acceptance is not completed. Full literature review, charged dynamics, quantum claims and general isolated-boundary validation remain separate.
