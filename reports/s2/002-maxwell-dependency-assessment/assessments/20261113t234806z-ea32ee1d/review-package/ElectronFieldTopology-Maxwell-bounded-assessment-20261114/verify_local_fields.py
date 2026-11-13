"""Read-only full-field integrity verification on the workstation; no metric replay."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args();root=a.run.expanduser().resolve();manifest=json.loads((root/'field-manifest.json').read_text());records=[]
for entry in manifest['files']:
 f=(root/entry['file']).resolve()
 if not f.is_relative_to(root):raise ValueError('Field path outside run')
 h=hashlib.sha256()
 with f.open('rb') as stream:
  for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
 if h.hexdigest()!=entry['sha256'] or f.stat().st_size!=entry['bytes']:raise ValueError('Field hash/size mismatch: '+entry['file'])
 with zipfile.ZipFile(f) as z:
  bad=z.testzip()
  if bad:raise ValueError('NPZ CRC mismatch: '+entry['file']+'/'+bad)
 records.append({'file':entry['file'],'sha256':h.hexdigest(),'bytes':entry['bytes'],'CRC':'passed'})
t=datetime.now(timezone.utc);r={'recorded_at':{'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()},'status':'field_bytes_and_CRC_verified','run':str(root),'count':len(records),'files':records,'scope':'Read-only hashes, sizes and NPZ CRCs; not scientific metric replay or an upload/download archival check.'}
if a.output:
 with a.output.expanduser().open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='files'},indent=2))
