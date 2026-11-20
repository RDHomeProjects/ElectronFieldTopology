# Complete result recording and retained-field diagnosis — 20 November 2026

This handover records the **entire completed non-field result**, its assessment and the diagnostic plan, then evaluates retained fields without relaxation or time evolution. All GitHub operations run only on the zbook through the commands below. Existing reports and graphics are retained.

The completed source is `20261120t003653z-a200a9db`, with evidence SHA-256 `cc17e740f2217cb072420c715d22a11cf1cf15b1d81e9c585251a89869edd643`. All six continuations remain preparation-unresolved and fail boundary admission. They used 225 additional attempts, with the registered early-stop conditions leaving 1,513 additional attempts unused. Those findings and all 34 seed dispositions remain unchanged.

## Why the result can appear contradictory

The diagnosis treats the concern as a comparison to be tested, not something to dismiss.

| Earlier/current comparison | What must be distinguished |
|---|---|
| Q2 positive result versus high-Q failures | The retained Q2 field must reproduce and pass first. It is a different configuration and Q sector. Its earlier positive finding remains valid unless same-field replay exposes a discrepancy. |
| Historical cell-energy convergence versus D4 dynamics admission | A pinned same-field Q17 record already reports cell residual about 0.0009666, alongside D4 force ratio about 0.1246 and maximum acceleration about 12.35. Operators and residual definitions differ; these numbers cannot be compared against one common threshold. |
| Older Q22 benchmark versus the current Q22 cable endpoint | The field hashes, grid and box differ: historical 129³/15.36 versus current 161³/23.04. A common Q label does not establish a common configuration. |
| Falling energy versus unresolved stationarity | Energy descent is a real result, but both measured force and acceleration must pass. Oscillation or rebound can coexist with falling energy. |
| Boundary fractions versus D4 static-action energy | Registered fractions use `energy_density`; the D4 action uses the sigma-corrected `hamiltonian_density`. Both are measured on identical fields, while the original registered gates remain unchanged. |
| 500-attempt authorization versus fewer steps | Five hundred is a total ceiling, not a requirement to override early stopping. None of the six reached 300, so no production conclusion about behaviour between 300 and 500 is claimed. |

These distinctions explain named comparisons; they do not establish that every earlier statement was correct. An unexplained disagreement on identical field bytes, operator, geometry, metric and gates is a blocking finding. The exact earlier assertion meant by the user has not been specified, so unlisted claims remain explicitly unassessed. Pinned local Q2–Q16 closure and higher-Q reconciliation documents are collected for reviewer inspection.

## Diagnosis scope

Five static field evaluations are performed sequentially:

1. Q2 retained positive control, 127³ / length 20.16.
2. Q21 final endpoint, 97³ / length 23.04.
3. Q21 retained parent, at the same grid and box.
4. Q22 cable final endpoint, 161³ / length 23.04.
5. Q22 retained parent, at the same grid and box.

For each field the run checks hashes, NPZ CRCs, float64 geometry and registered metric replay; evaluates projected force, instantaneous static acceleration, registered energy density and D4 Hamiltonian density; locates the ten largest sampled residuals; and measures every cube-shell grid layer plus radial profiles. The input array is made read-only and its array hash is compared before and after diagnosis.

It separates the projected-force numerator from the sigma normalization denominator, including held/free-node denominator contributions. Parent-to-endpoint comparisons show how those factors combine into the reported force ratio. Optimizer alpha and residual associations are recorded descriptively; dependent line-search observations do not prove causation. Central and hotspot slice graphics are self-contained SVGs with full-grid raster pixels, physical coordinate labels and logarithmic colours. No plotting dependency is added to the frozen environment.

**Optimizer steps: zero. Physical-time steps: zero.** Static acceleration is an operator evaluation at the retained state, not a simulation. No field is resampled, projected by this diagnosis, enlarged or used to restart relaxation. Built-in constraint handling in the original operator is preserved. No gate is lowered, and no old Q18 child is attached to a new parent.

CPU diagnostics use four threads for a common reference implementation. The already installed GPU dependency set is retained by `uv --frozen --extra gpu`, but CUDA is not initialized and the GPU optimizer is not run. A source-hash or same-field metric mismatch, including Q2 control failure, stops the diagnosis and preserves its error evidence.

## Record the entire completed result and start the diagnosis

Keep Open WebUI stopped. Require 10 GiB available RAM, 1 GiB free swap and 40 GiB free disk before launch. The service retains 7 GiB memory.high, 8 GiB memory.max, 1 GiB swap maximum, and sleep/idle/lid inhibition. Resource-pressure pauses occur only under sustained low available RAM. There is no overall wall-time cap.

