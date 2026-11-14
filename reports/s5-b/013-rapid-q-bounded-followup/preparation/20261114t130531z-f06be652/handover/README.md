# Rapid Q assessment and bounded follow-up — 14 November 2026

This handover records the completed rapid screen, corrects prior selection and explicit deferral reporting, and prepares the authorized fixed-configuration continuation. All GitHub operations execute on your workstation. It uses a new checkout and preserves both original run directories.

## 1. Verify, publish and merge the assessment/preparation

The default source checkout is `$HOME/ElectronFieldTopology-rapid-q-screen`, whose `artifacts/RAPID-Q-SCREEN-CURRENT` identifies the completed run. The original Q3/Q4/Q7 survey remains under the repository-admin checkout. The new publication/compute checkout is `$HOME/ElectronFieldTopology-rapid-q-followup`.

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-rapid-q-followup-20261114.zip" -d "$HOME/Downloads"
package="$HOME/Downloads/ElectronFieldTopology-rapid-q-followup-20261114"
(
  set -euo pipefail
  bash "$package/RUN.sh" verify
  bash "$package/RUN.sh" publish
  bash "$package/RUN.sh" merge
  bash "$package/RUN.sh" preflight
)
```

`verify` checks the original compact evidence, source/lock identities, the full completed-screen field manifest and selected original legacy fields. This may take time reading/decompressing several GiB. `publish` creates the separate clone, bundles its history, records the raw compact evidence plus assessment in a new immutable record, patches selection/deferral reporting, registers the follow-up and runs essential checks before creating the PR. `merge` respects required hosted checks. No numerical job starts during publication.

If DNS/fetch fails, restore connectivity and repeat **the same publish command**. A marked `.installing` clone is retained for retry. Do not rename or delete it. Unknown/edited directories stop; the package never resets an unrelated working checkout. `install` stages/checks without pushing if you want a separate review step.

## 2. Audit selected fields and start the bounded run

After other EFT analyses finish:

```bash
(
  set -euo pipefail
  bash "$package/RUN.sh" audit
  bash "$package/RUN.sh" run
  bash "$package/RUN.sh" status
)
```

`audit` runs in the foreground. It verifies the retained fields, replays CPU metrics on seven selected endpoints, verifies the original qualified device/environment/math identity, and compares one disposable CPU/device continuation step for every selected field. Original fields and optimizer states remain untouched. No full benchmark repeat is required when these identities and checks agree. CUDA mismatches or missing resources stop without fallback. The successful receipt is bound to this publication and package; changed source/environment requires a fresh audit.

`run` launches in a background session. Four CPU threads match the original device qualification; leave `EFT_THREADS` unset or set it to `4`. The fixed plan is:

| Endpoint | Grid | Additional steps |
| --- | --- | ---: |
| Q6 axial | 97³ | 200 |
| Q4 axial22, retained medium | 121³ | 100 |
| Q7 trefoil, retained medium | 121³ | 100 |
| Q8 trefoil, secondary | 121³ | 100 |
| Q5 trefoil, capacity control | 97³ | 50 |
| Q9 trefoil, cutoff control | 145³ | 50 |
| Q10 trefoil, cutoff control | 145³ | 50 |

Maximum **650 additional accepted steps**, in batches of at most 50. Branches stop early on strict measured gates, representation loss or solver stall. All scientific gates, grid, box, seed lineage and numerical algorithm stay fixed. Legacy Q4/Q7 imports explicitly restart conjugacy because their old format lacks the complete optimizer state; the five screen-state jobs continue that state exactly. No mesh or motion is launched.

## 3. Monitor, stop, resume and return results

```bash
bash "$package/RUN.sh" status
```

Status prints job, batch target, liveness, heartbeat, log and output paths. `stop` requests a graceful checkpoint; wait until status reports `interrupted` and no live worker, then use `resume`. Resume uses the same pack, source, plan, audit and parent fields. It does not reset conjugacy at a 50-step batch boundary. A changed seal/identity stops rather than continuing ambiguously. Abrupt power loss between checkpoint and seal replacement may require manual recovery; both source datasets remain intact.

After `complete_pending_review`:

```bash
run_dir="$(cat "$HOME/ElectronFieldTopology-rapid-q-followup/artifacts/RAPID-Q-FOLLOWUP-CURRENT")"
xdg-open "$run_dir/REPORT.html"
printf 'Evidence for review: %s\n' "$run_dir/evidence.zip"
```

Return **that new evidence.zip**. Keep all original/new full NPZ files and the original benchmark directory until separately archived and verified. Compact evidence is not a substitute for full fields.

Optional path arguments: `--repo /path/to/rapid-q-screen`, `--publication /new/followup/checkout`, `--source-run /completed/screen/run`, `--past-run /original/20261109t134425z-89d28344`. Use the same overrides consistently. A source-run override can bypass a missing/stale pointer, but its archive must match this assessed run exactly. The future run stores its chosen input paths in the installation record.

`qualify` reruns the small host controls after publication. See `MODEL.md`, `ASSESSMENT.html`, `FOLLOWUP.json` and `HOST-VALIDATION.json` for scope, measured preparation tests and limitations. New candidate outcomes and actual local audit are still pending; host CPU fixtures do not constitute CUDA production evidence.

## Repository replay support

The new preparation record includes an exact `handover/` copy of this payload, including launch support and compact inputs. After restoring matching full-field archives, its `followup_worker.py audit` and `run` entry points can be invoked directly with the repository's frozen uv environment and explicit `--repo`, `--source-run`, `--past-run`, `--output` and (for run) `--audit-receipt` paths. This preserves reproducibility beyond the Downloads directory; the higher-level RUN.sh commands remain the normal workstation workflow.
