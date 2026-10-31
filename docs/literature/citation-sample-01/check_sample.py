"""Validate the frozen 1% citation sample without network access."""
from pathlib import Path
from collections import Counter
import argparse
import csv
import gzip
import hashlib
import io
import json


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(folder, source=None):
    manifest = json.loads((folder / 'sample-manifest.json').read_text())
    for item in manifest['files']:
        data = (folder / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
    ids = (folder / 'selected-ids.txt').read_text().splitlines()
    assert ids == sorted(set(ids)) and len(ids) == 1133
    assert manifest['full_dataset_ids'] == 113295
    assert len(ids) == round(manifest['full_dataset_ids'] / 100)
    raw = gzip.decompress((folder / 'records.jsonl.gz').read_bytes())
    assert sha(raw) == manifest['records_uncompressed_sha256']
    lines = raw.splitlines(keepends=True)
    rows = [json.loads(line) for line in lines]
    assert [row['id'] for row in rows] == ids
    selected = set(ids)
    for row in rows:
        assert 0 <= row['min_depth'] <= 3
        assert row['substantive_review'] == 'pending'
    assert dict(Counter(str(r['min_depth']) for r in rows)) == manifest['depth_counts']
    assert dict(Counter(r['metadata_status'] for r in rows)) == manifest['metadata_status_counts']
    assert dict(Counter(r['screen_status'] for r in rows)) == manifest['screen_status_counts']
    edge_bytes = gzip.decompress((folder / 'edges.csv.gz').read_bytes())
    assert sha(edge_bytes) == manifest['edges_uncompressed_sha256']
    edges = list(csv.DictReader(io.StringIO(edge_bytes.decode())))
    pairs = {(r['parent_id'], r['referenced_id']) for r in edges}
    assert len(edges) == len(pairs) == manifest['incident_edges']
    assert all(a in selected or b in selected for a, b in pairs)
    assert all(e['provider'] == 'OpenAlex' and e['printed_bibliography_verified'] == 'false' for e in edges)
    assert sum(a in selected and b in selected for a, b in pairs) == manifest['internal_edges']
    endpoints = {x for pair in pairs for x in pair}
    assert len(endpoints - selected) == manifest['external_endpoint_ids']
    for row in rows:
        assert {a for a, b in pairs if b == row['id']} == set(row['parents'])
        if row['min_depth'] < 3 and row['metadata_status'] == 'acquired':
            assert {b for a, b in pairs if a == row['id']} == set(row['reference_ids'])
    if source:
        original_manifest = (source / 'manifest.json').read_bytes()
        assert sha(original_manifest) == manifest['source_manifest_sha256']
        original = json.loads(original_manifest)
        originals = {}
        for item in original['files']:
            data = (source / item['path']).read_bytes()
            assert len(data) == item['bytes'] and sha(data) == item['sha256']
            if item['path'].startswith('ledger-'):
                for line in gzip.decompress(data).splitlines(keepends=True):
                    key = json.loads(line)['id']
                    assert key not in originals
                    originals[key] = line
        assert len(originals) == manifest['full_dataset_ids']
        assert sorted(originals)[:1133] == ids
        assert b''.join(originals[key] for key in ids) == raw
        with gzip.open(source / 'edges.csv.gz', 'rt') as stream:
            expected = [r for r in csv.DictReader(stream) if r['parent_id'] in selected or r['referenced_id'] in selected]
        assert edges == expected
    assert manifest['research_complete'] is False
    assert manifest['s4b'] == 'paused' and manifest['level4'] == 'deferred'
    print(f"Citation sample integrity passed: {len(ids)}/113295 IDs, {len(edges)} incident edges; "
          f"source comparison={'passed' if source else 'not requested'}. Research incomplete; S4-B paused; level 4 deferred.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Optional recovered full-data directory for exact subset reproduction')
    args = parser.parse_args()
    verify(Path(__file__).resolve().parent, args.source)
