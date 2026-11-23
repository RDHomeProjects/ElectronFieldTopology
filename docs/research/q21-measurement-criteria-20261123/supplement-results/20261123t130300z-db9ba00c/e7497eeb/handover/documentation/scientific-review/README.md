# Q21 resolution scientific review — 23 November 2026

Extract the complete folder, then open **ASSESSMENT.html** in a browser. Its charts and tables work without a server. ASSESSMENT.md provides the same narrative for repository publication. Four figures are supplied as high-resolution PNG and scalable SVG.

This is a scientific review and reproducibility pack, not a new production-run or GitHub publication handover. It does not alter the completed run or initiate simulation. The proposed work is prospective and has no automatic allocation from the unused old budget.

The unchanged `data/completed-evidence.zip` is the reviewed compact source for run `20261123t032942z-26dd4a7c`. Its SHA256 is `36f7e89797230762ad9dec9385d9132543581835b82e60c7610ef33f3ab219d8`. Full NPZ fields remain on the workstation and are not included. Refer to the assessment's explicit limits before interpreting checks as a fresh field replay.

## Reproduce the independent compact checks

From this extracted folder, with Python 3 and NumPy available:

```bash
python3 review.py --evidence data/completed-evidence.zip --output /tmp/q21-review-recheck
```

The script pins the source archive identity, verifies compact integrity and recomputes gate decisions, windows, curve-model scores, selection, budget accounting and scope summaries. It writes a new output folder; it does not alter the evidence or contact GitHub. It does not run a field simulation.

To regenerate the figures, NumPy and Matplotlib are required:

```bash
python3 plot_review.py
```

This explicitly rewrites the four figure pairs in this extracted folder from its checked data. Recheck or regenerate the checksum manifest if you intentionally change files. The plots and scripts are independent of the original scratch workspace location.

## Contents

- ASSESSMENT.html and ASSESSMENT.md: detailed review, interpretation, literature alignment and recommended sequence.
- INDEPENDENT-REVIEW.json and REVIEW-VALIDATION.json: computed checks and pack validation.
- ENDPOINTS.csv: measured endpoint values and late-window progress, with observation timestamps.
- MEASUREMENTS.csv: all 486 Q21 observation rows, including the six initial observations.
- BULK-SCOPE-REVIEW.csv: original bulk rows plus corrected static, physical-time and secondary-source scope classifications.
- ANGLE-EXPLORATION.json: explicitly post-hoc geometric fits, not stationarity predictions.
- PRIMARY-SOURCES.json: primary literature and official technical sources.
- data/completed-evidence.zip: unchanged uploaded compact archive.
- SHA256SUMS: exhaustive checksums for this pack's payloads.

All GitHub recording and subsequent full-field measurements are to be performed on the zbook. The supplied PR95 merge receipt concerns the plan, not publication of the completed measurements reviewed here.
