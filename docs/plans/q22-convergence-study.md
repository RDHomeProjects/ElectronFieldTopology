# Q22 convergence study after PR 46

Prepared: 1 November 2026, Australia/Melbourne. Status: run tooling prepared; no new workstation measurements have been obtained. Requirements: GOV-002, SCI-003, NUM-003, REP-001/002. Implements the Q22 follow-up in [ADR-0007](../decisions/ADR-0007-tightened-milestones.md). The maintainer explicitly removed the inferred two-hour cap and requested thorough investigation with additional options where needed. This supersedes a total-duration assumption, not scientific acceptance gates or historical budgets.

## Question and scope

Can the existing cable-compatible Q22 fields reach the declared stationary residual, survive mesh and matched-spacing domain studies, and be compared fairly with a relaxed same-charge alternative? Preserve Q18's linked alternative and failed hyperbolic-basin result. No wider Q catalogue, new field theory, fitted coefficient or physical-time solver is introduced. The equation and discretisation remain [SF-J2015-static](../models/SF-J2015-static.md), with Jennings L36 and Sutcliffe L37 in the [literature register](../literature/README.md). No source equation is changed by this orchestration.

## Study matrix

| Stage | Grid | Spacing | Half-width | Starting field |
|---|---:|---:|---:|---|
| Historical stationary reference | 129³ | 0.12 | 7.68 | Preserved q22-129-cont-1 |
| Cable polish | 161³ | 0.096 | 7.68 | Preserved q22-161-1 |
| Cable polish | 193³ | 0.08 | 7.68 | Preserved q22-193-1 |
| Larger box | 161³ | 0.12 | 9.60 | Historical 129³ reference |
| Largest reviewed box | 193³ | 0.12 | 11.52 | New 161³ larger-box endpoint |
| Finer-spacing larger box | 193³ | 0.096 | 9.216 | New polished 161³ cable endpoint |
| Comparator polish | 129³ | 0.12 | 7.68 | Preserved q22-comparison-1 |
| Comparator refinement | 161³ | 0.096 | 7.68 | New comparator 129³ endpoint |
| Comparator refinement | 193³ | 0.08 | 7.68 | New comparator 161³ endpoint |

The comparator's seed was K(5,4); its previously observed endpoint was a three-component link. This is a same-charge alternative, not an imposed knot family. Relaxation may change preimage knot type. Ranking requires equal grids/spacing/boxes and independently audited stationary endpoints; topology remains a separate assessment. The finer-spacing larger box gives a second spacing at which domain sensitivity can be tested without exceeding the already validated 193³ allocation.

## Progress, checkpoints and stopping

There is **no overall wall-time cap** and no automatic completion after two hours. Each pass uses the solver's existing 3,000-iteration/1,800-second bounds, with 300 seconds allowed for endpoint auditing and orderly subprocess completion. These delimit a checkpoint/restart interval, not the length of the study. The next pass continues the accepted endpoint, restarting conjugate-gradient directions. An overall study can take many hours or longer; throughput and convergence are not guaranteed.

Continue a stage until its CPU tangent-gradient RMS is below the unchanged 1e-3 limit, a numerical/audit fault occurs, or progress stalls across the available optimiser options. The 5% charge-resolution checks, positive resolved-cell margins, unit norm, independent CPU/GPU endpoint audit, 2% mesh/domain energy comparison, 5% virial/independent scaling and 3% published-energy limit remain unchanged. A stationary endpoint that fails another scalar gate is recorded with that failure; it is not polished indefinitely merely to change its classification.

Use preconditioning lengths 0.5, then 0.25 and 1.0 only if needed. This changes the optimiser metric, not the energy functional or coefficients. A plateau is less than 0.5% best residual improvement **and** less than 1e-8 relative energy decrease over the most recent three passes at the same option. These are practical progress controls, not acceptance tolerances or proof that no minimum exists. Slow progress that exceeds either control continues without a fixed pass count. After all options stall, preserve the partial outcome for assessment; any additional strategy should be motivated by its residual/energy history rather than a blind catalogue expansion.

