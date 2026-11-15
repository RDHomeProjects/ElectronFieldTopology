from pathlib import Path
import sys,ast,tempfile,json,shutil,math,time,numpy as np,importlib.util,re
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
from support import *
from analysis import spatial_summary,curve_fits
# An early improvement followed by a plateau must NOT grant an extension.
h=[{'iteration':i,'relative_force_l2':.01*math.exp(-.05*min(i,50)),'acceleration_max':.1*math.exp(-.05*min(i,50))} for i in range(0,151,5)]
assert not contingency(h,0)[0]
h=[{'iteration':i,'relative_force_l2':.01*math.exp(-.005*i),'acceleration_max':.1*math.exp(-.005*i)} for i in range(0,151,5)];assert contingency(h,0)[0]
# Analytic projection and temporal fits retained.
n=np.zeros((13,)*3+(3,));n[...,2]=1;raw=np.zeros_like(n);raw[...,0]=2;raw[...,2]=99;fixed=np.ones((13,)*3,bool);fixed[2:-2,2:-2,2:-2]=False
r,mag=spatial_summary(n,raw,(.5,)*3,fixed);assert np.allclose(mag[~fixed],2) and not mag[fixed].any()
f=curve_fits(h);assert f['relative_force_l2']['models'][0]['model']=='exponential'
# Extract actual branch functions; deterministic substitute engine tests policy, not D4 physics.
tree=ast.parse((root/'worker.py').read_text());selected=[v for v in tree.body if isinstance(v,ast.FunctionDef) and v.name in ['save_history','branch_job']]
class Grid:
 def __init__(self,shape,lengths,mode):self.shape=shape;self.lengths=lengths
class Engine:
 kind='cpu';xp=np
 def __init__(self,*args):pass
 def state(self,n):return {'n':n.copy(),'iteration':100,'alpha':1.,'old_g':None,'old_z':None,'direction':None}
 def host(self,n):return n.copy()
 def sync(self):pass
 def audit(self,*args):return {'passed':True}
 def step(self,s,g):
  if case.get('interrupt_at')==s['iteration']:case.pop('interrupt_at');raise KeyboardInterrupt('fixture interruption')
  s['iteration']+=1;s['n'][0]=s['iteration'];return True,{'energy':1.,'objective_calls':2}
def checkpoint(path,s,e,ident):
 with Path(path).open('wb') as f:np.savez(f,**{k:v for k,v in s.items() if v is not None})
def restore(path,e,ident):
 with np.load(path) as z:return {k:z[k].copy() if k in ['n','old_g','old_z','direction'] else float(z[k]) if k=='alpha' else int(z[k]) for k in z.files}
case={'q':8,'kind':'slow'}
rows={k:{'seed':{'q':q,'id':k},'q':q,'iteration':i,'nodes':nodes} for k,q,i,nodes in [('q8-trefoil32-1-2',8,600,121),('q10-trefoil32-2-2',10,300,145),('q4-axial22',4,1300,121),('q5-trefoil32-1-1',5,100,121)]}
def metrics(n,g):
 q=case['q'];i=float(n[0]);start={8:600,10:300,4:1300,5:100}[q];d=i-start
 rate=.005
 if case['kind']=='plateau':d=min(d,50);rate=.05
 return {'relative_force_l2':.01*math.exp(-rate*d),'acceleration_max':.1*math.exp(-rate*d),'hopf_integral':-q,'minimum_corner_cone':.8,'unit_error':0.,'tail_fraction':.0001}
def representation(m,q,p):return True
def stationary(m,q,p):return m['relative_force_l2']<=1e-4 and m['acceleration_max']<=1e-3
def endpoint(key,start=False):
 i=rows[key]['iteration'];return {'n':np.array([float(i)]),'iteration':i,'alpha':.10936253623915125,'old_g':np.array([2.]),'old_z':np.array([3.]),'direction':np.array([4.])},{'fixture':True}
