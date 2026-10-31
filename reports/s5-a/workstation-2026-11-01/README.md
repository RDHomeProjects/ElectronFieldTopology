# Workstation GPU continuation — measured partial outcome

Recorded: 1 November 2026 (Australia/Melbourne). Model: SF-J2015-static; source: `a607ccd496ed75dc6c3cee00c9ecb14d8f2c3793`. This records the supplied workstation evidence, not a completed cable/hyperbolic reproduction or an electron model. The original interrupted run remains in [the historical report](../README.md).

## Evidence and provenance

The **unchanged [evidence.zip](evidence.zip)** is 2,714,167 bytes, SHA-256 `2ff8f15facc37b02736242926d1d43a2a20b3f7ed27bf5f28f2daf9f1cbe81f3`. Its 164 unique entries include a manifest covering all 163 other members. All hashes were verified. Readable byte-identical copies of [the original generated summary](records/SUMMARY.md), [machine summary](records/summary.json), [campaign](records/campaign.json), [plan](records/plan.json), configurations, results, histories and manifests accompany it. The generated summary's **completed** means the process finished; use the solver statuses below for scientific assessment.

All eleven executed cases record the same clean source commit and unchanged tracked source. The archived configuration/result hashes and case histories were reviewed; recorded energies are monotone. The uploaded ZIP contains extracted curves, diagrams, witnesses, logs and scalar records, **not the full three-dimensional field checkpoints**. Those remain on the workstation under `/home/rd/ElectronFieldTopology-timing/artifacts/gpu-continuation-20261101-004351/cases/`. Preserve this directory before further work. Endpoint native-CPU energy, full-gradient and Hopf audits passed according to the recorded workstation results. These full-field quantities cannot be independently recomputed here from this ZIP.

Hardware supplied by the maintainer: Ubuntu 24.04.4, i7-10850H (6 physical/12 logical cores), 16 GiB RAM, RTX 2080 Super Max-Q (8 GiB), driver 580.178.04. The maintainer reported successful on-device numerical checks and paired float64 timings. Q22 at 129³: 12-thread CPU 1.282994 s/step versus GPU .287333 s/step (4.465x). Q18 at 97³: .600113 versus .133655 s/step (4.490x). Raw timing artifacts have not been independently retrieved; these terminal observations are separate from the hashed continuation archive. They are short-solve measurements, not guaranteed long-run throughput or scientific acceptance.

## Retained case outcomes

The predeclared stationary residual limit remains 1e-3; fixed energy coefficients and other [model gates](../../../docs/models/SF-J2015-static.md) are unchanged. Signed Hopf values reflect the declared orientation, not electric charge.

| Stage | Solver status | Final energy | CPU tangent-gradient RMS | Signed Hopf integral |
|---|---|---:|---:|---:|
| q1-control | gradient_stationary | 1.235913870 | 0.000638546 | -0.9859280 |
| q2-control | gradient_stationary | 2.011853745 | 0.000673163 | -1.9822697 |
| q22-129 | residual_not_stationary | 12.591379967 | 0.00106413 | -21.9787461 |
| q18-97 | gradient_stationary | 10.944919931 | 0.000884191 | -17.9511610 |
| q18-129 | time_budget | 10.920585006 | 0.0133824 | -17.9838500 |
| q22-129-cont | gradient_stationary | 12.591379810 | 0.000881552 | -21.9787461 |
| q22-161 | time_budget | 12.576523303 | 0.00964283 | -21.9910886 |
| q22-193 | time_budget | 12.567837003 | 0.00723613 | -21.9956085 |
| q18-193 | gradient_stationary | 10.905757904 | 0.000866929 | -17.9966991 |
| q18-source-193 | time_budget | 11.280946448 | 0.604394 | -17.9968712 |
| q22-comparison | time_budget | 12.526701543 | 0.026898 | -21.9773193 |
| q18-comparison | not run: campaign budget | — | — | — |
| q22-domain | not run: campaign budget | — | — | — |
| q18-domain | not run: campaign budget | — | — | — |

The physics work consumed about 6,006.8 seconds of the 6,000-second allocation (individual-job/audit overhead accounts for overshoot). The 7,200-second campaign reserved 1,200 seconds for analysis. All 27 analysis jobs completed. Q18 comparison and both larger-domain cases were unrun because the physics budget ended; this is a recorded budget outcome. Resuming that campaign does not grant another physics allocation.

## Q22 cable assessment

