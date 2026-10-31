# scripts

Current helper: check_docs.py checks local Markdown link targets, fenced blocks and required documentation. It does not check remote URLs, physical correctness or numerical results.

See [the root README](../README.md) for the documentation index.
# Active literature checkpoint

The collector is capped at level 3 and defaults to a budget of 1,000 non-seed metadata records per invocation. Resume the existing output directory to preserve known nodes/edges; a new acquisition supplements rather than replaces earlier corpora. Level 4 is rejected, and references of depth-3 records are not requested. No network collection runs in CI.

```bash
python scripts/collect_literature.py --depth 3 --max-new-records 1000
python scripts/export_literature_checkpoint.py --graph artifacts/literature-depth4/graph.json --output artifacts/literature-publication
```

Export first to a separate directory; inspect/reconcile before updating a published snapshot. See [the active protocol](../docs/literature/depth4/PROTOCOL.md) and [review progress](../docs/literature/depth4/LEVEL3_REVIEW.md). Metadata is not a completed applicability review; S4-B remains paused.
