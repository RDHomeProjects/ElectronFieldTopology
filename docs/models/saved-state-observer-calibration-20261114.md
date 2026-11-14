# Saved-state observer calibration

Prepared for the 35-state run `20261114t000026z-1620e2b1`. Evidence SHA256:
`293f5dc04a5612622c30310ca461a9e43070f4995589e5355427ee54e4702bf7`.
Timestamps are supplied in UTC and Australia/Melbourne in the machine records.

## Equations, conventions and retained findings

The measurement is classical Maxwell E/B in model units c=epsilon0=mu0=1,
float64. It uses the frozen archived native stagger offsets, analytical
solutions and synchronized B convention. The existing Hopfion evaluator maps
Valverde et al., arXiv:2003.01896v1, Eqs. 1–5 (Bateman p=q=1). Its exact source
hash and evolution source hash are checked. Packet modes and amplitudes are
the same eight-mode analytical periodic reference in archived numerics.py.
This activity changes no Maxwell equation or SF model and adds no new
literature or mathematical-existence claim. Applicable provenance is the
existing L03 numerical reference and controlled-dependencies specification.

For the original observer O, vectors satisfy total=evolution+baseline:
evolution=O(Fnumerical)-O(Fexact-native), baseline=O(Fexact-native)-Fexact.
Every normalized squared norm uses the same integral of |Fexact|². Retain
2<evolution,baseline> and check squared-norm closure; scalar norms are not
additive. Interpolation stays componentwise linear; synchronization uses a
temporary B_plus and preserves saved E/B_half. The physical cube is [-2,2]^3.

Prior outcomes remain: packet mesh prediction/refinement pass; Hopfion mesh
prediction misses 5e-6 at N81; duration prediction passes but only one
qualifying refinement round was obtained. This calibration does not close
duration, select a new physical mesh, revise physical fits or run SF dynamics.

## Held variables and independent axes

Use six separate fixed states: Hopfion and packet at native N49,81,129, all
with L8, T1, dt1/960, phase/orientation/startup/boundaries unchanged. Native N
labels strata; it is not an independently varied input in a calibration fit.
All 35 source states are retained and archived; only these six are remeasured.

1. At each fixed state, vary only trapezoidal observer count M, starting with
   33,49,65,97. Use at most four further counts, bounded by 257. The next count
   is chosen before measurement from the previous norm changes and local
   slope-change indicator, increasing resolution faster where unresolved
   structure is large. Counts 101,157,229 are reserved and excluded from
   adaptation. All axes use identical M and the same physical cube.
2. Separately vary only cell-Gauss order 2,3, and if needed 4. For each E/B
   component, split the integration cube at that component's native knots;
   use tensor Gauss–Legendre within each clipped cell. The evolution vector
   component is piecewise trilinear, so its squared numerator is integrated
   exactly by order 2 in exact arithmetic. Analytical-denominator and
   baseline/total integrals still require quadrature checks. Agreement of
   successive orders is empirical evidence, not a rigorous global bound.
3. At the final uniform count, compare an independent composite midpoint
   rule on the same cube and same saved state. It changes the observation
   sampling rule, not the physical field, cube or numerical trajectory.

The budget is **1e-6 fractional field norm** for each of evolution, baseline
and total, one fifth of the previous 5e-6 mesh prediction limit. Uniform
readiness requires a passing Gauss order comparison, two consecutive adaptive
rounds with all three norm changes and Gauss-reference differences <=1e-6,
and the final midpoint/reference comparison <=1e-6. Budget exhaustion is
retained. This gives six-anchor readiness only, not all-mesh certification.

## Empirical dependency models and fresh checks

For each fixed state and each response, fit against x=1/(M-1), proportional
to observer spacing. Candidate constant/linear/quadratic/exponential/cubic
models use development leave-one-out selection. Freeze coefficients and
selection before the three reserved observer counts. Publish coefficients,
possible extrema/inflections, residuals and prediction outcomes. Prediction
passes only if each primary-response maximum is <=1e-6. It is separate from
quadrature readiness. These are fresh observation locations on existing fields,
not new physical validation meshes. Old physical validation remains inspected.

An empirical curve with an implausible extrapolated limit is not a continuum
certificate. Local slope/curvature changes may reflect interpolation-cell
alignment and must not be called physical bifurcations. Production calibration
can legitimately finish with failed readiness or prediction checks.

## Cost, provenance and next decision

At most six times eleven uniform observer evaluations (four seeds, four
adaptive, three validation), three Gauss orders and one midpoint control:
90 integrations of an observation norm at most; zero new physical evolutions.
Slab processing bounds observer memory; no GPU/precision/backend change is
introduced. Hashes/NPZ CRCs authenticate inputs; source arrays are checked again
after measurement. Sealed checkpoints, code/config/thread identity, choice
chronology and frozen fits permit safe resume. Reports carry both timestamps.

After review, prefer an empirically adequate observation contract. If the
six anchors pass, extend that contract to all mesh states before replacing a
physical dependency fit. Revised physical fits need pre-reserved new meshes.
Q2/Q3 prior-evidence inventory may proceed separately; Q1 stays parked and
Q4/Q7 retain their admission/preparation blocks. Original physical gates and
electron/charge/spin/isolation limitations remain unchanged. AI-assisted code
and assessment are disclosed; publication is not scientific peer review.
