# Frozen citation dataset — 1% sample

31 October 2026 (Australia/Melbourne). This publishes **1,133 of 113,295 citation-index IDs (1.00004%)** from recovered commit `1ed3395fd537cc68eb97787fbcc0dae0df72a931`. This percentage is based on dataset IDs, independently of the earlier 5,217-word prose transfer.

## Selection and files

The sample contains the first `round(113295/100)` IDs in ascending Python string order across all 23 frozen ledger shards: `W1000361025` through `W1495603779` inclusive. No relevance, metadata-status or review-status filter is applied. This is a deterministic transfer sample; it is not a random or statistically representative literature selection.

- [Selected IDs](selected-ids.txt): exactly 1,133 unique records.
- [Complete records, gzip JSONL](records.jsonl.gz): original JSONL rows copied byte for byte, retaining bibliographic metadata, source URLs, minimum depths, parents, references, screening reasons and pending-review states.
- [Incident edges, gzip CSV](edges.csv.gz): all **4,497** frozen graph edges touching those IDs, including **32** edges internal to the sample. Original CSV rows and verification flags are unchanged.
- [Sample manifest](sample-manifest.json): sample statistics, exact selection rule, byte counts and SHA256 values.
- [Original full-dataset manifest](source-manifest.json): frozen source counts, limits and shard hashes; it describes the full checkpoint, not files all included here.

There are 3,469 external endpoint IDs in the incident-edge file. Their full records are outside the sample. The sample is not a self-contained graph traversal: original shortest depths and parents refer to the full checkpoint. Historical level-3 reference lists remain inert provenance; references outside the frozen edge set are not added or traversed.

## Integrity checks

From the repository root:

```bash
python3 docs/literature/citation-sample-01/check_sample.py
python3 scripts/check_docs.py
```

With the recovered full-data directory available, reproduce selection and verify exact source rows and complete incident edges:

```bash
python3 docs/literature/citation-sample-01/check_sample.py --source /path/to/recovered-level3/data
```

The optional source check also verifies every compressed source file against its original manifest. [The checker](check_sample.py) uses only the Python standard library and performs no network access or paper review.

## Interpretation and project status

These records are citation-index IDs, not a fully deduplicated and version-reconciled set of papers. Automated topic screening does not establish substantive applicability; no-topic signals and missing metadata are not scientific exclusions. Substantive-review states remain pending. Original abstracts and complete papers are not included.

Publication of this sample does not complete the literature review or transfer the remaining 99% of the full dataset. Research is stopped; S4-B remains paused and level 4 deferred. No new collection, scientific reassessment or numerical work occurred. AI assisted the original collection/screening and this extraction; the records do not constitute expert certification. Requirements SCI-003/004 and REP-001/002. Tracks [issue #16](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/16) and [PR #17](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/17).
