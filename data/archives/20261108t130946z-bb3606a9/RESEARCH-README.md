# Q17/Q19 coarse motion screening and Q2 reference

Recorded UTC: 2026-11-08T13:24:26.740066+00:00; Australia/Melbourne: 2026-11-09T00:24:26.740066+11:00.

## Purpose and measured outcome

This release preserves the complete staged screen `20261108t022631z-7e649031`, including original inputs and full float64 fields, so researchers can inspect failures and develop a finer follow-up without reconstructing missing coarse data. Q1 correction was parked. Campaign status: **complete_pending_review**.

| Rest arm | Outcome | Preparation calls | Relative force | Maximum acceleration |
|---|---|---:|---:|---:|
| q2 | admitted | 0 | 1.1542460483789047e-05 | 6.636497024101145e-05 |
| q17 | preparation_unresolved | 4 | 0.001137637542414314 | 0.025864466240685238 |
| q19 | preparation_unresolved | 4 | 0.0021815984735131006 | 0.022204441196166342 |

| Case | Status | Time reached | Original speed error |
|---|---|---:|---:|
| q2-dt0.01 | screen_pass | 0.2 | 0.00844998407201462 |

Values in the error column are relative fractions; multiply by 100 for percent. Preparation and skipped-motion outcomes are in campaign.json and SUMMARY.md; an unresolved coarse preparation is not a physical rejection of a Q value.

## What was calculated

An authenticated admitted Q2 reference runs first. Q17/Q19 original 129-cubed fields are sampled on unchanged coordinates onto a 97-cubed h=0.24/L23.04 rest grid, with fresh unchanged-action D4 stationary readmission. Moving data use a projected cubic scalar boost at beta=0.3. Short T=0.05/0.1/0.2 segments stop on declared original gates; only passing higher-Q arms receive same-grid half-dt confirmation. The run records which stages actually executed.
Source commit: `8c2c9ed492f35a6cc0615085f8ca42479a6227e0`. Study configuration SHA-256: `484b45180757ed8bcd1bf1fe82353c898d7080352a8ff8c85c1fe9de6609feac`. Start UTC 2026-11-08T02:26:31.713625+00:00 / Melbourne 2026-11-08T13:26:31.713625+11:00.

## Files and how to use them

- `ARCHIVE.json`: root/part index; the Git catalog pins its hash.
- `r001-manifest.json`: every retained file path, byte size, mode and SHA-256.
- `r001-part-*.tarpart`: ordered lossless tar segments; restore all parts in order using RESTORE.py or the repository archive tool. Individual parts need not be valid standalone tar files.
- `RESTORE.py`: exact versioned archive/restore tool.
- Restored `sources/`: the original Q2/Q17/Q19 input fields, retained unchanged.
- Restored `rest/`: initial and readmitted coarse fields, optimizer manifests/histories and native status.
- Restored `cases/`: admitted fields/rates, full milestone/latest/final states, segment snapshots and diagnostics.
- D4 NPZ checkpoints contain float64 `field` and `field_rate` arrays of shape (nx,ny,nz,3), with actual step/time and code/config/model identities. Original static inputs contain `field`, spacing `h` and the Q label. The internal unit-vector field is not an electromagnetic B array; c=1 and lengths/times/energies use the declared model units.
- Restored `SUMMARY.md`, `campaign.json`, `plan.json`, `case-metrics.csv`, `evidence.zip`: compact outcomes and provenance; CSV may be absent if no motion arm was admitted.
- Restored `followup.json`: parent checkpoint hashes and conditional finer-grid options; no fine computation starts automatically.
- Restored `handover/`: runnable local preparation/publication package; dependency environments are rebuildable.

## Restore the recorded fields

Clone the repository and check out the published study branch or a later main containing its catalog. From that checkout:

```bash
python3 scripts/workstation_archive.py restore \
  --catalog data/archives/20261108t130946z-bb3606a9/CATALOG.json \
  --destination "$HOME/EFT-restored-20261108t022631z-7e649031" --roots r001
```

The destination must be new. The run restores below `extra/r001/20261108t022631z-7e649031/`. The restore tool downloads and validates exact member hashes and preserves the recorded paths inside that root.

## Repeat the numerical screen

Use the native source commit and frozen environment. From a separate clean checkout:

```bash
git switch --detach 8c2c9ed492f35a6cc0615085f8ca42479a6227e0
uv sync --frozen --all-groups --python 3.12.14
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 \
  uv run --frozen --python 3.12.14 python -m electron_field_topology.sf_higher_q_local start
```

The worker recovers the pinned original inputs automatically and creates a new immutable run ID. It retains all failed/skipped gates. For an offline repeat, use --source-map with q2/q17/q19 paths to the restored sources; each field must match its declared hash. Status/stop/resume use the same module. Details and measured limits are in docs/models/SF-higher-q-screen.md at the native source commit.

## Build a finer follow-up

Keep the original 129 fields and admitted coarse rest. New h=0.192/0.16/0.12 rest grids at matched box length can use the coarse rest as a documented warm start, followed by fresh readmission and a motion rerun from t0. Include original-source-start controls to expose inherited basins. A coarse trajectory is not silently reclassified as a fine-grid result.

The archive engine independently downloaded and verified 79 payload files (1511077768 bytes) before this catalog was registered. This screening dataset records the achieved scope; detailed spatial/domain and long-time studies are separate.
