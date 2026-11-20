"""Actual pinned CPU kernels, no-step controls, collection and local Git tests."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib
import numpy as np
from common import ROOT, load, save, sha
import diagnostics
import handover
import integrity
import publication
import reconcile
import worker

class DiagnosisTests(unittest.TestCase):
    def test_frozen_completed_evidence_and_scope(self):
        objects, hashes, original = integrity.baseline()
        self.assertEqual(len(hashes), 140)
        self.assertEqual(objects['record.json']['additional_attempts'], 225)
        self.assertEqual(len(objects['field-manifest.json']['fields']), 36)
        plan = load(ROOT / 'PLAN.json')
        self.assertEqual(len(plan['fields']), 5)
        self.assertEqual(plan['fields'][0]['id'], 'q2-control')
        self.assertEqual(plan['fields'][0]['kind'], 'control')
        self.assertEqual(plan['optimizer_steps'], 0)
        self.assertEqual(plan['physical_time_steps'], 0)
        self.assertEqual(plan['registered_gates'], objects['record.json']['plan'])
        self.assertEqual(load(ROOT / 'SOURCES.json'), original['identity.json'])

    def test_historical_q2_positive_is_preserved_by_exact_gates(self):
        gates = load(ROOT / 'PLAN.json')['registered_gates']
        q2 = load(ROOT / 'PRIOR-CONTEXT.json')['q2']['metrics']
        self.assertEqual(diagnostics.admission(q2, 2, gates), (True, True))
        objects = integrity.baseline()[0]
        for case in objects['record.json']['branches']:
            self.assertEqual(diagnostics.admission(case['metrics'], case['q'], gates), (False, False))

    @staticmethod
    def specimen():
        from electron_field_topology.sf_time import Grid
        from electron_field_topology.skyrme import rational_field
        from electron_field_topology.sf_readmission import stationarity
        grid = Grid((33,) * 3, (12.,) * 3, 'fixed')
        n = rational_field(grid.points(), alpha=1, beta=1, scale=1.4, cutoff=4.5)
        n[grid.fixed_mask()] = [0., 0., 1.]
        metrics = stationarity(n, grid)
        spec = {'id': 'small-cpu-fixture', 'kind': 'endpoint', 'q': 1, 'nodes': 33, 'length': 12., 'key': 'field', 'sha256': 'fixture', 'expected': metrics}
        return n, grid, spec

    def test_actual_static_diagnostics_preserve_field_and_partition_every_node(self):
        from electron_field_topology import sf_time, sf_readmission
        n, grid, spec = self.specimen()
        initial = n.copy()
        n.setflags(write=False)
        with tempfile.TemporaryDirectory() as td, patch.object(sf_time, 'step', side_effect=AssertionError('Physical step forbidden')), patch.object(sf_readmission, 'relax', side_effect=AssertionError('Relaxation forbidden')):
            result = diagnostics.analyse(n, grid, spec, load(ROOT / 'PLAN.json')['registered_gates'], Path(td))
            self.assertTrue(np.array_equal(n, initial))
            self.assertEqual(result['field_array_sha256_before'], result['field_array_sha256_after'])
            self.assertEqual(result['optimizer_steps'], result['physical_time_steps'])
            self.assertEqual(result['optimizer_steps'], 0)
            self.assertAlmostEqual(result['force_decomposition']['registered_ratio_reconstructed'], spec['expected']['relative_force_l2'], places=12)
            for filename in ['shell-profiles.json', 'radial-profiles.json']:
                rows = load(Path(td) / filename)
                self.assertEqual(sum(row['nodes'] for row in rows), n.shape[0] ** 3)
                self.assertAlmostEqual(sum(row['force_squared_fraction'] for row in rows), 1., places=12)
                self.assertAlmostEqual(sum(row['registered_energy_fraction'] for row in rows), 1., places=12)
            self.assertTrue((Path(td) / 'central-slices.svg').read_text().startswith('<svg'))
            e = result['energy_definition_check']
            self.assertAlmostEqual(e['d4_static_action'], e['d4_hamiltonian_energy'], places=12)
            self.assertFalse(e['gate_definition_changed'])
            from electron_field_topology.sf_time import densities
            energy = densities(n, np.zeros_like(n), grid)['energy_density']
            for key, width in [('tail_fraction', 2.), ('guard_fraction', 3.)]:
                old_mask = np.any(np.abs(grid.points()) >= np.asarray(grid.lengths) / 2 - width, axis=-1)
                self.assertAlmostEqual(result['reference_metrics'][key], float(np.sum(energy[old_mask]) / np.sum(energy)), places=13)
            d = result['force_decomposition']
            self.assertAlmostEqual(d['registered_sigma_denominator_l2']**2, d['free_node_sigma_denominator_l2_diagnostic']**2 + d['held_node_sigma_denominator_l2_diagnostic']**2, delta=d['registered_sigma_denominator_l2']**2 * 1e-12)

    def test_same_field_metric_mismatch_blocks_instead_of_explaining_away(self):
        n, grid, spec = self.specimen()
        spec['expected']['energy'] *= 1.1
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, 'metric replay differs'):
                diagnostics.analyse(n, grid, spec, load(ROOT / 'PLAN.json')['registered_gates'], Path(td))

    def test_nonstationary_control_blocks(self):
        n, grid, spec = self.specimen()
        spec['kind'] = 'control'
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, 'Q2 positive control fails'):
                diagnostics.analyse(n, grid, spec, load(ROOT / 'PLAN.json')['registered_gates'], Path(td))

    def test_cached_static_case_is_verified_and_corruption_is_rejected(self):
        n, grid, spec = self.specimen()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / 'source.npz'
            np.savez_compressed(path, field=n, expected_q=1)
            spec['sha256'] = sha(path)
            before = sha(path)
            with patch.object(worker, 'field_path', return_value=path), patch.object(worker, 'host', return_value={'available_gib': 10}):
                first = worker.run_case(root, root / 'out', spec, load(ROOT / 'PLAN.json')['registered_gates'])
                with patch.object(diagnostics, 'analyse', side_effect=AssertionError('Repeated case')):
                    second = worker.run_case(root, root / 'out', spec, load(ROOT / 'PLAN.json')['registered_gates'])
                self.assertEqual(first, second)
                self.assertEqual(sha(path), before)
                folder = root / 'out/cases/small-cpu-fixture'
                (folder / 'shell-profiles.csv').write_text('corrupt\n')
                with self.assertRaisesRegex(RuntimeError, 'Cached diagnostic output differs'):
                    worker.run_case(root, root / 'out', spec, load(ROOT / 'PLAN.json')['registered_gates'])

    def test_png_pixels_are_losslessly_encoded_with_valid_crcs(self):
        pixels = np.arange(36, dtype=np.uint8).reshape(3, 4, 3)
        png = diagnostics.png_rgb(pixels)
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        position, chunks = 8, {}
        while position < len(png):
            length = struct.unpack('!I', png[position:position+4])[0]
            name = png[position+4:position+8]
            data = png[position+8:position+8+length]
            crc = struct.unpack('!I', png[position+8+length:position+12+length])[0]
            self.assertEqual(crc, zlib.crc32(name+data) & 0xffffffff)
            chunks[name] = data
            position += 12 + length
        self.assertEqual(struct.unpack('!II', chunks[b'IHDR'][:8]), (4, 3))
        raw = zlib.decompress(chunks[b'IDAT'])
        self.assertEqual(raw, b''.join(b'\0' + row.tobytes() for row in pixels))

    def test_reconciliation_leaves_unknown_claims_open_and_distinguishes_operators(self):
        record = reconcile.reconcile({})
        self.assertEqual(record['claims'][0]['status'], 'control_replay_pending_or_failed')
        self.assertEqual(record['claims'][1]['status'], 'different_operator_and_metric_verified_by_prior_same_field_record')
        self.assertNotEqual(record['claims'][2]['historical_field_sha256'], record['claims'][2]['current_field_sha256'])
        self.assertIn('unassessed', record['unresolved'])
        cases = {'q2-control': {'metric_replay_passed': True, 'strict_stationary': True, 'boundary_admitted': True}}
        self.assertEqual(reconcile.reconcile(cases)['claims'][0]['status'], 'positive_control_reproduced')

    def test_resource_policy_does_not_pause_on_psi_alone(self):
        sample = {'host': {'available_gib': 9}, 'pressure': {'full': {'avg10': 80}}}
        self.assertEqual(handover.pressure_stop(sample, 40, None), (False, None))
        sample['host']['available_gib'] = 3
        self.assertTrue(handover.pressure_stop(sample, 41, 10)[0])
        args = handover.launch_argv(Path('/fixture/repo'), Path('/fixture/output'))
        self.assertIn('--property=MemoryHigh=' + str(7 * 1024**3), args)
        self.assertIn('--property=MemoryMax=' + str(8 * 1024**3), args)
        self.assertIn('--property=SendSIGKILL=no', args)

    def test_no_new_step_or_relax_calls_in_diagnostic_code(self):
        for name in ['diagnostics.py', 'worker.py', 'reconcile.py']:
            tree = ast.parse((ROOT / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, ['step', 'relax', 'batch'])

    @staticmethod
    def mock_completed(repo):
        source = integrity.completed(repo)
        source.mkdir(parents=True)
        archive = ROOT / 'assessment/data/completed-evidence.zip'
        with zipfile.ZipFile(archive) as z:
            integrity.checked_zip(z)
            z.extractall(source)
        shutil.copy2(archive, source / 'evidence.zip')
        (source / '.worker.lock').write_text('')
        (source / 'runner.log').write_text('Full retained runner log fixture  \n\n')
        (source / 'telemetry.jsonl').write_text('{"fixture": true}\n')
        for row in integrity.baseline()[0]['field-manifest.json']['fields']:
            path = source / row['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'local retained field fixture; collector does not authenticate fields')
        return source

    def test_complete_collection_keeps_logs_and_manifest_without_copying_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.mock_completed(root / 'repo')
            first = integrity.collect_completed(root / 'repo', root / 'collected')
            again = integrity.collect_completed(root / 'repo', root / 'collected')
            self.assertEqual(first['copied_nonfield_files'], again['copied_nonfield_files'])
            self.assertEqual(len(first['retained_full_fields']), 36)
            self.assertEqual((root / 'collected/runner.log').read_bytes(), (source / 'runner.log').read_bytes())
            self.assertTrue((root / 'collected/telemetry.jsonl').exists())
            self.assertFalse(list((root / 'collected').rglob('*.npz')))
            self.assertFalse(first['full_field_contents_verified_by_collection'])

    def test_optimizer_history_is_descriptive_and_preserves_real_decisions(self):
        rows = reconcile.history_analysis()
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual([x['plateau_count'] for x in row['last_three_policy_decisions']], [1, 2, 3])
            self.assertIn('not causal', row['scope'])
            self.assertEqual(row['last_three_policy_decisions'][-1]['action'], 'stop')

    def test_prior_markdown_is_preserved_as_raw_text_with_pinned_provenance(self):
        def git(folder, *args):
            return subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args], cwd=folder, text=True, capture_output=True, check=True).stdout.strip()
        with tempfile.TemporaryDirectory() as td:
            repo, out = Path(td) / 'repo', Path(td) / 'out'
            repo.mkdir()
            git(repo, 'init', '-b', 'main')
            path = repo / 'reports/s5-b/015-fixture/ASSESSMENT.md'
            path.parent.mkdir(parents=True)
            data = b'# Pinned earlier assertion\n\n[Original tree link](not-collected.md)  \n'
            path.write_bytes(data)
            git(repo, 'add', 'reports')
            git(repo, 'commit', '-m', 'Prior claim fixture')
            commit = git(repo, 'rev-parse', 'HEAD')
            with patch.object(reconcile, 'load', return_value={'checkout_commit': commit}):
                receipt = reconcile.collect_prior_records(repo, out)
            doc = receipt['documents'][0]
            self.assertTrue(doc['collected_path'].endswith('.md.txt'))
            self.assertEqual((out / doc['collected_path']).read_bytes(), data)
            self.assertEqual(doc['source_commit'], commit)
            self.assertIn('reports/s5-b/016-', receipt['missing_study_prefixes'])

    def test_real_local_git_staging_is_additive_and_repeatable(self):
        def git(folder, *args):
            return subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args], cwd=folder, text=True, capture_output=True, check=True).stdout.strip()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, pub, remote = root / 'repo', root / 'publication', root / 'origin.git'
            repo.mkdir()
            git(repo, 'init', '-b', 'main')
            (repo / 'README.md').write_text('# Prior research\n\nRetain existing graphics and findings.\n')
            (repo / '.gitignore').write_text('/artifacts/\n')
            git(repo, 'add', 'README.md', '.gitignore')
            git(repo, 'commit', '-m', 'Pinned local fixture')
            git(root, 'clone', '--bare', str(repo), str(remote))
            self.mock_completed(repo)
            with patch.object(publication, 'REMOTE', str(remote)):
                first = publication.prepare(repo, pub)
                second = publication.prepare(repo, pub)
            self.assertEqual(first, second)
            self.assertEqual(first['phase'], 'applied')
            self.assertTrue((pub / publication.DOC / 'completed/20261120t003653z-a200a9db/runner.log').exists())
            self.assertIn('Retain existing graphics', (pub / 'README.md').read_text())
            self.assertEqual(git(repo, 'status', '--porcelain'), '')
            git(pub, 'diff', '--cached', '--check')

    def test_sealed_diagnostic_zip_has_complete_hash_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / 'handover').mkdir()
            save(out / 'record.json', {'optimizer_steps': 0, 'physical_time_steps': 0})
            (out / 'handover/validation.txt').write_text('Preserved validation log\n')
            worker.seal(out)
            with zipfile.ZipFile(out / 'evidence.zip') as z:
                hashes = integrity.checked_zip(z)
                self.assertIn('handover/validation.txt', hashes)
                self.assertFalse(any(x.endswith('.npz') for x in hashes))

    def test_partial_and_later_failed_snapshots_are_separate_immutable_records(self):
        def git(folder, *args):
            return subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args], cwd=folder, text=True, capture_output=True, check=True).stdout.strip()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, pub, remote = root / 'repo', root / 'publication', root / 'origin.git'
            repo.mkdir()
            git(repo, 'init', '-b', 'main')
            (repo / 'README.md').write_text('# Prior research\n')
            (repo / '.gitignore').write_text('/artifacts/\n')
            git(repo, 'add', 'README.md', '.gitignore')
            git(repo, 'commit', '-m', 'Fixture baseline')
            git(root, 'clone', '--bare', str(repo), str(remote))
            self.mock_completed(repo)
            with patch.object(publication, 'REMOTE', str(remote)):
                initial = publication.prepare(repo, pub)
            git(pub, 'commit', '-m', 'Record source fixture')
            git(pub, 'push', 'origin', 'HEAD:main')
            initial['phase'] = 'merged'
            save(publication.marker(pub), initial)
            out = repo / 'artifacts/diagnosis-fixture'
            out.mkdir(parents=True)
            save(repo / '.git/field-diagnosis-last.json', {'output': str(out)})
            snapshots = []
            for status in ['interrupted', 'failed']:
                record = {'identity': {'run_id': 'fixture-run', 'package_sha256': sha(ROOT / 'SHA256SUMS')}, 'status': status,
                          'optimizer_steps': 0, 'physical_time_steps': 0, 'cases': {}}
                save(out / 'record.json', record)
                save(out / 'status.json', {'status': status})
                save(out / 'RECONCILIATION.json', {'status': status})
                (out / 'REPORT.html').write_text('<html>' + status + '</html>\n')
                worker.seal(out)
                with patch.object(publication, 'REMOTE', str(remote)), patch.object(handover, 'live', return_value=False), patch.object(handover, 'service_active', return_value=False):
                    staged = publication.prepare(repo, pub, True)
                snapshots.append(staged['source_snapshot_sha256'])
                git(pub, 'commit', '-m', 'Record ' + status + ' fixture')
                git(pub, 'push', 'origin', 'HEAD:main')
                staged['phase'] = 'merged'
                save(publication.marker(pub), staged)
            self.assertNotEqual(*snapshots)
            target = pub / publication.DOC / 'diagnosis/fixture-run'
            self.assertEqual(len(list(target.iterdir())), 2)
            self.assertIn('interrupted', (pub / publication.DOC / 'README.md').read_text())
            self.assertIn('failed', (pub / publication.DOC / 'README.md').read_text())
            current_index = (pub / publication.DOC / 'README.md').read_bytes()
            publication.prepare(repo, pub, False)
            self.assertEqual((pub / publication.DOC / 'README.md').read_bytes(), current_index)

if __name__ == '__main__':
    unittest.main()
