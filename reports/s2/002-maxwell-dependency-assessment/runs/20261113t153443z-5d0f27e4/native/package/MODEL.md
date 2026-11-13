# Bounded Maxwell dependency extension: equation and diagnostic contract

Code: Apache-2.0. Original explanatory prose and figures: CC BY 4.0. Prepared with AI assistance; neither the code nor its generated report is independent scientific peer review.

## Scope and sources

Requirements addressed as bounded controls: SCI-001/002/003/004/005, NUM-001/002/003, REP-001/002 and SW-001. This is an auxiliary Maxwell validation extension, not an SF dynamics campaign. It does not change the current repository's scientific acceptance gates or claim project-stage closure. Authoritative roadmap/publication changes follow review of the workstation results; this package leaves existing source, reports and navigation unchanged.

The existing checkout supplies the inspected analytical Hopfion evaluator and Fourier Maxwell propagator, checked against exact SHA-256 hashes. Its `docs/models/B0-H11.md` maps Valverde et al., arXiv:2003.01896v1, Eqs. (1)–(5), to the evaluator. Its `docs/models/B0-H11-PSATD.md` maps Godfrey, Vay and Haber, arXiv:1305.7375v2, Sec. 2, Eqs. (1)–(2), to the vacuum Fourier update and its sign convention. The extension uses these existing implementations without modifying them or silently projecting initial fields.

The submitted `maxwell_yee_alignment.py` supplies the unchanged `derivative`, `curl` and `points` functions, extracted into yee_primitives.py. Submitted script SHA-256: b1ad27cb811510a7dad139fad077187e09d0f290f74bba031f1ebbeb6bb3a328. This extension changes diagnostics and the bounded case driver, not those curl stencils. Source hashes and the actual checkout commit/dependency locks are recorded independently; a commit label is not substituted for a file hash.

Official Meep documentation was inspected for temporal synchronization and common-grid interpolation:

- https://meep.readthedocs.io/en/master/Synchronizing_the_Magnetic_and_Electric_Fields/
- https://meep.readthedocs.io/en/latest/Yee_Lattice/

No Meep installation or Meep solver is used. This is the project's NumPy Yee implementation compared against its Fourier reference.

## Equations and conventions

Vacuum Maxwell, c=epsilon0=mu0=1, Euclidean spatial vectors, real float64 fields. No potential/gauge or spacetime tensor is evolved. Coordinates, durations, fluxes and energies use model units, not SI electron quantities. Forward D+ is `(roll(f,-1)-f)/h`; backward D- is `(f-roll(f,+1))/h` along the chosen axis. Native E components are on cell edges; B components are on faces.

    B_(n+1/2) = B_(n-1/2) - dt curl_+ E_n
    E_(n+1)   = E_n + dt curl_- B_(n+1/2)

The prescribed analytical startup uses E at zero and B at -dt/2. Changing dt therefore also changes this algorithmic startup sample; the dt curve measures the complete retained prescription, not a separately proved asymptotic order of the time integrator alone.

At an observation time t=n*dt, form a temporary B_plus using the first update above, without committing another step. For driven Hopfion guard layers, impose their prescribed analytical value at t+dt/2 on that temporary array. Then

    B_sync(t) = [B_(n-1/2) + B_plus]/2.

The retained E/B_half arrays are not overwritten by observation. For common-grid energy and flux, linearly average each component along every coordinate in which its native offset is zero, giving cell-centre offset (.5,.5,.5). The primary error compares synchronized native component values to the exact field at the same component locations and common physical time. Common-grid error and Yee/Fourier differences are separate: they include the observation interpolation error.

Poynting density S=E cross B and physical energy density u=(|E|²+|B|²)/2 use synchronized, common-grid fields. Nodal trapezoidal cube energy and six signed outward face fluxes use the existing `cube_diagnostics`. The actual cube half extent is floor(2/h)*h, further restricted to remain interior, and is recorded. At fixed N and box this diagnostic region is fixed. Time-integrated flux is evaluated with the recorded samples and a nested coarser subset from the same trajectory, so quadrature sensitivity remains visible. Observation cadence is every four solver steps plus the endpoint; therefore raw flux differences across dt contain quadrature effects too. Primary field-error fits do not use this flux diagnostic as their response.

