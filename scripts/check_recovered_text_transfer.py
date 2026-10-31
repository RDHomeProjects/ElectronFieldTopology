"""Verify the fixed recovered prose transfer offline, without paper acquisition."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def check(root=ROOT, allow_incomplete=False):
    folder = root / 'docs/literature/recovered-transfer'
    manifest = json.loads((folder / 'manifest.json').read_text())
    assert manifest['total_words'] == 5217
    assert manifest['research_complete'] is False
    assert manifest['s4b'] == 'paused' and manifest['level4'] == 'deferred'
    sources = manifest['sources']
    ranges = {name: [] for name in sources}

    def accept(fragment):
        name = fragment['source']
        a, b = fragment['start_word'], fragment['end_word']
        text = fragment['text']
        assert 0 <= a < b <= sources[name]['words']
        assert len(text.split()) == b - a
        assert digest(text) == fragment['sha256']
        assert all(b <= start or a >= end for start, end, _ in ranges[name]), 'Overlapping source ranges'
        ranges[name].append((a, b, text))
        return b - a

    initial = 0
    for fragment in manifest['initial_fragments']:
        document = (root / fragment['published_document']).read_text()
        assert ' '.join(fragment['text'].split()) in ' '.join(document.split())
        initial += accept(fragment)
    assert initial == manifest['initial_words'] == 573
    cumulative = initial
    missing_seen = False
    stages = 0
    for batch in manifest['batches']:
        path = root / batch['path']
        if not path.exists():
            missing_seen = True
            assert allow_incomplete, f'Missing batch: {path.name}'
            continue
        assert not missing_seen, 'Transfer batches must form a merged prefix'
        assert digest(path.read_text()) == batch['sha256']
        assert path.with_suffix('.md').is_file()
        data = json.loads(path.read_text())
        assert data['batch'] == batch['batch']
        count = sum(accept(f) for f in data['fragments'])
        assert count == data['words'] == batch['words']
        cumulative += count
        assert cumulative == data['cumulative_words'] == batch['cumulative_words']
        stages += 1
    complete = cumulative == manifest['total_words']
    if complete:
        for name, records in ranges.items():
            cursor = 0
            text = ''
            for a, b, content in sorted(records):
                assert a == cursor, f'Missing words in {name}'
                cursor = b
                text += content
            assert cursor == sources[name]['words']
            assert digest(text) == sources[name]['sha256'], f'Reconstruction hash mismatch: {name}'
        assert stages == len(manifest['batches']) == 9
    else:
        assert allow_incomplete
    print(f'Recovered prose integrity: {cumulative}/5217 words ({100*cumulative/5217:.2f}%), '
          f'{stages}/9 further batches; complete={complete}; no overlaps. '
          'Research incomplete; S4-B paused; level 4 deferred.')
    return cumulative


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    check(allow_incomplete=args.allow_incomplete)
