# S5-B-010 assessed outcomes and field-replay record

UTC 2026-11-11T21:30:47.832272+00:00; Australia/Melbourne 2026-11-12T08:30:47.832272+11:00.

This immutable assessment follows run `20261109t134425z-89d28344` at measured commit `bae639dc700c5653cb4bfb2738608795b37da641`, published by merged PR63 (`d85e9d518fe5e17c659c0dfdb0010b6e8fa45331`). It records Q3 fixed-grid temporal/mesh/domain observations, Q4 boundary/preparation failures and Q7 preparation limits; the scientific gate remains open.

- [Assessment and publication decision](ASSESSMENT.md)
- [Original compact-record assessment](compact-assessment.md)
- [Field replay receipt](field-replay.json)
- [Reproducible verification](verify-publication.py)
- [Compact audit and derived tables](compact-assessment-metrics.json)
- [Planned bounded Q3 diagnosis](next-diagnostic.md)
- [Overview chart](assessment-overview.png)
- [Workstation archive/merge receipts](publication-receipts.json)
- [Workstation publication log](workstation-publication-log.txt.gz)

[Original run](../../runs/20261109t134425z-89d28344/README.md) and [verified full-field archive](../../../../../data/archives/20261111t132834z-2016a3d0/README.md) remain unchanged. Complete float64 fields/curves stay in the existing Release; this assessment adds no full fields.

Reproduce the compact/receipt cross-check from the repository root:

```bash
python3 reports/s5-b/010-intermediate-q-survey/assessments/20261111t213047z-4d88bfc1/verify-publication.py --repo .
```

This checks 238 compact payload hashes, recalculates scalar-history diagnostics and compares the supplied replay against the native records. Full arrays were replayed on the workstation: 36 initial/final rest metric sets, 25 evolved endpoints, 10 comparisons and 1588 instrument numeric comparisons with zero reported difference. The compact receipt payload itself permits 1313 numerical values to be compared here. These distinct counts are not interchangeable.

The new assessment closes the pending frozen-instrument replay step from the earlier compact-only report. It does not independently validate the physical theory or remove any original failed case. Field geometry/knot labels, isolated motion, physical mesh/domain convergence, long-time behavior, charge and quantum-spin claims remain limited. AI assisted this analysis and handover. Code Apache-2.0; original report/figures CC BY4.0 under repository licensing.

The original terminal log is retained byte-exact in gzip form; the verifier checks its decompressed SHA-256. SVG trailing whitespace is normalized for Git without changing the plotted geometry or numeric data.
