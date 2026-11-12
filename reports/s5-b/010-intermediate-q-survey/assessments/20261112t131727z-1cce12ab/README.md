# Q3 fixed-rest sampling assessment and next bounded diagnostic

The unchanged initialization-evidence.zip contains run 20261112t125541z-b1a86b59. It completed six cases in 388.071619 seconds, ending 2026-11-12 13:02:09 UTC / 2026-11-13 00:02:09 Australia/Melbourne. Original source, observation and initial-field evidence are retained unchanged here. No earlier record is overwritten. Full arrays stay local/in the verified archive; compact auditing is not independent field replay.

| Nominal lab nodes | Initial z vector speed error % | Initial x vector speed error % |
|---|---:|---:|
| 97 | 0.792607385 | 0.404446072 |
| 121 | 0.212368727 | 0.001598930 |
| 145 | 1.056716645 | 0.816608064 |

The 145-node state seals and all overlapping initial-field diagnostics exactly reproduce the earlier evidence. The near-zero 121 x error involves cancellation: axial P/E is 0.253698% above beta, while the weighted continuity residual contributes -0.254804%, both percentages relative to beta 0.3. It is not a converged or accepted motion result. Do not select a grid merely because its net speed error is small.

Cubic derivative probes decrease by about sixteen when perturbations decrease fourfold, consistent with the centered numerical check at the sampled points. The identical point set across resolutions tests the interpolant, not independent lab-grid convergence. Coarse held-layer projection maxima are about 0.00155 and 0.000483; free-node changes are at roundoff. Changing h changes the physical thickness of two held layers. This comparison therefore does not isolate interior discretization from boundary projection.

## Prepared numerical diagnostic

For each direction z and x, compute six initial-only cases from the same sealed q3-axial-fine-warm field: 121-native; 121-pad; 145-native; 145-pad; 145-half; 169-refine. The 121-pad and 145-pad pairs add twelve samples on each side of every lab axis, keeping nominal axis spacings and original interior coordinates. Rectangular lengths expand by 24 times each original axis spacing, rather than silently retuning h to a new cubic box. The same rest interpolant is evaluated with its existing constant north exterior. The rest field is not re-relaxed, rescaled or refined.

The padding pair removes the former held-layer constraint at the old wall and moves it outward. Report differences on old held layers separately from old free interior, whose reconstruction must agree within roundoff. This tests the numerical wall/extension treatment; it is not independent larger-domain equilibrium evidence. half samples the profile half a lab cell away in the boost direction within the padded box; it shifts the profile relative to walls, not just coordinate labels. Report it as a combined sampling-phase/position control until residual wall sensitivity is quantified. 169-refine uses exactly the 145-pad physical box, with finer lab sampling and the rest resolution held at 145 cubed. Its actual spacings are set by that fixed box and the finer node counts; it is not a padding pair against an uncomputed 169-native case.

Global centroid/density rates and cancellation terms remain separate. A common physical cube of half-width six reports truncated energy/momentum integrals, node counts and quadrature scope; its ratio must not be interpreted as isolated-region velocity. Original 145-native state seals must reproduce. No beta adjustment, interpolation substitution, smoothing, optimizer, physical-time step or new admission flag is generated. Check geometry/projection and component trends before selecting later short evolution. No Richardson order is assigned.

## Focused literature plan and assessment dimensions

See LITERATURE-PLAN.md and bibliography-additions.json. Connect numerical work to the five distinct questions: topology, localization, classical dynamics, quantum interpretation and particle-specific observables. Yang-Mills construction does not certify our effective model; Maxwell knots are distinct from SF Hopfions; adding a Dirac electron field is not deriving the electron. Preserve charge, spin/statistics and SI calibration limitations. Q1 parked, Q2 reference, Q4/Q7 unresolved. No new evolution is authorized by this preparation record.

Open initialization/REPORT.html for the latest completed browser report, initial-field/REPORT.html for the preceding diagnostic and REPORT.html for observation controls. The new production sampling/boundary results remain pending. Requirements: NUM-001/002/003, REP-001/002, REL-002, SCI-003/004. Equation map: repository docs/models/SF-boost-reconstruction.md and SF-physical-time.md; no new physical equation is introduced.
