# ADR-0015: stationary tail-domain mitigation is Q-dependent

UTC: 2026-11-05T06:49:56.783673+00:00; Australia/Melbourne: 2026-11-05T17:49:56.783673+11:00.

Status: numerical workflow decision for maintainer publication/review; overall scientific gate open.

## Evidence

[The S5-B-008 assessment](../../reports/s5-b/008-tail-domain-screening/assessments/20261105t064956z-339196d8/ASSESSMENT.md) covers Q1/Q2 at L16/17.92/20.16, h=.16. All six states meet the stricter preparation stationarity gates. Independently downloaded/verified all74 archived files and replayed all12 NPZ states, with separate energy/tail/core calculations. No new physical-time trajectory was computed.

Q2 passes the original stationary tail gate at both requested larger boxes (0.066603% and0.030154%). Q1 fails both (0.202260% and0.120632%). Initial L20.16 padding gives zero shell energy, but relaxation repopulates that shell. Field differences between the two larger boxes remain2.93% for Q1 and1.04% for Q2 in the common inner cube; scalar energy differences are much smaller.

## Decision

Retain Q2/L17.92 as the smallest tested passing stationary box and L20.16 as a larger-margin rest reference. Require explicit boosted/window checks before motion use and do not infer domain independence from the shell flag. Keep all Q1 failures and original numerical thresholds. S5-B-008 becomes assessed/open.

Prepare a limited remaining Q1 stationary correction/settling follow-up: L22.08/n139 at unchanged h=.16 is a modest next candidate, with a separately recorded tightening check of the retained L20.16 endpoint. Predeclare criteria before a new run. This does not predict a pass or authorize automatic expansion. Use fixed-region fields/densities alongside the moving shell and retain unresolved outcomes.

The previously planned S5-B-006 temporal audit and physical convergence decisions remain pending suitable stationary references. Finite-box method controls can retain that restricted scope; isolated-motion acceptance cannot follow automatically. Q17/Q19, Q18/additional-Q, inertia/quantization and external-probe stages remain conditional.

## Alternatives and limits

Raising the tail threshold, rescaling energy, shrinking/tapering the field or accepting an initial padding pass would change or evade the declared test. Jumping straight to L24 is not established as necessary; the next candidate is an incremental proposal. Repeating a large motion matrix would combine unresolved effects.

This supplements [ADR-0014](ADR-0014-focused-motion-assessment.md). It changes analysis/current planning only: existing scientific payloads, field arrays, solver/configuration, links and historical failures remain unchanged. Optimization is not physical time; topology quadrature is not electric charge. AI assisted analysis; external scientific peer review has not occurred.
