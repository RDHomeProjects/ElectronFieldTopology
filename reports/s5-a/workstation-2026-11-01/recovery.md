# Recovery of the interrupted PR 36 recording session

Date: 1 November 2026 (Australia/Melbourne).

GitHub PR 36 was still draft/open at `a607ccd496ed75dc6c3cee00c9ecb14d8f2c3793` when recovery began. The workstation evidence, readable records, result assessment, ADR-0007, status updates, archive checker and workflow indentation fixes survived as uncommitted changes in the recording checkout. The original uploaded `evidence.zip` and `SUMMARY.md` also survived. The session interruption's cause is unknown. Separately, the workstation campaign's omitted cases are explicitly recorded budget outcomes, not evidence of a solver crash.

The maintainer had instructed: “record and merge the current results before continuing down the tightened milestone path.” This recovery completes that publication tranche as a measured partial result. It does not convert either target into a completed reproduction or close issue 35 as successfully reproduced.

## Checks performed during recovery

- The retained archive matches the original upload byte for byte: SHA-256 `2ff8f15facc37b02736242926d1d43a2a20b3f7ed27bf5f28f2daf9f1cbe81f3`. Its 164 unique entries cover 163 hashed members and eleven case results. Readable records and generated summary are unchanged.
- Case configurations and summary endpoints match; all stored scaling records satisfy the declared numerical derivative/virial limits. These are checks of the retained records, not a recomputation from full fields.
- All eight cable witnesses have inputs belonging to the recorded reference/candidate diagrams. Their sixteen output diagrams reproduce the saved common canonical words. Fresh bounded common-diagram matching is checked separately; random-seed replay remains subject to the limitation in the main report.
- Locked local suite: `OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 uv run --frozen --extra topology pytest -q` — **154 passed, 1 skipped**. The skipped test requires an actual CUDA device.
- Archive checker, documentation checker and `git diff --check` passed. All workflow YAML files parse. Seven older workflow filters had malformed indentation at the previous head; the recovered fixes restore their intended documentation/report exclusions, without changing numerical jobs or physical tolerances.

The full three-dimensional fields are absent from this ZIP. Preserve the workstation directory recorded in the [assessment](README.md) for the next bounded Q22 continuation. No long-running physics calculation or new literature review was started during recovery. The next research scope is [ADR-0007](../../../docs/decisions/ADR-0007-tightened-milestones.md); final hosted checks and merge state are recorded by GitHub on PR 36.

AI assisted recovery, verification and reporting.
