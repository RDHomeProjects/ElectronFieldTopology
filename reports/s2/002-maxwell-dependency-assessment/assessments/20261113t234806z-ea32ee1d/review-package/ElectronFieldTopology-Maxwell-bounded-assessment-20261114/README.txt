Matter Waves — bounded Maxwell assessment — 14 November 2026

Extract the package and open ASSESSMENT.html directly in a browser.

Included:
- ASSESSMENT.html: self-contained report, exact data plots and proposed next steps.
- assessment-curves.png: high-resolution scientific figure.
- assessment.json and fit-summary.csv: numerical assessment tables.
- independent-audit.json: compact-evidence checks and their limits.
- verify_local_fields.py: optional read-only workstation hash/size/NPZ-CRC verifier.
- build_assessment.py: rebuilds the report/plots from the assessed source ZIP and its extracted files. It reuses the supplied audit receipt, rather than conducting a new full-field replay.

Disposition:
61 cases complete; manufactured qualification and all periodic numerical controls pass; all five frozen models pass withheld prediction checks. Hopfion-duration feature localization remains open. The primary next campaign should vary spatial spacing while holding box, time step, duration, alignment and physical observer fixed. The report also proposes 2–3 localized duration measurements and a correction to the stationary-point classifier.

No new scientific simulation, source edit or GitHub action is performed by opening this report. The original uploaded evidence and prior reports are preserved. New scientific execution/publication needs its corresponding workstation handover; this is an assessment and proposed scope.

Optional local full-field integrity check:

Set assessment to the extracted package path, then run on zbook:

assessment="$HOME/Downloads/ElectronFieldTopology-Maxwell-bounded-assessment-20261114"
run_dir="$HOME/ElectronFieldTopology-repository-admin/artifacts/maxwell-bounded-validation/20261113t153443z-5d0f27e4"
audit="$HOME/Downloads/Maxwell-bounded-field-integrity-$(date -u +%Y%m%dT%H%M%SZ).json"
python3 "$assessment/verify_local_fields.py" --run "$run_dir" --output "$audit"

The verifier checks field bytes, sizes and NPZ CRCs. It neither changes the fields nor replays scientific metrics, uploads an archive, or verifies a downloaded archival copy. Output refuses to overwrite an existing audit file. Keep the 61 local fields until the established upload/download archive verification has completed.

Optional report/figure reproduction (existing numpy/matplotlib environment required):

python build_assessment.py --evidence-dir /path/to/extracted-evidence --archive /path/to/original-evidence.zip --output /path/to/new-report-directory

The archive must match the SHA-256 in independent-audit.json. No GitHub credentials or connection are used.