The 129³ continuation passes the stationary residual and scalar gates; its energy is 12.591379810. The 161³ and 193³ fields retain the cable evidence, with energies 12.576523303 and 12.567837003, but residuals .00964283 and .00723613 exceed 1e-3. Their .1181% and .0691% successive energy changes are **provisional mesh observations**, because the finer fields are not stationary. At 193³ the energy is .4704% above Jennings's 12.509, within the source-energy tolerance; that alone does not complete reproduction. The larger-domain check is missing.

At all four Q22 cable endpoints (including both 129³ attempts), both preimages have one component. Three views at each of 256, 384 and 512 samples give cable-compatible diagrams and matching Jones polynomials. All eight stored common-diagram witnesses were checked: every input diagram belongs to its source analysis and all sixteen output diagrams have the recorded common canonical word. Fresh independent matching also recovered all eight candidate/reference matches.

**Witness limitation:** replaying only a saved random seed does not deterministically reproduce every reference simplification with this Spherogram implementation. Some exact-seed replays failed although fresh common-diagram searches succeeded. The saved diagrams and word equality are retained; there is no independently certified, explicitly replayable Reidemeister move trace or continuum isotopy certificate. Polynomial equality alone is insufficient. Any final acceptance must state this finite-diagram evidence limit.

The same-charge K(5,4)-seeded 129³ comparison reaches a lower trial energy, 12.526701543, but remains nonstationary (residual .0268980). Its final preimage is a three-component link, containing one trefoil and two unknots, rather than the initial single knot. Do not rank it as a converged minimum or omit its lower trial energy. Jennings's table already distinguishes the cable local minimum from lower-energy competing states.

## Q18 hyperbolic assessment

The 193³ field is stationary at energy 10.905757904, residual .000866929, and signed Hopf integral -17.9966991. Both preimages consist of **three unknotted components**. Independent polygon linking checks at 256 samples and three views recover pair-link magnitudes 1, 2, 2 (recorded signs -1, -2, -2 depend on orientations). This is a linked alternative, **not the target 10_139 hyperbolic knot**. Hopf degree near 18 does not fix preimage knot type.

The 97³ field is also stationary, while the intermediate 129³ field is not; mesh energy comparisons remain provisional and the domain study is missing. The alternate source-amplitude 193³ trial also becomes three components and remains strongly nonstationary (residual .604394). Neither outcome establishes nonexistence of the published hyperbolic local minimum. The source's 301³ mesh, h=.06, profile choices and quenched second-order relaxation differ from our compact initial fields and Sobolev conjugate-gradient relaxation. Preserve this basin-dependent negative result without imposing a knot type during relaxation.

## Independent scaling and limits

All computed five-dilation checks pass the declared 5% derivative/virial limits, with positive cell-cone margins. Passing scale checks does not remove the finer-grid stationarity or domain gaps. Static minimization does not test physical-time stability, radiation, Lorentz covariance or interactions. The unit-vector model has no defined electromagnetic electric-charge observable. Hopf charge, electric charge, classical angular momentum and quantum spin/statistics remain distinct.

## Accepted next scope

Under [ADR-0007](../../../docs/decisions/ADR-0007-tightened-milestones.md), first attempt a bounded Q22 closure from the existing 161³/193³ checkpoints, then a matched larger-domain test and stationary same-charge comparison if affordable. Keep every failure/budget outcome. Close this benchmark with an explicit accepted/partial/failed gate ledger even if a reproduction remains unresolved; do not expand to a general Q catalogue. Retain Q18 as a stationary linked alternative and a failed hyperbolic-basin reproduction.

Then perform the charged, relativistic **equation-level feasibility audit** before implementing another simulator: full fields/action, charge and asymptotic flux, finite-energy/scale accounting, causal evolution and stability, prescribed parameters versus predictions, and the path to interaction tests. Faber–Kobushkin remains an audit candidate, not an accepted theory. Electron and quantum gates and the deferred level-4 review are unchanged.

## Verification

From the repository root:

```bash
python3 scripts/check_workstation_evidence.py
python3 scripts/check_docs.py
uv sync --frozen --all-groups --extra topology --python 3.12.14
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 uv run --frozen --extra topology pytest -q
```

The offline archive checker verifies bytes, membership, readable copies and config/summary consistency; it does not certify scientific acceptance. No GPU is available in the review environment. Real-device measurements above are supplied workstation evidence; the local real-CUDA test is skipped when no device is available. The [recovery verification record](recovery.md) records the subsequent checks and the interrupted publication state. AI assisted the review and reporting; primary references are Jennings L36, Sutcliffe L37 and the topology conventions L38 in the [literature register](../../../docs/literature/README.md).
