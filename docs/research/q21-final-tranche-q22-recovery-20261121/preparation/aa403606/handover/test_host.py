"""Synthetic recovery, scheduling and real CPU-kernel checkpoint controls."""
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import numpy as np
from common import ROOT, canonical, load, manifest, save, sha, stamp
from engine import Engine, checkpoint, restore
from evaluations import gate_result, metrics, state_digest
from integrity import baseline
from planner import decide
from recovery import Search
import continuation
import worker

class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from electron_field_topology.sf_time import Grid
        from electron_field_topology.skyrme import rational_field
        cls.plan = load(ROOT/'PLAN.json')
        cls.grid = Grid((17,)*3, (8.,)*3, 'fixed')
        cls.n = rational_field(cls.grid.points(), alpha=1, beta=1, scale=1.3, cutoff=3.)
        cls.n[cls.grid.fixed_mask()] = [0,0,1]
        buffer = io.BytesIO(); np.savez_compressed(buffer, field=cls.n.astype(np.float32), h=.5)
        cls.field_bytes = buffer.getvalue()
        cls.expected = hashlib.sha256(cls.field_bytes).hexdigest()

    def search(self, out, settings=None, **kwargs):
        return Search(out, settings or copy.deepcopy(self.plan['recovery']), self.expected, **kwargs)

    def ample_disk(self):
        return patch('recovery.shutil.disk_usage', return_value=shutil._ntuple_diskusage(1000*1024**3, 0, 1000*1024**3))

    def test_reviewed_source_identity_and_exact_parent_selection(self):
        objects, hashes = baseline()
        self.assertEqual(len(hashes), 74)
        self.assertEqual(objects['q21/exact/record.json']['final']['iteration'], 315)
        self.assertEqual(self.plan['q21']['source_field']['sha256'], 'ad5e13216a4271a212c6a67c810d4394666dc570c33c3a48ff0dc005b01cf7b0')
        self.assertTrue(self.plan['q21']['retain_optimizer_memory'])
        self.assertEqual(self.plan['q21']['maximum_additional_attempts'], 20)

    def test_recover_direct_checkpoint_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as td, self.ample_disk():
            home=Path(td); source=home/'ElectronFieldTopology-old/renamed.npz';source.parent.mkdir();source.write_bytes(self.field_bytes)
            result=self.search(home/'output').run(home=home)
            self.assertEqual(result['status'],'authenticated_recovered')
            self.assertEqual(Path(result['path']).read_bytes(),self.field_bytes)
            self.assertEqual(source.read_bytes(),self.field_bytes)
            self.assertFalse(result['source_modified'])

    def test_recover_nested_zip_uses_hash_not_filename(self):
        with tempfile.TemporaryDirectory() as td, self.ample_disk():
            home=Path(td); downloads=home/'Downloads';downloads.mkdir()
            nested=io.BytesIO()
            with zipfile.ZipFile(nested,'w') as z:z.writestr('different-name.npz',self.field_bytes)
            with zipfile.ZipFile(downloads/'ElectronFieldTopology-Q22-backup.zip','w') as z:z.writestr('retained/fields.zip',nested.getvalue());z.writestr('../unsafe.npz',b'not data')
            result=self.search(home/'output').run(home=home)
            self.assertEqual(result['status'],'authenticated_recovered')
            self.assertIn('fields.zip!different-name.npz',result['source_locator'])
            self.assertEqual(sha(Path(result['path'])),self.expected)
            self.assertFalse((home/'unsafe.npz').exists())

    def test_recover_tar_gzip_checkpoint(self):
        with tempfile.TemporaryDirectory() as td, self.ample_disk():
            home=Path(td); archive=home/'ElectronFieldTopology-Q22.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                entry=tarfile.TarInfo('states/final.npz');entry.size=len(self.field_bytes);tar.addfile(entry,io.BytesIO(self.field_bytes))
            result=self.search(home/'output').run(extra_roots=[archive],home=home)
            self.assertEqual(result['status'],'authenticated_recovered')
            self.assertEqual(Path(result['path']).read_bytes(),self.field_bytes)

    def test_declared_absence_is_not_global_absence(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);result=self.search(home/'output').run(home=home)
            self.assertEqual(result['status'],'deferred_missing_exact_historical_field')
            self.assertTrue(result['not_a_global_absence_proof'])

    def test_corrupt_archive_remains_an_explicit_coverage_gap(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);project=home/'ElectronFieldTopology-old';project.mkdir();(project/'bad.zip').write_bytes(b'not a zip')
            result=self.search(home/'out').run(home=home)
            self.assertEqual(result['status'],'deferred_missing_exact_historical_field')
            self.assertGreater(result['coverage_gap_count'],0)
            self.assertFalse(result['coverage_complete_for_declared_scan'])

    def test_nested_depth_limit_is_recorded_as_coverage_gap(self):
        with tempfile.TemporaryDirectory() as td, self.ample_disk():
            home=Path(td); project=home/'ElectronFieldTopology-old';project.mkdir()
            inner=io.BytesIO()
            with zipfile.ZipFile(inner,'w') as z:z.writestr('final.npz',self.field_bytes)
            with zipfile.ZipFile(project/'outer.zip','w') as z:z.writestr('inner.zip',inner.getvalue())
            settings=copy.deepcopy(self.plan['recovery']);settings['maximum_nested_depth']=0
            result=self.search(home/'output',settings).run(home=home)
            self.assertEqual(result['status'],'deferred_missing_exact_historical_field')
            self.assertGreater(result['coverage_gap_count'],0)
            self.assertFalse(result['coverage_complete_for_declared_scan'])

    def test_search_budget_is_charged_and_retained_across_pause(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out'; settings=copy.deepcopy(self.plan['recovery']);settings['maximum_candidate_and_nested_stream_bytes']=10
            first=self.search(out,settings);first.charge(8,'synthetic charge')
            second=self.search(out,settings)
            self.assertEqual(second.budget['stream_bytes_charged'],8)
            with self.assertRaises(RuntimeError):second.charge(3,'exceeds declared total')
            (out/'recovery/BUDGET.json').unlink()
            with self.assertRaises(RuntimeError):self.search(out,settings)

    def history(self, improving=True):
        sign=-1 if improving else 1
        return [{'iteration':295+i,'metrics':{'relative_force_l2':.002*np.exp(sign*.01*i),'acceleration_max':.02*np.exp(sign*.01*i)}} for i in range(26)]

    def test_initial_five_probe_and_curve_sized_followup(self):
        first=decide(self.history(),0,self.plan['adaptive_policy'],self.plan['registered_gates'])
        self.assertEqual(first['next_attempts'],5)
        next_decision=decide(self.history(),5,self.plan['adaptive_policy'],self.plan['registered_gates'])
        self.assertEqual(next_decision['action'],'continue')
        self.assertTrue(5<=next_decision['next_attempts']<=10)
        self.assertIn('forecast_candidates',next_decision)
        self.assertFalse(next_decision['fit_admission'])
        self.assertFalse(next_decision['budget_extension'])

    def test_no_joint_progress_and_total_cap_stop_allocations(self):
        result=decide(self.history(False),5,self.plan['adaptive_policy'],self.plan['registered_gates'])
        self.assertEqual(result['action'],'stop')
        result=decide(self.history(),20,self.plan['adaptive_policy'],self.plan['registered_gates'])
        self.assertEqual(result['next_attempts'],0)

    def test_interrupted_attempts_and_lost_ledger_cannot_refund_budget(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            self.assertEqual(continuation.charge(folder,0,2),1)
            self.assertEqual(continuation.charge(folder,0,2),2)
            self.assertTrue(load(folder/'attempt-ledger.json')[0]['interrupted_or_uncommitted'])
            with self.assertRaises(RuntimeError):continuation.charge(folder,0,2)
            (folder/'attempt-ledger.json').unlink()
            with self.assertRaises(RuntimeError):continuation.charge(folder,1,2)

    def test_actual_cpu_continuation_preserves_memory_and_resumes(self):
        engine=Engine('cpu');parent=engine.state(self.n)
        for _ in range(3):engine.step(parent,self.grid)
        parent['iteration']=315
        initial=state_digest(parent)
        plan=copy.deepcopy(self.plan);plan['q21'].update(nodes=17,length=8.,maximum_additional_attempts=6,expected_metrics=metrics(parent['n'],self.grid,plan['registered_gates']))
        warm=[{'iteration':295+i,'metrics':copy.deepcopy(plan['q21']['expected_metrics']),'alpha':parent['alpha'],'objective_calls':0} for i in range(21)]
        fake={'representation':True,'strict_stationary':False,'boundary_admitted':False,'all_readiness_gates':False}
        def decisions(history,charged,policy,gates,ceiling):
            return {'recorded_at':stamp(),'iteration':history[-1]['iteration'],'action':'continue','reason':'synthetic control only','next_attempts':min(5,ceiling-charged)}
        paused=[False]
        def stop_once():
            return paused[0]
        class PauseEngine(Engine):
            def step(self,state,grid):
                result=super().step(state,grid);paused[0]=True;return result
        with tempfile.TemporaryDirectory() as td, patch('continuation.baseline',return_value=({'q21/exact/record.json':{'history':warm}},{})),patch('continuation.gate_result',return_value=fake),patch('continuation.check_reserve'),patch('continuation.decide',side_effect=decisions):
            normal, interrupted=Path(td)/'normal',Path(td)/'paused'
            for out in [normal,interrupted]:out.mkdir();save(out/'identity.json',{'id':'synthetic exact-memory control'})
            backend={'selected_backend':'cpu'}
            expected=continuation.run(Path(td),normal,parent,backend,self.grid,plan,lambda:False,{})
            with patch('continuation.Engine',PauseEngine),self.assertRaises(KeyboardInterrupt):
                continuation.run(Path(td),interrupted,parent,backend,self.grid,plan,stop_once,{})
            recovered=continuation.run(Path(td),interrupted,parent,backend,self.grid,plan,lambda:False,{})
            self.assertEqual(expected['accepted_new_steps'],recovered['accepted_new_steps'])
            self.assertEqual(recovered['new_attempts_charged'],6)
            self.assertEqual(len(list((interrupted/'q21/exact/states').glob('*.npz'))),7)
            with np.load(normal/'q21/exact/endpoint.npz') as a,np.load(interrupted/'q21/exact/endpoint.npz') as b:
                for key in ['n','old_g','old_z','direction','alpha','iteration']:self.assertTrue(np.array_equal(a[key],b[key]),key)
            self.assertEqual(initial,state_digest(parent))

    def test_boundary_failures_and_source_memory_are_not_relabelled(self):
        m={'relative_force_l2':1e-6,'acceleration_max':1e-5,'hopf_integral':-21.,'minimum_corner_cone':.9,'unit_error':1e-16,'tail_fraction':.002,'guard_fraction':.003}
        result=gate_result(m,21,self.plan['registered_gates'])
        self.assertTrue(result['strict_stationary']);self.assertFalse(result['all_readiness_gates'])

    def test_recovered_float32_values_evaluate_under_both_native_operators(self):
        from evaluations import q22_compare
        from electron_field_topology.skyrme import Energy,K
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);source=folder/'native.npz';source.write_bytes(self.field_bytes)
            with np.load(source) as z:n=z['field'].astype(np.float64)
            cell=Energy(17,.5,folder/'reference-cell','cell');parts,g=cell.evaluate(n);tangent=g-n*np.sum(n*g,axis=-1,keepdims=True)
            residual=float(np.sqrt(np.mean(tangent[2:-2,2:-2,2:-2]**2))/(K*.5**3))
            spec={'nodes':17,'spacing':.5,'length':8.,'energy':float(sum(parts)),'cpu_residual':residual,'sha256':self.expected}
            result=q22_compare(source,spec,self.plan['registered_gates'],folder)
            self.assertEqual(result['source_dtype'],'float32')
            self.assertFalse(result['normalized']);self.assertFalse(result['resampled'])
            self.assertTrue(result['values_preserved_by_promotion'])
            self.assertEqual(result['promoted_array_sha256_before'],result['promoted_array_sha256_after'])
            self.assertEqual(result['optimizer_steps'],0)

    def test_full_worker_synthetic_flow_keeps_q22_deferred_and_finishes_tranche(self):
        parent=Engine('cpu').state(self.n)
        for _ in range(2):Engine('cpu').step(parent,self.grid)
        parent['iteration']=315
        plan=copy.deepcopy(self.plan)
        plan['q21'].update(nodes=17,length=8.,maximum_additional_attempts=5,expected_metrics=metrics(parent['n'],self.grid,plan['registered_gates']))
        warm=[]
        for i in range(21):
            m=copy.deepcopy(plan['q21']['expected_metrics'])
            for key in ['relative_force_l2','acceleration_max']:m[key]*=np.exp(.01*(20-i))
            warm.append({'iteration':295+i,'metrics':m,'alpha':parent['alpha'],'objective_calls':0})
        original_load=worker.load
        def planned_load(path):return plan if Path(path)==ROOT/'PLAN.json' else original_load(path)
        def fake_gate(m,q,p):return {'representation':True,'strict_stationary':q==2,'boundary_admitted':q==2,'all_readiness_gates':q==2}
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);repo=home/'repo';out=home/'out';repo.mkdir();out.mkdir()
            np.savez_compressed(repo/'q2.npz',field=self.n)
            plan['q2'].update(nodes=17,length=8.,original_relative_path='q2.npz',sha256=sha(repo/'q2.npz'),expected=metrics(self.n,self.grid,plan['registered_gates']))
            search={'explicit_q22':None,'extra_roots':[]}
            save(out/'SEARCH-CONFIG.json',search)
            save(out/'identity.json',{'package_sha256':sha(ROOT/'SHA256SUMS'),'requested_backend':'cpu','search_configuration_sha256':canonical(search),'synthetic':True})
            worker.STOP.clear()
            with patch('worker.verify_manifest'),patch('worker.verify_sources'),patch('worker.source_checkpoint'),patch('worker.original_run',return_value=repo),patch('worker.read_parent',return_value=(parent,'cpu')),patch('worker.load',side_effect=planned_load),patch('worker.gate_result',side_effect=fake_gate),patch('worker.check_reserve'),patch('continuation.check_reserve'),patch('continuation.gate_result',return_value=fake_gate(None,21,None)),patch('continuation.baseline',return_value=({'q21/exact/record.json':{'history':warm}},{})),patch('recovery.Path.home',return_value=home):
                worker.execute(repo,out)
            r=load(out/'record.json')
            self.assertEqual(r['status'],'complete_pending_review')
            self.assertEqual(r['new_q21_attempts_charged'],5)
            self.assertEqual(r['q21']['final_iteration'],320)
            self.assertEqual(r['q22']['status'],'deferred_missing_exact_historical_field')
            from publication import checked_evidence
            checked_evidence(out/'evidence.zip')
            self.assertTrue((out/'REPORT.html').exists())

    def test_compact_seal_excludes_recovered_and_optimizer_fields(self):
        from publication import checked_evidence
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);(out/'recovered').mkdir();(out/'recovered/q22-native.npz').write_bytes(self.field_bytes)
            (out/'handover').mkdir();(out/'handover/SHA256SUMS').write_text('preserved manifest\n')
            save(out/'record.json',{'synthetic':True})
            worker.seal(out)
            checked_evidence(out/'evidence.zip')
            with zipfile.ZipFile(out/'evidence.zip') as z:
                self.assertNotIn('recovered/q22-native.npz',z.namelist());self.assertIn('handover/SHA256SUMS',z.namelist())
            self.assertEqual(load(out/'FIELD-MANIFEST.json')['fields'][0]['sha256'],self.expected)

if __name__=='__main__':
    unittest.main(verbosity=2)
