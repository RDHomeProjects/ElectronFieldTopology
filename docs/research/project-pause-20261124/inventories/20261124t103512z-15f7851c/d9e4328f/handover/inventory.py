"""Read-only scientific file inventory; no upload, deletion or optimization."""
import argparse,csv,gzip,hashlib,io,json,os,platform,re,signal,sqlite3,stat,subprocess,sys,time,uuid,zipfile
from pathlib import Path
from datetime import datetime,timezone
from common import ROOT,load,save,sha,stamp,need,log,verify_package,verify_zip,alive

SKIP_DIRS={'.git','.venv','venv','env','__pycache__','node_modules','.cache','.pytest_cache','.mypy_cache','.ruff_cache','.tox','.nox','.npm','.local','.config','.ssh','.gnupg','.mozilla','.vscode','.idea','lost+found'}
PREFIXES=('electronfieldtopology','matter-waves','matterwaves','matter waves','matter_waves')
GIB=1024**3

def named(p):return p.name.lower().startswith(PREFIXES)
def credential_candidate(p):return p.name in ['.env','auth.json','credentials.json'] or p.name.startswith('.env.') or p.suffix.lower() in ['.key','.pem','.p12','.pfx','.jks','.keystore']
def signature(p):
    s=p.stat(follow_symlinks=False);return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def public_url(value):
    value=re.sub(r'(https?://)[^/@]+@',r'\1',value)
    return value.split('?',1)[0].split('#',1)[0]
def command(args,cwd=None):
    r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),timeout=60)
    return {'ok':r.returncode==0,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()[:1000]}

def discover(home,extra,skip,depth=6):
    home=Path(home).resolve();roots=[];links=[];issues=[]
    for directory,dirs,files in os.walk(home,topdown=True,followlinks=False,onerror=lambda e:issues.append(str(e))):
        parent=Path(directory);level=len(parent.relative_to(home).parts)
        keep=[]
        for name in dirs:
            p=parent/name
            if p.resolve() in skip or name in SKIP_DIRS:continue
            if p.is_symlink():
                if named(p):links.append({'path':str(p),'target':os.readlink(p),'reason':'Named directory symlink not followed; add actual target with --root if needed'})
                continue
            if named(p):roots.append(p);continue
            if level<depth:keep.append(name)
        dirs[:]=keep
        for name in files:
            p=parent/name
            if named(p) and p.resolve() not in skip and not p.is_symlink():roots.append(p)
    for p in extra:
        p=Path(p).expanduser().resolve();need(p.exists(),'Additional root missing: '+str(p));need(p!=home,'Use --root for a project directory, not the entire home directory');roots.append(p)
    unique=[]
    for p in sorted(set(roots),key=lambda p:(len(p.parts),str(p))):
        if p.resolve() in skip:continue
        if not any(q.is_dir() and q in p.parents for q in unique):unique.append(p)
    return unique,links,issues

def file_stream(roots,skip,excluded,links,errors,repositories):
    for i,root in enumerate(roots):
        rid=f'root-{i:04d}'
        if root.is_file():
            if not credential_candidate(root):yield rid,root,root.name
            else:excluded.append({'path':str(root),'reason':'credential_candidate'})
            continue
        for directory,dirs,files in os.walk(root,topdown=True,followlinks=False,onerror=lambda e:errors.append(str(e))):
            parent=Path(directory)
            if (parent/'.git').exists():repositories.add(parent)
            keep=[]
            for name in dirs:
                p=parent/name
                if name in SKIP_DIRS or p.resolve() in skip:
                    excluded.append({'path':str(p),'reason':'git_metadata' if name=='.git' else 'rebuildable_runtime_or_explicit_output_exclusion'});continue
                if p.is_symlink():links.append({'path':str(p),'target':os.readlink(p),'reason':'symlink_not_followed'});continue
                keep.append(name)
            dirs[:]=keep
            for name in sorted(files):
                p=parent/name
                if name=='.git' or credential_candidate(p):excluded.append({'path':str(p),'reason':'git_pointer_or_credential_candidate'});continue
                if p.is_symlink():links.append({'path':str(p),'target':os.readlink(p),'reason':'symlink_not_followed'});continue
                try:
                    if not stat.S_ISREG(p.stat(follow_symlinks=False).st_mode):excluded.append({'path':str(p),'reason':'not_a_regular_file'});continue
                except OSError as exc:errors.append(str(exc));continue
                yield rid,p,p.relative_to(root).as_posix()

