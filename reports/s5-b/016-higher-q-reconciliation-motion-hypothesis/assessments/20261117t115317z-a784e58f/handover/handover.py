"""Publish completed reconciliation only, from the user's local workstation."""
import argparse, hashlib, io, json, os, re, shutil, subprocess, sys, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
REPOSITORY = 'RDHomeProjects/ElectronFieldTopology'
BRANCH = 'analysis/reconciliation-results-20261117'
MARKER = 'reconciliation-results-publication.json'
EXPECTED_EVIDENCE = '62ac6afb159d91664fe36bd3d6b52732cb9294d98ab5e527a5c28d3a4afec24e'
EXPECTED_ORIGINAL = '12d331160bff607d89250dc05811659aee11db5795b0ad1af4b9299de8c28893'
SOURCE = 'dfcdd9ef3509cf0b3e6970986c8458d69f084b27'
LEGACY_PACKAGE = 'cb8716d1ad9dd01b306ee735dea8f1cffaae5c98213a2588d46475673c928726'
PREPARATION = 'reports/s5-b/016-higher-q-reconciliation-motion-hypothesis/preparation/20261116t220546z-891159dc'
PREPARATION_MANIFEST = 'b1c8cd9ba5266a3c6b649c31dbedd061abc088a5950a02b940837c4e26e77c38'
RID = re.compile(r'\d{8}t\d{6}z-[a-f0-9]{8}')

def stamp():
    n = datetime.now(timezone.utc)
    return {'utc': n.isoformat(), 'melbourne': n.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}

def event(message, **kw):
    print(json.dumps({'recorded_at': stamp(), 'message': message, **kw}), flush=True)

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(Path(path).read_text())

def save(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)

def files(folder):
    return {p.relative_to(folder).as_posix() for p in folder.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}

def safe(name):
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '..' not in p.parts and p.as_posix() == name

def manifest(folder):
    # Exclude only this manifest, retaining every nested SHA256SUMS in coverage.
    (folder / 'SHA256SUMS').write_text(''.join(
        sha(folder / n) + '  ' + n + '\n'
        for n in sorted(files(folder) - {'SHA256SUMS'})))

def verify_manifest(folder):
    seen = set()
    for line in (folder / 'SHA256SUMS').read_text().splitlines():
        h, n = line.split('  ', 1)
        need(safe(n) and n not in seen and sha(folder / n) == h,
             'Missing, unsafe or modified package member: ' + n)
        seen.add(n)
    need(seen == files(folder) - {'SHA256SUMS'}, 'Manifest coverage differs: ' + str(folder))
    return len(seen)

def verify_zip(z):
    names = z.namelist()
    need(len(names) == len(set(names)) and z.testzip() is None, 'Evidence ZIP duplicates/CRC failure')
    seen = set()
    for line in z.read('SHA256SUMS').decode().splitlines():
        h, n = line.split('  ', 1)
        need(safe(n) and n not in seen and hashlib.sha256(z.read(n)).hexdigest() == h,
             'Evidence member differs: ' + n)
        seen.add(n)
    need(seen | {'SHA256SUMS'} == set(names), 'Evidence checksum coverage differs')
    return len(seen)

