# Workstation storage and verified GitHub archives

Recorded: UTC 2026-11-04T01:55:33.804578+00:00; Australia/Melbourne 2026-11-04T12:55:33.804578+11:00.
Study: s0-003. This is archival tooling/preparation, not a completed workstation upload.

The maintainer's 4 November 2026 12:38 AEDT size listing shows about 33.2 GiB across
Q22, low-Q motion and Q18 workspaces. Allocation counts include environments and Git;
the metadata inventory measures which actual files need archiving. Download packages
are comparatively small. Compact evidence ZIPs are not full scientific field archives.

## Storage responsibilities

Source, configurations, plans, compact results and archive catalogs remain in Git.
Large scientific files and complete workspace snapshots are GitHub Release assets.
The workstation is a temporary compute/cache location. One active checkout and only
the datasets needed for current work are retained after validated archival/cleanup.
Git clone alone does not fetch release data; restoration uses a versioned catalog.

GitHub's [release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
sets a per-asset limit under 2 GiB. The tool uses at most 1 GiB pieces, one root at a
time. It does not use expiring Actions artifacts or add bulk arrays to ordinary Git.
LFS remains an alternative when file-level binary versioning is needed; its storage
and download quotas must be assessed separately. No paid service is enabled here.

## Inventory and snapshot scope

Select immediate `~/ElectronFieldTopology*` and `~/Downloads/ElectronFieldTopology*`
paths, matching the maintainer's listing. Additional consolidated project/cache paths
can be selected explicitly with --include; they restore below extra/<root-id>/<name>. A new work area defaults to `~/EFT-archive-work`,
outside those sources. Other home/download files and third-party PDFs are not selected.
Inventory only reads metadata, Git refs/status and object IDs; no complete field hash
or upload happens at that stage. Git optional locks are disabled so reads do not refresh
source indexes. The report lists logical sizes, field-file counts, omissions and blockers.

All regular selected files, including Git-ignored `artifacts/`, handoff archives,
logs, figures and uncommitted working files, enter lossless tar streams. Source
relative names, file modes, sizes, nanosecond modification times and SHA-256 values
are retained. ZIP/NPZ bytes are not recompressed or re-solved. Empty directories are
restored. This inventories the currently surviving files; it cannot recover historical
fields that were already lost and never archived.

Git metadata is represented by complete object packs, including unreachable objects,
refs, HEAD, raw index/split-index state and a reflog text record. Working files are
separately archived. Linked worktrees restore as independent Git stores with the same
objects/refs/HEAD/index; local `.git/config`, credentials and hooks are not published.
Python environments and the specifically named caches listed by the tool are rebuildable
exclusions, documented for every root. They are not silently classified as scientific data.

Symlinks, non-regular files, unreadable paths and credential/private-key-like filenames
are actual inventory blockers. They require accounting before public upload; the tool
does not follow a link to an unselected target or silently discard a unique field.

## Archive, resume and verification

Each inventory gets a stable UTC/random archive ID. Archive creation refuses changed
source metadata/Git state, hashes every original regular file, writes per-root tarparts,
and validates every locally packed member against its manifest. Part boundaries may
fall inside a field file; restore concatenates them as a stream. Peak staging is roughly
the largest retained root plus 2 GiB, rather than a second copy of all roots at once.

The workstation CLI creates a draft release on a pinned source tag target, uploads
assets without `--clobber`, downloads them again and validates each tar member hash.
Existing identical assets are reused on resume; different same-name assets stop.
Generated staging parts are removed only after remote verification. Incomplete staging
is rebuilt only while original input bytes remain accounted for. No original path is
deleted or moved. After all roots, a master index and the exact restore tool are
uploaded; the release is published and verified again against the final catalog.

The background wrapper records PID and Linux process birth identity, status, progress,
logs and exit result. Heartbeats occur every 30 seconds. A cooperative stop is checked
at file/asset boundaries; a single large file or in-flight transfer may take time to
finish. Resume uses the same inventory/ID; no arbitrary overall runtime cap applies.

## Git catalog and restoration

`CATALOG.json` anchors the repository/release tag, master-index SHA-256, restore-tool
SHA-256 and root/file/byte counts. `VERIFIED.json` binds successful downloads to that
catalog. The registration command copies these compact records into
`data/archives/<archive-id>/` with a readable root map. They must be committed before
local cleanup. No full field is copied into the Git tree.

Restore requires a catalog and a new empty destination. Every remote part and file is
checked while streaming into original relative file locations, with Git graph/index
reconstruction. Root IDs allow one dataset to be fetched without restoring everything.
Recorded historical absolute paths are not edited; analysis tools must receive an
explicit restored source root. Do not run archived scripts or hooks merely because
they were restored. Local credentials/environments are configured separately.

## Cleanup boundary

The tooling has no source-delete command. `cleanup-plan` freshly downloads/verifies
the remote payload and compares the current source inventory/Git state. Changed roots
are marked KEEP_SOURCE_CHANGED. A failed verification invalidates the previous active
receipt. The review lists archived/unchanged candidates and rebuildable exclusions;
the maintainer chooses the single checkout and active data cache to keep. Exact removal
commands follow review of those actual paths and the committed catalog, not the size
listing alone. A future run is not complete as an archive until its full selected data
and restore metadata are remotely verified.

No equations, numerical tolerances, existing reports, source fields or acceptance
decisions are changed by this administrative stage. AI-assisted tooling; validation
uses synthetic fixtures and a simulated remote, not a new scientific computation.
