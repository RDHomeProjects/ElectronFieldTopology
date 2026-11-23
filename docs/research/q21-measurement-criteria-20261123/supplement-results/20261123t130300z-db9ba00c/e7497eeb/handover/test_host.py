"""Host checks; small numerical fixtures are not zbook production measurements."""
import ast,json,os,sys,tempfile,unittest,zipfile,hashlib,subprocess,shutil
from pathlib import Path
from unittest.mock import patch
import numpy as np
from criteria_common import ROOT,load,save,sha,verify_zip
sys.path.insert(0,str(ROOT/'legacy'))
from electron_field_topology.sf_time import Grid
from electron_field_topology.skyrme import rational_field
from engine import Engine
from evaluations import derivative_check,metrics
import cases
from field_audit import distribution,measure
from criteria import compare_case,trailing_true

class Checks(unittest.TestCase):
 def field(self,nodes=17):
  grid=Grid((nodes,)*3,(8.,)*3,'fixed');n=rational_field(grid.points(),kind='axial',alpha=1,beta=1,scale=1.3,cutoff=3.5);n[grid.fixed_mask()]=[0.,0.,1.];return n,grid
 def test_compact_author_energy_metrics(self):
  with zipfile.ZipFile(ROOT/'data/completed-evidence.zip') as z:record=json.loads(z.read('record.json'))
  expected={'mesh-145':1.8990521739116532e-7,'mesh-153':2.0807880279629185e-7,'mesh-161':1.6567857320706853e-7}
  for c in record['cases']:
   result,changes=compare_case(c);self.assertEqual(len(changes),80)
   if c['case']['id'] in expected:
    self.assertEqual(result['final10_updates_below_1e_minus9'],0);self.assertAlmostEqual(result['final10_relative_energy_change_median']/expected[c['case']['id']],1.,places=10)
  self.assertEqual(trailing_true([True,False,True,True]),2)
 def test_actual_cpu_gradient_and_step(self):
  n,g=self.field();d=derivative_check(n,g,{'epsilons':[.001,.0003,.0001],'rtol':.002,'atol':1e-7});self.assertTrue(d['passed']);e=Engine('cpu',.25);state=e.state(n);state.update(iteration=599,alpha=.08);before=e.value(state['n'],g)[0];accepted,row=e.step(state,g);self.assertTrue(accepted);self.assertLessEqual(row['energy'],before);self.assertEqual(state['iteration'],600);self.assertIsNone(state['old_g']);self.assertEqual(state['alpha'],1.)
  audit=e.audit(state['n'],g);self.assertTrue(audit['passed']);self.assertFalse(audit['independent_implementation']);self.assertIn('same CPU',audit['reference']);self.assertLess(np.max(abs(np.linalg.norm(state['n'],axis=-1)-1)),1e-12)
 def test_native_read_only_measurements_and_surfaces(self):
  n,g=self.field();before=n.copy()
  with tempfile.TemporaryDirectory() as td:
   result=measure(n,g,Path(td),'host-fixture',draw=True,q=1);self.assertTrue(np.array_equal(n,before));self.assertTrue((Path(td)/'author-surfaces.png').is_file());self.assertEqual(len(result['display_surfaces']),3)
   self.assertAlmostEqual(sum(v['squared_residual_fraction'] for v in result['acceleration']['regions'].values()),1.,places=10);self.assertAlmostEqual(result['acceleration']['component_rms']*np.sqrt(3),result['acceleration']['vector_rms'],places=12)
   self.assertAlmostEqual(result['energy_components']['sum'],result['metrics']['energy'],places=10)
 def test_checkpoint_resume_charges_and_native_phase(self):
  n,g=self.field();parent={'n':n,'alpha':.08,'iteration':545};backend={'selected':'cpu','device':None};cfg={'id':'fixture','nodes':17,'start':'restart','shift':.25,'max_attempts':80}
  # Synthetic Q metadata allows control-flow exercise; field arithmetic remains real.
  def fixture_metrics(a,grid,p):
   m=metrics(a,grid,p);m.update(hopf_integral=21.,tail_fraction=0.,guard_fraction=0.);return m
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);save(out/'identity.json',{'fixture':'no_scientific_result'});phase={}
   with patch.object(cases,'metrics',fixture_metrics),patch.object(cases,'reserves',lambda *_:None):
    first=cases.run_case(out,parent,g,cfg,2,backend,lambda:False,phase);second=cases.run_case(out,parent,g,cfg,3,backend,lambda:False,phase)
   self.assertEqual(first['charged_attempts'],2);self.assertEqual(second['charged_attempts'],3);self.assertEqual(second['final']['iteration'],548);self.assertTrue((out/'cases/fixture/endpoint.seal.json').is_file());self.assertTrue(np.array_equal(n,parent['n']))
 def test_cpu_geometry_not_gpu_admitted(self):
  from resources import geometry_budget
  for n in [177,193]:
   result=geometry_budget(n,'cpu',available=12);self.assertTrue(result['passed']);self.assertNotIn('estimated_gpu_gib',result)
  self.assertFalse(geometry_budget(193,'cpu',available=10)['passed'])
 def test_hash_failure_stops(self):
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'bad.zip'
   with zipfile.ZipFile(path,'w') as z:z.writestr('x','modified');z.writestr('SHA256SUMS','0'*64+'  x\n')
   with self.assertRaises(RuntimeError):verify_zip(path)
 def test_plan_limits_and_unchanged_optimizer(self):
  p=load(ROOT/'PLAN.json');self.assertEqual(p['cpu_grids'],[177,193]);self.assertEqual(p['maximum_new_optimizer_attempts'],160);self.assertEqual(p['attempts_per_grid'],80);self.assertEqual(p['physical_time_steps'],0)
  original=zipfile.ZipFile(ROOT/'data/completed-evidence.zip').read('handover/engine.py').decode();a=ast.parse(original);b=ast.parse((ROOT/'legacy/engine.py').read_text())
  def method(tree,name):return next(f for item in tree.body if isinstance(item,ast.ClassDef) and item.name=='Engine' for f in item.body if isinstance(f,ast.FunctionDef) and f.name==name)
  for name in ['step','value','state','cone']:self.assertEqual(ast.dump(method(a,name)),ast.dump(method(b,name)))
if __name__=='__main__':unittest.main(verbosity=2)
