# Workstation archive preparation controls

Recorded: UTC 2026-11-04T01:55:33.804578+00:00; Australia/Melbourne 2026-11-04T12:55:33.804578+11:00.
Source baseline: `fe7ce72408b2d1ad86a41a3b97ecc8482a746e25`. Study: s0-003. No workstation data or live GitHub mutation
was used in these controls. This report records software preparation only.

Twelve standard-library synthetic controls cover read-only inventory, Git-ignored
field capture, full multi-part remote roundtrip, modes/empty directories, staged and
unstaged work, unreachable Git objects, linked-worktree restoration, changed-source
rejection, credential-name and symlink blockers, interrupted upload resume, idempotence,
remote corruption/receipt invalidation, path traversal and overwrite rejection.
The remote is a local fake; real GitHub CLI transfer remains a workstation operation.

The canonical current plan remains administrative archiving before s5-b-005. Existing
scientific arrays, code/configurations, reports and gates are unchanged. The current
tool has no command to delete source folders.
