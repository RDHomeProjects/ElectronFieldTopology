import hashlib,json,os
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
def stamp():
 t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def save(path,data):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def log(message,**v):print(json.dumps({'recorded_at':stamp(),'message':message,**v}),flush=True)
def active_jobs():
 found=[];me=os.getpid();ancestors={me};parent=os.getppid()
 while parent>1 and parent not in ancestors:
  ancestors.add(parent)
  try:parent=int(next(v.split()[1] for v in (Path('/proc')/str(parent)/'status').read_text().splitlines() if v.startswith('PPid:')))
  except (FileNotFoundError,StopIteration,PermissionError):break
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name) in ancestors:continue
  try:
   if p.stat().st_uid!=os.getuid():continue
   raw=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   if any(n in raw for n in ['run_measurements.py','run_calibration.py','run_science.py','electron_field_topology.sf_candidate_survey','electron_field_topology.sf_temporal_run','electron_field_topology.sf_time_gpu_run','screen_worker.py']):
    if 'screen_worker.py' in raw and ('--status' in raw or 'resource-scan' in raw):continue
    # Ignore command text belonging to shell/inspection tools, not compute workers.
    executable=raw.split(' ',1)[0]
    if ('python' in executable or executable.endswith('/uv')):found.append({'pid':int(p.name),'executable':Path(executable).name})
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
 return found

def memory_guard(minimum_gib):
 info=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines());available=int(info['MemAvailable'].split()[0])/1024**2
 if available<minimum_gib:raise RuntimeError(f'Available host RAM {available:.2f} GiB below {minimum_gib} GiB start reserve')
 return available
