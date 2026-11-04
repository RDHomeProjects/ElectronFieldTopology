# Assessed full-field motion diagnostics

Recorded: UTC 2026-11-04T00:25:53.842380+00:00; Melbourne 2026-11-04T11:25:53.842380+11:00.

Read [the scientific assessment](ASSESSMENT.md). It records zero endpoint replay
mismatches, initial derivative and spatial/domain sensitivity, and unconverged classical
inertia. The global motion gate stays open; original failures remain unchanged.

Contents include both unchanged evidence archives, a reproducible compact-record
verifier, timestamped verification/CSV tables, source snapshots and scientific figures.
No full scientific field arrays are included, and no new trajectory is claimed.

```bash
python3 verify_review.py --diagnostic diagnostic-evidence.zip \
  --original original-motion-evidence.zip --summary ORIGINAL-SUMMARY.md --output replay
```

The report distinguishes full-field results recorded on the workstation from the
hash, scalar, matrix and consistency checks independently repeated in this review.
