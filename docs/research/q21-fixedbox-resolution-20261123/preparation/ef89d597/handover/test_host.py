"""Scientific/integrity/controller tests in temporary fixtures, not production Q21."""
import hashlib,json,os,shutil,subprocess,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import common,relationships,resources,bulk,publication,reporting,cases,measurements
from common import ROOT,load,save,sha,canonical
from electron_field_topology.sf_time import Grid
from electron_field_topology.sf_readmission import static_value_gradient
from evaluations import array_sha,derivative_check,gate_result
from engine import Engine,dst_fft
from scipy.fft import dstn

def fixture_field(nodes=17,length=8.):
    g=Grid((nodes,)*3,(length,)*3,'fixed');xyz=g.points();v=.12*np.exp(-np.sum(xyz*xyz,axis=-1)/3);n=np.zeros(g.shape+(3,));n[...,0]=v*np.cos(xyz[...,2]);n[...,1]=v*np.sin(xyz[...,2]);n[...,2]=np.sqrt(1-np.sum(n[...,:2]**2,axis=-1));n[g.fixed_mask()]=[0,0,1];return n,g

class ScientificTests(unittest.TestCase):
    def test_action_directional_derivative(self):
        n,g=fixture_field();before=array_sha(n);r=derivative_check(n,g,{'epsilons':[.001,.0003,.0001],'rtol':.002,'atol':1e-7});self.assertTrue(r['passed']);self.assertEqual(before,array_sha(n))
    def test_cpu_energy_descent_and_phase(self):
        n,g=fixture_field();e=Engine('cpu',.25);s=e.state(n);s.update(iteration=599,alpha=.078);old=static_value_gradient(n,g)[0];accepted,result=e.step(s,g)
        self.assertTrue(accepted);self.assertLessEqual(result['energy'],old);self.assertEqual(s['iteration'],600);self.assertIsNone(s['old_g']);self.assertEqual(s['alpha'],1.)
    def test_fft_dirichlet_adapter_matches_scipy(self):
        x=np.random.default_rng(42).normal(size=(7,8,9,3));self.assertTrue(np.allclose(dst_fft(x,np),dstn(x,axes=(0,1,2),type=1,norm='ortho'),rtol=1e-12,atol=1e-12))
    def test_resampling_fixed_box_preserves_source(self):
        n,g=fixture_field();before=array_sha(n);q,gg,info=cases.resample(n,g,25)
        self.assertEqual(gg.lengths,g.lengths);self.assertEqual(before,array_sha(n));self.assertTrue(np.allclose(np.linalg.norm(q,axis=-1),1));self.assertTrue(np.all(q[gg.fixed_mask()]==[0,0,1]));self.assertEqual(info['method'],'cubic_target_grid_then_unit_normalization_and_held_layers')
        identity,_,_=cases.resample(n,g,17);self.assertTrue(np.array_equal(identity,n));self.assertIsNot(identity,n)
    def test_regions_spectra_and_readonly(self):
        n,g=fixture_field();before=array_sha(n);r=measurements.localized(n,g)
        for key in ['force','acceleration']:
            self.assertAlmostEqual(sum(x['squared_residual_fraction'] for x in r['regions'][key]['regions'].values()),1,places=10)
            self.assertAlmostEqual(sum(r['regions'][key]['spectrum']['power_fractions']),1,places=10)
        self.assertEqual(before,array_sha(n));self.assertEqual(r['hessian_directions'],0)
    def test_gates_preserved_and_not_granted_by_fit(self):
        p=load(ROOT/'PLAN.json')['registered_gates'];m={'relative_force_l2':1e-5,'acceleration_max':1e-4,'hopf_integral':-21,'minimum_corner_cone':.8,'unit_error':1e-16,'tail_fraction':1e-4,'guard_fraction':2e-4}
        self.assertTrue(gate_result(m,21,p)['all_readiness_gates']);m['acceleration_max']=.011;self.assertFalse(gate_result(m,21,p)['strict_stationary'])
    def test_geometry_defers_without_backend_fallback(self):
        r=resources.geometry_budget(193,'cuda',available=11,free_gpu=7.5);self.assertFalse(r['passed']);self.assertEqual(r['backend'],'cuda')
        self.assertTrue(resources.geometry_budget(129,'cpu',available=11)['passed']);self.assertFalse(resources.geometry_budget(193,'cpu',available=7)['passed'])

