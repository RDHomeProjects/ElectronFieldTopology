"""Host controls, causal history replay and real local-Git publication fixture."""
import argparse,ast,io,json,os,re,shutil,subprocess,sys,tempfile,types,zipfile
from pathlib import Path
import numpy as np
from common import ROOT,load,save,sha,stamp,canonical
parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--kernel-only',action='store_true');a=parser.parse_args();sys.path.insert(0,str(a.repo/'src'))
from electron_field_topology import sf_time,skyrme,sf_dynamics
if a.kernel_only:
 # Execute literal retained operator functions without the unavailable unrelated
 # driver imports. Production preflight imports the complete installed modules.
 source=a.repo/'src/electron_field_topology/sf_readmission.py';tree=ast.parse(source.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['static_value_gradient','cone','stationarity','admitted']]
 module=types.ModuleType('electron_field_topology.sf_readmission');module.__dict__.update(np=np,K=skyrme.K,NORTH=skyrme.NORTH,topology=skyrme.diagnostics,currents=sf_dynamics.currents,**{n:getattr(sf_time,n) for n in ['Grid','gradients','sigma_terms','derivative','acceleration','densities']});exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),module.__dict__);sys.modules[module.__name__]=module
from science.instruments import qualify
from science.numeric import Branch,metrics,representation,stationary,qualify_geometry
from science.catalogue import catalogue,field
from science.fits import decide,models,predict
from science.topology import anisotropic_hopf
from science.motion import linear_reference
import publication as pub
checks=[];p=load(ROOT/'PLAN.json');cat=catalogue(p)
assert len(cat)==34 and {s['q'] for s in cat}==set(range(17,33))
assert sum(s['kind']=='cable' for s in cat)==1
checks.append('All Q17-Q32 labels covered by 34 frozen rational starts including the Q22 cable and comparator families')
instrument=qualify();checks.append('Actual retained numerical kernels pass independent array gradient, directional derivative, native-C cell energy, DST, geodesic order and bitwise optimizer-resume controls')
def rows(xs):return [{'iteration':int(x),'relative_force_l2':.01*np.exp(-.03*x)+.0002,'acceleration_max':.02*np.exp(-.02*x)+.002,'energy':5.+.3*np.exp(-.01*x)} for x in xs]
history=rows(np.arange(0,80,5));choice=decide(history,p,300)
assert 0<choice['steps']<=p['batch_limits'][1] and not choice['gate_pass'] and not choice.get('predicted_pass',False)
assert choice['steps']>10;json.dumps(choice,allow_nan=False)
fits=models(history,'relative_force_l2',p);exp=next(x for x in fits['accepted'] if x['model']=='exponential_floor');floor=exp['normal']*exp['coefficients'][0];assert abs(floor-.0002)<1e-6
assert decide(history,p,3)['steps']<=3
flat=[{'iteration':600+i*5,'relative_force_l2':.002,'acceleration_max':.02,'energy':5.} for i in range(16)];assert decide(flat,p,100,2)['action']=='stop'
turn=rows(np.arange(0,80,5));turn[-4]['relative_force_l2']=.004;turn[-3]['relative_force_l2']=.003;turn[-2]['relative_force_l2']=.0035;turn[-1]['relative_force_l2']=.0032
decision=decide(turn,p,100);assert decision['observe']==p['observe_limits'][0] and decision['steps']<=10
assert decide(history[:3],p,100)['steps']<=10
checks.append('Nonzero exponential floors recovered; scarce data, slope turns and remaining budgets shorten batches; repeated measured plateaus defer without a predicted pass')
replays={}
for q in ['q8','q10']:
 h=load(ROOT/'validation'/f'{q}-history.json');decisions=[];errors=[]
 for index in range(15,len(h)-1,12):
  prefix=h[:index+1];d=decide(prefix,p,300);assert not d['gate_pass'];assert d['steps']<=p['batch_limits'][1]
  # Evaluate an actually later observation, never used in the fitted prefix.
  target=next((x for x in h[index+1:] if x['iteration']>=h[index]['iteration']+max(d['steps'],1)),None)
  if target:
   accepted=d['models']['relative_force_l2']['accepted']
   if accepted:errors.append(abs(float(predict(accepted[0],target['iteration']))-target['relative_force_l2'])/target['relative_force_l2'])
  decisions.append({'iteration':h[index]['iteration'],'action':d['action'],'steps':d['steps'],'observation_interval':d['observe'],'reason':d['reason']})
 replays[q]={'observations':len(h),'decision_points':len(decisions),'decisions':decisions,'median_next_batch_force_prediction_relative_error':float(np.median(errors)) if errors else None,'scope':'Retrospective/correlated old optimizer history; no independent Q17-Q32 validation and no counterfactual trajectory claim'}
save(ROOT/'validation/BACKTEST.json',{'recorded_at':stamp(),'histories':replays})
checks.append('Causal replays use only prefixes of retained Q8/Q10 histories; future errors and every simulated allocation are reported without promoting forecast crossings')

