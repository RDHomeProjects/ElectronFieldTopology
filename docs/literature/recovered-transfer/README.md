# Recovered analysis transfer — complete

All **5,217 words** in the written-analysis corpus defined in PRs 18 and 19 are published. This is completion of the transfer, not completion of the scientific literature review. Research is stopped; S4-B remains paused and level 4 deferred. No new paper review or numerical work was performed.

The original samples preserve 573 words. Nine further batches preserve the remaining 4,644 words, without missing or overlapping source word ranges. All six source texts reconstruct exactly to their recorded SHA256 values. JSON fragments preserve original bytes; Markdown companions render internal historical links as annotated source-relative references. CSV fragments preserve the selected summary/applicability/review-depth fields; source-row identities, other original columns and field order are in the manifest.

## Reading the transfer

Earlier samples: [1% sample](../recovered-analysis-one-percent.md), [10% sample](../recovered-analysis-ten-percent.md).

| Further batch | New words | Cumulative corpus coverage | Analysis | Exact fragments |
|---|---:|---:|---|---|
| 1 | 498 | 1071/5,217 (20.53%) | [Read](batch-01.md) | [JSON](batch-01.json) |
| 2 | 480 | 1551/5,217 (29.73%) | [Read](batch-02.md) | [JSON](batch-02.json) |
| 3 | 490 | 2041/5,217 (39.12%) | [Read](batch-03.md) | [JSON](batch-03.json) |
| 4 | 473 | 2514/5,217 (48.19%) | [Read](batch-04.md) | [JSON](batch-04.json) |
| 5 | 480 | 2994/5,217 (57.39%) | [Read](batch-05.md) | [JSON](batch-05.json) |
| 6 | 487 | 3481/5,217 (66.72%) | [Read](batch-06.md) | [JSON](batch-06.json) |
| 7 | 578 | 4059/5,217 (77.80%) | [Read](batch-07.md) | [JSON](batch-07.json) |
| 8 | 581 | 4640/5,217 (88.94%) | [Read](batch-08.md) | [JSON](batch-08.json) |
| 9 | 577 | 5217/5,217 (100.00%) | [Read](batch-09.md) | [JSON](batch-09.json) |

## Verification and scope

[The manifest](manifest.json) identifies the original source hashes, word counts, previously published ranges, batch hashes and frozen recovery commit. From the repository root, run:

```bash
python3 scripts/check_recovered_text_transfer.py
python3 scripts/check_docs.py
```

The checker verifies sample provenance, fragment hashes, order, range uniqueness, all 5,217 words and exact reconstruction hashes for all six counted source texts. Prose-only batches require documentation and transfer-integrity CI; numerical workflows now skip changes confined to prose paths. Numerical code, tests, configurations, dependency files and experimental evidence remain eligible for their workflows.

The six-source scope is four review/audit Markdown files plus selected analysis fields from the seed and follow-up CSVs. The 113,295-ID citation dataset, supporting acquisition artifacts, and unpublished PR #17 implementation are outside this percentage denominator and are not claimed as transferred here. The complete recovery bundle remains preserved separately. Neither the corpus transfer nor passing checks certifies scientific correctness or completes the unfinished literature passes and impact audit.

AI assisted the original analysis and transfer. Original source authors retain authorship; their complete papers/abstracts are not reproduced. Historical labels, qualifications, negative findings and mathematical distinctions remain preserved. Requirements SCI-003/004, TOP-001, MOD-001/002, REP-001/002. Tracks [issue #16](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/16) and [PR #17](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/17).
