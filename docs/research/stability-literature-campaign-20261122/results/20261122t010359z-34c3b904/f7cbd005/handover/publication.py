"""Additive publication exclusively through the user's local Git/gh tools."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile
from common import ROOT, load, log, need, save, sha, stamp, verify_manifest

REMOTE = 'https://github.com/RDHomeProjects/ElectronFieldTopology.git'
REPOSITORY = 'RDHomeProjects/ElectronFieldTopology'
DOC = Path('docs/research/stability-literature-campaign-20261122')

def command(repo, args, capture=False):
    log('Local publication command', argv=args, checkout=str(repo))
    result = subprocess.run(args, cwd=repo, text=True, capture_output=capture)
    need(result.returncode == 0, 'Command failed: ' + repr(args) + ('\n' + result.stderr if capture else ''))
    return result.stdout.strip() if capture else None

def marker(pub):
    return pub / '.git/stability-literature-publication.json'

def copy_tree(source, target):
    for path in sorted(source.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        dest = target / path.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            need(sha(dest) == sha(path), 'Existing immutable publication payload differs: ' + str(dest))
        else:
            shutil.copy2(path, dest)

def checked_evidence(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        need(z.testzip() is None and len(names) == len(set(names)), 'Evidence CRC/duplicate failure')
        expected = {}
        for line in z.read('SHA256SUMS').decode().splitlines():
            digest, name = line.split('  ', 1)
            member = PurePosixPath(name)
            need(not member.is_absolute() and '..' not in member.parts and name not in expected, 'Unsafe evidence member')
            need(hashlib.sha256(z.read(name)).hexdigest() == digest, 'Evidence payload hash differs: ' + name)
            expected[name] = digest
        need(set(names) == set(expected) | {'SHA256SUMS'}, 'Evidence checksum coverage differs')
        need(not any(name.endswith(('.npz', '.so')) for name in names), 'Full fields/native binaries must remain local')
        return expected

def checks(pub, base):
    command(pub, ['git', 'diff', '--cached', '--check'])
    if (pub / 'scripts/project_records.py').exists():
        command(pub, ['/usr/bin/python3', 'scripts/project_records.py', 'check', '--compare-ref', base])
    if (pub / 'scripts/check_docs.py').exists():
        command(pub, ['/usr/bin/python3', 'scripts/check_docs.py'])

def prepare(repo, pub, results=False):
    verify_manifest(ROOT)
    kind = 'results' if results else 'assessment-and-plan'
    selected = None
    snapshot = sha(ROOT / 'SHA256SUMS')
    if not results:
        from integrity import authenticate
        authenticate(repo)
    if results:
        from handover import live, output
        from supervision import service_active
        selected = output(repo)
        need(not live(selected) and not service_active(), 'Wait for both worker and service to become inactive')
        need(load(selected / 'status.json')['status'] == 'complete_pending_review', 'Record-results requires a completed run; failures remain available for assessment')
        need(load(selected / 'identity.json')['package_sha256'] == snapshot, 'Completed run came from another package')
        checked_evidence(selected / 'evidence.zip')
        for row in load(selected / 'FIELD-MANIFEST.json')['fields']:
            need(sha(selected / row['path']) == row['sha256'], 'Retained output field hash differs: ' + row['path'])
        snapshot = sha(selected / 'evidence.zip')
    state = load(marker(pub)) if marker(pub).exists() else None
    if state and not results and state['kind'] == 'results':
        need(state['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Package identity differs')
        log('Assessment and plan already precede the results publication; retained index links unchanged')
        return state
    if state and state['kind'] == kind and state['snapshot_sha256'] == snapshot:
        need(state['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Publication package identity differs')
        if state['phase'] in ['applied', 'committed', 'published', 'merged']:
            if state['phase'] == 'applied':
                checks(pub, state['base'])
            log('Publication already prepared', phase=state['phase'], kind=kind)
            return state
    need(not state or state['phase'] == 'merged' or (state['phase'] == 'staging' and state['kind'] == kind and state['snapshot_sha256'] == snapshot), 'Finish the current publication before staging another snapshot')
    if not state or state['kind'] != kind or state['snapshot_sha256'] != snapshot:
        if not pub.exists():
            subprocess.run(['git', 'clone', '--no-hardlinks', str(repo), str(pub)], check=True)
            command(pub, ['git', 'remote', 'set-url', 'origin', REMOTE])
        else:
            need(command(pub, ['git', 'remote', 'get-url', 'origin'], True) in [REMOTE, REMOTE.removesuffix('.git'), 'git@github.com:' + REPOSITORY + '.git'], 'Unexpected publication remote')
        need(not command(pub, ['git', 'status', '--porcelain'], True), 'Publication checkout has local changes; preserve them before continuing')
        command(pub, ['git', 'fetch', 'origin', 'main'])
        base = command(pub, ['git', 'rev-parse', 'origin/main'], True)
        branch = 'analysis/stability-literature-' + kind + '-20261122-' + snapshot[:8]
        command(pub, ['git', 'switch', '-c', branch, base])
        state = {'recorded_at': stamp(), 'kind': kind, 'phase': 'staging', 'base': base, 'branch': branch, 'snapshot_sha256': snapshot, 'package_sha256': sha(ROOT / 'SHA256SUMS'), 'pr': None}
        save(marker(pub), state)
    need(command(pub, ['git', 'branch', '--show-current'], True) == state['branch'], 'Publication branch changed')
    destination = pub / DOC
    destination.mkdir(parents=True, exist_ok=True)
    (destination / '.gitattributes').write_text('results/** -text -diff\npreparation/** -text -diff\nassessment/data/** -text -diff\n')
    if results:
        relative = Path('results') / load(selected / 'identity.json')['run_id'] / snapshot[:8]
        target = destination / relative
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(selected / 'evidence.zip') as z:
            for name in z.namelist():
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                content = z.read(name)
                if path.exists():
                    need(path.read_bytes() == content, 'Existing result snapshot differs: ' + name)
                else:
                    path.write_bytes(content)
        zip_target = target / 'evidence.zip'
        if zip_target.exists():
            need(sha(zip_target) == snapshot, 'Existing published evidence differs')
        else:
            shutil.copy2(selected / 'evidence.zip', zip_target)
        addition = '\n\nCompleted evaluations: [browser report](' + (relative / 'REPORT.html').as_posix() + ') · [full measured record](' + (relative / 'record.json').as_posix() + ').\n'
    else:
        copy_tree(ROOT / 'assessment', destination / 'assessment')
        for name in ['LITERATURE.md','OPTIONS-PLAN.md','literature.bib','PLAN.json']:
            shutil.copy2(ROOT/name,destination/name)
        copy_tree(ROOT, destination / 'preparation' / snapshot[:8] / 'handover')
        addition = '\n\nRecorded scientific assessment: [browser report](assessment/ASSESSMENT.html) · [Markdown assessment](assessment/ASSESSMENT.md).\n\nLiterature applicability: [review](LITERATURE.md) · [option coverage](OPTIONS-PLAN.md).\n\nControlled preparation plan: [PLAN.json](PLAN.json). Nineteen independently initialized arms, at most2300 new charged optimizer attempts across all arms; unchanged action and original gates.\n'
    index = destination / 'README.md'
    current = index.read_text() if index.exists() else '# Literature-guided stability diagnosis\n\nHistorical cell-functional static successes, current D4 readiness and physical-time stability are separate claims. This record adds to existing reports and graphics.\n'
    if addition.strip() not in current:
        index.write_text(current.rstrip() + addition)
    readme = pub / 'README.md'
    link = '[Literature-guided stability diagnosis](' + DOC.as_posix() + '/README.md)'
    if link not in readme.read_text():
        readme.write_text(readme.read_text().rstrip() + '\n\n' + link + '\n')
    bibliography=pub/'docs/literature/stability-diagnosis-20261122.bib'
    bibliography.parent.mkdir(parents=True,exist_ok=True)
    if bibliography.exists():
        need(sha(bibliography)==sha(ROOT/'literature.bib'),'Existing bibliography supplement differs')
    else:shutil.copy2(ROOT/'literature.bib',bibliography)
    literature_index=pub/'docs/literature/README.md'
    if literature_index.exists():
        link='[Stability diagnosis bibliography](stability-diagnosis-20261122.bib)'
        if link not in literature_index.read_text():literature_index.write_text(literature_index.read_text().rstrip()+'\n\n'+link+' — focused reference-chain review and controlled experiments.\n')
    command(pub, ['git','add','--','README.md',DOC.as_posix(),'docs/literature'])
    state['phase'] = 'applied'
    save(marker(pub), state)
    checks(pub, state['base'])
    log('Assessment or completed evaluations staged locally', kind=kind, branch=state['branch'], destination=str(destination))
    return state

def pr_view(pub, reference):
    return json.loads(command(pub, ['gh', 'pr', 'view', str(reference), '--repo', REPOSITORY, '--json', 'number,url,state,headRefOid,mergeCommit,headRefName,baseRefName'], True))

def execute(mode, repo, pub):
    if mode in ['install', 'record-results']:
        prepare(repo, pub, mode == 'record-results')
        return
    need(marker(pub).exists(), 'Install the assessment before publication')
    state = load(marker(pub))
    need(state['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Publication package changed')
    if state['phase'] == 'merged':
        log('Already merged', pr=state['pr'])
        return
    need(command(pub, ['git', 'branch', '--show-current'], True) == state['branch'], 'Publication branch changed')
    if mode == 'publish':
        if state['phase'] == 'applied':
            checks(pub, state['base'])
            command(pub, ['git', 'commit', '-m', 'Record literature-guided stability ' + state['kind']])
            state.update(phase='committed', commit=command(pub, ['git', 'rev-parse', 'HEAD'], True))
            save(marker(pub), state)
        need(not command(pub, ['git', 'status', '--porcelain'], True), 'Publication changed after commit')
        need(command(pub, ['git', 'rev-parse', 'HEAD'], True) == state['commit'], 'Publication head changed')
        command(pub, ['git', 'push', '-u', 'origin', state['branch']])
        probe = subprocess.run(['gh', 'pr', 'view', state['branch'], '--repo', REPOSITORY, '--json', 'url'], cwd=pub, text=True, capture_output=True)
        if probe.returncode == 0:
            url = json.loads(probe.stdout)['url']
        else:
            title = 'Record Q21 final scientific assessment and literature-guided stability plan' if state['kind'] == 'assessment-and-plan' else 'Record controlled literature-guided stability outcomes'
            url = command(pub, ['gh', 'pr', 'create', '--repo', REPOSITORY, '--base', 'main', '--head', state['branch'], '--title', title, '--body-file', str(ROOT / 'PR-BODY.md')], True).splitlines()[-1]
        pr = pr_view(pub, url)
        need(pr['headRefOid'] == state['commit'] and pr['baseRefName'] == 'main', 'PR head/base differs')
        state.update(phase='published', pr=pr)
        save(marker(pub), state)
        log('Publication PR created or verified', pr=pr)
    else:
        need(state['phase'] == 'published', 'Publish before merging')
        pr = pr_view(pub, state['pr']['url'])
        need(pr['headRefOid'] == state['commit'], 'PR head changed; review required')
        if pr['state'] != 'MERGED':
            need(pr['state'] == 'OPEN', 'PR is not open or merged')
            rollup = json.loads(command(pub, ['gh', 'pr', 'view', pr['url'], '--repo', REPOSITORY, '--json', 'statusCheckRollup'], True))
            if rollup['statusCheckRollup']:
                command(pub, ['gh', 'pr', 'checks', pr['url'], '--repo', REPOSITORY, '--watch', '--interval', '10'])
            else:
                log('No remote checks registered; local checks passed and repository merge protections remain enforced')
            command(pub, ['gh', 'pr', 'merge', pr['url'], '--repo', REPOSITORY, '--squash', '--delete-branch', '--match-head-commit', state['commit']])
            pr = pr_view(pub, pr['url'])
        need(pr['state'] == 'MERGED' and pr.get('mergeCommit'), 'Merge did not complete')
        state.update(phase='merged', pr=pr)
        save(marker(pub), state)
        log('Publication merged', pr=pr)
