# Matter Waves / Electron Field Topology — pause and restart record

Generated UTC 2026-11-24T10:54:14.263046+00:00; Melbourne 2026-11-24T21:54:14.263046+11:00.

Inventory ID: `20261124t103512z-15f7851c`. Inventory status: **inventory_complete_review_required**.

**Archive state: inventory and restart documentation only. Full scientific data have not been uploaded by this operation. No pause tag/release or repository read-only archive has been created.**

## Scientific stopping point

Q21 remains unresolved. CG is the primary baseline; best and final remain separate. All measured boundary/representation gates pass, stationarity fails. No physical-time evolution or coupled-grid solve has been performed.

Latest assessed run: `20261124t073157z-b6ad806d`. Its source CPU run is `20261123t130300z-db9ba00c`.

Primary chronological continuation: final CG endpoint, native iteration **665**, force 0.00190405907, maximum acceleration 0.02499893657.

Logical numerical-checkout-relative path: `artifacts/q21-footprint-minimizer/20261124t073157z-b6ad806d/cases/exact-cg/endpoint.npz`.

SHA256: `959deb6868a8736f5e002ffa16ec49b00f01870224fcf5be5c3c131b8baf9a5d`.

The best CG checkpoint at native iteration 663 is retained separately and must not be substituted silently. The descent endpoint, CPU 177³/193³ source endpoints, Q2 reference, optimizer memories and historical fields are also retention candidates. Existing Q2–Q32 results remain candidate-specific; unresolved endpoints are not physical exclusions.

The gate limits remain relative force 1e-4 and maximum acceleration 1e-3, together with inherited representation, charge, unit-vector and boundary checks. All latest observed representation/boundary gates passed; stationarity did not. No physical-time evolution or coupled-grid evolution was conducted.

## Scope of this inventory

85573 regular files; 129.558 GiB of logical file content; 100.541 GiB after exact-content deduplication, before packaging overhead. Hashing does not remove duplicates.

ROOTS.json records every selected file/directory. FILES.jsonl.gz and FILES.csv.gz contain original paths, relative mappings, sizes, SHA256 and ZIP/NPZ CRC outcomes. Discovery searches for project-name prefixes under the home directory to a declared depth; explicitly supplied --root locations extend that scope. It does not prove that arbitrarily renamed or externally mounted datasets are covered.

EXCLUSIONS.json, SYMLINKS.json and UNASSIGNED-DOWNLOADS.json must be reviewed before selecting the final archive. Symlinks are not followed automatically. Runtime environments and Git internals are excluded from data hashing; recreate environments from locks and preserve Git history separately. Generic evidence ZIPs in Downloads are listed for assignment, not assumed to belong to this project.

FIELD-REFERENCES.json checks standard on-disk FIELD-MANIFEST.json declarations. A missing individual file may be inside an existing archive or deliberately retired; no conclusion of data loss is made automatically. Nested archive field declarations are not exhaustively expanded by this inventory.

## Required recent checkpoints

