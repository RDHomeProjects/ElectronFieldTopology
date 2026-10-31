"""Checkpointed backward citation collection, capped at level 3; no network in CI.

OpenAlex is an index, not a completeness certificate for printed bibliographies.
Raw abstracts stay in the ignored cache; publication artifacts are separate.
"""
import argparse
from collections import deque
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
MAX_DEPTH = 3  # Maintainer hold: level 4 needs a later explicit scope decision.
AGENT = 'ElectronFieldTopology-literature-review/1.0 (https://github.com/RDHomeProjects/ElectronFieldTopology)'


def request(url, cache):
    path = cache / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    if path.exists():
        cached = json.loads(path.read_text())
        if 'data' in cached:
            return cached
        # Failed attempts are evidence, not permanent negative responses.
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
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                break  # Stop this request on provider throttling; resume later.
            time.sleep(min(2 ** attempt, 8))
    result = {'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'error': error}
    path.write_text(json.dumps(result))
    return result


def short_id(value):
    return value.rsplit('/', 1)[-1]


def save_state(path, state):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state))
    temporary.replace(path)


def reconcile_depths(state):
    """Repair shortest known depths when recovering a previously missing parent."""
    depths = {key: 0 for key in state['seeds'].values() if key in state['nodes']}
    queue = deque(depths)
    while queue:
        key = queue.popleft()
        depth = depths[key]
        state['nodes'][key]['depth'] = depth
        if depth >= MAX_DEPTH:
            continue
        for target in state['nodes'][key].get('referenced_works', []):
            child = short_id(target)
            if child in state['nodes'] and child not in depths:
                depths[child] = depth + 1
                queue.append(child)


def collect(args):
    if not 1 <= args.depth <= MAX_DEPTH:
        raise ValueError('Level 4 is deferred pending the completed level-3 review and a maintainer decision')
    budget = getattr(args, 'max_new_records', 1000)
    if budget < 1:
        raise ValueError('max_new_records must be positive')
    output = Path(args.output)
    cache = output / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    seeds = json.loads(Path(args.seeds).read_text())
    state_path = output / 'graph.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'nodes': {}, 'seeds': {}, 'failures': [], 'levels': {}}
    nodes = state['nodes']
    state.setdefault('provenance', {})
    state.setdefault('frontiers', {})
    state['collection_depth_limit'] = MAX_DEPTH
    state['level4_status'] = 'deferred; no collection or applicability review authorised'
    seed_hash = hashlib.sha256(Path(args.seeds).read_bytes()).hexdigest()
    if state.get('seed_sha256', seed_hash) != seed_hash:
        raise ValueError('Seed set changed; preserve this checkpoint and use a separate output directory')
    state['seed_sha256'] = seed_hash
    state['failures_are'] = 'historical attempts; seeds and levels.pending_ids describe current gaps'
    state['review_status'] = 'not assessed by this metadata collector'
    collected = 0
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
                state['provenance'][key] = {k: result[k] for k in ('url', 'retrieved_utc')}
                print('seed', seed['id'], key, len(data.get('referenced_works', [])), flush=True)
            else:
                # A failed refresh must not erase a previously resolved identity.
                state['seeds'].setdefault(seed['id'], None)
                entry = {'seed': seed['id'], 'url': result['url'], 'reason': result.get('error', 'No unique exact title match')}
                if entry not in state['failures']:
                    state['failures'].append(entry)
                print('unresolved seed', seed['id'], entry['reason'], flush=True)
        reconcile_depths(state)
        save_state(state_path, state)
        for depth in range(1, args.depth + 1):
            parents = [x for x in nodes.values() if x['depth'] == depth - 1]
            referenced = {short_id(r) for x in parents for r in x.get('referenced_works', [])}
            state['frontiers'][str(depth)] = sorted(referenced)
            targets = sorted(referenced - set(nodes))
            state['levels'][str(depth)] = {
                'encountered_count': len(referenced),
                'pending_ids': targets,
                'metadata_complete': not targets,
            }
            save_state(state_path, state)
            print('level', depth, 'new targets', len(targets), flush=True)
            # Persist the entire frontier before applying the per-invocation budget.
            admitted = targets[:max(0, budget - collected)]
            batches = [admitted[i:i + 100] for i in range(0, len(admitted), 100)]
            def batch(ids):
                # Do not even request level-3 bibliographies: their targets would be level 4.
                fields = FIELDS if depth < MAX_DEPTH else ','.join(x for x in FIELDS.split(',') if x != 'referenced_works')
                query = urllib.parse.urlencode({'filter': 'openalex_id:' + '|'.join(ids), 'per_page': 100, 'select': fields})
                return ids, request('https://api.openalex.org/works?' + query, cache)
            for index, (ids, result) in enumerate(pool.map(batch, batches)):
                found = []
                if 'data' in result:
                    for data in result['data']['results']:
                        key = short_id(data['id'])
                        data['depth'] = min(depth, nodes.get(key, {}).get('depth', depth))
                        nodes[key] = data
                        state['provenance'][key] = {k: result[k] for k in ('url', 'retrieved_utc')}
                        found.append(key)
                    collected += len(found)
                    reconcile_depths(state)
                missing = sorted(set(ids) - set(found))
                if missing:
                    entry = {'depth': depth, 'ids': missing, 'url': result['url'], 'reason': result.get('error', 'IDs absent from response')}
                    if entry not in state['failures']:
                        state['failures'].append(entry)
                pending = sorted(referenced - set(nodes))
                state['levels'][str(depth)] = {'encountered_count': len(referenced), 'pending_ids': pending, 'metadata_complete': not pending}
                save_state(state_path, state)
                print('level', depth, 'batch', index + 1, '/', len(batches), 'nodes', len(nodes), 'missing', len(missing), flush=True)
            if state['levels'][str(depth)]['pending_ids']:
                print('paused: unfinished frontier at level', depth, '; resume this checkpoint before deeper acquisition', flush=True)
                break
    print('saved', len(nodes), 'nodes', 'failures', len(state['failures']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', default='docs/literature/depth4/seeds.json')
    parser.add_argument('--output', default='artifacts/literature-depth4')
    parser.add_argument('--depth', type=int, choices=range(1, MAX_DEPTH + 1), default=MAX_DEPTH)
    parser.add_argument('--max-new-records', type=int, default=1000, help='Non-seed metadata budget per invocation; pending IDs remain checkpointed')
    collect(parser.parse_args())
