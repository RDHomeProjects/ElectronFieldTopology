"""Publish completed reconciliation only, from the user's local workstation."""
import argparse, hashlib, io, json, os, re, shutil, subprocess, sys, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
REPOSITORY = 'RDHomeProjects/ElectronFieldTopology'
BRANCH = 'work/adaptive-q17-q32-screen-20261117'
MARKER = 'adaptive-q17-q32-publication.json'
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


def verify():
    count=verify_manifest(ROOT)
    cfg=load(ROOT/'RESULTS.json')
    need(RID.fullmatch(cfg['record_id']), 'Invalid canonical preparation ID')
    plan=load(ROOT/'PLAN.json')
    need(plan['q_values']==list(range(17,33)) and plan['force_limit']==1e-4 and plan['acceleration_limit']==1e-3, 'Campaign scope/gates differ')
    for f in ROOT.rglob('*.csv'):need(b'\r' not in f.read_bytes(), 'CSV must use LF')
    event('Adaptive screening package verified', payload_files=count, q_values=16, seed_variants=34, production_started=False)
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

def verify_baseline(dest,base):
    cfg=load(ROOT/'RESULTS.json');roadmap=json.loads(cmd(['git','show',base+':docs/project/roadmap.json'],dest,True))
    parent=next((x for x in roadmap['studies'] if x['id']=='s5-b-016'),None)
    need(parent and parent['state']=='assessed' and any(x['role']=='assessment' and x['path']==cfg['parent_assessment'] for x in parent['records']), 'Merged PR79 assessment is required')
    argv=['git','show',base+':'+cfg['parent_results']];event('Command',argv=argv);result=subprocess.run(argv,cwd=dest,capture_output=True)
    need(result.returncode==0 and hashlib.sha256(result.stdout).hexdigest()==cfg['parent_results_sha256'], 'Published prior result identity differs')
    return {'recorded_at':stamp(),'method':'registered assessed parent and exact prior result bytes','publication_base':base,'parent_study':'s5-b-016','parent_results_sha256':cfg['parent_results_sha256'],'ancestry_required':False}

def apply(dest,m):
    cfg=load(ROOT/'RESULTS.json');path=dest/'docs/project/roadmap.json';d=load(path);slug='adaptive-q17-q32-screen'
    parent=next((x for x in d['studies'] if x['id']=='s5-b-016'),None);need(parent and parent['state']=='assessed','Published reconciliation assessment required')
    study=next((x for x in d['studies'] if x['slug']==slug),None)
    if study is None:
        number=max(x['number'] for x in d['studies'] if x['stage']=='s5-b')+1
        study={'id':f's5-b-{number:03d}','stage':'s5-b','number':number,'slug':slug,'title':'Adaptive Q17 to Q32 candidate screening','state':'prepared','gate':'open','question':'Which declared higher-Q starts survive controlled adaptive D4 preparation, mesh/domain checks and bounded coasting screens?','finding':'Campaign prepared, not measured. Curve fits choose additional optimizer iteration counts and observation intervals; original measured gates determine promotion. Native operator comparison is included.','next_action':'Run qualified local CPU/CUDA screening with retained Q2 control, authenticated native Q22 or Q17 comparison, fair bootstrap coverage and bounded adaptive refinement.','exit_evidence':'All declared candidate outcomes, forward-validated fit choices/rejections, measured admission gates, explicit capacity/budget deferrals, full-field hashes and conditional short motion/time-step comparisons.','depends_on':[parent['id']],'requirements':['SCI-001','SCI-003','SCI-004','NUM-001','NUM-002','NUM-003','BND-001','REL-002','REP-001','REP-002'],'specifications':['docs/models/adaptive-q17-q32-screen-20261117.md'],'records':[]};d['studies'].append(study)
    need(study['state']=='prepared','Adaptive screen already advanced; preserve its findings')
    rel=Path('reports')/study['stage']/f"{study['number']:03d}-{slug}"/'preparation'/cfg['record_id'];folder=dest/rel
    if folder.exists():need(load(folder/'record.json')['handover_sha256']==m['package_sha256'],'Existing preparation differs')
    folder.mkdir(parents=True,exist_ok=True)
    save(folder/'record.json',{'study_id':study['id'],'record_id':cfg['record_id'],'role':'preparation','recorded_at':m['installed_at'],'source_commit':m['base'],'handover_sha256':m['package_sha256'],'outcome':'Adaptive Q17-Q32 static screening, native operator bridge, CPU/CUDA qualification and conditional short-motion tests prepared; no production result yet','limitations':['Predicted crossing is not a measured gate pass','No Q sector physically rejected','Full fields remain local until verified archival','No long-time stability or electron acceptance']})
    shutil.copytree(ROOT,folder/'handover',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    (folder/'README.md').write_text('# Adaptive Q17 to Q32 screening preparation\n\n[Run instructions](handover/README.md) · [Frozen plan](handover/PLAN.json) · [Scientific scope](handover/MODEL.md) · [Host validation](handover/HOST-VALIDATION.json) · [Declared catalogue](handover/CATALOGUE.json) · [Retained controls](handover/ANCHORS.json)\n\nPreparation only; no candidate results or CPU/CUDA production measurements have been obtained by this handover build. Scientific gate remains open.\n')
    manifest(folder)
    entry={'role':'preparation','path':(rel/'README.md').as_posix(),'label':'Adaptive batch/fitting policy, native comparison and bounded CPU/CUDA Q17-Q32 campaign'}
    if not any(x['path']==entry['path'] for x in study['records']):study['records'].append(entry)
    spec=dest/study['specifications'][0];spec.parent.mkdir(parents=True,exist_ok=True);link=Path(os.path.relpath(folder/'handover/MODEL.md',spec.parent)).as_posix()
    text='# Adaptive Q17 to Q32 screening scope\n\n'+f'[Frozen campaign and scientific decision rules]({link}).\n\nOne integrated campaign includes the native-grid operator bridge, qualified CPU/CUDA preparation, held-out curve-fit batch allocation and conditional bounded mesh/domain/motion tests. Original gates remain measured requirements; source fields and failures are retained. No long-time or physical acceptance is conferred by preparing this record.\n'
    if spec.exists():need(spec.read_text()==text,'Existing scope differs')
    else:spec.write_text(text)
    priority=d.get('priority',[])
    if study['id'] not in priority:d['priority']=[study['id'] if x==parent['id'] else x for x in priority] if parent['id'] in priority else priority+[study['id']]
    d['updated_at']=m['installed_at'];save(path,d);m.update(study_id=study['id'],preparation_path=rel.as_posix());return m

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
        need(m['package_sha256'] == package_sha, 'Publication belongs to another package; preserve it')
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
    event('Adaptive screening preparation staged', checkout=str(dest), phase=m['phase'],
          preparation_path=m.get('preparation_path'), production_started=False)
    return m

def publish(a):
    m = install(a)
    dest = a.publication
    if m.get('merged'):
        event('Already merged', url=m['pr']['url'])
        return
    cmd(['gh', 'auth', 'status'], dest)
    if m['phase'] == 'staged':
        cmd(['git', 'commit', '-m', 'Prepare adaptive Q17 to Q32 screening campaign'], dest)
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
             '--title', 'Prepare adaptive Q17 to Q32 screening campaign', '--body-file', body], dest)
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
    event('Adaptive screening preparation PR recorded', url=pr['url'], state=pr['state'])

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
    event('Adaptive screening preparation merged', url=pr['url'], merge_commit=pr.get('mergeCommit'),
          relaxation_steps=0, physical_time_steps=0)
