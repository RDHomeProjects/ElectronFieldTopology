"""Standard-library IO, checksums and process identity helpers."""
import hashlib,json,os,zipfile
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
GIB=1024**3

def stamp():
 now=datetime.now(timezone.utc);return {'utc':now.isoformat(),'melbourne':now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def need(value,message):
 if not value:raise RuntimeError(message)
def load(path):return json.loads(Path(path).read_text())
def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
 with tmp.open('w') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 tmp.replace(path)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
 return h.hexdigest()
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def log(message,**kw):print(json.dumps({'recorded_at':stamp(),'message':message,**kw},allow_nan=False),flush=True)
def safe(name):
 p=PurePosixPath(name);return bool(name and not p.is_absolute() and '..' not in p.parts and '\\' not in name and '\n' not in name and '\r' not in name)
def manifest(root):
 root=Path(root);files=sorted(p for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS' and '__pycache__' not in p.parts)
 (root/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in files))
def verify_manifest(root):
 root=Path(root);items={}
 for line in (root/'SHA256SUMS').read_text().splitlines():
  digest,name=line.split('  ',1);need(safe(name) and name not in items,'Unsafe/duplicate manifest path');need(sha(root/name)==digest,'Package checksum differs: '+name);items[name]=digest
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS' and '__pycache__' not in p.parts}
 need(set(items)==actual,'Package checksum coverage differs');return len(items)
def verify_zip(path,expected=None):
 if expected:need(sha(path)==expected,'Evidence archive identity differs: '+str(path))
 with zipfile.ZipFile(path) as z:
  names=z.namelist();need(len(names)==len(set(names)) and all(safe(n) for n in names),'Archive has unsafe/duplicate names');need(z.testzip() is None,'Archive CRC failure');items={}
  for line in z.read('SHA256SUMS').decode().splitlines():
   digest,name=line.split('  ',1);need(safe(name) and name not in items and name!='SHA256SUMS','Unsafe manifest entry');need(hashlib.sha256(z.read(name)).hexdigest()==digest,'Compact checksum differs: '+name);items[name]=digest
  need(set(items)|{'SHA256SUMS'}==set(names),'Compact checksum coverage differs')
 return items
def host():
 values={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if len(line.split())>1 and line.split()[1].isdigit()}
 return {k:values[n]/GIB for k,n in [('total_gib','MemTotal'),('available_gib','MemAvailable'),('swap_free_gib','SwapFree')]}
def process_identity(pid):
 try:
  value=Path('/proc',str(pid),'stat').read_text();parts=value[value.rfind(')')+2:].split()
  return None if parts[0]=='Z' else {'pid':pid,'start_ticks':parts[19],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
 except (OSError,ProcessLookupError):return None
def alive(row):return bool(row and row.get('process_identity') and process_identity(row['pid'])==row['process_identity'])

# This package inventories data; it does not inherit a scientific execution plan.
def verify_package():return {'package_files':verify_manifest(ROOT),'package_sha256':sha(ROOT/'SHA256SUMS')}
