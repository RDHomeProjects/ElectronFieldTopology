# Restore the final cleanup snapshot

The original 69-part archive remains at tag
`pause-20261124-15f7851c-339430fc`. The final cleanup record under
`docs/research/project-pause-20261124/residual-cleanup/` supplies the supplemental
release tag and SHA256 of `VERIFIED-SUPPLEMENT.json`. The additional manifest maps
original folders and records which bytes live in the original or supplemental
archive. Rebuildable environments and bytecode were intentionally omitted.

## Download the restore tools and manifests

Use Git, GitHub CLI and Python 3 on the local workstation. Choose a fresh tools
folder and copy the exact tag/proof hash from the committed cleanup record.

```bash
set -euo pipefail
supplement_tag='COPY_THE_RECORDED_SUPPLEMENTAL_TAG'
proof_sha256='COPY_THE_RECORDED_VERIFIED_SUPPLEMENT_SHA256'
mkdir -p "$HOME/MatterWaves-RestoreTools-Final"
cd "$HOME/MatterWaves-RestoreTools-Final"
gh release download "$supplement_tag" --repo RDHomeProjects/ElectronFieldTopology \
  --pattern VERIFIED-SUPPLEMENT.json --pattern RESIDUAL-MANIFEST.json.gz \
  --pattern restore-kit.zip --pattern RESTORE.md
gh release download pause-20261124-15f7851c-339430fc \
  --repo RDHomeProjects/ElectronFieldTopology \
  --pattern MATTER-WAVES-ARCHIVE.json.gz
printf '%s  %s\n' "$proof_sha256" VERIFIED-SUPPLEMENT.json | sha256sum -c -
python3 - <<'PY'
import hashlib,json
from pathlib import Path
proof=json.loads(Path('VERIFIED-SUPPLEMENT.json').read_text())
for name in ['RESIDUAL-MANIFEST.json.gz','restore-kit.zip']:
    expected=next(x['sha256'] for x in proof['metadata'] if x['name']==name)
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
assert hashlib.sha256(Path('MATTER-WAVES-ARCHIVE.json.gz').read_bytes()).hexdigest()==proof['base_manifest_sha256']
print('Restore manifests and tools match the recorded proof')
PY
unzip -n restore-kit.zip -d tools
```

## List and restore selected folders

```bash
python3 tools/restore.py --manifest RESIDUAL-MANIFEST.json.gz \
  --proof VERIFIED-SUPPLEMENT.json --base-manifest MATTER-WAVES-ARCHIVE.json.gz \
  --list

python3 tools/restore.py --manifest RESIDUAL-MANIFEST.json.gz \
  --proof VERIFIED-SUPPLEMENT.json --base-manifest MATTER-WAVES-ARCHIVE.json.gz \
  --destination "$HOME/MatterWaves-Restored-Residual" --root root-0001
```

Replace the example root ID with the wanted entry from the listing. Repeat
`--root` for multiple folders, or omit it to restore all eligible roots. Roots
labelled retained/unarchived were never deleted and are not represented as fully
recoverable supplemental roots.

The tool fetches only needed parts, validates the complete downloaded part and
its members, reconstructs chunked files, checks every whole-file SHA256, restores
file permissions and recreates captured internal links in the new location.
Data appear under `roots/root-ID`; `ORIGINAL-ROOTS.json` records original paths.
It never writes over the original home folders. Interrupted restores can resume
with the same arguments; conflicting completed files stop the restore.

Git folders include their captured metadata and an independent bundle under
`bundles/`. For a clean source checkout, prefer:

```bash
git clone --no-checkout /absolute/path/to/restored/bundles/root-ID-NNN.bundle new-checkout
git -C new-checkout checkout --detach COPY_THE_RECORDED_HEAD
```

Use the manifest's `git` entries for the exact bundle and HEAD. Raw Git metadata
also preserve the original index, locally stored unreachable objects and settings;
external object-alternate paths may need adjustment if reconstructing a raw
checkout. The independent bundle preserves the captured refs/HEAD without those
external paths. No credential-bearing local configuration was uploaded; roots
containing such configuration were retained on the workstation instead.

Recreate environments from the preserved locks and runtime records. The tested
numerical interpreter was CPython 3.12.14. Check the original pause restart guide
before selecting Q21 native-665 versus the separately retained native-663 best.
Restoring files does not run or certify new scientific analysis.