def verify():
    count = verify_manifest(ROOT)
    for p in ROOT.rglob('*.csv'):
        need(b'\r' not in p.read_bytes(), 'New CSV must use LF: ' + p.name)
    cfg = load(ROOT / 'RESULTS.json')
    need(cfg['source_commit'] == SOURCE and cfg['evidence_sha256'] == EXPECTED_EVIDENCE
         and cfg['original_evidence_sha256'] == EXPECTED_ORIGINAL, 'Frozen source identities differ')
    need(RID.fullmatch(cfg['assessment_id']) and RID.fullmatch(cfg['measurement_id']), 'Invalid record ID')
    p = ROOT / 'data/completed-evidence.zip'
    need(sha(p) == EXPECTED_EVIDENCE, 'Final evidence archive differs')
    with zipfile.ZipFile(p) as z:
        outer = verify_zip(z)
        coverage = json.loads(z.read('REFERENCE-COVERAGE.json'))
        need(coverage['source_commit'] == SOURCE and coverage['all_declared_references_present']
             and len(coverage['references']) == 57, 'Declared references differ')
        original = z.read('original-evidence.zip')
        need(hashlib.sha256(original).hexdigest() == EXPECTED_ORIGINAL, 'Original evidence differs')
        with zipfile.ZipFile(io.BytesIO(original)) as old:
            original_count = verify_zip(old)
            probes = json.loads(old.read('MOTION-PROBES.json'))
            need({x['field'] for x in probes['results']} == {'Q2', 'Q8'}, 'Probe field set differs')
        name = 'repository/reports/s5-a/q22-fresh-20261101T102757+1100/evidence.zip'
        with zipfile.ZipFile(io.BytesIO(z.read(name))) as q22:
            for item in coverage['deferred']:
                n = item['path'].split('/records/', 1)[1]
                b = q22.read(n)
                need(hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
                     == item['git_blob'], 'Deferred curve differs: ' + n)
    event('Completed results and publication pack verified', payload_files=count,
          supplemental_payloads=outer, original_payloads=original_count,
          declared_references=57, deferred_curve_copies_present=21,
          relaxation_steps=0, physical_time_steps=0)
    return cfg

def cmd(argv, cwd, capture=False):
    argv = list(map(str, argv))
    event('Command', argv=argv)
    r = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.PIPE if capture else None)
    need(r.returncode == 0, 'Command failed: ' + repr(argv) + ('\n' + r.stderr if capture else ''))
    return r.stdout.strip() if capture else ''

def marker(dest):
    return dest / '.git' / MARKER

def clean(dest):
    return not cmd(['git', 'status', '--porcelain'], dest, True)

def fingerprint(dest):
    names = cmd(['git', 'diff', '--cached', '--name-only', '-z'], dest, True).split('\0')
    return {n: sha(dest / n) for n in names if n}

def verify_baseline(dest, base):
    """Authenticate immutable preparation content independently of squash ancestry."""
    trees = {}
    for label, ref in [('scientific_source', SOURCE), ('publication_base', base)]:
        argv = ['git', 'show', ref + ':docs/project/roadmap.json']
        roadmap = json.loads(cmd(argv, dest, True))
        study = next((s for s in roadmap['studies'] if s['id'] == 's5-b-016'), None)
        need(study and study['slug'] == 'higher-q-reconciliation-motion-hypothesis'
             and any(r['role'] == 'preparation' and r['path'] == PREPARATION + '/README.md'
                     for r in study['records']), 'Required registered preparation is absent: ' + ref)
        trees[label] = cmd(['git', 'rev-parse', ref + ':' + PREPARATION], dest, True)
        argv = ['git', 'show', ref + ':' + PREPARATION + '/handover/SHA256SUMS']
        event('Command', argv=argv)
        r = subprocess.run(argv, cwd=dest, capture_output=True)
        need(r.returncode == 0 and hashlib.sha256(r.stdout).hexdigest() == PREPARATION_MANIFEST,
             'Pinned preparation handover manifest differs: ' + ref)
    need(trees['scientific_source'] == trees['publication_base'],
         'Published preparation content differs from the recorded scientific source; preserve and reconcile')
    receipt = {'recorded_at': stamp(), 'method': 'registered preparation, exact Git tree and pinned handover manifest',
               'scientific_source_commit': SOURCE, 'publication_base_commit': base,
               'preparation_path': PREPARATION, 'preparation_tree': trees['scientific_source'],
               'handover_manifest_sha256': PREPARATION_MANIFEST,
               'ancestry_required': False, 'scientific_source_substituted': False}
    event('Published preparation content verified', **{k:v for k,v in receipt.items() if k!='recorded_at'})
    return receipt

