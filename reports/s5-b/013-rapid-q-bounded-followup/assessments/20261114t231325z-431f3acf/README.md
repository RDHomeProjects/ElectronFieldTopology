# Completed bounded rapid Q follow-up assessment

Run: `20261114t132254z-9e6c35d4`; correct parent: `20261114t094318z-7800d5c4`.

[Browser assessment and charts](ASSESSMENT.html) · [Machine-readable assessment](ASSESSMENT.json) · [Original compact evidence](evidence.zip)

Seven jobs completed 645/650 additional accepted optimizer steps, in approximately 60.55 minutes. No new strict static survivor, hard Q rejection or motion case resulted. Six allocations exhausted their declared budgets unresolved. Q5 stopped five steps early at native iteration 95 because its approximate Hopf-magnitude error reached 6.356%, above the unchanged 5% admission limit; the corner cone remained positive. This is representation-admission loss, not a certificate of continuum topology change.

| Branch | Grid | Force / gate | Acceleration / gate | Disposition |
|---|---:|---:|---:|---|
| q6-axial6-1 | 97³ | 13.967 | 7.667 | budget_exhausted_unresolved |
| q4-axial22 | 121³ | 1.727 | 2.101 | budget_exhausted_unresolved |
| q7-trefoil | 121³ | 6.259 | 5.642 | budget_exhausted_unresolved |
| q8-trefoil32-1-2 | 121³ | 3.643 | 6.220 | budget_exhausted_unresolved |
| q5-trefoil32-1-1 | 97³ | 2073.982 | 8028.211 | deferred_representation_loss |
| q9-trefoil32-3-1 | 145³ | 573.442 | 961.553 | budget_exhausted_unresolved |
| q10-trefoil32-2-2 | 145³ | 78.692 | 287.961 | budget_exhausted_unresolved |

Both stationarity ratios must be ≤1, alongside unchanged representation and rest-tail gates. Q4 briefly passed force alone at iteration 1210, with acceleration still 1.586 times its limit. Its endpoint plateaued. Q6 and Q7 ended with larger residuals despite decreasing energy. Q8 reduced force/acceleration by approximately 4.75/4.25 times. Q10 improved by approximately 18.5/10.6 times but remains far from admission. Delayed progress outside the original priority cutoff supports a small rescue allocation; it does not measure a physical false-negative rate.

All 93 compact payload hashes and 27 result seals agree. The recorded local full-field/CPU/device checks passed; this assessment did not independently replay the 29 full NPZ fields (about 3.26 GiB). Those files remain at their workstation locations. Compact evidence and this commit are not an archive backup of those fields. Preserve them and previous source runs. Exact screen optimizer continuation and the explicit legacy Q4/Q7 conjugacy/step-length restarts remain distinguished.

All 56 delivered fit models were independently reproduced from recorded histories. Correlated observations, oscillation and poor extrapolation preclude a reliable passing-time estimate. Optimizer iterations and all values are dimensionless model quantities, not physical electron evolution. No electric charge, quantum spin or final knot identification is certified.

## Proposed next work — unexecuted

1. Inspect retained Q4/Q6 residual spatial structure and optimizer conditioning before further blanket iteration extensions. Falling energy alone does not establish stationarity.
2. Consider bounded 50-step continuation at the unchanged grid and box for Q8, with a smaller Q10 delayed-progress control. Declare budgets in a separate preparation; none is authorized or scheduled by this record-only package.
3. Test Q5 resolution sensitivity from the retained iteration-50 pre-loss state, changing only resolution at fixed box and lineage. Audit interpolation and all gates before relaxation; do not reuse the failed endpoint as admitted Q5.
4. Explicitly defer Q7/Q9 pending diagnostics. Any optimizer comparison changes one numerical variable at a time and retains the original method as a control.
5. Strict survivors must still pass mesh/domain/boost admission before motion. Q1 remains parked; Q2 remains the reference. Preserve all unresolved and negative outcomes.

The next campaign has not been prepared or run. This record-only publication changes documentation and evidence records, not scientific software, gates, dependencies or raw results.
