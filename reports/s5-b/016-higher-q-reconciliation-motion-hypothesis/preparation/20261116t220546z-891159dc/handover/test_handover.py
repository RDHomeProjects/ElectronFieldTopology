"""Offline analytic, publication and real local Git collection checks; no scientific field replay."""
import argparse,sys,tempfile,subprocess,json,re,io,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
import publication as pub,collector,diagnostics,handover
p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();checks=[]
for f in ROOT.glob('*.py'):compile(f.read_text(),str(f),'exec')
checks.append('All shipped Python sources compile')
# Independent closed-form generator/rate-balance fixture with an interior exact optimum.
class Grid:
 shape=(7,7,7);lengths=(6.,)*3;spacing=(1.,)*3;boundary='fixed'
 def fixed_mask(self):
  f=np.ones(self.shape,bool);f[1:-1,1:-1,1:-1]=False;return f
g=Grid();n=np.zeros(g.shape+(3,));n[...,2]=1.;n[~g.fixed_mask()]=[.6,0,.8];north=np.array([0.,0.,1.]);generator=np.cross(north,n);centripetal=np.cross(north,generator);c=north-n*np.sum(n*north,axis=-1,keepdims=True);c[g.fixed_mask()]=0;a0=-.0004*c
class Analytic:
 @staticmethod
 def retract(n,v,g):return n.copy(),v.copy()
 @staticmethod
 def acceleration(n,v,g):
  w=float(np.sum(v*generator)/np.sum(generator*generator));return v,a0+w*w*(c+centripetal)
