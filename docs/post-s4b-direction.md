# Post-S4-B assessment and recommended next steps

31 October 2026 (Australia/Melbourne). PR 31 merged at `0be60b6e7ff3c7a43580a069ce7f6040a7f8d90a`, after all nine final-head workflows passed. The [report](../reports/s4-b/README.md) preserves 116 local tests, ten instrument checks and all numerical outcomes. This assessment recommends scope; it does not authorise or implement a new numerical search, level-4 acquisition or modified dynamics.

## Assessment

Retain S4 as the validated Maxwell/topology reference. Change the immediate emphasis from accumulating more knot examples to diagnosing unresolved return dynamics, then deciding whether a different physical model is warranted for the particle objective. Broad optimisation and a universal knot identifier currently have lower decision value than those questions.

S4-B's 24 cases are **12 initial seed choices observed at two related times**, not 24 independent random trajectories. Eight cases are known core controls. There are eight distinct off-core initial seeds: two Hopfion seeds close at both times, and six higher-family seeds remain unresolved at both times. The reported 12/24 closure count is therefore an instrument result, not an estimated probability that arbitrary field lines close.

The coarse/fine study simultaneously changes arclength budget, ODE tolerance, maximum step and polygon sampling. This checks joint robustness for accepted closures but does not isolate which control explains an unresolved outcome. The next diagnostic should vary those controls separately. Determinants and signed links are useful independent checks; a determinant is not a unique knot name and polygon agreement is not a certified continuous-line isotopy.

## Proposed priorities

| Workstream | Suitability and priority | Recommended handling |
|---|---|---|
| Diagnose unresolved off-core returns | Highest immediate S4 priority | Small return-map and independently varied numerical-control study |
| Broader seeds or more Bateman families | Useful eventually for topology coverage | Defer until the present return structure and guard sensitivity are understood |
| Complete knot identification | Needed if a later decision depends on exact knot type | Use stronger independent invariants/certificates on shortlisted genuinely closed curves; do not make a universal classifier the immediate project bottleneck |
| Near-zero and radius robustness | Necessary numerical validation | Vary guard floor and observation radius independently, preserving every outcome |
| Long-time isolated simulations/open boundaries | Conditional | Design equation-level reflection/loss controls once the intended dynamics and observables are specified |
| S5 model feasibility | High value for the particle objective | Prepare a focused paper/action comparison with explicit rejection gates before coding new dynamics |
| S6 interactions and S7 quantum matching | Premature as an implementation programme | Keep conditional on an admissible localized model and independent charge/quantum mechanisms |
| Complete checkpoint publication/literature backlog | Reproducibility work remains useful | Preserve separately; the text transfer and 1% dataset publication did not close the scientific review; level 4 stays deferred |

## Recommended bounded S4-C proposal

Start with one currently unresolved initial seed from each higher family, plus known periodic and nonclosing controls. Use the other unresolved seeds for replication after the diagnostic works. At fixed field/time and solver settings, compare arclength budgets 20/40/80. Independently compare three tolerances, then guard floors and observation radii within declared bounds. Do not change all controls together or merely increase every budget until something closes.

Retain the actual return-section positions, not only distance to the starting point. Examine return maps, recurrence distances and, where a suitable angular coordinate is justified, estimated winding/rotation behaviour. Validate any proposed classifier against known periodic and irrational torus-flow controls. Finite observations may support an interpretation but cannot alone prove quasiperiodicity or nonclosure. Establish a source-mapped invariant surface/first integral before claiming the sampled Maxwell trajectory lies on a particular torus.

Exit gate: identify solver-, budget-, guard- or domain-sensitive cases and state what remains genuinely unresolved. Classify a curve as a closure candidate only under the existing position/tangent/refinement requirements. If the controls do not distinguish the possibilities, retain an inconclusive result. This is a proposed compact follow-up, not a claim that S4-B has already computed return maps or rotation numbers.

## Why the particle objective needs a separate model decision

For smooth source-free Maxwell fields on ordinary space, Gauss's law supplies zero net electric flux through a closed surface. Knot complexity does not change that assumption. The existing [S3-B energy diagnostics](../reports/s3-b/README.md) separately show spreading for the measured Hopfion baseline. Topological persistence must remain distinct from energy localization.

For the relevant Hopf-type Bateman class, Bode's [arXiv:2409.20357v1, Theorem 1.8 and Section 6](https://arxiv.org/html/2409.20357v1) state that the transported set of initially closed field lines eventually leaves every fixed compact set. This is a theorem about those field-line sets in that class. It is not by itself an energy-containment theorem for arbitrary moving regions or an exclusion of other field theories. Final journal/preprint version reconciliation remains pending. Bode–Peralta-Salas [v2, Section 1.1 and Section 6](https://arxiv.org/html/2302.01043v2) separately distinguish preserved topological structures and invariant tori from the statement that every orbit is periodic.

Our inference is that generating more examples in the present class cannot, by itself, supply the missing binding or electric-charge mechanism. This supports changing research priority while retaining the validated Maxwell reference and its negative results. It does not establish that every electromagnetic explanation is impossible or that a particular nonlinear model works.

For S5, compare a small number of explicit actions/equations against: finite-energy localization, an energy/stability argument under admissible perturbations, charge and changed Gauss-law assumptions, scale setting and externally supplied constants, causal/well-posed evolution, and a demonstrable change to the relevant solution dynamics. Adding a named nonlinear term is not sufficient. Keep classical angular momentum, quantum spin/statistics and precision-electron predictions separate. Select no model until those constraints and the exact equation sources are reviewed.

## Disposition

The bounded S4-B instrument tranche is accepted through the maintainer-authorised merge. The full S4 stage, comprehensive literature review and S5–S7 gates are not declared complete. Recommend **bounded return-map diagnosis next, followed by a model-feasibility decision**, rather than a broad Maxwell-knot search. No future stage is implemented by this assessment. AI assisted this assessment; source theorems, measured results and project recommendations are distinguished above.
