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
