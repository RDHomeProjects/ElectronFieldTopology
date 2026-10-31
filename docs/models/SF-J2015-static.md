# SF-J2015 — static Skyrme–Faddeev reference

Authorised in the discussion after merged PR 34; [issue 35](https://github.com/RDHomeProjects/ElectronFieldTopology/issues/35). This is a new unit-vector static model, not a change to Maxwell B0 and not a physical-time solver. Euclidean spatial indices, dimensionless source normalization and fixed coefficients are used. There is no electromagnetic gauge field or electric-charge observable.

## Primary equation map

Paul Jennings, *Cabling in the Skyrme–Faddeev model*, J. Phys. A 48 (2015) 315401, [arXiv:1412.8597v2](https://arxiv.org/html/1412.8597v2), inspected Sections 2–4, Eqs. (2.1)–(2.7), (3.7)–(3.13), Table 1 and conclusion. Equation (2.1) is

```math
E=K\int\left(\sum_i|\partial_i n|^2+
\sum_{i<j}|\partial_i n\times\partial_j n|^2\right)d^3x,\qquad K=(32\pi^2\sqrt2)^{-1},\quad |n|=1.
```

The source's one-half ordered double sum equals the unordered pair sum here. No coefficient is adjusted during relaxation. The source boundary is n=(0,0,1) at infinity, approximated with two fixed north-pole layers on each box face. Grid spacing, finite box and numerical stationarity are distinct limits.

## Discrete cell functional and independent gradient

Use trilinear shape functions N_a on each Cartesian cell, v=sum_a N_a u_a, n=v/|v|, with unit nodal values u_a. Integrate the stated continuum density at 2x2x2 Gauss points. This changes numerical quadrature/interpolation, not the physical energy or its coefficients. The C implementation is optional acceleration of the explicitly declared lattice functional; independent NumPy interpolation/quadrature and constrained finite-variation checks verify it.

Our differentiation sets r=|v|, P=I-nn^T, c_i=n dot partial_i v and a_i=P partial_i v/r. If p_i=2a_i+2 sum_(j!=i)(|a_j|² a_i-(a_i dot a_j)a_j), then the derivative with respect to partial_i v is P p_i/r, and the derivative with respect to v is

```math
 g_v=-n\sum_i(p_i\cdot a_i)/r
 -\sum_i[c_iPp_i/r^2+(n\cdot p_i)a_i/r].
```

The nodal gradient sums N_a g_v + sum_i (partial_i N_a) Pp_i/r with the same cell/Gauss weights. For raw nodal variables w, u=w/|w|, apply (I-uu^T)/|w|. Boundary variables have zero gradient. L-BFGS iterations are optimisation steps, never physical time.

Every cell must have all corner vectors in the open hemisphere about their sum. The minimum corner dot product is a sufficient positive lower bound on the norm of any convex interpolant, so the cell field is defined everywhere, beyond just the quadrature points. Reject unresolved initial cells. Accepted optimisation steps change each nodal vector by less than min(.2, half the previous global hemisphere margin); this gives a nonsingular continuous interpolation path between accepted fields. It protects field-map continuity, not a particular core curve. A target preimage is free to reconnect or change knot type. Hopf quadrature is still independently monitored, without rounding it to the intended charge.

Development centred-derivative and forward-node functionals lowered energy through lattice-scale artefacts, even in Q=1. Their failed histories are retained and they are not the production reference. The forward implementation remains only as a documented negative numerical control. A projected Sobolev-CG option was also tested during diagnosis; full evidence declares the actual method. None of these minimisers is a physical-time solver.

## Initial fields and published targets

Source Eq. (2.4) maps a radial profile to Z1,Z0 in S3; Eq. (2.5) uses W=p/q. Evaluate the unit vector directly from homogeneous coordinates: n=(2 Re(p conjugate(q)),2 Im(p conjugate(q)),|q|²-|p|²)/(|p|²+|q|²), avoiding W's poles. Reject common zeros. We use a declared smooth cutoff profile, since the paper does not specify every profile, amplitude and checkpoint. This is a reproduction attempt with independent numerics, not a bitwise recreation.

Cable target: Table 1, Q=22, C(3,2)^(2,3), E=12.509. Equation (3.8), eta=.5, gamma=0, alpha=4,beta=1 gives Q=4 alpha+6 beta=22. Hyperbolic target: Table 1, Q=18, K(7,2) precursor relaxing to H4.851 (10_139), E=10.838. Equation (2.7), alpha=2,beta=2 gives Q=2 alpha+7 beta=18. These Q values describe Hopf topology, not electric charge. Same-Q alternate seeds permit meaningful energy comparisons; lower energy alone does not identify a knot.

Jennings used 301³ points, h=.06, fixed faces and damped second-order minimisation. Our optimising method and staged meshes differ; report those differences and do not claim paper-level convergence from a smaller lattice. The Q=18 published target is a local minimum, not the lowest energy found at that Q. Core changes are expected possibilities, not software failures.

## Independent validation and predeclared gates

Before target relaxation: zero energy for constant n; native versus independent NumPy energy/gradient agreement below 1e-11 relative; constrained directional derivative error below 2e-6; independent analytic Hopf field E2=s/sqrt(2), E4=1/(sqrt(2)s), at three scales. The last expressions follow by integrating independently derived densities 32s²/(r²+s²)² and 256s⁴/(r²+s²)⁴. Test spatial refinement and box/profile sensitivity separately. Source coefficients stay fixed.

Monitor numerical Hopf integral, unit norm, fixed faces, neighbour angle and energy histories. An accepted numerical reproduction requires: resolved initial charge within 5%; final charge within 5%; fine/coarse energy difference below 2%; independently measured scale/virial residual below 5%; stationary tangent-gradient RMS below 1e-3 in unweighted lattice units; energy within 3% of the source; and independently consistent extracted-core identification across resolutions/projections. Numerical knot identification is not a continuum isotopy theorem. An energy match without these gates is insufficient. Neither a stationary point nor an energy minimum proves causal dynamics or general stability.

Preimage diagnostics use face-consistent Kuhn tetrahedra, solving two linear component constraints on each face and requiring degree-two adjacency for every closed component. No manual joining or discarded small components. The primary target is (7e-6,11e-6,-1) normalized, fixed before target runs; a secondary near-south target tests sensitivity to the chosen preimage. This polygonal approximation is distinct from the energy's trilinear interpolant and needs mesh checks. Three regular projections produce oriented planar diagrams; SnapPy/Spherogram supplies Reidemeister simplification and numerical complement comparison to 10_139. A finite exact Kauffman state sum (maximum 18 simplified crossings) checks Jones polynomials, but polynomial equality alone does not uniquely identify a knot. Canonical Gauss-word equality after certified diagram moves can support a finite-diagram match; failure to match is inconclusive. Compare the cable to the independent Eq. (3.7) parameter curve (Z1,Z0)=(t^4,t^6+.5t^3) intersected with S3. The figure-eight complement and trefoil/unknot controls calibrate the diagram mapping. Software version, conventions and unresolved states are retained.

Targets use a reproducible amplitude-.005 smooth perturbation (seed 35, eight declared sinusoidal modes, radial envelope) to avoid silently enforcing seed symmetry. The initial W amplitude is a conditioning input, not a changed coupling. Conditioning records are retained; target energies are not fitted by adjusting model coefficients.

Full experiments run locally with explicit iteration/time caps, checkpoints and retained failure statuses. Hosted CI runs only the energy/gradient instrument and small controls. The bibliography, measured report and immutable configuration record actual evidence. AI assisted derivation, implementation and reporting; primary sources and independent controls remain essential.
