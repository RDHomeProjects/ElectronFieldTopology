# Neutral SF dynamics admission

{"utc": "2026-11-02T10:22:31.593216+00:00", "melbourne": "2026-11-02T21:22:31.593216+11:00"}

Execution: **complete**; 31/31 endpoints; 0 numerical-check failures.

Neutral static-field dynamics admission only; no physical-time evolution, full stability proof, electric charge or electron-model acceptance.

| Stage | E | ||integrated stress|| / E | Kinetic condition | Curvature probes |
|---|---:|---:|---:|---:|
| q1-control | 1.23591387 | 0.00404404 | 1.64463 | 4 |
| q2-control | 2.01185375 | 0.00229887 | 2.96218 | 4 |
| q22-control | 12.5913797 | 0.0222404 | 3.81707 | 4 |
| q18-baseline-97 | 10.9449199 | 0.0201832 | 5.63116 | 0 |
| q17-neighbour-129 | 11.0019115 | 0.0159995 | 4.36407 | 0 |
| q19-neighbour-129 | 12.0632306 | 0.0152959 | 4.52128 | 0 |
| q18-scale35-97 | 10.945158 | 0.0204061 | 5.63689 | 0 |
| q18-scale45-97 | 10.9451003 | 0.020307 | 5.62068 | 0 |
| q18-ell025-97 | 10.9448892 | 0.0201893 | 5.64252 | 0 |
| q18-baseline-129 | 10.9205667 | 0.0153476 | 5.36736 | 0 |
| q18-baseline-161 | 10.9110907 | 0.0151711 | 5.08865 | 0 |
| q18-baseline-193 | 10.905551 | 0.0149946 | 5.05815 | 4 |
| q18-baseline-domain | 10.8784362 | 0.00562789 | 5.06833 | 0 |
| q17-neighbour-161 | 10.9932315 | 0.0159678 | 4.32255 | 0 |
| q17-neighbour-193 | 10.9883283 | 0.0159933 | 4.31184 | 4 |
| q17-neighbour-domain | 10.9618497 | 0.00364201 | 4.23187 | 0 |
| q19-neighbour-161 | 12.053995 | 0.015293 | 4.48497 | 0 |
| q19-neighbour-193 | 12.0487237 | 0.0153063 | 4.46088 | 4 |
| q19-neighbour-domain | 12.0157233 | 0.00457631 | 4.31324 | 0 |
| q18-scale35-129 | 10.92631 | 0.0201581 | 5.65693 | 0 |
| q18-scale35-161 | 10.9166 | 0.0201886 | 5.40727 | 0 |
| q18-scale35-193 | 10.9109947 | 0.0200575 | 5.24381 | 0 |
| q18-scale35-domain | 10.8801591 | 0.00679025 | 5.17184 | 0 |
| q18-scale45-129 | 10.925139 | 0.0196524 | 5.64897 | 0 |
| q18-scale45-161 | 10.9111106 | 0.015188 | 5.19058 | 0 |
| q18-scale45-193 | 10.9055797 | 0.0150449 | 5.03347 | 0 |
| q18-scale45-domain | 10.8785736 | 0.00557036 | 5.25027 | 0 |
| q18-ell025-129 | 10.9261102 | 0.0198733 | 5.57668 | 0 |
| q18-ell025-161 | 10.9163601 | 0.0200852 | 5.39279 | 0 |
| q18-ell025-193 | 10.9108972 | 0.0199154 | 5.22368 | 0 |
| q18-ell025-domain | 10.8805028 | 0.00640813 | 5.16725 | 0 |

Inspect mesh/domain trends in summary.json. Nonzero stress or negative trial curvature is retained,
not suppressed. Particle-boost relations require negligible integrated stress.
No passing result authorises electron or full stability claims.

Q18 fresh fine-start/conditioning and broader Q controls remain planned separately.
