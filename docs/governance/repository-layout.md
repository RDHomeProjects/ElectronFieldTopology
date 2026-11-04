# Repository layout and recording policy

Recorded: UTC 2026-11-04T01:00:23.956083+00:00; Australia/Melbourne 2026-11-04T12:00:23.956083+11:00.
Baseline: `8cffc20fad3017373541b2b165eaf51215b50460` (merged PR54). Scope: documentation and administration only.

## Audit and corrective design

The baseline contains 1212 tracked files. Nineteen report roots mix stage
names, dates, implementation labels, preparation work and campaigns. STATUS and the
development plan still describe the completed diagnostic as the next run; several
dated sections compete as current priorities. The reports themselves retain valid
provenance. Renaming those paths indiscriminately would risk embedded paths, replay
scripts, checksum ledgers, historical URLs and downloaded handoffs.

This correction therefore changes the authoritative navigation and recording rules,
not the location or bytes of existing evidence. Stage indexes and stable study IDs
form the canonical browsing layout. Pre-policy report folders are frozen compatibility
locations, fully mapped in [the legacy catalog](../project/legacy-locations.md).
They are not to receive new campaigns. This deliberately does not make the old
physical folder list disappear: preserving published paths takes priority over a
cosmetic rename. No symlinks, redirects, history rewriting, file deletion or evidence
duplication is used to disguise a path change.

## Folder responsibilities

| Path | Purpose and ownership |
|---|---|
| `docs/project/roadmap.json` | Sole source for current study state, scientific gate, dependencies, priorities and evidence links |
| `docs/STATUS.md` | Generated current capability and next task; no dated append-only current sections |
| `docs/06-development-plan.md` | Generated milestone sequence, dependencies and stage scope |
| `docs/plans/<stage>/<nnn>-<study>.md` | Generated current study contract, exit evidence and links to source specifications |
| `docs/models/` | Scientific equations, conventions and model definitions; unchanged by this migration |
| `docs/decisions/` | Numbered ADRs; retain superseded decisions and record replacements |
| `docs/literature/` | Existing main bibliography, source register and applicability reviews |
| `docs/governance/` | Folder, naming, publication and maintenance rules |
| `docs/history/layout-20261104/` | Exact pre-reconciliation navigation documents with original-path/hash manifest |
| `reports/<stage>/INDEX.md` | Canonical stage navigation; existing scientific README files are left untouched |
| `reports/<stage>/<nnn>-<study>/README.md` | Generated study evidence catalog |
| `reports/<stage>/<nnn>-<study>/preparation/<record-id>/` | Measured tool/control/preflight results, explicitly not production |
| `reports/<stage>/<nnn>-<study>/runs/<record-id>/` | Immutable compact numerical records and initial scientific assessment |
| `reports/<stage>/<nnn>-<study>/assessments/<record-id>/` | New dated analysis or correction referencing one or more immutable runs |
| `experiments/configs/` | Existing versioned numerical inputs; future new studies may use matching stage/study subfolders |
| `src/`, `tests/`, `scripts/` | Existing reusable science, tests and small administrative tools; no numerical changes here |
| Local `artifacts/` | Full fields, checkpoints, raw run folders and display exports; never relocate automatically |

The established S1-A through S4-C stages are retained. S5-A groups static neutral
references; S5-B explicitly names the neutral physical-time track; S5-C groups
charged-theory feasibility without claiming it is accepted. S6 and S7 remain conditional.
These are administrative subdivisions of the existing plan, not new physical milestones.

## Naming rules

Stage slugs are lower-case (`s5-b`). A study ID is permanent and sequential within
its stage (`s5-b-005`), with a folder `005-boost-initialization`. Do not recycle a
number after rejection or cancellation. A short slug describes a scientific question,
not a date, workstation, PR number or temporary execution status.

New record IDs use UTC `yyyymmddthhmmssz-xxxxxxxx`, where the suffix is eight random
hexadecimal characters generated before execution and retained on resume. Example
format: `20261104t003000z-1a2b3c4d` (illustrative, not an executed run). Store UTC and
Australia/Melbourne ISO-8601 timestamps in record metadata and every analysis/report.
Use a fresh ID for a genuinely new run or assessment, not for a restart of one run.
Existing names with offsets, PIDs or longer timestamps remain grandfathered verbatim.

Use lower-case kebab-case for new directories and descriptive files. Reserved names
`README.md`, `INDEX.md`, `ASSESSMENT.md`, `SHA256SUMS` and established instrument
filenames are exceptions. CSVs must use LF line endings. Paths are repository-relative
POSIX paths; local absolute field paths belong in provenance with explicit portability
limitations, not in the project navigation. Existing filenames are not normalized.

## Plan and status updates

