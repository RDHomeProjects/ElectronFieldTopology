# Scientific assessment — fresh Q22 convergence study

Recorded: **2026-11-01T12:35:36+11:00 (Australia/Melbourne)**; **2026-11-01T01:35:36+00:00 (UTC)**.

Evidence: [merged PR 47](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/47), merge `31732a6b5c1558927fe47ae7fc7f6d81a4b30d2c`; workstation source `90181ce13722ef74dfb606b6eb2b848166b958d7`. Requirements: GOV-002, SCI-003, NUM-003, REP-001/002. Model: [SF-J2015-static](../../../docs/models/SF-J2015-static.md). Scope follows [ADR-0007](../../../docs/decisions/ADR-0007-tightened-milestones.md).

## Assessment and recommended disposition

**The bounded Q22 static numerical benchmark is supported at its declared finite-grid and finite-diagram evidence level.** The previously missing finer-grid stationarity, matched-spacing domain comparisons and stationary same-charge comparator are now present and pass the declared scalar gates. The retained cable witnesses have been checked beyond the summary flags. This supports closing the narrowed Q22 numerical milestone and proceeding to the charged relativistic equation audit.

This is a qualified scientific assessment, not an automatic change to the measured summary or a formal continuum knot/stability certificate. The generated `partial_pending_scientific_review` summary remains unchanged. Q18 remains a linked alternative and an unsuccessful hyperbolic-basin reproduction. S5-A as a whole is not a completed cable-and-hyperbolic reproduction programme, and no electron model has been established.

## Evidence checked

- The original archive is 1,627,128 bytes, SHA-256 `fe4f75db8d1823242e5448ee414d7f83d6e1301007f2f604f8e240a3c6eaa4c5`, Git blob `790d3104850b5b6d32d97672dbcfe398a99fab92`. All **217 hashed members**, 218 unique archive entries, readable copies and duplicate root scalar records match.
- All **70 campaign source/configuration/lock hashes** agree with the retained implementation. All 18 pass manifests record clean source `90181ce…`, unchanged source during execution, actual CUDA float64 execution, successful device controls and independent initial/final CPU endpoint audits: **36 audited endpoints** in total.
- All saved result/configuration/history pairs and checkpoint-digest dependency chains agree. Recorded energy histories are monotone within roundoff; restart energies agree. No full 3-D field arrays are in the published archive, so energy, field gradients and the field Hopf integrals were **not recomputed from fields in this review**. Their validation is the independently recorded workstation CPU/GPU audit, tied to the preserved field hashes.
- All **33 analysis jobs** record successful execution. The review independently recomputed energy-component/virial identities, the final scalar gates, mesh/domain differences, same-grid energy gaps, stored signed Gauss words and polygon-link cross-checks.
- Seven intermediate passes remain visible: **six `residual_not_stationary` and one `iteration_budget`**, followed by eleven stationary endpoints. No failed intermediate result was relabelled as stationary.

The measured execution interval was **10:27:58–12:03:51 Melbourne time on 1 November 2026**, or **1 h 35 min 53 s** to the final summary. There was no overall wall-time cap. All 18 passes used preconditioning length 0.5; the alternative lengths were available but not invoked.

## Final measured endpoints

Energy uses the dimensionless published normalization; residual is the independently recomputed CPU tangent-gradient RMS. Half-width is `(n−1)h/2`. Signed Hopf values retain the implementation orientation; their magnitudes are compared with the intended topology label, without rounding them to integers.

| Stage | Grid | h | Half-width | Energy | CPU residual | Signed Hopf | Virial |
|---|---:|---:|---:|---:|---:|---:|---:|
| q1-control-fresh | 65³ | 0.240 | 7.680 | 1.235913870 | 0.000638546 | -0.9859280 | 0.5407% |
| q2-control-fresh | 65³ | 0.240 | 7.680 | 2.011853745 | 0.000673163 | -1.9822697 | 0.3729% |
| q22-129-fresh | 129³ | 0.120 | 7.680 | 12.591379810 | 0.000881552 | -21.9787461 | 3.3239% |
| q22-161-polish | 161³ | 0.096 | 7.680 | 12.575002154 | 0.000971246 | -21.9910309 | 3.1374% |
| q22-193-polish | 193³ | 0.080 | 7.680 | 12.568066714 | 0.000815791 | -21.9956095 | 3.1647% |
| q22-domain-161 | 161³ | 0.120 | 9.600 | 12.529561116 | 0.000483844 | -21.9807300 | 0.7138% |
| q22-domain-193 | 193³ | 0.120 | 11.520 | 12.511731397 | 0.000670385 | -21.9809879 | 0.1538% |
| q22-domain-fine-193 | 193³ | 0.096 | 9.216 | 12.524772087 | 0.000618105 | -21.9917285 | 1.0056% |
| q22-comparison-129 | 129³ | 0.120 | 7.680 | 12.513212840 | 0.000905692 | -21.9775733 | 2.5870% |
| q22-comparison-161 | 161³ | 0.096 | 7.680 | 12.501306202 | 0.000911081 | -21.9905544 | 2.6612% |
| q22-comparison-193 | 193³ | 0.080 | 7.680 | 12.494502480 | 0.000771251 | -21.9953779 | 2.6820% |

