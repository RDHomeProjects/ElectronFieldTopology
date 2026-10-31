# S5-A — static reference and measured partial reproductions

The latest evidence is the [1 November workstation GPU continuation record](workstation-2026-11-01/README.md), including the unchanged uploaded archive, readable case records and scientific gate assessment. Q22 retains cable topology but needs finer-grid stationarity and domain checks. Q18 reaches a stationary three-component link, not the target hyperbolic knot. Neither target is accepted as a completed reproduction. [ADR-0007](../../docs/decisions/ADR-0007-tightened-milestones.md) narrows the follow-up to bounded Q22 closure and then a charged relativistic equation audit.

## Historical interrupted CPU tranche

The following sections preserve the 31 October interrupted run. Its then-current draft/unmerged status and missing files are historical; the newer workstation evidence above supersedes its current-status assessment. Read [the interruption record](interruption-2026-10-31.md), [model/source map](../../docs/models/SF-J2015-static.md) and [issue 35](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/35).

## Established evidence

Jennings's *Cabling in the Skyrme–Faddeev model* is integrated as L36, with Sutcliffe's low-charge references (L37) and Kauffman's bracket conventions (L38) in the main bibliography/BibTeX. SF-J2015-static is a separate unit-vector static model; Maxwell B0 is unchanged. Fixed coefficients, normalized trilinear cells, Gauss integration, an independently checked gradient and bounded minimisation are specified explicitly. No physical-time solver, electric-charge mechanism or electron model is claimed.

**136 local tests passed** before interruption. Independent NumPy/cell energy, constrained finite variations, analytic Hopf-field densities and three scale-integral checks passed. Q=1 and Q=2 controls reached the declared gradient residual at three meshes, with separate larger-box checks. The finest pair of mesh energies differs by about 0.10% for each charge; larger-box changes at fixed spacing are below 0.4%. These are bounded numerical controls, not general stability proofs.

All eleven implementation-head hosted workflows passed at `4c587c2184b9aec760cfe76e599c614f0493916a`. All four applicable workflows passed at the subsequent evidence head `8f11142075360d3217325846d108aff89e273930`. Later report-only commits require documentation checks; numerical source is unchanged.

## Complete case records preserved in GitHub

The table below is generated from retained complete result JSON, rather than reconstructed estimates. Signed Hopf values are kept; source Q labels refer to magnitudes under the declared Cartesian orientation.

| Case | Grid | Status | Final energy | Signed Hopf integral | Tangent-gradient RMS |
|---|---:|---|---:|---:|---:|
| [q1-65](cases/q1-65/result.json) | 65 | gradient_stationary | 1.2359139 | -0.985928 | 6.386e-4 |
| [q1-97](cases/q1-97/result.json) | 97 | gradient_stationary | 1.2330718 | -0.997034 | 4.253e-4 |
| [q1-129](cases/q1-129/result.json) | 129 | gradient_stationary | 1.2318521 | -0.999039 | 9.066e-4 |
| [q1-domain](cases/q1-domain/result.json) | 97 | gradient_stationary | 1.2318961 | -0.986196 | 8.976e-4 |
| [q2-65](cases/q2-65/result.json) | 65 | gradient_stationary | 2.0118537 | -1.982270 | 6.732e-4 |
| [q2-97](cases/q2-97/result.json) | 97 | gradient_stationary | 2.0069877 | -1.996282 | 4.169e-4 |
| [q2-129](cases/q2-129/result.json) | 129 | gradient_stationary | 2.0050617 | -1.998803 | 5.510e-4 |
| [q2-domain](cases/q2-domain/result.json) | 97 | gradient_stationary | 2.0098554 | -1.982294 | 8.258e-4 |
| [q18-97](cases/q18-97/result.json) | 97 | time_budget | 11.5872980 | -17.953909 | 6.471e-2 |
| [q22-97](cases/q22-97/result.json) | 97 | initial_charge_unresolved | 38.8637849 | -21.014832 | 2.316e+1 |
| [q22-129](cases/q22-129/result.json) | 129 | time_budget | 12.5933869 | -21.978634 | 2.605e-2 |

The Q=22 97³ rejection is a nonpositive cell-hemisphere margin, even though its numerical charge error alone falls within 5%. The generic stored status name must not be read as proof that only the charge check failed.

## Target interpretation

The Q=18 source precursor changed from one knotted preimage to three closed components at a saved intermediate observation, while its Hopf-integral magnitude stayed near 18. This is an allowed core-topology change, not a reproduction of the published hyperbolic knot. The first pass exhausted its time budget without stationarity.

The Q=22 129³ pass retained a single cable-compatible knotted preimage and approached the published energy 12.509, but exhausted its time budget without passing the declared stationary-gradient threshold. A later tool-reported diagram match goes beyond polynomial equality, but its complete witness file was not durably confirmed after interruption. Neither a close energy nor the solver stop flag is sufficient for acceptance.

[Additional observations](interruption-observations.json) retain rounded later results and development failures, explicitly distinguished from complete clean-run records. The latest observed Q=18 129³ energy was 11.5480886 with residual 0.041126; cable polishing reached 12.5929624 with residual 0.007025. Both exceed the 0.001 residual criterion. Complete later result files were not recovered into this PR, so these observations are not promoted to validated reproductions.

No completed 193³ or same-charge comparator result was confirmed after the environment failure. The independent case 193³ configurations and analysis/polishing scripts are preserved for continuation. None of the reproduction gates or energy coefficients has been weakened.

## Reproduction and limits

Use the [model specification](../../docs/models/SF-J2015-static.md), [fixed configurations](../../experiments/configs/sf-j2015), and the [recovery order](interruption-2026-10-31.md). GCC with OpenMP is required for the native static kernel. Install the locked environment with the optional topology instruments:

```bash
uv sync --frozen --all-groups --extra topology
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 uv run --frozen --extra topology pytest -q
```

Run each experiment into a new/empty output directory, in checkpoint dependency order. Do not overwrite recovered data. Original scalar histories use float64; saved field checkpoints use float32 and must be normalized on reload as the supplied scripts do. Hashes, config, compiler/dependency information and every retained status accompany the complete cases.

Jennings used 301³ nodes, h=.06, a larger box and a different minimisation scheme. Our radial cutoff, W amplitudes, smooth symmetry-breaking perturbation and smaller meshes are inputs, not inferred physical quantities. Exact source initial/final field files and all profile choices were not supplied in the inspected paper. Core identification, numerical stationarity, domain/refinement limits and energy ranking remain separate checks. A matching Jones polynomial is not a unique knot name.

Large checkpoint binaries were supplied separately for recovery; only the earlier simple-reference archive was confirmed saved. This report does not claim that all later field files survived. At that interruption the solver was CPU-only; the newer workstation record documents the subsequently implemented GPU backend and measured device checks.

Level 4 remains deferred. AI assisted source auditing, derivation, implementation and reporting. Primary sources and independent controls do not amount to expert certification of this project's interpretation.
