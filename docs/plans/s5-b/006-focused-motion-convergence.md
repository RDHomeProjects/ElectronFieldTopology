# s5-b-006: Focused motion, mesh and domain convergence

Updated: UTC 2026-11-05T06:31:26.938968+00:00; Australia/Melbourne 2026-11-05T17:31:26.938968+11:00.

State: **assessed**. Scientific gate: **open**. State records workflow progress, not a physical claim.

## Question and scope

Which residuals survive improved initialization, a third physical mesh and a larger matched-spacing box?

## Evidence and present finding

Focused tranche assessed: 48 fixed-layer admissions pass; eight arms complete T=1/2/3. Cubic improves shape in all 12 matched comparisons, but 24/24 milestone tail gates fail, with overlapping 16 shape, six momentum and four speed failures. No general motion acceptance.

## Next action and exit evidence

Prepare staged convergence: clarify raw/baseline transport labels and use a fixed common analysis region; first audit cubic Q1/x and Q2/z at T=1 with dt=.01/.005/.0025, then larger matched-spacing domains and a third physical mesh with readmitted rest controls. Preserve all gates; no automatic wider matrix.

Focused initialization/time-window tranche assessed; convergence remains outstanding. Require independent temporal/full-state comparisons, domain and third-physical-grid evidence, original tail/speed/momentum gates and bounded classical-inertia sensitivity before higher-Q or quantum work. Full native fields retained in verified Release catalog.

## Traceability

Requirements: NUM-002, NUM-003, BND-001, REL-002, REP-001, REP-002.

Dependencies: [s5-b-005](005-boost-initialization.md).

[Evidence index](../../../reports/s5-b/006-focused-motion-convergence/README.md).

- [docs/models/SF-focused-motion.md](../../models/SF-focused-motion.md)
- [docs/models/SF-physical-time.md](../../models/SF-physical-time.md)
- [docs/decisions/ADR-0013-conditional-cubic-initialization.md](../../decisions/ADR-0013-conditional-cubic-initialization.md)
- [docs/decisions/ADR-0014-focused-motion-assessment.md](../../decisions/ADR-0014-focused-motion-assessment.md)
