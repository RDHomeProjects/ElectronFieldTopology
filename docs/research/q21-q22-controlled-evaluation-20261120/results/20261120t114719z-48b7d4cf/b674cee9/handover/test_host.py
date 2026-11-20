"""Meaningful controls for intervention isolation, recovery and native operators."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import numpy as np
from common import ROOT, load, save, sha, stamp
from engine import Engine, checkpoint, restore
from evaluations import array_sha, derivative_check, fit_history, gate_result, paired_summary, q22_compare, split_state, state_digest
from integrity import q22_inventory
from supervision import pressure_stop
import worker

class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from electron_field_topology.sf_time import Grid
        from electron_field_topology.skyrme import NORTH, rational_field
        cls.grid = Grid((17,) * 3, (8.,) * 3, 'fixed')
        cls.n = rational_field(cls.grid.points(), alpha=1, beta=1, scale=1.3, cutoff=3.)
        cls.n[cls.grid.fixed_mask()] = NORTH
        cls.p = load(ROOT / 'PLAN.json')['registered_gates']

    def test_actual_d4_directional_derivatives_and_mutation(self):
        before = array_sha(self.n)
        record = derivative_check(self.n, self.grid, load(ROOT / 'PLAN.json')['directional_derivatives'])
        self.assertTrue(record['passed'], record)
        self.assertEqual(before, array_sha(self.n))

    def test_memory_intervention_and_alpha_isolation(self):
        engine = Engine('cpu')
        state = engine.state(self.n)
        for _ in range(3):
            self.assertTrue(engine.step(state, self.grid)[0])
        before = state_digest(state)
        exact, reset = split_state(state), split_state(state, True)
        self.assertEqual(before, state_digest(exact))
        self.assertEqual(array_sha(exact['n']), array_sha(reset['n']))
        self.assertEqual(exact['alpha'], reset['alpha'])
        self.assertTrue(all(reset[k] is None for k in ['old_g', 'old_z', 'direction']))
        self.assertTrue(engine.step(exact, self.grid)[0])
        self.assertTrue(engine.step(reset, self.grid)[0])
        self.assertEqual(before, state_digest(state))

    def test_checkpoint_roundtrip_preserves_optimizer_memory(self):
        engine = Engine('cpu')
        state = engine.state(self.n)
        engine.step(state, self.grid)
        identity = {'test': 'checkpoint-memory'}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'state.npz'
            checkpoint(path, state, engine, identity)
            self.assertEqual(state_digest(state), state_digest(restore(path, engine, identity)))
            seal = load(path.with_suffix('.seal.json'))
            seal['sha256'] = '0' * 64
            save(path.with_suffix('.seal.json'), seal)
            with self.assertRaises(ValueError):
                restore(path, engine, identity)

    def test_charged_interrupted_attempts_are_not_refunded(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            self.assertEqual(worker.charge_attempt(folder, 0, 2), 1)
            self.assertEqual(worker.charge_attempt(folder, 0, 2), 2)
            self.assertTrue(load(folder / 'attempt-ledger.json')[0]['interrupted_or_uncommitted'])
            with self.assertRaises(RuntimeError):
                worker.charge_attempt(folder, 0, 2)
            (folder / 'attempt-ledger.json').unlink()
            with self.assertRaises(RuntimeError):
                worker.charge_attempt(folder, 1, 2)

    def test_failed_boundary_remains_failed(self):
        m = {'relative_force_l2': 1e-6, 'acceleration_max': 1e-5, 'hopf_integral': -21., 'minimum_corner_cone': .9, 'unit_error': 1e-16, 'tail_fraction': .002, 'guard_fraction': .003}
        gates = gate_result(m, 21, self.p)
        self.assertTrue(gates['strict_stationary'])
        self.assertFalse(gates['boundary_admitted'])
        self.assertFalse(gates['all_readiness_gates'])
        m['minimum_corner_cone'] = -1
        self.assertFalse(gate_result(m, 21, self.p)['representation'])

    def test_native_float32_cell_d4_same_values_no_normalization(self):
        from electron_field_topology.skyrme import Energy, K
        n = self.n.astype(np.float32)
        before = array_sha(n)
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            path = folder / 'field.npz'
            np.savez_compressed(path, field=n, h=.5)
            engine = Energy(17, .5, folder / 'reference-build', 'cell')
            parts, g = engine.evaluate(n.astype(np.float64))
            tangent = g - n.astype(np.float64) * np.sum(n.astype(np.float64) * g, axis=-1, keepdims=True)
            residual = float(np.sqrt(np.mean(tangent[2:-2, 2:-2, 2:-2]**2)) / (K * .5**3))
            spec = {'nodes': 17, 'spacing': .5, 'length': 8., 'energy': float(sum(parts)), 'cpu_residual': residual, 'sha256': sha(path)}
            result = q22_compare(path, spec, self.p, folder)
            self.assertEqual(result['source_dtype'], 'float32')
            self.assertTrue(result['values_preserved_by_promotion'])
            self.assertFalse(result['normalized'])
            self.assertEqual(result['promoted_array_sha256_before'], result['promoted_array_sha256_after'])
            self.assertAlmostEqual(result['cell']['tangent_gradient_rms'], residual, places=12)
            self.assertEqual(result['optimizer_steps'], 0)
        self.assertEqual(before, array_sha(n))

    def test_missing_q22_explicitly_deferred_and_wrong_explicit_refused(self):
        with tempfile.TemporaryDirectory() as td, patch('integrity.Path.home', return_value=Path(td)):
            result = q22_inventory(Path(td))
            self.assertEqual(result['status'], 'deferred_missing_exact_historical_field')
            wrong = Path(td) / 'different.npz'
            np.savez_compressed(wrong, field=self.n)
            with self.assertRaises(RuntimeError):
                q22_inventory(Path(td), wrong)

    def test_curve_fits_chronological_holdout_and_no_extension(self):
        rows = [{'iteration': 295 + i, 'metrics': {'relative_force_l2': .1 * np.exp(-.04 * i)}} for i in range(21)]
        result = fit_history(rows, 'relative_force_l2')
        self.assertFalse(result['budget_extension'])
        self.assertFalse(result['admission_inferred'])
        exponential = next(r for r in result['models'] if r['model'] == 'exponential')
        self.assertLess(exponential['holdout_relative_rmse'], 1e-10)

    def test_matched_iteration_comparison_does_not_compare_unmatched_endpoint(self):
        def row(i, f):
            return {'iteration': i, 'metrics': {'relative_force_l2': f, 'acceleration_max': f}}
        result = paired_summary({'exact': {'history': [row(295, 1), row(296, .8), row(297, .3)]}, 'memory-reset': {'history': [row(295, 1), row(296, .7)]}})
        self.assertEqual(result['matched_iterations'], [295, 296])
        self.assertTrue(result['last_matched_joint_reset_improvement'])

    def test_resource_pause_requires_sustained_pressure(self):
        sample = {'host': {'available_gib': 3}, 'pressure': {'full': {'avg10': 25}}}
        stop, began = pressure_stop(sample, 10., None)
        self.assertFalse(stop)
        self.assertTrue(pressure_stop(sample, 41., began)[0])

    def test_compact_archive_preserves_frozen_manifests_excludes_fields(self):
        from publication import checked_evidence
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / 'handover').mkdir()
            (out / 'handover/SHA256SUMS').write_text('frozen-source-data\n')
            save(out / 'record.json', {'status': 'complete_pending_review'})
            np.savez_compressed(out / 'retained.npz', field=self.n)
            worker.seal(out)
            with zipfile.ZipFile(out / 'evidence.zip') as z:
                self.assertIn('handover/SHA256SUMS', z.namelist())
                self.assertNotIn('retained.npz', z.namelist())
            checked_evidence(out / 'evidence.zip')
            self.assertEqual(len(load(out / 'FIELD-MANIFEST.json')['fields']), 1)

    def test_arm_orderly_resume_matches_uninterrupted_cpu_path(self):
        parent = Engine('cpu').state(self.n)
        for _ in range(3):
            Engine('cpu').step(parent, self.grid)
        parent['iteration'] = 295
        spec = {'state': {'sha256': 'synthetic-parent'}, 'attempts_per_arm': 3}
        backend = {'selected_backend': 'cpu'}
        fake_gate = {'representation': True, 'strict_stationary': False, 'boundary_admitted': False, 'all_readiness_gates': False}
        class PauseEngine(Engine):
            def step(self, state, grid):
                result = super().step(state, grid)
                worker.STOP.set()
                return result
        with tempfile.TemporaryDirectory() as td, patch('worker.gate_result', return_value=fake_gate), patch('worker.check_reserve'):
            baseline = Path(td) / 'baseline'
            paused = Path(td) / 'paused'
            for out in [baseline, paused]:
                out.mkdir()
                save(out / 'identity.json', {'id': 'synthetic-recovery-control'})
            worker.STOP.clear()
            normal = worker.run_arm(baseline, 'exact', parent, backend, self.grid, self.p, spec, {})
            with patch('worker.Engine', PauseEngine), self.assertRaises(KeyboardInterrupt):
                worker.run_arm(paused, 'exact', parent, backend, self.grid, self.p, spec, {})
            worker.STOP.clear()
            recovered = worker.run_arm(paused, 'exact', parent, backend, self.grid, self.p, spec, {})
            self.assertEqual(normal['accepted_steps'], recovered['accepted_steps'])
            self.assertEqual(recovered['attempts_charged'], 3)
            with np.load(baseline / 'q21/exact/endpoint.npz') as a, np.load(paused / 'q21/exact/endpoint.npz') as b:
                for key in ['n', 'old_g', 'old_z', 'direction', 'alpha', 'iteration']:
                    self.assertTrue(np.array_equal(a[key], b[key]), key)

    def test_full_worker_synthetic_flow_and_q22_deferral(self):
        import copy
        parent = Engine('cpu').state(self.n)
        Engine('cpu').step(parent, self.grid)
        parent['iteration'] = 295
        original_load = worker.load
        plan = copy.deepcopy(load(ROOT / 'PLAN.json'))
        plan['q21']['attempts_per_arm'] = 2
        plan['q21']['spec'].update(nodes=17, length=8.)
        plan['q21']['spec']['expected'] = worker.metrics(parent['n'], self.grid, self.p)
        def instrument_gates(m, q, p):
            # Synthetic test instrumentation only: force both Q21 arms through
            # the small real-kernel control; this is not scientific admission.
            return {'representation': True, 'strict_stationary': q == 2, 'boundary_admitted': q == 2, 'all_readiness_gates': q == 2}
        def planned_load(path):
            return plan if Path(path) == ROOT / 'PLAN.json' else original_load(path)
        with tempfile.TemporaryDirectory() as td:
            repo, out = Path(td) / 'repo', Path(td) / 'out'
            repo.mkdir(); out.mkdir()
            np.savez_compressed(repo / 'q2.npz', field=self.n)
            plan['q2'].update(nodes=17, length=8., original_relative_path='q2.npz', sha256=sha(repo / 'q2.npz'))
            plan['q2']['expected'] = worker.metrics(self.n, self.grid, self.p)
            save(out / 'identity.json', {'package_sha256': sha(ROOT / 'SHA256SUMS'), 'requested_backend': 'cpu', 'synthetic': True})
            save(out / 'Q22-INVENTORY.json', {'status': 'deferred_missing_exact_historical_field', 'reason': 'synthetic missing-field control'})
            worker.STOP.clear()
            with patch('worker.verify_manifest'), patch('worker.verify_sources'), patch('worker.check_reserve'), patch('worker.original_run', return_value=repo), patch('worker.q21_sources'), patch('worker.source_state', return_value=(parent, 'cpu')), patch('worker.load', side_effect=planned_load), patch('worker.gate_result', side_effect=instrument_gates):
                worker.execute(repo, out)
            record = load(out / 'record.json')
            self.assertEqual(record['status'], 'complete_pending_review')
            self.assertEqual(record['charged_q21_attempts'], 4)
            self.assertEqual(record['q22']['status'], 'deferred_missing_exact_historical_field')
            self.assertEqual(len(record['arms']), 2)
            self.assertTrue((out / 'REPORT.html').exists())
            self.assertTrue((out / 'q21-comparison.svg').exists())
            from publication import checked_evidence
            checked_evidence(out / 'evidence.zip')

if __name__ == '__main__':
    unittest.main(verbosity=2)