The original campaign is read-only. Original final fields must match the SHA-256 hashes in the published manifests; in checkpoint-continuation mode, required missing or modified inputs stop preflight. A missing optional comparator is recorded and blocks its refinements, while the cable/domain study remains possible. Numerical source and lockfile hashes must still match the original validated implementation. New orchestration and the new plan are separately hashed. Each new pass performs the existing device validation and independent CPU endpoint audit.

Every pass has its own field and scalar records. Checkpoints, failures and all optimiser options remain preserved. Disk availability is checked against eight uncompressed field arrays before starting each pass; insufficient space pauses the study without deleting results. Full 3-D fields can accumulate substantial disk usage. The small evidence archive deliberately excludes those bulk fields, whose absolute workstation paths and hashes are retained.

## Dates and times

Use ISO 8601 timestamps with explicit offsets in **UTC and Australia/Melbourne**. Study and pass directories and logs carry a date/time tag. Generated configurations, results, manifests, analysis JSON, summaries and evidence manifests record dates/times. Per-pass `timing.json` records execution start/end and modification times for raw field/history files; the evidence manifest records modification times and hashes for every included member. Binary field values are not rewritten to add dates. Historical elapsed-time samples remain unchanged; no absolute per-sample times are invented retrospectively. The original research files retain their contemporaneous dates.

## Run and recover locally

Commit this additive tooling on `work/q22-convergence-study` before computation. Publishing/PR/merge operations are performed by the maintainer from the workstation. Python 3.12.14 and the committed lockfile remain the numerical environment.

```bash
uv sync --frozen --all-groups --extra topology --extra gpu --python 3.12.14
uv run --frozen --extra topology --extra gpu --python 3.12.14 \
  python -m electron_field_topology.sf_q22_closure --preflight
```

The default original field directory is `/home/rd/ElectronFieldTopology-timing/artifacts/gpu-continuation-20261101-004351`. Override it with `--source-campaign` if that entire original tree was copied elsewhere. Keep the original tree.

```bash
study_dir="$PWD/artifacts/q22-study-$(TZ=Australia/Melbourne date +%Y%m%dT%H%M%S%z)"
printf '%s\n' "$study_dir" > artifacts/q22-study-latest.txt
uv run --frozen --extra topology --extra gpu --python 3.12.14 \
  python -m electron_field_topology.sf_q22_closure --output "$study_dir"
```

Create `artifacts/` first if needed. Keep the terminal open during a foreground run. A single Ctrl+C asks the child to retain its accepted field and complete the endpoint audit. Wait for that to finish. `--resume --output <same-directory>` continues an interrupted study from complete audited endpoints without repeating finished stages or changing its plan. An incomplete/corrupt last pass is preserved and marked unresolved rather than silently used. A process lock rejects concurrent launches against the same output directory. Source, commit, plan and original-input hashes must agree on resume.

```bash
study_dir="$(cat artifacts/q22-study-latest.txt)"
uv run --frozen --extra topology --extra gpu --python 3.12.14 \
  python -m electron_field_topology.sf_q22_closure --resume --output "$study_dir"
```

The timestamped output records `campaign.json`, `summary.json`, `SUMMARY.md` and `evidence.zip`. The summary/archive are refreshed after each completed pass and stage and on orderly interruption. To rebuild only the small evidence archive after a stopped process, use `--collect --output <same-directory>`; it performs no solver or topology run. Collection is refused while the study process holds the lock.

## Analysis and disposition

At each stage endpoint, compute the two preimages, three sampling resolutions and three views, independent dilation checks, and cable common-diagram searches for cable/domain cases. Analysis jobs have their own 900-second attempt timeout; a failed/timed-out analysis remains unresolved and may be retried by resuming the study. The current witness implementation's finite random-seed search has its existing internal bound; the study-wide two-hour cap is not reinstated. An unchanged successful analysis is cached by input signature. Date-stamped logs and failed/partial outputs remain evidence.

