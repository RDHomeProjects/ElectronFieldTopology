# Recursive literature checkpoint protocol

Requested: 2026-10-31 (Australia/Melbourne). Baseline: `ae0a1908b5081d4fe24948a5892a76d0220bd4d0`, after S3-D PR 13 and S4-A PR 15 merged. S4-B is paused for this checkpoint.

## Scope and graph

The 19 papers L01–L19 in [the register](../README.md) form depth 0; [frozen identities](seeds.json) specify the seed set. Follow backward references, not papers citing the seed. Include reference levels 1–4. Do not discard an edge because its target appears inapplicable. Expand each deduplicated work at its shortest depth; retain all parent edges and a traceable seed path. Depth-4 works are screened but their references are not traversed. Books, proceedings, historical sources and inaccessible records remain in the ledger. Tools/teaching websites outside L01–L19 are not extra seeds.

OpenAlex supplies a first citation-index traversal; publisher/Crossref and available primary bibliographies provide identity and coverage checks. An index reference list can be incomplete, wrong or version-merged. No zero-reference index record is treated as proof that the paper has no references. Record missing records, API failures, uncertain matches, raw unparsed references and bibliography discrepancies; never label an index-only closure as the entire published literature. Graph inclusion is not endorsement.

## Two passes

Pass 1 retains one record per discovered work, its ID/title/year/source, minimum depth, parent relationships, content summary, applicability/reason, access and review depth. Separate automated metadata/abstract screening from substantive AI reading. Title-only records cannot receive a claimed content review. Unknown is an explicit disposition, not rejection. No citation-count ranking.

Pass 2 examines potentially applicable works for the specific transferable aspect, version and section/page/equation/theorem, assumptions/domain, limitations, proposed use and effect on existing results. Do not claim a full-text or equation audit from an abstract. Unretrieved potentially applicable works remain pending and prevent an unqualified completion claim.

## Development audit

Assess S1–S4-A source mappings, Maxwell/null and integral instruments, Lorentz/centroid treatment, helicity/link orientation/gauge, tracing and closure, and confinement/charge/spin language. Maintain an action matrix distinguishing corrections required now, additional validation, future extensions and no-change findings. No numerical result is rerun or revised just to agree with a paper. Review theorem hypotheses before invoking a no-go conclusion.

## Reproduction and integrity

`python scripts/collect_literature.py --depth 4` uses a checkpointed ignored cache, at most three concurrent public API requests and bounded retries. No API key/account, paid service or network collection in CI. Bibliographic graph artifacts record retrieval dates, provider, depth and gaps. Link primary papers rather than redistributing PDFs or complete abstracts. Local text/PDF inspection stays in ignored artifacts. Review notes disclose AI assistance and never imply specialist certification.

Completion requires graph/gap accounting, an assessed first-pass row for every discovered item, pass-two notes or explicit access-blocked status for every retained item, a development-impact assessment, documentation integrity and human review. A large corpus or an access gap must be reported honestly; draft status is retained until the acceptance evidence supports completion.