Periodic leapfrog has a separately derived native modified invariant:

    U_modified(n) = h³/2 sum[ |E_n|² + B_(n-1/2) dot B_(n+1/2) ].

It follows by summation by parts, curl_+ being the periodic adjoint of curl_-, and the two leapfrog updates. It is checked against an independently derived discrete travelling wave and recorded separately from synchronized physical energy. It is not a continuum confinement claim. Driven Hopfion boundaries do not receive a periodic full-box conservation assertion.

Native divergence uses D- on E and D+ on B. The packet is analytically transverse in continuum coordinates, but its initial finite-difference divergence need not vanish for oblique modes. Both its initial normalized residual and subsequent change are recorded. No hidden transverse projection makes that discrepancy disappear. Growth normalization uses L times the divergence L2 divided by the initial native field L2. Driven-field divergence is evaluated away from the forced layers and is not an outer-boundary admission certificate.

## Independent manufactured periodic packet

The packet is a deterministic finite superposition of eight transverse periodic modes, not an isolated Gaussian packet. For integer m vectors given in numerics.py, set k=(2*pi/L)*m. Choose a perpendicular unit vector a by a normalized cross product with a coordinate axis. Each contribution is

    E = amplitude*a*cos(k.x - |k|t + phase)
    B = amplitude*(khat cross a)*cos(k.x - |k|t + phase).

These expressions satisfy both vacuum curl equations and both continuum divergences by direct differentiation and k dot a=0. Qualification independently checks the PDE by central differences and the Fourier evolution against these exact finite-mode fields. Every default packet mode is resolved by the requested odd grids. Fourier initial data are sampled directly at the common cell centres, with projection disabled; no evolved exact field is supplied to either periodic propagator.

Continuous arbitrary rotations of this integer k set would generally break the box periodicity. Therefore packet rotation controls use proper cubic x90/y90 rotations only. They test axis-permutation consistency, not general isotropy. Continuous y-axis orientation sweeps apply to the driven analytical Hopfion, where the rotated exact field is evaluated as E_R(x,t)=R E(R^T x,t), B_R likewise. Phase, grid, box, boundary prescription and duration remain fixed in that sweep.

## Numerical qualification and empirical fit checks

Before local work, require: Fourier exact finite-mode relative L2 and relative energy drift below 1e-11; Fourier divergence max below 1e-10; native Yee discrete-wave, synchronization identity, modified-invariant and divergence-change errors below 1e-11; central-difference manufactured PDE residual below 1e-7; correct acquisition on known quadratic and cubic-inflection controls. All outcomes are retained. The completed packet cases separately check exact Fourier error, Fourier energy drift, modified Yee invariant and divergence preservation below 1e-10. Those are numerical-control tolerances, not newly relaxed physical or SF gates.

Empirical fit tolerances are separately predeclared in PLAN.json: new-point prediction residual 1e-6 in fractional L2, feature bracket 3% of the tested variable span, two successive qualifying adaptive rounds after at least two additions, at most nine additions for each Hopfion block (50% above the earlier allowance of six), at most six for each packet block, and fresh-validation maximum error 5e-6. Reaching the measurement budget is labelled budget_exhausted if those refinement conditions have not passed. These choices bound a diagnostic extension; they do not certify a universal approximation law. Variation below 1e-12 in the fractional response is treated as unresolved at the acquisition floor, preventing artificial extrema from rounding-scale variation.

Linear, quadratic, exponential and, once at least six development measurements exist, cubic fits compete using development leave-one-out residuals. A constant is allowed for an unresolved dependence. Coefficients use z=(x-origin)/scale and are stored with units. Adaptive acquisition balances interval width, possible slope reversals/concavity changes, residuals and disagreement between the leading two models. Choices are recorded before measurement. Fresh validation locations are excluded from acquisition, and the primary model is frozen before those measurements. Validation errors are not used to pick a replacement winning model. Any failure remains in the report; any later development round requires a new validation reservation.

No accuracy-budget crossing is active by default because no new operating objective has been declared. No optimum is selected automatically. Maxima/minima and inflections are distinct; any suspected inflection is a refinement target, not a certificate. Fits are limited to the tested configuration/range. Fixed 65³ and box side 8 do not establish spatial/domain convergence. Source-free classical Maxwell evolution supplies no emergent electric charge, quantum spin, particle stability or accepted electron model here.
