# Low-Q results assessment package

Recorded: UTC 2026-11-03T22:37:38.390464+00:00; Australia/Melbourne 2026-11-04T09:37:38.390464+11:00.

Read ASSESSMENT.md first. This records a compact-evidence review of six stationary rest
candidates and 60 completed cases, with six bounded case passes and the global motion gate open.

Contents: the unchanged submitted evidence.zip and summary; a reproducible scalar verifier;
timestamped verification ledger; case/comparison CSV tables; two scientific figures; and
eight source snapshots matched to the workstation campaign hashes. These snapshots document
source provenance; they are not a complete installable solver or a replacement checkout.

No local full-field solve, GitHub write, pull request or merge is performed by these files.
The report identifies which measurements were independently replayed and which need fields.

Replay with Python and NumPy:

```bash
python3 verify_assessment.py --archive evidence.zip --summary ORIGINAL-SUMMARY.md --output replay
```

The source evidence archive's SHA-256 is 780cfff1d5be5fe9e61b238206aceb6a6f47a82350e8ce257c76cc79f56d8784.
SHA256SUMS covers every package member except itself.
