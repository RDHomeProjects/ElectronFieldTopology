# Q3 observation controls and initial-field diagnostic decision

Recorded: 12 November 2026 Australia/Melbourne. Native receipt timestamps in status.json preserve UTC and Melbourne.

The completed workstation observation diagnostic 20261112t080754z-abc22089 replays 133 alternative fits and 10 matched comparisons from the unchanged source survey. Cadence and start-window changes do not move any recorded moving-case envelope across the original 1% speed gate. The fine z envelope is approximately 1.057319–1.057461%; the fine x envelope is 0.819694–0.820566%; the larger-domain z common T0.2 envelope is 0.965613–0.965939%. These envelopes are observation controls, not uncertainty intervals. Original decisions are preserved in observation-diagnostic.json.

The same-cadence coarse screen/detail slopes agree. Time-step refinement did not resolve the z deficit. This rules out the tested fit choices as sufficient explanations; it does not establish spatial/domain convergence or identify the remaining cause.

Next: evaluate the retained admitted float64 initial fields with the original CPU vector field, without taking physical time steps. Compare the initial directional rate of the recorded continuum-energy centroid with its later fitted velocity; separately report Hamiltonian-density centroid and momentum/energy ratios. Decompose the continuum centroid rate into integrated flux/energy, weighted local continuity residual and an exact discrete summation term. The last term mixes discretization/domain effects and is not a measurement of isolated boundary flux. Do not claim a Hamiltonian continuity identity from the continuum flux.

The accompanying field_diagnostic.py is a prepared diagnostic, not a completed production result. Its state-space derivative probes do not generate a physical trajectory. No optimizer, mesh change, tolerance change, GPU migration or new evolution is authorized by this record. Q1 stays parked; Q2 is the reference; Q4 admission and Q7 preparation remain unresolved. No charge, spin or SI electron validation follows.

The unchanged uploaded ZIP is observation-evidence.zip; REPORT.html is a directly selectable browser report. verify-publication.py checks its member seals and replays the scalar analysis against the native compact evidence. Full arrays remain in the existing verified workstation archive and are never added here.