Change the register in the same PR as a preparation, publication, assessment or
priority decision. Record IDs, state, separate scientific gate, requirement IDs,
dependencies, exact next action, exit evidence and report/specification links. Then:

```bash
python3 scripts/project_records.py render
python3 scripts/project_records.py check
python3 scripts/check_docs.py
```

The renderer creates navigation only; never edit its generated outputs by hand.
Study workflow states are planned/prepared/running/recorded/assessed/deferred. Gates
are open/bounded/blocked/not-applicable. An assessed negative result is valid evidence.
No generator infers acceptance from a green CI check or an inactive runner. New
priorities replace the current register entry; historical rationale belongs in an ADR,
commit history or dated assessment, not another current-plan paragraph.

## Recording a new result or analysis

Before computation, register the stable study and current plan. Retain model/requirements,
source and configuration hashes, independent controls, tolerances, boundaries, precision,
hardware/environment, seed and exact command. Renderer profiles remain separate from
scientific inputs. A preparation report is not a production result.

Each new record folder contains `record.json`, `README.md` and `SHA256SUMS`, with
compact evidence and analysis as appropriate. Use [the run template](../templates/run-record.json).
Register its README or assessment path in the owning study. The record declares its
study/record IDs, role, UTC/Melbourne timestamps, source commit, outcome, associated
config/evidence hashes and field-retention location. Hash all immutable payload files;
exclude the checksum file itself. Record physical failures, skipped gates and limits.

Re-analysis goes in a new `assessments/<record-id>/` folder with references to exact
run IDs and input hashes. A later correction records `supersedes`, reason and scope;
do not overwrite earlier assessment prose, numeric tables, scripts or hashes. Current
navigation may point to the latest assessment while retaining the older links. PR
merge is publication and software validation, not scientific peer review or acceptance.

## Publication and essential checks

Use one focused task branch and reviewable PR. PR text states study IDs, administrative
or scientific scope, findings/negative findings, validation and remaining limits.
Pure administrative changes run the standard-library layout/link/provenance checks;
do not launch simulation matrices for moved navigation text. Existing required hosted
checks are respected; this change adds a cheap step to documentation CI and does not
alter numerical workflows or bypass required checks. Scientific changes retain their
appropriate independent controls and tests.

GitHub interaction remains on the maintainer's workstation. The supplied installer
uses a separate fresh clone and branch, creates a complete-history Git bundle before
applying, verifies the pinned baseline, stages only the administrative patch and runs
checks. A repeated install verifies the existing exact result without reapplying or
discarding local edits. Unknown destinations, changed packages or protected bytes
stop with a diagnostic. No push, commit, PR, merge or physical calculation is performed
by installation; explicit publish/merge commands are separate.

## Preservation, rollback and future migration

`layout-baseline.json` inventories every baseline path, SHA-256, Git blob, size and
mode. The migration checker verifies all non-administrative baseline files; normal CI
continues to freeze pre-policy reports and validate navigation/record naming. PR/base
comparisons also reject rewriting published canonical record payloads or their hashes;
append a superseding assessment instead. The
archive manifest authenticates exact earlier administrative documents, whose old
relative links refer to their recorded original locations. Compatibility heading
anchors preserve the former current-plan section URLs on the rewritten live pages.

No source code, tests, physical configurations, dependency locks, report payloads,
evidence archives, report-local scripts or published paths are renamed or edited.
Local artifacts and existing worktrees are not touched. To roll back after publication,
use a reviewed `git revert` PR. To recover the pre-change repository, clone the saved
bundle into a different directory; never use a destructive reset on a working run.

A future physical migration needs an explicit path map, complete consumer/link audit,
hash and mode equivalence checks, compatibility strategy tested on GitHub as well as
local replay, and a separate decision. Moving files now with symlinks is rejected:
GitHub web/raw URLs do not provide a general server-side redirect through a local
filesystem symlink. A fresh clone plus an additive administrative patch gives the
strongest isolation for this correction; an existing checkout or worktree provides
less protection from unrelated untracked work and running artifact paths.

## Temporary workstation storage

Follow [the archive and restore policy](workstation-archives.md). Full scientific data is archived in verified release assets with a compact Git catalog before local copies become disposable. Published report paths and bytes remain unchanged.

## Current summary maintenance

UTC: 2026-11-04T13:35:35.703463+00:00; Australia/Melbourne: 2026-11-05T00:35:35.703463+11:00.

The register's `current` object identifies the latest assessed study, measured summary and outstanding limits. The first `priority` entry supplies the next task. The renderer uses those fields for status, roadmap, report navigation and the README Current capability section; its introduction, development and licensing sections are preserved. Update these fields with an assessment so an older hard-coded next-task paragraph cannot compete with the current plan.
