# Matter Waves restart from the verified full-data archive

This guide belongs to the 24 November 2026 pause inventory
`20261124t103512z-15f7851c`. Full fields are release assets, not ordinary Git
files. The completion record under `docs/research/project-pause-20261124/archives/`
provides the release tag, verification receipt SHA256, source commit and cleanup
receipt. Keep that small record and this handover after cleanup.

## Retrieve and authenticate the restore tools

On the workstation, with Git, GitHub CLI and Python 3 available, copy the exact
release tag and upload-proof SHA256 from the committed completion record:

```bash
set -euo pipefail
tag='COPY_THE_RECORDED_RELEASE_TAG'
proof_sha256='COPY_THE_RECORDED_VERIFIED_UPLOAD_SHA256'
mkdir -p "$HOME/MatterWaves-RestoreTools"
cd "$HOME/MatterWaves-RestoreTools"
gh release download "$tag" --repo RDHomeProjects/ElectronFieldTopology \
  --pattern VERIFIED-UPLOAD.json --pattern MATTER-WAVES-ARCHIVE.json.gz \
  --pattern restore-kit.zip --pattern RESTORE.md
printf '%s  %s\n' "$proof_sha256" VERIFIED-UPLOAD.json | sha256sum -c -
python3 - <<'PY'
import hashlib,json
from pathlib import Path
proof=json.loads(Path('VERIFIED-UPLOAD.json').read_text())
for name in ['restore-kit.zip','MATTER-WAVES-ARCHIVE.json.gz']:
    expected=next(x['sha256'] for x in proof['metadata'] if x['name']==name)
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
print('Restore tools and manifest match the recorded upload proof')
PY
unzip -n restore-kit.zip -d tools
```

Use a new tools directory if files are already present. Do not replace existing
research data. GitHub CLI authentication stays on the local workstation.

## Restore the primary scientific restart

```bash
python3 tools/restore.py \
  --manifest MATTER-WAVES-ARCHIVE.json.gz --proof VERIFIED-UPLOAD.json \
  --destination "$HOME/MatterWaves-Restored-Q21" --mode restart
```

This downloads only parts needed for the primary code bundle and all 17 declared
checkpoint roles, together with their run identities, seals, source settings,
measurements and frozen handovers. It verifies every object in those parts, checks each restored file
hash and creates `code/numerical`. It restores both the native exact-CG endpoint
at iteration **665** and the separately retained best at **663**. Retain conjugacy
arrays, alpha, grid, box and gates when restarting; the endpoint is not stationary.
The pause package performs no optimizer or physical-time steps. Inspect the
retained run configuration and report before launching a new scientific campaign.

The numerical code is restored at its inventoried checkout HEAD, not silently
updated to main. Recreate its environment with its pinned `pyproject.toml` and
`uv.lock`; the original interpreter was CPython 3.12.14. Inspect the relevant run
handover for the required CPU/GPU extra and backend qualification. Reinstalling
CUDA/Python dependencies is a separate task; this archive does not claim to
preserve installed system drivers or packages.

## Restore the full inventory, or selected roots

```bash
python3 tools/restore.py \
  --manifest MATTER-WAVES-ARCHIVE.json.gz --proof VERIFIED-UPLOAD.json \
  --destination "$HOME/MatterWaves-Restored-All" --mode full
```

Full mode recreates all inventoried regular files under `roots/root-ID/` and
preserves all 24 repository bundles plus the pinned current-main bundle under
`bundles/`. `ORIGINAL-ROOTS.json` maps those safe destinations to original paths.
It does not write directly over `/home/rd` or follow/recreate runtime symlinks.
Allow at least 132 GiB free for the logical inventory and bounded staging, plus
space for source Git checkouts. Actual free-space admission is checked at runtime.

For a selected root, add `--root root-0011` (the numerical checkout); repeat the
option for more roots. Read the manifest root list first. Full mode retains
bundles so additional original checkouts can be reconstructed with:

```bash
git clone --no-checkout /absolute/path/to/bundles/repository-NNN.bundle new-checkout
git -C new-checkout checkout --detach COPY_THE_RECORDED_HEAD
```

`git` entries in the manifest map bundle names, original repository paths, HEADs
and refs. Every repository bundle was made with `--all HEAD` and verified before
upload. Git bundles preserve committed histories and refs, not reflogs, hooks,
credentials, ignored environments or arbitrary Git configuration. All inventoried
regular files, including untracked science data, are independently stored as
content objects. The 12 inventoried runtime symlinks are documented but not
recreated; rebuild those environments instead.

Restoration is resumable with identical arguments. Existing matching files are
verified and retained; conflicting files stop restoration. The tool downloads one
part at a time and deletes only its own temporary staging directories. Check
`RESTORE-COMPLETE.json` before using a restored result. Download verification
establishes byte preservation, not scientific validity or long-term stability.
