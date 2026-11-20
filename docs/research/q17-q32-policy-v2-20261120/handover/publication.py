"""GitHub actions execute only when this file is run on the local workstation."""
from pathlib import Path, PurePosixPath
import json
import re
import shutil
import subprocess
import zipfile
from common import ROOT, load, log, need, save, sha, stamp, verify_manifest

REMOTE = 'https://github.com/RDHomeProjects/ElectronFieldTopology.git'
REPOSITORY = 'RDHomeProjects/ElectronFieldTopology'
DOC = Path('docs/research/q17-q32-policy-v2-20261120')

def command(repo, args, capture=False):
    log('Local publication command', argv=args, checkout=str(repo))
    p = subprocess.run(args, cwd=repo, text=True, capture_output=capture)
    need(p.returncode == 0, 'Command failed: ' + repr(args) + ('\n' + p.stderr if capture else ''))
    return p.stdout.strip() if capture else None

def marker(pub):
    return pub / '.git/policy-v2-publication.json'

def checks(pub, base):
    command(pub, ['git', 'diff', '--cached', '--check'])
    if (pub / 'scripts/project_records.py').exists():
        command(pub, ['/usr/bin/python3', 'scripts/project_records.py', 'check', '--compare-ref', base])
    if (pub / 'scripts/check_docs.py').exists():
        command(pub, ['/usr/bin/python3', 'scripts/check_docs.py'])

