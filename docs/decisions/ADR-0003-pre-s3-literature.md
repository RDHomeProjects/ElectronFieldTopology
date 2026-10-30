# ADR-0003: incorporate the pre-S3 literature review

Date: 2026-10-31. Status: proposed for review with the documentation PR.

## Context

S2 is merged. The requested literature assessment found useful covariant, centroid, topology and nonlinear-theory references, including 2025/2026 publications. See [the review](../literature/pre-s3-review.md) and L11-L19 in [the register](../literature/README.md).

## Recommendation

Split S3 into analytic event-consistent Lorentz tests (A), energy-centroid/localisation diagnostics (B) and classified perturbation studies (C). Helicity/topology instrumentation is a separate D/S4 task; it should not block A.

Use energy-based and explicitly bounded diagnostics. A global Maxwell perturbation norm can be conserved without self-binding. Helicity conservation is not complete topology evidence. Any nonlinear extension must first identify which proposed terms actually change the null background.

## Consequences

New acceptance requirements are planned, not already passed. S1/S2 numerical results remain unchanged. The existing periodic solver remains a short-time reference; no absorbing boundary or new physical theory is approved by this review. No S3 numerical code is introduced.

The next implementation task is S3-A with a source/version/convention mapping and independent controls. Maintainers review the refined scope with this documentation change.
