"""Offline regression checks for the research hold and restart safety."""
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import urllib.error
import urllib.parse
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'collect_literature.py'
spec = importlib.util.spec_from_file_location('collect_literature', SCRIPT)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def test_level4_rejected_before_output_or_network(tmp_path):
    args = SimpleNamespace(depth=4, output=str(tmp_path / 'output'))
    with patch.object(collector, 'request') as fetch:
        with pytest.raises(ValueError, match='Level 4 is deferred'):
            collector.collect(args)
        fetch.assert_not_called()
    assert not (tmp_path / 'output').exists()
    result = subprocess.run([sys.executable, str(SCRIPT), '--depth', '4'], capture_output=True)
    assert result.returncode == 2


def test_failed_request_retried_on_restart(tmp_path):
    with patch.object(collector.urllib.request, 'urlopen', side_effect=urllib.error.URLError('outage')), patch.object(collector.time, 'sleep'):
        assert 'error' in collector.request('https://example.invalid/work', tmp_path)
    with patch.object(collector.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"id": "W1"}')) as fetch:
        assert collector.request('https://example.invalid/work', tmp_path)['data']['id'] == 'W1'
        assert fetch.call_count == 1
    with patch.object(collector.urllib.request, 'urlopen') as fetch:
        assert collector.request('https://example.invalid/work', tmp_path)['data']['id'] == 'W1'
        fetch.assert_not_called()


def test_budgeted_resume_keeps_cross_edges_and_stops_at_level3(tmp_path):
    seed_path = tmp_path / 'seeds.json'
    seed_path.write_text(json.dumps([{'id': 'L01', 'title': 'seed', 'doi': '10.example/seed'}]))
    references = {'W0': ['W1', 'W2'], 'W1': ['W2', 'W3'], 'W2': ['W3'], 'W3': ['W4'], 'W4': ['W5']}
    requests = []

    def request(url, cache):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        ids = ['W0'] if '/works/https://doi.org/' in url else query['filter'][0].split(':', 1)[1].split('|')
        requests.extend(ids)
        fields = query['select'][0].split(',')
        works = [{'id': 'https://openalex.org/' + key, 'title': key, **({'referenced_works': ['https://openalex.org/' + x for x in references[key]]} if 'referenced_works' in fields else {})} for key in ids]
        return {'url': url, 'retrieved_utc': '2026-10-31T00:00:00Z', 'data': works[0] if ids == ['W0'] else {'results': works}}

    args = SimpleNamespace(depth=3, max_new_records=1, output=str(tmp_path / 'output'), seeds=str(seed_path))
    with patch.object(collector, 'request', side_effect=request), contextlib.redirect_stdout(io.StringIO()):
        collector.collect(args)
        first = json.loads((tmp_path / 'output' / 'graph.json').read_text())
        assert first['levels']['1']['pending_ids'] == ['W2']
        for _ in range(3):
            collector.collect(args)
    graph = json.loads((tmp_path / 'output' / 'graph.json').read_text())
    assert {key: node['depth'] for key, node in graph['nodes'].items()} == {'W0': 0, 'W1': 1, 'W2': 1, 'W3': 2, 'W4': 3}
    assert graph['nodes']['W1']['referenced_works'] == ['https://openalex.org/W2', 'https://openalex.org/W3']
    assert 'referenced_works' not in graph['nodes']['W4']
    assert 'W5' not in requests
    assert all(graph['levels'][str(i)]['metadata_complete'] for i in range(1, 4))
    assert graph['provenance']['W4']['retrieved_utc']


def test_published_supplement_is_intact_bounded_and_honest():
    root = SCRIPT.parents[1]
    folder = root / 'docs' / 'literature' / 'depth4'
    manifest = json.loads((folder / 'acquisition-supplement.json').read_text())
    packed = (folder / manifest['snapshot']).read_bytes()
    assert hashlib.sha256(packed).hexdigest() == manifest['sha256']
    raw = gzip.decompress(packed)
    assert hashlib.sha256(raw).hexdigest() == manifest['uncompressed_sha256']
    assert hashlib.sha256((folder / 'seeds.json').read_bytes()).hexdigest() == manifest['seed_sha256']
    snapshot = json.loads(raw)
    assert not manifest['level3_review_complete']
    assert manifest['s4b'] == 'paused' and manifest['level4'] == 'deferred'
    assert all(work['depth'] <= 3 for work in snapshot['works'].values())
    assert len(snapshot['works']) == manifest['encountered_work_ids']
    assert len(snapshot['edges']) == manifest['edges']
    # Request URLs retain the selected field names for provenance, not abstract data.
    assert all('abstract_inverted_index' not in work for work in snapshot['works'].values())
    for parent, target in snapshot['edges']:
        assert snapshot['works'][parent]['depth'] < 3
        assert parent in snapshot['works'][target]['parents']
    reviews = json.loads((folder / 'applicability.json').read_text())
    bib = (root / 'docs' / 'literature' / 'references.bib').read_text()
    for review in reviews['records'] + reviews['supplementary_corrections']:
        assert '{' + review['bibliography_key'] + ',' in bib


def test_recovered_parent_repairs_depth_without_expanding_level3():
    state = {'seeds': {'L01': 'W0'}, 'nodes': {
        'W0': {'depth': 0, 'referenced_works': ['https://openalex.org/W1']},
        'W1': {'depth': 1, 'referenced_works': ['https://openalex.org/W2']},
        'W2': {'depth': 3, 'referenced_works': ['https://openalex.org/W3']},
        'W3': {'depth': 4, 'referenced_works': ['https://openalex.org/W4']},
        'W4': {'depth': 4, 'referenced_works': []},
    }}
    collector.reconcile_depths(state)
    assert state['nodes']['W2']['depth'] == 2
    assert state['nodes']['W3']['depth'] == 3
    assert state['nodes']['W4']['depth'] == 4  # Retained historical data, never expanded.


def test_failed_seed_refresh_preserves_known_identity(tmp_path):
    seed_path = tmp_path / 'seeds.json'
    seed_path.write_text(json.dumps([{'id': 'L01', 'title': 'seed', 'doi': '10.example/seed'}]))
    output = tmp_path / 'output'
    output.mkdir()
    (output / 'graph.json').write_text(json.dumps({'nodes': {'W0': {'depth': 0, 'referenced_works': []}}, 'seeds': {'L01': 'W0'}, 'failures': [], 'levels': {}}))
    args = SimpleNamespace(depth=3, output=str(output), seeds=str(seed_path))
    with patch.object(collector, 'request', return_value={'url': 'https://example.invalid', 'error': 'outage'}), contextlib.redirect_stdout(io.StringIO()):
        collector.collect(args)
    state = json.loads((output / 'graph.json').read_text())
    assert state['seeds']['L01'] == 'W0'
    assert state['nodes']['W0']['depth'] == 0
