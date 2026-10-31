# Recovered analysis transfer — batch 4

This batch transfers **473 words (9.07%)** of the fixed 5,217-word written-analysis corpus. Together with earlier merged samples and batches, coverage reaches **2,514/5,217 words (48.19%)**.

The source is recovered commit `1ed3395fd537cc68eb97787fbcc0dae0df72a931`. Original review depths, negative findings and limitations are preserved. Research remains incomplete and stopped; S4-B paused; level 4 deferred. Historical next-action instructions below are superseded by this hold. No new literature review occurred.

[Exact source fragments](batch-04.json) retain the original text and source word ranges. For readability, internal historical links below are shown as source-relative references; public paper links remain active. Source labels and fields for CSV material are recorded in [the manifest](manifest.json). AI assistance is disclosed.

## Source: `depth4/BATCH2_REVIEW.md`, words 1124–1172

Maintainer instruction after this batch: stop further literature review and consolidate existing work for merge. Full-text gaps, L01 identity issues and the final impact/disposition report remain unfinished and suspended. Keep level 4 deferred and S4-B paused.

AI assisted source extraction, assessment and documentation; specialist scientific certification is not claimed.

## Source: `recovered-level3/SECOND-PASS.md`, words 1–424

> Historical recovered record, preserved for provenance. Local L20–L25 labels may differ from the main register; consult the alias mapping (historical source reference: `../depth4/bibliography-aliases.json`). The consolidation decision (historical source reference: `../depth4/CONSOLIDATION.md`) supersedes operational instructions below: research is stopped, level 4 deferred, S4-B paused. Historical validation statements apply to that earlier workspace.

# Second-pass notes: initial source audits

**Work in progress, not the completed corpus review.** This file records targeted audits already possible from the seed papers and one directly cited primary paper. It does not certify that every potentially applicable level-3 paper has been reviewed. Prior project source inspections are identified as carry-forward evidence. New PDF retrieval alone does not upgrade an entry to a fresh equation audit. URLs, retrieval hashes and bibliography coverage accompany the checkpoint.

## A01 — Initial nullness versus global null transport

Source: Kedia, Peralta-Salas and Irvine, *When do knots in light stay knotted?*, J. Phys. A 51 (2018), 025204, [DOI](https://doi.org/10.1088/1751-8121/aa9749), [author-hosted journal PDF](https://irvinelab.uchicago.edu/papers/Kedia_2018_J._Phys._A__Math._Theor._51_025204.pdf). Reached from L05 reference 17, L15 reference 17 and L19 reference 33. Fresh targeted inspection: journal pp. 2–6, Sections 2–3, Eqs. (4), (9)–(10); Appendix C is referenced by the authors, not independently reproved here.

Applicable aspect: for analytic initial fields with a smooth normalised Poynting flow, their initial-data criterion includes both $\mathbf F\cdot\mathbf F=0$ and $\mathbf F\cdot(\nabla\times\mathbf F)=0$. Initial nullness alone is insufficient; the source explicitly requires the flow to be “initially shear-free”. Transport uses energy-normalised electric/magnetic fields for generally compressible flow.

Impact: current Bateman fields are analytical globally null constructions, and S3-C already separates generic non-null perturbations. No existing result is invalidated by this targeted check. Before a more general initial-data generator claims persistence, add a source-mapped shear-free diagnostic and state analyticity/smooth-flow assumptions, including treatment of zeros. This is a proposed next validation task, not a newly implemented instrument.

## A02 — Non-containment of transported closed field lines

Source: Bode, [arXiv:2409.20357v1](https://arxiv.org/abs/2409.20357v1), freshly inspected Theorem 1.8 (PDF p. 5), Section 6/proof (pp. 21–22) and Remark 6.1 (p. 25). The [journal abstract](https://doi.org/10.1016/j.topol.2026.109803) is accessible; the attempted journal-PDF endpoint returned a non-PDF payload. Version reconciliation is pending.

Applicable aspect: closed electric/magnetic field-line sets in this Hopf-type Bateman class eventually leave every fixed compact set. This is not an energy-containment theorem for arbitrary moving regions or nonlinear theories.

Impact: retain independent S3-B energy localisation and do not infer confinement from knot persistence.

## A03 — Constructive existence is not a turnkey polynomial generator

Same source, Theorems 1.5–1.6 and Remark 1.7, pp. 4–5. Trigonometric Legendrian representatives lead to candidate linear systems, with different guarantees for homogeneous and inhomogeneous problems. General polynomial solvability, extra zeros and regularity remain qualifications.
