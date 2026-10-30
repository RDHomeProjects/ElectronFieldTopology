# Project status

Updated: 2026-10-31 (Australia/Melbourne).

## Current stage

S0 documentation foundation. Repository structure, requirements, staged plan, AI instructions, literature register, templates and documentation checker are supplied.

No simulator, numerical environment, field configuration implementation, topology search or scientific result exists yet. Future capabilities in the roadmap are planned, not implemented.

## Evidence

- Run python3 scripts/check_docs.py for local documentation integrity.
- GitHub Actions workflow: .github/workflows/docs.yml.
- Hosted execution status is available in the repository Actions tab; a local pass does not establish a hosted pass.
- Primary literature links and review-depth notes: docs/literature/README.md.

## Next task

S1-A: implement and independently verify one published analytical Hopfion, following docs/06-development-plan.md. First complete its equation-to-code mapping and Python dependency lock.

## Open decisions

- Exact Hopfion equation source/version and normalisation: S1.
- Numerical evolution method and boundary treatment: S2.
- Topology invariants and candidate families: S3-S4.
- Whether any extended dynamics is justified: S5.
- Long-term artifact archive and release citation: before research publication.

## Handoff prompt

Read AGENTS.md, this status, requirements, development plan and literature register. Continue the earliest incomplete stage. Implement S1-A in a reviewable pull request with primary equation mapping, independent verification and run provenance. Preserve negative results; make no claim that a Maxwell knot is an electron.
