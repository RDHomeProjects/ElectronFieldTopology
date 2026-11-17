"""Pinned local Git snapshot and explicit Q22/Q18 reconciliation; no network or evolution."""
import hashlib,json,subprocess,csv,io,zipfile,html,shutil
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
def stamp():
 n=datetime.now(timezone.utc);return {'utc':n.isoformat(),'melbourne':n.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def digest(b):return hashlib.sha256(b).hexdigest()
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
def seal(out):
 # Only the enclosing manifest is excluded; nested handover manifests are payload.
 paths=[p for p in sorted(out.rglob('*')) if p.is_file() and p not in [out/'evidence.zip',out/'SHA256SUMS'] and '__pycache__' not in p.parts]
 (out/'SHA256SUMS').write_text(''.join(digest(p.read_bytes())+'  '+p.relative_to(out).as_posix()+'\n' for p in paths))
 with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in paths+[out/'SHA256SUMS']:z.write(p,p.relative_to(out))
def verify(out):
 hashes={}
 for line in (out/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);p=(out/n).resolve()
  if not p.is_relative_to(out.resolve()) or not p.is_file() or digest(p.read_bytes())!=h or n in hashes:raise RuntimeError('Collection checksum mismatch: '+n)
  hashes[n]=h
 actual={p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file() and p not in [out/'SHA256SUMS',out/'evidence.zip'] and '__pycache__' not in p.parts}
 if actual!=set(hashes):raise RuntimeError('Collection manifest coverage differs')
 with zipfile.ZipFile(out/'evidence.zip') as z:
  if z.testzip() is not None or len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=actual|{'SHA256SUMS'}:raise RuntimeError('Collection ZIP coverage or CRC differs')
  for n,h in hashes.items():
   if digest(z.read(n))!=h:raise RuntimeError('Collection ZIP payload differs: '+n)
  if z.read('SHA256SUMS')!=(out/'SHA256SUMS').read_bytes():raise RuntimeError('Collection ZIP manifest differs')
 return len(hashes)
def report(out):
 data={'collection':json.loads((out/'COLLECTION.json').read_text())}
 if (out/'MOTION-PROBES.json').exists():data['motion_probes']=json.loads((out/'MOTION-PROBES.json').read_text())
 if (out/'DIAGNOSTIC-STATUS.json').exists():data['diagnostic_command']=json.loads((out/'DIAGNOSTIC-STATUS.json').read_text())
 (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Higher-Q reconciliation and motion hypothesis</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:30px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f9;padding:20px}</style><h1>Higher-Q reconciliation and motion hypothesis</h1><p>No relaxation or physical-time trajectory. Source collection and instantaneous probes require review; none certifies stability.</p><p><a href="handover/ASSESSMENT.html">Scientific assessment and decision criteria</a> · <a href="RECONCILIATION.csv">Study ledger</a> · <a href="local-field-availability.json">Retained-field availability</a></p><pre>'+html.escape(json.dumps(data,indent=2))+'</pre></html>')
def collect(repo,out,q2_run,q8_run):
 repo=Path(repo).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);head=git(repo,'rev-parse','HEAD').decode().strip()
 roadmap=json.loads(git(repo,'show',head+':docs/project/roadmap.json'));wanted={'q22-benchmark','q18-neighbours','q18-fresh-starts','additional-q','higher-q-motion','dynamics-admission','q2-q16-closure-higher-q-review','spacing-observer-controls','saved-state-observer-calibration','cell-aware-spacing-measurements','controlled-q-dependencies','boost-initialization','focused-motion-convergence'}
 studies=[x for x in roadmap['studies'] if x['slug'] in wanted];required={'q22-benchmark','q18-neighbours','q2-q16-closure-higher-q-review'}
 if not required.issubset({s['slug'] for s in studies}):raise RuntimeError('Required published baseline studies missing; collect from the current installed publication checkout')
 prefixes=[f"reports/{s['stage']}/{s['number']:03d}-{s['slug']}/" for s in studies]
 tree=git(repo,'ls-tree','-rlz',head).split(b'\0');entries=[]
 for item in tree:
  if not item:continue
  meta,path=item.split(b'\t',1);mode,kind,oid,size=meta.decode().split();name=path.decode()
  if kind=='blob':entries.append((name,int(size),oid))
 sources=set(json.loads((ROOT/'SOURCE.json').read_text()));selected=[]
 for name,size,oid in entries:
  numeric=name.startswith('src/electron_field_topology/') and any(k in name.lower() for k in ['skyrme','rational','cable','q18','q22','hopf','seed','convergence','sf_dynamics','sf_time','sf_readmission'])
  if numeric or name in sources or name=='docs/project/roadmap.json' or name.startswith('docs/models/SF-') or any(name.startswith(p) for p in prefixes) or ('literature' in name.lower() and name.endswith(('.md','.json','.bib'))):selected.append((name,size,oid))
 # Prefer complete text records over archived binary payloads already held elsewhere.
 selected.sort(key=lambda r:(Path(r[0]).suffix not in ['.md','.json','.csv','.py','.txt','.toml','.lock','.bib'],r[0]))
 inventory=[];used=0;cap=64*1024*1024
 for name,size,oid in selected:
  item={'path':name,'bytes':size,'git_blob':oid}
  if name.endswith(('.npz','.npy')):item.update(status='deferred_full_field_not_embedded')
  elif size>8*1024*1024 or used+size>cap:item.update(status='deferred_collection_size_budget',reason='8MiB per member;64MiB total; original remains in Git')
  else:
   b=git(repo,'cat-file','blob',oid);p=out/'repository'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);used+=len(b);item.update(status='copied',sha256=digest(b))
  inventory.append(item)
 history=[]
 for commit in [json.loads((ROOT/'LEGACY-ENDPOINTS.json').read_text())['source_commit']]:
  try:
   raw=git(repo,'ls-tree','-rlz',commit)
   start=len(inventory)
   for item in raw.split(b'\0'):
    if not item:continue
    meta,path=item.split(b'\t',1);mode,kind,oid,size=meta.decode().split();name=path.decode()
    if kind!='blob' or not (name.startswith('src/electron_field_topology/') or name.startswith('docs/models/SF-')):continue
    size=int(size)
    target='repository-history/'+commit+'/'+name;entry={'path':target,'source_path':name,'source_commit':commit,'git_blob':oid,'bytes':size}
    if size>8*1024*1024 or used+size>cap:entry['status']='deferred_collection_size_budget'
    else:
     b=git(repo,'cat-file','blob',oid);p=out/target;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);used+=len(b);entry.update(status='copied',sha256=digest(b))
    inventory.append(entry)
   members=inventory[start:];copied=sum(x['status']=='copied' for x in members)
   history.append({'source_commit':commit,'status':'historical_sources_collected' if copied==len(members) else 'historical_sources_partially_collected','copied_members':copied,'deferred_members':len(members)-copied})
  except subprocess.CalledProcessError as e:history.append({'source_commit':commit,'status':'explicitly_deferred_missing_git_object','reason':e.stderr.decode(errors='replace').strip()})
 save(out/'repository-inventory.json',{'recorded_at':stamp(),'head':head,'members':inventory,'historical_commits':history,'copied_bytes':used,'budget_bytes':cap})
 save(out/'selected-studies.json',studies)
 with (out/'RECONCILIATION.csv').open('w',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['study_id','slug','state','gate','published_records','finding','next_action'])
  for s in studies:w.writerow([s['id'],s['slug'],s['state'],s['gate'],len(s['records']),s.get('finding',''),s.get('next_action','')])
 legacy=json.loads((ROOT/'LEGACY-ENDPOINTS.json').read_text());availability=[]
 for r in legacy['rows']:
  p=Path(r['field_path']);availability.append({'field':r['stage'],'path':str(p),'expected_sha256':r['sha256'],'exists':p.is_file(),'bytes':p.stat().st_size if p.is_file() else None,'hash_replayed':False,'scope':'Existence/size only; missing files may be in existing verified archives. No automatic download or physical rejection.'})
 anchors=json.loads((ROOT/'ANCHORS.json').read_text())
 for key,root in [('Q2',q2_run),('Q8',q8_run)]:
  p=Path(root)/anchors[key]['checkpoint'];availability.append({'field':key,'path':str(p),'expected_sha256':anchors[key]['checkpoint_sha256'],'exists':p.is_file(),'bytes':p.stat().st_size if p.is_file() else None,'hash_replayed':False})
 save(out/'local-field-availability.json',{'recorded_at':stamp(),'fields':availability});shutil.copytree(ROOT,out/'handover',ignore=shutil.ignore_patterns('__pycache__'))
 record={'recorded_at':stamp(),'status':'complete_pending_review','source_commit':head,'package_sha256':digest((ROOT/'SHA256SUMS').read_bytes()),'study_ids':[s['id'] for s in studies],'copied_members':sum(i['status']=='copied' for i in inventory),'deferred_members':[i for i in inventory if i['status']!='copied'],'scientific_questions':['Which exact seeds/final curves were established for Q22/Q18?','Were old static cell endpoints readmitted under the current D4 action?','Are energy normalization and mesh/domain effects separated?','Does any retained evidence establish a genuine physical instability or only unresolved preparation?'],'decisions':{'Q17_Q32_full_campaign':'deferred','Q22_pair':'conditional_pilot_contract_not_executed','Q18_hyperbolic':'secondary_pending_Q22_and_identity_reconciliation','motion_hypothesis':'See scientific assessment and optional read-only instantaneous probes; no stability result inferred'},'relaxation_steps':0,'physical_time_steps':0,'new_model_terms':False,'limits':['Metadata/text reconciliation; not a fresh Q22/Q18 full-field replay','Binary omissions and missing local fields are explicit','A frozen-field acceleration fit is not a stability proof or a gate replacement']}
 save(out/'COLLECTION.json',record);report(out);seal(out);return record
