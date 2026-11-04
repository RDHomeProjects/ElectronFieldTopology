# ADR-0011 - Full-field motion diagnosis and conditional spin-method follow-up

Recorded: UTC 2026-11-03T23:43:39.658706+00:00; Melbourne 2026-11-04T10:43:39.658706+11:00.
Status: diagnostic implementation prepared under the maintainer's next-step request.

PR52 records six bounded low-Q passes and unresolved shape/momentum/tail sensitivity.
The maintainer supplied three configuration-space quantization papers and requested
the next local analysis in accordance with those discussions.

1. Run [read-only full-field diagnostics](../plans/sf-motion-diagnostics.md) on the
   retained campaign before selecting more production runs. Preserve all failed gates.
2. Measure classical kinetic/inertia matrices now to expose discretization/domain
   sensitivity relevant to the future quantum-method stage. Do not introduce a
   mass term, electromagnetic coupling, smoothing or a new physical model here.
3. Keep the [L41-L43 method assessment](../literature/soliton-quantization-methods.md)
   and conditional Q1/Q2 FR/quantization benchmark in the plan. Their quantum
   assumptions do not establish classical emergence of spin or electric charge.
4. Keep Q17/Q19 motion behind adequate low-Q control; retain the Q18 fine-start/
   conditioning and additional-Q follow-up. Charged dynamics remains deferred under
   ADR-0008. Stern-Gerlach simulation requires a specified interaction/detector model.

Alternative: immediately repeat a broad finer/longer run. Deferred because the same
errors could be reproduced at higher cost before initialization/sampling causes are
distinguished. This decision authorizes diagnostics within the existing action and
does not assert numerical or physical gate completion. Full workstation fields remain
local; compact diagnostic results are separately timestamped and transferable.