def hash_file(path,db,progress):
    before=signature(path);old=db.execute('select signature,sha256,crc from cache where path=?',(str(path),)).fetchone()
    key=json.dumps(before)
    if old and old[0]==key and old[1] and old[2] in ['passed','not_a_zip_container']:return old[1],old[2],True,before
    digest=hashlib.sha256();count=0
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024**2),b''):digest.update(chunk);count+=len(chunk);progress(path,count,before[2])
    crc='not_a_zip_container'
    if path.suffix.lower() in ['.npz','.zip']:
        try:
            with zipfile.ZipFile(path) as z:
                members=[i for i in z.infolist() if not i.is_dir()];expanded=sum(i.file_size for i in members);read=0
                for member in members:
                    with z.open(member) as stream:
                        for chunk in iter(lambda:stream.read(4*1024**2),b''):read+=len(chunk);progress(path,read,expanded,'zip_npz_crc_expanded_bytes')
                crc='passed'
        except (OSError,RuntimeError,zipfile.BadZipFile) as exc:crc='failed: '+str(exc)
    after=signature(path);need(before==after,'File changed during inventory: '+str(path));value=digest.hexdigest()
    db.execute('insert or replace into cache values(?,?,?,?)',(str(path),key,value,crc));db.commit();return value,crc,False,before

def git_record(repo):
    def git(*args):return command(['git','-C',str(repo),*args])
    origin=git('remote','get-url','origin');head=git('rev-parse','HEAD');branch=git('branch','--show-current');status=git('status','--porcelain=v1','--untracked-files=normal');refs=git('for-each-ref','--format=%(refname) %(objectname)')
    return {'path':str(repo),'origin':public_url(origin['stdout']) if origin['ok'] else None,'head':head['stdout'] if head['ok'] else None,'branch':branch['stdout'] if branch['ok'] else None,'status_porcelain':status['stdout'],'refs':refs['stdout'].splitlines(),'read_errors':[r['stderr'] for r in [origin,head,branch,status,refs] if not r['ok']],'git_object_bundles_created':False,'dirty_files_not_yet_archived':bool(status['stdout'])}

def check_liveness(roots):
    active=[]
    for root in roots:
        if not root.is_dir():continue
        artifacts=root/'artifacts'
        if not artifacts.is_dir():continue
        for directory,dirs,files in os.walk(artifacts,followlinks=False):
            dirs[:]=[n for n in dirs if n not in SKIP_DIRS and not (Path(directory)/n).is_symlink()]
            for name in ['heartbeat.json','supervisor.json','worker-launch.json']:
                if name not in files:continue
                p=Path(directory)/name
                try:
                    row=load(p)
                    if alive(row):active.append({'record':str(p),'pid':row['pid']})
                except (OSError,ValueError,KeyError):pass
    return active

def field_references(manifests,by_path,by_hash):
    result=[];errors=[]
    for p in manifests:
        try:
            doc=load(p)
            if not isinstance(doc,dict) or not isinstance(doc.get('fields'),list):continue
            for item in doc['fields']:
                if not isinstance(item,dict) or not isinstance(item.get('path'),str) or not re.fullmatch('[0-9a-f]{64}',str(item.get('sha256',''))):continue
                target=Path(item['path']).expanduser();target=target if target.is_absolute() else p.parent/target;key=str(target.resolve());match=by_path.get(key);digest=item['sha256']
                state='present_at_declared_path' if match and match['sha256']==digest else 'present_elsewhere_same_hash' if digest in by_hash else 'not_found_as_individual_file'
                result.append({'manifest':str(p),'declared_path':item['path'],'sha256':digest,'state':state,'available_example':match['path'] if state=='present_at_declared_path' else by_hash.get(digest,{}).get('example')})
        except (ValueError,OSError) as exc:errors.append({'manifest':str(p),'error':str(exc)})
    return result,errors