def inspect_compact(path):
    import hashlib
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        need(len(names) == len(set(names)) and z.testzip() is None, 'Result evidence CRC/duplicate failure')
        seen = set()
        for line in z.read('SHA256SUMS').decode().splitlines():
            h, name = line.split('  ', 1)
            p = PurePosixPath(name)
            need(not p.is_absolute() and '..' not in p.parts and name not in seen, 'Unsafe result archive member')
            need(hashlib.sha256(z.read(name)).hexdigest() == h, 'Result checksum differs: ' + name)
            seen.add(name)
        need(seen == set(names) - {'SHA256SUMS'}, 'Result compact coverage differs')
        record = json.loads(z.read('record.json'))
        need(record['status'] == 'complete_pending_review', 'Only completed continuation results can be recorded by this command')
        specs = {x['id']: x for x in load(ROOT / 'SELECTION.json')['branches']}
        need(len(record['branches']) == 6 and {x['seed']['id'] for x in record['branches']} == set(specs), 'Result branch selection differs')
        for row in record['branches']:
            spec = specs[row['seed']['id']]
            need(row['status'] not in ('active', 'pending') and spec['already_spent_attempts'] <= row['attempts'] <= 500, 'Result is unfinished or exceeds its allocation')
            need(row['additional_attempts'] == row['attempts'] - spec['already_spent_attempts'], 'Result attempt accounting differs')
        need(sum(x['additional_attempts'] for x in record['branches']) == record['additional_attempts'], 'Aggregate result accounting differs')
        need(not any(n.endswith('.npz') for n in names), 'Compact publication unexpectedly contains full fields')
        need(record['maximum_additional_attempts'] == 1738 and record['additional_attempts'] <= 1738, 'Result allocation differs')
        need(record['identity']['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Result package identity differs')
        return record

def prepare(repo, pub, results=False):
    verify_manifest(ROOT)
    kind = 'results' if results else 'preparation'
    current = load(marker(pub)) if marker(pub).exists() else None
    if current and current['kind'] == kind:
        need(current['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Publication package identity differs')
        if current['phase'] in ('applied', 'committed', 'published', 'merged'):
            if current['phase'] == 'applied':
                checks(pub, current['base'])
            log('Publication record already prepared', **current)
            return current
    need(not current or current['phase'] == 'merged', 'Finish the existing publication before preparing results')
    if not pub.exists():
        subprocess.run(['git', 'clone', '--no-hardlinks', str(repo), str(pub)], check=True)
        command(pub, ['git', 'remote', 'set-url', 'origin', REMOTE])
    else:
        remote = command(pub, ['git', 'remote', 'get-url', 'origin'], True)
        need(remote in (REMOTE, REMOTE.removesuffix('.git'), 'git@github.com:' + REPOSITORY + '.git'), 'Unexpected publication remote')
    need(not command(pub, ['git', 'status', '--porcelain'], True), 'Publication checkout has local changes; preserve them before proceeding')
    command(pub, ['git', 'fetch', 'origin', 'main'])
    base = command(pub, ['git', 'rev-parse', 'origin/main'], True)
    branch = 'analysis/q17-q32-policy-v2-' + ('results-' + load(repo / '.git/policy-v2-last-run.json')['output'].rstrip('/').split('/')[-1] if results else 'recovery-20261120')
    command(pub, ['git', 'switch', '-c', branch, base])
    destination = pub / DOC
    destination.mkdir(parents=True, exist_ok=True)
    if not results:
        pack = destination / 'handover'
        shutil.copytree(ROOT, pack, ignore=shutil.ignore_patterns('__pycache__'))
        (destination / 'README.md').write_text('# Q17–Q32 stopping-policy audit and targeted recovery\n\n'
            'The actual-history audit reproduces 881 decisions and identifies six unsupported preparation stops. '
            'Twenty-three other preparation stops and five representation cases remain unchanged. No broad endpoint passed stationarity; all 29 representation-admitted endpoints failed boundary admission.\n\n'
            'The recovery preserves the six exact CUDA optimizer parents, CG memory, alpha, grid, box, float64 precision and scientific gates. '
            'Each selected branch receives a 500-total-attempt ceiling, including original/interrupted work: at most 1,738 additional attempts. '
            'Corrected epoch-local plateau evidence and validated curve fits still control shorter allocations and early stopping. '
            'Mesh/domain/motion remain deferred pending preparation review; the 33 spent Q18 mesh attempts stay recorded.\n\n'
            '[Browser audit](handover/assessment/ASSESSMENT.html) · [Audit assessment](handover/assessment/ASSESSMENT.md) · '
            '[Run instructions](handover/README.md) · [Frozen plan](handover/PLAN.json) · [Six-parent allocation](handover/SELECTION.json)\n\n'
            'This preparation record starts no simulation and does not claim any candidate passes. Numerical work and GitHub operations run only on the local workstation.\n')
    else:
        out = Path(load(repo / '.git/policy-v2-last-run.json')['output'])
        record = inspect_compact(out / 'evidence.zip')
        target = destination / 'results' / record['identity']['run_id']
        need(not target.exists(), 'Result destination already exists; do not overwrite retained records')
        target.mkdir(parents=True)
        with zipfile.ZipFile(out / 'evidence.zip') as z:
            for name in z.namelist():
                p = target / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(z.read(name))
        shutil.copy2(out / 'evidence.zip', target / 'evidence.zip')
        index = destination / 'README.md'
        prior = index.read_text() if index.exists() else '# Q17–Q32 policy-v2 continuation\n'
        index.write_text(prior.rstrip() + '\n\nCompleted continuation: [browser report](results/' + record['identity']['run_id'] + '/REPORT.html) · [structured results](results/' + record['identity']['run_id'] + '/record.json).\n')
    readme = pub / 'README.md'
    link = '[Q17–Q32 stopping-policy audit and targeted continuation](' + DOC.as_posix() + '/README.md)'
    if link not in readme.read_text():
        readme.write_text(readme.read_text().rstrip() + '\n\n' + link + '\n')
    current = {'recorded_at': stamp(), 'kind': kind, 'phase': 'applied', 'branch': branch, 'base': base,
               'package_sha256': sha(ROOT / 'SHA256SUMS'), 'pr': None}
    save(marker(pub), current)
    command(pub, ['git', 'add', '--', 'README.md', DOC.as_posix()])
    checks(pub, base)
    log('Publication changes prepared locally', **current)
    return current

def pr_view(pub, reference):
    return json.loads(command(pub, ['gh', 'pr', 'view', str(reference), '--repo', REPOSITORY, '--json', 'number,url,state,headRefOid,mergeCommit,headRefName,baseRefName'], True))

def execute(mode, repo, pub):
    if mode in ('install', 'record-results'):
        prepare(repo, pub, mode == 'record-results')
        return
    need(marker(pub).exists(), 'Install the publication record first')
    state = load(marker(pub))
    need(state['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Publication package identity differs')
    if state['phase'] == 'merged':
        log('Already merged', pr=state['pr'])
        return
    need(command(pub, ['git', 'branch', '--show-current'], True) == state['branch'], 'Publication branch differs')
    if mode == 'publish':
        if state['phase'] == 'applied':
            command(pub, ['git', 'add', '--', 'README.md', DOC.as_posix()])
            checks(pub, state['base'])
            command(pub, ['git', 'commit', '-m', 'Record Q17-Q32 policy-v2 ' + state['kind']])
            state.update(phase='committed', commit=command(pub, ['git', 'rev-parse', 'HEAD'], True))
            save(marker(pub), state)
        need(not command(pub, ['git', 'status', '--porcelain'], True), 'Publication checkout changed after commit')
        need(command(pub, ['git', 'rev-parse', 'HEAD'], True) == state['commit'], 'Committed publication head changed')
        command(pub, ['git', 'push', '-u', 'origin', state['branch']])
        probe = subprocess.run(['gh', 'pr', 'view', state['branch'], '--repo', REPOSITORY, '--json', 'url'], cwd=pub, text=True, capture_output=True)
        if probe.returncode == 0:
            url = json.loads(probe.stdout)['url']
        else:
            title = 'Record Q17–Q32 policy audit and 500-attempt targeted recovery' if state['kind'] == 'preparation' else 'Record Q17–Q32 corrected-policy continuation results'
            url = command(pub, ['gh', 'pr', 'create', '--repo', REPOSITORY, '--base', 'main', '--head', state['branch'], '--title', title, '--body-file', str(ROOT / 'PR-BODY.md')], True).splitlines()[-1]
        pr = pr_view(pub, url)
        need(pr['headRefOid'] == state['commit'] and pr['baseRefName'] == 'main', 'PR head/base differs from the reviewed local record')
        state.update(phase='published', pr=pr)
        save(marker(pub), state)
        log('Publication PR created or verified', pr=pr)
    else:
        need(state['phase'] == 'published', 'Publish the record before merging')
        pr = pr_view(pub, state['pr']['url'])
        need(pr['headRefOid'] == state['commit'], 'PR head changed; no automatic merge of unreviewed content')
        if pr['state'] != 'MERGED':
            need(pr['state'] == 'OPEN', 'PR is not open or merged')
            rollup = json.loads(command(pub, ['gh', 'pr', 'view', pr['url'], '--repo', REPOSITORY, '--json', 'statusCheckRollup'], True))
            if rollup['statusCheckRollup']:
                command(pub, ['gh', 'pr', 'checks', pr['url'], '--repo', REPOSITORY, '--watch', '--interval', '10'])
            else:
                log('No PR checks registered; local checks passed and repository merge protections remain enforced')
            command(pub, ['gh', 'pr', 'merge', pr['url'], '--repo', REPOSITORY, '--squash', '--delete-branch', '--match-head-commit', state['commit']])
            pr = pr_view(pub, pr['url'])
        need(pr['state'] == 'MERGED' and pr.get('mergeCommit'), 'Merge did not complete')
        state.update(phase='merged', pr=pr)
        save(marker(pub), state)
        log('Publication merged', pr=pr)
