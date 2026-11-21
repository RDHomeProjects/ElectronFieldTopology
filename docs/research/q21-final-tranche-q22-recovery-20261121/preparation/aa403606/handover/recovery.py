"""Read-only source inventory; restore only one authenticated native Q22 NPZ."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import zipfile
from common import ROOT, canonical, load, log, need, save, sha, stamp
from integrity import check_file

class SearchLimit(RuntimeError):
    pass

def archive_kind(name):
    name = str(name).lower()
    if name.endswith('.zip'):
        return 'zip'
    if name.endswith(('.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tar.xz')):
        return 'tar'
    return None

def safe_member(name):
    p = PurePosixPath(name)
    return not p.is_absolute() and '..' not in p.parts

def default_roots(home=None):
    home = Path.home() if home is None else Path(home)
    plan = load(ROOT / 'PLAN.json')['recovery']
    return sorted(path for path in home.iterdir() if path.is_dir() and not path.is_symlink() and any(path.name.startswith(p) for p in plan['project_directory_prefixes']))

class Search:
    def __init__(self, out, settings, expected, stop=None, phase=None):
        self.out, self.settings, self.expected = Path(out), settings, expected
        self.folder = self.out / 'recovery'
        self.folder.mkdir(parents=True, exist_ok=True)
        self.stop = stop or (lambda: False)
        self.phase = phase if phase is not None else {}
        state_path = self.folder / 'BUDGET.json'
        identity_path = self.folder / 'SEARCH-IDENTITY.json'
        identity = {'expected_sha256': expected, 'settings_sha256': canonical(settings)}
        if identity_path.exists():
            need(load(identity_path) == identity and state_path.exists(), 'Recovery identity or budget ledger lost/changed; refusing automatic budget refund')
        self.budget = load(state_path) if state_path.exists() else {'recorded_at': stamp(), 'stream_bytes_charged': 0, 'filesystem_entries': 0, 'archive_members': 0, 'attempted_candidates': 0, 'archive_streams': 0}
        if not identity_path.exists():
            save(state_path, self.budget)
            save(identity_path, identity)
        self.seen_archives, self.seen_files = set(), set()
        self.gaps, self.gap_count, self.found = [], 0, None

    def persist(self):
        self.budget['recorded_at'] = stamp()
        save(self.folder / 'BUDGET.json', self.budget)

    def check_stop(self):
        if self.stop() or (self.out / 'STOP.json').exists():
            raise KeyboardInterrupt('Q22 inventory paused; completed receipts and charged stream budget retained')

    def gap(self, locator, reason):
        self.gap_count += 1
        if len(self.gaps) < 1000:
            self.gaps.append({'locator': str(locator), 'reason': str(reason)})

    def charge(self, size, locator):
        self.check_stop()
        if size < 0 or self.budget['stream_bytes_charged'] + size > self.settings['maximum_candidate_and_nested_stream_bytes']:
            raise SearchLimit('Candidate/nested/archive-hash stream budget reached before: ' + str(locator))
        self.budget['stream_bytes_charged'] += size
        self.persist()  # Charged before reading; interruption never refunds work.

    def file_event(self):
        self.check_stop()
        if self.budget['filesystem_entries'] >= self.settings['maximum_filesystem_entries']:
            raise SearchLimit('Declared filesystem entry limit reached')
        self.budget['filesystem_entries'] += 1
        if self.budget['filesystem_entries'] % 1000 == 0:
            self.persist()

    def member_event(self):
        self.check_stop()
        if self.budget['archive_members'] >= self.settings['maximum_archive_members']:
            raise SearchLimit('Declared archive member limit reached')
        self.budget['archive_members'] += 1

    def stream_digest(self, opener, size, locator, destination=None):
        if destination is not None:
            need(shutil.disk_usage(self.folder).free >= size + 40*1024**3, 'Disk reserve reached before recovery spool/restore: ' + str(locator))
        self.charge(size, locator)
        digest, count = hashlib.sha256(), 0
        with opener() as stream:
            while True:
                self.check_stop()
                block = stream.read(1024**2)
                if not block:
                    break
                count += len(block)
                need(count <= size, 'Source stream exceeds declared member size: ' + str(locator))
                digest.update(block)
                if destination is not None:
                    destination.write(block)
        need(count == size, 'Source stream size differs: ' + str(locator))
        return digest.hexdigest()

    def receipt(self, value):
        with (self.folder / 'candidates.jsonl').open('a') as stream:
            stream.write(json.dumps({'recorded_at': stamp(), **value}) + '\n')
            stream.flush(); os.fsync(stream.fileno())

    def candidate(self, opener, size, locator):
        self.check_stop()
        self.phase.update(name='q22-local-inventory', candidate=str(locator))
        self.budget['attempted_candidates'] += 1
        value = self.stream_digest(opener, size, locator)
        matched = value == self.expected
        self.receipt({'locator': str(locator), 'bytes': size, 'sha256': value, 'matched': matched})
        if not matched:
            return
        target = self.out / 'recovered/q22-native.npz'
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            check_file(target, self.expected)
        else:
            temporary = target.with_suffix('.partial')
            with temporary.open('wb') as output:
                copied = self.stream_digest(opener, size, str(locator)+' [authenticated restore]', output)
                output.flush(); os.fsync(output.fileno())
            need(copied == self.expected, 'Historical source changed between matching and restore')
            check_file(temporary, self.expected)
            temporary.replace(target)
        self.found = {'recorded_at': stamp(), 'status': 'authenticated_recovered', 'path': str(target), 'sha256': self.expected,
                      'source_locator': str(locator), 'bytes': size, 'source_modified': False, 'normalized': False, 'resampled': False}
        save(self.folder / 'FOUND.json', self.found)
        log('Exact historical Q22 checkpoint recovered', source=str(locator), restored=str(target), sha256=self.expected)

    def nested(self, opener, size, locator, depth, kind):
        if depth > self.settings['maximum_nested_depth']:
            self.gap(locator, 'nested archive depth limit')
            return
        if size > self.settings['maximum_nested_archive_bytes']:
            self.gap(locator, 'nested archive exceeds declared spool limit')
            return
        with tempfile.TemporaryFile(dir=self.folder) as temporary:
            digest = self.stream_digest(opener, size, locator, temporary)
            if digest in self.seen_archives:
                return
            self.seen_archives.add(digest)
            temporary.seek(0)
            self.budget['archive_streams'] += 1
            self.scan_archive(temporary, locator, depth, kind)

    def scan_archive(self, source, locator, depth, kind):
        try:
            if kind == 'zip':
                with zipfile.ZipFile(source) as z:
                    members = z.infolist()
                    if len(members) > self.settings['maximum_archive_members'] - self.budget['archive_members']:
                        raise SearchLimit('Archive member limit would be exceeded: ' + str(locator))
                    # Q22-labelled members first, then other possible copies.
                    members.sort(key=lambda m: ('q22' not in m.filename.lower(), m.filename))
                    for member in members:
                        self.member_event()
                        if self.found:
                            return
                        name = member.filename
                        if member.is_dir():
                            continue
                        if not safe_member(name) or ((member.external_attr >> 16) & 0o170000) == 0o120000:
                            self.gap(str(locator)+'!'+name, 'unsafe path or symlink member skipped')
                            continue
                        location = str(locator)+'!'+name
                        opener = lambda z=z, m=member: z.open(m)
                        try:
                            if name.lower().endswith('.npz'):
                                self.candidate(opener, member.file_size, location)
                            elif archive_kind(name):
                                self.nested(opener, member.file_size, location, depth+1, archive_kind(name))
                        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, EOFError) as error:
                            if isinstance(error, SearchLimit):
                                raise
                            self.gap(location, 'unreadable/corrupt archive member: ' + str(error))
            else:
                with tarfile.open(fileobj=source, mode='r:*') as tar:
                    for member in tar:
                        self.member_event()
                        if self.found:
                            return
                        if not member.isfile():
                            if member.issym() or member.islnk():
                                self.gap(str(locator)+'!'+member.name, 'tar link skipped')
                            continue
                        location = str(locator)+'!'+member.name
                        if not safe_member(member.name):
                            self.gap(location, 'unsafe tar member path skipped')
                            continue
                        opener = lambda tar=tar, m=member: tar.extractfile(m)
                        if member.name.lower().endswith('.npz'):
                            self.candidate(opener, member.size, location)
                        elif archive_kind(member.name):
                            self.nested(opener, member.size, location, depth+1, archive_kind(member.name))
        except (OSError, ValueError, RuntimeError, tarfile.TarError, zipfile.BadZipFile, EOFError) as error:
            if isinstance(error, SearchLimit):
                raise
            self.gap(locator, 'archive could not be completely inspected: ' + str(error))

    def inspect_file(self, path):
        self.check_stop()
        path = Path(path)
        if path.is_symlink():
            self.gap(path, 'source symlink skipped')
            return
        try:
            stat = path.stat()
            identity = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
            if identity in self.seen_files:
                return
            self.seen_files.add(identity)
            if path.suffix.lower() == '.npz':
                self.candidate(lambda: path.open('rb'), stat.st_size, path)
            elif archive_kind(path.name):
                value = self.stream_digest(lambda: path.open('rb'), stat.st_size, str(path)+' [archive identity]')
                if value in self.seen_archives:
                    return
                self.seen_archives.add(value)
                self.budget['archive_streams'] += 1
                with path.open('rb') as stream:
                    self.scan_archive(stream, path, 0, archive_kind(path.name))
        except (OSError, ValueError, RuntimeError) as error:
            if isinstance(error, SearchLimit):
                raise
            self.gap(path, 'file could not be completely inspected: ' + str(error))

    def scan_root(self, root):
        root = Path(root).expanduser()
        if root.resolve() == self.out.resolve() or self.out.resolve() in root.resolve().parents:
            self.gap(root, 'current campaign output excluded from source inventory')
            return
        if not root.exists():
            self.gap(root, 'declared root absent')
            return
        if root.is_file():
            self.file_event(); self.inspect_file(root)
            return
        for directory, dirs, files in os.walk(root, followlinks=False, onerror=lambda error: self.gap(error.filename, str(error))):
            self.file_event()
            here = Path(directory)
            dirs[:] = [name for name in sorted(dirs, key=lambda n: ('q22' not in n.lower(), n)) if name not in self.settings['exclude_directories'] and not (here/name).is_symlink() and (here/name).resolve() != self.out.resolve()]
            for name in sorted(files, key=lambda n: ('q22' not in n.lower(), not n.lower().endswith('.npz'), n)):
                self.file_event()
                if self.found:
                    return
                path = here/name
                if path.suffix.lower() == '.npz' or archive_kind(path.name):
                    self.inspect_file(path)

    def run(self, extra_roots=(), explicit=None, home=None):
        receipt_path = self.folder / 'INVENTORY.json'
        if receipt_path.exists():
            old = load(receipt_path)
            if old['status'] in ['authenticated_recovered', 'deferred_missing_exact_historical_field']:
                if old['status'] == 'authenticated_recovered':
                    check_file(Path(old['path']), self.expected)
                return old
        if (self.folder / 'FOUND.json').exists():
            self.found = load(self.folder / 'FOUND.json')
            check_file(Path(self.found['path']), self.expected)
        home = Path.home() if home is None else Path(home)
        roots = default_roots(home) + [Path(p).expanduser() for p in extra_roots]
        roots = sorted(dict.fromkeys(roots), key=lambda p: ('q22' not in str(p).lower(), str(p)))
        expected_location = home / load(ROOT / 'PLAN.json')['q22']['path']
        status, stop_reason = 'working', None
        try:
            if explicit and not self.found:
                path = Path(explicit).expanduser().resolve()
                check_file(path, self.expected)  # A wrong explicit file is refused.
                self.inspect_file(path)
            if expected_location.is_file() and not self.found:
                self.inspect_file(expected_location)
            downloads = home / 'Downloads'
            if downloads.is_dir() and not self.found:
                for path in sorted(downloads.iterdir()):
                    if 'q22' in path.name.lower() and path.is_file() and (path.suffix.lower() == '.npz' or archive_kind(path.name)):
                        self.file_event()
                        self.inspect_file(path)
                        if self.found:
                            break
            for root in roots:
                if self.found:
                    break
                self.scan_root(root)
            if downloads.is_dir() and not self.found:
                for path in sorted(downloads.iterdir(), key=lambda p: ('q22' not in p.name.lower(), p.name)):
                    self.file_event()
                    if self.found:
                        break
                    if path.is_file() and (path.suffix.lower() == '.npz' or (archive_kind(path.name) and any(token in path.name.lower() for token in self.settings['download_archive_name_tokens']))):
                        self.inspect_file(path)
            status = 'authenticated_recovered' if self.found else 'deferred_missing_exact_historical_field'
        except SearchLimit as error:
            status, stop_reason = 'deferred_missing_exact_historical_field', str(error)
            self.gap('declared inventory', stop_reason)
        except KeyboardInterrupt:
            status, stop_reason = 'interrupted', 'operator/resource pause; replayed search streams remain charged'
            raise
        finally:
            self.persist()
            result = {'recorded_at': stamp(), 'status': status, 'expected_sha256': self.expected, 'roots': [str(r) for r in roots],
                      'expected_location': str(expected_location), 'downloads_archive_filter': self.settings['download_archive_name_tokens'],
                      'limits': self.settings, 'charged_work': self.budget, 'coverage_gaps': self.gaps, 'coverage_gap_count': self.gap_count,
                      'coverage_gap_details_truncated': self.gap_count > len(self.gaps), 'stop_reason': stop_reason,
                      'coverage_complete_for_declared_scan': status != 'interrupted' and not self.gap_count and not self.found,
                      'not_a_global_absence_proof': True, 'source_modified': False,
                      'scope': 'Declared local project roots and matching Download archives/NPZs only. Git object databases, excluded caches, external backups and unsupported archive formats are not claimed searched. Exact SHA determines eligibility; filenames do not.'}
            if self.found:
                result.update(self.found)
                result['search_stopped_after_first_authenticated_match'] = True
            save(receipt_path, result)
        return result
