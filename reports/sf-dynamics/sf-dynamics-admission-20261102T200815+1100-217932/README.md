# Neutral SF dynamics admission: recorded workstation results

Assessed: 2026-11-02T10:41:22.656985+00:00 UTC; 2026-11-02T21:41:22.656985+11:00 Australia/Melbourne.

Read the [scientific assessment](ASSESSMENT.md) and [verification ledger](assessment-verification.json).
The unchanged [workstation archive](evidence.zip) contains 31 endpoints and their
read-only admission diagnostics. [Raw summary](SUMMARY.md), [full summary](summary.json),
[run manifest](manifest.json) and [instrument record](instruments.json) are readable
copies. Full fields remain on the workstation.

Main finding: positive reported curvature in 24 trial directions, but substantial
domain sensitivity of integrated stress. This is not physical-time evolution or a
full stability/electron-model result. The native central curvature energy was not
explicitly archived; baseline-free consistency and the resulting replay limit are
recorded without rewriting the original evidence.

Replay arithmetic/integrity without rerunning field analysis:

```bash
python3 reports/sf-dynamics/sf-dynamics-admission-20261102T200815+1100-217932/verify_assessment.py
```

Regenerate the figures with locked numerical dependencies:

```bash
uv run --frozen python reports/sf-dynamics/sf-dynamics-admission-20261102T200815+1100-217932/render_assessment.py
```

The source commit's expected tree is checked by the workstation updater before
publication. Figures are derived from archived records; no original field data or
negative findings are changed.
