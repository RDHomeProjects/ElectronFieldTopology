"""Host controls; synthetic responses are never production scientific results."""
import copy,hashlib,importlib.util,json,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from common import ROOT,load,save,sha,canonical
from engine import Engine
from checkpoints import write_state,read_state
from evaluations import gate_result
from fitting import fit,curves,fitted_candidate,next_sample,select,response
from electron_field_topology.sf_time import Grid
from electron_field_topology.skyrme import rational_field
from diagnostics import audit,spectrum,curvature,masks
from reporting import seal,render
from integrity import checked_evidence

P=load(ROOT/'PLAN.json')

def samples(kind='quadratic'):
    out=[]
    for x in P['initial_log2_values']:
        score=10+(x-.3)**2 if kind=='quadratic' else 10
        out.append({'case':str(x),'log2_shift':x,'shift':2.**x,'all_readiness_gates':False,'response':{'eligible':True,'score':score,'median_force':score*1e-4,'median_acceleration':score*.001,'trajectory_score_mad':.01,'accepted_steps':30}})
    return out

def history(steps=30,q=21):
    return [{'accepted_step':i,'iteration':425+i,'metrics':{'energy':10-i*.001,'relative_force_l2':.001/(1+i*.02),'acceleration_max':.02/(1+i*.02),'hopf_integral':-q,'minimum_corner_cone':.9,'unit_error':1e-16,'tail_fraction':.0002,'guard_fraction':.0004},'gates':{'representation':True,'boundary_admitted':True,'all_readiness_gates':False,'strict_stationary':False}} for i in range(steps+1)]

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g=Grid((17,)*3,(12.,)*3,'fixed');cls.n=rational_field(cls.g.points(),scale=2.,cutoff=4.5);cls.n[cls.g.fixed_mask()]=[0,0,1]
    def test_default_engine_is_bitwise_original(self):
        spec=importlib.util.spec_from_file_location('reference_engine',ROOT/'validation/reference_engine.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
        a,b=Engine('cpu',.25),ref.Engine('cpu');sa,sb=a.state(self.n),b.state(self.n)
        for _ in range(5):
            self.assertEqual(a.step(sa,self.g)[0],b.step(sb,self.g)[0])
            for key in ['n','old_g','old_z','direction']:np.testing.assert_array_equal(sa[key],sb[key])
            self.assertEqual(sa['alpha'],sb['alpha'])
    def test_shift_changes_trajectory_not_action(self):
        ends=[];initial=Engine().value(self.n,self.g)[0]
        for shift in [.03125,.25,2.]:
            e=Engine('cpu',shift);s=e.state(self.n)
            for _ in range(4):self.assertTrue(e.step(s,self.g)[0])
            self.assertLess(e.value(s['n'],self.g)[0],initial);self.assertLess(np.max(abs(np.linalg.norm(s['n'],axis=-1)-1)),1e-12);ends.append(s['n'])
        self.assertFalse(np.array_equal(ends[0],ends[1]));self.assertFalse(np.array_equal(ends[1],ends[2]))
        for bad in [0,-1,np.nan,np.inf]:
            with self.assertRaises(ValueError):Engine('cpu',bad)
    def test_checkpoint_restores_full_conjugacy_and_identity(self):
        e=Engine('cpu',.125);s=e.state(self.n)
        for _ in range(3):e.step(s,self.g)
        identity={'shift':.125,'start':'restart'}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.npz';write_state(path,s,e,identity);r=read_state(path,e,identity);e.step(s,self.g);e.step(r,self.g)
            for key in ['n','old_g','old_z','direction']:np.testing.assert_array_equal(s[key],r[key])
            with self.assertRaises(RuntimeError):read_state(path,e,{'shift':.25})
            with path.open('ab') as f:f.write(b'corrupt')
            with self.assertRaises(RuntimeError):read_state(path,e,identity)
    def test_gate_thresholds_are_unchanged(self):
        m=history()[0]['metrics'];p=P['registered_gates'];self.assertFalse(gate_result(m,21,p)['strict_stationary']);self.assertTrue(gate_result(m,21,p)['boundary_admitted'])
        m.update(relative_force_l2=1e-4,acceleration_max=.001);self.assertTrue(gate_result(m,21,p)['all_readiness_gates']);m['guard_fraction']=.001001;self.assertFalse(gate_result(m,21,p)['all_readiness_gates'])
    def test_response_uses_matched_window(self):
        h=history();r=response(h,P);self.assertEqual(r['window_steps'],list(range(21,31)));self.assertTrue(r['eligible']);self.assertFalse(response(h[:-1],P)['eligible']);h[12]['gates']['boundary_admitted']=False;self.assertFalse(response(h,P)['eligible'])
    def test_fit_finds_supported_quadratic_optimum(self):
        c,f=fitted_candidate(samples(),P);self.assertIsNotNone(c);self.assertAlmostEqual(c['log2_shift'],.3,delta=.025);self.assertFalse(c['admission_inferred']);self.assertIn('quadratic',c['model_names'])
    def test_flat_and_insufficient_fits_do_not_invent_optimum(self):
        c,_=fitted_candidate(samples('flat'),P);self.assertIsNone(c);self.assertEqual(select(samples('flat'),P)['mode'],'no_supported_improvement');self.assertEqual(fit(samples()[:4],'score',P)['status'],'insufficient_matched_points')
    def test_adaptive_points_are_bounded_and_distinct(self):
        ss=samples()
        for _ in range(4):
            n=next_sample(ss,P);self.assertIsNotNone(n);xs=[s['log2_shift'] for s in ss];self.assertGreaterEqual(n['log2_shift'],min(xs)-.5);self.assertLessEqual(n['log2_shift'],max(xs)+.5);self.assertGreaterEqual(min(abs(n['log2_shift']-x) for x in xs),.125-1e-10)
            x=n['log2_shift'];r=copy.deepcopy(ss[0]);r.update(case=str(x),log2_shift=x,shift=n['shift']);v=10+(x-.3)**2;r['response'].update(score=v,median_force=v*1e-4,median_acceleration=v*.001);ss.append(r)
    def test_full_driver_bounded_and_restart_stable(self):
        import worker
        cached={}
        def fake(out,parent,g,cfg,limit,backend,stop,phase):
            old=cached.get(cfg['id'],{});steps=max(limit,old.get('accepted_steps',0));x=cfg.get('log2_shift',-2);value=10+(x-.3)**2;h=history(steps)
            for r in h:r['metrics'].update(relative_force_l2=value*1e-4,acceleration_max=value*.001)
            r={'case':cfg,'history':h,'response':{'eligible':True,'score':value,'median_force':value*1e-4,'median_acceleration':value*.001,'trajectory_score_mad':.01,'accepted_steps':30},'final_window':{},'accepted_steps':steps,'charged_attempts':steps,'final':h[-1]};cached[cfg['id']]=r;return r
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);result=worker.campaign(out,None,None,{}, {},lambda:None,fake);self.assertLessEqual(sum(r['charged_attempts'] for r in cached.values()),580);self.assertEqual(len(result['samples']),11);self.assertTrue(result['validation']['longer_comparison_allocated']);self.assertTrue(result['validation']['longer_comparison']['matched_accepted_horizon']);self.assertNotEqual(result['selection']['mode'],'no_supported_improvement')
            selection=load(out/'SELECTION.json');again=worker.campaign(out,None,None,{}, {},lambda:None,fake);self.assertEqual(selection,again['selection']);self.assertEqual(len(load(out/'ADAPTIVE-PROPOSALS.json')),4)
    def test_real_case_recovery_keeps_charges(self):
        import cases
        e=Engine('cpu');parent=e.state(self.n);parent.update(iteration=425,alpha=.0604)
        class KillAfterCharge(Exception):pass
        calls=[0]
        def fake_metrics(n,g,p):
            m=history()[0]['metrics'].copy();m['energy']=e.value(n,g)[0];return m
        cfg={'id':'small-cpu-recovery','shift':.25,'start':'restart','max_attempts':4}
        with tempfile.TemporaryDirectory() as td,patch.object(cases,'metrics',fake_metrics),patch.object(cases,'reserves',return_value={}):
            out=Path(td);save(out/'identity.json',{'synthetic_small_grid':True})
            original=cases.Engine.step
            def crash(engine,s,g):
                calls[0]+=1
                if calls[0]==2:raise KillAfterCharge('power-loss control')
                return original(engine,s,g)
            with patch.object(cases.Engine,'step',crash):
                with self.assertRaises(KillAfterCharge):cases.run_case(out,parent,self.g,cfg,4,{'selected':'cpu'},lambda:False,{})
            self.assertEqual(cases.charge_count(out),2)
            from worker import case_records
            partial=case_records(out)[0];self.assertEqual(partial['accepted_steps'],1);self.assertEqual(partial['charged_attempts'],2);self.assertIsNone(partial['endpoint'])
            r=cases.run_case(out,parent,self.g,cfg,4,{'selected':'cpu'},lambda:False,{})
            self.assertEqual(r['charged_attempts'],4);self.assertEqual(r['accepted_steps'],3);self.assertFalse(r['response']['eligible']);self.assertEqual(r['final']['iteration'],428)
    def test_residual_audit_is_read_only_and_partitions_grid(self):
        e=Engine();before=self.n.copy();r=audit(self.n,self.g,e,[.001,.0005]);np.testing.assert_array_equal(self.n,before);self.assertFalse(r['source_modified']);self.assertEqual(sum(v['voxel_count'] for v in r['regions']['force']['regions'].values()),17**3);self.assertAlmostEqual(sum(v['squared_residual_fraction'] for v in r['regions']['force']['regions'].values()),1);self.assertEqual(r['optimizer_attempts'],0)
        z=spectrum(np.zeros_like(self.n),self.g);self.assertIsNone(z['eigenvalue_weighted_quantiles']['0.5'])
    def test_local_negative_curvature_control(self):
        class Toy:
            xp=np
            def value(self,n,g):return -float(np.sum(n[...,:2]**2)),np.concatenate([-2*n[...,:2],np.zeros_like(n[...,:1])],axis=-1)
            def host(self,n):return n
        n=np.zeros_like(self.n);n[...,2]=1;v=np.zeros_like(n);v[...,0]=np.sin(self.g.points()[...,0]);r=curvature(n,self.g,Toy(),[('test',v)],[.001,.0005]);self.assertTrue(r['negative_direction_in_tested_subspace'])
    def test_seal_remains_valid_during_telemetry_appends(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);save(out/'record.json',{'synthetic':True});(out/'telemetry.jsonl').write_bytes(b'{"sample":0}\n');stop=threading.Event()
            def append():
                i=1
                while not stop.is_set():
                    with (out/'telemetry.jsonl').open('ab') as f:f.write(json.dumps({'sample':i}).encode()+b'\n')
                    i+=1;time.sleep(.001)
            t=threading.Thread(target=append);t.start()
            try:
                for _ in range(3):seal(out);self.assertGreater(len(checked_evidence(out/'evidence.zip')),0)
            finally:stop.set();t.join()
            self.assertTrue(load(out/'SEAL-RECEIPT.json')['telemetry_snapshot_bytes']>0)
    def test_browser_report_and_csv_render_measured_curves(self):
        import xml.etree.ElementTree as ET
        ss=samples();h=history();record={'status':'synthetic_report_control','charged_optimizer_attempts':210,'samples':ss,'fits':curves(ss,P),'cases':[{'case':{'id':'optimal-validation','log2_shift':.3,'shift':2**.3},'response':ss[0]['response'],'history':h}],'selection':{'mode':'synthetic'},'validation':{}}
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);render(out,record)
            for name in ['conditioning-response.svg','force-response.svg','acceleration-response.svg']:ET.parse(out/name)
            for name in ['sampling.csv','measurements.csv']:self.assertNotIn(b'\r',(out/name).read_bytes())
            self.assertIn('red ring',(out/'force-response.svg').read_text());self.assertIn('not motion simulations',(out/'REPORT.html').read_text())

    def test_merge_check_uses_live_state_and_published_bytes(self):
        import integrity
        from types import SimpleNamespace
        spec=load(ROOT/'SOURCE.json');pr={'number':1,'url':'https://github.com/RDHomeProjects/ElectronFieldTopology/pull/1','state':'MERGED','headRefOid':'test-head','mergeCommit':{'oid':'test-merge'},'baseRefName':'main'}
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo';pub=Path(td)/'pub';(repo/'.git').mkdir(parents=True);(pub/'.git').mkdir(parents=True);source=repo/spec['relative_run'];source.mkdir(parents=True)
            for n in ['record.json','FIELD-MANIFEST.json','arms/domain-pad-16/endpoint.seal.json','review/ASSESSMENT.json','evidence.zip']:
                f=source/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b'fixture-'+n.encode())
            snapshot=sha(source/'evidence.zip');save(pub/spec['source_publication_marker'],{'phase':'published','kind':'results','snapshot_sha256':snapshot,'commit':'test-head','pr':{'url':pr['url'],'mergeCommit':None}})
            def command(where,argv,json_result=False):
                if argv[:3]==['git','remote','get-url']:return 'https://github.com/RDHomeProjects/ElectronFieldTopology.git'
                if argv[:3]==['gh','pr','view']:return pr
                return ''
            prefix='origin/main:'+spec['source_document_root']+'/results/'+spec['run_id']+'/'+snapshot[:8]+'/'
            def show(argv,**kwargs):return SimpleNamespace(returncode=0,stdout=(source/argv[-1].removeprefix(prefix)).read_bytes())
            with patch.object(integrity,'authenticate',return_value={'evidence_sha256':snapshot}),patch.object(integrity,'local_command',command),patch.object(integrity.subprocess,'run',show):
                r=integrity.check_merge(repo,pub);self.assertEqual(r['status'],'merged_source_verified_on_workstation')
                with patch.object(integrity.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'wrong remote bytes')):
                    with self.assertRaises(RuntimeError):integrity.check_merge(repo,pub)
                pr['state']='OPEN'
                with self.assertRaises(RuntimeError):integrity.check_merge(repo,pub)

    def test_resource_and_budget_configuration(self):
        from handover import launch_argv
        command=launch_argv(Path('/tmp/test-repo'),Path('/tmp/test-output'));self.assertIn('--property=MemoryHigh=7516192768',command);self.assertIn('--property=MemoryMax=8589934592',command);self.assertIn('--property=MemorySwapMax=1073741824',command);self.assertEqual(P['maximum_new_optimizer_attempts'],40+7*30+4*30+120+90);self.assertEqual(P['physical_time_steps'],0)

if __name__=='__main__':unittest.main(verbosity=2)
