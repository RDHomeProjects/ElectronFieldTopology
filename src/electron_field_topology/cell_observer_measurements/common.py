import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
def stamp():
 t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def save(path,value):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');t.replace(p)
def load(path):return json.loads(Path(path).read_text())
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
 return h.hexdigest()
def checkpoint(out,name,fn):
 p=out/'measurements'/(name+'.json');seal=p.with_suffix('.sha256')
 if p.exists():
  if not seal.exists() or seal.read_text().strip()!=sha(p):raise ValueError('Changed measurement checkpoint: '+str(p))
  return load(p)
 v=fn();save(p,v);seal.write_text(sha(p)+'\n');return v