```bash
unzip -n \
  "$HOME/Downloads/ElectronFieldTopology-results-and-field-diagnosis-20261120.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-results-and-field-diagnosis-20261120"

(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" install
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" preflight
  bash "$package/RUN.sh" run
  bash "$package/RUN.sh" status
)
```

`install` creates a separate publication clone, `~/ElectronFieldTopology-results-diagnosis-record-20261120`, based on fetched `origin/main`. It records every non-field file from the completed run, including logs, telemetry, complete frozen handover and compact evidence; the full current assessment and diagnostic plan are also included. Collection hashes are additional provenance and do not rewrite the original evidence seal. GitHub data is added under `docs/research/q17-q32-results-field-diagnosis-20261120/`, with a root README link. Protected earlier report/run identities are unchanged. Local project-record/documentation/whitespace checks and essential PR checks govern publication; no force merge or ancestry assumption is used.

The **36 full float64 NPZ files remain local**, with their original manifests. Preflight hash/CRC-checks all 36 plus the Q2 control, for 37 full-field checks. Full fields are not uploaded into Git or falsely described as remotely archived. This is an entire compact/non-field record plus authenticated local field retention, not a new remote full-field backup. No source or lock file is changed in the numerical checkout.

The numerical checkout remains at its pinned commit in `~/ElectronFieldTopology-adaptive-q-screen-20261117`. The diagnosis creates a separate `artifacts/q17-q32-field-diagnosis/<run-id>/` output and holds both earlier worker locks to prevent accidental simultaneous resume.

## Status, pause, resume and review

```bash
bash "$package/RUN.sh" status
bash "$package/RUN.sh" stop
```

An orderly pause finishes the current static field evaluation. It may take several minutes during CPU metrics, FFT diagnostics or file hashing. Wait for the worker and service to become inactive, then:

```bash
bash "$package/RUN.sh" resume
bash "$package/RUN.sh" status
```

Completed case outputs are sealed and reused. A partially completed static evaluation can be repeated without advancing any optimizer or physical time. A scientific `failed` record requires assessment; it is not automatically resumed.

At `complete_pending_review`, open the reported `REPORT.html`. It includes same-field metric checks, preserved gate outcomes, force normalization comparisons, density-definition comparisons, residual locations, all-layer profiles, central/hotspot slices and a claim-by-claim reconciliation ledger. `PRIOR-RECORDS.json` identifies the source Git commit and document hashes; copied Markdown bytes use `.md.txt` so old relative links are not misrepresented as a reconstructed website.

If the residual is associated with the guard region, a future fixed-spacing larger-domain test may be justified. If it is concentrated in the interior, a separate optimizer/operator diagnosis may be justified. Localization alone does not prove boundary causation, and this handover starts neither intervention. Q24/Q30, further relaxation, refinement and motion remain deferred pending these findings.

## Record the completed diagnosis

After status shows completion and both worker and service are inactive:

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" record-diagnosis
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" status
)
```

This creates a second local PR recording the complete diagnostic output, logs and telemetry. The source result and the initial assessment remain intact. Publication records completion and evidence; it does not certify a physically stable electron model.

An inactive interrupted or failed diagnosis can also be recorded with `record-diagnosis` once its compact evidence is sealed; the publication labels its actual status and preserves errors rather than claiming completion. An interrupted run can later resume from its completed cases. A numerical failure remains blocked for assessment. Raw retained logs and copied historical blobs are treated as immutable data in Git diffs; editable code/documentation checks remain enforced.

Each published diagnostic snapshot has its own status and archive-hash revision. If an interrupted diagnosis is recorded and later finishes, recording again adds the new snapshot without overwriting the earlier partial record.

Copy a uniquely named evidence ZIP for assessment:

```bash
repo="$HOME/ElectronFieldTopology-adaptive-q-screen-20261117"
run_dir="$(python3 - "$repo" <<'PY'
import json,sys
from pathlib import Path
print(json.loads((Path(sys.argv[1])/'.git/field-diagnosis-last.json').read_text())['output'])
PY
)"
assessment_zip="$HOME/Downloads/ElectronFieldTopology-field-diagnosis-$(date -u +%Y%m%dT%H%M%SZ).zip"
cp --update=none -- "$run_dir/evidence.zip" "$assessment_zip"
sha256sum "$assessment_zip"
```

See [HOST-VALIDATION.json](HOST-VALIDATION.json) for executed host tests and the checks still requiring retained zbook fields. The prior completed-run assessment is [available here](assessment/ASSESSMENT.html).