def write_restart(out,summary,repos,required):
    state=load(ROOT/'KNOWN-STATE.json');primary=state['primary_restart'];status=summary['status']
    lines=['# Matter Waves / Electron Field Topology — pause and restart record','',f"Generated UTC {summary['recorded_at']['utc']}; Melbourne {summary['recorded_at']['melbourne']}.",'',f"Inventory ID: `{summary['inventory_id']}`. Inventory status: **{status}**.",'', '**Archive state: inventory and restart documentation only. Full scientific data have not been uploaded by this operation. No pause tag/release or repository read-only archive has been created.**','', '## Scientific stopping point','',state['scientific_summary'],'',f"Latest assessed run: `{state['latest_run_id']}`. Its source CPU run is `{state['source_run_id']}`.",'',f"Primary chronological continuation: final CG endpoint, native iteration **{primary['native_iteration']}**, force {primary['force']:.10g}, maximum acceleration {primary['acceleration_max']:.10g}.",'',f"Logical numerical-checkout-relative path: `{primary['relative_path']}`.",'',f"SHA256: `{primary['sha256']}`.",'','The best CG checkpoint at native iteration 663 is retained separately and must not be substituted silently. The descent endpoint, CPU 177³/193³ source endpoints, Q2 reference, optimizer memories and historical fields are also retention candidates. Existing Q2–Q32 results remain candidate-specific; unresolved endpoints are not physical exclusions.','', 'The gate limits remain relative force 1e-4 and maximum acceleration 1e-3, together with inherited representation, charge, unit-vector and boundary checks. All latest observed representation/boundary gates passed; stationarity did not. No physical-time evolution or coupled-grid evolution was conducted.','', '## Scope of this inventory','',f"{summary['files']} regular files; {summary['logical_bytes']/GIB:.3f} GiB of logical file content; {summary['unique_content_bytes']/GIB:.3f} GiB after exact-content deduplication, before packaging overhead. Hashing does not remove duplicates.",'', 'ROOTS.json records every selected file/directory. FILES.jsonl.gz and FILES.csv.gz contain original paths, relative mappings, sizes, SHA256 and ZIP/NPZ CRC outcomes. Discovery searches for project-name prefixes under the home directory to a declared depth; explicitly supplied --root locations extend that scope. It does not prove that arbitrarily renamed or externally mounted datasets are covered.','', 'EXCLUSIONS.json, SYMLINKS.json and UNASSIGNED-DOWNLOADS.json must be reviewed before selecting the final archive. Symlinks are not followed automatically. Runtime environments and Git internals are excluded from data hashing; recreate environments from locks and preserve Git history separately. Generic evidence ZIPs in Downloads are listed for assignment, not assumed to belong to this project.','', 'FIELD-REFERENCES.json checks standard on-disk FIELD-MANIFEST.json declarations. A missing individual file may be inside an existing archive or deliberately retired; no conclusion of data loss is made automatically. Nested archive field declarations are not exhaustively expanded by this inventory.','', '## Required recent checkpoints','', '| Role | Availability | Example path |','|---|---|---|']
    for row in required:lines.append('| '+row['label']+' | '+row['state']+' | '+str(row.get('available_example') or 'Review required').replace('|','\\|')+' |')
    lines+=['','## Code and environment recovery','', 'REPOSITORIES.json records all discovered repository heads, branches, refs, worktree status and sanitized origin URLs. The working numerical checkout need not be on the latest main commit. Before considering the pause archive complete, capture local-only refs in Git bundles and preserve dirty/untracked project files identified by this inventory. A source tag alone does not preserve ignored artifacts or commits available only locally.','', 'Known tested numerical runtime: Python 3.12.14, float64; NVIDIA RTX 2080 Super Max-Q; CuPy 14.2.0 at the latest qualification. CPU-only operation remains possible. Restore the recorded pyproject.toml/uv.lock and numerical-source hashes; do not upgrade dependencies as part of a continuation by accident. Current launcher/OS/driver observations are in ENVIRONMENT.json. Do not copy or publish account credentials to recreate the environment.','', '## Complete the archive before cleanup','', '1. Review every discovery exclusion, external symlink, generic download and missing field declaration. Add actual scientific paths with --root and rerun inventory as needed.','2. Record this document and the inventory metadata through the separate publication checkout. Preserve the known assessment supplied alongside it.','3. Create source/history snapshots and full-data release assets, with a path-restoration map and per-file hashes. The next packaging step must consume the inventory rather than guessing from directory names.','4. Upload from the zbook, download the assets into a fresh directory, reconstruct them and verify every retained file. Confirm a selected NPZ loads and matches its declared optimizer state without running relaxation.','5. Record the final pause commit, tag, release URL and restore-verification receipt in an additive archive-completion record. Retain an independent backup. Only then consider cleanup or optionally making the GitHub repository read-only.','', 'No local fields are safe to delete merely because this inventory documentation is merged. Archive completion and restore verification are separate, pending steps.','', '## Resume later','', '1. Read the pause record and final archive-completion receipt before selecting a source. Unarchive the repository first if it was made read-only.','2. Obtain the tagged source and any Git bundles; restore full data using the stored path map. Verify both asset and per-file hashes.','3. Recreate the pinned environment and qualify the selected CPU/GPU backend against the original discrete energy and gradient. Absolute paths and old .git run pointers may need reconstruction; do not invoke an old completed-run resume command blindly.','4. Use the declared final CG native-665 state for chronological continuation. Keep native-663 best, the descent arm and incoming CPU endpoints separately labelled. The intended next study was a bounded noise-aware CG control plus read-only coarse-exterior reconstruction tests before any composite-grid evolution.','5. Compare restored source measurements with the sealed record before authorizing new optimizer or physical-time work.','', 'This pause procedure runs no scientific simulation and changes no scientific gates.']
    (out/'PAUSE-AND-RESUME.md').write_text('\n'.join(lines)+'\n')

