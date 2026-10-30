# Physics baseline and hypotheses

## Baseline B0

Classical vacuum electromagnetism on flat spacetime, SI reference conventions:

```text
div E = 0                         div B = 0
dB/dt = -curl E                   dE/dt = c^2 curl B
u = (epsilon_0 |E|^2 + |B|^2 / mu_0) / 2
S = E cross B / mu_0              g = S / c^2
U = integral u dV                 P = integral g dV
J = integral (r - r_origin) cross g dV
Q_flux = epsilon_0 closed_surface_integral E dot n dA
M^2 c^4 = U^2 - c^2 |P|^2
```

Here g denotes momentum density, not the electron magnetic g-factor. J depends on the chosen origin when P is nonzero. For an isolated system M is invariant mass; U/c^2 alone is rest mass only in its centre-of-momentum frame. Finite computational domains need flux accounting and truncation-error estimates.

Initial numerical work may use c = epsilon_0 = mu_0 = 1, with the conversion recorded explicitly. Later tensor formulations must declare metric signature and index conventions.

## Constraints that guide the search

- For smooth source-free E on ordinary space, Gauss's law gives Q_flux = 0 on every enclosing surface. A nonzero value in a baseline numerical run is an error to investigate, not emergent charge.
- Maxwell's equations already respect special relativity. Boosts transform fields, coordinates and simultaneity; boosting a snapshot without its time dependence is insufficient.
- Field-line topology, energy-flow topology, optical vortex topology and topology of physical space are different objects.
- A knot may retain its type while moving or expanding. This does not establish a particle confined at rest.
- In linear Maxwell theory, overlap does not introduce a nonlinear self-binding interaction between waves. Energy cross terms alone are not evidence of mutual scattering or a Coulomb force between independent wave packets.
- Equal energy-density maps can have different field directions and interactions. Signed charge cannot be reconstructed from positive scalar energy density alone.
- Classical J is not by itself proof of spin 1/2 or Fermi statistics.
- Scale choices calibrated to measured electron mass are inputs, not predictions.

These are baseline deductions, not a blanket impossibility result for every extended field theory.

## Hypothesis register

| ID | Question | Evidence needed | Present status |
|---|---|---|---|
| H01 | Can known linked Maxwell fields be reproduced? | Equation residuals, analytical comparison, convergence | Analytically reproduced in S1-A; independent evolution pending |
| H02 | Does topology persistence imply stationary energy confinement? | Localisation about fixed and moving centres, radiation flux | Not assumed; test separately |
| H03 | Can full field structure yield robust charge-like interactions? | Force law and external-field tests under explicit dynamics | Baseline net charge constrained to zero |
| H04 | Can a justified extension support finite-energy stable structures? | Equations/action, admissible data, perturbation and stability analysis | No extension selected |
| H05 | Can a candidate reproduce electron properties? | Independent classical and quantum predictions, comparison with experiment | Long-term, unestablished |

## Extension requirements

Before coding an extension, write a model specification identifying changed assumptions, fields, sources, action or evolution equations, constraints, conserved quantities, scale-setting mechanism, causal behaviour and testable predictions. Identify any singularities, internal boundaries or nontrivial spatial topology rather than hiding them in numerical boundary conditions.

Read L01 and L07 for proposed models, L02-L05 for knot methods and limitations, and L08 for an experimental benchmark in the [literature register](literature/README.md).
