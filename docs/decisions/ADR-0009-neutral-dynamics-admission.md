# ADR-0009 — Neutral dynamics admission before free-flight evolution

Recorded: 2026-11-02T08:48:53.481631+00:00 UTC; 2026-11-02T19:48:53.481631+11:00 Australia/Melbourne. Status: maintainer-requested preparation;
scientific model acceptance and physical-time solver remain open.

PR50 merged the Q18/neighbour evidence. The maintainer then requested that the
research assess candidates while moving at speed, and authorised progression to
the next step with local workstation commands. A new dynamics specification is
necessary because the current Sobolev-CG minimizer has no physical time or momentum.

1. Prioritize [neutral relativistic SF specification and admission](../models/SF-relativistic.md),
   followed by verified low-Q physical-time evolution and then a selected higher-Q
   free-flight benchmark. This is a neutral reference, not an adopted electron model.
2. Retain the charged model deferral under [ADR-0008](ADR-0008-charged-model-audit.md).
   A moving neutral knot does not resolve charge, spin/statistics or quantum gates.
3. Execute read-only admission on all 31 authenticated workstation endpoints,
   including finite-grid/domain alternatives and negative/inconclusive diagnostics.
   No missing field is replaced with a new solve or a similar-looking seed.
4. Keep fresh Q18 amplitude-4 129/193 starts and the incomplete amplitude-1 fresh-193
   conditioning run explicitly unresolved. Return to additional Q comparisons after
   this dynamics tranche; optional Q20/Q24 controls remain in the
   [post-audit plan](../plans/post-audit-q-assessment.md). Do not erase Q18's linked
   outcome or describe it as hyperbolic reproduction.
5. Workstation execution has no arbitrary overall time cap. Save each finished
   endpoint, support resumption, timestamp all result/analysis records in UTC and
   Australia/Melbourne, and keep bulk fields local. GitHub mutations remain local.

No existing numerical kernel, optimizer, coupling, lockfile or scientific acceptance
threshold is changed. New small dynamics tests get their own path-scoped workflow.
This ADR specifies the next instrument; it does not report new workstation results.