def adapt_state(s,e):return {k:v.copy() if isinstance(v,np.ndarray) else v for k,v in s.items()}
def fine_q5():
 s,meta=endpoint('q5-trefoil32-1-1');state=Engine().state(s['n']);return state,Grid((145,)*3,(27.648,)*3,'fixed'),meta
v=globals().copy();v.update(GATES={'initial_tail_limit':.00075,'qualification_rtol':2e-10,'qualification_atol':2e-11},engine_for=lambda *args:Engine(),guard=lambda:None,gc=__import__('gc'),log=lambda *args,**kw:None,PROFILE={},record_time=lambda *args:None,audited=lambda *args:{'passed':True})
exec(compile(ast.Module(body=selected,type_ignores=[]),'actual-campaign2-branch-under-test','exec'),v)
checks=[]
with tempfile.TemporaryDirectory() as td:
 v['out']=Path(td)
 for key,label,q,maximum,base,kind,fine,trial in [('q8-trefoil32-1-2','q8-max',8,250,150,'slow',False,False),('q8-trefoil32-1-2','q8-plateau',8,250,150,'plateau',False,False),('q10-trefoil32-2-2','q10-max',10,150,150,'slow',False,False),('q4-axial22','q4-control',4,50,50,'slow',False,False),('q4-axial22','q4-trial',4,50,50,'slow',False,True),('q5-trefoil32-1-1','q5-control',5,50,50,'slow',False,False),('q5-trefoil32-1-1','q5-expanded',5,50,50,'slow',True,False)]:
  case.update(q=q,kind=kind);result=v['branch_job'](key,label,maximum,base,{'identity':{}},fine,trial)
  assert result['additional_steps']==(150 if label=='q8-plateau' else maximum)
  folder=Path(td)/'jobs'/label
  contingencies=sorted(f.name for f in folder.glob('contingency-*'))
  if label=='q8-max':assert contingencies==['contingency-750.json','contingency-800.json']
  if q==10:assert not contingencies
  if q==4:
   meta=load(folder/'import.json');assert meta['initial_alpha']==.10936253623915125 and meta['initial_memory_present']==(not trial)
  if q==5:assert result['length']==(27.648 if fine else 23.04) and load(folder/'import.json')['initial_alpha']==1.
  # Every paired observation occurs at the common5-step native schedule.
  if q in [4,5]:assert all((b['iteration']-a['iteration'])==5 for a,b in zip(result['history'],result['history'][1:]))
  checks.append({k:result[k] for k in ['label','additional_steps','allocation_status']})
 case.update(q=8,kind='slow',interrupt_at=620)
 try:v['branch_job']('q8-trefoil32-1-2','q8-resume',250,150,{'identity':{}})
 except KeyboardInterrupt:pass
 else:raise AssertionError('Expected interruption')
 result=v['branch_job']('q8-trefoil32-1-2','q8-resume',250,150,{'identity':{}});assert result['additional_steps']==250
