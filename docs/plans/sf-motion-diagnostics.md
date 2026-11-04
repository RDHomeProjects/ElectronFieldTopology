# Full-field low-Q motion diagnosis and classical kinetic metrics

Prepared: UTC 2026-11-03T23:43:39.658706+00:00; Australia/Melbourne 2026-11-04T10:43:39.658706+11:00.

## Current result and next question

Merged PR52 at b9e2442755e49f1b03663b0ea1a4cb721a957d3e publishes the
[60-case assessment](../../reports/sf-motion/lowq-motion-2026-11-03T104629-568611+1100-30672/ASSESSMENT.md).
Six Q2 L20 rest/beta=.1 cases pass every declared case check. The global motion gate
remains open: 50 tail, 18 shape and four momentum failures overlap. Halving dt has
little effect on endpoint shape errors; spatial refinement reduces them by 20-32%.
The next task is read-only diagnosis of retained full fields before new production
refinements, Q17/Q19 free flight or a wider Q catalogue.

The run does not optimize or evolve any field. It reads float64 scientific checkpoints,
never renderer exports. The original action, K, grid, timestep, precision, thresholds
and reflecting boundaries remain unchanged. No overall wall-time cap is applied.

## Input authentication and local paths

The original evidence.zip must match SHA-256
`780cfff1d5be5fe9e61b238206aceb6a6f47a82350e8ce257c76cc79f56d8784`.
Its 389 listed members and exact source-file hashes are authenticated before computation.
The source dataset is chosen explicitly with --source. Embedded old absolute paths
are not followed; case/attempt paths are resolved below that chosen campaign.

Default inventory: six latest rest fields, 60 initial states and 60 final states.
Rest/final checkpoint file hashes are compared with published records. Initial files
have no independently published file hash, so their actual bytes enter the input
fingerprint; during analysis their metadata and arrays must reproduce the authenticated
rest snapshot and original boost bit-exactly. Final array-state hashes are also checked.
Missing/changed fields are listed by preflight, never reconstructed by a new solve.

The new diagnostic checkout/output is separate from the original campaign. Each
completed rest/case/pair audit is atomic and resumable. Resume requires identical
input hashes, configuration and diagnostic/numerical source. Stop requests finish
the current audit unit. Status gives unit counts and the log; it does not infer
success from an inactive PID. Complete means pending scientific review.

## Measurements and conventions

Model: SF-relativistic-neutral-v1; scheme D4-action-projected-RK4-v1; metric +---,
c=1 and model time/length units. K=(32 pi^2 sqrt(2))^-1. No SI electron scale or
electromagnetic coupling is introduced. See the [action](../models/SF-physical-time.md).

1. Recompute original endpoint shape, Hopf/cone, tail, radius and continuum energy
   from full fields, and replay scalar histories. Original failed checks are retained.
   Replay rtol=1e-9/atol=1e-11 compare two evaluations of the same diagnostic; these
   are not new physical acceptance tolerances and do not replace original limits.
2. Reconstruct initial boosts exactly, compare the translated reference at t=0, and
   measure tangent transport-rate/acceleration mismatches:

```math
v_{\rm tr}=P_n[-\beta D_a n],\qquad
r_a=P_n a_{\rm solver}-P_n[\beta^2D_aD_a n],\quad P_n=I-nn^T.
```

The acceleration comes from the unchanged nonlinear solver, including its Mdot term.
These are lattice transport identities; approximate equilibrium and interpolation
errors contribute. A normalized trilinear interpolant is piecewise smooth, with
derivative jumps at cell interfaces. We therefore do not assume it has a globally
smooth second event-time derivative or diagnose every residual as a solver defect.

3. Temporal endpoint fields are compared directly on their original full grids.
   Centroid fits use identical saved physical times, removing the earlier 11-versus-21
   sample-weighting discrepancy. This does not change any original fitted result.
4. All 70 original temporal/spatial/domain pairs are compared on the same central
   cube, with 33/49/65 diagnostic sampling nodes per axis. Its side is the smaller box
   side minus twice the original shell width. Raw componentwise linear interpolation
   is used without normalization. Both field and rate differences are retained, including
   absolute rates when their relative normalization is near zero. The sampling levels
   test the comparison quadrature/interpolant, not the original scientific grid.
   Central agreement does not establish convergence of exterior tails.
5. Per-face initial/final shell energies and instantaneous fluxes help localize domain
   effects. Face shells overlap at edges/corners. Flux samples use a rectangular sum
   on the closest shell-boundary grid plane; they are not an integrated radiation loss,
   a discrete Noether flux or proof of reflection. The two endpoints alone cannot
   establish the history of reflected radiation. Asymmetric padding remains a possible
   later controlled test, using common central data and matched h/dt/window.

## Classical kinetic metric: connection to the supplied papers

The [three-paper source assessment](../literature/soliton-quantization-methods.md)
is integrated into the main bibliography as L41-L43. Krusch/Speight Sections 4-5
motivate configuration-space topology and a kinetic metric; Cork/Halcrow Section
3.2 motivates measuring inertia and deformation rather than selecting by static
energy alone. Their Skyrme metric formula is not copied into the different SF theory.

For our declared action T=K integral v^T M v, and tangent field modes eta_A,

```math
T=\frac12G_{AB}\dot q_A\dot q_B,\qquad
G_{AB}=2K\int\eta_A^TM\eta_B\,d^3x.
```

The seven recorded modes are three translations, three spatial rotations and the
one internal rotation about the north axis allowed by the fixed boundary:
eta_Ti=-P_n D_i n; eta_Ri=-P_n[(e_i cross x) dot D n]; eta_phase=e_z cross n.
Modes vanish on the two fixed layers. Gram matrices, rotational diagonals and
eigenvalues are retained for all six rest states. Finite boxes/boundary projection
break ideal continuous rotation symmetry; dependent modes can yield small eigenvalues.
The raw basis is dimensional in model units, and eigenvalues are not quantum energies.
The matrix is not inverted and no angular momentum or electric charge is assigned.
An independent direct-Hamiltonian kinetic-energy test checks its factor of two.

## Decision after this run

Read SUMMARY.md, diagnostic.json, seeds/, cases/ and pairs/. Any endpoint replay
mismatch needs an integrity/instrument investigation before new physical claims.
If replay agrees, use the transport and common-field results to select a small third-h
study at beta=.3 with an x/z comparison, and a matched-h larger-domain Q1 test.
Do not automatically launch a replacement 60-case production matrix or weaken gates.
Three diagnostic sampling grids do not satisfy NUM-003's three physical resolutions.

Then, conditional on numerical control, assess Q17/Q19 motion. Preserve the later
Q18 fresh fine-start/conditioning and additional-Q tranche, including optional Q20/Q24.
In parallel, retain the charged-model feasibility questions in ADR-0008. The separate
spin-method tranche would reproduce Q1/Q2 symmetry/FR controls, then map suitable
closed configuration-space loops and deformations before a quantum spectrum.
Quantization assumptions, classical-emergence hypotheses, electromagnetic coupling
and Stern-Gerlach/detector outcomes remain distinct questions. None is accepted here.

Requirements: GOV-002, SCI-001/003/004, NUM-001/002/003, REL-001/002, BND-001,
REP-001/002; preparation supports future QNT-001 methods, not its acceptance.
AI-assisted implementation and analysis; independent scientific peer review not claimed.
