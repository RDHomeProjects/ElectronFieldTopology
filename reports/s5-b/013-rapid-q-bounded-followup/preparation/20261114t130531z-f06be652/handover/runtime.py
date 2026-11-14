import ast,hashlib,json,os,subprocess,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'SETTINGS.json').read_text())
def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def load(p):return json.loads(Path(p).read_text())
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def event(message,**kw):print(json.dumps({'recorded_at':stamp(),'message':message,**kw}),flush=True)
def need(condition,message):
    if not condition:raise RuntimeError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def command(argv,cwd=None,capture=False):
    event('Command',argv=list(map(str,argv)));r=subprocess.run(list(map(str,argv)),cwd=cwd,text=True,capture_output=capture)
    need(r.returncode==0,'Command failed: '+str(argv)+'\n'+(r.stderr or ''));return r.stdout.strip() if capture else r

def package_check():
    covered=set()
    for line in (ROOT/'SHA256SUMS').read_text().splitlines():
        h,n=line.split('  ',1);path=(ROOT/n).resolve();need(path.is_relative_to(ROOT) and n not in covered and path.is_file() and sha(path)==h,'Changed package member: '+n);covered.add(n)
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=ROOT/'SHA256SUMS'};need(covered==actual,'Package inventory differs')
    event('Follow-up package verified',members=len(covered))
def source_check(repo,installed=False):
    manifest=load(ROOT/'BASE-SOURCE.json')
    for name,h in manifest['files'].items():need((repo/'src/electron_field_topology'/name).is_file() and sha(repo/'src/electron_field_topology'/name)==h,'Required SF source missing/different: '+name)
    for name,h in manifest['locks'].items():need(sha(repo/name)==h,'Dependency lock differs: '+name)
    for name,h in CFG['original_code_sha256'].items():
        expected=sha(ROOT/'patches/runner.py') if installed and name=='runner.py' else h
        need(sha(repo/'src/electron_field_topology/rapid_q_screen'/name)==expected,'Screen source differs: '+name)
    text=(repo/'src/electron_field_topology/rapid_q_screen/runner.py').read_text();node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='branch');need(hashlib.sha256(ast.get_source_segment(text,node).encode()).hexdigest()==CFG['branch_function_sha256'],'Existing optimizer branch changed')
    if installed:
        for f in (ROOT/'science').glob('*.py'):need(sha(f)==sha(repo/'src/electron_field_topology/rapid_q_followup'/f.name),'Published follow-up module differs: '+f.name)
    return True

def compact(archive,expected=None):
    if expected:need(sha(archive)==expected,'Compact archive differs: '+str(archive))
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Archive CRC/duplicate failure')
        for n in names:need(not Path(n).is_absolute() and '..' not in Path(n).parts,'Unsafe archive member')
        if 'SHA256SUMS' in names:
            covered=set()
            for line in z.read('SHA256SUMS').decode().splitlines():
                h,n=line.split('  ',1);need(n not in covered and hashlib.sha256(z.read(n)).hexdigest()==h,'Compact checksum mismatch: '+n);covered.add(n)
            need(covered|{'SHA256SUMS'}==set(names),'Compact inventory mismatch')
        return {n:json.loads(z.read(n)) for n in ['record.json','campaign.json','benchmark.json','field-manifest.json'] if n in names}

def inputs():
    screen=compact(ROOT/'data/completed-screen-evidence.zip',CFG['screen_evidence_sha256']);past=compact(ROOT/'data/prior-survey-evidence.zip',CFG['prior_evidence_sha256'])['campaign.json'];return screen,past

def job_sources(screen,past):
    result=[];r=screen['record.json']
    for spec in load(ROOT/'FOLLOWUP.json')['jobs']:
        if spec['source']=='screen':row=next(v for v in r[spec['phase']] if v['seed']['id']==spec['id']);seed=row['seed'];iteration=row['iteration'];metrics=row['metrics'];path=row['checkpoint'];digest=row['checkpoint_sha256'];field_key='n'
        else:
            row=past['rest'][spec['rest_id']];seed=next(v['seed'] for v in r['broad'] if v['seed']['id']==spec['id']);iteration=row['native_result']['iterations'];metrics={**row['latest']['stationarity'],'tail_fraction':row['latest']['tail']['fraction']};path=row['checkpoint'];digest=row['checkpoint_sha256'];field_key='field';need(row['lineage']['seed_sha256']==canonical(seed),'Legacy seed lineage differs')
        need(row['nodes']==spec['nodes'] and row['length']==load(ROOT/'FOLLOWUP.json')['length'],'Job geometry differs from frozen source')
        result.append({**spec,'seed':seed,'start_iteration':iteration,'metrics':metrics,'checkpoint':path,'checkpoint_sha256':digest,'field_key':field_key,'length':row['length']})
    return result

def safe_field(root,relative):
    path=(root/relative).resolve();need(path.is_relative_to(root.resolve()) and path.is_file(),'Missing/unsafe field: '+str(path));return path

def verify_inputs(screen_run,past_run,full=False):
    s,past=inputs();need(sha(screen_run/'evidence.zip')==CFG['screen_evidence_sha256'],'Selected screen run differs');need(sha(past_run/'evidence.zip')==CFG['prior_evidence_sha256'],'Selected original survey differs')
    for name in ['record.json','identity.json','benchmark.json','field-manifest.json']:
        with zipfile.ZipFile(ROOT/'data/completed-screen-evidence.zip') as z:need(sha(screen_run/name)==hashlib.sha256(z.read(name)).hexdigest(),'Original compact run member differs: '+name)
    with zipfile.ZipFile(ROOT/'data/prior-survey-evidence.zip') as z:need(sha(past_run/'campaign.json')==hashlib.sha256(z.read('campaign.json')).hexdigest(),'Original campaign differs')
    jobs=job_sources(s,past);fields={}
    if full:
        for f in s['field-manifest.json']['files']:fields[str(safe_field(screen_run,f['path']))]=f['sha256']
    for job in jobs:
        root=screen_run if job['source']=='screen' else past_run;fields[str(safe_field(root,job['checkpoint']))]=job['checkpoint_sha256']
        if job['source']=='screen':
            folder=(root/job['checkpoint']).parent
            for name in ['latest.npz','latest.seal.json','history.json']:need((folder/name).is_file(),'Missing optimizer continuation payload: '+str(folder/name))
    for name,h in fields.items():
        need(sha(name)==h,'Field checkpoint changed: '+name)
        with zipfile.ZipFile(name) as z:need(z.testzip() is None,'NPZ CRC failure: '+name)
    event('Original evidence and fields verified',full_screen_manifest=full,unique_NPZ_files=len(fields),jobs=len(jobs))
    return s,past,jobs
