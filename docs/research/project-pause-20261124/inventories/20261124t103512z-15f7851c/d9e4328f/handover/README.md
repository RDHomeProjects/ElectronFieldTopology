# Matter Waves — pause inventory and restart documentation

This handover completes the inventory/documentation phase on the zbook. It does not run scientific analysis, delete files, upload full arrays, create a release/tag or make the repository read-only. The previous scientific handover is already recorded; it is not republished by these commands.

## Run the inventory

```bash
unzip -n "$HOME/Downloads/ElectronFieldTopology-pause-inventory-20261124.zip" -d "$HOME/Downloads"

pause="$HOME/Downloads/ElectronFieldTopology-pause-inventory-20261124"

(
  set -euo pipefail
  bash "$pause/RUN.sh" verify
  bash "$pause/RUN.sh" inventory
  bash "$pause/RUN.sh" status
  bash "$pause/RUN.sh" collect
)
```

Keep the terminal open and the laptop awake on AC power. SHA256 hashing and ZIP/NPZ CRC checks read the actual file contents, so a large collection can take hours. Progress is printed about every 15 seconds during file hashing and container checks; CRC progress counts expanded bytes. The script uses the system Python standard library; it does not need the numerical venv or GPU. Do not change project files while it runs. Valid live-worker identity records block a new inventory; use the appropriate scientific handover to stop a worker rather than killing arbitrary Python processes.

The numerical checkout defaults to `$HOME/ElectronFieldTopology-adaptive-q-screen-20261117`. If it has moved, add `--repo /actual/checkout` to all commands. The output is a new directory under `$HOME/MatterWaves-PauseInventory`, with a LATEST.json pointer. Existing source files and prior inventories are not deleted.

Discovery searches under the home directory, to the declared discovery depth, for file/directory names beginning ElectronFieldTopology, Matter-Waves, MatterWaves, Matter Waves or Matter_Waves. Once a project directory is selected, its contents are traversed without that depth restriction. Runtime caches, venvs, Git internals and credential-candidate files are explicitly excluded. Named directory symlinks are listed without following them. This scope is recorded; arbitrary renamed folders and external drives are not assumed to be covered.

Add actual additional scientific locations when needed:

```bash
bash "$pause/RUN.sh" inventory --resume --root "/media/rd/EXTERNAL/actual-project-data"
bash "$pause/RUN.sh" collect
```

Replace that example path with a real existing directory. Repeat --root for multiple additional locations. Resume retains previously specified additional roots and reuses unchanged hash/CRC results. It verifies file metadata around hashing and checks for changes again before completion. This cache is an inventory convenience; the later upload/restore phase must verify actual archive bytes independently.

If interrupted, repeat:

```bash
bash "$pause/RUN.sh" inventory --resume
bash "$pause/RUN.sh" status
bash "$pause/RUN.sh" collect
```

## What is generated

- **PAUSE-AND-RESUME.md:** scientific stopping point, exact Q21 final/best identities, environment, recovery sequence and pending archive steps.
- **SUMMARY.json / SUMMARY.md:** selected roots, file counts, logical/unique-content sizes, duplicates, cache use and coverage issues.
- **FILES.jsonl.gz / FILES.csv.gz:** per-file paths, sizes, SHA256 and ZIP/NPZ CRC outcomes. No full scientific arrays are copied into this inventory archive.
- **ROOTS.json / EXCLUSIONS.json / SYMLINKS.json:** the actual scope and exclusions to review before final packaging.
- **FIELD-REFERENCES.json / REQUIRED-CHECKPOINTS.json:** availability of standard on-disk field declarations and 17 recent reference paths, with same-hash relocation recognized. Missing individual files may exist inside old archives; they are not automatically declared lost.
- **REPOSITORIES.json:** checkout commits, branches, refs and worktree status, with sanitized origins. Git bundles are a later archive step; this inventory alone does not preserve local-only history.
- **UNASSIGNED-DOWNLOADS.json:** generic evidence/summary/pasted-text filenames that need assignment before final archiving. Their contents are not automatically published.
- **ENVIRONMENT.json:** basic platform and available Python/uv/GPU-driver observations, without running numerical code.
- **ERRORS.json:** unreadable, unstable or CRC-failed files. Their available hashes are retained where possible; gaps remain explicit.
- **inventory-evidence.zip / SHA256SUMS:** the compact metadata archive with exhaustive payload checksums.

The normal terminal status is **inventory_complete_review_required**. It means the selected scope was inventoried, not that every historical field is proven preserved or that an archival release exists. An incomplete-with-errors status preserves the metadata for review and is labelled as incomplete in the restart document. Generic downloads, external locations, symlinks, nested archives and missing field references require disposition before declaring the full archive complete.

## Record the inventory and restart document in GitHub

After the inventory finishes:

```bash
(
  set -euo pipefail
  bash "$pause/RUN.sh" install
  bash "$pause/RUN.sh" publish
  bash "$pause/RUN.sh" merge
  bash "$pause/RUN.sh" status
)
```

All GitHub interaction occurs from these workstation commands. A separate checkout, `$HOME/ElectronFieldTopology-pause-publication-20261124`, is used. No scientific checkout is reset or overwritten. The additive records are under `docs/research/project-pause-20261124/inventories/`, with a root README link and the last scientific assessment retained alongside the reproducible inventory code.

The publication transaction requires the repository's record/documentation checks, staged whitespace check, available PR CI checks and post-merge payload verification. It uses squash-safe payload verification rather than assuming an old PR head must be an ancestor of main. Metadata errors and unresolved coverage are published as such, never as successful full-data archiving.

The collection command prints a uniquely named ZIP in Downloads. Provide that ZIP for review of coverage, required files and archive size before preparing the full-data release. Do not delete local fields or run `gh repo archive` at this stage. A later full-data upload and fresh-directory restoration test must still be completed.

## Reproducing the host checks

`python3 -B test_host.py` uses small synthetic local fixtures. It tests discovery, exclusions, hashes/CRC, cache invalidation, duplicate recognition, restart-document generation, metadata sealing and offline publication staging. No remote repository, full scientific dataset or zbook source directory is accessed by those fixtures.

All generated timestamps include UTC and Australia/Melbourne. Source scientific gates remain unchanged.
