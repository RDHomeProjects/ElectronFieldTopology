"""Publish a partial, abstract-free supplement without replacing earlier corpora."""
import argparse
from collections import Counter, deque
import gzip
import hashlib
import json
from pathlib import Path


def export(graph_path, output):
    graph = json.loads(Path(graph_path).read_text())
    source_nodes = graph['nodes']
    edges = sorted({(key, target.rsplit('/', 1)[-1])
                    for key, node in source_nodes.items() if node['depth'] < 3
                    for target in node.get('referenced_works', [])})
    adjacency = {}
    parents = {}
    for source, target in edges:
        adjacency.setdefault(source, []).append(target)
        parents.setdefault(target, []).append(source)
    depths = {key: 0 for key in graph['seeds'].values() if key}
    queue = deque(depths)
    while queue:
        source = queue.popleft()
        if depths[source] >= 3:
            continue
        for target in adjacency.get(source, []):
            if target not in depths:
                depths[target] = depths[source] + 1
                queue.append(target)
    edges = [(a, b) for a, b in edges if a in depths and b in depths and depths[a] < 3]
    works = {}
    for key, depth in sorted(depths.items()):
        original = source_nodes.get(key, {})
        works[key] = {
            **{k: original.get(k) for k in ('title', 'doi', 'publication_year', 'type')},
            'depth': depth,
            'parents': sorted(parents.get(key, [])),
            'metadata_status': 'retrieved' if original else 'pending',
            'review_status': 'unreviewed; consult applicability.json for separately assessed records',
            'provenance': graph.get('provenance', {}).get(key),
        }
    snapshot = {'scope': 'partial acquisition supplement, not the earlier larger checkpoint',
                'max_depth': 3, 'seeds': graph['seeds'], 'works': works, 'edges': edges,
                'failures': graph['failures'], 'levels': graph['levels']}
    raw = (json.dumps(snapshot, sort_keys=True, separators=(',', ':')) + '\n').encode()
    packed = gzip.compress(raw, mtime=0)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'checkpoint-supplement.json.gz').write_bytes(packed)
    manifest = {
        'date': '2026-10-31', 'provider': 'OpenAlex', 'kind': snapshot['scope'],
        'baseline_commit': 'ae0a1908b5081d4fe24948a5892a76d0220bd4d0',
        'seed_sha256': graph['seed_sha256'], 'max_depth': 3, 'level4': 'deferred',
        'level3_review_complete': False, 's4b': 'paused',
        'snapshot': 'checkpoint-supplement.json.gz',
        'sha256': hashlib.sha256(packed).hexdigest(),
        'uncompressed_sha256': hashlib.sha256(raw).hexdigest(),
        'metadata_records': len(source_nodes), 'encountered_work_ids': len(works),
        'edges': len(edges), 'depth_counts': dict(sorted(Counter(depths.values()).items())),
        'unresolved_seeds': [k for k, v in graph['seeds'].items() if not v],
        'acquisition_complete': False, 'printed_bibliography_coverage': 'not established',
        'gap': 'HTTP 429 on two seed title searches and final two level-1 batches; deeper metadata not acquired in this run',
        'historical_checkpoint': {
            'status': 'previously reported; bytes not located/recounted in this continuation; preserve and reconcile',
            'reported_ids': 113295, 'reported_metadata_records': 93657,
            'reported_edges': 243005, 'reported_queued_ids': 19487,
            'reported_unresolved': 151,
        },
        'reproduce': 'python scripts/export_literature_checkpoint.py --graph artifacts/literature-depth4/graph.json --output docs/literature/depth4',
    }
    (output / 'acquisition-supplement.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--graph', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.graph, args.output), indent=2))
