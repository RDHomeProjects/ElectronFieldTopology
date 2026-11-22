"""Small-grid numerical and recovery controls; no workstation evidence invented."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from common import ROOT,load,save,sha,canonical,manifest,verify_manifest
from electron_field_topology.sf_time import Grid
from electron_field_topology.skyrme import rational_field
from optimizers import ComparisonEngine,write_state,read_state
from numerics import transformed,curvature_probe,geometry
from curves import analyze,uniform,writhe
from evaluations import gate_result

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g=Grid((17,)*3,(12.,)*3,'fixed');cls.n=rational_field(cls.g.points(),scale=2.,cutoff=4.5);cls.n[cls.g.fixed_mask()]=[0,0,1]
    def test_methods_descend_same_action(self):
        e=ComparisonEngine('cpu')
        for method in ['cg','sd','inertial','lbfgs']:
            s=e.state(self.n);last=e.value(s['n'],self.g)[0]
            for _ in range(5):
                ok,r=e.step_method(s,self.g,method);self.assertTrue(ok);self.assertLess(r['energy'],last);last=r['energy'];self.assertLess(np.max(abs(np.linalg.norm(s['n'],axis=-1)-1)),1e-12)
    def test_exact_cg_is_unchanged(self):
        from engine import Engine
        a,b=Engine('cpu'),ComparisonEngine('cpu');sa,sb=a.state(self.n),b.state(self.n)
        for _ in range(3):a.step(sa,self.g);b.step_method(sb,self.g,'cg')
        for k in ['n','old_g','old_z','direction']:np.testing.assert_array_equal(sa[k],sb[k])
    def test_lbfgs_checkpoint_restores_memory(self):
        e=ComparisonEngine('cpu');s=e.state(self.n)
        for _ in range(3):e.step_method(s,self.g,'lbfgs')
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.npz';identity={'test':'lbfgs'};write_state(path,s,e,identity);r=read_state(path,e,identity)
            self.assertGreater(len(r['pairs']),0);e.step_method(s,self.g,'lbfgs');e.step_method(r,self.g,'lbfgs');np.testing.assert_array_equal(s['n'],r['n'])
            with path.open('ab') as f:f.write(b'corrupt')
            with self.assertRaises(RuntimeError):read_state(path,e,identity)
    def test_domain_and_mesh_are_separate_variables(self):
        n,g,info=transformed(self.n,self.g,{'kind':'domain','padding':2});np.testing.assert_array_equal(n[2:-2,2:-2,2:-2],self.n);self.assertEqual(g.spacing,self.g.spacing)
        n,g,info=transformed(self.n,self.g,{'kind':'mesh','nodes':25});self.assertEqual(g.lengths,self.g.lengths);self.assertNotEqual(g.spacing,self.g.spacing)
    def test_new_map_degree_labels(self):
        from numerics import transformed
        for arm in load(ROOT/'PLAN.json')['arms']:
            if arm['kind']=='fresh':
                degree=2*arm['alpha']+7*arm['beta'] if arm['family']=='torus72' else 3*arm['alpha']+2*arm['beta'];self.assertEqual(degree,21)
    def test_curvature_negative_control(self):
        class Toy:
            xp=np
            def value(self,n,g):return -float(np.sum(n[...,:2]**2)),np.concatenate([-2*n[...,:2],np.zeros_like(n[...,:1])],axis=-1)
            def host(self,n):return n
        g=Grid((9,)*3,(8.,)*3,'fixed');n=np.zeros(g.shape+(3,));n[...,2]=1;r,d=curvature_probe(n,g,Toy(),count=3)
        self.assertTrue(r['direction_qualified']);self.assertIsNotNone(d);self.assertLess(r['epsilon_minimum_relative_difference'],.1)
    def test_curve_regular_target_and_planar_writhe(self):
        t=np.linspace(0,2*np.pi,100,endpoint=False);ring=np.c_[np.cos(t),np.sin(t),np.zeros_like(t)];self.assertLess(abs(writhe(ring,128)),1e-12)
        g=Grid((25,)*3,(12.,)*3,'fixed');n=rational_field(g.points(),scale=2.,cutoff=4.5);n[g.fixed_mask()]=[0,0,1];r,loops=analyze(n,g);self.assertEqual(r['extraction']['components'],1);self.assertEqual(r['extraction']['ambiguous_tetrahedra'],0)
    def test_original_gates_remain_strict(self):
        p=load(ROOT/'PLAN.json')['registered_gates'];m=dict(relative_force_l2=1.1e-4,acceleration_max=.0009,hopf_integral=-21.,minimum_corner_cone=.8,unit_error=0.,tail_fraction=.0002,guard_fraction=.0004)
        self.assertFalse(gate_result(m,21,p)['all_readiness_gates']);m['relative_force_l2']=.00009;self.assertTrue(gate_result(m,21,p)['all_readiness_gates']);m['guard_fraction']=.0011;self.assertFalse(gate_result(m,21,p)['all_readiness_gates'])
    def test_source_artifact_and_budget(self):
        from integrity import checked_evidence
        s=load(ROOT/'SOURCE.json');self.assertEqual(sha(ROOT/'data/completed-evidence.zip'),s['evidence_sha256']);self.assertEqual(len(checked_evidence(ROOT/'data/completed-evidence.zip')),89)
        plan=load(ROOT/'PLAN.json');self.assertEqual(sum(a['cap'] for a in plan['arms']),2300);self.assertEqual(plan['maximum_motion_integration_calls'],300)
    def test_small_grid_pause_resume_no_refund(self):
        import worker
        plan=copy.deepcopy(load(ROOT/'PLAN.json'));plan['registered_gates']['charge_relative_error']=2.;plan['registered_gates']['force_limit']=1e-12;plan['registered_gates']['acceleration_limit']=1e-12
        original=worker.load
        def loader(p):return plan if Path(p)==ROOT/'PLAN.json' else original(p)
        parent=ComparisonEngine('cpu').state(self.n);parent['iteration']=335;arm={'id':'synthetic-resume-control','kind':'identity','optimizer':'lbfgs','cap':3}
        with tempfile.TemporaryDirectory() as td,patch.object(worker,'load',side_effect=loader),patch.object(worker,'reserves'):
            out=Path(td);out.mkdir(exist_ok=True);calls=[0]
            def stop():calls[0]+=1;return calls[0]>1
            with self.assertRaises(KeyboardInterrupt):worker.run_arm(out,out,parent,self.g,arm,'cpu',None,{},stop)
            folder=out/'arms'/arm['id'];self.assertEqual(len(load(folder/'attempt-ledger.json')),1)
            # A charged but uncommitted attempt is retained through recovery.
            ledger=load(folder/'attempt-ledger.json');ledger.append({'attempt':2,'charged_before_execution':True});save(folder/'attempt-ledger.json',ledger)
            r=worker.run_arm(out,out,parent,self.g,arm,'cpu',None,{},lambda:False);self.assertEqual(r['charged_attempts'],3);self.assertEqual(r['accepted_steps'],2)
            again=worker.run_arm(out,out,parent,self.g,arm,'cpu',None,{},lambda:False);self.assertEqual(again['charged_attempts'],3)
    def test_motion_gate_blocks_unadmitted_candidate(self):
        from motion_checks import run
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);(out/'handover').mkdir()
            for name in ['SOURCE.json','PLAN.json']:(out/'handover'/name).write_bytes((ROOT/name).read_bytes())
            records=[{'arm':{'id':k},'final':{'gates':{'all_readiness_gates':False}}} for k in ['mesh-129','mesh-161']]
            r=run(out,out,records,out/'absent-q2.npz','cpu',lambda:False,{})
            self.assertEqual(r['status'],'deferred_no_mesh_admitted_candidate');self.assertEqual(r['production_steps'],0);self.assertFalse((out/'motion-attempt-ledger.json').exists())
    def test_motion_budget_is_not_refunded(self):
        from motionlib import numeric
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);numeric.CONTEXT.update(out=out,stop=lambda:False);save(out/'motion-attempt-ledger.json',[{'attempt':i+1} for i in range(300)])
            with self.assertRaises(RuntimeError):numeric.charge()
            self.assertEqual(len(load(out/'motion-attempt-ledger.json')),300)
    def test_rest_screen_retains_and_reuses_results(self):
        from motionlib import numeric
        from motion_checks import rest_run
        p=copy.deepcopy(load(ROOT/'PLAN.json')['registered_gates']);p['motion']['duration']=.02
        with tempfile.TemporaryDirectory() as td,patch('motionlib.numeric.reserves'):
            out=Path(td);numeric.CONTEXT.update(out=out,stop=lambda:False);r=rest_run(self.n,self.g,1,out/'rest',p);count=len(load(out/'motion-attempt-ledger.json'))
            self.assertIn(r['status'],['screen_pass','screen_failed']);self.assertGreater(count,0);rest_run(self.n,self.g,1,out/'rest',p);self.assertEqual(count,len(load(out/'motion-attempt-ledger.json')))
    def test_validated_dependency_fit(self):
        from relationships import scalar_fits
        x=np.linspace(-.02,.02,5);r=scalar_fits(x,3+2*x+5*x*x)
        quad=next(m for m in r['models'] if m['model']=='quadratic');self.assertLess(quad['leave_one_out_relative_rmse'],1e-10);self.assertFalse(r['extrapolation_allowed']);self.assertEqual(scalar_fits(x[:3],x[:3])['status'],'insufficient_points_for_validated_curve')
    def test_same_field_model_operator_audit(self):
        from model_audit import audit
        with tempfile.TemporaryDirectory() as td:
            r=audit(self.n,self.g,Path(td),load(ROOT/'GATES.json'))
            self.assertAlmostEqual(r['decomposition']['e2']+r['decomposition']['e4'],r['d4']['energy'],places=11)
            self.assertEqual(r['source_array_before'],r['source_array_after']);self.assertEqual(r['optimizer_steps'],0)
    def test_motion_control_requires_both_dt_pairs(self):
        from motion_checks import control_pass
        rows=[{'candidate':'q2-control','result':{'status':'screen_pass'}} for _ in range(4)]
        rows.extend({'temporal_comparison':{'candidate':'q2-control','status':'screen_pass'}} for _ in range(2))
        self.assertTrue(control_pass(rows));rows[-1]['temporal_comparison']['status']='screen_failed';self.assertFalse(control_pass(rows));self.assertFalse(control_pass(rows[:3]))
    def test_supervised_limits(self):
        from handover import launch_argv
        from supervision import UNIT
        args=launch_argv(Path('/tmp/numerical'),Path('/tmp/output'));self.assertIn('--property=MemoryMax=8589934592',args);self.assertIn('--property=MemorySwapMax=1073741824',args);self.assertIn('--unit='+UNIT,args)

if __name__=='__main__':unittest.main()
