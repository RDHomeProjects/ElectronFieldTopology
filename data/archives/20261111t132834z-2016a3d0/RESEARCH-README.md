# Q3/Q4/Q7 fresh-field survey and detailed motion data

{"utc": "2026-11-11T13:28:34.076373+00:00", "melbourne": "2026-11-12T00:28:34.076373+11:00"}

Run `20261109t134425z-89d28344`; measured code commit `bae639dc700c5653cb4bfb2738608795b37da641`; configuration SHA-256 `425246008dad48bf3722a245f2ecbc70567208b1e7397fc7bca1baf6a1003090`.

## What was recorded
Native status: **complete_pending_review**. 18 stationary-preparation records and 15 motion/admission records; every failed/skipped case is retained. The compact Git record is `reports/s5-b/010-intermediate-q-survey/runs/20261109t134425z-89d28344`. Scientific assessment follows publication.

The study compares two fresh starts at each of Q3/Q4/Q7, uses the retained Q2 short control, and conditionally records strict stationary preparation, physical meshes97/121/145 at L23.04, fresh/warm starts, finest-grid dt0.02/0.01/0.005, crossed-axis motion and a169³/h0.16/L26.88 domain. Original criteria and early decisions remain in plan.json and campaign.json. Q1 remains parked.

| Rest ID | Outcome | Calls | Final force | Final maximum acceleration |
|---|---|---:|---:|---:|
|q2-reference|stationary|0|1.1542460483789047e-05|6.636497024101145e-05|
|q3-axial-coarse-fresh|stationary|2|7.456741350477546e-05|0.000738149854967357|
|q3-bent-coarse-fresh|preparation_unresolved|6|0.0003698130543172773|0.002240373067580353|
|q4-axial41-coarse-fresh|preparation_unresolved|6|0.0011594344536356488|0.006330411158048311|
|q4-axial22-coarse-fresh|topology_unresolved|1|0.25115458924998774|11.649766937638372|
|q7-axial-coarse-fresh|stationarity_unresolved|3|0.15114952263458575|4.987432760731952|
|q7-trefoil-coarse-fresh|topology_unresolved|2|0.1487381738687389|5.6447470012541805|
|q3-axial-medium-fresh|stationary|1|6.49098329766592e-05|0.0006786804238339941|
|q3-axial-medium-warm|stationary|2|9.318091212904314e-05|0.000673689185657545|
|q3-axial-fine-fresh|stationary|2|9.027288089489444e-05|0.0006613874156058099|
|q3-axial-fine-warm|stationary|1|9.460063192660284e-05|0.0007749056125761395|
|q3-axial-domain-warm|stationary|1|8.321395664562329e-05|0.0006204729269432818|
|q4-axial41-medium-fresh|stationary|2|6.35318860363358e-05|0.0005436435896968481|
|q4-axial22-medium-fresh|preparation_unresolved|6|0.00016979860357199805|0.0019882973631413434|
|q4-axial41-fine-fresh|preparation_unresolved|6|0.008571991096005866|0.07313172460333907|
|q4-axial41-fine-warm|preparation_unresolved|6|0.020581278620729518|0.17504570845989817|
|q7-axial-medium-fresh|preparation_unresolved|6|0.005293887226215454|0.04989205333805393|
|q7-trefoil-medium-fresh|preparation_unresolved|6|0.00017940288265448742|0.0035355805783470495|

| Motion/admission case | Outcome | Reached model time | Speed error % | Original shape error % | Maximum observed tail % |
|---|---|---:|---:|---:|---:|
|q2-reference-dt0.01|screen_pass|0.2|0.8449984|0.2096233|0.02745246|
|q3-axial-coarse-fresh-screen-dt0.01|screen_failed|0.2|2.347749|0.4311816|0.02384908|
|q3-axial-coarse-fresh-rest-dt0.01|screen_pass|0.2|not measured|0.0001137788|0.02704875|
|q3-axial-coarse-fresh-z-dt0.01|screen_failed|0.2|2.347803|0.4311816|0.02384908|
|q3-axial-medium-warm-rest-dt0.01|screen_pass|0.2|not measured|0.0001120595|0.02810055|
|q3-axial-medium-warm-z-dt0.01|screen_failed|0.2|1.770977|0.3115465|0.02487338|
|q3-axial-fine-warm-rest-dt0.01|screen_pass|0.2|not measured|0.0001191173|0.02848491|
|q3-axial-fine-warm-z-dt0.01|screen_failed|0.2|1.057322|0.2311195|0.02554531|
|q3-axial-fine-warm-z-dt0.02|screen_failed|0.2|1.057322|0.2311195|0.02554531|
|q3-axial-fine-warm-z-dt0.005|screen_failed|0.2|1.057322|0.2311195|0.02554531|
|q3-axial-fine-warm-x-dt0.01|screen_pass|0.2|0.8196939|0.2656546|0.02482385|
|q3-axial-domain-warm-z-dt0.01|screen_pass|0.5|0.9672171|0.1608156|0.01269756|
|q4-axial41-medium-fresh-screen-dt0.01|admission_rejected|not evolved|not measured|not measured|not measured|
|q4-axial41-medium-fresh-rest-dt0.01|admission_rejected|not evolved|not measured|not measured|not measured|
|q4-axial41-medium-fresh-z-dt0.01|admission_rejected|not evolved|not measured|not measured|not measured|