class RelationshipTests(unittest.TestCase):
    def setUp(self):self.p=load(ROOT/'PLAN.json')
    def test_real_linear_relation_qualifies(self):
        pts=[{'nodes':n,'spacing':30.72/(n-1),'joint':2+10*30.72/(n-1)} for n in [129,145,161,177,193]];fit=relationships.fit_curve(pts,'joint',self.p)
        self.assertEqual(fit['status'],'validated_model_available');self.assertTrue(next(x for x in fit['models'] if x['model']=='linear')['eligible']);self.assertFalse(fit['supported_optimum'])
    def test_irregular_curve_and_insufficient_points(self):
        pts=[{'spacing':float(i),'joint':v} for i,v in enumerate([3,40,2,50,1])];self.assertFalse(any(x['eligible'] for x in relationships.fit_curve(pts,'joint',self.p)['models']));self.assertEqual(relationships.fit_curve(pts[:4],'joint',self.p)['status'],'insufficient_distinct_matched_points')
    def test_constant_response_has_no_predictive_skill(self):
        points=[{'spacing':float(i),'joint':10.} for i in range(5)]
        self.assertFalse(any(m['eligible'] for m in relationships.fit_curve(points,'joint',self.p)['models']))
    def test_component_worsening_blocks_selection(self):
        b={'eligible':True,'force':1.,'acceleration':1.,'joint':10};c={'eligible':True,'force':1.2,'acceleration':.7,'joint':8};self.assertFalse(relationships.better(c,b,self.p))
    def test_adaptive_point_is_new_and_bounded(self):
        pts=[{'nodes':n,'spacing':30.72/(n-1),'joint':y} for n,y in [(129,10),(145,9),(161,4),(177,5)]];n=relationships.acquire(pts,[129,145,161,177],self.p,[193]);self.assertIn(n,[137,153,169,185]);self.assertNotEqual(n,193)
    def test_matched_accepted_windows(self):
        h=[{'accepted_step':i,'metrics':{'relative_force_l2':.001,'acceleration_max':.01},'gates':{'representation':True,'boundary_admitted':True}} for i in range(80)]
        self.assertFalse(relationships.window(h,80)['eligible']);h.append(dict(h[-1],accepted_step=80));self.assertTrue(relationships.window(h,80)['eligible'])
    def test_budget_and_restart_design(self):
        self.assertEqual(self.p['maximum_new_optimizer_attempts'],5*80+80+2*80+2*40);self.assertEqual(600-load(ROOT/'SOURCE.json')['source_iteration'],55)

class IntegrityTests(unittest.TestCase):
    def test_legacy_archive_pin_and_declarations(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);field_hash='a'*64;doc={'field_sha256':field_hash,'nodes':17,'length':8.};archive=run/'evidence.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('rest/result.json',json.dumps(doc))
            bulk.CACHE.clear();digest,docs=bulk.metadata(run,sha(archive));self.assertEqual(bulk.declared_hash(docs,field_hash,'rest/latest.npz'),['rest/result.json'])
            with self.assertRaises(RuntimeError):bulk.metadata(run,'b'*64)
            with self.assertRaises(RuntimeError):bulk.declared_hash(docs,'c'*64,'rest/latest.npz')
    def test_unknown_native_geometry_is_deferred(self):
        with self.assertRaises(RuntimeError):bulk.geometry_from({}, {'unrelated.json':{'nodes':17,'length':8.}},'rest/latest.npz',(17,17,17,3))
        self.assertEqual(bulk.geometry_from({'h':np.array(.5)}, {},'rest/latest.npz',(17,17,17,3))[0],(8.,)*3)
    def test_compact_sealing_excludes_live_streams_keeps_nested_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);(out/'handover').mkdir();(out/'handover/SHA256SUMS').write_text('fixture\n');(out/'record.json').write_text('{}\n');(out/'telemetry.jsonl').write_text('live');(out/'heartbeat.json').write_text('live');(out/'field.npz').write_bytes(b'full field fixture');reporting.seal(out)
            with zipfile.ZipFile(out/'evidence.zip') as z:
                self.assertIn('handover/SHA256SUMS',z.namelist());self.assertNotIn('field.npz',z.namelist());self.assertNotIn('telemetry.jsonl',z.namelist());self.assertNotIn('heartbeat.json',z.namelist());self.assertIsNone(z.testzip())
                for line in z.read('SHA256SUMS').decode().splitlines():
                    h,n=line.split('  ',1);self.assertEqual(hashlib.sha256(z.read(n)).hexdigest(),h)
    def test_parameter_plot_is_valid_svg(self):
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);save(out/'CURVE-FITS.json',{'responses':[{'nodes':n,'spacing':30.72/(n-1),'force':.001,'acceleration':.01,'joint':10.} for n in [129,145,161]]});reporting.parameter_plot(out);ET.parse(out/'parameter-response.svg')
    def test_known_original_screen_not_silently_replaced(self):
        c=load(ROOT/'CATALOGUE.json');self.assertEqual(set(x['q_label'] for x in c['candidates']),set(range(2,33)));secondary=[x for x in c['candidates'] if '20261114t120027z' in x['relative_home_path']];self.assertTrue(secondary);self.assertTrue(all(x['role']=='historical_secondary_run_not_the_original_094318_screen_source' for x in secondary))

