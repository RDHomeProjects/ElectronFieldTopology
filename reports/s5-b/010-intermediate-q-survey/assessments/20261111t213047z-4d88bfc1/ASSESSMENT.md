# Q3/Q4/Q7 assessment, replay and next diagnostic decision

UTC 2026-11-11T21:30:47.832272+00:00; Australia/Melbourne 2026-11-12T08:30:47.832272+11:00.

## Decision

Mark S5-B-010 **assessed**, with scientific gate **open**. Preserve the complete native run, full-field archive and every original failure. Place a focused Q3 mesh/domain/initialization/centroid diagnosis first in the current roadmap. Q1 remains parked and Q2 remains the reference. Q4/Q7 receive separate targeted follow-ups rather than automatic motion admission.

## Verified evidence chain

Run `20261109t134425z-89d28344` was computed at `bae639dc700c5653cb4bfb2738608795b37da641`. Its compact evidence SHA-256 is `c066b7f2bab8308cf68945b0b6e5de837585775647634ffd721b3e84bee87517`. The earlier compact analysis checked all 238 hashed payloads, 18 rest endpoint histories and 207 moving/rest-control observations across 12 evolved cases. It reconstructed 37 milestone/final history calculations and the recorded temporal-order arithmetic.

The workstation's complete read-only replay finished at 2026-11-12T00:25:16.081319+11:00 Melbourne / 2026-11-11T13:25:16.081319+00:00 UTC. It audited 112 sealed field/curve files, re-evaluated both initial and final states for all 18 preparations, replayed 25 positive-time endpoints across 12 evolved cases, and checked 10 field comparisons. Three Q4 admission-rejected records correctly have no evolved endpoint. Its 1588 instrument numeric comparisons report maximum difference0.0. The supplied JSON has SHA-256 `9abd97cb13568bedc9112525716e7d1a149ea739cadea9580a0c75a2a7bea651`; 1313 numerical values in its retained payload match the original compact records exactly. Histories between saved fields are authenticated/reused, not reconstructed from missing arrays. Core knot invariants are retained measurements, not independently recalculated by this replay.

Full archive `20261111t132834z-2016a3d0` completed at 2026-11-12T02:47:02.491391+11:00 Melbourne / 2026-11-11T15:47:02.491391+00:00 UTC. The catalog/verification were published and PR63 merged at 2026-11-12T08:25:52+11:00 / 2026-11-11T21:25:52Z, merge `d85e9d518fe5e17c659c0dfdb0010b6e8fa45331`. The provided workstation log is the source of these publication receipts. This handover makes no remote request during preparation; installation validates the merged on-disk archive catalog/verification hash chain and native evidence identity before adding this record.

## Scientific interpretation

| Case | Reached T | Speed error (%) | Original 1% gate |
|---|---:|---:|---|
| Q3 coarse z, L23.04 | 0.2 | 2.347803 | Fail |
| Q3 medium z, L23.04 | 0.2 | 1.770977 | Fail |
| Q3 fine z, L23.04, all three dt | 0.2 | 1.057322 | Fail |
| Q3 fine x, L23.04 | 0.2 | 0.819694 | Pass |
| Q3 larger-domain z, L26.88 | 0.5 | 0.967217 | Pass |

The six failed motion records fail speed alone; six records pass and three are admission rejections. Three of the six passes are Q3 rest controls and one is Q2, so the count is not six independent successful moving candidates. Three-step temporal orders are near four at the reached common T0.1/T0.2 windows; the requested T0.5 comparison remains incomplete. Time-step refinement alone barely changes the residual speed deficit. Domain field sensitivity at matched T0.2 is about3.0069%, versus1.0631% for medium/fine mesh. Direction and box changes cross the speed criterion. These observations support a controlled numerical diagnosis, not causal attribution to reflection or a continuum conclusion.

Q4 medium axial41 is stationary but its moving width3 guard is0.137709% against0.1%; its rest case also fails the stricter width2 initial reserve. No Q4 motion step was taken. Both axial41 fine routes remain unqualified; their optimizer histories require diagnosis. Q7 medium trefoil-seeded ends at force1.79 times and maximum acceleration3.54 times the limits; axial is farther away. Its lower energy and seed name do not certify a stationary minimum or final knot. Neither Q7 starting family qualifies for motion. Allocation exhaustion is not an existence/nonexistence theorem.

See [the full compact analysis](compact-assessment.md) and [the chart](assessment-overview.png) for the complete numerical tables and scopes. This assessment adds replay and publication evidence to those observations. It does not revise any measured native result.

## Scope and next action

The neutral SF model, +--- conventions, dimensionless c=1 units, float64 D4/RK4 scheme and fixed reflecting layers remain as documented in the measured source specifications. No solver, action, optimizer, threshold, workflow, physical configuration or dependency changes are included. Hopf Q is not electric charge; classical numerical persistence is not quantum spin or an electron model.

Follow [the bounded diagnostic plan](next-diagnostic.md). This publication is an assessment/plan update and launches no new solve. A new executable Q3 campaign requires its own preparation record, source/configuration seals and explicit run command. The optional CUDA motion backend is qualification support; stationary preparation remains CPU and the completed full survey is not automatically repeated.
