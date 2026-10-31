"""Verify byte-exact staged publication; no scientific acceptance is implied."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
ledger = json.loads((root / "docs/pr36-staged-recovery.json").read_text())
seen = set()
count = 0
for stage in ledger["stages"]:
    for name, expected in stage["files"].items():
        assert name not in seen, f"Duplicate staged path: {name}"
        seen.add(name)
        if stage["stage"] > ledger["completed_stage"]:
            continue
        data = (root / name).read_bytes()
        actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        assert actual == expected, f"Original blob mismatch: {name}"
        count += 1
assert len(seen) == 191, "Original change-set coverage mismatch"
assert len(ledger["stages"]) == 10
print(f"Stage {ledger['completed_stage']}/10: {count}/191 original files verified byte-exact; no scientific acceptance implied.")
if ledger['completed_stage'] == 10:
    import subprocess
    bundle = ledger['source_bundle']
    path = root / bundle['path']
    data = path.read_bytes()
    assert len(data) == bundle['bytes'], 'Source bundle length mismatch'
    assert hashlib.sha256(data).hexdigest() == bundle['sha256'], 'Source bundle SHA-256 mismatch'
    heads = subprocess.check_output(['git', 'bundle', 'list-heads', str(path)], text=True)
    assert f"{ledger['source_commit']} HEAD" in heads, 'Original commit absent from bundle'
    subprocess.run(['git', 'bundle', 'verify', str(path)], check=True, capture_output=True)
    print('Exact original source commit retained in verified complete-history Git bundle.')