r=diagnostics.probe(n,g,Analytic,Analytic)
assert abs(r['fit']['omega_clipped']-.02)<1e-10 and r['fitted_ansatz_residual']['maximum']<1e-12 and not r['stability_certified'] and not r['gate_override'] and r['physical_time_steps']==0
mask=~g.fixed_mask();assert diagnostics.fit_squared_frequency(c,c,mask,.05)['omega_squared_clipped']==0
assert diagnostics.fit_squared_frequency(-c,c,mask,.05)['clipped_at_boundary']
assert not diagnostics.fit_squared_frequency(c,np.zeros_like(c),mask,.05)['identifiable']
checks.append('Known analytic frequency optimum recovered; boundary clipping and unidentifiable fit reported; no stability/gate promotion')
fixture={'studies':[{'id':'s5-a-002','stage':'s5-a','number':2,'slug':'q22-benchmark','state':'assessed','gate':'open','records':[],'finding':'retain Q22 finding'},{'id':'s5-a-003','stage':'s5-a','number':3,'slug':'q18-neighbours','state':'assessed','gate':'open','records':[],'finding':'retain Q18 finding'},{'id':'s5-b-015','stage':'s5-b','number':15,'slug':'q2-q16-closure-higher-q-review','state':'assessed','gate':'open','records':[],'finding':'park unchanged route'},{'id':'s5-c-002','stage':'s5-c','number':2,'slug':'unrelated','state':'prepared','records':[],'finding':'preserve unrelated'}],'priority':['s5-c-002','s5-b-015'],'current':{'latest_assessed_study':'s5-c-002','summary':'preserve'}}
def git(dest,*args):return subprocess.check_output(['git','-C',str(dest),*args],text=True,stderr=subprocess.STDOUT).strip()
with tempfile.TemporaryDirectory() as td:
 dest=Path(td);git(dest,'init','-q');git(dest,'config','user.name','Offline fixture');git(dest,'config','user.email','fixture@example.invalid')
 (dest/'docs/project').mkdir(parents=True);pub.save(dest/'docs/project/roadmap.json',fixture)
 prior=dest/'reports/s5-a/002-q22-benchmark/README.md';prior.parent.mkdir(parents=True);prior.write_text('# Unchanged measured result\n')
 oversized=prior.parent/'large.bin';oversized.write_bytes(b'0'*(9*1024*1024))
 (dest/'src/electron_field_topology').mkdir(parents=True);(dest/'src/electron_field_topology/skyrme.py').write_text('K = 1\n')
 git(dest,'add','.');git(dest,'commit','-qm','fixture base');base=git(dest,'rev-parse','HEAD');oldhash=pub.sha(prior)
 m={'base':base,'installed_at':pub.stamp(),'package_sha256':pub.sha(ROOT/'SHA256SUMS')};pub.apply(dest,m)
 one={str(f.relative_to(dest)):pub.sha(f) for f in dest.rglob('*') if f.is_file() and '.git' not in f.parts};pub.apply(dest,m);two={str(f.relative_to(dest)):pub.sha(f) for f in dest.rglob('*') if f.is_file() and '.git' not in f.parts};assert one==two
 d=pub.load(dest/'docs/project/roadmap.json');assert d['current']==fixture['current'] and d['priority'][0]=='s5-c-002' and pub.sha(prior)==oldhash
 assert d['studies'][:4]==fixture['studies']
 for f in (dest/'reports').rglob('record.json'):
  r=pub.load(f);assert r['role']=='preparation' and r['record_id']==f.parent.name and re.fullmatch(r'\d{8}t\d{6}z-[a-f0-9]{8}',r['record_id'])
 for f in (dest/'reports').rglob('SHA256SUMS'):pub.verify_manifest(f.parent)
 for f in dest.rglob('*.md'):
  for link in re.findall(r'\]\(([^)]+)\)',f.read_text()):
   if '://' not in link and not link.startswith('#'):assert (f.parent/link).exists(),(f,link)
 checks.append('Actual publication apply is idempotent; prior reports/studies/current and unrelated priorities unchanged; canonical IDs, roles, Markdown links and nested checksums verified')
 git(dest,'add','.');git(dest,'commit','-qm','fixture prepared');head=git(dest,'rev-parse','HEAD')
 out=dest/'artifacts/test-collection';record=collector.collect(dest,out,Path('/missing/Q2'),Path('/missing/Q8'));collector.verify(out)
 assert record['source_commit']==head and record['relaxation_steps']==record['physical_time_steps']==0
 assert any(x['status']=='deferred_collection_size_budget' and x['path'].endswith('large.bin') for x in record['deferred_members'])
 assert (out/'repository/reports/s5-a/002-q22-benchmark/README.md').read_bytes()==prior.read_bytes()
 assert b'\r' not in (out/'RECONCILIATION.csv').read_bytes();assert len(list(csv.reader(io.StringIO((out/'RECONCILIATION.csv').read_text()))))>=4
 inv=pub.load(out/'repository-inventory.json');assert inv['historical_commits'][0]['status']=='explicitly_deferred_missing_git_object'
 assert all(not x['hash_replayed'] for x in pub.load(out/'local-field-availability.json')['fields'])
 checks.append('Real local Git collector pins HEAD, preserves source bytes, marks missing historical object/fields and binary size budget explicitly, and emits LF CSV')
 # Exercise actual frontend cache and resealing of a blocked diagnostic.
 pub.save(handover.latest_path(argparse.Namespace(publication=dest)),{'output':str(out),'source_commit':head,'package_sha256':pub.sha(ROOT/'SHA256SUMS'),'field_roots':{'Q2':'/missing/Q2','Q8':'/missing/Q8'},'recorded_at':pub.stamp()})
 args=argparse.Namespace(publication=dest,repo=dest,q2_run=Path('/missing/Q2'),q8_run=Path('/missing/Q8'),new_collection=False)
 assert handover.collect(args)==out
 pub.save(out/'DIAGNOSTIC-STATUS.json',{'status':'explicitly_blocked_diagnostic','exit_code':1,'relaxation_steps':0,'physical_time_steps':0});collector.report(out);collector.seal(out);collector.verify(out);handover.diagnose(args)
 checks.append('Frontend retains matching sealed collection and blocked diagnostic receipt; evidence ZIP includes nested manifests and matches payload hashes')
 # Tampering must be rejected rather than producing a false completed assessment.
 (out/'RECONCILIATION.csv').write_bytes(b'changed\r\n')
 try:collector.verify(out)
 except RuntimeError:pass
 else:raise AssertionError('Tampered collection accepted')
 checks.append('Tampered reconciliation artifact rejected')
from html.parser import HTMLParser
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.tables=0;self.scripts=0
 def handle_starttag(self,t,attrs):self.tables+=t=='table';self.scripts+=t=='script'
h=Parser();h.feed((ROOT/'ASSESSMENT.html').read_text());assert h.tables==2 and h.scripts==0
checks.append('Browser report HTML parses with two assessment tables and no script dependency')
result={'recorded_at':pub.stamp(),'status':'passed','checks':checks,'limits':['Analytic generator fixture is not a full-field solver validation','Actual repository project_records.py/check_docs.py run on the workstation','Read-only retained-field source/geometry/metric and nonzero-rate CPU/array replay are mandatory local diagnostic checks','No GitHub requests, numerical relaxation, physical-time integration, GPU execution or scientific stability proof performed here']}
if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
else:print(json.dumps(result,indent=2))
