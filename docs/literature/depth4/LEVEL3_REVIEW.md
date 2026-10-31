# Level-3 applicability review: progress and development impacts

Updated: 2026-10-31 (Australia/Melbourne). **Incomplete. S4-B paused. Level 4 deferred with no collection or review authorised.** Tracks [issue 16](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/16) and [draft PR 17](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/17).

## Corpus continuity and coverage

Prior project context reports a frozen checkpoint of 113,295 index IDs, 93,657 metadata records, 243,005 edges, 19,487 queued IDs and 151 unresolved. These are historical reported counts, not independently recounted here. Its compressed checkpoint and earlier notes could not be located in the current branch, workspace or file search. The independently fetched branch was still at `0f321bd`, containing only the protocol, seeds and collector. Recover/reconcile that earlier checkpoint before making any whole-corpus completion claim. Do not replace it with the supplemental snapshot.

This continuation publishes a separate, bounded [acquisition supplement](acquisition-supplement.json) and [machine-readable applicability notes](applicability.json). The supplement preserves all IDs encountered in this run and parent edges through the allowed depth, including records whose metadata was not acquired. It does not recreate the earlier level-3 corpus. OpenAlex returned HTTP 429 for two seed title searches and the last two first-level batches. No level-4 requests or reviews were made. The absence of a record here is not an inapplicability decision.

Four newly assessed cited papers are promoted as L20–L23 in [the main bibliography](../README.md), together with the relevant Moffatt correction in BibTeX. The original 19 recursion seeds remain unchanged. Their review depths differ; abstract-only items still need substantive follow-up. All other supplement records are unreviewed. This batch is not the completed first or second pass over level 3.

## Incremental source notes

### L20 — Newcomb (1958)

[Publisher](https://doi.org/10.1016/0003-4916(58)90024-1). Printed discovery: L12 reference [19]. Review: publisher abstract, not full text; pass 2 pending.

Separates flux-preserving and line-preserving transport and discusses the observer dependence of simultaneous field lines. Applicable to specifying what a tracked trajectory represents. Before implementing its criteria, inspect the original equations, units and smoothness assumptions. A transport velocity is not automatically material motion or confinement. Proposed use: make transport/observer assumptions explicit in future topology evidence.

### L21 — Moffatt (1969), with 2017 correction

[Original](https://doi.org/10.1017/S0022112069000991); [corrigendum](https://doi.org/10.1017/jfm.2017.667). Printed discovery: L12 [22]. Review: original publisher abstract/references; correction full HTML, pp. 821–822. Original mathematical audit pending.

The original relates helicity and vortex linkage under specified fluid assumptions. The correction revises pitch-limit arguments for Hicks-vortex lines and distinguishes velocity trajectories from vorticity trajectories. It does not invalidate helicity generally or directly correct our Maxwell implementation. Proposed use: require independently measured winding/closure for the actual traced vector field; do not infer available knot types from a shared toroidal surface or an assumed pitch range.

### L22 — Berger and Field (1984)

[DOI](https://doi.org/10.1017/S0022112084002019); [primary-paper PDF](https://www.hao.ucar.edu/people/phil-judge/Book/preparations/bergerfield84.pdf). Discovery: L19 index edge; printed parent-bibliography reconciliation pending. Review: targeted text and PDF visual inspection, p. 134 Eq. (3), pp. 140–142 Section 3; not a whole-paper audit.

An open subvolume needs an appropriate reference-field construction for gauge-independent relative helicity. A Coulomb-gauge choice alone does not resolve unknown exterior structure. Applicable before adding finite-window/open-boundary helicity claims. The paper's domain and reference-field hypotheses must be mapped; its plasma interpretation is not vacuum self-binding. Existing periodic and unbounded diagnostics retain their declared domains.

### L23 — Woltjer (1958)

[DOI](https://doi.org/10.1073/pnas.44.6.489); [primary scans](https://pmc.ncbi.nlm.nih.gov/articles/PMC528606/). Discovery: L19 index edge; also L12 → Moffatt (1969) → Woltjer (1958a) in printed references. Review: all three scanned pages 489–491; targeted variational argument, Eqs. (2)–(10).

The magnetic-energy minimum at fixed helicity is derived for a closed, perfectly conducting system, with a force-free equilibrium and constant parameter. It supplies a conditional comparison, not a vacuum radiation-confinement theorem. Proposed use: require an explicit boundary/current/constraint map before applying relaxation or minimum-energy arguments to B0 or a proposed extension. No current numerical result needs alteration from this reading.

## Development-impact register

These are project assessments based on the cited passages, not additional claims made by the papers. Numerical dynamics and S1–S4-A outputs are unchanged.

| ID | Source | Effect on approach | Disposition |
|---|---|---|---|
| LR3-01 | Maintainer scope | Level-3 review first; no level-4 work; preserve earlier corpus | Enforced in collector/protocol; overall review pending |
| LR3-02 | L20 | State transport and observer assumptions | Proposed validation specification; original full text pending |
| LR3-03 | L21 and correction | Verify winding and closure for the actual vector field | Proposed S4-B acceptance refinement; no S4-B implementation now |
| LR3-04 | L22 | Separate finite-window helicity from declared-domain diagnostics | Required specification before such an extension; current S3-D claims retained |
| LR3-05 | L23 | Map boundary and model assumptions before energy-minimum comparisons | Interpretation constraint; no numerical correction identified |
| LR3-06 | Main bibliography policy | Promote influential papers, including corrections, without enlarging seed set | L20–L23 and correction added in this PR |
| LR3-07 | Collector recovery | Retry failed cache entries and retain full budgeted frontier with provenance | Implemented; offline regression checks |

## Remaining work and release gate

1. Recover and reconcile the reported larger checkpoint and its previous assessments. Preserve independent copies and provenance; reconcile by work identity and edges, not by replacing counts.
2. Continue record-by-record applicability review throughout the level-1–3 corpus, retaining unknown/access-blocked items. Resolve seed identity, provider-throttling and printed-bibliography gaps without presenting metadata as read papers.
3. Complete targeted second-pass work for retained sources, including the original Newcomb and Moffatt texts and any additional influential papers. Link each promotion to a bibliography entry and an impact decision.
4. Finish the S1–S4-A impact audit. Record required changes, validation additions, deferred extensions and no-change findings, with rationale.
5. Present the level-3 results and proposed changes for maintainer review before any S4-B resumption. This batch neither closes issue 16 nor authorises level 4.

AI assistance: source discovery, extraction, assessment and code were assisted by AI. No specialist scientific certification or complete systematic review is claimed.
