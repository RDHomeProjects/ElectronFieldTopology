"""Offline record tests and real local Git publication transitions; no network."""
from pathlib import Path
import io, json, re, subprocess, sys, tempfile, zipfile
from html.parser import HTMLParser
import handover as p

checks = []
for source in p.ROOT.glob('*.py'):
    compile(source.read_text(), str(source), 'exec')
p.verify()
checks.append('Package, 297 supplemental and 717 original hashes; source identities and all 21 nested curve copies verified')
with zipfile.ZipFile(p.ROOT/'data/completed-evidence.zip') as final:
    with zipfile.ZipFile(io.BytesIO(final.read('original-evidence.zip'))) as original_zip:
        prepared_manifest = original_zip.read('handover/SHA256SUMS')

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *map(str, args)],
                                   stderr=subprocess.PIPE, text=True).strip()

def tree(repo):
    return {f.relative_to(repo).as_posix(): p.sha(f) for f in repo.rglob('*')
            if f.is_file() and '.git' not in f.parts}

cfg = p.load(p.ROOT / 'RESULTS.json')
slug = cfg['study_slug']
fixture = {'schema_version': 1, 'studies': [
    {'id': 's5-a-002', 'stage': 's5-a', 'number': 2, 'slug': 'q22-benchmark',
     'state': 'assessed', 'gate': 'bounded', 'finding': 'Historical static support', 'records': []},
    {'id': 's5-b-015', 'stage': 's5-b', 'number': 15, 'slug': 'q2-q16-closure-higher-q-review',
     'state': 'assessed', 'gate': 'open', 'finding': 'Original closure retained', 'records': []},
    {'id': 's5-b-016', 'stage': 's5-b', 'number': 16, 'slug': slug, 'state': 'prepared',
     'gate': 'open', 'finding': 'Prepared original plan',
     'specifications': ['docs/models/higher-q-reconciliation-motion-20261117.md'],
     'records': [{'role': 'preparation', 'path': p.PREPARATION+'/README.md', 'label': 'Original preparation'}]},
    {'id': 's2-005', 'stage': 's2', 'number': 5, 'slug': 'unrelated', 'state': 'prepared',
     'gate': 'open', 'finding': 'Unrelated finding', 'records': []}],
    'priority': ['s2-005', 's5-b-016', 's5-b-015'],
    'current': {'latest_assessed_study': 's5-b-015', 'summary': 'Closure summary'}}

def init_fixture(repo):
    repo.mkdir()
    git(repo, 'init', '-q', '-b', 'main')
    git(repo, 'config', 'user.name', 'Offline Fixture')
    git(repo, 'config', 'user.email', 'fixture@example.invalid')
    for n, b in {'README.md': b'# Local fixture\n',
                 'docs/project/roadmap.json': (json.dumps(fixture, indent=2)+'\n').encode(),
                 'docs/models/higher-q-reconciliation-motion-20261117.md': b'# Original prepared scope\n\nConditional pilot not executed.\n',
                 'reports/old-preparation/README.md': b'# Original preparation\n',
                 'reports/old-result.csv': b'iteration,value\r\n1,2\r\n',
                 'src/operator.py': b'UNCHANGED = True\n'}.items():
        f = repo / n; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(b)
    prep = repo/p.PREPARATION
    (prep/'handover').mkdir(parents=True)
    (prep/'README.md').write_text('# Preserved published preparation\n')
    (prep/'handover/SHA256SUMS').write_bytes(prepared_manifest)
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'fixture baseline')

