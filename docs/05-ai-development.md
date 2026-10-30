# Development using AI and GitHub

## Responsibilities

AI assists with literature extraction, derivations, implementation, tests and documentation. GitHub preserves evidence and executes checks. The maintainer evaluates scope and scientific interpretation; specialised mathematical/physics review becomes necessary before strong model claims.

No AI agent, subscription or unattended coding workflow is activated by this documentation. A connected coding assistant can work through task branches; GitHub Actions provides deterministic validation independently of which assistant wrote the code.

## Task cycle

1. Read AGENTS.md and STATUS.md. Choose the earliest unfinished stage.
2. Open a focused research issue with requirement IDs, falsifiable question, source versions and compute budget.
3. Inspect the primary equations. Record exact equation/page mapping, conventions and any derivation in the model specification.
4. Define independent acceptance checks before implementation.
5. Implement the smallest reusable change on a branch. Keep numerical analysis separate from presentation.
6. Run local checks and submit a PR with commands, measured results, errors and limitations.
7. Run hosted CI. Review physical assumptions, sources and convergence independently of code style.
8. After authorised merge, update STATUS.md, requirements evidence and any decision record.

AI-authored tests derived from the same mistaken expression do not provide independent verification. Use a separately derived limit, published expression or independent implementation. Preserve a failing experiment as evidence instead of rewriting its hypothesis.

## GitHub Actions plan

S0: documentation integrity only, using the standard-library checker.

S1: pinned Python setup, locked dependencies, static checks and small analytical/numerical benchmarks.

S2: workflow_dispatch for bounded experiments and convergence studies. Validate input choices; impose timeouts, limited artifacts and concurrency. Summarise metrics and link exact provenance. No recurring job until explicitly requested.

Avoid bulk topology sweeps on every push. Larger runs use local commands first. Restrict any workstation runner to trusted reviewed code and keep tokens read-only unless a specific operation requires more.

## Task specification example

Implement an analytical Hopfion evaluator against a verified primary equation source; address SCI-001, SCI-004, SCI-005 and REP-001. Produce a model specification, source equation mapping, pointwise benchmark and convergence of sampled divergence/flux. Report only what was measured. Do not claim confinement or nonzero charge.

## Handoff

Every completed stage must leave a new assistant enough context to reproduce results from the repository alone. Keep one authoritative STATUS.md, a decision history, source limitations and the exact next task. Do not depend on private chat history.
