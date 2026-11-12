# Q3/Q4/Q7 campaign assessment

Assessed: UTC 2026-11-11T12:42:44.910770+00:00 / Australia/Melbourne 2026-11-11T23:42:44.910770+11:00.

Source run: `20261109t134425z-89d28344`. Measured code commit: `bae639dc700c5653cb4bfb2738608795b37da641`. Study: S5-B-010. Disposition: **completed campaign; useful bounded Q3 evidence; overall convergence and isolated-motion gate remain open; Q4 admission/preparation and Q7 preparation unresolved**.

## Main finding

Q3 is the strongest candidate in this campaign for focused numerical follow-up. Its fixed-box z-speed deficit decreases with physical-mesh refinement, survives time-step refinement, and changes enough with direction and box/preparation to cross the original 1% gate. This implicates spatial resolution, initialization/centroid measurement, orientation and finite-domain/preparation sensitivity as questions to separate. The records do not identify a unique cause. A larger box pass does not erase the original small-box failures.

Q4 has two separate blockers: unqualified coarse/fine preparation, and boundary admission of its stationary medium endpoint. Q7 has preparation failures, not measured motion failures. No physical exclusion of these Q sectors follows.

## Verification scope

The supplied evidence ZIP is 462,496 bytes, SHA-256 `c066b7f2bab8308cf68945b0b6e5de837585775647634ffd721b3e84bee87517`. All 238 payload hashes, all 239 ZIP-member CRCs/uniqueness, the canonical plan hash and the separately supplied summary bytes were checked here. Eighteen final rest metric sets match their last retained history observations.

Independent centered least-squares/arithmetic reconstruction from 207 authenticated history observations reproduced centroid velocities, speed errors, energy drift, momentum drift and sampled maximum tails for all 12 evolved cases. Thirty-seven milestone/final assessment calculations were checked. Admission decisions were recomputed for all 15 records. The three fine-dt cases share one admitted initial-state hash. Four descriptive temporal-order calculations were reproduced from the recorded difference norms.

The workstation receipt separately reports successful checking of 112 sealed field/curve payloads and NPZ CRCs. Those float64 fields/curves were not supplied in the compact ZIP and have not been independently rehashed or replayed here. Field-based shape/topology, raw field differences and core invariants are authenticated recorded measurements, not newly recomputed field results. The measured commit object was not fetched; code/lock verification remains the workstation attestation. This is a compact-record assessment, pending full-field replay and archive retention.

## Q3 motion and convergence

| Configuration | Reached T | Speed error (%) | Original case outcome |
|---|---:|---:|---|
| Coarse, z, L23.04, dt0.01 | 0.2 | 2.347803 | Speed failure |
| Medium, z, L23.04, dt0.01 | 0.2 | 1.770977 | Speed failure |
| Fine, z, L23.04, dt0.02 | 0.2 | 1.057322 | Speed failure |
| Fine, z, L23.04, dt0.01 | 0.2 | 1.057322 | Speed failure |
| Fine, z, L23.04, dt0.005 | 0.2 | 1.057322 | Speed failure |
| Fine, x, L23.04, dt0.01 | 0.2 | 0.819694 | Pass through requested short window |
| Larger domain, z, L26.88, dt0.01 | 0.5 | 0.967217 | Pass through requested T0.5 window |

The speed gate remains exactly 1%. All six failed motion records (including the separate coarse short screen) failed speed alone at their final endpoint. Energy, momentum, constraints, shape, topology and tail flags passed in those cases. The small-box z trajectories stopped at T0.2 as designed, so the requested three-step T0.5 comparison is incomplete.

At T0.2, field/time-derivative descriptive temporal orders are 4.02369/3.96751; at T0.1 they are 3.97167/4.02148. Near-fourth-order fixed-grid refinement is consistent with the time integrator over these short matched windows. It does not cure the speed deficit or establish physical-mesh convergence. Fine dt0.005/0.01/0.02 speed errors differ by only about 0.000000122 percentage point.

The larger-domain speed error at matched T0.2 is **0.965823%**, compared with **1.057322%** in the smaller domain; the T0.5 larger-domain endpoint is **0.967217%**. The comparison includes exact-spacing extension and new stationary readmission, so it does not isolate wall reflection as the cause. No assertion of isolated boundaries or long-time stability follows.

| Recorded comparison at matched T0.2 | Field difference (%) | Rate difference (%) |
|---|---:|---:|
| Coarse–medium mesh | 3.658496 | 4.176943 |
| Medium–fine mesh | 1.063113 | 1.450436 |
| Coarse–fine mesh | 4.648761 | 5.394136 |
| Small–large domain, matched h | 3.006934 | 0.701569 |

These are raw fixed-world-cube L2 diagnostics (side16, 41³ analysis nodes), with no fitted alignment. They are not full-domain norms or an automatic spatial-order estimate. Domain field sensitivity is larger than the medium–fine field difference. Mesh refinement reduces the pairwise differences, but spatial/domain closure is not demonstrated.

