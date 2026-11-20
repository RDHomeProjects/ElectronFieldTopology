"""Additive local-workstation-only publication; prior reports are preserved."""
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile
from common import ROOT, load, log, need, save, sha, stamp, verify_manifest
from integrity import COMPLETED_SHA, checked_zip, collect_completed
REMOTE = 'https://github.com/RDHomeProjects/ElectronFieldTopology.git'
REPOSITORY = 'RDHomeProjects/ElectronFieldTopology'
DOC = Path('docs/research/q17-q32-results-field-diagnosis-20261120')

def copy_exact_tree(source, destination):
    for path in sorted(source.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.name.endswith(('.tmp', '.lock')):
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            need(sha(target) == sha(path), 'Existing staged file differs: ' + str(target))
        else:
            shutil.copy2(path, target)

def prepare(repo, pub, results=False):
    verify_manifest(ROOT)
    kind = 'diagnosis' if results else 'completed-results'
    snapshot = COMPLETED_SHA
    if results:
        from handover import live, service_active
        selected_output = Path(load(repo / '.git/field-diagnosis-last.json')['output'])
        need(not live(selected_output) and not service_active(), 'Wait until the diagnostic worker and service are inactive')
        snapshot = sha(selected_output / 'evidence.zip')
    state = load(marker(pub)) if marker(pub).exists() else None
    if not results and state and state['kind'] == 'diagnosis':
        need(state['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Publication package differs')
        log('Completed source result was already recorded before the diagnostic publication; prior index links are preserved')
        return state
    if state and state['kind'] == kind and state.get('source_snapshot_sha256') == snapshot:
        need(state['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Publication package differs')
        if state['phase'] in ('applied', 'committed', 'published', 'merged'):
            if state['phase'] == 'applied':
                checks(pub, state['base'])
            log('Record already prepared', **state)
            return state
    need(not state or state['phase'] == 'merged' or (state['phase'] == 'staging' and state['kind'] == kind and state.get('source_snapshot_sha256') == snapshot), 'Complete the existing local publication first')
    if not state or state['kind'] != kind or state.get('source_snapshot_sha256') != snapshot:
        if not pub.exists():
            subprocess.run(['git', 'clone', '--no-hardlinks', str(repo), str(pub)], check=True)
            command(pub, ['git', 'remote', 'set-url', 'origin', REMOTE])
        else:
            remote = command(pub, ['git', 'remote', 'get-url', 'origin'], True)
            need(remote in (REMOTE, REMOTE.removesuffix('.git'), 'git@github.com:' + REPOSITORY + '.git'), 'Unexpected publication remote')
        need(not command(pub, ['git', 'status', '--porcelain'], True), 'Publication clone has local changes; preserve them before continuing')
        command(pub, ['git', 'fetch', 'origin', 'main'])
        base = command(pub, ['git', 'rev-parse', 'origin/main'], True)
        suffix = load(repo / '.git/field-diagnosis-last.json')['output'].rstrip('/').split('/')[-1] + '-' + snapshot[:8] if results else '20261120'
        branch = 'analysis/q17-q32-' + ('field-diagnosis-' if results else 'completed-results-and-diagnosis-') + suffix
        command(pub, ['git', 'switch', '-c', branch, base])
        state = {'recorded_at': stamp(), 'kind': kind, 'phase': 'staging', 'branch': branch, 'base': base, 'package_sha256': sha(ROOT / 'SHA256SUMS'), 'source_snapshot_sha256': snapshot, 'pr': None}
        save(marker(pub), state)
    need(command(pub, ['git', 'branch', '--show-current'], True) == state['branch'], 'Staging branch differs')
    destination = pub / DOC
    destination.mkdir(parents=True, exist_ok=True)
    # Immutable logs and prior source blobs are data, not editable code/docs.
    # Preserve their bytes even when they contain historical whitespace.
    attributes = '# Byte-exact retained data; code and documentation checks remain enabled.\n**/*.log -diff\n**/*.jsonl -diff\n**/prior-records/** -diff\n'
    attribute_path = destination / '.gitattributes'
    if attribute_path.exists():
        need(attribute_path.read_text() == attributes, 'Research record attributes differ')
    else:
        attribute_path.write_text(attributes)
    if not results:
        copy_exact_tree(ROOT, destination / 'handover')
        collection = collect_completed(repo, destination / 'completed/20261120t003653z-a200a9db')
        text = '# Complete Q17–Q32 results and retained-field diagnosis\n\n'
        text += 'The corrected continuation completed with 225 additional attempts. All six candidates remain preparation-unresolved and fail both boundary checks. The complete consolidated record retains 34 seed dispositions; no stationary high-Q parent was admitted. All 500-total-attempt ceilings and scientific gates are preserved.\n\n'
        text += '[Completed browser report](completed/20261120t003653z-a200a9db/REPORT.html) · [Structured result](completed/20261120t003653z-a200a9db/record.json) · [Full non-field collection](completed/20261120t003653z-a200a9db/COLLECTION.json)\n\n'
        text += '[Assessment with measured plots](handover/assessment/ASSESSMENT.html) · [Diagnosis instructions](handover/README.md) · [Frozen diagnosis plan](handover/PLAN.json) · [Prior recorded operator context](handover/PRIOR-CONTEXT.json)\n\n'
        text += 'This record includes all non-field files, logs, telemetry and the full executed handover, not only the compact ZIP filter. The 36 float64 NPZ files remain local with their original hashes; preflight additionally verifies Q2, for 37 field hash/CRC checks. No remote full-field archive is claimed. Existing earlier graphics and findings are preserved.\n\n'
        text += 'The planned diagnosis has zero optimizer steps and zero physical-time steps. It compares Q2, Q21 parent/endpoint and Q22 parent/endpoint without resampling or changing gates, then reconciles differences in field identity, operator, grid and metric definitions. No claim of a resolved same-field disagreement is made before replay.\n'
        (destination / 'README.md').write_text(text)
    else:
        from handover import live, service_active
        out = Path(load(repo / '.git/field-diagnosis-last.json')['output'])
        need(not live(out) and not service_active(), 'Wait for the completed diagnostic worker/service to become inactive before recording')
        actual_status = load(out / 'status.json')['status']
        need(actual_status in ('complete_pending_review', 'interrupted', 'failed'), 'Only an inactive terminal/paused diagnosis can be recorded')
        with zipfile.ZipFile(out / 'evidence.zip') as z:
            checked_zip(z)
            record = json.loads(z.read('record.json'))
        need(record['status'] == actual_status and record['optimizer_steps'] == record['physical_time_steps'] == 0, 'Unexpected diagnostic scope')
        need(record['identity']['package_sha256'] == sha(ROOT / 'SHA256SUMS'), 'Diagnostic identity differs')
        if actual_status == 'complete_pending_review':
            need(len(record['cases']) == 5, 'Completed diagnosis coverage differs')
        need(sha(out / 'evidence.zip') == snapshot, 'Diagnostic snapshot changed during publication preparation')
        need(not list(out.rglob('*.npz')), 'Unexpected full-field file in diagnostic output; fields are retained in their original source runs')
        revision = actual_status + '-' + snapshot[:8]
        relative = 'diagnosis/' + record['identity']['run_id'] + '/' + revision
        target = destination / relative
        copy_exact_tree(out, target)
        index = destination / 'README.md'
        line = '\n\nField diagnosis (' + actual_status + '): [browser report](' + relative + '/REPORT.html) · [claim reconciliation](' + relative + '/RECONCILIATION.json).\n'
        current = index.read_text() if index.exists() else '# Retained-field diagnosis\n'
        if line.strip() not in current:
            index.write_text(current.rstrip() + line)
    readme = pub / 'README.md'
    link = '[Q17–Q32 complete results, assessment and retained-field diagnosis](' + DOC.as_posix() + '/README.md)'
    if link not in readme.read_text():
        readme.write_text(readme.read_text().rstrip() + '\n\n' + link + '\n')
    command(pub, ['git', 'add', '--', 'README.md', DOC.as_posix()])
    state['phase'] = 'applied'
    save(marker(pub), state)
    checks(pub, state['base'])
    log('Complete result or diagnosis staged locally', **state)
    return state

def command(repo, args, capture=False):
    log('Local publication command', argv=args, checkout=str(repo))
    p = subprocess.run(args, cwd=repo, text=True, capture_output=capture)
    need(p.returncode == 0, 'Command failed: ' + repr(args) + ('\n' + p.stderr if capture else ''))
    return p.stdout.strip() if capture else None

def marker(pub):
    return pub / '.git/field-diagnosis-publication.json'

def checks(pub, base):
    command(pub, ['git', 'diff', '--cached', '--check'])
    if (pub / 'scripts/project_records.py').exists():
        command(pub, ['/usr/bin/python3', 'scripts/project_records.py', 'check', '--compare-ref', base])
    if (pub / 'scripts/check_docs.py').exists():
        command(pub, ['/usr/bin/python3', 'scripts/check_docs.py'])

def pr_view(pub, reference):
    return json.loads(command(pub, ['gh', 'pr', 'view', str(reference), '--repo', REPOSITORY, '--json', 'number,url,state,headRefOid,mergeCommit,headRefName,baseRefName'], True))

def execute(mode, repo, pub):
    if mode in ('install', 'record-diagnosis'):
        prepare(repo, pub, mode == 'record-diagnosis')
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
            command(pub, ['git', 'commit', '-m', 'Record Q17-Q32 results and field diagnosis: ' + state['kind']])
            state.update(phase='committed', commit=command(pub, ['git', 'rev-parse', 'HEAD'], True))
            save(marker(pub), state)
        need(not command(pub, ['git', 'status', '--porcelain'], True), 'Publication checkout changed after commit')
        need(command(pub, ['git', 'rev-parse', 'HEAD'], True) == state['commit'], 'Committed publication head changed')
        command(pub, ['git', 'push', '-u', 'origin', state['branch']])
        probe = subprocess.run(['gh', 'pr', 'view', state['branch'], '--repo', REPOSITORY, '--json', 'url'], cwd=pub, text=True, capture_output=True)
        if probe.returncode == 0:
            url = json.loads(probe.stdout)['url']
        else:
            title = 'Record complete Q17–Q32 results, assessment and reconciliation diagnosis plan' if state['kind'] == 'completed-results' else 'Record retained-field diagnosis and prior-result reconciliation'
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
