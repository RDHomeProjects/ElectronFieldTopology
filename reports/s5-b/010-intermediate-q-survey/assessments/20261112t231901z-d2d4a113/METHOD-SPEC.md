# Independent D2 initial SF action and observable contract

Requirements NUM-001/002/003, REL-002, SCI-003/004 and REP-001/002. Conventions unchanged: neutral SF unit-vector n, tangent v, metric +---, c=1 model units, K=(32 pi^2 sqrt(2))^-1. Primary continuum equation map remains docs/models/SF-relativistic.md and SF-physical-time.md. This is a locally derived discretization; no new equation is attributed to a paper.

Let D_i be the skew centered second-order derivative with periodic or constant-zero exterior acting on u=n-north. Set d_i=D_i u. Define the positive nearest-edge sigma density by the half-sum of forward/backward squared differences; E2 is its nodal volume sum. Define E4=sum(i<j)|d_i cross d_j|^2 and M=I+sum_i(|d_i|^2 I-d_i d_i^T). The D2 action is

```math
L_h=K\sum_x\left[v^TMv-E_{2,h}(x)-\sum_{i<j}|d_i\times d_j|^2\right]\Delta V.
```

Varying this action gives

```math
M a=\Delta_2 u+\sum_iD_i C_i-\dot Mv+\lambda n,
\quad C_i=\sum_{j\ne i}(|d_j|^2d_i-(d_i\cdot d_j)d_j)-|v|^2d_i+(v\cdot d_i)v.
```

Solve for lambda so n.a=-v.v. Mdot is the exact directional derivative of M with d_i dot =D_i v. Fixed faces hold the same two physical node layers as D4 at a matched geometry. The code does not call the D4 force or current implementation. The positive edge sigma action avoids the alternating-mode zero of a pure centered-derivative squared sigma action. Native discrete H is K(v.Mv+E2+E4), distinct from the D2 continuum-density diagnostic. D2 is not asserted superior to D4; lower-order error must be compared under refinement.

Qualification: centered-sine derivative refinement; independently finite-differenced Lagrangian directional variation against M a+Mdot v on tangent variations; native instantaneous H balance; sphere-acceleration constraint; density directional probes; shared observer versus prior D4 diagnostic. Both periodic and fixed manufactured fields are used. These test implementation consistency and small analytic controls, not global stability or physical causal well-posedness.

The common observer uses the existing D4 density/flux definition for both accelerations and a separately qualified algebraic directional moment calculation. D2-native H should have zero instantaneous rate within numerical guard; the common D4 H generally need not be conserved by D2. Physical-volume residual L2 is reported instead of interpreting vacuum-diluted RMS as improved accuracy. No RK4/leapfrog/Verlet method is introduced for D2 in this handover; its velocity-dependent constrained dynamics requires a separate integrator qualification before evolution.
