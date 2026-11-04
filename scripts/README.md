# scripts

Current helper: check_docs.py checks local Markdown link targets, fenced blocks and required documentation. It does not check remote URLs, physical correctness or numerical results.

See [the root README](../README.md) for the documentation index.

For bounded local CPU timing, use the importable `electron_field_topology.sf_timing`
module. See [the timing guide](../docs/static-timing.md) for quick and target runs.

## Project records

`python3 scripts/project_records.py render` derives navigation from the project register. `python3 scripts/project_records.py check` checks status/plan consistency, frozen reports, ownership and new record naming. During this administration migration, add `--migration` to verify every non-administrative baseline byte and file mode. These checks do not validate physical results.

## Workstation archives

`workstation_archive.py` inventories, packs, publishes/download-verifies release assets, restores selected roots and prepares cleanup reviews. It never deletes a source. See [the storage policy](../docs/governance/workstation-archives.md). `test_workstation_archive.py` uses synthetic data and a fake remote.
