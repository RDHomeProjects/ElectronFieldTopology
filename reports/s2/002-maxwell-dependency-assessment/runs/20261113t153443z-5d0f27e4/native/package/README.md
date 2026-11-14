# Maxwell bounded validation extension — local workstation handover

This package runs the previously discussed bounded Maxwell extension with adaptive single-variable dependency studies. No earlier package is required. It reads the existing ElectronFieldTopology checkout but does not edit source, reset a branch, install new dependencies into its lockfile, or contact GitHub. Authoritative repository publication/roadmap changes follow review of the new results; no project completion claim is made by this auxiliary control package.

## What runs

| Block | Active variable | Fixed conditions |
|---|---|---|
| Hopfion time-step curve | dt, via integer step count | N=65, box side 8, T=0.2, phase 0, unrotated field, analytical two-layer boundary prescription |
| Periodic packet time-step curve | dt | Same N/box/T; fixed eight-mode packet and periodic boundary |
| Hopfion duration curve | T in [0.2,1.0], including 0.5 and 1.0 | Same grid/box/phase/orientation; dt=1/240; same driven boundary prescription |
| Packet duration curve | T in [0.2,1.0], including 0.5 and 1.0 | Same periodic packet/grid/box; dt=1/240 |
| Hopfion orientation curve | Proper rotation about y, 0–90 degrees | T=0.2, dt=1/240, same grid/box/phase and rotated analytical boundary prescription |

Each block starts with four development points, adds up to nine adaptively selected measurements for Hopfion or six for the periodic packet, then freezes its model before three reserved validation measurements. The Hopfion adaptive allowance is increased by 50% from six to nine in each of its three blocks; the fixed seed and validation counts are unchanged. A block may finish earlier if its declared stopping tolerances are met. Selection concentrates around provisional turning points, possible inflections, residuals, disagreement or informative gaps. It does not use the reserved validation values. Intervals adapt; they are not a repeated fixed spacing. Empirical stopping tolerances and the maximum measurement count are explicit in PLAN.json. A failed prediction check or exhausted budget remains visible.

Additional matched controls retain periodic cubic x90/y90 rotations at T=1 and two smaller dt checks at T=1 (480/960 steps) for each field. The late-time step checks are a targeted interaction test, not a mixed-variable fitted curve. Across the entire default run at most 80 distinct cases may execute; repeated identical configurations are reused with verified hashes. There is no wall-clock timeout or two-hour cap. This implementation uses the existing NumPy/SciPy CPU reference in float64; it does not switch backends or reduce precision/grid on failure.

See MODEL.md for equations, sources, synchronization, interpolations, conservation diagnostics, all tolerances and limitations. No optimal operating condition is selected because no new numerical accuracy/cost objective has been supplied.

## Required workstation state

Ubuntu zbook; existing repository at `$HOME/ElectronFieldTopology-repository-admin`; uv; locked CPython 3.12.14 environment with the existing numpy/scipy/matplotlib dependencies. The existing fields.py and evolution.py must match the supplied SHA-256 pins. Verification reports a mismatch without overwriting anything; retain that output for assessment. A different current commit is allowed only if those scientific source files remain byte-identical. Actual commit, tracked working-tree changes, dependency lock hashes, versions, host and thread settings are recorded.

Full final fields stay under the new local run directory and need free disk space; a case starts only while at least 3 GiB remains. Allocate several GiB for the complete run. No full state is deleted or uploaded automatically. Keep previous research runs and archives untouched.

## Exact commands

Download ElectronFieldTopology-Maxwell-bounded-validation-20261114.zip into Downloads:

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-Maxwell-bounded-validation-20261114.zip" \
  -d "$HOME/Downloads"

package="$HOME/Downloads/ElectronFieldTopology-Maxwell-bounded-validation-20261114"

