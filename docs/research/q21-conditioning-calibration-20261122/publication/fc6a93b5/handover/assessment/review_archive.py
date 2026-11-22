from pathlib import Path,PurePosixPath
import json,hashlib,zipfile,statistics,csv,io
import numpy as np
import argparse
parser=argparse.ArgumentParser(description='Validate the pinned completed compact archive and recompute recorded gates/fits. This does not replay full fields.')
parser.add_argument('evidence',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
base=args.output.resolve();base.mkdir(parents=True,exist_ok=True);src=args.evidence.resolve();out=base/'compact';out.mkdir(exist_ok=True)
assert hashlib.sha256(src.read_bytes()).hexdigest()=='c0fd32690d23b80fad77e33d1bc27048983ec1cb3335ac36c91004d75c938962','This review is pinned to a different evidence archive'
with zipfile.ZipFile(src) as z:
 names=z.namelist();assert len(names)==len(set(names));assert z.testzip() is None
 sums={}
 for line in z.read('SHA256SUMS').decode().splitlines():
  h,n=line.split('  ',1);p=PurePosixPath(n);assert not p.is_absolute() and '..' not in p.parts and n not in sums;assert hashlib.sha256(z.read(n)).hexdigest()==h,n;sums[n]=h
 assert set(sums)|{'SHA256SUMS'}==set(names)
 for n in names:
  f=out/n;f.parent.mkdir(exist_ok=True,parents=True);f.write_bytes(z.read(n))
load=lambda n:json.loads((out/n).read_text())
sha=lambda n:hashlib.sha256((out/n).read_bytes()).hexdigest()
r=load('record.json');p=load('handover/PLAN.json');g=p['registered_gates'];total=0;accepted=0;allgates=[];audits=[];summary=[]
for c in r['cases']:
 cfg=c['case'];folder='cases/'+cfg['id'];cp=load(folder+'/control.json');ledger=load(folder+'/attempt-ledger.json');hist=c['history'];total+=len(ledger);accepted+=c['accepted_steps'];assert c['history']==cp['history'];assert len(ledger)==c['charged_attempts']==c['accepted_steps'];assert len(hist)==c['accepted_steps']+1
 canon=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
 assert cp['history_sha256']==canon(hist);assert load(folder+'/record.seal.json')['sha256']==sha(folder+'/record.json');assert c==load(folder+'/record.json')
 assert hist[0]['iteration']==425
 for row in hist:
  m=row['metrics'];finite=all(np.isfinite(m[k]) for k in ['relative_force_l2','acceleration_max','hopf_integral','minimum_corner_cone','unit_error','tail_fraction','guard_fraction']);rep=bool(finite and abs(abs(m['hopf_integral'])-21)/21<=g['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<g['unit_limit']);st=rep and m['relative_force_l2']<=g['force_limit'] and m['acceleration_max']<=g['acceleration_limit'];bd=finite and m['tail_fraction']<=g['initial_tail_limit'] and m['guard_fraction']<=g['tail_guard_limit'];assert row['gates']=={'representation':rep,'strict_stationary':st,'boundary_admitted':bd,'all_readiness_gates':st and bd};allgates.append(row['gates']);
  if row['accepted_step']>0:audits.append(row['backend_audit']);assert row['backend_audit']['passed']
 energy=[a['metrics']['energy'] for a in hist];assert all(b<=a+1e-13 for a,b in zip(energy,energy[1:]))
 best=min(hist,key=lambda a:max(a['metrics']['relative_force_l2']/g['force_limit'],a['metrics']['acceleration_max']/g['acceleration_limit']));assert c['best_retained']['accepted_step']==best['accepted_step'];assert c['best_retained']['sha256']==load(folder+'/'+c['best_retained']['path'].replace('.npz','.seal.json'))['sha256'];assert c['endpoint']['sha256']==load(folder+'/endpoint.seal.json')['sha256']
 response=c['response'];window=hist[21:31];f=statistics.median(a['metrics']['relative_force_l2'] for a in window);a=statistics.median(a['metrics']['acceleration_max'] for a in window);assert np.isclose(response['median_force'],f,rtol=1e-13);assert np.isclose(response['median_acceleration'],a,rtol=1e-13);assert np.isclose(response['score'],max(f/1e-4,a/.001),rtol=1e-13)
 final=c['final']['metrics'];time=[a.get('optimization_seconds',0) for a in hist[1:]]
 summary.append({'case':cfg['id'],'shift':cfg['shift'],'attempts':len(ledger),'energy':final['energy'],'force':final['relative_force_l2'],'amax':final['acceleration_max'],'arm_best_step':best['accepted_step'],'best_force':best['metrics']['relative_force_l2'],'best_amax':best['metrics']['acceleration_max'],'best_score':max(best['metrics']['relative_force_l2']/1e-4,best['metrics']['acceleration_max']/.001),'median_opt_seconds':statistics.median(time),'optimization_seconds':sum(time),'tail':final['tail_fraction'],'guard':final['guard_fraction'],'endpoint_sha256':c['endpoint']['sha256']})
assert total==accepted==r['charged_optimizer_attempts']==580
# Embedded payloads must match the released handover, apart from its own excluded manifest path.
hand=out/'handover';ms={}
for line in (hand/'SHA256SUMS').read_text().splitlines():
 h,n=line.split('  ',1);assert hashlib.sha256((hand/n).read_bytes()).hexdigest()==h;ms[n]=h
assert set(ms)=={f.relative_to(hand).as_posix() for f in hand.rglob('*') if f.is_file() and f.name!='SHA256SUMS' and '__pycache__' not in f.parts}
assert hashlib.sha256((hand/'SHA256SUMS').read_bytes()).hexdigest()=='4e38724a5e0b42ee2abaaaa0741e4273d053744c175511c76c8a01350b27138a','Released handover identity differs'
fm=load('FIELD-MANIFEST.json')['fields'];assert len({a['path'] for a in fm})==len(fm)
for x in fm:assert load(x['path'].replace('.npz','.seal.json'))['sha256']==x['sha256']
# Independent curve reproduction from uploaded measurements, using unchanged registered implementation.
import sys
sys.path.insert(0,str(hand));from fitting import curves,select
def compare(a,b):
 if isinstance(a,dict):
  assert a.keys()==b.keys()
  for k in a:compare(a[k],b[k])
 elif isinstance(a,list):
  assert len(a)==len(b)
  for x,y in zip(a,b):compare(x,y)
 elif isinstance(a,float):assert np.isclose(a,b,rtol=1e-11,atol=1e-12),(a,b)
 else:assert a==b,(a,b)
compare(curves(r['samples'],p),load('CURVE-FITS.json'));compare(select(r['samples'],p),load('SELECTION.json'))
# Telemetry and CPU/IO accounting.
tele=[json.loads(l) for l in (out/'telemetry.jsonl').read_text().splitlines()];first=tele[0];last=tele[-1]
from datetime import datetime
duration=(datetime.fromisoformat(r['recorded_at']['utc'])-datetime.fromisoformat(load('identity.json')['recorded_at']['utc'])).total_seconds()
res={'archive_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'members':len(names),'verified_hashed_members':len(sums),'run_id':load('identity.json')['run_id'],'status':r['status'],'elapsed_seconds':duration,'charged_attempts':total,'accepted_steps':accepted,'cases':len(summary),'all_observations':len(allgates),'strict_stationary_passes':sum(x['strict_stationary'] for x in allgates),'all_readiness_passes':sum(x['all_readiness_gates'] for x in allgates),'representation_passes':sum(x['representation'] for x in allgates),'boundary_passes':sum(x['boundary_admitted'] for x in allgates),'backend_audits_passed':sum(x['passed'] for x in audits),'retained_field_files':len(fm),'retained_bytes':sum(x['bytes'] for x in fm),'maximum_optimization_energy_gradient_difference':max(x['gradient_max_abs_difference'] for x in audits),'minimum_host_available_gib':min(x['host']['available_gib'] for x in tele),'maximum_cgroup_peak_bytes':max(x['cgroup']['memory.peak'] for x in tele),'maximum_oom_kill':max(x['cgroup']['memory.events']['oom_kill'] for x in tele),'maximum_high_events':max(x['cgroup']['memory.events']['high'] for x in tele),'optimization_seconds':sum(x['optimization_seconds'] for x in summary),'summary':summary,'scope':'Compact archive replay and independent recorded-measurement analysis. Full NPZ fields are declared and sealed but absent, so their metrics are not independently recomputed here.'}
(base/'INDEPENDENT-REVIEW.json').write_text(json.dumps(res,indent=2)+'\n');(base/'ENDPOINTS.csv').write_text('')
with (base/'ENDPOINTS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(summary[0]),lineterminator='\n');w.writeheader();w.writerows(summary)
print(json.dumps(res,indent=2))
