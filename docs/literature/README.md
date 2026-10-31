# Literature register

A [frozen 1% citation-dataset sample](citation-sample-01/README.md) publishes 1,133 complete records with their incident citation edges and reproducible integrity checks.

The recovered written-analysis corpus is now published: [reading index, source provenance and completeness checks](recovered-transfer/README.md). This transfer is complete; the scientific review remains incomplete and S4-B has resumed in a bounded study; see the source map below.

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

Review depth: arXiv:1302.0342v1 Eqs. (5), (9)-(11), unnumbered coprime core parametrisation and time-flow discussion inspected for [S4-A](../models/B0-Bateman-PQ.md), including PDF visual checks. The report separates source-provided core labels from numerical invariants and retains the v1 special-case ring-count convention discrepancy. This is not an audited comparison with a later journal text. Stages: S1, S4.

### L03 — Numerical reproduction benchmark

A. M. Valverde, L. D. Angulo, M. R. Cabello, S. G. Garcia, J. J. Omiste and J. Luo (2020), *Numerical simulation of knotted solutions for Maxwell equations*. Physical Review E 101, 063305.
[DOI](https://doi.org/10.1103/PhysRevE.101.063305); [arXiv version](https://arxiv.org/abs/2003.01896).

Role: FDTD simulation and validation of Hopfion solutions; useful benchmark for independent numerical evolution. A simulation reference, not an electron model.

Review depth: versioned PDF page 2, Eqs. (1)-(5), inspected for S1-A; (1,1) equations mapped and checked in [B0-H11](../models/B0-H11.md). S2 uses an independent Fourier propagator, not a reproduction of this paper's FDTD solver; FDTD remains an optional future cross-check.

### L04 — Existence beyond torus links

Benjamin Bode (2021), *Stable Knots and Links in Electromagnetic Fields*. Communications in Mathematical Physics 387, 1757-1770.
[DOI](https://doi.org/10.1007/s00220-021-04219-3).

Role: existence results for arbitrary persistent link types in free Maxwell fields. The paper distinguishes existence from explicit construction; its theorem is not an immediately runnable generator for every knot. Stable topology must not be interpreted as stationary energy confinement.

Review depth: abstract/introduction and construction limitation checked. Stages: S3-S4.

### L05 — Constructive methods and a confinement limitation

Benjamin Bode (2026), *Totally tangential C-links and electromagnetic knots*. Topology and its Applications 384, 109803 (May 2026).
[DOI](https://doi.org/10.1016/j.topol.2026.109803); [original 2024 arXiv version](https://arxiv.org/abs/2409.20357v1).

Role: constructive methods for Legendrian representatives and Bateman fields, with a limitation on indefinite containment in compact spatial regions for the class considered. Relevant to search design and stop conditions. Distinguish the original preprint from the final publication before implementation.

Do not generalise that statement to every possible nonlinear field theory. Verify theorem assumptions and publication/version updates before using it as a formal exclusion.

Review depth: original preprint abstract and 2026 publisher abstract checked; publication confirmed against the author's list. Final-paper/preprint equation and theorem reconciliation remains pending. Stages: S3-S5. See the [pre-S3 assessment](pre-s3-review.md).

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

- [Feynman Lectures II, Chapter 20](https://www.feynmanlectures.caltech.edu/II_20.html), vacuum equations (20.12) and the linearity paragraph before (20.25), plus Section 20-2; [Chapter 27](https://www.feynmanlectures.caltech.edu/II_27.html), local balance (27.2), energy/Poynting definitions (27.14)-(27.15). Primary teaching sources rechecked for S3-C; exact short excerpts and measured comparisons are in [the report](../../reports/s3-c/README.md).
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

## L10 — Independent Fourier Maxwell propagation

B. B. Godfrey, J.-L. Vay and I. Haber (2014), *Numerical stability analysis of the pseudo-spectral analytical time-domain PIC algorithm*. Journal of Computational Physics 258, 689-704.
[DOI](https://doi.org/10.1016/j.jcp.2013.10.053); [arXiv:1305.7375v2](https://arxiv.org/abs/1305.7375v2).

Role: primary numerical method reference. Section 2, equations (1)-(2), inspected for the source-free vacuum specialisation and Fourier-sign conversion. [S2 model](../models/B0-H11-PSATD.md) records the implementation. Its plasma/beam stability results are not reproduced or claimed by this repository. Stage: S2.

## Pre-S3 additions (2026-10-31)

[Assessment and action priorities](pre-s3-review.md). These are literature findings and planned uses, not implemented capabilities. Review depth is specific to each entry.

### L11 — Covariant Bateman construction and generated solutions

Carlos Hoyos, Nilanjan Sircar and Jacob Sonnenschein (2015), *New knotted solutions of Maxwell's equations*. Journal of Physics A 48, 255204.
[DOI](https://doi.org/10.1088/1751-8113/48/25/255204); [accessible text/version](https://arxiv.org/abs/1502.01382v2).

Priority: S3-A and S4. S4-A rechecks Eqs. (2.21)-(2.22), the following momentum/helicity ratios and Eq. (4.48) for independent monomial-family integral references; see [the graphical report](../../reports/s4-a/README.md).

Full-text targeted inspection: Sections 2.1, 2.2, 3 and 4.1; Appendix C located. S3-A uses the p=q momentum/energy ratio and tensor convention with an explicit [equation mapping](../models/B0-H11-Lorentz.md). S3-D inspects Eqs. (2.7)-(2.12) and the Section 2.2 Hopfion helicity reference. The [model/report](../models/B0-H11-Topology.md) records an independently verified factor-of-two audit of the printed null-case exchange expression when interpreted away from null fields. Covariant definitions and conserved quantities offer references beyond the current polynomial implementation. Real Lorentz changes and complex conformal generation must be separated; a complex transformation is not a change of inertial observer. The literature review itself establishes no numerical result or electron conclusion; subsequent S3-A implementation is reported separately.

### L12 — Helicity is not a complete topology test

William T. M. Irvine (2010), *Linked and knotted beams of light, conservation of helicity and the flow of null electromagnetic fields*. Journal of Physics A 43, 385203.
[DOI](https://doi.org/10.1088/1751-8113/43/38/385203); [accessible text/version](https://arxiv.org/abs/1110.5408v1).

Priority: Immediate: S3-C; later S4.

Targeted HTML inspection: Sections 3-5, including the non-null counterexample; abstract and Sections 2-3 rechecked for S3-C. [The S3-C report](../../reports/s3-c/README.md) quotes a short orthogonality excerpt and compares only measured constraint/null diagnostics, not an uncomputed topology change. S3-D rechecks Eqs. (4)/(5)/(9) and the Hopf-fibration paragraph for [declared-domain helicity and selected closed-pair linking](../models/B0-H11-Topology.md), with an explicit orientation convention. Conserved helicity can accompany unravelling field lines. This motivates null-condition diagnostics and explicit topology tests rather than a helicity-only acceptance rule. The journal year is 2010 although the arXiv upload is 2011; do not silently change the publication year.

### L13 — Boosts and energy-centroid shifts

Konstantin Y. Bliokh and Franco Nori (2012), *Relativistic Hall Effect*. Physical Review Letters 108, 120403.
[DOI](https://doi.org/10.1103/PhysRevLett.108.120403); [accessible text/version](https://arxiv.org/abs/1112.5618v2).

Priority: Immediate: S3-A/B.

Full-text targeted inspection: energy centroid, angular-momentum tensor and boost discussion, Eqs. (1)-(4); Eqs. (1)-(3) rechecked for [S3-B](../models/B0-H11-Centroid.md), whose reference uses the complete conserved tensor instead of paraxial coefficients. Distinct centroid definitions and transverse shifts are useful warnings against simply contracting a picture. Some examples use paraxial approximations; their numerical coefficients must not be applied automatically to a non-paraxial Hopfion.

### L14 — Recent centroid guidance

Konstantin Y. Bliokh (2025), *On the Ehrenfest theorem and centroids of relativistic particles*. Physics Letters A 542, 130425.
[DOI](https://doi.org/10.1016/j.physleta.2025.130425); [accessible text/version](https://arxiv.org/abs/2412.11115v1).

Priority: Immediate: S3-B.

Full-text targeted inspection: Section II.2, Eqs. (7)-(9), and Section III. Energy weighting and boost momentum rechecked for [S3-B](../models/B0-H11-Centroid.md), alongside an independent Maxwell continuity/stress-energy derivation. Energy-weighted and probability-weighted centroids have different meanings. Use a Maxwell stress-energy derivation for our vector field; this paper's explicit scalar/fixed-polarisation approximations do not directly cover every Hopfion observable.

### L15 — Stable topology: recent mathematical structures

Benjamin Bode and Daniel Peralta-Salas (2025), *The topology of stable electromagnetic structures and Legendrian fields on the 3-sphere*. International Mathematics Research Notices 2025(11), rnaf155.
[DOI](https://doi.org/10.1093/imrn/rnaf155); [accessible text/version](https://arxiv.org/abs/2302.01043v2).

Priority: S3-C terminology; S4 construction.

Targeted preprint inspection: Introduction, Section 1.1 and main construction context. Null-field topology preservation is conditional on the stated flow regularity; this is not robustness against arbitrary perturbations or stationary energy confinement. Journal metadata checked on the publisher index and author's publication list; detailed text reviewed was the 2023 v2 preprint, not an audited final-version comparison.

### L16 — Null knots in nonlinear electrodynamics

E. Goulart (2016), *Nonlinear electrodynamics is skilled with knots*. EPL 115, 10004.
[DOI](https://doi.org/10.1209/0295-5075/115/10004); [accessible text/version](https://arxiv.org/abs/1602.05071v1).

Priority: S5 feasibility; S6 probe-response ideas.

Full-text targeted inspection: Eqs. (1)-(3), Bateman construction and null-field lemma leading to Eq. (11). Within the stated smooth, well-posed L(F,G) class, the null background can obey the same Maxwell equations. A different response to a probe does not show that the background acquires confinement or electric charge.

### L17 — Nonlinear extensions: scope and effective-action limits

Daniel F. W. Alves, Carlos Hoyos, Horatiu Nastase and Jacob Sonnenschein (2017), *Knotted solutions for linear and nonlinear theories: electromagnetism and fluid dynamics*. Physics Letters B 773, 412-416.
[DOI](https://doi.org/10.1016/j.physletb.2017.08.063); [accessible text/version](https://arxiv.org/abs/1705.06750v2).

Priority: S5 before selecting an extension.

Full-text targeted inspection: Section III, Eqs. (15)-(18). Null configurations can remain solutions of the invariant-based nonlinear theories discussed. Derivative terms are neglected under explicit scale assumptions; this is not a general proof for every nonlinear or quantum theory. Require an explicit calculation of which proposed terms change the selected background.

### L18 — Open-boundary numerical reference

Jean-Pierre Berenger (1994), *A perfectly matched layer for the absorption of electromagnetic waves*. Journal of Computational Physics 114(2), 185-200.
[DOI](https://doi.org/10.1006/jcph.1994.1159).

Priority: Before long-time isolated numerical experiments.

Publisher metadata and abstract-level material checked; full-text retrieval was unavailable in this review. Candidate reference for an independent absorbing-boundary implementation. It is not a drop-in PML design for our global periodic Fourier solver. Before implementation read the equations and demonstrate reflection, layer-thickness, initial-tail and energy-loss convergence.

### L19 — September 2026 helicity treatment

Gaetano Diglio and Renzo L. Ricca (2026), *Helicity conservation of the Riemann-Silberstein vector*. Royal Society Open Science 13(9), 260497.
[DOI](https://doi.org/10.1098/rsos.260497); [accessible text/version](https://pmc.ncbi.nlm.nih.gov/articles/PMC13561072/).

Priority: S3 diagnostic design; S4 helicity implementation.

Primary article full text inspected in PMC: Sections 3-6, gauge/boundary assumptions and conservation statements. Useful current reference for electric/magnetic helicity and covariant currents. Decay assumptions for unbounded domains cannot be silently replaced by a finite periodic box. Fix potential/sign conventions independently and handle mean modes explicitly. S3-D re-retrieval on 2026-10-31 was blocked by the public text endpoints; this historical review is not a fresh equation audit. The implementation uses accessible Irvine/Hoyos equations and independent controls instead.

## Recovered sources integrated for S4-B

The maintainer resumed bounded S4-B on 31 October 2026. [The source/equation map and impact dispositions](../models/B0-S4B-Offcore.md) identify what is implemented, retained as a limit, or deferred. The following recovered entries retain their actual review depths; abstract-only entries supply no implemented equations. L01–L19 remain the frozen recursion seeds.

### L20 — Field-line transport

William A. Newcomb (1958), *Motion of magnetic lines of force*. Annals of Physics 3(4), 347–385. [DOI](https://doi.org/10.1016/0003-4916(58)90024-1).

Role: transport/observer assumptions for topology tracking. Review: publisher abstract only; original full-text assessment pending. Stages: S3/S4. [Impact LR3-02](recovered-transfer/README.md).

### L21 — Helicity and corrected vortex arguments

H. K. Moffatt (1969), *The degree of knottedness of tangled vortex lines*. Journal of Fluid Mechanics 35(1), 117–129. [DOI](https://doi.org/10.1017/S0022112069000991). Read with [2017 corrigendum](https://doi.org/10.1017/jfm.2017.667), JFM 830, 821–822.

Role: winding/closure validation. Review: original targeted text/PDF pp. 118–121; correction full HTML. Full audit pending. Stage: S4. [Impact LR3-03](recovered-transfer/README.md).

### L22 — Relative helicity and boundaries

Mitchell A. Berger and George B. Field (1984), *The topological properties of magnetic helicity*. Journal of Fluid Mechanics 147, 133–148. [DOI](https://doi.org/10.1017/S0022112084002019).

Role: reference-field requirements for open subvolumes. Review: targeted text/PDF inspection; not a full audit. Stages: S3/S4 and boundaries. [Impact LR3-04](recovered-transfer/README.md).

### L23 — Conditional magnetic-energy minimisation

L. Woltjer (1958), *A theorem on force-free magnetic fields*. PNAS 44(6), 489–491. [DOI](https://doi.org/10.1073/pnas.44.6.489).

Role: boundary/model applicability checks. Review: three original scanned pages; targeted argument. Stages: interpretation/S5. [Impact LR3-05](recovered-transfer/README.md).

## Level-3 continuation: batch 2

[Assessments, precise locations and impacts](recovered-transfer/README.md). The larger review remains incomplete; S4-B resumes under ADR-0005 and level 4 remains deferred. The frozen seeds remain L01–L19.

### L24 — Initial conditions for null persistence

H. Kedia, D. Peralta-Salas and W. T. M. Irvine (2018), *When do knots in light stay knotted?* J. Phys. A 51, 025204. [DOI](https://doi.org/10.1088/1751-8121/aa9749).

Role: persistence/transport acceptance. Review: targeted journal text/PDF; theorem hypotheses retained. Online date: 2017. S3/S4.

### L25 — Normalised Hopf integral

J. H. C. Whitehead (1947), *An Expression of Hopf's Invariant as an Integral*. PNAS 33(5), 117–123. [DOI](https://doi.org/10.1073/pnas.33.5.117).

Role: map/normalisation discipline. Review: targeted primary text; equation transcription not audited. S3/S4.

### L26 — Scaling limitations

G. H. Derrick (1964), *Comments on Nonlinear Wave Equations as Models for Elementary Particles*. J. Math. Phys. 5, 1252–1254. [DOI](https://doi.org/10.1063/1.1704233).

Role: model-specific feasibility. Review: targeted proof/discussion and scan; no universal exclusion inferred. S5.

### L27 — Unit-vector knot solitons

L. Faddeev and A. J. Niemi (1997), *Stable knot-like structures in classical field theory*. Nature 387, 58–61. [DOI](https://doi.org/10.1038/387058a0).

Role: extension-energy comparison. Review: related 1996 preprint *Knots and Particles*, targeted text/PDF; final-version reconciliation pending. S5.

### L28 — Writhe and curve geometry

F. Brock Fuller (1971), *The Writhing Number of a Space Curve*. PNAS 68(4), 815–819. [DOI](https://doi.org/10.1073/pnas.68.4.815).

Role: optional geometry diagnostic. Review: original pp. 816–817 scans. S4; not a complete knot classifier.

### L29 — Constrained toroidal energy minima

A. Y. K. Chui and H. K. Moffatt (1992), *Minimum Energy Magnetic Fields with Toroidal Topology*. In *Topological Aspects of the Dynamics of Fluids and Plasmas*, 195–218. [DOI](https://doi.org/10.1007/978-94-017-3550-6_9).

Role: constraint-class comparison. Review: targeted chapter assumptions; no stability reproduction. S5.

### L30 — Quantum numbers in a specified microscopic model

Victor M. Yakovenko (1989), *Spin, Statistics and Charge of Solitons in (2+1)-Dimensional Theories*. Fizika 21, supplement 3, 231. [1997 author upload](https://arxiv.org/abs/cond-mat/9703195v1).

Role: conditional quantum comparison. Review: targeted HTML; dimensional/microscopic assumptions explicit. S7.

### L31 — Global gauge topology

H. C. Tze and Z. F. Ezawa (1976), *Global signatures of gauge invariance: Vortices and monopoles*. Phys. Rev. D 14, 1006. [DOI](https://doi.org/10.1103/PhysRevD.14.1006).

Role: possible later-model comparison. Review: publisher abstract only; full-text assessment pending. S5.


### L32 — Quantum spin/statistics of nonlinear topological configurations

D. Finkelstein and J. Rubinstein (1968), *Connection between Spin, Statistics, and Kinks*. J. Math. Phys. 9, 1762. [DOI](https://doi.org/10.1063/1.1664510).

Printed in L01 reference 50 and present in the index graph. Indexed-abstract review only; direct publisher retrieval was unavailable. Its conditional quantum treatment of nonlinear kink fields is relevant to a future configuration-space/quantisation analysis. It is not a claim that classical Maxwell circulation already yields fermionic electrons. Full assumptions and mathematical construction remain to be read.

Preserved from the recovered checkpoint; no additional reading was performed during consolidation. Historical labels are mapped in [the alias register](bibliography-aliases.json).


### L33 — Additional Bateman-pulse benchmarks

John Lekner (2025), *Bateman electromagnetic pulses*. Physica Scripta 100, 065533. [DOI](https://doi.org/10.1088/1402-4896/add221).

Reached through L19 reference 26. Indexed-abstract review only: pulse families, conserved observables, zero-momentum-frame treatment and linkage are potentially useful independent analytical comparisons. Obtain and map the equations before generating a new candidate or treating linkage as unique to a particular construction. No numerical reproduction is claimed.

Preserved from the recovered checkpoint; no additional reading was performed during consolidation. Historical labels are mapped in [the alias register](bibliography-aliases.json).


### L34 — RS-vector review and correction queue

I. Bialynicki-Birula and Z. Bialynicka-Birula (2013), *The role of the Riemann–Silberstein vector in classical and quantum theories of electromagnetism*. J. Phys. A 46, 053001. [DOI](https://doi.org/10.1088/1751-8113/46/5/053001); [arXiv](https://arxiv.org/abs/1211.2655).

Reached through L05/L15/L19; indexed abstract and bibliography review only. Useful convention/history and photon-wave-function reading, not a primary proof of an electron model. L19's bibliography explicitly lists a corrigendum, so both the review and correction must be inspected before importing formulas. The correction's content is not audited here.

Preserved from the recovered checkpoint; no additional reading was performed during consolidation. Historical labels are mapped in [the alias register](bibliography-aliases.json).



### L35 — Independent Fox-colouring polygon invariant

Altan B. Kılıç, Anne Nijsten, Ruud Pellikaan and Alberto Ravagnani (2025), *Knot theory and error-correcting codes*. Designs, Codes and Cryptography 93, 3029–3068. [DOI and publisher full text](https://doi.org/10.1007/s10623-025-01615-x).

Targeted publisher-text inspection for S4-B: Definition 2.6 (regular projections), Eq. (1), Definition 3.5 (Fox matrix), Proposition 3.7 (minor equivalence), Definition 3.10 (determinant). The implementation specialises to t=-1 and compares exact integer cofactors; it does not implement coding-theory claims or a complete knot classifier. This direct methods lookup is not recursion expansion.

## S4-C targeted equation inspections

The [model-feasibility audit](../models/S5-feasibility-audit.md) records targeted primary-source follow-up after the bounded return-map diagnosis. This does not complete the larger literature review or expand recursion seeds.

- **L16 / Goulart:** arXiv:1602.05071v1 Eqs.(1)–(3), the null-field lemma and Eq.(11) inspected directly. The constant-invariant substitution is used for feasibility, not a new NLED solver. Other sectors and causal assumptions remain separate.
- **L27 / Faddeev–Niemi:** hep-th/9610193v1 printed pp.2–3, Hamiltonian Eq.(2), virial Eq.(3), relaxation Eq.(4) inspected; the Hamiltonian page visually checked. Static scaling is distinguished from full stability and physical evolution. Final journal/preprint reconciliation remains pending.
- **L07 / Faber–Kobushkin:** hep-th/0207167v4 Section II Eqs.(11)–(20) inspected. Added internal fields, elementary-charge normalization and dimensional scale are explicit inputs. No spin/statistics or finite-size dynamical certification follows.

The manufactured torus control in S4-C is an explicitly differentiated geometric construction, not a new physical-model citation. [The return-map specification](../models/B0-S4C-ReturnMap.md) gives the derivation.
