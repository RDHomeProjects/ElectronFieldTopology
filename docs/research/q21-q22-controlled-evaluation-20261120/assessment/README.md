# Field-diagnosis assessment

Open [ASSESSMENT.html](ASSESSMENT.html) in a browser. Q2 reproduces. Q21/Q22 residuals are overwhelmingly interior; neither normalization changes nor boundary-density choice explains their current gate failures. Historical cell-functional static successes remain preserved and must not be relabelled as failed D4 experiments.

This is an assessment bundle, not a new numerical launcher. No further workstation run is needed to complete this assessment. Read the proposed focused next steps before changing optimizer, box or mesh.

To reproduce compact checks with Python standard-library tools:

```bash
assessment="$HOME/Downloads/ElectronFieldTopology-field-diagnosis-assessment-20261120"
python3 -B "$assessment/review.py" \
  --output "$HOME/Downloads/field-diagnosis-review-$(date -u +%Y%m%dT%H%M%SZ).json"
```

Full 3D fields are not included; the original diagnostic archive is retained byte-for-byte. All plots use measured values, without a predicted gate pass.
