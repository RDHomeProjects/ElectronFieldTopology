Matter Waves: observer calibration outcome assessment

Extract this package and open ASSESSMENT.html directly in a browser. It is
self-contained and includes the scientific figure. assessment-plots.png is
available separately at high resolution. CSVs contain exact numeric summaries;
assessment.json records scope, integrity and independent checks.

Input evidence SHA256:
04cd1d5d7ffc79cef09dcd5c77dfd27008e8760f843f5d3a420b20a62034419d

The original compact input is preserved byte-exact in data/input-evidence.zip.
It excludes the full NPZ fields. No physical-field replay, new physical
simulation, source-run modification or GitHub action occurred in this review.

Key outcome: five of six joint cell references pass; two uniform observers
pass readiness; one anchor passes all-response fresh prediction. Cell-aware
primary evolution metrics are stable at all six anchors. Higher uniform
observer count is not a general cure. See ASSESSMENT.html for qualifications
and the recommended saved-state remeasurement sequence.

Optional reproduction with Python, NumPy and Matplotlib:
  unzip -n data/input-evidence.zip -d input
  python3 assess.py --archive data/input-evidence.zip --evidence-dir input --output reproduced
  python3 render_report.py --evidence-dir input --output reproduced

This replays compact-data checks and renders analysis. It does not replay
absent fields. Timestamps change on reproduction. Reports record both UTC
and Australia/Melbourne timestamps.

Verify the delivered package after extraction:
  sha256sum -c SHA256SUMS