def adopt_stopped_legacy(dest, m, package_sha):
    """Repair only the identified original pack, stopped before result application."""
    need(m['package_sha256'] == LEGACY_PACKAGE and m['phase'] in ('cloned', 'branching', 'base'),
         'Publication belongs to another package or has already applied results; preserve it')
    need(not m.get('commit') and not m.get('pr') and clean(dest),
         'Legacy checkout has results, commits, a PR or unrecorded edits; preserve it')
    if m['phase'] == 'base':
        need(cmd(['git', 'rev-parse', 'HEAD'], dest, True) == m['base']
             and cmd(['git', 'branch', '--show-current'], dest, True) == BRANCH,
             'Stopped legacy checkout changed')
    backup = dest / '.git' / ('before-squash-baseline-repair-' + uuid.uuid4().hex[:8] + '.json')
    shutil.copy2(marker(dest), backup)
    m.update(package_sha256=package_sha,
             repaired_from_package_sha256=LEGACY_PACKAGE,
             baseline_repair={'recorded_at': stamp(), 'backup': str(backup),
                              'reason': 'Accept exact published preparation content after squash merge; scientific source remains pinned'})
    save(marker(dest), m)
    event('Stopped publication adopted by content-validation repair', backup=str(backup), phase=m['phase'])
    return m

