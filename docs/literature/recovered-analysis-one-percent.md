# Recovered analysis sample: approximately 1%

31 October 2026 (Australia/Melbourne). Extracted from the recovered PR #17 analysis at local commit `1ed3395fd537cc68eb97787fbcc0dae0df72a931`. This publishes one complete existing source assessment without new literature review.

## Selection and provenance

The sample is **54 of 5,217 whitespace-delimited words (1.0351%, rounded to 1.04%)** in the recovered written-review corpus defined below. The assessment is copied verbatim, including its heading, source link and review-depth qualification. This is a prose sample, not 1% of the citation graph or 1% of completed paper reviews. These provenance annotations are excluded from the sample word count.

| Recovered source | Counted words |
|---|---:|
| `depth4/LEVEL3_REVIEW.md` | 918 |
| `depth4/BATCH2_REVIEW.md` | 1172 |
| `recovered-level3/SECOND-PASS.md` | 1294 |
| `recovered-level3/IMPACT.md` | 927 |
| `recovered-level3/seed-first-pass.csv` | 715 |
| `recovered-level3/follow-up-first-pass.csv` | 191 |
| **Total** | **5,217** |

Markdown files are counted in full using Python `str.split()`. For seed rows, the counted fields are `content_summary`, `applicability_assessment`, and `review_basis`; for follow-up rows, `content_summary`, `applicability_assessment`, and `review_depth`. Repeated historical text remains part of this explicitly defined denominator.

Original source: `docs/literature/depth4/BATCH2_REVIEW.md`, section L31. Source SHA256: `9fecd931c7d1d6bebed6bd653cc338172db4cf32d72037f0059aab0a261572d3`.

## Preserved assessment

### L31 — Tze and Ezawa (1976), depth 3

[Publisher](https://journals.aps.org/prd/abstract/10.1103/PhysRevD.14.1006). Publisher abstract only; detailed second pass pending.

Classifies vortices and monopoles using global gauge-group topology and Higgs-field structure. Potential use: compare changed field content/topological assumptions in S5 specifications. No equations are imported and no exception to the smooth source-free B0 charge constraint is inferred.

## Bibliographic identity and limits

H. C. Tze and Z. F. Ezawa, *Global signatures of gauge invariance: Vortices and monopoles*, Physical Review D **14**, 1006 (1976). [DOI: 10.1103/PhysRevD.14.1006](https://doi.org/10.1103/PhysRevD.14.1006). Recovered identity: OpenAlex `W1327516`; applicability: `potentially_applicable`. The recorded index path is `L08 → W2134251287 → W1981960713 → W1327516`; full printed-reference-chain reconciliation remains pending. L31 is the recovered review label, not a new recursion seed.

The assessment reflects publisher-abstract access only. Full-text review and any equation verification remain pending. The project review is incomplete; S4-B remains paused and level 4 deferred. This publication does not release either gate or claim new numerical results.

AI assistance was used in the original assessment and this extraction. Primary authors retain authorship of the cited work; this project assessment is provisional. Related requirements: SCI-003/004, TOP-001, MOD-001/002 and REP-001/002. Tracks [issue #16](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/16) and [PR #17](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/17).
