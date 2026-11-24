"""Immutable inputs, crash-safe local records and compact sealing."""
from base_common import *
import csv,io

def verify_package():
    count=verify_manifest(ROOT);spec=load(ROOT/'SOURCE.json')
    payloads=verify_zip(ROOT/'data/completed-evidence.zip',spec['evidence_sha256'])
    return {'package_files':count,'source_compact_payloads':len(payloads),'package_sha256':sha(ROOT/'SHA256SUMS')}

def csv_write(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=keys,lineterminator='\n');writer.writeheader();writer.writerows(rows)
    Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(stream.getvalue(),newline='\n')

def seal(out):
    # Exclude only the ROOT checksum manifest; nested package manifests are evidence.
    excluded={'evidence.zip','evidence.tmp','runner.log','telemetry.jsonl','telemetry-latest.json','heartbeat.json','supervisor.json','worker-launch.json','STOP.json'}
    files=sorted(p for p in out.rglob('*') if p.is_file() and p!=out/'SHA256SUMS' and p.name not in excluded and p.suffix not in ['.npz','.tmp'] and '__pycache__' not in p.parts and not any(part.startswith('STOP-retained-') for part in p.parts))
    sums=''.join(sha(p)+'  '+p.relative_to(out).as_posix()+'\n' for p in files)
    (out/'SHA256SUMS').write_text(sums)
    with zipfile.ZipFile(out/'evidence.tmp','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.relative_to(out).as_posix())
        z.writestr('SHA256SUMS',sums)
    (out/'evidence.tmp').replace(out/'evidence.zip');return verify_zip(out/'evidence.zip')

def source_record():
    with zipfile.ZipFile(ROOT/'data/completed-evidence.zip') as z:return json.loads(z.read('record.json'))

def source_endpoint(source,nodes):
    spec=load(ROOT/'SOURCE.json');name=f'cases/cpu-{nodes}/endpoint.npz'
    row=next(r for r in spec['fields'] if r['path']==name);p=source/name
    need(p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'Authenticated endpoint missing/different: '+str(p))
    return p

def source_metrics(nodes):
    record=source_record();row=next(c for c in record['new_cases'] if c['case']['nodes']==nodes)
    return row['final']['metrics']
