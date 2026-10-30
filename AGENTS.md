# Instructions for AI contributors

## Required reading

Read README.md, docs/STATUS.md, docs/02-physics-and-hypotheses.md, docs/03-requirements.md, docs/05-ai-development.md and the applicable literature entry before implementing a task.

## Scientific integrity

- Investigate the hypothesis; do not optimise the narrative toward proving it.
- Separate assumptions, derivations, numerical observations, interpretations and experimental evidence.
- Never describe an imposed charge, boundary, length scale or circulation path as an emergent prediction.
- Distinguish energy density from the complete field state, topological charge from electric charge, and classical angular momentum from quantum spin.
- Source-free Maxwell evolution on ordinary space cannot produce nonzero net electric flux from smooth zero-charge initial data. State precisely which assumptions any extension changes.
- Preserve null and negative results. A hypothesis failing is not a software test failure.
- Do not invent citations, equation numbers, data, simulation output or successful checks.
- Read the actual equation source before coding it. Bibliographic or abstract review is not equation verification.
- Record units, metric signature, field conventions, gauge and normalisation. Derive transformations consistently.
- Never weaken tolerances merely to obtain passing results; justify and record revisions against independent benchmarks.
- Do not infer persistent energy confinement from persistence of field-line knot type.
- No electron claim from a classical animation or fitted magnetic moment alone.

## Implementation

Use Python initially. Put reusable code in src/electron_field_topology, not only notebooks. Stage S1 must add pyproject.toml and a committed dependency lock before numeric work. Keep configurations separate from code and generated results. Use deterministic seeds and record provenance.

Work in a task branch and open a reviewable pull request for subsequent development. Include requirement IDs, source/version/equation mapping, exact commands, results, limitations and status changes. Human maintainers review scientific interpretation and changed physical assumptions. Do not merge your own PR unless the user has authorised it.

Use small hosted CI jobs; larger experiments are explicitly dispatched or run locally. Do not enable recurring compute, paid services, API keys or AI workflow execution merely because this file exists. Do not execute untrusted PR code on a workstation runner.

AI may draft code, derivations and reviews; an AI response is not a primary physics source. Cite actual papers and disclose AI assistance in research reports without assigning the AI human authorship.
