# Q3 initial-field assessment and controlled sampling study

The unchanged uploaded output initial-field-evidence.zip contains completed run 20261112t084359z-94c6b672: nine cases in approximately 10 minutes, ending 2026-11-12 08:54 UTC / 19:54 Australia/Melbourne. Initial scalar observables and checkpoint identities match source survey 20261109t134425z-89d28344. The full fields are retained only in the verified local/archive dataset. This audit rechecks compact evidence; it is not an independent full-field replay.

| Case | Initial vector speed error % | Historical fitted vector speed error % |
|---|---:|---:|
| Q2 reference | 0.845762 | 0.844998 |
| Q3 coarse z | 2.349075 | 2.347803 |
| Q3 medium z | 1.766353 | 1.770977 |
| Q3 fine z | 1.056717 | 1.057322 |
| Q3 fine x | 0.816608 | 0.819694 |
| Q3 larger-domain z | 0.967836 | 0.967217 |

The fine z axial rate is 0.2968298500701072, already below requested 0.3. Its continuum momentum/energy proxy is 0.29737646434861564 and weighted continuity residual contribution is -0.0005466142784930281; discrete summation contribution is approximately -1.54e-14. This is an algebraic decomposition, not a claimed exact discrete conservation law. The diagnostic agrees with independent directional density probes, with finest-probe RMS discrepancies below 1.70e-13 across the moving cases. Switching to the Hamiltonian-density centroid leaves fine z outside the original 1% gate (about 1.057861%). Three rest cases have zero instantaneous centroid rates; this alone does not demonstrate equilibrium or long-time stability.

The deficit therefore precedes accumulated physical-time evolution and historical fitting. The original observation controls are retained here as well, so this assessment can be installed whether or not the separate observation-only assessment was published. No prior record is overwritten. This evidence does not identify cubic reconstruction as the sole cause, isolate physical boundary leakage, or establish continuum convergence.

## Prepared next step

Hold the sealed q3-axial-fine-warm rest checkpoint (145 cubed, side 23.04) fixed. Reconstruct beta 0.3 on nominal lab node counts 97, 121, 145 in x and z. Use the same normalized cubic Hermite reconstruction and reflecting-box conventions; report all boundary and free-node projection corrections. Compare initial centroid derivatives, continuum flux/energy proxies, density choices and local continuity moments. Independently probe interpolant spatial and prescribed-time derivatives at deterministic interior off-node points. Check the D4 translation-rate relation as a sampling diagnostic, not as an exact lattice boost identity. The 145-node reconstruction must reproduce the existing admitted field/rate state seal.

Only lab sampling varies within each direction. The rest field itself is not refined or re-relaxed; no continuum convergence claim or Richardson order follows from this alone. No physical time step is taken. Results remain pending workstation execution. Source implementation is provided in src/electron_field_topology/sf_q3_initialization.py and sf_initial_centroid.py; the packaged standalone copies use the same code.

After review: distinguish padding the identical retained field from independently relaxing a larger-domain field, then consider short matched evolution with original gates. This package does not launch those later stages or repeat the survey. Q1 parked, Q2 reference, Q4 admission/preparation and Q7 preparation unresolved. Neutral SF model units, c=1; no SI electron, electric-charge or quantum-spin claim.

Open initial-field/REPORT.html for the completed diagnostic and REPORT.html for the earlier observation controls. Original timestamps and all pass/fail decisions are preserved.
