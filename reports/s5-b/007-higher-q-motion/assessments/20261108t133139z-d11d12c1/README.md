# Q17/Q19 preparation assessment and short Q2 motion reference

UTC: 2026-11-08T13:31:39.521682+00:00; Australia/Melbourne: 2026-11-09T00:31:39.521682+11:00.

[Read the scientific assessment](ASSESSMENT.md). Both higher-Q arms exhausted their frozen 200-iteration preparation allocation without stationarity; neither was evolved. Q2 passed all seven original gates at all three short milestones. The recommended next priority returns to Q2 numerical/physical-mesh/domain controls, retaining Q1 parked and all higher-Q parent fields.

## Files

| File | Use |
|---|---|
| [ASSESSMENT.md](ASSESSMENT.md) | Findings, interpretation, alternatives and staged recommendation |
| [record.json](record.json), [SHA256SUMS](SHA256SUMS) | Identity, provenance and exact payload preservation |
| [rest-metrics.csv](rest-metrics.csv), [optimizer-history.csv](optimizer-history.csv), [q2-milestones.csv](q2-milestones.csv) | Timestamped LF tables; native history duplicates at batch boundaries retained |
| [compact-verification.json](compact-verification.json) | Compact evidence/source/threshold and scalar replay receipt |
| [field-verification.json](field-verification.json), [field-replay.txt](field-replay.txt) | Full-field metrics, 23 NPZ identities/12 distinct states, 234 numerical comparisons and residual localization |
| [archive-verification.json](archive-verification.json), [archive-recheck.json](archive-recheck.json) | Independent six-asset/79-payload verification receipts |
| [release-index.json](release-index.json), [release-manifest.json](release-manifest.json), [release-snapshot.json](release-snapshot.json) | Frozen binary inventory, hashes and asset identities |
| [release-research-readme.md](release-research-readme.md) | Original descriptive archive/restore/repeat guide |
| `preparation-residuals`, `preparation-energy`, `q2-reference` PNG/SVG pairs | Timestamped scientific figures |
| [verify_assessment.py](verify_assessment.py), [replay_fields.py](replay_fields.py), [verify_archive.py](verify_archive.py), [render_assessment.py](render_assessment.py) | Read-only reproduction; output must go to a new temporary folder |
| [validation.json](validation.json), [validation.txt](validation.txt) | Report verification and essential repository checks; publication rehearsals are identified separately in the downloaded handover |

Original [compact run](../../runs/20261108t022631z-7e649031/README.md) and [Git archive catalog](../../../../../data/archives/20261108t130946z-bb3606a9/README.md) remain byte-exact. The new analysis does not mutate them. [The canonical plan](../../../../../docs/plans/s5-b/007-higher-q-motion.md) and [ADR-0019](../../../../../docs/decisions/ADR-0019-higher-q-preparation-assessment.md) describe the current decision.

## Reproduce compact checks

From the repository checkout at this assessment commit (standard-library Python only):

```bash
report="reports/s5-b/007-higher-q-motion/assessments/20261108t133139z-d11d12c1"
review="$(mktemp -d /tmp/eft-q17-review.XXXXXXXX)"
PYTHONDONTWRITEBYTECODE=1 python3 "$report/verify_assessment.py"   --repo . --output "$review/compact"
```

This checks published hashes/source pins and replays scalar gates. It does not redo field-dependent shapes/topology, solve a trajectory, or create files in the immutable report. Native failed/skipped outcomes remain failures/skips.

## Restore and replay full fields

Use the same `report` and `review` variables. The Release assets occupy about 1.51 GB; allow about 3.1 GB for assets plus an extracted copy. This is an optional independent recheck, not required to install the completed assessment.

```bash
mkdir "$review/assets"
gh release download archive-workstation-20261108t130946z-bb3606a9   --repo RDHomeProjects/ElectronFieldTopology --dir "$review/assets"
PYTHONDONTWRITEBYTECODE=1 python3 "$report/verify_archive.py"   --assets "$review/assets" --restore "$review/restored"   --output "$review/archive-verification.json"
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1   uv run --frozen --python 3.12.14 python "$report/replay_fields.py"   --repo . --run "$review/restored/files" --output "$review/fields"
```

If the original workstation campaign still exists, its full path can be used for `--run` instead of restoring another copy. The replay authenticates every original manifest member before loading it and computes measurements only. It imports the pinned numerical sources; future kernel changes require an isolated checkout at the assessment commit. Floating comparisons use relative1e-8/absolute1e-11 to accommodate platform/library changes, while scientific tolerances remain unchanged.

To regenerate the figures in a temporary destination:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --frozen --python 3.12.14   python "$report/render_assessment.py" --output "$review/figures"
```

## Publish from the workstation

The companion `ElectronFieldTopology-Q17-Q19-assessment-20261109.zip` supplies UPDATE, VERIFY, PUBLISH and MERGE wrappers. UPDATE applies only the analysis/administrative patch to the existing PR62 branch after creating a verified full-history Git bundle. PUBLISH commits/pushes the assessment and updates PR62; MERGE separately watches required checks and matches the exact head. Full-field assets already uploaded are checked for unchanged identity/digest, not uploaded again. Existing fields, older results and Releases are never removed.

The scripts and report were AI assisted. Scientific claims are limited to the retained numerical evidence; no new external literature review or primary-source reproduction was performed in this assessment.
