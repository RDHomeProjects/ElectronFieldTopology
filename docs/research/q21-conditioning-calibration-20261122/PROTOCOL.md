# Q21 localized residual audit and one-factor conditioning calibration

Registered 22 November2026. Every runtime timestamp includes UTC and Australia/Melbourne.

The source is the completed literature campaign20261122t010359z-34c3b904, specifically `arms/domain-pad-16/endpoint.npz`, SHA256 `aa42276416d5eccac218e2028dcc3bc66a2bc80bf46a5fcb59849b545c7971a4`. It is iteration425,129³,L30.72,h0.24. The retained step88 best state is not substituted. The corrected archive, original preserved archive, unchanged scientific hashes and live merged publication are checked on the zbook before allocation.

The preceding result fixed boundary admission: tail0.000262415 and guard0.000468216 pass. Force0.000620818 and maximum acceleration0.0174658 remain6.21 and17.47 times the original limits. This preparation is neither stationary nor a demonstrated stable physical object. The previous method, grid and domain comparisons are retained; no earlier chart is removed.

## Read-only diagnosis

Replay this exact parent and the passing Q2 reference; check the constrained directional derivative and independently compare CPU/CUDA energy and gradient. Locate force/acceleration peaks and quantify squared residual in disjoint outer-guard, former held-layer, core-neighborhood and remaining-interior regions. Record radial DST-I power and weighted discrete-Laplacian eigenvalues. Probe up to eight independent residual-oriented constrained-Hessian directions at perturbations0.001 and0.0005 after removing approximate translation/target-rotation modes. This finite subspace at a nonstationary field is not a global stability certificate. No optimizer or physical-time steps are charged by these read-only evaluations.

## One changed parameter

Vary the positive spectral shift λ in the Sobolev inverse `(λ + discrete Dirichlet Laplacian)⁻¹`. λ is a numerical metric parameter in inverse model-length squared, not a physical mass. The neutral D4 action, float64,129³ grid,L30.72 box,h0.24, initial alpha0.060446290980731544, native iteration counter425, Armijo search and all scientific gates remain unchanged. Every scan case clears the same three conjugacy arrays, then restarts from the same field. A separate λ0.25 exact-memory arm preserves those arrays for a40-attempt control; it is never treated as one of the restarted response samples. No automatic native200-iteration restart is reached before the maximum native counter545.

Seven initial values are λ0.03125,0.0625,0.125,0.25,0.5,1,2. Each receives at most30 charged attempts and measurements at every accepted update. Only30-accepted-update cases that retain representation and boundary admission are eligible for the cross-parameter fits. All early stops are explicitly listed and their actual observations retained. An interrupted uncommitted attempt remains charged; its branch may consequently lack a matched30-step response and is excluded, not silently topped up.

The response is the worse of median force/0.0001 and median maximum acceleration/0.001 over accepted updates21–30. Separate component medians, trajectory MAD, alpha, accepted displacement, objective calls, optimization-only time, energy, topology and tail/guard measurements are retained. The MAD measures temporal variation within a deterministic trajectory, not independent statistical uncertainty.

## Curves and adaptive measurements

Fit linear, quadratic and exponential response models against x=log₂λ. At least five eligible matched points are required. A model must have leave-one-out RMSE no greater than25% of measured response variation (with a trajectory-variation floor), and predictive skill at least0.10 versus the leave-one-out constant predictor. A near-flat total-energy fit cannot qualify a candidate. For optimum selection, the competitive model pool includes only validated fits whose RMSE is no greater than 1.5 times the best validated RMSE plus 2% of measured response variation; a substantially worse fit cannot veto an otherwise stable well-predicted turn.

Up to four additional30-attempt measurements concentrate near fitted turns, unresolved local best regions or a continuing boundary trend. Candidate points must be separated by at least 0.125 octave. An exploratory extension is at most0.5 octave beyond current measured coverage, within the absolute λ range0.015625–4. Such a measurement remains explicitly exploratory; extrapolation never grants readiness.

A fitted optimum requires either agreement of at least two validated model minima within 0.5 octave, or a validated upward quadratic whose leave-one-out turns remain within 0.5 octave. Force and acceleration models must independently qualify. Predicted joint score must improve at least5% over λ0.25 without either component worsening more than10%. The proposed value is bounded by current measured coverage plus0.5 octave and the absolute bounds. Polynomial sign changes are checked; nonpositive predicted residuals are rejected. Fitted curves are descriptive over their measured support, and a quadratic has a turn rather than an inflection point. The adaptive rule addresses observable turns and changes in slope without inventing a higher-order inflection.

If no qualified fitted optimum exists, an actually measured setting may still be confirmed if it demonstrates the same joint improvement. It is labelled `best_measured_value_without_validated_optimum`. If neither condition holds, longer relaxation is not allocated and the lack of a supported optimum is reported.

## Actual confirmation

Rerun the selected interpolated/extrapolated/measured value from the original parent for30 attempts. A new measured joint improvement or actual readiness is required before extension. Then continue the restarted λ0.25 baseline and selected candidate to at most120 attempts each. Baseline's first30 updates are reused; the new candidate is a separate restart. Compare longer endpoints as matched only if both actually reach120 accepted updates. Earlier scientific stops are reported separately. Repeating a deterministic run at the same setting is a replay/confirmation of this initialization; it is not an independent population sample or robustness demonstration.

At most580 newly charged attempts:40 exact +7×30 initial +4×30 adaptive +120 selected validation +90 baseline extension. This ceiling is not a requirement to consume the entire budget. Unused attempts do not reopen a completed campaign.

## Gates, execution and publication

Original gates: force≤0.0001; maximum acceleration≤0.001; absolute relative approximate-Hopf error≤5%; corner cone>0; unit error<1e-10; tail≤0.00075; guard≤0.001. The finite-grid Coulomb-gauge Hopf integral is not an exact topological certificate. A failed representation or boundary gate stops that arm; an actual all-readiness pass also stops it. All failed/deferred cases remain visible. No motion simulation, action change, other Q-value campaign, or change of box/spacing occurs here.

`auto` qualifies one backend for the whole campaign: CUDA float64 when available within the VRAM estimate, otherwise CPU. Failed CPU/CUDA parity is fatal and cannot trigger a quiet fallback. CPU diagnostics accompany CUDA optimizer updates. A backend transfer from the original CUDA parent is disclosed, and no bitwise-identical CPU/CUDA trajectory is claimed. Resume pins the selected device/backend. Each update is independently audited against the CPU D4 energy/gradient.

Run sequentially under the established systemd sleep inhibitor with MemoryHigh7GiB,MemoryMax8GiB,MemorySwapMax1GiB,four CPU threads; initial host reserves10GiB available RAM,1GiB free swap and56GiB disk, with6GiB host/40GiB disk runtime reserves. The old worker lock prevents concurrent writes to the source. Charges are durable before execution; two restart slots and retained best/latest fields support recovery. Existing source data remain unchanged.

Every compact member is captured into immutable bytes once and those exact bytes are both hashed and zipped. Telemetry is captured through a complete-line prefix, so a later supervisor append cannot recreate the previous seal race. Full fields stay local and are listed with hashes; they are not silently uploaded. Preparation and completed compact results use separate additive publication snapshots in `docs/research/q21-conditioning-calibration-20261122`. Git/gh operations run only on the workstation in a separate publication clone; the pinned numerical checkout is not switched or pulled.