class FakeEngine:
    """Controller-only fixture: not a scientific action or production field."""
    fail=False
    def __init__(self,kind,shift):self.kind=kind;self.xp=np
    def state(self,n):return {'n':n.copy(),'old_g':None,'old_z':None,'direction':None,'alpha':.1,'iteration':545}
    def host(self,n):return n.copy()
    def sync(self):pass
    def audit(self,n,g):return {'passed':True,'fixture_only':True}
    def step(self,s,g):
        if self.fail:raise KeyboardInterrupt('fixture interrupted attempt')
        s['n'][4,4,4,0]+=.01;s['iteration']+=1;return True,{'objective_calls':2}

def fake_metrics(n,g,p):
    v=float(n[4,4,4,0]);return {'energy':1-v,'relative_force_l2':.001*(1-v),'acceleration_max':.01*(1-v),'hopf_integral':-21.,'minimum_corner_cone':1.,'unit_error':0.,'tail_fraction':0.,'guard_fraction':0.}

class ControllerTests(unittest.TestCase):
    def test_interrupt_does_not_refund_charge(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);save(out/'identity.json',{'fixture':True});n=np.zeros((9,9,9,3));n[...,2]=1;parent={'n':n,'alpha':.1,'iteration':545};cfg={'id':'fixture','nodes':9,'start':'restart','shift':.25,'max_attempts':120};backend={'selected':'cpu','device':None};g=Grid((9,)*3,(30.72,)*3,'fixed')
            with patch.object(cases,'Engine',FakeEngine),patch.object(cases,'metrics',fake_metrics),patch.object(cases,'geometry_budget',return_value={'passed':True}),patch.object(cases,'reserves',return_value={}):
                FakeEngine.fail=True
                with self.assertRaises(KeyboardInterrupt):cases.run_case(out,parent,g,cfg,2,backend,lambda:False,{})
                self.assertEqual(cases.charge_count(out),1);FakeEngine.fail=False;r=cases.run_case(out,parent,g,cfg,2,backend,lambda:False,{})
                self.assertEqual(r['charged_attempts'],2);self.assertEqual(r['accepted_steps'],1);self.assertTrue(np.array_equal(n,parent['n']))

class CampaignScheduleTests(unittest.TestCase):
    def test_full_scheduler_ceiling_and_resume(self):
        import worker
        p=load(ROOT/'PLAN.json');data={};charged=0
        def trial(nodes,start='restart',horizon=80):
            nonlocal charged
            name='exact-control' if start=='exact' else 'mesh-%03d'%nodes
            old=data.get(name,{}).get('accepted_steps',0);charged+=max(0,horizon-old);horizon=max(old,horizon)
            ratio=129/nodes
            hist=[{'accepted_step':i,'iteration':545+i,'metrics':{'relative_force_l2':.001*ratio,'acceleration_max':.01*ratio},'gates':{'representation':True,'boundary_admitted':True}} for i in range(horizon+1)]
            record={'case':{'id':name,'nodes':nodes,'start':start},'accepted_steps':horizon,'spacing':[30.72/(nodes-1)]*3,'history':hist};data[name]=record;return record
        with tempfile.TemporaryDirectory() as td,patch.object(worker,'records',lambda out:list(data.values())):
            out=Path(td);selection=worker.mesh_campaign(out,p,trial);self.assertEqual(selection['mode'],'persistent_measured_value_for_longer_matched_confirmation');self.assertLessEqual(charged,720);self.assertEqual(len([r for r in data.values() if r['case']['start']!='exact']),7);before=charged;worker.mesh_campaign(out,p,trial);self.assertEqual(charged,before)
    def test_no_benefit_has_no_longer_confirmation(self):
        import worker
        data={};calls=[]
        def trial(nodes,start='restart',horizon=80):
            calls.append(horizon);name='exact-control' if start=='exact' else 'mesh-%03d'%nodes
            hist=[{'accepted_step':i,'metrics':{'relative_force_l2':.001,'acceleration_max':.01},'gates':{'representation':True,'boundary_admitted':True}} for i in range(horizon+1)]
            data[name]={'case':{'id':name,'nodes':nodes,'start':start},'spacing':[30.72/(nodes-1)]*3,'history':hist};return data[name]
        with tempfile.TemporaryDirectory() as td,patch.object(worker,'records',lambda out:list(data.values())):
            selection=worker.mesh_campaign(Path(td),load(ROOT/'PLAN.json'),trial);self.assertEqual(selection['mode'],'no_persistent_measured_joint_benefit');self.assertNotIn(120,calls)