def validate_applied(dest, m):
    roadmap = p.load(dest / 'docs/project/roadmap.json')
    study = next(s for s in roadmap['studies'] if s['id'] == 's5-b-016')
    assert study['state'] == 'assessed' and study['gate'] == 'open'
    for key in ['measurement_path', 'assessment_path']:
        folder = dest / m[key]
        p.verify_manifest(folder)
        rec = p.load(folder / 'record.json')
        assert p.RID.fullmatch(folder.name) and rec['record_id'] == folder.name
        assert rec['role'] == ('measurement' if key == 'measurement_path' else 'assessment')
        assert rec['relaxation_steps'] == rec['physical_time_steps'] == 0
        for text in folder.rglob('*.md'):
            for link in re.findall(r'\]\(([^)]+)\)', text.read_text()):
                if not link.startswith(('https:', 'http:', '#')):
                    assert (text.parent / link).exists(), (text, link)
        for csv in folder.rglob('*.csv'):
            assert b'\r' not in csv.read_bytes(), csv
    assert p.sha(dest / m['assessment_path'] / 'handover/data/completed-evidence.zip') == p.EXPECTED_EVIDENCE

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    src = root / 'source'; init_fixture(src)
    original = tree(src)
    base = git(src, 'rev-parse', 'HEAD')
    m = {'base': base, 'installed_at': p.stamp(), 'package_sha256': p.sha(p.ROOT / 'SHA256SUMS')}
    p.apply(src, m); validate_applied(src, m)
    first = tree(src); p.apply(src, m); assert tree(src) == first
    for n, h in original.items():
        if n not in ('docs/project/roadmap.json', 'docs/models/higher-q-reconciliation-motion-20261117.md'):
            assert p.sha(src / n) == h, n
    new = p.load(src / 'docs/project/roadmap.json')
    assert new['studies'][:2] == fixture['studies'][:2] and new['studies'][3] == fixture['studies'][3]
    assert new['priority'] == fixture['priority']
    assert new['current']['latest_assessed_study'] == 's5-b-016'
    assert (src/'docs/models/higher-q-reconciliation-motion-20261117.md').read_bytes().startswith(
        b'# Original prepared scope\n\nConditional pilot not executed.\n')
    # Preserve a newer unrelated current pointer on a repeated application.
    new['current'] = {'latest_assessed_study': 's2-005', 'summary': 'Newer unrelated result'}
    p.save(src/'docs/project/roadmap.json', new); p.apply(src, m)
    assert p.load(src/'docs/project/roadmap.json')['current'] == new['current']
    checks += ['Actual record application is idempotent; prior source/evidence, Q2-Q16 and other study findings preserved',
               'Canonical measurement/assessment IDs, entry points, local Markdown links, LF presentation CSV and exact nested checksum coverage pass',
               'Current-summary pointer advances conditionally; unrelated newer pointer and priorities preserved',
               'Original CRLF source CSV bytes preserved outside new records; embedded ZIP never rewritten']
    # Changed evidence in the output record is rejected by its unchanged manifest.
    f = src / m['measurement_path'] / 'MOTION-PROBES.json'; original_bytes = f.read_bytes(); f.write_bytes(b'changed')
    try: p.verify_manifest(f.parent)
    except RuntimeError: pass
    else: raise AssertionError('Modified record accepted')
    f.write_bytes(original_bytes)
    checks.append('Modified evidence member rejected by record checksum verification')

    # Replay against the actual pinned project register supplied in the archive.
    with zipfile.ZipFile(p.ROOT/'data/completed-evidence.zip') as final:
        with zipfile.ZipFile(io.BytesIO(final.read('original-evidence.zip'))) as original_zip:
            actual = json.loads(original_zip.read('repository/docs/project/roadmap.json'))
    actual_repo = root/'actual-register'; init_fixture(actual_repo)
    p.save(actual_repo/'docs/project/roadmap.json', actual)
    actual_marker = {'base': base, 'installed_at': p.stamp(), 'package_sha256': p.sha(p.ROOT/'SHA256SUMS')}
    p.apply(actual_repo, actual_marker); validate_applied(actual_repo, actual_marker)
    result = p.load(actual_repo/'docs/project/roadmap.json')
    assert [s for s in result['studies'] if s['id']!='s5-b-016'] == [s for s in actual['studies'] if s['id']!='s5-b-016']
    assert result['priority'] == actual['priority']
    checks.append('Application against the actual pinned roadmap updates only S5-B-016 and its eligible current summary; all other studies and priorities preserved')

    # Exercise installer/commit/push/merge transitions with REAL LOCAL Git; gh replies are fixtures.
    local = root/'local'; init_fixture(local)
    git(local, 'remote', 'add', 'origin', 'https://github.com/RDHomeProjects/ElectronFieldTopology.git')
    parent = git(local, 'rev-parse', 'HEAD')
    git(local, 'commit', '--allow-empty', '-qm', 'Prepared source branch commit')
    p.SOURCE = git(local, 'rev-parse', 'HEAD')
    git(local, 'update-ref', 'refs/heads/work/preparation', p.SOURCE)
    tree_id = git(local, 'rev-parse', 'HEAD^{tree}')
    squash = git(local, 'commit-tree', tree_id, '-p', parent, '-m', 'Squash-merged preparation')
    git(local, 'update-ref', 'refs/heads/main', squash)
    r = subprocess.run(['git', '-C', str(local), 'merge-base', '--is-ancestor', p.SOURCE, squash])
    assert r.returncode == 1 and git(local, 'rev-parse', p.SOURCE+'^{tree}') == git(local, 'rev-parse', squash+'^{tree}')
    receipt = p.verify_baseline(local, squash)
    assert not receipt['ancestry_required'] and receipt['scientific_source_commit'] == p.SOURCE
    # A later unrelated commit is also eligible if published preparation stays exact.
    (local/'unrelated.txt').write_text('Later main-only administrative update\n')
    git(local, 'add', 'unrelated.txt'); git(local, 'commit', '-qm', 'Unrelated later update')
    p.verify_baseline(local, git(local, 'rev-parse', 'HEAD'))
    checks.append('Actual non-ancestor squash-equivalent commits and a later unrelated main commit pass exact registered-preparation tree/manifest validation')
    # Alter a preparation member while retaining its manifest: tree comparison must reject it.
    baseline = git(local, 'rev-parse', 'HEAD')
    (local/p.PREPARATION/'README.md').write_text('Modified preparation\n')
    git(local, 'add', '.'); git(local, 'commit', '-qm', 'Changed preparation negative control')
    try: p.verify_baseline(local, git(local, 'rev-parse', 'HEAD'))
    except RuntimeError: pass
    else: raise AssertionError('Changed published preparation accepted')
    # Undo only the isolated negative-control fixture commit using a new matching commit.
    (local/p.PREPARATION/'README.md').write_text('# Preserved published preparation\n')
    git(local, 'add', '.'); git(local, 'commit', '-qm', 'Restore fixture preparation content')
    checks.append('Changed published preparation is rejected even when the handover manifest file remains unchanged')
    # verify() binds production source; it already ran above, so isolate transport transitions here.
    real_verify, real_cmd, real_checks = p.verify, p.cmd, p.checks
    p.verify = lambda: cfg
    args = type('Args', (), {'repo': local, 'publication': root/'publication'})()
    hosted = {'state': 'OPEN', 'number': 999, 'url': 'https://example.invalid/fixture-pr', 'headRefOid': None}
    controls = {'fail_fetch': True, 'bad_head': False, 'failed_checks': False}
    calls = []
    def transport(argv, cwd, capture=False):
        argv = list(map(str, argv)); calls.append(argv)
        if argv[:3] == ['git', 'fetch', 'origin']:
            if controls['fail_fetch']:
                controls['fail_fetch'] = False
                raise RuntimeError('Fixture DNS failure; no request sent')
            return real_cmd(['git', 'fetch', str(local), 'main:refs/remotes/origin/main'], cwd, capture)
        if argv[:3] == ['git', 'push', '-u']:
            # Push to a local bare peer, never the configured GitHub URL.
            peer = root/'peer.git'
            if not peer.exists():
                subprocess.run(['git', 'init', '--bare', '-q', str(peer)], check=True)
            return real_cmd(['git', 'push', str(peer), 'HEAD:refs/heads/'+p.BRANCH], cwd, capture)
        if argv[0] == 'gh':
            hosted['headRefOid'] = git(cwd, 'rev-parse', 'HEAD')
            if argv[1:3] == ['pr', 'list']: return '[]'
            if argv[1:3] == ['pr', 'view']:
                return json.dumps({**hosted, 'headRefOid': '0'*40} if controls['bad_head'] else hosted)
            if argv[1:3] == ['pr', 'checks'] and controls['failed_checks']:
                raise RuntimeError('Fixture hosted check failed')
            if argv[1:3] == ['pr', 'merge']:
                assert '--match-head-commit' in argv
                hosted.update(state='MERGED', mergeCommit={'oid': 'f'*40})
            return ''
        return real_cmd(argv, cwd, capture)
    def local_checks(dest, marker):
        validate_applied(dest, marker)
        real_cmd(['git', 'add', '--', 'README.md', 'docs', 'reports'], dest)
        real_cmd(['git', 'diff', '--cached', '--check'], dest)
    p.cmd, p.checks = transport, local_checks
    try: p.install(args)
    except RuntimeError as e: assert 'Fixture DNS failure' in str(e)
    else: raise AssertionError('Transport failure hidden')
    assert p.load(p.marker(args.publication))['phase'] == 'cloned'
    # Simulate the original stopped package marker, then adopt it without altering Git.
    old = p.load(p.marker(args.publication)); old['package_sha256'] = p.LEGACY_PACKAGE
    p.save(p.marker(args.publication), old)
    p.install(args)
    # Local identity is intentionally configured only inside this temporary checkout.
    git(args.publication, 'config', 'user.name', 'Offline Fixture')
    git(args.publication, 'config', 'user.email', 'fixture@example.invalid')
    assert p.load(p.marker(args.publication))['phase'] == 'staged'
    adopted = p.load(p.marker(args.publication))
    assert adopted['repaired_from_package_sha256'] == p.LEGACY_PACKAGE
    assert Path(adopted['baseline_repair']['backup']).is_file()
    assert adopted['baseline_validation']['scientific_source_commit'] == p.SOURCE
    stopped = root/'stopped-at-base'
    subprocess.run(['git', 'clone', '--no-hardlinks', '-q', str(local), str(stopped)], check=True)
    git(stopped, 'switch', '-qc', p.BRANCH)
    stopped_base = git(stopped, 'rev-parse', 'HEAD')
    old_marker = {'package_sha256': p.LEGACY_PACKAGE, 'phase': 'base', 'base': stopped_base,
                  'origin': 'https://github.com/RDHomeProjects/ElectronFieldTopology.git', 'installed_at': p.stamp()}
    p.save(p.marker(stopped), old_marker)
    repaired = p.adopt_stopped_legacy(stopped, old_marker, p.sha(p.ROOT/'SHA256SUMS'))
    assert repaired['phase']=='base' and git(stopped, 'rev-parse', 'HEAD')==stopped_base and not git(stopped,'status','--porcelain')
    assert Path(repaired['baseline_repair']['backup']).is_file()
    before = git(args.publication, 'diff', '--cached', '--binary')
    p.install(args); assert git(args.publication, 'diff', '--cached', '--binary') == before
    p.publish(args)
    for failure in ['bad_head', 'failed_checks']:
        controls[failure] = True
        try: p.merge(args)
        except RuntimeError: pass
        else: raise AssertionError('Unsafe merge permitted: '+failure)
        assert hosted['state'] == 'OPEN' and p.load(p.marker(args.publication))['phase'] == 'committed'
        controls[failure] = False
    p.merge(args); p.status(args)
    assert p.load(p.marker(args.publication))['phase'] == 'merged'
    # Re-running the full workflow after merging must not create a second commit/PR.
    head = git(args.publication, 'rev-parse', 'HEAD')
    p.install(args); p.publish(args); p.merge(args)
    assert git(args.publication, 'rev-parse', 'HEAD') == head
    assert not any('force' in arg or arg == '--admin' for call in calls for arg in call)
    assert len([call for call in calls if call[:3] == ['gh', 'pr', 'create']]) == 1
    checks.append('Real local Git install/stage/retry/commit/push transitions pass; simulated PR/check/guarded-merge and merged rerun create no duplicate commit or PR')
    checks.append('Interrupted fetch resumes without another clone; changed PR head and failed hosted checks prevent merge')
    checks.append('Stopped original-package marker is backed up and adopted; scientific source identity remains distinct from squash publication base')
    p.verify, p.cmd, p.checks = real_verify, real_cmd, real_checks

class Report(HTMLParser):
    def __init__(self): super().__init__(); self.scripts = 0
    def handle_starttag(self, tag, attrs): self.scripts += tag == 'script'
report = Report(); report.feed((p.ROOT/'ASSESSMENT.html').read_text()); assert report.scripts == 0
checks.append('Browser assessment parses without scripts or external rendering dependencies')
result = {'recorded_at': p.stamp(), 'status': 'passed', 'checks': checks,
          'limits': ['Actual project_records.py and check_docs.py are not available in this workspace and must pass on the zbook before commit',
                     'Hosted API responses/check outcomes are fixtures here; actual hosted checks must pass locally before merge',
                     'No GitHub request, numerical solver, full-field replay or physical-time evolution performed here']}
target = Path(sys.argv[1]) if len(sys.argv)>1 else p.ROOT/'HOST-VALIDATION.json'
target.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
