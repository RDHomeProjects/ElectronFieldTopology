"""Checkpointed backward citation collection; no topic pruning or network in CI.

OpenAlex is an index, not a completeness certificate for printed bibliographies.
Raw abstracts stay in the ignored cache; publication artifacts are separate.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

FIELDS = 'id,doi,title,publication_year,type,referenced_works,abstract_inverted_index,primary_location,open_access,ids'
AGENT = 'ElectronFieldTopology-literature-review/1.0 (https://github.com/RDHomeProjects/ElectronFieldTopology)'


def request(url, cache):
    path = cache / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    if path.exists():
        return json.loads(path.read_text())
    error = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': AGENT})
            with urllib.request.urlopen(req, timeout=45) as response:
                data = json.load(response)
            result = {'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'data': data}
            path.write_text(json.dumps(result))
            return result
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            error = str(exc)
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (400, 401, 403, 404):
                break
            time.sleep(min(2 ** attempt, 8))
    result = {'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'error': error}
    path.write_text(json.dumps(result))
    return result


def short_id(value):
    return value.rsplit('/', 1)[-1]


def collect(args):
    output = Path(args.output)
    cache = output / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    seeds = json.loads(Path(args.seeds).read_text())
    state_path = output / 'graph.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'nodes': {}, 'seeds': {}, 'failures': [], 'levels': {}}
    nodes = state['nodes']
    with ThreadPoolExecutor(max_workers=3) as pool:
        def resolve(seed):
            if seed['doi']:
                url = 'https://api.openalex.org/works/https://doi.org/' + seed['doi'] + '?select=' + FIELDS
            else:
                query = urllib.parse.urlencode({'search': seed['title'], 'per_page': 3, 'select': FIELDS})
                url = 'https://api.openalex.org/works?' + query
            result = request(url, cache)
            if 'error' in result:
                return seed, None, result
            data = result['data']
            if not seed['doi']:
                matches = data.get('results', [])
                norm = lambda s: ''.join(c for c in s.casefold() if c.isalnum())
                matches = [x for x in matches if norm(x['title']) == norm(seed['title'])]
                data = matches[0] if len(matches) == 1 else None
            return seed, data, result
        for seed, data, result in pool.map(resolve, seeds):
            if data:
                key = short_id(data['id'])
                data['depth'] = 0
                nodes[key] = data
                state['seeds'][seed['id']] = key
                print('seed', seed['id'], key, len(data.get('referenced_works', [])), flush=True)
            else:
                state['seeds'][seed['id']] = None
                entry = {'seed': seed['id'], 'url': result['url'], 'reason': result.get('error', 'No unique exact title match')}
                if entry not in state['failures']:
                    state['failures'].append(entry)
                print('unresolved seed', seed['id'], entry['reason'], flush=True)
        state_path.write_text(json.dumps(state))
        for depth in range(1, args.depth + 1):
            parents = [x for x in nodes.values() if x['depth'] == depth - 1]
            targets = sorted({short_id(r) for x in parents for r in x.get('referenced_works', [])} - set(nodes))
            print('level', depth, 'new targets', len(targets), flush=True)
            batches = [targets[i:i + 100] for i in range(0, len(targets), 100)]
            def batch(ids):
                query = urllib.parse.urlencode({'filter': 'openalex_id:' + '|'.join(ids), 'per_page': 100, 'select': FIELDS})
                return ids, request('https://api.openalex.org/works?' + query, cache)
            for index, (ids, result) in enumerate(pool.map(batch, batches)):
                found = []
                if 'data' in result:
                    for data in result['data']['results']:
                        key = short_id(data['id'])
                        data['depth'] = min(depth, nodes.get(key, {}).get('depth', depth))
                        nodes[key] = data
                        found.append(key)
                missing = sorted(set(ids) - set(found))
                if missing:
                    entry = {'depth': depth, 'ids': missing, 'url': result['url'], 'reason': result.get('error', 'IDs absent from response')}
                    if entry not in state['failures']:
                        state['failures'].append(entry)
                state['levels'][str(depth)] = {'target_count': len(targets), 'batches_completed': index + 1, 'batch_count': len(batches)}
                state_path.write_text(json.dumps(state))
                print('level', depth, 'batch', index + 1, '/', len(batches), 'nodes', len(nodes), 'missing', len(missing), flush=True)
    print('saved', len(nodes), 'nodes', 'failures', len(state['failures']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', default='docs/literature/depth4/seeds.json')
    parser.add_argument('--output', default='artifacts/literature-depth4')
    parser.add_argument('--depth', type=int, choices=range(1, 5), default=4)
    collect(parser.parse_args())
