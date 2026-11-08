# Coarse Q17/Q19 motion preparation and controls

UTC: 2026-11-08T01:48:14.439097+00:00; Australia/Melbourne: 2026-11-08T12:48:14.439097+11:00.

Study S5-B-007. [Scientific/work-allocation specification](../../../../../docs/models/SF-higher-q-screen.md), [ordering decision](../../../../../docs/decisions/ADR-0018-coarse-higher-q-screen.md).

The maintained kernels are unchanged. Q1 correction is parked and Q2 remains a short control. This record prepares exact source coarsening, selective archive-member recovery, bounded readmission, early motion stops and optional two-dt screening confirmation; it records no production optimizer or physical-time result.

[Source probes](source-probes.json) and [resolution table](resolution-probes.csv) retain the measured read-only checks. Frozen historical archive indexes/manifests in this directory are authenticated against committed Git catalogs and pin the original 129³ Q17/Q19 fields and admitted Q2 field. Selected-source recovery transfers only required bytes with per-member hash checks. If Range is unavailable, required individual parts are hashed in full; other historical data are untouched.

[Validation](validation.json) and [test transcript](tests.txt) record the actual small software controls. [Handover rehearsal](handover-validation.json) covers fresh installation, idempotence, clean source/record preservation and local publication/archive registration with remote writes mocked. The new physical-time segmentation is checked bit-for-bit against direct calls to the unchanged step; original-gate failures and source corruption are negative controls. The test fixture's artificial acceptance stub isolates IO/segmentation and is never scientific evidence.

The default screen uses a 97³/h=0.24/L23.04 rest grid, beta=0.3 to T=0.2, with T=0.05/0.1 early decisions and original criteria. Both candidates are screened before any half-dt confirmation. At most 140 moving steps and four 50-iteration optimizer calls per higher-Q source are allocated; interrupted calls consume allocation. See the specification for exact reserves, classification and the planning estimate.

Full original input fields, coarse preparation states and every admitted/milestone/latest state remain available for new finer h=0.192/0.16/0.12 rest grids and matched motion reruns. `followup.json` names parent hashes and proposes next choices; it starts no expensive finer calculation automatically. The original 129 source is preserved to avoid concealing inherited-basin effects, including the lesson from Q18.

The handover runs in the existing administrative checkout, records UTC/Melbourne metadata and supplies status/stop/resume, compact publication and full-field archive commands. Its archive release receives a descriptive research guide, file inventory and repeat/restore commands. No source cleanup, historical path move, old threshold revision or Release deletion is performed.