Fresh/warm Q3 rest endpoints have tiny relative energy differences (medium 0.0000502540%, fine 0.0000326953%) while raw full-grid field differences are 1.280869% and 1.378523%. Equal energy does not demonstrate the same field or basin; registration was not fitted. The three rest-motion controls pass T0.2. Core records at three primary Q3 meshes and one Q4 medium state each show one closed component at both selected targets, with determinant1 in all recorded regular projections. This is limited finite-preimage evidence; it neither uniquely names a knot nor verifies all curves/topology in the continuum.

## Q4: admission and preparation are distinct

The medium axial41 rest endpoint passes strict force/acceleration stationarity. It fails admission before every requested rest/moving evolution. No Q4 physical-time step was taken.

| Admission quantity (%) | Medium rest | Medium moving z | Limit (%) |
|---|---:|---:|---:|
| Initial width2 tail | 0.084198 | 0.074684 | 0.075 |
| Width3 guard | 0.151397 | 0.137709 | 0.1 |

The moving width2 initial/predicted tails pass narrowly, but its width3 guard fails. The rest case fails both width2 initial/predicted reserve and width3 guard. Projection and initial shape floor pass. These are boundary-admission failures, not evidence of failed Q4 motion.

The axial41 fine fresh endpoint misses force/acceleration by 85.72×/73.13×; the fine warm endpoint by 205.81×/175.05×. Their histories previously approach much smaller residuals and later depart from them while energy decreases. This warrants optimizer/stationarity-landscape diagnosis; energy monotonicity alone is insufficient. Axial22 coarse encounters the topology diagnostic; medium axial22 misses force/acceleration by 1.70×/1.99×. The source's same-mesh stationary selection rule correctly chose axial41; lower energy at an unqualified endpoint cannot override stationarity.

## Q7: qualified preparation not obtained

Both medium starts reach 1200 iterations without stationary admission. Axial ends at energy5.54851738, force0.00529389 and maximum acceleration0.04989205 (52.94×/49.89× their limits). Trefoil-seeded ends at energy5.33279972, force0.000179403 and acceleration0.00353558 (1.79×/3.54×). Its energy is about3.89% lower than the axial endpoint on the same mesh, but neither endpoint is a qualified minimum and the final knot type is unverified.

The coarse axial arm reports Armijo search stalled; the coarse trefoil-seeded arm triggers the topology diagnostic. The finer retry mitigates some representation problems but does not satisfy stationarity. The trefoil-seeded medium endpoint is the most economical Q7 checkpoint for a separately declared convergence/continuation diagnostic; no automatic continuation or tolerance relaxation is authorized by its proximity alone.

## Counts and scientific limits

Preparations: 8 stationary, 7 preparation-unresolved, 2 topology-unresolved, 1 stationarity-unresolved. Motion records: 6 passes, 6 speed failures, 3 admission rejections. The six passes comprise the Q2 reference, three Q3 rest controls, Q3 x short motion and the larger-box Q3 z trajectory; they are not six independent successful moving candidates. Coarse short/detail Q3 cases reuse the same prepared parent and are not independent seed replications.

Model: neutral relativistic SF, D4-action-projected-RK4 reference, float64, fixed reflecting layers. Length/time and velocities use dimensionless model units with c=1, not electron SI units. Topological Q is not electric charge. Nothing here establishes charge, quantum spin, a physical electron, a unique final knot or isolated long-time stability. Q1 stays parked and Q2 remains the reference. Prior Q17/Q19 and Q18 limitations are retained.

## Recommended sequence

1. Preserve the complete native run and publish compact results using the existing local handover. Archive every float64 field/curve and verify the downloaded archive before cleanup or merge. All GitHub actions remain on the maintainer workstation.
2. Run the supplied read-only full-field replay in a new output folder and retain its receipt. This reproduces frozen metric instruments; it is not independent theory validation. Reconcile any disagreement before stronger interpretation.
3. Give Q3 the next focused numerical study: cross mesh and box size, separate initial/centroid measurement sensitivity, and repeat matched-window x/z checks. The larger-box pass has little speed margin. Repeat time-step controls where new meshes/initializations require them, while retaining the completed small-box results.
4. Treat Q4 boundary-tail correction and optimizer/stationarity diagnosis as separate questions before requesting new motion. Reuse the retained states with explicit lineage in new records.
5. Consider a separately registered Q7 trefoil-seeded medium continuation and optimizer check at unchanged original gates. Preserve the 1200-iteration outcome and verify topology/constraints throughout. Defer another broad Q sweep until the dominant numerical blockers are understood.
6. GPU qualification can support future motion costs, but this campaign's preparation blockers are CPU optimizer work; a GPU motion backend does not by itself resolve them. Do not rerun the entire campaign merely to switch execution backends.

This is an AI-assisted assessment of supplied numerical evidence. The native scientific source map remains the measured repository's `docs/models/SF-candidate-survey.md`, `SF-physical-time.md` and its literature entries; no new literature claims or physical model changes are introduced.