class PublicationTests(unittest.TestCase):
    def test_local_additive_plan_and_byte_verification(self):
        def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL).decode().strip()
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);source=base/'source';source.mkdir();git(source,'init','-b','main');git(source,'config','user.name','Fixture');git(source,'config','user.email','fixture@example.invalid');original=b'# Existing project\n\nKeep this introduction.\n';(source/'README.md').write_bytes(original);(source/'.gitignore').write_text('*.log\n');(source/'old-chart.svg').write_text('<svg/>\n');git(source,'add','.');git(source,'commit','-m','fixture');remote=base/'remote.git';subprocess.run(['git','clone','--bare',str(source),str(remote)],check=True,capture_output=True);target=base/'publication'
            with patch.object(publication,'REMOTE',str(remote)),patch.object(publication,'authenticate',return_value={'fixture':True}),patch.object(publication,'merged_source',return_value={'fixture':True}):
                state=publication.prepare(source,target,source);self.assertEqual(state['phase'],'applied');self.assertEqual(publication.prepare(source,target,source)['branch'],state['branch']);self.assertTrue((target/'README.md').read_bytes().startswith(original));self.assertEqual((target/'old-chart.svg').read_bytes(),b'<svg/>\n');git(target,'config','user.name','Fixture');git(target,'config','user.email','fixture@example.invalid');git(target,'commit','-m','registered plan fixture');self.assertEqual(publication.verify_bytes(target,'HEAD',state['immutable_files']),len(state['immutable_files']))
                wrong=dict(state['immutable_files']);wrong[next(iter(wrong))]='0'*64
                with self.assertRaises(RuntimeError):publication.verify_bytes(target,'HEAD',wrong)
                (target/'unrelated.txt').write_text('hold');git(target,'add','unrelated.txt')
                with self.assertRaises(RuntimeError):publication.checks(target,state)
                git(target,'restore','--staged','unrelated.txt');(target/'unrelated.txt').unlink()
                git(target,'push','origin','HEAD:main');state['phase']='merged';save(publication.marker(target),state)
                out=base/'completed';out.mkdir();save(out/'status.json',{'status':'complete_pending_review'});save(out/'identity.json',{'run_id':'fixture-run'});(out/'runner.log').write_text('ignored raw fixture log\n');(out/'REPORT.html').write_text('<html>fixture</html>\n');save(out/'record.json',{'status':'complete_pending_review'});reporting.seal(out)
                with patch('supervision.service_active',return_value=False):result_state=publication.prepare(source,target,source,out)
                paths=git(target,'diff','--cached','--name-only').splitlines();self.assertTrue(any(x.endswith('/runner.log') for x in paths));git(target,'commit','-m','raw completed fixture');self.assertEqual(publication.verify_bytes(target,'HEAD',result_state['immutable_files']),len(result_state['immutable_files']));self.assertEqual((target/'old-chart.svg').read_bytes(),b'<svg/>\n');git(target,'push','origin','HEAD:main');git(target,'fetch','origin','refs/heads/main:refs/remotes/origin/main');self.assertEqual(publication.verify_bytes(target,'origin/main',result_state['immutable_files']),len(result_state['immutable_files']))

if __name__=='__main__':unittest.main(verbosity=2)