## Asset and restored-file guide
- `ARCHIVE.json`: master root/part inventory and restore-tool hash.
- `r001-manifest.json`: exact paths, byte sizes, modes and SHA-256 for every retained payload.
- `r001-part-*.tarpart`: ordered segments of one uncompressed tar stream, at most1GiB each; these are not separate ZIP files.
- `RESTORE.py`: the pinned archive restore/check tool.
- `RESEARCH-README.md`: this human-readable guide.
- Restored `sources/`: hash-pinned original Q2 field; `rest/`: every analytic/warm initial and native latest field with all optimizer histories.
- Restored `cases/`: admitted full n/v, physical config, segment initial/latest/final states, milestone snapshots, diagnostics and original gates.
- Restored `core/`: complete extracted polygons and both-target finite-invariant outcomes; seed labels are not final knot certificates.
- Restored `plan.json`, `campaign.json`, CSVs, SUMMARY.md, comparisons and followup: exact work allocation, outcomes and lineage.
- Restored `handover/`: executable source patch, pinned base, checksums and local instructions.

The arrays are float64 scientific data. Optional Float32 renderer outputs are rebuildable from the retained states and versioned profile. Model time and length are dimensionless; the neutral action has no electromagnetic-charge or quantum-spin observable. These files describe the actual tested finite boxes/windows.

## Restore without overwriting a working dataset
Clone the Git repository and use its committed archive catalog:
```bash
python3 scripts/workstation_archive.py restore --catalog data/archives/20261111t132834z-2016a3d0/CATALOG.json --destination "$HOME/EFT-restored/20261109t134425z-89d28344" --roots r001
```
The restored run is under `extra/r001/20261109t134425z-89d28344`. The tool verifies downloaded part hashes and every payload member. Native absolute paths remain as provenance; the S5-B-010 readers map them through the record ID without rewriting the records.

## Reproduce the calculation in a new run
```bash
git clone https://github.com/RDHomeProjects/ElectronFieldTopology.git ElectronFieldTopology-reproduction
cd ElectronFieldTopology-reproduction
git switch --detach bae639dc700c5653cb4bfb2738608795b37da641
uv sync --frozen --all-groups --python 3.12.14
new_id="$(python3 -c 'from datetime import datetime,timezone; import secrets; print(datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%Sz")+"-"+secrets.token_hex(4))')"
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 uv run --frozen --python 3.12.14 python -m electron_field_topology.sf_candidate_survey --config experiments/configs/s5-b/010-intermediate-q-survey/study.json --output "artifacts/s5-b/010-intermediate-q-survey/$new_id"
```
This is a new potentially multi-day simulation, with a new immutable record ID. It does not overwrite the archived run. Read the complete specification before changing the frozen matrix.

## Verify and analyse retained results
At the measured code commit, run `python3 scripts/check_candidate_survey.py --run RESTORED_RUN_PATH` to check source/lock, compact, checkpoint and curve seals without evolving anything. For numerical replay, run `uv run --frozen --python 3.12.14 python -m electron_field_topology.sf_candidate_replay --run RESTORED_RUN_PATH --output NEW_REPLAY_FOLDER`. This writes a separate receipt and shares the frozen instruments; it does not evolve fields. The compact tables are a starting point; use full fields for independent spatial/topology/trajectory analysis. The original script and source versions are named in each native manifest.

## Offline display
Use the original RUN.sh preview command after a completed run, or read full states with the versioned renderer tools. Open the resulting series.pvd in ParaView, Apply, choose Volume, select energy_density and reset the camera. Display sampling never changes the calculation.

No source files, historical results or older Releases are deleted by this archive. All payloads were uploaded and independently downloaded/hash verified before catalog registration.
