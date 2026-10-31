"""Timing controls: process isolation and refusal to compare different work."""
import copy
import json
import subprocess
import sys

from electron_field_topology.sf_timing import compare


def test_timing_uses_fresh_thread_settings_and_compares_matching_work(tmp_path):
    out = tmp_path / "timing"
    subprocess.run([sys.executable, "-m", "electron_field_topology.sf_timing",
                    "--grids", "33", "--threads", "1", "2", "--steps", "1",
                    "--repeats", "1", "--output", str(out)], check=True)
    report = json.loads((out / "timing.json").read_text())
    assert [r["thread_environment"]["OMP_NUM_THREADS"] for r in report["cases"]] == ["1", "2"]
    for row in report["cases"]:
        assert row["short_solve"]["results"][0]["iterations"] == 1
        assert row["worker_peak_rss_mib"] > 0
    assert all(c["comparable"] for c in compare(report, report))
    changed = copy.deepcopy(report)
    changed["cases"][0]["short_solve"]["results"][0]["evaluations"] += 1
    assert not compare(report, changed)[0]["comparable"]
    changed = copy.deepcopy(report)
    changed["source_sha256"]["different"] = "source"
    assert not any(c["comparable"] for c in compare(report, changed))
    # Existing output is protected, including a second invocation with a typo.
    rerun = subprocess.run([sys.executable, "-m", "electron_field_topology.sf_timing",
                            "--output", str(out)], capture_output=True)
    assert rerun.returncode != 0
    assert json.loads((out / "timing.json").read_text()) == report
