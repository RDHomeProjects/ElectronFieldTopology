# Contributing

Start with [the AI workflow](docs/05-ai-development.md), [requirements](docs/03-requirements.md) and [status](docs/STATUS.md).

Open a focused issue using the research-task template. State a falsifiable question, applicable requirements, sources, deliverables, acceptance criteria and compute budget. Label conjectures as conjectures.

Implement on a branch. Include independent benchmarks and numerical error estimates for physics changes. For documentation, run:

```bash
python3 scripts/check_docs.py
```

Do not include unlicensed paper copies, credentials, bulk simulation arrays or generated animations in ordinary source commits. Use linked, versioned artifacts with checksums for substantial outputs. Cite any adapted equations or algorithms and retain third-party notices.

Pull requests must explain what is assumed and what is derived. Reviewers should evaluate correctness separately from whether the result supports the hypothesis. Record rejected candidates and inconclusive experiments.

Contributions are submitted under the applicable repository licence: Apache-2.0 for software and CC-BY-4.0 for original explanatory prose and figures. Only submit material you have the right to contribute.

## Recording work

Use [the layout policy](docs/governance/repository-layout.md) and [study plans](docs/plans/README.md). Update the project register and render generated navigation when recording preparation, a run, assessment or priority change. Preserve failed gates and old evidence; corrections are new dated assessments. Run `python3 scripts/project_records.py check` and the documentation checker for administrative changes.