## Acceptance ledger

| Gate | Reviewed result | Disposition |
|---|---|---|
| Initial/final Hopf resolution | All endpoints satisfy the original 5% bound; numerical signed values remain reported | Pass within the stated diagnostic |
| Resolved cells and unit norm | Smallest final corner-cone margin 0.856449; largest final unit error 2.22e-16 | Pass on workstation records |
| Stationarity | All eleven final CPU residuals below 1e-3; largest 0.000971246 at cable 161³ | Pass |
| CPU/GPU endpoint agreement | All 36 initial/final audits and device validations pass; source/field-digest lineage checked | Pass on retained audits |
| Mesh energy | 129³→161³: 0.130070%; 161³→193³: 0.055153%, at half-width 7.68 | Pass, below 2% |
| Domain energy | All four matched-spacing comparisons pass; largest shift 0.632563% | Pass, below 2% |
| Virial and independent dilation | Largest final virial 3.323921%; largest dilation derivative 4.148269%; largest dilation identity defect 0.853403% | Pass, below 5% |
| Published cable energy | All six cable/domain endpoints within 3%; fine fixed-box result +0.472194% | Pass within source-comparison scope |
| Cable core evidence | Two single-component preimages per endpoint; 108 projection checks; 12 verified stored witnesses | Supported with finite-diagram limits |
| Same-charge competitor | Three audited stationary, same-grid comparisons; all lower than the cable branch | Eligible and lower energy; no global-minimum claim |
| Q18 hyperbolic target | Not rerun; previous stationary linked alternative remains distinct from target | Unresolved reproduction, unchanged |
| Continuum isotopy, Hessian/physical-time stability, electric charge and electron properties | Not established by this dataset | Outside accepted benchmark scope |

For Q1/Q2 the controller reports source-energy success by default because those seed configurations contain no `published_energy` field. The audit records this as **not configured**, rather than an independent source-energy test. Direct comparison with the already registered Sutcliffe values 1.204 and 1.967 gives +2.650654% and +2.280312%, respectively. Those are rounded numerical reference values with known discretisation error, not exact energies.

## What the domain study adds

At fixed spacing h=0.12, increasing half-width from 7.68 to 9.60 lowers cable energy by **0.490960%**; increasing to 11.52 changes it by **0.632563%** relative to the small box. The final 9.60→11.52 increment is **0.142301%**. At h=0.096, half-width 7.68→9.216 changes energy by **0.399444%**. These checks address domain size without confusing it with a spacing change.

Boundary sensitivity is measurable, even though it lies inside the original 2% criterion. In the h=0.12 family the virial residual falls from **3.323921% to 0.153805%** with the larger box, consistent with a reduced boundary restriction. This is an interpretation of the measured family, not an extrapolated error bound.

The largest-box energy 12.511731 is only **0.021835%** above the published cable value 12.509; the finer-spacing enlarged box gives 12.524772, or **0.126086%** above it. Do not present the smaller discrepancy as 0.02% continuum accuracy. Our discretisation, mesh and finite boxes differ from the paper, and finite-spacing/domain effects have not been extrapolated jointly to their limits.

## Cable topology and its remaining limits

The six cable/domain endpoints each have one closed component in each of the two declared preimages. Every target has nine stored diagrams: three polygon sampling resolutions and three projections. All 108 diagrams are single-component and have the reference Jones polynomial.

For all **12 common-diagram witnesses**, this review checked that the stored input diagram belongs to the recorded analytical-reference or extracted-candidate diagram at the declared sampling/view. It rebuilt the two output links and independently recomputed their signed canonical Gauss words; both outputs equal the stored common word.

This is stronger than polynomial equality alone. It still does **not** supply an explicit certified Reidemeister move trace from each input to output. The earlier limitation concerning random-seed replay remains: a saved seed is not a deterministic certificate with this simplification implementation. The preimage polygons also approximate the continuous field, using a tetrahedral diagnostic distinct from the energy interpolant. Consistency across the retained grids, targets and projections supports the declared numerical identification; it does not prove continuum isotopy.

## The comparator is a resolved linked alternative

The summary labels comparator topology `unresolved` because its convenience check expects one cable component and a cable witness. The underlying extraction is **not unresolved adjacency**: both preimages at all three comparator grids record `closed_components` with **three components**.

Each retained endpoint has two components whose nine diagrams simplify to zero crossings, and one component with nine three-crossing, trefoil-compatible diagrams. Pairwise projected linking is consistent across 256/384 segments and three views. The absolute linking numbers are **1, 2, 2**. Signs vary with the independent curve orientations and are preserved in the machine ledger.

This review additionally computed **36 independent polygon Gauss integrals**, at 256 and 384 segments for every component pair, target and grid. Their largest discrepancy from the corresponding signed projection count is **0.00021455**. These are finite-polygon cross-checks, not a recomputation of the full field Hopf integral.

