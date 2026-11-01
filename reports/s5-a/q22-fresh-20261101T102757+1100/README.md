# Checkpointed Q22 convergence study

Initialization: fresh_seed.

Generated: 2026-11-01T12:03:51+11:00 (Melbourne); 2026-11-01T01:03:51+00:00 (UTC).

partial_pending_scientific_review

| Stage | Execution | Solver | Energy | CPU residual |
|---|---|---|---:|---:|
| q1-control-fresh | stationary | gradient_stationary | 1.2359138695857361 | 0.0006385459766903154 |
| q2-control-fresh | stationary | gradient_stationary | 2.0118537450633793 | 0.0006731626733685903 |
| q22-129-fresh | stationary | gradient_stationary | 12.591379809579184 | 0.0008815516255655406 |
| q22-161-polish | stationary | gradient_stationary | 12.57500215425474 | 0.0009712463752229241 |
| q22-193-polish | stationary | gradient_stationary | 12.568066713575845 | 0.00081579101343235 |
| q22-domain-161 | stationary | gradient_stationary | 12.529561115671404 | 0.00048384406246025494 |
| q22-domain-193 | stationary | gradient_stationary | 12.511731396946402 | 0.0006703846779042784 |
| q22-domain-fine-193 | stationary | gradient_stationary | 12.524772086782672 | 0.0006181045034668618 |
| q22-comparison-129 | stationary | gradient_stationary | 12.51321284012085 | 0.0009056919734132301 |
| q22-comparison-161 | stationary | gradient_stationary | 12.501306202384423 | 0.0009110811887252954 |
| q22-comparison-193 | stationary | gradient_stationary | 12.494502479686533 | 0.0007712506736608309 |

| Comparison | Status |
|---|---|
| mesh_129_161 | pass |
| mesh_161_193 | pass |
| domain_129_161_h012 | pass |
| domain_129_193_h012 | pass |
| domain_161_193_h012 | pass |
| domain_161_193_h0096 | pass |
| same_mesh_comparator_129 | eligible |
| same_mesh_comparator_161 | eligible |
| same_mesh_comparator_193 | eligible |

Q22 static closure only; no reproduction automatically certified; Q18 retained unchanged

finite diagrams only; witness inputs/words need review; no deterministic move trace or continuum proof

Full field checkpoints remain on the workstation. Retain this output directory and its source campaign.