def run(home,repo,extra,destination,publication,resume=None):
    verify_package();home=Path(home).resolve();repo=Path(repo).resolve();destination=Path(destination).resolve();need(repo.is_dir(),'Numerical checkout missing; supply --repo with its actual location')
    skip={ROOT.resolve(),destination,Path(publication).resolve()};roots,links,discovery_errors=discover(home,extra,skip)
    need(roots,'No named project files found; supply --root for actual project directories')
    running=check_liveness(roots);need(not running,'Project workers are still alive; stop them using their existing handover before inventory: '+json.dumps(running))
    if resume:
        out=Path(resume).resolve();identity=load(out/'identity.json');need(identity['package_sha256']==sha(ROOT/'SHA256SUMS'),'Inventory package changed');need(identity['home']==str(home) and identity['repo']==str(repo),'Inventory identity changed')
    else:
        rid=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+uuid.uuid4().hex[:8];out=destination/rid;out.mkdir(parents=True);save(out/'identity.json',{'recorded_at':stamp(),'inventory_id':rid,'home':str(home),'repo':str(repo),'package_sha256':sha(ROOT/'SHA256SUMS')})
    save(destination/'LATEST.json',{'output':str(out),'recorded_at':stamp()});save(out/'ROOTS.json',{'recorded_at':stamp(),'roots':[{'id':f'root-{i:04d}','path':str(p),'kind':'directory' if p.is_dir() else 'file'} for i,p in enumerate(roots)],'discovery_depth':6,'prefixes':list(PREFIXES),'discovery_excluded_directory_names':sorted(SKIP_DIRS),'outside_home_automatically_scanned':False,'additional_roots':[str(p) for p in extra],'discovery_errors':discovery_errors})
    save(out/'status.json',{'recorded_at':stamp(),'status':'inventory_working','output':str(out)});db=sqlite3.connect(out/'HASH-CACHE.sqlite');db.execute('create table if not exists cache(path text primary key,signature text,sha256 text,crc text)');db.commit()
    excluded=[];errors=[];repositories=set();by_path={};by_hash={};file_stamps={};manifests=[];total=0;files=0;cached=0;last=time.monotonic();counts={};began=time.monotonic()
    def progress(p,count,size,phase='sha256_file_bytes'):
        nonlocal last
        if time.monotonic()-last>=15:log('Inventory progress',phase=phase,files_completed=files,current_file=str(p),gib_read=count/GIB,gib_total=size/GIB);last=time.monotonic()
    try:
        with gzip.open(out/'FILES.jsonl.gz','wt',encoding='utf-8',newline='') as j,gzip.open(out/'FILES.csv.gz','wt',encoding='utf-8',newline='') as c:
            writer=csv.DictWriter(c,fieldnames=['root_id','relative_path','path','bytes','sha256','container_crc','cache_reused'],lineterminator='\n');writer.writeheader()
            for rid,p,relative in file_stream(roots,skip,excluded,links,errors,repositories):
                try:
                    digest,crc,reused,sig=hash_file(p,db,progress);row={'root_id':rid,'relative_path':relative,'path':str(p),'bytes':sig[2],'sha256':digest,'container_crc':crc,'cache_reused':reused};j.write(json.dumps(row,ensure_ascii=False)+'\n');writer.writerow(row);files+=1;total+=sig[2];cached+=int(reused);counts[rid]=counts.get(rid,0)+sig[2];by_path[str(p.resolve())]=row;file_stamps[p]=sig
                    if digest not in by_hash:by_hash[digest]={'count':0,'bytes_each':sig[2],'example':str(p)}
                    by_hash[digest]['count']+=1
                    if crc.startswith('failed:'):errors.append({'path':str(p),'error':crc,'file_sha256_retained':True})
                    if p.name.lower()=='field-manifest.json':manifests.append(p)
                    if p.name in ['heartbeat.json','supervisor.json','worker-launch.json']:
                        try:need(not alive(load(p)),'A project worker started during inventory: '+str(p))
                        except (ValueError,KeyError):pass
                    progress(p,sig[2],sig[2])
                except (OSError,RuntimeError,zipfile.BadZipFile) as exc:errors.append({'path':str(p),'error':str(exc)})
        for path,before in file_stamps.items():
            try:
                if signature(path)!=before:errors.append({'path':str(path),'error':'File metadata changed after hashing; repeat inventory while project is idle'})
            except OSError as exc:errors.append({'path':str(path),'error':str(exc)})
        running=check_liveness(roots)
        if running:errors.append({'error':'Project worker became active during inventory','workers':running})
        refs,ref_errors=field_references(manifests,by_path,by_hash);save(out/'FIELD-REFERENCES.json',{'recorded_at':stamp(),'references':refs,'reader_errors':ref_errors,'scope':'Standard on-disk FIELD-MANIFEST.json only; nested archives are not exhaustively expanded'})
        required=[]
        for item in load(ROOT/'KNOWN-STATE.json')['required_fields']:
            expected=str((repo/item['relative_to_numerical_repo']).resolve());at=by_path.get(expected);digest=item['sha256'];state='present_at_expected_path' if at and at['sha256']==digest else 'present_elsewhere_same_hash' if digest in by_hash else 'not_found_as_individual_file'
            required.append({**item,'state':state,'available_example':at['path'] if state=='present_at_expected_path' else by_hash.get(digest,{}).get('example')})
        save(out/'REQUIRED-CHECKPOINTS.json',{'recorded_at':stamp(),'checkpoints':required})
        repo_records=[git_record(p) for p in sorted(repositories)];save(out/'REPOSITORIES.json',{'recorded_at':stamp(),'repositories':repo_records})
        unassigned=[];downloads=home/'Downloads'
        if downloads.is_dir():
            for p in downloads.iterdir():
                if p.is_file() and (p.name.lower().startswith(('evidence','summary','pasted text'))):unassigned.append({'path':str(p),'bytes':p.stat().st_size,'reason':'Generic name; assign to project or mark unrelated before final archive'})
        save(out/'UNASSIGNED-DOWNLOADS.json',{'recorded_at':stamp(),'files':unassigned})
        save(out/'EXCLUSIONS.json',{'recorded_at':stamp(),'excluded':excluded,'source_files_deleted':0});save(out/'SYMLINKS.json',{'recorded_at':stamp(),'symlinks':links});save(out/'ERRORS.json',{'recorded_at':stamp(),'errors':errors})
        with gzip.open(out/'DUPLICATE-HASHES.jsonl.gz','wt') as f:
            for digest,r in sorted(by_hash.items()):
                if r['count']>1:f.write(json.dumps({'sha256':digest,**r})+'\n')
        env={'recorded_at':stamp(),'platform':platform.platform(),'inventory_python':sys.version,'numerical_python':command([str(repo/'.venv/bin/python3'),'--version']) if (repo/'.venv/bin/python3').exists() else None,'uv':command(['uv','--version']) if __import__('shutil').which('uv') else None,'gpu_driver':command(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader']) if __import__('shutil').which('nvidia-smi') else None,'scientific_processes_started':0};save(out/'ENVIRONMENT.json',env)
        summary={'recorded_at':stamp(),'inventory_id':load(out/'identity.json')['inventory_id'],'status':'inventory_complete_review_required' if not errors and not discovery_errors else 'inventory_incomplete_errors_require_review','files':files,'logical_bytes':total,'unique_content_bytes':sum(r['bytes_each'] for r in by_hash.values()),'cached_hashes':cached,'root_bytes':counts,'roots':len(roots),'repositories':len(repo_records),'dirty_repositories':sum(bool(r['status_porcelain']) for r in repo_records),'missing_required_individual_files':sum(r['state']=='not_found_as_individual_file' for r in required),'missing_declared_individual_files':sum(r['state']=='not_found_as_individual_file' for r in refs),'unassigned_downloads':len(unassigned),'symlinks_not_followed':len(links),'errors':len(errors)+len(discovery_errors),'elapsed_seconds':time.monotonic()-began,'full_data_uploaded':False,'repository_archived':False,'scientific_steps':0}
        save(out/'SUMMARY.json',summary);write_restart(out,summary,repo_records,required)
        (out/'SUMMARY.md').write_text('# Matter Waves pause inventory\n\n'+json.dumps(summary,indent=2)+'\n\nRead PAUSE-AND-RESUME.md and the coverage/retention lists before the full-data release is prepared.\n')
        save(out/'status.json',summary);seal(out);log('Pause inventory ready',**summary,output=str(out),restart_document=str(out/'PAUSE-AND-RESUME.md'),evidence=str(out/'inventory-evidence.zip'))
        return out
    except (KeyboardInterrupt,SystemExit):
        save(out/'status.json',{'recorded_at':stamp(),'status':'inventory_interrupted','files_completed':files,'output':str(out),'resume':'Repeat inventory with --resume; unchanged hashes and CRC checks are cached'});log('Inventory interrupted; repeat with --resume',output=str(out));raise
    finally:db.close()

def seal(out):
    files=sorted(p for p in out.iterdir() if p.is_file() and p.name not in ['HASH-CACHE.sqlite','HASH-CACHE.sqlite-journal','SHA256SUMS','inventory-evidence.zip','inventory-evidence.tmp'])
    sums=''.join(sha(p)+'  '+p.name+'\n' for p in files);(out/'SHA256SUMS').write_text(sums)
    with zipfile.ZipFile(out/'inventory-evidence.tmp','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.name)
        z.writestr('SHA256SUMS',sums)
    (out/'inventory-evidence.tmp').replace(out/'inventory-evidence.zip');verify_zip(out/'inventory-evidence.zip')