bash "$package/RUN.sh" verify
bash "$package/RUN.sh" run
bash "$package/RUN.sh" status
```

`run` performs fresh local manufactured qualification before the adaptive studies and then continues in the background. If qualification fails, it stops with the failure retained. Closing the terminal does not stop the detached run. A repeated `run` while it is active reports already_running. The package records one current run in its own pointer, independent of older campaign pointers.

```bash
run_dir="$(cat "$HOME/ElectronFieldTopology-repository-admin/artifacts/MAXWELL-BOUNDED-VALIDATION-CURRENT")"
tail -n 25 "$run_dir/runner.log"
bash "$package/RUN.sh" status
```

Optional local controls without starting the default campaign:

```bash
bash "$package/RUN.sh" qualify
bash "$package/RUN.sh" smoke
```

`smoke` uses N=17 with a smaller adaptive budget and is prominently labelled smoke. It does not replace the 65³ run or change the production plan. These optional commands write separate receipt directories and do not change the current production pointer.

To pause and resume the current default run:

```bash
bash "$package/RUN.sh" stop
bash "$package/RUN.sh" status
# After runner_alive is false:
bash "$package/RUN.sh" resume
```

Resume reuses completed cases, verifies full-field hashes, and recomputes only an interrupted case. It preserves recorded choices and frozen models and rejects source/config/dependency/package identity changes. Do not edit or move the package, change Python/thread settings or update the checkout while this run is in progress. A completed run is not restarted by resume. To run the full plan again after completion use run, which creates a new directory. To use a different existing checkout pass `--repo /absolute/path` to every command. Thread setting defaults to six; set `EFT_THREADS` before starting and keep it fixed through resume.

## Outputs and review

Status `complete_pending_review` means the finite run finished, not scientific admission. Open the report and locate the compact evidence:

```bash
run_dir="$(cat "$HOME/ElectronFieldTopology-repository-admin/artifacts/MAXWELL-BOUNDED-VALIDATION-CURRENT")"
xdg-open "$run_dir/REPORT.html"
cat "$run_dir/SUMMARY.md"
printf '\nUpload for review: %s\n' "$run_dir/evidence.zip"
```

Upload the new evidence.zip for assessment. It includes the self-contained browser report, high-resolution curves, measurements.csv, all per-case diagnostics/traces, adaptation selections, frozen fits, validation residuals, numerical-control outcomes, source/dependency hashes, code/config and field manifest. It excludes the large native float64 arrays, which stay in fields/ with hashes and CRC checks. Their local retention is required until a separately verified archive is available. This package does not implement a release upload or deletion step.

UTC and Australia/Melbourne timestamps appear in status, provenance and reports. Driver wall times are recorded as measurements, not a prediction of workstation performance. No GPU speedup is claimed.

## Interpretation limits

E and B are synchronized in time before mixed diagnostics and linearly interpolated to common cell centres for energy/flux and direct Yee/Fourier comparisons. The original native staggered arrays remain available. The matched periodic packet is a controlled synthetic multimode problem, separate from the driven-boundary Hopfion. Arbitrary packet rotations would break its periodicity, so its rotations are cubic only. Native divergence preservation and a discrete modified-energy invariant are distinguished from physical continuum energy. Flux defects retain quadrature/interpolation sensitivity. The analytic half-step startup depends on dt. Fixed grid and box do not establish spatial/domain convergence or isolated boundary validity.

Q1 stays parked; Q2 remains the SF reference; prior Q3/Q4/Q7 unresolved findings and all original gates remain. These Maxwell field-error curves are not SF speed errors and provide no electron/charge/spin/confinement certificate.

## GitHub handoff boundary

All GitHub work remains on your workstation. This run handover performs no commit, push, PR, merge or release action. The run first produces reviewable evidence; publication should add that assessment and reconcile the current authoritative study register from the actual workstation checkout, without overwriting earlier reports. This package does not supply an automatic merge script or fabricate a new project-stage ID against an unseen current register.