The signed diagram words, input membership and common-diagram witnesses require review. Preserve the existing random-seed replay limitation and avoid a continuum-isotopy claim. A Jones polynomial is not a unique knot name. Scalar convergence comparisons are reported only for eligible audited stationary endpoints with compatible geometries. A small energy difference at nonstationary endpoints remains provisional. All unresolved/failing gates remain visible, and `partial_pending_scientific_review` stays explicit until the retained outputs are reviewed.

After the Q22 ledger is assessed, proceed to the charge-capable relativistic equation audit in ADR-0007. More minimisation time is not evidence for physical-time stability, electric charge, quantum spin or an electron model.

AI assisted orchestration, verification and reporting. No new GPU result has been produced in the review environment.


## Fresh calculation when historical fields are unavailable

Added: 1 November 2026, Australia/Melbourne, after the maintainer's search found no Q22 `final.npz`, `latest.npz` or `previous.npz` files in the searched home/media/mount locations. This establishes that those searches found no usable checkpoint; it is not proof that every possible backup was searched.

Use `--fresh-seed` to make a **new calculation with new provenance**. No historical field file or campaign path is required. Preflight checks the unchanged historical numerical source and lockfile, and verifies the preserved Q1, Q2, Q22 cable and comparator seed configurations against their published campaign hashes. This does not regenerate byte-identical historical trajectories or certify the earlier results again.

The runtime plan first solves fresh Q1 and Q2 controls at 65³ and h=0.24. Both must satisfy all existing basic gates before any Q22 solve starts. It then solves a fresh Q22 cable seed at 129³, refines this new endpoint to 161³ and then 193³, runs the same larger-domain studies, and independently solves/refines the preserved comparator seed. There are eleven stages in total. A new seed is used only on the first pass of the two controls, the coarse cable and the coarse comparator. Every later pass continues its own audited endpoint, and every refinement starts from a newly measured dependency field. The original seed parameters, field equations, coefficients and scientific acceptance thresholds stay fixed.

The new coarse Q22 endpoint becomes the reference for all fresh-study mesh, domain and same-grid comparator comparisons. Historical scalar records are explicitly marked **context only** and cannot fill a missing fresh reference or gate. If the fresh relaxation reaches another basin or core topology, preserve and report that outcome. The procedure does not impose a cable topology or assume the original result will repeat.

```bash
uv run --frozen --extra topology --extra gpu --python 3.12.14 \
  python -m electron_field_topology.sf_q22_closure --fresh-seed --preflight
```

Start a new, dated output directory with `--fresh-seed --output <new-directory>`. The handoff's `RUN-FRESH.sh` creates this directory and prints its path. It writes `artifacts/q22-fresh-latest.txt` so `RUN-FRESH.sh <repo> resume` can continue it. The module also infers fresh mode from a saved study when `--resume` is used. `--collect` remains metadata/evidence export only. Existing no-overall-cap, progress-option, locking, timestamp and preservation rules continue to apply. Fresh controls receive scaling audits; the cable-identification search is not misapplied to low-charge controls.

No new physical result was obtained while preparing this mode. Fresh and historical results must remain distinguishable in any subsequent assessment or publication.


## Recorded outcome and next task

Assessment recorded: 2026-11-01T12:35:36+11:00 (Australia/Melbourne); 2026-11-01T01:35:36+00:00 (UTC). The fresh study was published in [PR 47](https://github.com/RDHomeProjects/ElectronFieldTopology/pull/47). See the [scientific assessment and numerical gate ledger](../../reports/s5-a/q22-fresh-20261101T102757+1100/ASSESSMENT.md). All eleven final endpoints satisfy the declared scalar gates; cable evidence is supported at the finite-diagram level, and the stationary three-component linked comparator is lower in energy on each matched grid. The narrowed Q22 milestone is supported with these stated limits; Q18 remains incomplete. The recommended next task is the ADR-0007 charge-capable relativistic equation audit, rather than a wider Q catalogue or another physical-time simulator. Raw generated summaries and all intermediate failures remain unchanged.
