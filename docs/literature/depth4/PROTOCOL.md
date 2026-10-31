# Recursive literature checkpoint protocol

Requested: 2026-10-31 (Australia/Melbourne). Baseline: `ae0a1908b5081d4fe24948a5892a76d0220bd4d0`, after S3-D PR 13 and S4-A PR 15 merged. Maintainer scope clarification: continue applicability review through level 3; undertake no level-4 collection, screening or substantive review. S4-B remains paused.

## Active scope and retained graph

The 19 papers L01–L19 in [the register](../README.md) form depth 0; [frozen identities](seeds.json) specify the seed set. Follow backward references, not citing papers. Levels 1–3 are the active scope. The original four-level objective is deferred at level 4, not completed or abandoned. Existing corpus, edges, unknowns, notes and access gaps must be retained; a supplemental acquisition must never replace a larger existing checkpoint. Keep this directory/branch name for continuity.

Do not prune the level-1–3 graph by apparent relevance. Expand each deduplicated work at its shortest known depth; retain all parent edges and traceable seed paths. Do not retrieve or expand level-3 bibliographies to discover level 4. Keep any previously encountered level-4 IDs deferred without further work. Newly promoted bibliography entries are not additional recursion seeds.

OpenAlex supplies an initial citation-index traversal. Publisher/Crossref and available primary bibliographies check identity and coverage. An index can omit, misidentify or merge references. A zero-reference index record is not proof of an empty bibliography. Record missing records, uncertain matches, API failures and bibliography discrepancies. Index closure is never described as complete published-bibliography coverage. Graph inclusion is not endorsement. Later corrections/version checks are supplementary source verification, not extra recursion seeds; do not expand their bibliographies automatically.

## Applicability review through level 3

Pass 1 records every encountered identity, source, shortest known depth or qualified path bound, parent relationships, content summary, applicability/reason, access and review depth. Distinguish unreviewed, title-only, abstract-based, targeted full-text and equation-audited records. A priority flag is not a content summary or an applicability decision. Unknown is not rejection. No citation-count ranking.

Pass 2 examines retained sources for transferable aspects, exact version and section/page/equation/theorem, assumptions/domain, limitations, proposed use and effects on existing work. Inaccessible potentially applicable papers remain pending. An abstract cannot establish a full-text or equation audit. [Current review notes and pending work](LEVEL3_REVIEW.md) distinguish incremental progress from completion.

## Main bibliography and development audit

When a paper influences a method, interpretation, diagnostic, validation requirement or roadmap choice, add it to both [the main literature register](../README.md) and [references.bib](../references.bib), with its role, review depth, limitations and a link to the impact record. Include relevant corrections. Record no-change findings and counterevidence as well as proposed changes. Promotion does not expand the frozen seed set.

Audit S1–S4-A source mappings, Maxwell/null and integral instruments, Lorentz/centroid treatment, helicity/link orientation/gauge, tracing/closure, and confinement/charge/spin language. The [impact matrix](LEVEL3_REVIEW.md) separates immediate corrections, validation proposals, later extensions and no-change findings. Review theorem hypotheses before applying exclusions. Do not rerun or revise numerical results merely to agree with a paper.

## Collection and reproduction

`python scripts/collect_literature.py --depth 3 --max-new-records 1000` resumes an ignored cache with at most three concurrent requests, bounded retries and a non-seed metadata budget per invocation. The collector rejects depth 4 before output/network activity and omits bibliography fields when retrieving depth-3 records. It checkpoints the full current frontier before budgeting and stops at an unfinished acquisition frontier. Failed cache entries are retried on restart; HTTP 429 stops that request. Provenance includes request URLs and retrieval timestamps. No API keys, paid services, network collection in CI or recurring jobs are introduced.

The [supplemental acquisition manifest](acquisition-supplement.json) identifies the new partial snapshot and its limitations. Preserve earlier independent checkpoints separately until identity/edge reconciliation is possible. Do not interpret missing earlier bytes as proof that earlier work never occurred. Link primary papers; do not redistribute PDFs or complete abstracts. AI assists extraction and assessment; specialist certification is not claimed.

## Gates

S4-B remains paused until the level-3 corpus and gaps are reconciled, every encountered work has a documented first-pass disposition (with unresolved cases visible), retained sources have pass-two findings or explicit access-blocked treatment, influential papers are in the main bibliography, and the development-impact report identifies proposed changes and their disposition for maintainer review. Partial batches and metadata-only screening do not satisfy this gate.

Neither collection completion nor finishing a batch authorises level 4 or resumes S4-B automatically. Level 4 requires a later explicit maintainer scope decision after the level-3 results are assessed. The draft PR remains open while the level-3 review is incomplete.