# Test actual embedding code, not a replacement, with a real-sized unit field.
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fine_q5')
parent=np.zeros((121,)*3+(3,));parent[...,2]=1;parent[60,60,60]=[.6,0,.8]
env={'np':np,'Grid':Grid,'Engine':Engine,'need':need,'endpoint':lambda key:({'n':parent.copy()},{'fixture':True})}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-domain-embedding-under-test','exec'),env)
state,g,meta=env['fine_q5']();assert np.array_equal(state['n'][12:133,12:133,12:133],parent);assert np.all(state['n'][:12,...,2]==1) and state['iteration']==100 and state['alpha']==1.;assert abs(23.04/120-27.648/144)<1e-15
# Publication fixture: actual apply() on an existing prepared schema, twice.
spec=importlib.util.spec_from_file_location('pub',root/'publication.py');pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
with tempfile.TemporaryDirectory() as td:
 dest=Path(td);(dest/'docs/project').mkdir(parents=True)
 roadmap={'studies':[{'id':'s5-b-013','stage':'s5-b','number':13,'slug':'rapid-q-bounded-followup','state':'assessed','records':[]}],'priority':['unrelated-active','s5-b-013'],'current':{'latest_assessed_study':'unrelated-active','summary':'preserve'}};save(dest/'docs/project/roadmap.json',roadmap)
 m={'installed_at':stamp(),'base':'fixture-base','package_sha256':'1'*64};pub.apply(dest,m);before=(dest/'docs/project/roadmap.json').read_bytes();pub.apply(dest,m);assert before==(dest/'docs/project/roadmap.json').read_bytes()
 d=load(dest/'docs/project/roadmap.json');assert d['priority'][0]=='unrelated-active' and d['current']==roadmap['current'];assert len(d['studies'])==2
 for f in (dest/'reports').rglob('record.json'):
  rec=load(f);assert re.fullmatch(r'\d{8}t\d{6}z-[a-f0-9]{8}',rec['record_id']) and f.parent.name==rec['record_id']
 for md in (dest/'reports').rglob('*.md'):
  for target in re.findall(r'\]\(([^)]+)\)',md.read_text()):
   assert (md.parent/target).exists(),(md,target)
 # Exact checksum inventory must include nested checksum files.
 for checksum in (dest/'reports').rglob('SHA256SUMS'):
  directory=checksum.parent;covered=set()
  for line in checksum.read_text().splitlines():
   digest,name=line.split('  ',1);assert sha(directory/name)==digest;covered.add(name)
  actual={f.relative_to(directory).as_posix() for f in directory.rglob('*') if f.is_file() and f!=checksum}
  assert covered==actual,(directory,actual-covered,covered-actual)

# Actual campaign orchestration: Q10 diagnostic must follow its continuation.
run_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run');order=[]
with tempfile.TemporaryDirectory() as td:
 out=Path(td);receipt={'identity':{}};save(out/'preflight.json',receipt);(out/'preflight.sha256').write_text(sha(out/'preflight.json')+'\n')
 def branch_stub(key,label,maximum,base,receipt,fine=False,trial=False):
  order.append(('branch',label));return {'seed':key,'label':label,'additional_steps':maximum,'allocation_status':'budget_exhausted_unresolved'}
 env=globals().copy();env.update(out=out,identity=lambda:{},source_verify=lambda full:order.append(('verify',full)),branch_job=branch_stub,diagnose_q10=lambda item:order.append(('diagnose',item['label'])),PLAN=load(root/'PLAN.json'),PROFILE={},log=lambda *args,**kw:None,report=lambda results:None,seal_output=lambda:(out/'evidence.zip').write_bytes(b'fixture'))
 env['rows']={**rows,'q4-axial22':{**rows['q4-axial22'],'checkpoint_sha256':'fixture'}}
 exec(compile(ast.Module(body=[run_node],type_ignores=[]),'actual-campaign-orchestration-under-test','exec'),env);env['run']()
 assert order.index(('diagnose','q10-continuation-2'))==order.index(('branch','q10-continuation-2'))+1
 rec=load(out/'record.json');assert rec['additional_steps']==600 and rec['q6_relaxation_steps']==0 and len(rec['results'])==6
validation={'recorded_at':stamp(),'status':'passed','branch_control_flow':checks,'additional_tests':['recent-window plateau rejection despite large early improvement','Q8 first150 then only50-step extensions and250 cap','actual orchestration: Q10 continuation precedes diagnosis and full cap totals600','Q4 alpha preservation and exclusive memory treatment','Q5 bitwise aligned embedding and equal spacing','common paired measurement schedule','interrupted optimizer continuation recovery','publication ID format, idempotency and unrelated-priority preservation','prepared documentation local link targets','exact nested checksum coverage including child SHA256SUMS'],'limits':['Synthetic branch engine tests control flow, not actual D4 solver physics.','Production full fields/CUDA unavailable here; actual source/field replay, parity and timing are mandatory local preflight checks.','Actual repository administrative validators run locally before publication.']}
print(json.dumps(validation,indent=2))
