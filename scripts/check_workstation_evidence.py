"""Verify the retained workstation transfer offline, not its scientific claims."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "reports/s5-a/workstation-2026-11-01"
EXPECTED_SHA256 = "2ff8f15facc37b02736242926d1d43a2a20b3f7ed27bf5f28f2daf9f1cbe81f3"


def verify(archive, record=RECORD):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Original evidence.zip SHA-256 mismatch")
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or len(names) != 164:
            raise ValueError("Unexpected or duplicate archive entries")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError(f"Unsafe archive path: {name}")
        hashes = json.loads(bundle.read("evidence-hashes.json"))
        if set(hashes) != set(names) - {"evidence-hashes.json"}:
            raise ValueError("Archive hash manifest coverage mismatch")
        for name, expected in hashes.items():
            data = bundle.read(name)
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"Archive member hash mismatch: {name}")
            copy = record / "records" / name
            if copy.exists() and copy.read_bytes() != data:
                raise ValueError(f"Readable copy differs: {name}")
        results = sorted(n for n in names if n.startswith("cases/") and n.endswith("/result.json"))
        if len(results) != 11:
            raise ValueError("Expected eleven case results")
        summary = json.loads(bundle.read("summary.json"))
        for name in results:
            result = json.loads(bundle.read(name))
            case = name.split("/")[1]
            config = json.loads(bundle.read(f"configs/{case}.json"))
            if result["config"] != config:
                raise ValueError(f"Case configuration mismatch: {case}")
            stage = summary["stages"][case.rsplit("-", 1)[0]]
            if result["final"] != stage["final"]:
                raise ValueError(f"Summary endpoint mismatch: {case}")
        required = ["SUMMARY.md", "summary.json", "plan.json", "campaign.json"] + results
        for name in required:
            if not (record / "records" / name).is_file():
                raise ValueError(f"Missing readable record: {name}")
    return len(hashes), len(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=RECORD / "evidence.zip")
    args = parser.parse_args()
    try:
        members, cases = verify(args.archive)
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Workstation transfer verification failed: {error}\n")
    print(f"Workstation transfer verified: {members} hashed members, {cases} case results; no scientific acceptance implied.")
