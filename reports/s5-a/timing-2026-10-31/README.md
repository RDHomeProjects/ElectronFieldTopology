# CPU timing reference — 31 October 2026

This is performance instrumentation for PR 36 / issue 35, supporting REP-001/002
and SW-001. It adds no reproduction, convergence, stability or electron claim.
AI assisted the harness, measurement and reporting. Read [the usage guide](../../../docs/static-timing.md)
and [existing model/source map](../../../docs/models/SF-J2015-static.md).

## Replacement environment: controlled short runs

CPU: AMD EPYC 9V74; nine visible CPUs, cgroup quota equivalent to eight CPUs and
8 GiB memory limit. GCC 13.3.0, Python 3.12.14, NumPy 2.5.4 and SciPy 1.18.1.
No GPU was used. Kernel/platform string matches the old manifests, but old CPU
allocation/hardware is not established; do not assume this is the crashed machine.

The retained reference comes from sequential runs with no concurrent local test
job. An earlier exploratory quick run overlapped initial validation and was
excluded. Three timed samples follow warm-ups, and every short solve restarts
from the same seed for three steps. Settings, all samples, numerical values,
hardware limits and hashes are retained in [quick timing.json](timing.json),
[Q18 timing](q18-timing.json) and [Q22 timing](q22-timing.json).

| Case | Grid | Threads | Energy + gradient, s | Whole short solve / step, s | Diagnostics, s | Peak RSS, MiB |
|---|---:|---:|---:|---:|---:|---:|
| q1 | 65³ | 1 | 0.381868 | 0.561406 | 0.150706 | 176.6 |
| q1 | 65³ | 4 | 0.134398 | 0.251144 | 0.123080 | 176.3 |
| q1 | 97³ | 1 | 1.205138 | 1.927820 | 0.707783 | 444.5 |
| q1 | 97³ | 4 | 0.328340 | 0.823294 | 0.681082 | 444.7 |
| q18 | 97³ | 4 | 0.374571 | 0.796491 | 0.716395 | 464.9 |
| q22 | 129³ | 4 | 1.056182 | 1.848480 | 1.405143 | 945.0 |

Times are medians. Per-step short-solve cost includes initial evaluation and
startup, but excludes callbacks, archives and report I/O. The peak RSS covers
the complete worker including setup/diagnostics/warm-ups. Compiler/seed setup is
excluded from timed operations. These measurements do not predict production
memory or convergence time. CPU load, thermal behaviour and shared-host scheduling
can affect results. Q18/Q22 refer to initial precursors, not accepted final knots.

Each JSON records a working tree based on public commit `76bbbe1`, with the
new timing module not yet committed when measured. Its exact source hashes are
preserved and verified against the files published with this report. The solver,
energy implementation and lockfile are unchanged from that base. The comparison
uses hashes/configuration/numerics rather than assuming equal git commit IDs.

## Crashed environment: approximate historical context

The [retained history derivation](historical-context.json) records source hashes,
iteration ranges and timestamps. Both original production runs requested four
OpenMP threads and one OpenBLAS thread:

| Historical run | Iteration interval | History interval / step |
|---|---:|---:|
| q18-97 | 0–516 | 1.743838 s |
| q22-129 | 0–240 | 3.736643 s |

Those histories include changing line-search/field workloads, periodic diagnostics,
compressed checkpoints and reporting. They are **not the same timing experiment**.
No controlled speedup versus the crashed environment is inferred from these
numbers. Re-run the harness on the workstation and use `--compare` for the exact
replacement-environment comparison. Ratios greater than one mean the new run is
faster; numerical/configuration/source mismatches suppress ratios.

## Validation and limitations

Targeted independent energy/gradient, minimisation and timing checks: **11 passed**.
The new process-isolation integration test verifies one/two-thread workers,
refusal to overwrite results, and rejection of source/work mismatches. Quick and
both target workloads completed with resolved initial cells/Hopf integrals and
identical repeat iteration/evaluation counts. No numerical production source or
acceptance threshold changed. A tiny timing integration check was added to the
existing static-energy CI job; no hosted timing study or larger solve was added.

The seven pre-existing malformed workflow filters identified during the status
review remain outside this timing change. This report does not claim all PR
workflows pass. PR 36 remains draft and unmerged; the target reproductions remain
unfinished. No CUDA install or GPU implementation is supplied.
