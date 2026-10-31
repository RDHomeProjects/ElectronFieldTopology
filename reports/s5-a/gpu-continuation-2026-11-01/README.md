# GPU continuation preparation — 1 November 2026

The user authorised integrating the GPU backend into checkpointed relaxation
and continuing the analysis interrupted on 31 October. Work belongs to issue 35
and draft PR 36; requirements NUM-001/003, SCI-003/004, TOP-001, REP-001/002,
SW-001. Sources and coefficients remain those of
[SF-J2015](../../../docs/models/SF-J2015-static.md), Jennings L36–L38.
AI assisted implementation, tests and reporting.

## Workstation evidence supplied by the user

These are terminal observations supplied in the conversation, **not raw JSON
artifacts independently downloaded in this execution environment**. Both runs
printed successful independent CUDA numerical checks; the harness only prints
ratios after its per-workload parity checks succeed. CPU reference used twelve
threads; CUDA used float64, three ten-step repetitions, RTX 2080 Super Max-Q.

| Case | CPU solve s/step | GPU solve s/step | CPU/GPU ratio | CPU diagnostics s | GPU diagnostics s |
|---|---:|---:|---:|---:|---:|
| Q22 129³ | 1.282994 | 0.287333 | 4.465186 | 1.832294 | 0.074822 |
| Q18 97³ | 0.600113 | 0.133655 | 4.490018 | 1.002467 | 0.033924 |

The workstation paths were `artifacts/gpu-q22-20261101-000947/timing.json` and
`artifacts/gpu-q18-20261101-001208/timing.json`. These support short-run performance
and device-parity observations, not long-run convergence or reproduction.

## Recovery audit

Library ZIP metadata lists `/Matter Waves/S5A-field-checkpoints.zip` at
39,275,371 bytes, matching the earlier confirmed simple-reference archive size.
The 82,223,333-byte target replacement was not recovered here. No claim is made
that target fields or a cable diagram witness survived. The existing recovery
record therefore still justifies regenerating the specified Q18/Q22 precursors.
Local workstation benchmark output directories are not full relaxation fields.

## Implementation and remaining execution

[The continuation guide](../../../docs/static-gpu-continuation.md) gives one
command for the frozen two-hour bounded campaign, restart, fields, analysis and
small evidence ZIP. It includes controls, targets/refinement, the distinct
amplitude-one hyperbolic precursor, same-Q competitors, independent scaling,
domain changes, both preimage targets and cable witness replay.

New field checkpoints are full-precision float64 and atomic. Endpoint CPU audits
and independently measured residuals gate the result. Ctrl-C preserves accepted
fields. A rejected trial cannot change the accepted continuity margin; a targeted
regression test reproduces the old line-search failure and checks the corrected
production path. Original timing-default semantics remain available. Campaign
budget exhaustion, numerical rejection, changed core type and unresolved topology
remain explicit. No tolerance or coupling is weakened to obtain acceptance.

No GPU is accessible in this execution environment, and it cannot launch programs
on the user's workstation. **Long-run workstation fields and scientific outcomes
are pending.** The supplied local campaign performs the remaining computation;
its evidence ZIP is the input to the final applicability/reproduction assessment.
PR 36 remains draft and unmerged, and issue 35 stays open until that assessment.

## Verification of the continuation implementation

Full locked suite with topology instruments: **154 passed, 1 actual-device test
skipped**, 23.63 seconds. Documentation checks passed for 76 Markdown files; the
dependency lock and whitespace checks passed. New tests cover float64 checkpoint
round trips and rolling fallback, field restart with matching energy, Ctrl-C
preservation, the accepted-margin correction, stage budgets/dependencies,
subprocess timeout/log retention, input-aware analysis caching and evidence ZIP
hashes without duplicate/self-referential entries.

A separate 33³ two-step **CPU test-double** run exercised the production runner's
checkpoint/endpoint-audit path and the independent five-dilation scaling script.
Its fields and numbers are instrument checks, not GPU performance or target
results. Actual checkpointed long GPU runs remain pending on the workstation.
