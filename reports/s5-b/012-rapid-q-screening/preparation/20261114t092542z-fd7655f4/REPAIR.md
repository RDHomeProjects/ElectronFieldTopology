# Revision 2 — missing D4 adapter and baseline preflight repair

The workstation diagnostic recorded on 14 November 2026 at 09:09:39.620066 UTC / 20:09:39.620066 Australia/Melbourne showed seven required CPU sources and both dependency locks matching the frozen manifest, with `sf_time_gpu.py` missing from both the checkout and fetched `origin/main` (`baa9e49`). Revision 1 incorrectly assumed that the prepared adapter was already published. Its earlier local rehearsal had the module present and did not cover this installation state.

The corrected archive extracts to **ElectronFieldTopology-rapid-q-screen-20261114-r2**, so `unzip -n` cannot silently keep revision-1 scripts. Use this new directory for every command; keep the earlier archive unchanged for reference.

## Changes

- Bundle the exact prepared `sf_time_gpu.py`, SHA-256 `c6771c9a6bf69cbe3397ff8db718f4c10994a1025852d5159c3d45e589c18af3`.
- Permit only this specific missing module during baseline verification. If an existing module has different bytes, stop. All seven CPU sources, both dependency locks and retained survey hashes remain strict checks.
- Fetch main in a separate publication clone, verify its baseline, create the git bundle backup, add the missing exact adapter there, then require the complete strict source check before tests/staging/publication.
- Include the adapter and independent CPU comparison tests in the same screening PR. No original checkout files are changed, and no GPU motion driver is installed or activated.
- Benchmark, run and resume validate the installed clone. They no longer demand that the unchanged original checkout contain the newly published optional module. Retained original full-field checks remain mandatory.
- Preserve the scientific policy, candidate catalogue, thresholds, optimizer, earlier controls and negative outcomes. Actual CUDA qualification remains a workstation task.

## New validation

`validation/repair-installation.json` records the actual new missing-adapter installation rehearsal, conflict rejection, source/lock preservation, read-only original checkout, strict post-install check and independent numerical controls. These new tests supplement the earlier preparation evidence; they do not turn host NumPy execution into CUDA evidence or certify newly screened candidates.

GitHub is contacted only by the commands you run locally. No live GitHub operation was performed during preparation of this correction.
