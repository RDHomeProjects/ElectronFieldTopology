import hashlib, json, os
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
def stamp():
 t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def save(path,value):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp')
 with tmp.open('w') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 tmp.replace(p)
 directory=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(directory)
 finally:os.close(directory)
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def log(message,**kw):print(json.dumps({'recorded_at':stamp(),'message':message,**kw},allow_nan=False),flush=True)
def need(x,m):
 if not x:raise RuntimeError(m)
def manifest(root):
 fs=sorted(p for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS' and '__pycache__' not in p.parts)
 (root/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in fs))
def verify_manifest(root):
 from pathlib import PurePosixPath
 seen=set()
 for row in (root/'SHA256SUMS').read_text().splitlines():
  h,n=row.split('  ',1);q=PurePosixPath(n)
  need(not q.is_absolute() and '..' not in q.parts and n not in seen and sha(root/n)==h,'Checksum differs: '+n);seen.add(n)
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS' and '__pycache__' not in p.parts}
 need(seen==actual,'Package checksum coverage differs');return len(seen)