def apply(dest, m):
    cfg = load(ROOT / 'RESULTS.json')
    path = dest / 'docs/project/roadmap.json'
    d = load(path)
    study = next((s for s in d['studies'] if s['id'] == cfg['study_id']), None)
    need(study and study['slug'] == cfg['study_slug'], 'Existing reconciliation study S5-B-016 is required')
    stem = Path('reports') / study['stage'] / f"{study['number']:03d}-{study['slug']}"
    measurement = stem / 'runs' / cfg['measurement_id']
    assessment = stem / 'assessments' / cfg['assessment_id']
    af, mf = dest / assessment, dest / measurement
    expected_assessment = (assessment / 'README.md').as_posix()
    own = next((r for r in study['records'] if r['path'] == expected_assessment), None)
    need(study['state'] == 'prepared' or (study['state'] == 'assessed' and own),
         'Reconciliation study already advanced differently; preserve it and reconcile')
    # Bind record paths before any write; refuse a different existing record.
    for folder in (af, mf):
        if folder.exists():
            need((folder / 'record.json').is_file()
                 and load(folder / 'record.json').get('handover_sha256') == m['package_sha256'],
                 'Existing record differs: ' + str(folder))
        folder.mkdir(parents=True, exist_ok=True)
    common = {'study_id': study['id'], 'recorded_at': m['installed_at'],
              'source_commit': SOURCE, 'publication_base_commit': m['base'],
              'handover_sha256': m['package_sha256'],
              'publication_baseline_validation': m.get('baseline_validation'),
              'input_sha256': {'completed_linked_evidence': EXPECTED_EVIDENCE,
                               'original_diagnostic_evidence': EXPECTED_ORIGINAL},
              'relaxation_steps': 0, 'physical_time_steps': 0,
              'limitations': ['Compact evidence excludes full 3D fields',
                             'Instantaneous internal rotation is not a stability certificate',
                             'Historical cell-functional success is not D4 admission',
                             'Original gates and Q2-Q16 closure remain unchanged']}
    save(mf / 'record.json', {**common, 'record_id': cfg['measurement_id'], 'role': 'measurement',
         'outcome': 'Pinned records collected, Q2/Q8 frozen-field probes completed, all declared documents reconciled',
         'original_collection_id': cfg['original_collection_id']})
    save(af / 'record.json', {**common, 'record_id': cfg['assessment_id'], 'role': 'assessment',
         'outcome': 'Historical Q22 and Q17/Q19 static successes reconciled; Q18 hyperbolic result incomplete; no useful Q8 internal-rotation rescue'})
    shutil.copytree(ROOT, af / 'handover', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    with zipfile.ZipFile(ROOT / 'data/completed-evidence.zip') as z:
        (mf / 'REFERENCE-COVERAGE.json').write_bytes(z.read('REFERENCE-COVERAGE.json'))
        with zipfile.ZipFile(io.BytesIO(z.read('original-evidence.zip'))) as original:
            for n in ('COLLECTION.json', 'DIAGNOSTIC-STATUS.json', 'MOTION-PROBES.json', 'local-field-availability.json'):
                (mf / n).write_bytes(original.read(n))
    evidence_link = Path(os.path.relpath(af / 'handover/data/completed-evidence.zip', mf)).as_posix()
    assessment_link = Path(os.path.relpath(af / 'README.md', mf)).as_posix()
    (mf / 'README.md').write_text('# Completed higher-Q reconciliation and frozen-field probes\n\n'
        + f'[Unchanged complete evidence ZIP]({evidence_link}) · [Scientific assessment]({assessment_link}) · '
        + '[Motion probes](MOTION-PROBES.json) · [Reference coverage](REFERENCE-COVERAGE.json) · '
        + '[Local field availability](local-field-availability.json)\n\n'
        + 'Collection 20261117t082634z-ee428350 and linked completion 20261117t114258z-f6c4cae0 are retained. '
        + 'Both Q2/Q8 diagnostic probes completed. All 57 declared reference occurrences are covered. '
        + 'The 21 deferred curve copies are present inside the original Q22 archive. '
        + 'No relaxation or physical-time steps were taken. Compact evidence is not a full-field backup.\n')
    measurement_link = Path(os.path.relpath(mf / 'README.md', af)).as_posix()
    (af / 'README.md').write_text('# Assessed higher-Q reconciliation results\n\n'
        + '[Browser assessment](handover/ASSESSMENT.html) · [Markdown assessment](handover/ASSESSMENT.md) · '
        + '[Record verification](handover/REVIEW-VALIDATION.json) · [Static endpoint ledger](handover/STATIC-ENDPOINTS.csv) · '
        + f'[Completed measurements]({measurement_link}) · [Local publication handover](handover/README.md)\n\n'
        + 'Historical Q22 bounded static and selected Q17/Q19 branch benchmarks are supported with their original limits. '
        + 'Q18 hyperbolic reproduction and current higher-Q D4 motion readiness remain unresolved. '
        + 'Q8 receives no useful improvement from tested internal rotation. Scientific gate remains open. '
        + 'A native-grid operator compatibility test is recommended before more relaxation; no new campaign is prepared.\n')
    manifest(mf)
    manifest(af)
    additions = [('measurement', measurement, 'Completed source reconciliation, Q2/Q8 probes and linked-document coverage'),
                 ('assessment', assessment, 'Reconciled static benchmarks, motion-probe outcomes and operator compatibility decision')]
    for role, folder, label in additions:
        entry = {'role': role, 'path': (folder / 'README.md').as_posix(), 'label': label}
        if not any(r['path'] == entry['path'] for r in study['records']):
            study['records'].append(entry)
    study.update(state='assessed', gate='open',
        finding='Completed records reconcile supported historical Q22 cable and Q17/Q19 static branches with unresolved later D4 preparation. Q18 hyperbolic reproduction remains incomplete. Internal rotation modestly improves Q2 residuals but offers no useful Q8 rescue. All declared document references are covered.',
        next_action='Record completed findings; compare one authenticated successful field under native cell and D4 operators at unchanged grid and box before allocating bounded readmission. Preserve Q2-Q16 closure; defer broad Q17-Q32 work and Q8 rotation rescue.',
        exit_evidence='Unchanged final and original compact archives, all 57 declared reference occurrences, 21 duplicate curves verified inside the original Q22 archive, completed probe receipts, explicit full-field limits and assessed historical/static versus current D4 distinctions.')
    spec = dest / 'docs/models/higher-q-reconciliation-motion-20261117.md'
    need(spec.is_file(), 'Existing model-scope document is absent')
    tag = '<!-- completed-reconciliation-' + cfg['assessment_id'] + ' -->'
    if tag not in spec.read_text():
        link = Path(os.path.relpath(af / 'README.md', spec.parent)).as_posix()
        with spec.open('a') as f:
            f.write('\n\n' + tag + '\n## Completed reconciliation assessment\n\n'
                + f'[Completed measurements and consolidated assessment]({link}). '
                + 'All declared documents are covered; the original Q22 static benchmark and Q17/Q19 selected branches are supported within their historical scope. '
                + 'Q18 hyperbolic reproduction and current D4 motion readiness remain unresolved. Q8 internal rotation gives no useful rescue. '
                + 'The earlier conditional two-arm Q22 pilot remains unexecuted; its next allocation is deferred in favor of a native-grid operator compatibility comparison. '
                + 'No model, gate or numerical campaign is changed by this record.\n')
    if d.get('current', {}).get('latest_assessed_study') in ('s5-b-015', study['id']):
        d['current'] = {'latest_assessed_study': study['id'], 'summary': study['finding'],
                        'limits': 'Historical finite-grid static support; current D4 readiness and physical-time stability remain open. No new numerical allocation.'}
    d['updated_at'] = m['installed_at']
    save(path, d)
    m.update(study_id=study['id'], measurement_path=measurement.as_posix(), assessment_path=assessment.as_posix())
    return m

def checks(dest, m):
    cmd([sys.executable, 'scripts/project_records.py', 'render'], dest)
    cmd(['git', 'add', '--', 'README.md', 'docs', 'reports'], dest)
    cmd([sys.executable, 'scripts/project_records.py', 'check', '--compare-ref', m['base']], dest)
    cmd([sys.executable, 'scripts/check_docs.py'], dest)
    cmd(['git', 'diff', '--cached', '--check'], dest)

def install(a):
    verify()
    dest = a.publication
    package_sha = sha(ROOT / 'SHA256SUMS')
    if dest.exists():
        need(marker(dest).is_file(), 'Existing publication directory has no matching marker; choose a new --publication directory')
        m = load(marker(dest))
        if m['package_sha256'] != package_sha:
            m = adopt_stopped_legacy(dest, m, package_sha)
    else:
        origin = cmd(['git', 'remote', 'get-url', 'origin'], a.repo, True)
        need(origin.rstrip('/').removesuffix('.git').lower() in (
            'https://github.com/rdhomeprojects/electronfieldtopology',
            'git@github.com:rdhomeprojects/electronfieldtopology'), 'Unexpected repository origin')
        cmd(['git', 'clone', '--no-hardlinks', a.repo, dest], a.repo)
        m = {'package_sha256': package_sha, 'installed_at': stamp(), 'origin': origin, 'phase': 'cloned'}
        save(marker(dest), m)
    if m['phase'] == 'cloned':
        need(clean(dest), 'Clone has unrecorded edits; preserve it')
        cmd(['git', 'remote', 'set-url', 'origin', m['origin']], dest)
        cmd(['git', 'fetch', 'origin', 'main'], dest)
        m.update(base=cmd(['git', 'rev-parse', 'origin/main'], dest, True), phase='branching')
        save(marker(dest), m)
    if m['phase'] == 'branching':
        need(clean(dest), 'Checkout has unrecorded edits; preserve it')
        r = subprocess.run(['git', 'show-ref', '--verify', '--quiet', 'refs/heads/' + BRANCH], cwd=dest)
        if r.returncode == 0:
            need(cmd(['git', 'rev-parse', BRANCH], dest, True) == m['base'], 'Existing local branch differs')
            cmd(['git', 'switch', BRANCH], dest)
        else:
            cmd(['git', 'switch', '-c', BRANCH, m['base']], dest)
        m['phase'] = 'base'
        save(marker(dest), m)
    if m['phase'] == 'base':
        need(clean(dest), 'Unrecorded edits before applying results')
        m['baseline_validation'] = verify_baseline(dest, m['base'])
        m['phase'] = 'applying'
        save(marker(dest), m)
    if m['phase'] == 'applying':
        apply(dest, m)
        m['phase'] = 'applied'
        save(marker(dest), m)
    if m['phase'] == 'applied':
        checks(dest, m)
        m.update(phase='staged', staged=fingerprint(dest))
        save(marker(dest), m)
    if m['phase'] == 'staged':
        need(fingerprint(dest) == m['staged'] and not cmd(['git', 'diff', '--name-only'], dest, True), 'Prepared files changed')
    event('Completed reconciliation publication prepared', checkout=str(dest), phase=m['phase'],
          measurement_path=m.get('measurement_path'), assessment_path=m.get('assessment_path'), production_started=False)
    return m

def publish(a):
    m = install(a)
    dest = a.publication
    if m.get('merged'):
        event('Already merged', url=m['pr']['url'])
        return
    cmd(['gh', 'auth', 'status'], dest)
    if m['phase'] == 'staged':
        cmd(['git', 'commit', '-m', 'Record completed higher-Q reconciliation and motion-probe assessment'], dest)
        m.update(phase='committed', commit=cmd(['git', 'rev-parse', 'HEAD'], dest, True))
        save(marker(dest), m)
    need(m['phase'] == 'committed' and clean(dest)
         and cmd(['git', 'rev-parse', 'HEAD'], dest, True) == m['commit'], 'Publication checkout changed')
    cmd(['git', 'fetch', 'origin', 'main'], dest)
    need(cmd(['git', 'rev-parse', 'origin/main'], dest, True) == m['base'],
         'Main advanced; preserve this checkout and use a new --publication directory for current main. No reset or force push performed.')
    cmd(['git', 'push', '-u', 'origin', BRANCH], dest)
    body = dest / '.git/reconciliation-results-pr-body.md'
    body.write_text((ROOT / 'PR-BODY.md').read_text())
    prs = json.loads(cmd(['gh', 'pr', 'list', '--repo', REPOSITORY, '--head', BRANCH,
                          '--state', 'all', '--json', 'number,state,headRefOid,url'], dest, True))
    if not prs:
        cmd(['gh', 'pr', 'create', '--repo', REPOSITORY, '--base', 'main', '--head', BRANCH,
             '--title', 'Record completed higher-Q reconciliation and motion-probe assessment', '--body-file', body], dest)
        pr = json.loads(cmd(['gh', 'pr', 'view', BRANCH, '--repo', REPOSITORY,
                             '--json', 'number,state,headRefOid,url'], dest, True))
    else:
        need(len(prs) == 1, 'Ambiguous PR for publication branch')
        pr = prs[0]
    need(pr['headRefOid'] == m['commit'] and pr['state'] in ('OPEN', 'MERGED'), 'Existing PR differs or is closed')
    m['pr'] = pr
    if pr['state'] == 'MERGED':
        m['phase'] = 'merged'
        m['merged'] = {'recorded_at': stamp(), **pr}
    save(marker(dest), m)
    event('Completed results PR recorded', url=pr['url'], state=pr['state'])

def merge(a):
    verify()
    dest = a.publication
    m = load(marker(dest))
    need(m.get('pr'), 'Publish first')
    need(clean(dest) and cmd(['git', 'rev-parse', 'HEAD'], dest, True) == m['commit'], 'Publication checkout changed')
    number = str(m['pr']['number'])
    argv = ['gh', 'pr', 'view', number, '--repo', REPOSITORY,
            '--json', 'state,headRefOid,url,mergeCommit']
    pr = json.loads(cmd(argv, dest, True))
    need(pr['headRefOid'] == m['commit'], 'PR head changed')
    if pr['state'] != 'MERGED':
        need(pr['state'] == 'OPEN', 'PR is not open')
        cmd(['gh', 'pr', 'checks', number, '--repo', REPOSITORY, '--watch', '--interval', '15'], dest)
        cmd(['gh', 'pr', 'merge', number, '--repo', REPOSITORY, '--squash',
             '--match-head-commit', m['commit']], dest)
        pr = json.loads(cmd(argv, dest, True))
    need(pr['state'] == 'MERGED', 'Merge not confirmed')
    m.update(phase='merged', pr=pr, merged={'recorded_at': stamp(), **pr})
    save(marker(dest), m)
    event('Completed reconciliation results merged', url=pr['url'], merge_commit=pr.get('mergeCommit'),
          relaxation_steps=0, physical_time_steps=0)

def status(a):
    m = load(marker(a.publication)) if marker(a.publication).is_file() else {'phase': 'not_installed'}
    event('Publication status', checkout=str(a.publication), phase=m['phase'], pr=m.get('pr'),
          merged=m.get('merged'), measurement_path=m.get('measurement_path'),
          assessment_path=m.get('assessment_path'), production_started=False)

def main():
    p = argparse.ArgumentParser(description='Record completed results only; no numerical analysis modes')
    p.add_argument('mode', choices=['verify', 'install', 'publish', 'merge', 'status'])
    p.add_argument('--repo', type=Path, default=Path.home() / 'ElectronFieldTopology-higher-q-reconciliation-20261117')
    p.add_argument('--publication', type=Path, default=Path.home() / 'ElectronFieldTopology-reconciliation-results-20261117')
    a = p.parse_args()
    a.repo = a.repo.expanduser().resolve()
    a.publication = a.publication.expanduser().resolve()
    if a.mode == 'verify':
        verify()
    else:
        globals()[a.mode](a)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        event('Results publication stopped', error=str(e))
        sys.exit(1)
