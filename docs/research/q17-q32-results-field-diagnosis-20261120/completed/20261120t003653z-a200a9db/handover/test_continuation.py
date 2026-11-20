"""Real checkpoint/resume controls and offline publication/state fixtures."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from common import ROOT, canonical, load, manifest, save, sha
import handover
import integrity
import publication
import worker
from science.engine import Engine, checkpoint, restore
from science.fits import decide
from science.numeric import metrics, representation

class ContinuationTests(unittest.TestCase):
    def setUp(self):
        worker.STOP.clear()

    def tearDown(self):
        worker.STOP.clear()

    def test_real_archive_selection_and_500_budget(self):
        objects, hashes = integrity.baseline()
        self.assertEqual(len(hashes), 775)
        specs = load(ROOT / 'SELECTION.json')['branches']
        self.assertEqual(sum(x['maximum_additional_attempts'] for x in specs), 1738)
        self.assertEqual(sorted(x['maximum_additional_attempts'] for x in specs), [283, 285, 290, 290, 290, 300])
        old, new = objects['handover/PLAN.json'], load(ROOT / 'PLAN.json')
        self.assertEqual({k: v for k, v in old.items() if k != 'branch_attempt_budget'}, {k: v for k, v in new.items() if k != 'branch_attempt_budget'})
        for spec in specs:
            ptr = objects['broad/' + spec['id'] + '/optimizer/latest.json']
            self.assertEqual(ptr['identity'], canonical(integrity.original_identity(spec, objects['identity.json'])))

    def test_numerical_algorithms_and_fit_functions_unchanged(self):
        import zipfile
        with zipfile.ZipFile(ROOT / 'assessment/data/source-evidence.zip') as z:
            for name in ['science/engine.py', 'science/numeric.py']:
                self.assertEqual((ROOT / name).read_bytes(), z.read('handover/' + name))
            old = ast.parse(z.read('handover/science/fits.py').decode())
        new = ast.parse((ROOT / 'science/fits.py').read_text())
        for name in ['fit_model', 'predict', 'models']:
            extract = lambda tree: ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), include_attributes=False)
            self.assertEqual(extract(old), extract(new))

    def test_migration_does_not_double_count_terminal_vote(self):
        objects, _ = integrity.baseline()
        p = load(ROOT / 'PLAN.json')
        for spec in load(ROOT / 'SELECTION.json')['branches']:
            folder = 'broad/' + spec['id'] + '/optimizer/'
            h = objects[folder + 'history.json']
            saved = objects[folder + 'decisions.json'][-1]
            with patch('science.fits.models', side_effect=lambda rows, key, plan: saved['models'][key]):
                choice = decide(h, p, 500 - spec['already_spent_attempts'], spec['prior_plateau_count'], plateau_epoch=spec['prior_plateau_epoch'])
            self.assertEqual(choice['plateau_count'], spec['corrected_initial_count'])
            self.assertEqual(choice['action'], 'continue')
            self.assertLessEqual(choice['steps'], spec['maximum_additional_attempts'])

    def test_epoch_400_requires_new_evidence(self):
        p = load(ROOT / 'PLAN.json')
        h = [{'iteration': i, 'relative_force_l2': .01, 'acceleration_max': .1, 'energy': 10.} for i in range(380, 401, 2)]
        choice = decide(h, p, 100, 2, plateau_epoch=200)
        self.assertEqual(choice['plateau_count'], 0)
        self.assertIsNone(choice['recent_joint_progress'])
        self.assertEqual(choice['action'], 'continue')

    def test_pending_decision_is_reused_after_interruption(self):
        objects, _ = integrity.baseline()
        spec = next(x for x in load(ROOT / 'SELECTION.json')['branches'] if x['id'].startswith('q22-'))
        class Fake:
            history = objects['broad/q22-cable-source-family/optimizer/history.json']
            attempts = 200
            s = {'iteration': 200}
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            save(folder / 'planner.json', {'plateau_count': 2, 'plateau_epoch': 0})
            first = worker.plan_once(Fake(), folder, spec, load(ROOT / 'PLAN.json'))
            save(folder / 'planner.json', first['choice'])
            with patch.object(worker, 'decide', side_effect=AssertionError('Duplicate vote')):
                second = worker.plan_once(Fake(), folder, spec, load(ROOT / 'PLAN.json'))
            self.assertEqual(first, second)

    @staticmethod
    def small_field():
        from electron_field_topology.sf_time import Grid
        from electron_field_topology.skyrme import rational_field
        g = Grid((65,) * 3, (12.,) * 3, 'fixed')
        n = rational_field(g.points(), alpha=1, beta=1, scale=1.4, cutoff=4.5)
        n[g.fixed_mask()] = [0., 0., 1.]
        return g, n

    def test_actual_cuda_origin_host_migration_preserves_all_memory(self):
        g, n = self.small_field()
        engine = Engine('cpu')
        state = engine.state(n)
        for _ in range(3):
            self.assertTrue(engine.step(state, g)[0])
        p = load(ROOT / 'PLAN.json')
        row = {'iteration': 3, **metrics(state['n'], g, p)}
        self.assertTrue(representation(row, 1, p))
        spec = {'id': 'q1-control', 'seed': {'id': 'q1-control', 'q': 1}, 'nodes': 65, 'length': 12., 'backend': 'cuda', 'initial_iteration': 3, 'already_spent_attempts': 3,
                'prior_plateau_count': 0, 'prior_plateau_epoch': 0, 'maximum_additional_attempts': 497}
        original_identity = {'fixture': 'cuda-origin-metadata; CPU-computed small field'}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            parent_path = path / 'original.npz'
            # A host adapter models CUDA checkpoint metadata. This is never
            # described as an actual CUDA execution test.
            checkpoint(parent_path, state, worker.HostCheckpoint(), original_identity)
            np.savez_compressed(path / 'endpoint.npz', field=state['n'])
            parent = {'state': str(parent_path), 'state_sha256': sha(parent_path), 'endpoint': str(path / 'endpoint.npz'), 'original_identity': original_identity,
                      'history': [row], 'receipt': {'selected_backend': 'cuda'}}
            identity = {'test': 'new-policy-identity'}
            before = worker.state_digests(state)
            with patch.object(worker, 'parent_check', return_value=parent), patch.object(worker, 'resources', return_value={}):
                receipt, new_identity = worker.migrate(path, path / 'out', spec, identity, p, g)
            restored = restore(path / 'out/continuation/q1-control/state-0.npz', worker.HostCheckpoint(), new_identity)
            self.assertEqual(worker.state_digests(restored), before)
            self.assertEqual(sha(parent_path), parent['state_sha256'])
            with patch.object(worker, 'parent_check', return_value=parent), patch.object(worker, 'metrics', side_effect=AssertionError('Repeated migration')):
                worker.migrate(path, path / 'out', spec, identity, p, g)

    def test_real_optimizer_pause_resume_across_cg_reset_is_bitwise_equal(self):
        g, n = self.small_field()
        p = load(ROOT / 'PLAN.json')
        seed = {'id': 'small-control', 'q': 1}
        root = {'test': 'actual-optimizer-pause-control'}
        with tempfile.TemporaryDirectory() as td, patch('science.numeric.resources', return_value={}):
            folder = Path(td)
            b = worker.SafeBranch(folder, g, seed, p, {'selected_backend': 'cpu'}, root, initial=n)
            b.s['iteration'] = 198
            b.observe()
            b.persist()
            expected = copy.deepcopy(b.s)
            for _ in range(4):
                self.assertTrue(b.engine.step(expected, g)[0])
            original_step = b.engine.step
            def one_step(state, grid):
                result = original_step(state, grid)
                worker.STOP.set()
                return result
            b.engine.step = one_step
            pending = {'choice': {'observe': 2}, 'target_iteration': 202}
            with patch.object(worker, 'resources', return_value={}):
                with self.assertRaises(KeyboardInterrupt):
                    b.batch_pending(pending)
            worker.STOP.clear()
            del b
            b = worker.SafeBranch(folder, g, seed, p, {'selected_backend': 'cpu'}, root)
            with patch.object(worker, 'resources', return_value={}):
                b.batch_pending(pending)
            self.assertEqual(b.attempts, 4)
            for key in ['n', 'old_g', 'old_z', 'direction']:
                self.assertTrue(np.array_equal(b.s[key], expected[key]))
            self.assertEqual(b.s['alpha'], expected['alpha'])
            self.assertEqual(b.s['iteration'], 202)

    def test_500_ceiling_charges_last_attempt_only(self):
        g, n = self.small_field()
        p = load(ROOT / 'PLAN.json')
        with tempfile.TemporaryDirectory() as td, patch('science.numeric.resources', return_value={}):
            b = worker.SafeBranch(Path(td), g, {'id': 'budget-control', 'q': 1}, p, {'selected_backend': 'cpu'}, {'test': 'budget'}, initial=n)
            b.attempts = 499
            with patch.object(worker, 'resources', return_value={}):
                b.batch_pending({'choice': {'observe': 2}, 'target_iteration': 20})
            self.assertEqual(b.attempts, 500)
            self.assertEqual(b.s['iteration'], 1)

    def test_host_pressure_requires_low_available_memory(self):
        sample = {'host': {'available_gib': 9}, 'pressure': {'full': {'avg10': 80}}}
        stop, began = handover.pressure_stop(sample, 40, None)
        self.assertFalse(stop)
        self.assertIsNone(began)
        sample['host']['available_gib'] = 3
        self.assertFalse(handover.pressure_stop(sample, 10, None)[0])
        self.assertTrue(handover.pressure_stop(sample, 41, 10)[0])

    def test_branch_driver_seals_and_reuses_real_terminal_checkpoint(self):
        g, n = self.small_field()
        p = load(ROOT / 'PLAN.json')
        spec = {'id': 'driver-control', 'seed': {'id': 'driver-control', 'q': 1}, 'nodes': 65, 'length': 12., 'backend': 'cpu',
                'initial_iteration': 198, 'already_spent_attempts': 499, 'maximum_additional_attempts': 1}
        identity = {'test': 'branch-driver', 'parent_checkpoint_sha256': 'fixture-parent'}
        full = {**identity, 'seed': spec['seed'], 'shape': list(g.shape), 'lengths': list(g.lengths), 'backend': 'cpu'}
        with tempfile.TemporaryDirectory() as td, patch('science.numeric.resources', return_value={}):
            out = Path(td)
            folder = out / 'continuation/driver-control'
            b = worker.SafeBranch(folder, g, spec['seed'], p, {'selected_backend': 'cpu'}, identity, initial=n)
            b.s['iteration'] = 198
            b.attempts = 499
            b.observe()
            b.persist()
            save(folder / 'attempts.json', {'attempts': 499})
            save(folder / 'planner.json', {'plateau_count': 0, 'plateau_epoch': 0})
            save(folder / 'MIGRATION.json', {'source_sha256': 'fixture-parent'})
            del b
            with patch.object(worker, 'migrate', return_value=({'selected_backend': 'cpu'}, full)), patch.object(worker, 'resources', return_value={}):
                result = worker.run_branch(out, out, spec, {'test': 'driver'}, p)
                self.assertEqual(result['status'], 'budget_exhausted_unresolved')
                self.assertEqual(result['attempts'], 500)
                self.assertEqual(result['additional_attempts'], 1)
                self.assertEqual(result['iteration'], 199)
                repeated = worker.run_branch(out, out, spec, {'test': 'driver'}, p)
                self.assertEqual(result, repeated)

    def test_evidence_crc_coverage_and_full_field_exclusion(self):
        specs = load(ROOT / 'SELECTION.json')['branches']
        rows = [{'seed': x['seed'], 'iteration': x['initial_iteration'], 'attempts': x['already_spent_attempts'], 'additional_attempts': 0,
                 'status': 'preparation_unresolved', 'metrics': {}, 'strict_stationary': False, 'boundary_admitted': False} for x in specs]
        record = {'recorded_at': {}, 'status': 'complete_pending_review', 'identity': {'package_sha256': sha(ROOT / 'SHA256SUMS')},
                  'maximum_additional_attempts': 1738, 'additional_attempts': 0, 'branches': rows, 'deferrals': {'scope': 'test fixture only'}}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / 'handover').mkdir()
            np.savez_compressed(out / 'retained-fixture.npz', field=np.zeros((3, 3, 3, 3)))
            save(out / 'record.json', record)
            worker.render(out, record, seal=True)
            inspected = publication.inspect_compact(out / 'evidence.zip')
            self.assertEqual(inspected, record)
            self.assertEqual(len(load(out / 'field-manifest.json')['fields']), 1)

    def test_merged_pr_without_number_and_squash_ancestry_is_recognized(self):
        with tempfile.TemporaryDirectory() as td:
            pub = Path(td)
            (pub / '.git').mkdir()
            save(publication.marker(pub), {'phase': 'published', 'package_sha256': sha(ROOT / 'SHA256SUMS'), 'branch': 'fixture-branch', 'commit': 'fixture-head', 'pr': {'url': 'https://example.invalid/pr/80'}})
            calls = []
            def command(repo, args, capture=False):
                calls.append(args)
                if args[:3] == ['git', 'branch', '--show-current']:
                    return 'fixture-branch'
                if args[:3] == ['gh', 'pr', 'view']:
                    return json.dumps({'state': 'MERGED', 'headRefOid': 'fixture-head', 'mergeCommit': {'oid': 'different-squash-oid'}, 'url': 'https://example.invalid/pr/80'})
                self.fail('Unexpected command: ' + repr(args))
            with patch.object(publication, 'command', side_effect=command):
                publication.execute('merge', pub, pub)
            self.assertEqual(load(publication.marker(pub))['phase'], 'merged')
            self.assertFalse(any('merge-base' in call for call in calls))

    def test_service_limits_and_nonroot_worker_command(self):
        argv = handover.launch_argv(Path('/example/repo'), Path('/example/out'))
        self.assertIn('--property=MemoryHigh=' + str(7 * 1024**3), argv)
        self.assertIn('--property=MemoryMax=' + str(8 * 1024**3), argv)
        self.assertIn('--property=MemorySwapMax=' + str(1024**3), argv)
        self.assertIn('--property=SendSIGKILL=no', argv)
        self.assertIn('--reset-env', argv)
        self.assertIn('--what=sleep:idle:handle-lid-switch', argv)

    def test_additive_publication_real_local_git_fixture(self):
        def git(folder, *args):
            return subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args], cwd=folder, check=True, capture_output=True, text=True).stdout.strip()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, pub, remote = root / 'repo', root / 'publication', root / 'origin.git'
            repo.mkdir()
            git(repo, 'init', '-b', 'main')
            (repo / 'README.md').write_text('# Existing research\n\nExisting findings and graphics are retained.\n')
            git(repo, 'add', 'README.md')
            git(repo, 'commit', '-m', 'Fixture baseline')
            git(root, 'clone', '--bare', str(repo), str(remote))
            with patch.object(publication, 'REMOTE', str(remote)):
                result = publication.prepare(repo, pub)
                again = publication.prepare(repo, pub)
            self.assertEqual(result, again)
            self.assertEqual(result['phase'], 'applied')
            self.assertIn('Existing findings and graphics are retained.', (pub / 'README.md').read_text())
            self.assertTrue((pub / publication.DOC / 'handover/assessment/ASSESSMENT.html').exists())
            git(pub, 'diff', '--cached', '--check')
            # The source checkout is not switched or dirtied by publication.
            self.assertEqual(git(repo, 'status', '--porcelain'), '')
            self.assertEqual(git(repo, 'branch', '--show-current'), 'main')

if __name__ == '__main__':
    unittest.main()
