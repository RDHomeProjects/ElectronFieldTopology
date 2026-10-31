# Recovered analysis sample: approximately 10%

31 October 2026 (Australia/Melbourne). Extracted from the recovered PR #17 analysis at local commit `1ed3395fd537cc68eb97787fbcc0dae0df72a931`. This publishes existing analysis; no further source acquisition or literature review was performed.

## Selection and provenance

The sample is **519 of 5,217 whitespace-delimited words (9.9482%, rounded to 9.95%)**, using the same recovered written-review corpus as [the earlier 1% sample](recovered-analysis-one-percent.md). It includes seven complete contiguous source assessments, L24–L30, together with the original section heading and the original project-assessment attribution sentence. Those components are copied verbatim. The earlier Tze–Ezawa sample, L31, is not repeated.

This percentage measures written-review prose, not citation-graph records or completed paper reviews. Provenance annotations outside the preserved excerpt are excluded from its word count.

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

Original source: `docs/literature/depth4/BATCH2_REVIEW.md`. Source SHA256: `9fecd931c7d1d6bebed6bd653cc338172db4cf32d72037f0059aab0a261572d3`. Each assessment retains its primary-source link, inspected locations and access/version limitations. Historical L24–L30 labels identify recovered assessments and do not add recursion seeds.

## Preserved excerpt begins

## Reviewed sources and precise applicable aspects

### L24 — Kedia, Peralta-Salas and Irvine (2018)

[Journal PDF](https://irvinelab.uchicago.edu/papers/Kedia_2018_J._Phys._A__Math._Theor._51_025204.pdf), Sections 2–3, Eqs. (4), (9)–(10), Corollary B.1. Targeted full text/PDF inspection. The journal volume is 2018; online publication was December 2017.

Global null persistence requires more than null initial data under the stated analytic/flow hypotheses. Compressible transport uses energy-normalised fields. Proposed acceptance refinement: check the initial complex-curl condition and the smooth extension of the Poynting flow through field zeros before invoking persistence. A sampled residual is not a theorem certificate. No current S3-C result is invalidated.

### L25 — Whitehead (1947)

[Primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC1079004/pdf/pnas01698-0025.pdf), Section 1, pp. 117–118, Eqs. (1.1)–(1.4). Targeted primary-text inspection; formula rendering contains OCR defects, so no transcription-to-code audit is claimed.

The integral representation applies to a specified normalised map from the three-sphere to the two-sphere. Proposed use: require a map, orientation and normalisation before interpreting a helicity integral as an integer Hopf invariant. The present physical-field helicities retain their existing amplitude and domain conventions.

### L26 — Derrick (1964)

[Primary scan hosted by the University of Athens](https://eclass.uoa.gr/modules/document/file.php/PHYS181/%CE%94%CE%B9%CE%B1%CE%BB%CE%AD%CE%BE%CE%B5%CE%B9%CF%82%20%CE%BA%CE%B1%CE%B9%20%CE%A5%CE%BB%CE%B9%CE%BA%CF%8C%202021-2022/%CE%A5%CE%BB%CE%B9%CE%BA%CF%8C%20%CE%BC%CE%B5%CE%BB%CE%AD%CF%84%CE%B7%CF%82%20-%20%CE%B1%CE%BD%CE%B1%CF%86%CE%BF%CF%81%CE%AD%CF%82%202021/DERRICK_THEOREM1.1704233.pdf), Section 2 and Section 3, pp. 1253–1254; proof page visually checked.

For its scalar/multicomponent energy class, dilation rules out stable nontrivial static localised solutions. Higher derivative powers, different kinetic structures and time dependence require separate analysis. Proposed use: a model-specific scaling audit before S5 selection. This is not an exclusion theorem for every electromagnetic or time-periodic theory.

### L27 — Faddeev and Niemi (1997), related 1996 preprint

[Publisher record](https://doi.org/10.1038/387058a0); [arXiv:hep-th/9610193v1, “Knots and Particles”](https://arxiv.org/abs/hep-th/9610193v1). Targeted preprint pp. 2–4, Eqs. (1)–(5); scaling page visually checked. Final journal/preprint reconciliation pending.

The unit-vector model balances quadratic and quartic gradient energies. Its minimisation flow and adjusted coupling are computational choices, not demonstrated physical relaxation or emergent electron scales. Proposed use: compare candidate S5 energy functionals and distinguish optimisation time from physical time. No extension is selected.

### L28 — Fuller (1971)

[Original page scans](https://pmc.ncbi.nlm.nih.gov/articles/PMC389050/), pp. 816–817, Sections 2–3, Eqs. (1)–(3), visually inspected.

Writhe describes curve geometry through a ribbon/link relation and directional averaging. It does not provide a complete knot classifier. Proposed use: optional geometry/orientation cross-checks for genuinely closed, disjoint curves; do not label an open or quasi-periodic trace by forcibly closing it. No writhe implementation is added.

### L29 — Chui and Moffatt (1992), depth 3

[Author-hosted chapter](https://www.damtp.cam.ac.uk/user/hkm2/PDFs/Chui_Moffatt_1992_Kluwer_Memfwtt_195.pdf), pp. 195–201, Sections 1–3; opening assumptions visually inspected.

The minimisation fixes flux and the volume/helicity functions associated with magnetic surfaces in a perfectly conducting incompressible fluid. Axisymmetric equilibria need not withstand non-axisymmetric perturbations. Proposed use: document the entire admissible constraint class before comparing energy minima; these equilibria are not vacuum self-binding evidence. Numerical asymptotics and stability are not reproduced.

### L30 — Yakovenko (1989), depth 3

[arXiv:cond-mat/9703195v1](https://arxiv.org/html/cond-mat/9703195v1), Eqs. (1)–(10) and surrounding discussion. Targeted full HTML inspection. Published in 1989; uploaded in 1997.

Spin and charge follow from a specified two-space-plus-one-time microscopic model with electron fields already present. Proposed use: keep the microscopic input, dimension and quantisation mechanism explicit in S7 comparisons. Its soliton quantum numbers cannot be imported as predictions of a photon-only Maxwell model.

These are project assessments, not claims that the cited authors evaluated our code.

## Preserved excerpt ends

## Status and limitations

The complete recovered review remains incomplete. S4-B is paused and level 4 deferred; publication of this sample does not release either gate. No numerical implementation, tolerance or S1–S4-A evidence is changed. Review-depth descriptions report the original assessment, not a fresh verification of the papers during this publication.

AI assistance was used in the original assessments and this extraction; specialist scientific certification is not claimed. Related requirements: SCI-003/004, TOP-001, MOD-001/002 and REP-001/002. Tracks [issue #16](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/16) and [PR #17](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/17).
