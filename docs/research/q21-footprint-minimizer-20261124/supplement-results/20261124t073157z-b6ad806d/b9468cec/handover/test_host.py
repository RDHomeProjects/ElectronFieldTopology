"""Small real-kernel checks; fixtures are not new Q21 scientific results."""
import ast,copy,hashlib,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from common import ROOT,load,save,sha,seal,verify_zip
sys.path.append(str(ROOT/'kernel'))
from engine import Engine
from evaluations import metrics,derivative_check,gate_result
from worker import MeasuredEngine,run_arm
from science import footprint,response_fits,next_batch
from probe import route

class Checks(unittest.TestCase):
    def field(self):
        from electron_field_topology.sf_time import Grid
        from electron_field_topology.skyrme import rational_field,NORTH
        g=Grid((17,)*3,(8.,)*3,'fixed');n=rational_field(g.points(),kind='axial',alpha=1,beta=1,scale=1.3,cutoff=3.5);n[g.fixed_mask()]=NORTH;return n,g

    def test_inherited_exact_engine_methods_byte_equivalent(self):
        with zipfile.ZipFile(ROOT/'data/completed-evidence.zip') as z:old=z.read('handover/legacy/engine.py').decode()
        def methods(text):
            node=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='Engine')
            return {n.name:ast.dump(n) for n in node.body if isinstance(n,ast.FunctionDef)}
        a,b=methods(old),methods((ROOT/'kernel/engine.py').read_text())
        for key in ['step','value','state','cone']:self.assertEqual(a[key],b[key])

    def test_real_descent_gradient_constraint_and_exact_control(self):
        n,g=self.field();settings={'epsilons':[.001,.0003,.0001],'rtol':.002,'atol':1e-7}
        self.assertTrue(derivative_check(n,g,settings)['passed']);plan=load(ROOT/'PLAN.json')
        with tempfile.TemporaryDirectory() as td:
            for method in ['exact-cg','sobolev-descent']:
                folder=Path(td)/method;folder.mkdir();e=MeasuredEngine('cpu',folder,method,plan);s=e.state(n);s.update(alpha=.08,iteration=625)
                reference=Engine('cpu',.25);control=reference.state(n);control.update(alpha=.08,iteration=625)
                before=reference.value(n,g)[0]
                for _ in range(3):
                    accepted,r=e.step(s,g);self.assertTrue(accepted)
                    if method=='exact-cg':
                        reference.step(control,g);self.assertTrue(np.array_equal(s['n'],control['n']))
                self.assertLess(r['energy'],before);self.assertLess(np.max(abs(np.linalg.norm(s['n'],axis=-1)-1)),1e-12)
                self.assertTrue(np.array_equal(s['n'][g.fixed_mask()],n[g.fixed_mask()]))
                if method=='sobolev-descent':self.assertIsNone(s['old_g']);self.assertIsNone(s['old_z']);self.assertIsNone(s['direction'])
                self.assertEqual(e.calls['optimizer_energy_gradient_calls'],sum([2,2,2]))

    def test_adaptive_footprint_is_native_and_read_only(self):
        n,g=self.field();before=n.copy()
        with tempfile.TemporaryDirectory() as td:
            r=footprint(n,g,Path(td),'host-fixture')
            self.assertTrue(np.array_equal(n,before));self.assertFalse(r['source_modified']);self.assertTrue((Path(td)/'capture.png').exists());self.assertTrue((Path(td)/'slices.png').exists())
            for key in ['energy','squared_force','squared_acceleration','angular_variation']:
                values=[row[key+'_capture_fraction'] for row in r['rows']];self.assertTrue(np.all(np.diff(values)>=-1e-14));self.assertAlmostEqual(values[-1],1.,places=12)
            self.assertLessEqual(len(r['rows']),load(ROOT/'PLAN.json')['maximum_footprint_probes_per_field'])

    def test_forecast_requires_holdout_skill_and_joint_progress(self):
        plan=load(ROOT/'PLAN.json');history=[]
        for i in range(30):history.append({'accepted_updates':i,'metrics':{'relative_force_l2':.01*np.exp(-.025*i),'acceleration_max':.1*np.exp(-.03*i)}})
        result=response_fits(history,plan);self.assertTrue(result['qualified']);self.assertEqual(result['selected']['model'],'exponential');d=next_batch(history,plan);self.assertTrue(d['continue']);self.assertGreaterEqual(d['attempts'],5);self.assertLessEqual(d['attempts'],20)
        flat=[{'accepted_updates':i,'metrics':{'relative_force_l2':.01,'acceleration_max':.1}} for i in range(30)]
        self.assertFalse(next_batch(flat,plan)['continue'])

    def test_auto_cpu_fallback_and_explicit_cuda_deferral(self):
        self.assertEqual(route('auto',12,6.71,True)['selected'],'cpu')
        self.assertEqual(route('auto',12,8.,True)['selected'],'cuda')
        self.assertEqual(route('cpu',12,8.,True)['selected'],'cpu')
        with self.assertRaises(RuntimeError):route('cuda',12,6.71,True)
        with self.assertRaises(RuntimeError):route('auto',7,8.,True)

    def test_sealer_preserves_nested_manifests_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'handover').mkdir();(root/'handover/SHA256SUMS').write_text('retained original manifest\n');(root/'x.txt').write_text('evidence\n');seal(root)
            items=verify_zip(root/'evidence.zip');self.assertIn('handover/SHA256SUMS',items)
            with zipfile.ZipFile(root/'bad.zip','w') as z:z.writestr('x.txt','changed');z.writestr('SHA256SUMS',sha(root/'x.txt')+'  x.txt\n')
            with self.assertRaises(RuntimeError):verify_zip(root/'bad.zip')

    def test_resume_keeps_optimizer_memory_and_does_not_refund_attempt(self):
        import worker
        from electron_field_topology import sf_time
        n,g=self.field();base=Engine('cpu');s=base.state(n);s.update(iteration=625,alpha=.08,pairs=[])
        plan=load(ROOT/'PLAN.json');plan.update(initial_attempts_per_arm=4,maximum_attempts_per_arm=6)
        def measure(a,grid,p):
            m=metrics(a,grid,p);m.update(hopf_integral=21.,tail_fraction=0.,guard_fraction=0.);return m
        expected=measure(n,g,plan['registered_gates'])
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);save(out/'identity.json',{'fixture':True});checks=[0]
            def pause():
                checks[0]+=1
                if checks[0]==4:raise KeyboardInterrupt('fixture interruption')
            with patch.object(sf_time,'Grid',lambda *_:g),patch.object(worker,'load_parent',lambda *_:copy.deepcopy(s)),patch.object(worker,'source_endpoint',lambda *_:Path('/unused-fixture')),patch.object(worker,'source_metrics',lambda *_:expected),patch.object(worker,'metrics',measure):
                with self.assertRaises(KeyboardInterrupt):run_arm(out,Path('/unused-fixture'),'cpu','exact-cg',plan,{},pause)
                folder=out/'cases/exact-cg';ledger=load(folder/'ATTEMPTS.json');self.assertEqual(len(ledger),2)
                # Represents a charged attempt lost between execution and checkpoint commit.
                ledger.append({'attempt':3,'precharged':True});save(folder/'ATTEMPTS.json',ledger)
                r=run_arm(out,Path('/unused-fixture'),'cpu','exact-cg',plan,{},lambda:None)
                self.assertEqual(r['charged_attempts'],4);self.assertEqual(r['accepted_updates'],3);self.assertEqual(r['final']['native_iteration'],628)
                self.assertEqual(r['reason'],'insufficient_recent_measurements')

    def test_plan_gates_equal_completed_source(self):
        with zipfile.ZipFile(ROOT/'data/completed-evidence.zip') as z:original=json.loads(z.read('handover/legacy/PLAN.json'))['registered_gates']
        p=load(ROOT/'PLAN.json');self.assertEqual(p['registered_gates'],original);self.assertEqual(p['maximum_optimizer_attempts'],240);self.assertEqual(p['physical_time_steps'],0);self.assertFalse(p['adaptive_grid_evolution']['implemented_here'])

    def test_objective_call_ceiling_prevents_an_extra_evaluation(self):
        from worker import CallCeiling
        n,g=self.field();p=load(ROOT/'PLAN.json');p['maximum_objective_calls_per_arm']=2
        with tempfile.TemporaryDirectory() as td:
            e=MeasuredEngine('cpu',Path(td),'sobolev-descent',p);s=e.state(n);self.assertTrue(e.step(s,g)[0]);before=s['n'].copy()
            with self.assertRaises(CallCeiling):e.step(s,g)
            self.assertEqual(e.calls['optimizer_energy_gradient_calls'],2);self.assertTrue(np.array_equal(before,s['n']))

    def test_host_reserve_interrupts_and_seals_for_resume(self):
        import worker
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);out=root/'output';out.mkdir();save(out/'identity.json',{'fixture':True})
            with patch.object(worker,'host',lambda:{'available_gib':5.}):code=worker.run(root,out,root,'cpu')
            self.assertEqual(code,0);self.assertEqual(load(out/'status.json')['status'],'interrupted');verify_zip(out/'evidence.zip')

    def test_worker_pipeline_report_and_seal(self):
        import worker
        from electron_field_topology import sf_time
        n,g=self.field();base=Engine('cpu');state=base.state(n);state.update(iteration=625,alpha=.08,pairs=[])
        p=load(ROOT/'PLAN.json');p.update(initial_attempts_per_arm=4,maximum_attempts_per_arm=4,maximum_optimizer_attempts=8)
        original_load=load
        def fixture_load(path):return p if Path(path)==ROOT/'PLAN.json' else original_load(path)
        expected=metrics(n,g,p['registered_gates'])
        gate_fixture={'representation':True,'strict_stationary':False,'boundary_admitted':True,'all_readiness_gates':False}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);out=root/'output';out.mkdir();save(out/'identity.json',{'fixture':'synthetic-control-flow-not-Q21-evidence'})
            source=root/'endpoint.npz';np.savez(source,n=n,iteration=625,backend='cpu');before=sha(source)
            with patch.object(sf_time,'Grid',lambda *_:g),patch.object(worker,'load',fixture_load),patch.object(worker,'load_parent',lambda *_:copy.deepcopy(state)),patch.object(worker,'source_endpoint',lambda *_:source),patch.object(worker,'source_metrics',lambda *_:expected),patch.object(worker,'gate_result',lambda *_:gate_fixture):
                code=worker.run(root,out,root,'cpu')
            self.assertEqual(code,0);self.assertEqual(load(out/'status.json')['status'],'complete_pending_review');self.assertEqual(sha(source),before)
            self.assertEqual(len(load(out/'record.json')['cases']),2);self.assertTrue((out/'method-curves.png').is_file());self.assertTrue((out/'REPORT.html').is_file());verify_zip(out/'evidence.zip')
            self.assertEqual(sum(r['charged_attempts'] for r in load(out/'record.json')['cases']),8)

    def test_publication_staging_payload_rehearsal_no_network(self):
        import local_publication as pub
        def command(repo,args,capture=False):
            if args[:3]==['git','remote','get-url']:return pub.REMOTE
            if args[:2]==['git','status']:return ''
            if args[:2]==['git','rev-parse']:return 'f'*40
            return '' if capture else None
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo';repo.mkdir();(repo/'.git').mkdir();(repo/'README.md').write_text('# Fixture repository\n')
            with patch.object(pub,'cmd',command),patch.object(pub,'checks') as check:
                state=pub.prepare(repo,repo)
            self.assertEqual(state['phase'],'applied');check.assert_called_once()
            self.assertIn('README.md',state['stage_paths']);self.assertTrue(any(n.endswith('/PROTOCOL.md') for n in state['immutable_files']))
            self.assertTrue(any(n.endswith('/assessment/ASSESSMENT.html') for n in state['immutable_files']))
            for name,digest in state['immutable_files'].items():self.assertEqual(sha(repo/name),digest)
            text=(repo/pub.DOC/'README.md').read_text();self.assertIn('illustrated review',text);self.assertIn('registered protocol',text)

if __name__=='__main__':unittest.main(verbosity=2)
