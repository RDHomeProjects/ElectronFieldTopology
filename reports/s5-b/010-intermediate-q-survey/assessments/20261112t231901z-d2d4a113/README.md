# Q3 sampling/boundary assessment and independent method comparison

Completed input: run 20261112t133212z-4c066e0b, twelve initial-only cases in 38 minutes 50 seconds. Finish 2026-11-12 14:11:02 UTC / 2026-11-13 01:11:02 Australia/Melbourne. Unchanged sampling-boundary-evidence.zip and earlier evidence are retained here. Compact receipts are auditable; full arrays remain local/archived and were not independently replayed here.

| Configuration | z initial speed error % | x initial speed error % |
|---|---:|---:|
| 121 native | 0.212369 | 0.001599 |
| 121 padded | 0.211860 | 0.001379 |
| 145 native | 1.056717 | 0.816608 |
| 145 padded | 1.056717 | 0.816608 |
| 145 padded half-cell | 0.611557 | 0.634376 |
| 169 refined | 0.071573 | 0.098348 |

Fine-mesh padding leaves initial speed unchanged. Native free-interior arrays match padded reconstructions exactly. The 121 wall removal changes error only by about 0.00051 pp (z) and 0.00022 pp (x). Moving the 145 profile half a lab cell changes axial rates from below to above beta: z 0.296829850 to 0.301834670, x 0.297552608 to 0.301898109. Tested alignment matters strongly. Reduced residual RMS under padding is vacuum dilution: the corresponding physical-volume L2 norm at 145 is unchanged. The 169 zero-phase results are promising but neither phase envelopes nor continuum convergence. The retained rest field is still 145 cubed.

## Prepared comparison

Use the fixed finest padded geometry (197 x 197 x 207, permuted by direction), the same sealed rest field, normalized cubic reconstruction and requested beta 0.3. For x and z evaluate phases 0, 1/4, 1/2, 3/4. On each identical n/v state evaluate the original D4 action and a separately derived second-order positive-edge/centered-jet SF action. Both approximate the same continuum model; native Hamiltonians/densities differ at finite h. No SF physical-time integrator is added or run. Recalculate zero-phase D4 as a replay through the new common observer and require original state seals and scalar agreement.

Native density/rates and a common D4 continuum-density observer are reported separately. The common observer is independently qualified by directional density probes and manufactured controls; its D4 derivative is not an unbiased continuum ground truth. Shared reconstruction can produce common error. Preserve every phase and all original gates; no favorable-phase selection or phase average replaces a failed case. The D2 action is detailed in METHOD-SPEC.md and qualified against an independent finite variation of its action. Instantaneous native-H balance is a calculation guard, not evidence of trajectory conservation.

## Maxwell comparison

The executable Yee benchmark is separate from SF. It uses analytical Maxwell Hopfions at native edge/face locations and staggered times, plus periodic plane waves cross-checked with the existing Fourier solver. Hopfion outer guard values are analytically prescribed and only interior errors are measured. This is a driven-boundary numerical control, not an isolated-source-free whole-box conservation test or a matched-boundary Fourier Hopfion comparison. It makes no exact-nullness, helicity or knot-persistence claim. See MAXWELL-VALIDATION.md.

Keep the focused literature plan and five assessment dimensions: topology; energy localization; classical dynamics/convergence; quantum-state/statistics; particle-specific observables. The previous source review plan is retained in LITERATURE-PLAN.md, not marked complete. No Yang-Mills proof/model equivalence, electric charge, electron spin/statistics or SI calibration follows from numerical agreement. Q1 parked, Q2 reference, Q4/Q7 unresolved.

Open sampling-boundary/REPORT.html for the latest completed input. New SF and Maxwell production runs remain pending on the workstation. Required outcomes before later short SF trajectories: qualified method controls, phase ranges/component trends and refinement plan reviewed. No convergence claim from one resolution. Native original 1% speed criterion unchanged.