| Role | Availability | Example path |
|---|---|---|
| latest/cases/exact-cg/best.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-footprint-minimizer/20261124t073157z-b6ad806d/cases/exact-cg/best.npz |
| latest/cases/exact-cg/endpoint.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-footprint-minimizer/20261124t073157z-b6ad806d/cases/exact-cg/endpoint.npz |
| latest/cases/exact-cg/restart-0.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-footprint-minimizer/20261124t073157z-b6ad806d/cases/exact-cg/restart-0.npz |
| latest/cases/exact-cg/restart-1.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-footprint-minimizer/20261124t073157z-b6ad806d/cases/exact-cg/restart-1.npz |
| latest/cases/sobolev-descent/best.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-footprint-minimizer/20261124t073157z-b6ad806d/cases/sobolev-descent/best.npz |
| latest/cases/sobolev-descent/endpoint.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-footprint-minimizer/20261124t073157z-b6ad806d/cases/sobolev-descent/endpoint.npz |
| latest/cases/sobolev-descent/restart-0.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-footprint-minimizer/20261124t073157z-b6ad806d/cases/sobolev-descent/restart-0.npz |
| latest/cases/sobolev-descent/restart-1.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-footprint-minimizer/20261124t073157z-b6ad806d/cases/sobolev-descent/restart-1.npz |
| prior-cpu/cases/cpu-177/best-00079.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-criteria-audit-cpu-resolution/20261123t130300z-db9ba00c/cases/cpu-177/best-00079.npz |
| prior-cpu/cases/cpu-177/endpoint.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-criteria-audit-cpu-resolution/20261123t130300z-db9ba00c/cases/cpu-177/endpoint.npz |
| prior-cpu/cases/cpu-177/restart-0.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-criteria-audit-cpu-resolution/20261123t130300z-db9ba00c/cases/cpu-177/restart-0.npz |
| prior-cpu/cases/cpu-177/restart-1.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-criteria-audit-cpu-resolution/20261123t130300z-db9ba00c/cases/cpu-177/restart-1.npz |
| prior-cpu/cases/cpu-193/best-00080.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-criteria-audit-cpu-resolution/20261123t130300z-db9ba00c/cases/cpu-193/best-00080.npz |
| prior-cpu/cases/cpu-193/endpoint.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-criteria-audit-cpu-resolution/20261123t130300z-db9ba00c/cases/cpu-193/endpoint.npz |
| prior-cpu/cases/cpu-193/restart-0.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-criteria-audit-cpu-resolution/20261123t130300z-db9ba00c/cases/cpu-193/restart-0.npz |
| prior-cpu/cases/cpu-193/restart-1.npz | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/q21-criteria-audit-cpu-resolution/20261123t130300z-db9ba00c/cases/cpu-193/restart-1.npz |
| q2-reference | present_at_expected_path | /home/rd/ElectronFieldTopology-adaptive-q-screen-20261117/artifacts/adaptive-q17-q32-screen/20261117t133953z-d6617788/sources/q2-reference.npz |

## Code and environment recovery

REPOSITORIES.json records all discovered repository heads, branches, refs, worktree status and sanitized origin URLs. The working numerical checkout need not be on the latest main commit. Before considering the pause archive complete, capture local-only refs in Git bundles and preserve dirty/untracked project files identified by this inventory. A source tag alone does not preserve ignored artifacts or commits available only locally.

Known tested numerical runtime: Python 3.12.14, float64; NVIDIA RTX 2080 Super Max-Q; CuPy 14.2.0 at the latest qualification. CPU-only operation remains possible. Restore the recorded pyproject.toml/uv.lock and numerical-source hashes; do not upgrade dependencies as part of a continuation by accident. Current launcher/OS/driver observations are in ENVIRONMENT.json. Do not copy or publish account credentials to recreate the environment.

## Complete the archive before cleanup

1. Review every discovery exclusion, external symlink, generic download and missing field declaration. Add actual scientific paths with --root and rerun inventory as needed.
2. Record this document and the inventory metadata through the separate publication checkout. Preserve the known assessment supplied alongside it.
3. Create source/history snapshots and full-data release assets, with a path-restoration map and per-file hashes. The next packaging step must consume the inventory rather than guessing from directory names.
4. Upload from the zbook, download the assets into a fresh directory, reconstruct them and verify every retained file. Confirm a selected NPZ loads and matches its declared optimizer state without running relaxation.
5. Record the final pause commit, tag, release URL and restore-verification receipt in an additive archive-completion record. Retain an independent backup. Only then consider cleanup or optionally making the GitHub repository read-only.

No local fields are safe to delete merely because this inventory documentation is merged. Archive completion and restore verification are separate, pending steps.

## Resume later

1. Read the pause record and final archive-completion receipt before selecting a source. Unarchive the repository first if it was made read-only.
2. Obtain the tagged source and any Git bundles; restore full data using the stored path map. Verify both asset and per-file hashes.
3. Recreate the pinned environment and qualify the selected CPU/GPU backend against the original discrete energy and gradient. Absolute paths and old .git run pointers may need reconstruction; do not invoke an old completed-run resume command blindly.
4. Use the declared final CG native-665 state for chronological continuation. Keep native-663 best, the descent arm and incoming CPU endpoints separately labelled. The intended next study was a bounded noise-aware CG control plus read-only coarse-exterior reconstruction tests before any composite-grid evolution.
5. Compare restored source measurements with the sealed record before authorizing new optimizer or physical-time work.

This pause procedure runs no scientific simulation and changes no scientific gates.
