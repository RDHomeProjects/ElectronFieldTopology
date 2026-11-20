"""Offline publication rehearsal; no GitHub connection or PR is made."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import publication
import worker
from common import load, save, sha, stamp

def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True, stderr=subprocess.STDOUT).strip()

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    repo, remote, pub = base / 'numerical', base / 'remote.git', base / 'publication'
    subprocess.run(['git', 'init', '-q', '--initial-branch=main', str(repo)], check=True)
    git(repo, 'config', 'user.email', 'local-test@example.invalid')
    git(repo, 'config', 'user.name', 'Local publication control')
    (repo / 'README.md').write_text('# Original project\n\nKeep this original introduction.\n')
    (repo / 'reports').mkdir()
    (repo / 'reports/original.csv').write_bytes(b'column,value\r\noriginal,retained\r\n')
    (repo / 'original-graphic.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Original graphic</text></svg>\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'Original local fixture')
    original_csv = (repo / 'reports/original.csv').read_bytes()
    subprocess.run(['git', 'clone', '-q', '--bare', str(repo), str(remote)], check=True)
    with patch.object(publication, 'REMOTE', str(remote)):
        first = publication.prepare(repo, pub)
        assert first['phase'] == 'applied'
        assert publication.prepare(repo, pub)['branch'] == first['branch']
        assert (pub / 'reports/original.csv').read_bytes() == original_csv
        assert (pub / 'original-graphic.svg').read_bytes() == (repo / 'original-graphic.svg').read_bytes()
        assert 'Keep this original introduction.' in (pub / 'README.md').read_text()
        git(pub, 'config', 'user.email', 'local-test@example.invalid')
        git(pub, 'config', 'user.name', 'Local publication control')
        git(pub, 'commit', '-qm', 'Offline assessment publication rehearsal')
        git(pub, 'push', 'origin', 'HEAD:main')
        first['phase'] = 'merged'
        first['pr'] = {'state': 'SYNTHETIC_LOCAL_REHEARSAL_ONLY'}
        save(publication.marker(pub), first)
        out = repo / 'artifacts/synthetic-results'
        out.mkdir(parents=True)
        save(out / 'identity.json', {'run_id': 'synthetic-publication-control', 'package_sha256': sha(ROOT / 'SHA256SUMS')})
        save(out / 'record.json', {'status': 'complete_pending_review', 'synthetic': True, 'q22': {'status': 'deferred_missing_exact_historical_field'}})
        (out / 'REPORT.html').write_text('<!doctype html><title>Synthetic publication control</title>\n')
        worker.seal(out)
        save(out / 'status.json', {'status': 'complete_pending_review'})
        save(repo / '.git/q21-q22-evaluation-last.json', {'output': str(out)})
        with patch('handover.live', return_value=False), patch('supervision.service_active', return_value=False):
            second = publication.prepare(repo, pub, True)
            assert second['kind'] == 'results' and second['phase'] == 'applied'
            assert publication.prepare(repo, pub, True)['branch'] == second['branch']
        assert (pub / 'reports/original.csv').read_bytes() == original_csv
        assert (pub / publication.DOC / 'assessment/ASSESSMENT.html').exists()
        assert (pub / publication.DOC / 'README.md').read_text().count('Completed evaluations:') == 1
        git(pub, 'diff', '--cached', '--check')
        print(json.dumps({'recorded_at': stamp(), 'status': 'pass', 'initial_publication_idempotent': True, 'completed_publication_idempotent': True, 'original_csv_crlf_preserved': True, 'original_graphic_preserved': True, 'staged_whitespace': 'pass', 'github_connections': 0, 'scope': 'Real local Git clone/fetch/staging/checks against a temporary local bare repository. PR creation/merge and live repository administrative checks remain workstation operations.'}))
