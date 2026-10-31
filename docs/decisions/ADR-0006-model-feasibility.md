# ADR-0006 — Model-feasibility decision after bounded return-map diagnosis

Date: 31 October 2026 (Australia/Melbourne). Status: decision submitted for maintainer review in the authorised S4-C PR. [Issue 33](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/33). This records explicit dispositions; it does not implement extended dynamics or claim a validated electron model.

## Evidence considered

Read [the measured diagnosis](../../reports/s4-c/README.md), [the return-map specification](../models/B0-S4C-ReturnMap.md) and [the primary-equation feasibility audit](../models/S5-feasibility-audit.md). The study independently varies numerical controls for three chosen Maxwell seeds, replicates three more, and validates section-event accuracy against manufactured torus controls. It is a finite return-sequence diagnosis, not a complete map or proof of an invariant torus.

Completed comparisons support reproducibility within the tested controls. Some runs are evaluation-limited and some short budgets contain too few events; both remain explicit. Neither failure to find closure nor successful geometric controls establishes a physical binding mechanism. The feasibility decision additionally uses the baseline charge constraint, retained energy-localisation evidence and inspected action structures. Even later closure of an unresolved orbit would not remove those independent gates.

## Decision

| Route | Disposition | Reason and allowed next scope |
|---|---|---|
| More knots in the unchanged smooth source-free Maxwell baseline as a charged bound-electron route | **No-go for that route; retain B0 as reference** | More field-line topology supplies neither a changed charge law nor a demonstrated energy-binding mechanism. This is scoped to the stated baseline, not every field theory. |
| Replace Maxwell by smooth invariant-based NLED while retaining the same null configurations | **No-go as a binding fix for that retained sector** | The inspected null-invariant substitution leaves those background solutions unchanged. Other non-null sectors and perturbations are not excluded; they require a separate proposal and checks. |
| Skyrme–Faddeev static energy as a controlled mechanism reference | **Conditional-go to a bounded S5-A static-energy specification/validation** | Quadratic/quartic derivative scaling supplies a concrete competing-scale mechanism with extra unit-vector fields. Fix coefficients; validate constraints, gradient and scaling/virial accounting independently. Do not present this neutral topological charge as electric charge or implement time evolution before its full action/causal map is reviewed. |
| Faber–Kobushkin charged internal-field model | **Defer a numerical implementation** | It is charge-relevant, but needs independent finite-size energy/charge, characteristic, stability and parameter audits. Elementary-charge normalization and r0 are inputs; their presence limits prediction claims rather than alone proving infeasibility. Keep its targeted equation review as a comparison, not an accepted electron theory. |

No candidate is selected as a physically adequate electron model. The selected next feasibility target is **a small, fixed-coupling Skyrme–Faddeev static-energy reference**, solely to test a binding-mechanism methodology. The charge-focused internal-field alternative stays on the analytical audit queue. This is a bounded research-priority choice, not permission for broad soliton optimisation, a full nonlinear solver or parameter fitting to electron data.

## Required S5-A acceptance before a later dynamics decision

1. Declare the new model ID, fields, unit constraint, exact source-version/normalization mapping and changed assumptions relative to B0. Preserve all Maxwell controls separately.
2. Specify finite-energy boundary conditions and report every imposed coefficient and length scale. Do not identify a fitted scale with a prediction.
3. Validate energy and constrained variations against independent symbolic/finite-difference references. Check the dilation/virial relation as a measured residual with fixed couplings, not by adjusting a coupling to force agreement.
4. Keep static energy minima, minimisation iterations, actual time evolution and stability under general perturbations distinct. Review a full causal/well-posed action and conserved quantities before any dynamical solver.
5. Record the electric-charge gap explicitly; any charged proposal needs a separate field/source/topology and flux map. Hopf charge, electric charge, classical angular momentum and quantum spin/statistics remain different observables.

## Consequences and stop rules

Stop expanding the current null-family catalogue solely in pursuit of electron binding. Retain its diagnostic tools, unresolved records and negative results. No blanket exclusion of non-null NLED or other field theories is inferred. No S6 interaction calculation or S7 quantum comparison is released by this decision.

S4-C's fixed experiment is complete only to its stated numerical/observation limits; broader source review, full dataset publication and final-version reconciliation remain unfinished. Level 4 stays deferred. If independent variations reveal instability or a control fails, retain that outcome and repair the instrument before attaching a stronger physical interpretation. The existing S4-B report and hashes remain historical evidence, not rewritten output.

AI assisted this assessment. Primary papers supply the inspected equations; scale derivations are identified as project algebra, and finite numerical observations do not replace expert scientific review.
