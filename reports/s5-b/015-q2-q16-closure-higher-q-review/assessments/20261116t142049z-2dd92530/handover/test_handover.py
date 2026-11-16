"""Offline checks of actual publication application; no GitHub requests or numerical solver."""
import hashlib,importlib.util,json,re,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('closure_handover',ROOT/'handover.py');pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
checks=[]
for p in ROOT.glob('*.py'):compile(p.read_text(),str(p),'exec')
checks.append('All shipped Python sources compile')
for p in ROOT.rglob('*.csv'):
 b=p.read_bytes();assert b'\r' not in b and b.endswith(b'\n'),p
checks.append('Every shipped CSV uses LF only and retains a final newline')
ledger=pub.load(ROOT/'SCREEN-LEDGER.json');closure=pub.load(ROOT/'Q2-Q16-CLOSURE.json')
assert len([r for r in ledger['rows'] if r['stage']=='broad'])==30 and len([r for r in ledger['rows'] if r['stage']=='priority'])==4
assert len([r for r in ledger['rows'] if r['decision']=='defer_resolution'])==6
assert [r['q'] for r in closure['rows']]==list(range(2,17)) and not any(r['physical_Q_rejected'] for r in closure['rows'])
checks.append('Full Q2–Q16 scope,30 broad entries,4 priority entries,6 explicit resolution deferrals and zero physical rejections')
with zipfile.ZipFile(ROOT/'data/campaign2-evidence.zip') as z:c=json.loads(z.read('record.json'))
assert c['additional_steps']==500 and c['maximum_additional_steps']==600
with zipfile.ZipFile(ROOT/'data/decision-audit-evidence.zip') as z:a=json.loads(z.read('COMPARISON.json'))
assert a['decision']=='not_ready_within_final_declared_audit_park_unchanged_route' and sum(r['accepted_steps'] for r in a['results'])==100
endpoints=pub.load(ROOT/'ENDPOINTS.json')['rows'];look={x['arm']:x for x in endpoints}
assert abs(look['CG-control']['acceleration_gate_multiple']-1.294412713040077)<1e-12
assert abs(look['LBFGS-trial']['acceleration_gate_multiple']-5.968750226150226)<1e-12
assert not any(all(x[k]<=1 for k in ['force_gate_multiple','acceleration_gate_multiple','tail_gate_multiple']) for x in endpoints)
checks.append('Measured campaign/audit counts and endpoint gate table match original archives')
fixture={'studies':[{'id':'s5-b-012','stage':'s5-b','number':12,'slug':'rapid-q-screening','state':'assessed','records':[]},{'id':'s5-b-013','stage':'s5-b','number':13,'slug':'rapid-q-bounded-followup','state':'assessed','records':[]},{'id':'s5-b-014','stage':'s5-b','number':14,'slug':'targeted-q-campaign2','state':'prepared','records':[]},{'id':'s5-c-002','stage':'s5-c','number':2,'slug':'unrelated-study','state':'prepared','records':[],'next_action':'Preserve me'}],'priority':['s5-c-002','s5-b-014','s5-b-013'],'current':{'latest_assessed_study':'s5-c-002','summary':'preserve unrelated current'}}
def snapshot(dest):return {n:pub.sha(dest/n) for n in pub.files(dest)}
with tempfile.TemporaryDirectory() as td:
 dest=Path(td);(dest/'docs/project').mkdir(parents=True);pub.save(dest/'docs/project/roadmap.json',fixture)
 # Existing immutable scientific record must remain byte-exact.
 old=dest/'reports/s5-b/014-targeted-q-campaign2/preparation/20261115t141810z-12345678/old.txt';old.parent.mkdir(parents=True);old.write_text('Original negative/prepared record: retain exactly.\n');oldhash=pub.sha(old)
 m={'installed_at':pub.stamp(),'base':'a'*40,'package_sha256':pub.sha(ROOT/'SHA256SUMS')}
 pub.apply(dest,m);one=snapshot(dest);pub.apply(dest,m);assert one==snapshot(dest)
 d=pub.load(dest/'docs/project/roadmap.json');assert d['current']==fixture['current'] and d['priority'][0]=='s5-c-002'
 assert next(s for s in d['studies'] if s['id']=='s5-c-002')==fixture['studies'][-1]
 assert pub.sha(old)==oldhash and len(d['studies'])==5
 checks.append('Actual apply() idempotence; immutable original record; unrelated study/current/priority preserved')
 for p in (dest/'reports').rglob('record.json'):
  rec=pub.load(p);assert re.fullmatch(r'\d{8}t\d{6}z-[a-f0-9]{8}',rec['record_id']) and p.parent.name==rec['record_id']
 for p in (dest/'reports').rglob('SHA256SUMS'):pub.verify_manifest(p.parent)
 # The outer record MUST include the child handover checksum itself.
 outer=dest/m['assessment_path'];assert 'handover/SHA256SUMS' in (outer/'SHA256SUMS').read_text()
 checks.append('Canonical record ID grammar and exact nested checksum coverage including child SHA256SUMS')
 for p in dest.rglob('*.md'):
  for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in target and not target.startswith('#'):assert (p.parent/target).exists(),(p,target)
 checks.append('All published Markdown relative file links resolve')
 # A conflicting existing scientific assessment must be refused rather than overwritten.
 record=outer/'record.json';x=pub.load(record);x['handover_sha256']='different';pub.save(record,x)
 try:pub.apply(dest,m)
 except RuntimeError as e:assert 'Existing closure record differs' in str(e)
 else:raise AssertionError('Conflicting record overwritten')
 checks.append('Conflicting existing assessment rejected')
 # Current summary for affected route is advanced to closure, not left claiming pending production.
 fixture['current']={'latest_assessed_study':'s5-b-014','summary':'old pending'}
 other=dest/'other';(other/'docs/project').mkdir(parents=True);pub.save(other/'docs/project/roadmap.json',fixture);pub.apply(other,m)
 d=pub.load(other/'docs/project/roadmap.json');assert d['current']['latest_assessed_study']==m['study_id'] and all(s['state']=='assessed' for s in d['studies'] if s['id'] in ['s5-b-012','s5-b-013','s5-b-014'])
 checks.append('Affected allocation states and current summary resolve to assessed/parked, with scientific gate open')
 # Rehearse the actual merge function without any service call.
 from types import SimpleNamespace
 dest=Path(td)/'merge';(dest/'.git').mkdir(parents=True)
 m={'commit':'b'*40,'pr':{'number':123,'url':'fixture-pr'},'phase':'committed'};pub.save(pub.marker(dest),m)
 original_cmd,original_verify=pub.cmd,pub.verify;calls=[];state={'merged':False}
 def fake_cmd(args,cwd,capture=False):
  calls.append(args)
  if args[:3]==['git','status','--porcelain']:return ''
  if args[:3]==['git','rev-parse','HEAD']:return m['commit']
  if args[:3]==['gh','pr','view']:return json.dumps({'number':123,'state':'MERGED' if state['merged'] else 'OPEN','headRefOid':m['commit'],'url':'fixture-pr'})
  if args[:3]==['gh','pr','merge']:assert args[-2:]==['--match-head-commit',m['commit']];state['merged']=True
  return ''
 pub.cmd=fake_cmd;pub.verify=lambda:None
 try:pub.merge(SimpleNamespace(publication=dest))
 finally:pub.cmd=original_cmd;pub.verify=original_verify
 assert pub.load(pub.marker(dest))['phase']=='merged' and pub.load(pub.marker(dest))['pr']['state']=='MERGED'
 assert next(i for i,x in enumerate(calls) if x[:3]==['gh','pr','checks'])<next(i for i,x in enumerate(calls) if x[:3]==['gh','pr','merge'])
 checks.append('Actual merge control flow rehearsed: checks precede exact-head merge and observed MERGED status is persisted; no network calls')
validation={'recorded_at':pub.stamp(),'status':'passed','checks':checks,'execution_scope':'Offline actual publication apply() and original archive checks; no mocked scientific metrics','limitations':['Actual repository project_records.py/check_docs.py and hosted checks run on the workstation before publication','No GitHub request, CPU/GPU solver run, new field replay, physical stability proof or peer review was performed here']}
if len(__import__('sys').argv)>1:Path(__import__('sys').argv[1]).write_text(json.dumps(validation,indent=2)+'\n')
else:print(json.dumps(validation,indent=2))
