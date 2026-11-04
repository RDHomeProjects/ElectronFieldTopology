"""Render and validate the administrative project record. Standard library; Apache-2.0.

This checks provenance/navigation, not numerical or scientific acceptance.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if not __debug__:
    raise RuntimeError('Run the administrative validator without Python optimization (-O).')
REGISTRY = 'docs/project/roadmap.json'
BASELINE = 'docs/project/layout-baseline.json'
STATES = {'planned', 'prepared', 'running', 'recorded', 'assessed', 'deferred'}
GATES = {'open', 'bounded', 'blocked', 'not-applicable'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def immutable_changes(root, ref):
    """Previously published canonical records are append-only, including their hashes."""
    assert re.fullmatch(r'[0-9a-f]{40}', ref), 'A complete comparison commit is required'
    rows=subprocess.check_output(['git','diff','--no-renames','--name-status','-z',ref,'--','reports/'],cwd=root).decode().split('\0')[:-1]
    for status,name in zip(rows[::2],rows[1::2]):
        parts=Path(name).parts
        if len(parts)>=6 and parts[3] in {'runs','preparation','assessments'}:
            assert status=='A', 'Published record is immutable; append a superseding assessment: '+name


def link(source, target, label):
    return f'[{label}]({os.path.relpath(target, Path(source).parent).replace(os.sep, "/")})'


def stamp(data):
    t = data['updated_at']
    return f'Updated: UTC {t["utc"]}; Australia/Melbourne {t["melbourne"]}.\n'


def ancestors(text):
    """GitHub-style ASCII headings used by the pre-migration navigation pages."""
    used = {}
    for line in text.splitlines():
        if not re.match(r'^#{1,6} ', line):
            continue
        heading = re.sub(r'[*_`]', '', line.lstrip('# ').lower())
        slug = re.sub(r'[^\w\- ]', '', heading).replace(' ', '-')
        n = used.get(slug, 0)
        used[slug] = n + 1
        yield slug + (f'-{n}' if n else '')


def compatibility(root, name, text):
    old = root / 'docs/history/layout-20261104' / (name.replace('/', '__') + '.txt')
    if not old.exists():
        return text
    missing = [a for a in ancestors(old.read_text()) if a not in set(ancestors(text))]
    if missing:
        text += '\n## Historical section links\n\n'
        text += link(name, old.relative_to(root).as_posix(), 'Exact pre-reconciliation document') + '. '
        text += 'The following anchors retain former section links; use the current roadmap above.\n\n'
        text += '\n'.join(f'<a id="{a}"></a>' for a in missing) + '\n'
    return text


def documents(data, root=ROOT):
    result = {}
    studies = data['studies']
    by_id = {s['id']: s for s in studies}
    def add(path, text):
        result[path] = compatibility(root, path, text.rstrip() + '\n')
    def planpath(s):
        return f'docs/plans/{s["stage"]}/{s["number"]:03d}-{s["slug"]}.md'
    def reportpath(s):
        return f'reports/{s["stage"]}/{s["number"]:03d}-{s["slug"]}/README.md'
    def study_table(path, items):
        lines = ['| Study | Activity | State | Scientific gate |', '|---|---|---|---|']
        for s in items:
            lines.append(f'| {link(path, planpath(s), s["id"])} | {s["title"]} | {s["state"]} | {s["gate"]} |')
        return '\n'.join(lines) + '\n'
    stages = data['stages']
    p = 'docs/06-development-plan.md'
    t = '# Staged development plan\n\n' + stamp(data)
    t += '\nThis is the current roadmap, generated from ' + link(p, REGISTRY, 'the project register') + '. '
    t += 'Study state and scientific acceptance are separate. An assessed run can retain an open or blocked gate.\n'
    t += '\n## Current priority\n\nAdministrative reconciliation is prepared in this change. '
    t += 'After it is merged, the next scientific task is **s5-b-005: boost initialization and field registration**, '
    t += 'using retained fields before another production matrix. PR54 recorded the completed diagnostics; it did not close general motion acceptance.\n'
    t += '\n## Stage map\n\n| Stage | Responsibility | Current scope |\n|---|---|---|\n'
    for st in stages:
        t += f'| {link(p, "reports/"+st["id"]+"/INDEX.md", st["id"].upper())} | {st["title"]} | {st["scope"]} |\n'
    t += '\n## Ordered work and dependencies\n\n'
    for n, sid in enumerate(data['priority'], 1):
        s = by_id[sid]
        t += f'{n}. {link(p, planpath(s), s["id"]+": "+s["title"])} — {s["next_action"]}\n'
    t += '\n## Parallel and conditional work\n\nCharged-theory feasibility may proceed analytically in parallel. '
    t += 'Q1/Q2 symmetry and collective-coordinate methods require converged kinetic metrics; '
    t += 'quantization assumptions are explicit, and are separate from a classical-emergence claim. '
    t += 'External-field, Stern–Gerlach and wavefunction-observable tests require justified coupling, state preparation and detector models. '
    t += 'Energy density is not automatically a Born position probability. Renderer profiles affect display data only.\n'
    t += '\n## Stop and reassess rules\n\nPreserve negative findings. Do not relax gates to obtain a pass. '
    t += 'A missing input or integrity mismatch blocks dependent claims. Do not launch a new 60-case matrix automatically. '
    t += 'Three diagnostic sampling grids do not constitute three physical solver resolutions. '
    t += 'No arbitrary overall two-hour limit is imposed; use checkpointed, documented local work.\n'
    t += '\n## Plan maintenance\n\nEdit the register and the applicable study specification in the same PR as a scope or priority change. '
    t += 'Run `python3 scripts/project_records.py render`, then `python3 scripts/project_records.py check`. '
    t += 'Historical decisions stay in ADRs and immutable reports; do not prepend another competing current plan.\n'
    add(p, t)
    p = 'docs/STATUS.md'
    t = '# Project status\n\n' + stamp(data)
    t += '\n## Current position\n\nReviewed baseline: PR54, commit `' + data['baseline_commit'] + '`. '
    t += 'The latest completed scientific activity is **s5-b-004**, the retained-field motion diagnostic assessment. '
    t += 'The administration update is prepared; no new trajectory is produced.\n'
    t += '\nThe review records 540 endpoint numeric comparisons with zero mismatch, 6 rest metrics and 70 pair records. '
    t += 'The original 6 bounded passes and overlapping 50 tail, 18 shape and 4 momentum failures remain unchanged. '
    t += 'Initial internal-field-rate mismatch is 5.99–10.98%; maximum temporal final-field difference is 0.000038%. '
    t += 'Cross-box raw-field and inertia sensitivity remain unresolved. These are different observables, not interchangeable speed errors.\n'
    t += '\n## Next scientific task\n\n' + link(p, planpath(by_id['s5-b-005']), 's5-b-005: initialization and field registration')
    t += ': compare the current initializer with a smoother, consistently differentiated variant; '
    t += 'validate independent exact-node/off-node/boundary controls; separate initial-state and comoving evolution differences. '
    t += 'A focused evolution and third-mesh/larger-domain decision follows those results.\n'
    t += '\n## Study register\n\n' + study_table(p, studies)
    t += '\n## Claims and deferred work\n\nNo accepted general isolated motion, full stability, emergent electric charge, quantum spin or electron model. '
    t += 'Retain Q17/Q19 motion after low-Q control, Q18 fresh fine starts/conditioning and further Q values including optional Q20/Q24. '
    t += 'Q18\'s repeatable linked outcome and unsuccessful hyperbolic reproduction stay recorded. '
    t += 'The wider literature review remains incomplete and its level-4 work deferred.\n'
    t += '\nUse ' + link(p, '06-development-plan.md' if False else 'docs/06-development-plan.md', 'the current roadmap') + ' for ordering and '
    t += link(p, 'reports/README.md', 'stage report indexes') + ' for evidence. '
    t += 'Scientific specifications, hypotheses and acceptance thresholds are not changed by this administration update.\n'
    add(p, t)
    p = 'reports/README.md'
    t = '# Research reports\n\n' + stamp(data)
    t += '\nBrowse by stage below. Dates identify runs within a study, not new top-level project stages. '
    t += 'A catalog entry links to the original report; it does not recalculate or reaccept it.\n'
    t += '\n| Stage | Report index |\n|---|---|\n'
    for st in stages:
        t += f'| {st["id"].upper()} | {link(p,"reports/"+st["id"]+"/INDEX.md",st["title"])} |\n'
    t += '\n## Existing published locations\n\nThe irregular pre-policy folders are frozen compatibility locations. '
    t += 'They remain at their exact paths so hashes, replay scripts, old links and local handoffs keep working. '
    t += 'Use ' + link(p, 'docs/project/legacy-locations.md', 'the complete location-to-study map') + ' to find their canonical stage. '
    t += 'Do not add a new campaign beneath a legacy root. New records use `reports/<stage>/<nnn>-<study>/runs/<utc>-<token>/`.\n'
    t += '\n## Current assessment\n\n' + link(p, by_id['s5-b-004']['records'][-1]['path'], 'Completed motion diagnostic assessment')
    t += ' — reproducible endpoint records; initialization and domain effects remain unresolved.\n'
    add(p, t)
    p = 'docs/plans/README.md'
    t = '# Study plans\n\n' + stamp(data) + '\n'
    t += 'Each study has a stable stage/number and one current plan below. Earlier flat plan files remain source specifications at their published paths; their historical next-step wording is superseded by the register.\n\n'
    t += study_table(p, studies)
    add(p, t)
    p = 'docs/project/legacy-locations.md'
    t = '# Preserved report locations\n\n' + stamp(data)
    t += '\nEvery existing report root is assigned a stage and study. Original bytes, basenames and paths remain unchanged. New records must use the canonical layout.\n\n'
    t += '| Preserved root | Owning study | Canonical stage |\n|---|---|---|\n'
    for item in data['legacy_locations']:
        t += f'| {link(p,item["path"]+"/README.md" if (root/item["path"]/"README.md").exists() else item["path"],item["path"])} | {item["study"]} | {item["stage"]} |\n'
    t += '\n## Studies sharing a preserved root\n\n'
    for item in data.get('legacy_substudies',[]):
        t += '- ' + link(p,item['path']+'/ASSESSMENT.md',item['path']) + ' belongs to '+item['study']+'.\n'
    add(p, t)
    for st in stages:
        p = f'reports/{st["id"]}/INDEX.md'
        group = [s for s in studies if s['stage'] == st['id']]
        t = f'# {st["id"].upper()}: {st["title"]}\n\n' + stamp(data)
        t += '\n' + st['scope'] + '\n\n' + study_table(p, group)
        t += '\nStudy indexes distinguish preparation, measurements and assessment. A planned record has no measured results.\n'
        for s in group:
            t += '\n- ' + link(p, reportpath(s), s['id'] + ' evidence index')
        add(p, t)
    for s in studies:
        p = planpath(s)
        t = f'# {s["id"]}: {s["title"]}\n\n' + stamp(data)
        t += f'\nState: **{s["state"]}**. Scientific gate: **{s["gate"]}**. '
        t += 'State records workflow progress, not a physical claim.\n'
        t += '\n## Question and scope\n\n' + s['question'] + '\n'
        t += '\n## Evidence and present finding\n\n' + s['finding'] + '\n'
        t += '\n## Next action and exit evidence\n\n' + s['next_action'] + '\n\n' + s['exit_evidence'] + '\n'
        t += '\n## Traceability\n\nRequirements: ' + ', '.join(s['requirements']) + '.\n\n'
        t += 'Dependencies: ' + (', '.join(link(p, planpath(by_id[d]), d) for d in s['depends_on']) or 'none in this register') + '.\n\n'
        t += link(p, reportpath(s), 'Evidence index') + '.\n'
        for spec in s['specifications']:
            t += '\n- ' + link(p, spec, spec)
        add(p, t)
        p = reportpath(s)
        t = f'# {s["id"]}: {s["title"]} — evidence index\n\n' + stamp(data)
        t += '\n' + link(p, planpath(s), 'Current study plan') + f'. State: {s["state"]}; scientific gate: {s["gate"]}.\n'
        t += '\n' + s['finding'] + '\n'
        if s['records']:
            t += '\n| Record role | Retained record |\n|---|---|\n'
            for r in s['records']:
                t += f'| {r["role"]} | {link(p,r["path"],r["label"])} |\n'
        else:
            t += '\nNo measured result is registered for this study. This index reserves its identity; it is not evidence of execution.\n'
        t += '\nPublished records are append-only. Corrections require a dated superseding assessment and reason; keep earlier files and original hashes.\n'
        add(p, t)
    return result


def validate(data, root=ROOT):
    assert data['schema_version'] == 1
    utc = datetime.fromisoformat(data['updated_at']['utc'])
    mel = datetime.fromisoformat(data['updated_at']['melbourne'])
    assert utc.utcoffset().total_seconds() == 0 and utc == mel
    assert utc.astimezone(ZoneInfo('Australia/Melbourne')).isoformat() == mel.isoformat()
    stage_ids = {s['id'] for s in data['stages']}
    ids = [s['id'] for s in data['studies']]
    assert len(ids) == len(set(ids)), 'Duplicate study ID'
    assert len(stage_ids) == len(data['stages']), 'Duplicate stage'
    by_id = {s['id']: s for s in data['studies']}
    requirements = (root/'docs/03-requirements.md').read_text()
    def safe(name):
        p = Path(name)
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in name, name
        assert (root/p).resolve().is_relative_to(root.resolve()), name
        return p
    for s in data['studies']:
        assert s['stage'] in stage_ids and re.fullmatch(r's[0-7](?:-[a-z])?', s['stage'])
        assert s['id'] == f'{s["stage"]}-{s["number"]:03d}' and 1 <= s['number'] <= 999
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', s['slug']), s['slug']
        assert s['state'] in STATES and s['gate'] in GATES
        assert all(d in by_id and d != s['id'] for d in s['depends_on'])
        assert s['question'] and s['finding'] and s['next_action'] and s['exit_evidence']
        for req in s['requirements']:
            assert req in requirements, req
        for spec in s['specifications']:
            assert (root/safe(spec)).is_file(), spec
        for r in s['records']:
            assert r['role'] in {'preparation','measurement','assessment','verification','decision','historical'}
            assert (root/safe(r['path'])).is_file(), r['path']
        if s['state'] in {'recorded','assessed'}:
            assert s['records'], s['id'] + ' has no evidence'
    def walk(sid, visiting, done):
        assert sid not in visiting, 'Dependency cycle: '+sid
        if sid in done:return
        for dep in by_id[sid]['depends_on']:walk(dep,visiting|{sid},done)
        done.add(sid)
    done=set()
    for sid in ids:walk(sid,set(),done)
    assert all(s in by_id for s in data['priority'])
    roots = [i['path'] for i in data['legacy_locations']]
    assert len(roots)==len(set(roots))
    for item in data['legacy_locations']+data.get('legacy_substudies',[]):
        assert item['study'] in by_id and item['stage']==by_id[item['study']]['stage']
        assert (root/safe(item['path'])).is_dir()
    generated = documents(data, root)
    for path in generated:safe(path)
    return generated


def check(root=ROOT, migration=False):
    data=json.loads((root/REGISTRY).read_text())
    generated=validate(data,root)
    for path, expected in generated.items():
        assert (root/path).read_text()==expected, 'Generated navigation drift: '+path
    baseline=json.loads((root/BASELINE).read_text())
    archive=json.loads((root/'docs/history/layout-20261104/manifest.json').read_text())
    assert archive['baseline_commit']==baseline['source_commit']==data['baseline_commit']
    for item in archive['files']:
        assert item['sha256']==baseline['files'][item['original_path']]['sha256']
        assert digest(root/item['archive_path'])==item['sha256'], 'Changed navigation archive: '+item['original_path']
    protected=0
    for name, info in baseline['files'].items():
        if migration and name not in baseline['administrative_edits'] or name.startswith('reports/') and name!='reports/README.md':
            path=root/name
            assert path.is_file() and not path.is_symlink(), 'Missing/replaced baseline file: '+name
            assert digest(path)==info['sha256'], 'Changed protected bytes: '+name
            if info['mode']=='100755':assert path.stat().st_mode & 0o111, 'Lost executable mode: '+name
            else:assert not path.stat().st_mode & 0o111, 'Changed executable mode: '+name
            protected+=1
    # Every pre-policy report root has an owner; no historical folder is orphaned.
    known={i['path'] for i in data['legacy_locations']}
    expected={str(Path(n).parts[0]+'/'+Path(n).parts[1]) for n in baseline['files'] if n.startswith('reports/') and len(Path(n).parts)>2}
    assert known==expected, 'Legacy root coverage differs'
    # New report files obey the canonical stage/study/run hierarchy.
    checked_records=set()
    for p in (root/'reports').rglob('*'):
        assert not p.is_symlink(), 'Report symlinks are not canonical evidence: '+str(p)
        if not p.is_file():continue
        name=p.relative_to(root).as_posix()
        if name in baseline['files'] or name in generated:continue
        parts=Path(name).parts
        assert len(parts)>=6 and re.fullmatch(r's[0-7](?:-[a-z])?',parts[1]), 'Noncanonical new report: '+name
        assert re.fullmatch(r'[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*',parts[2]), name
        sid=parts[1]+'-'+parts[2][:3]
        study=next((s for s in data['studies'] if s['id']==sid),None)
        assert study and parts[2]==f'{study["number"]:03d}-{study["slug"]}', 'Unknown study folder: '+name
        assert parts[3] in {'runs','preparation','assessments'}, name
        assert re.fullmatch(r'[0-9]{8}t[0-9]{6}z-[0-9a-f]{8}',parts[4]), 'Invalid run ID: '+name
        # A registered top-level run record makes unpublished loose files visible to review.
        record=root/Path(*parts[:5])/'record.json'
        assert record.is_file(), 'Missing run record: '+name
        r=json.loads(record.read_text())
        assert r['study_id']==sid and r['record_id']==parts[4]
        assert r['role']=={'runs':'measurement','preparation':'preparation','assessments':'assessment'}[parts[3]]
        assert re.fullmatch(r'[0-9a-f]{40}',r['source_commit']) and r['outcome']
        ru=datetime.fromisoformat(r['recorded_at']['utc']);rm=datetime.fromisoformat(r['recorded_at']['melbourne'])
        assert ru.utcoffset().total_seconds()==0 and ru==rm
        assert ru.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()==rm.isoformat()
        assert (root/Path(*parts[:5])/'README.md').is_file()
        assert (root/Path(*parts[:5])/'SHA256SUMS').is_file()
        assert any(x['path'].startswith('/'.join(parts[:5])+'/') for x in study['records']), 'Unregistered run: '+name
        record_root=root/Path(*parts[:5])
        if record_root not in checked_records:
            checked_records.add(record_root)
            covered=set()
            for line in (record_root/'SHA256SUMS').read_text().splitlines():
                expected,relative=line.split('  ',1)
                q=Path(relative)
                assert re.fullmatch(r'[0-9a-f]{64}',expected) and relative not in covered
                assert not q.is_absolute() and '..' not in q.parts and '\\' not in relative
                payload=record_root/q
                assert not payload.is_symlink() and payload.resolve().is_relative_to(record_root.resolve())
                assert payload.is_file() and digest(payload)==expected, 'Run payload hash mismatch: '+str(payload)
                covered.add(relative)
            actual={q.relative_to(record_root).as_posix() for q in record_root.rglob('*') if q.is_file() and q!=record_root/'SHA256SUMS'}
            assert covered==actual, 'Run checksum coverage differs: '+str(record_root)
            for q in record_root.rglob('*.csv'):
                assert b'\r' not in q.read_bytes(), 'CSV must use LF: '+str(q)
    return {'studies':len(data['studies']),'stages':len(data['stages']),'protected_files':protected,'migration':migration}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['render','check'])
    p.add_argument('--migration',action='store_true',help='Also verify every non-administrative baseline file byte-for-byte')
    p.add_argument('--compare-ref',help='Reject rewriting canonical records already present at this full commit')
    p.add_argument('--ci',action='store_true',help='Use the GitHub event base when available to enforce append-only records')
    a=p.parse_args()
    try:
        if a.command=='render':
            data=json.loads((ROOT/REGISTRY).read_text())
            for name,text in validate(data).items():
                path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
            print('Rendered administrative navigation from '+REGISTRY)
        else:
            ref=a.compare_ref
            if a.ci:
                event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
                ref=event.get('pull_request',{}).get('base',{}).get('sha') or event.get('before')
                if ref and set(ref)=={'0'}:ref=None  # First branch push; the PR comparison checks the target base.
            if ref:immutable_changes(ROOT,ref)
            print(json.dumps(check(migration=a.migration),sort_keys=True))
    except (AssertionError,ValueError,KeyError,OSError) as error:
        p.exit(1,'Project record validation failed: '+str(error)+'\n')


if __name__=='__main__':main()
