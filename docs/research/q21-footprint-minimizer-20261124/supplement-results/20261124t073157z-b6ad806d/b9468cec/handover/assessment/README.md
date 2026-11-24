# Q21 CPU scientific review — 24 November 2026

Extract the folder and open **ASSESSMENT.html** in a browser. It includes the detailed scientific review, four new charts and a labelled original campaign image. ASSESSMENT.md provides the same narrative for later repository recording. The plots are high-resolution PNG and scalable SVG.

This is a review pack, not a simulation or publication handover. It initiates no GitHub operations, optimizer steps or physical-time evolution.

The two user-supplied ZIPs were identical. Only one unchanged copy is included as data/supplement-evidence.zip. The terminal log and original released handover are also retained. The latter authenticates two nested checksum manifests omitted by the campaign's archive filter; that limitation is explicitly assessed in the report. Full NPZ fields remain on the zbook and are not included.

## Reproduce compact-record checks

With Python 3 and NumPy installed, from the extracted folder:

```bash
python3 review.py --evidence data/supplement-evidence.zip --terminal data/terminal-log.txt --output /tmp/q21-cpu-independent-recheck
```

The script reads archives and recomputes recorded decisions and scalar relationships. It does not execute archived handover code and does not replay field arrays. The packaged data/original-handover.zip is used by default to verify the inherited source files against the authenticated released package.

To regenerate the four review chart pairs, NumPy and Matplotlib are required:

```bash
python3 plot_review.py
```

This overwrites the chart files in the extracted folder. Regenerate checksums if you intentionally change outputs. Display images remain distinct from native field measurements and topology identification.

## Materials

- INDEPENDENT-REVIEW.json: check results, numerical summaries, predictions and publication receipt.
- Q21-ENDPOINTS.csv: eight arms, including the exact continuation control.
- FIELD-AUDIT-REVIEW.csv: the 15 field audits and regional/RMS quantities.
- ENERGY-CHANGE-REVIEW.csv: all 640 measured accepted-update energy changes across both campaigns.
- Q2-Q32-LEDGER.csv: original retained-ledger accounting, with two new Q21 branches separately indicated.
- REVIEW-VALIDATION.json and SHA256SUMS: review-pack validation and exhaustive payload hashes.
- data/: unchanged received supplement, terminal log and original handover release.

All original experiment results and limitations remain unchanged. The supplied terminal records the raw-results publication; this new independent assessment has not itself been published to GitHub by the assistant.
