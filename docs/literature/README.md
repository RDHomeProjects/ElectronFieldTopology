# Literature register

Last checked: 2026-10-31. This is a scoped starting bibliography, not an exhaustive systematic review or a claim to identify the latest result in every subfield.

Each entry records why it matters and what it does not establish. Metadata/abstract checking does not equal verification of its equations. Before implementation record the precise version and equation/page references in the model specification. Primary mathematical papers supply methods, experimental papers supply benchmarks, and proposed electron models supply hypotheses.

## Sources used to frame the project

### L01 — Confined-photon electron proposal

J. G. Williamson and M. B. van der Mark (1997), *Is the electron a photon with toroidal topology?* Annales de la Fondation Louis de Broglie 22(2), 133-160.
[Publisher PDF](https://fondationlouisdebroglie.org/AFLB-222/MARK.TEX2.pdf).

Role: motivation for exploring self-confined electromagnetic structures. Section 2 develops a double-loop toroidal construction and acknowledges other knots; Section 7 leaves detailed self-confinement dynamics unresolved. Its electron-property claims are proposals to assess, not accepted evidence that electrons contain photons.

Review depth: abstract and relevant topology/confinement passages checked. No numerical reproduction. Stages: S0, S5.

### L02 — Explicit torus-knot Maxwell solutions

H. Kedia, I. Bialynicki-Birula, D. Peralta-Salas and W. T. M. Irvine (2013), *Tying Knots in Light Fields*. Physical Review Letters 111, 150404.
[DOI](https://doi.org/10.1103/PhysRevLett.111.150404).

Role: primary construction of null Maxwell fields encoding torus knots and links with topology preserved during evolution. Candidate source for valid field families. Knot preservation is not a demonstration of charged, self-bound electrons.

Review depth: publisher metadata/abstract checked; equation extraction pending. Stages: S1, S4.

### L03 — Numerical reproduction benchmark

A. M. Valverde, L. D. Angulo, M. R. Cabello, S. G. Garcia, J. J. Omiste and J. Luo (2020), *Numerical simulation of knotted solutions for Maxwell equations*. Physical Review E 101, 063305.
[DOI](https://doi.org/10.1103/PhysRevE.101.063305); [arXiv version](https://arxiv.org/abs/2003.01896).

Role: FDTD simulation and validation of Hopfion solutions; useful benchmark for independent numerical evolution. A simulation reference, not an electron model.

Review depth: arXiv metadata/abstract checked; implementation details and equation verification pending. Stages: S1-S2.

### L04 — Existence beyond torus links

Benjamin Bode (2021), *Stable Knots and Links in Electromagnetic Fields*. Communications in Mathematical Physics 387, 1757-1770.
[DOI](https://doi.org/10.1007/s00220-021-04219-3).

Role: existence results for arbitrary persistent link types in free Maxwell fields. The paper distinguishes existence from explicit construction; its theorem is not an immediately runnable generator for every knot. Stable topology must not be interpreted as stationary energy confinement.

Review depth: abstract/introduction and construction limitation checked. Stages: S3-S4.

### L05 — Constructive methods and a confinement limitation

Benjamin Bode (2024 arXiv submission), *Totally tangential C-links and electromagnetic knots*.
[arXiv:2409.20357v1](https://arxiv.org/abs/2409.20357v1).

Role: proposes algorithms for Legendrian representatives and candidate Bateman fields; also states that no compact spatial subset contains an electromagnetic knot indefinitely in the Hopf-type class considered. Relevant to both search design and stop conditions.

Do not generalise that statement to every possible nonlinear field theory. Verify theorem assumptions and publication/version updates before using it as a formal exclusion.

Review depth: arXiv metadata/abstract checked. Stages: S3-S5.

### L06 — Spin as Dirac-field circulation

Charles T. Sebens (2019), *How Electrons Spin*.
[Author manuscript record](https://authors.library.caltech.edu/records/xjs66-atp16); [arXiv:1806.01121](https://arxiv.org/abs/1806.01121).

Role: explores angular momentum and magnetic moment through mass/charge flow in a Dirac-field description. This is a different field from ordinary Maxwell electromagnetism and is not evidence for a photon-only electron.

Review depth: author-record abstract checked. Stage: S7 and interpretation constraints.

### L07 — Charged topological-soliton model

Manfried Faber and Alexander P. Kobushkin (2004), *Electrodynamic Limit in a Model for Charged Solitons*. Physical Review D 69, 116002.
[DOI](https://doi.org/10.1103/PhysRevD.69.116002); [arXiv version](https://arxiv.org/abs/hep-th/0207167).

Role: investigates finite-mass charged solitons and an electrodynamic limit in a specified model. Illustrates why the field theory must accompany the topology. It is not a result obtained by merely knotting a source-free Maxwell wave.

Review depth: arXiv metadata/abstract checked; model equations and quantum implications pending. Stage: S5.

### L08 — Experimental electron benchmark

X. Fan, T. G. Myers, B. A. D. Sukra and G. Gabrielse (2023), *Measurement of the Electron Magnetic Moment*. Physical Review Letters 130, 071801.
[DOI](https://doi.org/10.1103/PhysRevLett.130.071801).

Role: experimental magnetic-moment benchmark with reported 0.13-parts-per-trillion relative precision. A later electron model must identify which corrections and uncertainty it can actually predict. Fitting approximately g = 2 is not equivalent to matching this measurement.

Review depth: publisher metadata/abstract checked. Stage: S7. This entry is a benchmark, not a claim that no newer measurement exists.

## Recent contextual reading queue

### L09 — 2025 electron-model review

*Critical Review of Zitterbewegung Electron Models* (2025), Symmetry 17(3), 360.
[Publisher](https://www.mdpi.com/2073-8994/17/3/360); [DOI](https://doi.org/10.3390/sym17030360).

Discovery/context only. Metadata and abstract located; full critical appraisal and independent verification of cited claims are pending. Do not use a review's assessment as primary proof of a proposed mechanism. Follow its references to the original equations and experiments.

## Background and tools

- [Feynman Lectures III, Chapter 19](https://www.feynmanlectures.caltech.edu/III_19.html): atomic orbitals and the distinction between orbital angular momentum and electron spin.
- [SymPy](https://docs.sympy.org/): symbolic checks.
- [SciPy](https://docs.scipy.org/doc/scipy/): numerical analysis.
- [PyVista](https://docs.pyvista.org/): 3D field inspection.
- [Dedalus](https://dedalus-project.readthedocs.io/en/latest/): potential custom-PDE framework.
- [Meep](https://meep.readthedocs.io/en/latest/): potential independent Maxwell solver.

Tool documentation is an implementation reference, not evidence for the physical hypothesis.

## Updating this register

At each research stage, search for relevant corrections, later versions and counterexamples. Record search date, query scope, source version and review depth. Add primary sources for every new equation or empirical comparison. Link papers instead of copying them without permission. Citation is not endorsement.

For sources with only abstract-level review, do not imply that detailed mathematical claims have been independently audited. Maintain disagreements and negative results alongside supporting literature.
