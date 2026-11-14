# Cell-aware spacing measurements on fixed saved states

This follows the assessed six-state observer calibration whose compact ZIP
SHA256 is `04cd1d5d7ffc79cef09dcd5c77dfd27008e8760f843f5d3a420b20a62034419d`.
The physical source is the unchanged 35-state run
`20261114t000026z-1620e2b1`, evidence SHA256
`293f5dc04a5612622c30310ca461a9e43070f4995589e5355427ee54e4702bf7`.
Machine records and all generated reports include UTC and Australia/Melbourne.

## Retained equations and measurement contract

Use the archived observation kernel byte-exact. Classical model units are
c=epsilon0=mu0=1; native arrays remain float64. The Bateman (1,1) analytical
Hopfion evaluator is the existing Valverde et al., arXiv:2003.01896v1,
Eqs. 1–5 map in fields.py. The eight-mode periodic packet, native Yee offsets,
analytical boundary convention and temporary synchronized B construction stay
unchanged. No Maxwell/SF equation, physical integration, initial state, phase,
orientation, boundary, native mesh or time-step is altered. The existing L03
and B0-H11 source mapping applies; this adds no new physics citation or claim.

The observer is componentwise linear interpolation over the same physical
cube [-2,2]^3. Split each component integral at its own native interpolation
knots and integrate within clipped cells using tensor Gauss–Legendre.
For observed and exact-native interpolated fields, record evolution, baseline,
total normalized norms and the vector cross term on a common exact-field
denominator. Scalar norms are not additive. The piecewise trilinear evolution
component has a quadratic square, so two-point cell Gauss is exact for that
numerator in exact arithmetic; analytical denominators, baseline and cross
terms still need numerical qualification. Order agreement is empirical.

## Stage A: higher-order anchor confirmation

At each field's native N49,81,129 state, reuse its authenticated order-4 receipt
from the completed calibration and measure orders 5 and 6 on the same saved
arrays. Require both 4→5 and 5→6 differences to be <=1e-6 fractional norm for
each of evolution, interpolation baseline and total. The budget is unchanged
and is separate from the old 5e-6 physical-mesh fit tolerance. Original failed
reference/readiness/prediction results remain unchanged in their records.

All six anchors must satisfy the registered common all-response contract
before Stage B begins. If one fails, retain every measured result, finish as
complete_pending_review with anchor-contract-unresolved, and explicitly skip
the remaining nineteen states. There is no tolerance relaxation, hidden order
increase or physical rerun. This new contract does not rewrite old stopping
conditions or promote a failed original result to a pass.

## Stage B: consistent measurement of all saved spacing states

The source contains sixteen Hopfion and nine packet spatial configurations,
all L8, T1, dt1/960, unrotated with fixed startup/boundaries. Their physical
independent variable is h=8/N, with all other inputs held fixed. Measure orders
5 and 6 at all states, reusing Stage A measurements for the six anchors. Adopt
order 6 as the common response for every descriptive curve; never mix orders
across meshes. Retain the order-5 comparison and all original 33-node metrics.

Each later state's all-response check requires 5→6 <=1e-6 for all three norms.
A later scientific failure does not abort measurements of the other states;
it stays visible in per-response and aggregate readiness flags. At most fifty
new norm integrations and six reused order-4 receipts occur. Native fields
are authenticated by size/hash/NPZ CRC before observation and hash afterwards.
No new field arrays are generated or uploaded. The original full-field archive
is reused; this pack does not duplicate its release upload or delete local data.

## Descriptive relationships and future validation

Fit the order-6 observations against h separately for each field and response.
Candidate constant, linear, quadratic, cubic and exponential forms retain the
existing development leave-one-out selection. Add pure power A*(h/hmax)^p and
nonnegative-offset power a+b*(h/hmax)^p, with A,a,b>=0 and 0.2<=p<=6. The
original unconstrained negative-floor power candidate is excluded from this
new model set; its earlier measured result is not changed. Polynomial and
exponential extrapolations also remain qualified to the tested finite range.

All existing physical points, including previously inspected validation
meshes, are development context. Report coefficients, units, source points,+fit residuals, leave-one-out errors and possible polynomial features. Do not
claim new held-out prediction success. Fit readiness follows the measured
per-response order checks; unqualified curves remain exploratory. No optimum
mesh is selected without a separately declared accuracy/cost objective.

Reserve native grids N73,103,123 for a possible later physical confirmation;
assert that none already occurs in the supplied spatial source. Freeze the
descriptive fits/config/source hashes before any such future measurements.
This handover does not run the reserved physical grids. If the observation
contract or physical setup changes, declare and freeze a new model first.

## Reproducibility and the wider plan

Preserve exact code/config/source identities and thread settings across resume.
Sealed norm checkpoints permit reuse; interrupted measurements are repeated.
Record source-case and state hashes, reuse provenance, full original values,
all failures and skipped phases. The fixed kernel and independent analytic
integral controls are separate from empirical constrained-fit controls.

Qualification uses temporary reduced fields as explicitly labelled preparation;
production only reads saved fields. All GitHub actions run on the workstation.
New immutable measurement/assessment/preparation records and the actual current
roadmap are updated together; earlier reports stay unchanged. AI assistance is
disclosed and does not constitute independent scientific peer review.

Q2 prior-evidence inventory and a single Q3 dependency can be prepared separately.
No new SF trajectory, duration confirmation, isolated-motion qualification,
physical confinement, charge, quantum spin or electron acceptance follows.
Q1 remains parked; Q4/Q7 retain their original preparation/admission blocks.
