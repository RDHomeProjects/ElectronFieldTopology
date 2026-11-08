# Tail-controlled Q1/Q2 motion: assessment and reproduction

UTC: 2026-11-08T01:09:15.758801+00:00; Australia/Melbourne: 2026-11-08T12:09:15.758801+11:00.

[Read the scientific assessment](ASSESSMENT.md). Six T1 trajectories correct the recorded tail issue; Q2 passes its original case gates and Q1 retains a1.563660% speed failure. Fixed-grid time refinement is approximately fourth order. Physical meshes and matched domains are next.

## Files and provenance

| File | Use |
|---|---|
| `ASSESSMENT.md` | Findings, limitations, endpoint audit and proposed next experiment |
| `case-metrics.csv` | Six cases, all original gates, original/cubic/comoving shape measures |
| `temporal-metrics.csv` | Eight original central73³ temporal comparisons and reporting floor |
| `full-field-comparisons.csv` | Central and whole-lab-grid vector/rate comparisons,16 region/time rows |
| `verification.json`, `verify_assessment.py` | Recomputed compact scalar, gate, source and historical-audit checks |
| `full-field-verification.json`, `replay_fields.py`, `replay-trace.jsonl` | Actual52-NPZ replay, explicit energy/current contractions, additional whole-grid and kinematic controls |
| `download-verification.json` | Independent download/hash verification of all 128 full payload files |
| `release-index.json`, `release-manifest.json`, `verify_retention.py` | Frozen archive metadata and checks against the Git catalog; local receipt verification is distinct from a new download |
| `motion-gates.png/.svg`, `temporal-orders.png/.svg`, `render_assessment.py` | Shareable plots and repeatable plotting script |
| `assessment-metadata.json`, `record.json`, `SHA256SUMS` | Timestamps, provenance, conventions, hashes and outcome |
| `publication-terminal.txt.gz` | Byte-preserved uploaded terminal transcript; decompress for original commands and outputs |
| `administrative-checks.txt`, `handover-validation.json` | Recorded essential validation and workstation updater rehearsal |

The immutable compact input is [the original run](../../runs/20261106t212927z-589f5f5d/README.md), including `evidence.zip`; its SHA-256 is `9c57be7d19ef234e16f05fee517a8146ae71c5de20edb53d5dcb4fdec0f861d1`. All full fields/rates remain in [the Release](https://github.com/RDHomeProjects/ElectronFieldTopology/releases/tag/archive-workstation-20261107t233600z-d1c399ad), anchored by [its Git catalog](../../../../../data/archives/20261107t233600z-d1c399ad/README.md). No scientific data is duplicated, deleted or moved by this assessment.

## Essential replay without downloading fields

From the repository checkout containing this assessment:

```bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
assessment="reports/s5-b/006-focused-motion-convergence/assessments/20261108t010058z-672ebb4c"
run="reports/s5-b/006-focused-motion-convergence/runs/20261106t212927z-589f5f5d"
replay_out="$(mktemp -d "$HOME/EFT-temporal-replay-XXXXXXXX")"
date -u '+Replay started: %Y-%m-%d %H:%M:%S UTC'
TZ=Australia/Melbourne date '+Replay started: %Y-%m-%d %H:%M:%S %Z'
uv run --frozen --python 3.12.14 python "$assessment/verify_assessment.py" \
  --repo . --evidence "$run/evidence.zip" --summary "$run/SUMMARY.md" \
  --output "$replay_out/verification.json"
python3 "$assessment/verify_retention.py" --repo . --folder "$assessment" \
  --output "$replay_out/retention.json"
```

The latter authenticates the saved replay/download receipts and catalog chain; it does not download 6 GB again. Keep newly created outputs outside this immutable assessment directory.

## Independently restore and replay all arrays

Requires authenticated `gh`, Python/`uv`, the committed lock, and roughly 16 GiB free for parts plus restored fields. The archive tool refuses an existing restore destination. This command downloads the actual arrays and checks every file, rather than relying only on this assessment's receipt.

```bash
restore_parent="$(mktemp -d "$HOME/EFT-temporal-restore-XXXXXXXX")"
python3 scripts/workstation_archive.py restore \
  --catalog data/archives/20261107t233600z-d1c399ad/CATALOG.json \
  --destination "$restore_parent/restored" --roots r001
full_run="$restore_parent/restored/extra/r001/20261106t212927z-589f5f5d"
uv run --frozen --python 3.12.14 python "$assessment/replay_fields.py" \
  --repo . --run "$full_run" --evidence "$run/evidence.zip" \
  --output "$replay_out/full-field-verification.json"
date -u '+Replay finished: %Y-%m-%d %H:%M:%S UTC'
TZ=Australia/Melbourne date '+Replay finished: %Y-%m-%d %H:%M:%S %Z'
```

The read-only replay took about 464 seconds on the assessment host, excluding download. It uses the existing kernels, independently checks explicit energy/current contractions and field norms, and launches no optimizer or physical-time stepping. Output timestamps and tiny floating-point differences may vary by environment; identity/hashes, original gates and declared numerical tolerances are checked. Environment details are in the full-field receipt.

## Regenerate figures safely

Copy the plot script and its input CSV/metadata into a fresh output folder; do not overwrite published figures in place.

```bash
plot_out="$(mktemp -d "$HOME/EFT-temporal-plots-XXXXXXXX")"
cp -- "$assessment/render_assessment.py" "$assessment/assessment-metadata.json" \
  "$assessment/case-metrics.csv" "$assessment/temporal-metrics.csv" "$plot_out/"
uv run --frozen --python 3.12.14 python "$plot_out/render_assessment.py"
```

The handover updates existing PR61 on `work/s5-b-006-audit-temporal`; it applies only to reviewed head `6c214afe141ecd4c538acf7aafa72551c6adfd4d` or the already installed exact assessment. It backs up Git, stages only new analysis/documentation, verifies source/config pins and original immutable records, and supplies separate publication/merge commands. Full fields are already uploaded. No archive asset or release description is modified. AI-assisted assessment; original scientific failures are retained.
