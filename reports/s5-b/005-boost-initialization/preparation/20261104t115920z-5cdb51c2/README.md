# S5-B-005 preparation and measured controls

UTC: 2026-11-04T11:59:20.718361+00:00; Melbourne: 2026-11-04T22:59:20.718361+11:00.

The independent reconstruction controls, 72 targeted tests and existing physical-time control suite passed. The final 13 new tests were repeated after guard changes and passed. End-to-end fixtures exercised read-only replay, failed-gate retention, evidence hashes, stop/resume and source tampering. Synthetic fixture output is not a measured Q1/Q2 workstation result.

Candidate off-node field order was 3.04–3.10; derivative order was 1.97–2.44. Event-difference maximum error was below 1.5e-10. The generic reconstruction is third-order in values and second-order in derivatives; it is not promoted into the existing solver. The candidate has not been evolved.

[Reconstruction controls](reconstruction-controls.json), [existing solver controls](existing-time-controls.json), [targeted tests](targeted-tests.txt), [final new tests](final-new-tests.txt), and [source/config/environment record](record.json).

Next: execute the authenticated retained-field study locally, then assess old/candidate initial data and raw/restricted-phase comoving residuals before selecting S5-B-006. Preserve all failures and negative findings. AI assisted the implementation and reporting; no external peer review is claimed.