with tempfile.TemporaryDirectory() as td:
 root=Path(td);pp=dict(p);pp.update(host_reserve_gib=0,disk_reserve_gib=0,force_limit=1e-20,acceleration_limit=1e-20)
 g=sf_time.Grid((41,)*3,(12.,)*3,'fixed');s=dict(id='host-q1',q=1,kind='axial',alpha=1,beta=1,scale=1.4,cutoff=4.5,amplitude=1.);n=field(g,s);m=metrics(n,g,pp);assert representation(m,1,pp)
 measured=qualify_geometry(sf_time.Grid((49,)*3,(23.04,)*3,'fixed'),pp,root/'measured-cpu-benchmark','cpu');assert measured['selected_backend']=='cpu' and measured['results']['cpu']['assumed_observations_per_50_steps']==25
 assert qualify_geometry(sf_time.Grid((49,)*3,(23.04,)*3,'fixed'),pp,root/'measured-cpu-benchmark','cpu')==measured
 checks.append('Actual CPU geometry benchmark warms the optimizer, measures audits/checkpoint costs at dense cadence, and reuses its matching receipt')
 receipt={'selected_backend':'cpu'};b=Branch(root/'a',g,s,pp,receipt,{'host':1},n);b.batch(2,1,8);before=b.engine.host(b.s['n']);iteration=b.s['iteration'];del b
 b=Branch(root/'a',g,s,pp,receipt,{'host':1},n);assert b.s['iteration']==iteration and np.array_equal(before,b.engine.host(b.s['n']));b.batch(2,1,8)
 c=Branch(root/'b',g,s,pp,receipt,{'host':1},n);c.batch(4,1,8);assert np.array_equal(b.engine.host(b.s['n']),c.engine.host(c.s['n']))
 assert b.attempts==4 and b.s['iteration']==4 and b.history[-1]['energy']<b.history[0]['energy']
 b.batch(20,2,8);assert b.attempts==8 and b.s['iteration']==8
 # An uncommitted inactive slot does not change the latest committed pointer.
 pointer=load(root/'a/latest.json');inactive=root/'a'/f"state-{1-pointer['slot']}.npz";inactive.write_bytes(b'incomplete inactive write')
 d=Branch(root/'a',g,s,pp,receipt,{'host':1},n);assert d.s['iteration']==8
 assert np.isclose(anisotropic_hopf(n,g),skyrme.diagnostics(n,g.spacing[0])['hopf_integral'],rtol=1e-13,atol=1e-13)
 point=np.array([[[[.15,.23,-.31]]]]);reference=linear_reference(n,g,point);assert reference.shape==point.shape and np.isclose(np.linalg.norm(reference),1)
 checks.append('Real CPU field relaxation preserves conjugacy across adaptive batch boundaries, resumes bitwise, enforces attempted-step budget and survives an incomplete inactive checkpoint slot')
 checks.append('Per-axis Hopf diagnostic equals the established isotropic operator on equal spacings; trilinear reference is finite and normalized')

 # Exercise the actual funnel/report/seal/resume orchestration on a small real
 # numerical branch. Only external workstation controls/device benchmarking are
 # fixtures; branch metrics and optimizer steps are the retained actual kernels.
 import worker
 import science.catalogue as catmod,science.native as native,science.numeric as numeric
 import science.instruments as instruments
 small_root=root/'small-package';shutil.copytree(ROOT,small_root,ignore=shutil.ignore_patterns('__pycache__'))
 small_plan=dict(pp);small_plan.update(q_values=[1],grids=[41],length=12.,bootstrap_steps=2,branch_attempt_budget=2,maximum_mesh_branches=0,maximum_domain_branches=0,maximum_motion_branches=0)
 save(small_root/'PLAN.json',small_plan)
 fixture_repo=root/'numerical-repo';fixture_repo.mkdir();(fixture_repo/'src').symlink_to((a.repo/'src').resolve(),target_is_directory=True)
 subprocess.run(['git','init','-q',str(fixture_repo)],check=True);subprocess.run(['git','-C',str(fixture_repo),'config','user.name','Offline Fixture'],check=True);subprocess.run(['git','-C',str(fixture_repo),'config','user.email','fixture@example.invalid'],check=True);(fixture_repo/'README.md').write_text('# Fixture\n');subprocess.run(['git','-C',str(fixture_repo),'add','README.md'],check=True);subprocess.run(['git','-C',str(fixture_repo),'commit','-qm','fixture numerical source'],check=True)
 actual=(worker.ROOT,worker.source_check,catmod.catalogue,native.control,native.bridge,numeric.qualify_geometry,instruments.qualify)
 worker.ROOT=small_root;worker.source_check=lambda _: {'fixture':'external source gate tested separately'};catmod.catalogue=lambda _:[s]
 def external_control(repo,out,plan):
  value={'status':'host_fixture_external_control_not_admission','field':'unused','nodes':41,'length':12.};save(out/'Q2-CONTROL.json',value);return value
 def external_bridge(repo,out,plan,allow):
  value={'status':'host_fixture_external_fields_unavailable'};save(out/'NATIVE-BRIDGE.json',value);return value
 native.control=external_control;native.bridge=external_bridge;numeric.qualify_geometry=lambda *args: {'selected_backend':'cpu'};instruments.qualify=lambda: {'status':'host_instruments_passed','scope':'Independent kernel qualification already completed earlier in this same test'}
 output=root/'small-campaign';worker.execute(fixture_repo,output,'cpu','run',False)
 record=load(output/'record.json');assert record['status']=='complete_pending_review' and record['broad'][0]['status']=='budget_exhausted_unresolved' and record['counts']['spent_optimizer_attempts']==2
 worker.execute(fixture_repo,output,'cpu','run',False);assert load(output/'record.json')['counts']['spent_optimizer_attempts']==2
 with zipfile.ZipFile(output/'evidence.zip') as z:
  assert z.testzip() is None and not any(n.endswith('.npz') for n in z.namelist())
  for line in z.read('SHA256SUMS').decode().splitlines():
   digest,name=line.split('  ',1);assert __import__('hashlib').sha256(z.read(name)).hexdigest()==digest
 assert '<svg' in (output/'REPORT.html').read_text() and b'\r' not in (output/'screening.csv').read_bytes()
 worker.ROOT,worker.source_check,catmod.catalogue,native.control,native.bridge,numeric.qualify_geometry,instruments.qualify=actual
 checks.append('Actual small CPU funnel reaches budget exhaustion, produces browser plots/LF CSV and complete compact ZIP hashes, and resumes without repeating optimizer steps; external retained-field/device gates are labelled fixtures')

 # Apply the actual publication mutation to the supplied real register, with a
 # temporary parent already assessed as confirmed by workstation PR79 receipt.
 repo=root/'repo';repo.mkdir();subprocess.run(['git','init','-q',str(repo)],check=True)
 original=load(a.repo/'docs/project/roadmap.json') if (a.repo/'docs/project/roadmap.json').exists() else load(ROOT/'validation/ROADMAP.json')
 parent=next(x for x in original['studies'] if x['id']=='s5-b-016');parent.update(state='assessed');entry={'role':'assessment','path':load(ROOT/'RESULTS.json')['parent_assessment'],'label':'Confirmed PR79 assessment'}
 if not any(r['path']==entry['path'] for r in parent['records']):parent['records'].append(entry)
 (repo/'docs/project').mkdir(parents=True);save(repo/'docs/project/roadmap.json',original);m={'base':'f'*40,'installed_at':stamp(),'package_sha256':sha(ROOT/'PLAN.json')}
 parent_file=repo/load(ROOT/'RESULTS.json')['parent_results'];parent_file.parent.mkdir(parents=True,exist_ok=True);parent_file.write_bytes((ROOT/'validation/PARENT-RESULTS.json').read_bytes())
 subprocess.run(['git','-C',str(repo),'config','user.name','Offline Fixture'],check=True);subprocess.run(['git','-C',str(repo),'config','user.email','fixture@example.invalid'],check=True);subprocess.run(['git','-C',str(repo),'add','.'],check=True);subprocess.run(['git','-C',str(repo),'commit','-qm','fixture baseline'],check=True)
 head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip();assert not pub.verify_baseline(repo,head)['ancestry_required']
 pub.apply(repo,m);one={f.relative_to(repo).as_posix():sha(f) for f in repo.rglob('*') if f.is_file() and '.git' not in f.parts};pub.apply(repo,m);two={f.relative_to(repo).as_posix():sha(f) for f in repo.rglob('*') if f.is_file() and '.git' not in f.parts};assert one==two
 updated=load(repo/'docs/project/roadmap.json');assert updated['studies'][:-1]==original['studies'] and updated['current']==original['current']
 record=load(repo/m['preparation_path']/'record.json');assert re.fullmatch(r'\d{8}t\d{6}z-[a-f0-9]{8}',record['record_id'])
 pub.verify_manifest(repo/m['preparation_path'])
 for md in (repo/m['preparation_path']).rglob('*.md'):
  for link in re.findall(r'\]\(([^)]+)\)',md.read_text()):
   if not link.startswith(('http:','https:','#')):assert (md.parent/link).exists(),(md,link)
 checks.append('Actual preparation apply is idempotent against the supplied project register; prior study/current records preserved, canonical IDs, Markdown links and nested checksums pass')

for f in ROOT.rglob('*.py'):compile(f.read_text(),str(f),'exec')
result={'recorded_at':stamp(),'status':'passed','checks':checks,'numerical_instruments':instrument,'limits':['Complete module imports and actual retained Q2/native Q22 or Q17 fields are qualified on the zbook','Host numerical tests used literal retained operator kernels without unavailable unrelated driver imports' if a.kernel_only else 'Complete installed reference modules used','No actual CUDA device, production Q17-Q32 campaign or GitHub request executed here; small numerical control fields only','Actual repository administrative validators and hosted checks run on the zbook before merge','Historical backtests are correlated diagnostics, not a validated higher-Q selection probability']}
save(ROOT/'HOST-VALIDATION.json',result);print(json.dumps(result,indent=2))