The result should therefore be described as a **three-component link, with one trefoil-compatible component and two unknots**. It was K(5,4)-seeded, but its final state must not be called a retained K(5,4) knot. No fully framed-link identification or individual component Hopf-charge assignment is inferred from component polynomials and pairwise links alone.

| Same grid and box | Cable energy | Linked-comparator energy | Comparator lower by |
|---|---:|---:|---:|
| 129³; half-width 7.68 | 12.591379810 | 12.513212840 | 0.620797% |
| 161³; half-width 7.68 | 12.575002154 | 12.501306202 | 0.586051% |
| 193³; half-width 7.68 | 12.568066714 | 12.494502480 | 0.585327% |

The 193³ gap is **0.073564234 dimensionless energy units**, or **0.585327%** of cable energy. It is a valid comparison between same-charge, same-discretisation, same-spacing and same-box stationary endpoints. It shows that this cable endpoint is not the lowest-energy configuration among the tested states on that lattice. Neither stationarity nor a lower observed energy establishes a global minimum or a positive Hessian.

Cross-box comparisons must stay separate: comparing the largest-box cable with the smaller-box comparator does not provide a controlled ranking. Comparator domain studies were not part of this study; no domain-independent ordering is claimed.

## Relation to the published reference

Jennings Table 1 lists the Q22 cable at **12.509**, a lower linked state at **12.446**, and a K(5,4) state at **12.455**. Its numerical grid was 301³ at h=0.06. The measured lower linked alternative is qualitatively consistent with the reference landscape. Our fine comparator is **0.389703%** above the quoted linked-state energy, but this is contextual agreement, not a certified match to its full framed link. The controller’s comparator energy gate still references its original K(5,4) seed target, so that flag alone does not identify the final state. The source references are already L36/L37; no new bibliography entry is needed.

## Implication for the Matter Waves objective

This completes a useful controlled static benchmark: the implemented nonlinear functional supports a stationary, cable-compatible branch at the declared numerical resolution, while relaxation can produce a lower-energy linked branch at the same Hopf label. It validates a numerical binding/topology reference for comparing proposed mechanisms.

The unit-vector field, its fixed energy terms, the seed Hopf label, dimensionless scales and boundary conditions are supplied model inputs. They have not emerged from source-free Maxwell evolution or predicted electron measurements. Optimisation iterations are not physical time. This dataset establishes neither electric charge, Lorentz-covariant dynamics, radiative/perturbative stability, spin one-half, statistics nor interaction laws.

## Recommended next step

Record the Q22 bounded milestone as **supported with stated numerical/diagram limits**, retain all raw summaries and intermediate failures, and keep Q18 explicitly incomplete. Further unguided Q22 polishing or a wider Q catalogue is not needed to close the declared scalar gates.

Proceed to the equation-level feasibility audit specified by ADR-0007 before another simulator: changed assumptions; complete fields/action and conventions; an electric-flux/charge map; finite energy and scale accounting; causal/characteristic and stability conditions; supplied parameters versus independent predictions; and a falsifiable interaction experiment. Faber–Kobushkin remains a candidate for that audit, not an accepted numerical theory. A formal knot certificate can be a separate task if a later claim requires it.

## Reproduce this assessment

From the repository root:

```bash
uv sync --frozen --all-groups --extra topology --python 3.12.14
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 \
  uv run --frozen --extra topology --python 3.12.14 \
  python scripts/assess_q22_fresh_results.py --topology \
  --output artifacts/q22-assessment-check.json
python3 scripts/check_pr36_staged_recovery.py
python3 scripts/check_workstation_evidence.py
python3 scripts/check_docs.py
```

Validation of the review: the record/curve audit passed, **41 relevant topology/controller tests passed**, and an intentionally altered archive was rejected by the integrity check. Documentation, original 191-file recovery verification and the older workstation evidence checks also passed.

The dated [machine verification ledger](assessment-verification-20261101.json) records the original review and the additional polygon calculations. The command above writes a new timestamped verification to ignored artifacts and does not modify the retained numerical evidence or launch a GPU solve. Preserve the full workstation field directory given in the original summary and back it up before subsequent experiments.

## Sources and authorship

- [Published run summary](SUMMARY.md), [machine summary](summary.json), [campaign](campaign.json), [frozen runtime plan](plan.json), [archive](evidence.zip), and [archive member manifest](records/evidence-hashes.json).
- Jennings, *Cabling in the Skyrme–Faddeev model*, [arXiv:1412.8597v2](https://arxiv.org/html/1412.8597v2), Section 4/Table 1 and the already recorded model/source map (L36).
- Sutcliffe, *Knots in the Skyrme–Faddeev model*, [arXiv:0705.1468v1](https://arxiv.org/html/0705.1468v1), Section 2 and low-charge energy table (L37).

AI assisted this assessment, verification code and reporting. New calculations in this review are limited to retained-record checks and finite-polygon diagnostics. No new full-field minimisation, physical-time simulation or literature-review expansion was performed.
