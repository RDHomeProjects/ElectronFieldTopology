"""Local-only GitHub archive transaction, verified parts, and guarded cleanup."""
import csv,gzip,hashlib,io,json,os,shutil,subprocess,sys,tempfile,time,zipfile
from pathlib import Path,PurePosixPath
from common import ROOT,load,save,sha,stamp,need,log,verify_manifest,verify_zip,alive
from capsule import partition,make_part,inspect_part,checkpoint_check,exact_unlink,no_symlinks,signature
GIB=1024**3
SPEC=load(ROOT/'ARCHIVE.json');REPO=SPEC['repository'];REMOTE=SPEC['remote']

def checked(cmd,cwd=None,capture=True,strip=True):
    log('Archive command',argv=cmd,working_directory=str(cwd) if cwd else None)
    r=subprocess.run(cmd,cwd=cwd,capture_output=capture,text=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
    need(r.returncode==0,'Command failed: '+repr(cmd[:5])+('\n'+r.stderr if capture else ''));return (r.stdout.strip() if strip else r.stdout) if capture else None

def api(path):return json.loads(checked(['gh','api',path]))
def release(tag):
    value=api('repos/'+REPO+'/releases/tags/'+tag);assets=[];page=1
    while True:
        batch=api(f'repos/{REPO}/releases/{value["id"]}/assets?per_page=100&page={page}');assets+=batch
        if len(batch)<100:break
        page+=1
    names=[a['name'] for a in assets];need(len(names)==len(set(names)),'Duplicate release asset names');value['assets']=assets;return value

def verify_package():
    need(sha(ROOT/'data/inventory-evidence.zip')==SPEC['inventory_sha256'],'Inventory identity differs');count=verify_manifest(ROOT);verify_zip(ROOT/'data/inventory-evidence.zip');return count

def inventory():
    with zipfile.ZipFile(ROOT/'data/inventory-evidence.zip') as z:
        read=lambda n:json.loads(z.read(n));summary=read('SUMMARY.json');need(summary['errors']==0 and summary['missing_required_individual_files']==0 and summary['missing_declared_individual_files']==0,'Source inventory has unresolved file errors')
        with gzip.GzipFile(fileobj=io.BytesIO(z.read('FILES.jsonl.gz'))) as stream:rows=[json.loads(line) for line in stream]
        return rows,read('ROOTS.json')['roots'],read('REPOSITORIES.json')['repositories'],read('SYMLINKS.json')['symlinks']

def safe_rows(rows,roots,home):
    root_by={r['id']:r for r in roots};seen=set()
    for row in rows:
        p=Path(row['path']);relative=PurePosixPath(row['relative_path']);r=root_by[row['root_id']];base=Path(r['path'])
        need(p.is_absolute() and home in p.parents and p not in seen and '.git' not in p.parts,'Unsafe or duplicate inventory path');need(not relative.is_absolute() and '..' not in relative.parts,'Unsafe relative inventory path')
        expected=base/row['relative_path'] if r['kind']=='directory' else base;need(p==expected,'Inventory root/path mapping differs');need(len(row['sha256'])==64 and all(c in '0123456789abcdef' for c in row['sha256']),'Invalid data hash');seen.add(p)

def assert_idle(rows):
    for row in rows:
        p=Path(row['path'])
        if p.name not in ['heartbeat.json','supervisor.json','worker-launch.json'] or not p.exists():continue
        try:need(not alive(load(p)),'An inventoried scientific worker is alive: '+str(p))
        except (ValueError,KeyError):pass
    # Include workers whose heartbeat was created after the frozen inventory.
    for folder in Path('/proc').glob('[0-9]*'):
        try:
            args=(folder/'cmdline').read_bytes().split(b'\0');text=' '.join(x.decode(errors='replace') for x in args)
            python=bool(args and Path(args[0].decode(errors='replace')).name.startswith('python'))
            science=python and (any(x==b'electron_field_topology' or x.startswith(b'electron_field_topology.') for x in args) or any(Path(x.decode(errors='replace')).name in ['worker.py','screen_worker.py'] and ('ElectronFieldTopology' in text or 'Matter-Waves' in text) for x in args))
            need(not science,'Scientific worker is running; leave source records intact: PID '+folder.name)
        except (OSError,ProcessLookupError):pass

def git_snapshot(repo):
    head=checked(['git','-C',str(repo),'rev-parse','HEAD']);dirty=checked(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']);need(not dirty,'Tracked source files changed; retain them and update inventory: '+str(repo))
    tracked=checked(['git','-C',str(repo),'ls-files','-z'],strip=False);paths=set()
    for name in tracked.split('\0'):
        if name:paths.add(str(repo/name))
    refs=checked(['git','-C',str(repo),'for-each-ref','--format=%(refname) %(objectname)']);return head,paths,refs

def classify(path,tracked,roots):
    if str(path) in tracked:return 'keep_git_tracked'
    if any(name in ['.git','.venv','venv','__pycache__'] or name.endswith('-browser-env') for name in path.parts):return 'keep_runtime_or_git_metadata'
    if '.git' in path.parts:return 'keep_git_metadata'
    return 'delete_verified_project_download' if Path(SPEC['home'])/'Downloads' in path.parents else 'delete_verified_untracked_record'

def prepare(work,repo):
    verify_package();need(os.geteuid()!=0 and Path.home()==Path(SPEC['home']),'Run as the inventoried rd account, without sudo');work.mkdir(parents=True,exist_ok=True)
    if (work/'PLAN.json.gz').exists():return read_plan(work)
    need(shutil.disk_usage(work).free>=SPEC['minimum_free_disk_gib']*GIB,'Require 20 GiB free for bounded part/restore staging')
    rows,roots,repositories,links=inventory();safe_rows(rows,roots,Path(SPEC['home']));assert_idle(rows)
    need(work!=Path(SPEC['home']) and Path(SPEC['home']) in work.parents,'Archive work must be a separate directory under the inventoried home')
    need(not any(Path(r['path'])==work or Path(r['path']) in work.parents or work in Path(r['path']).parents for r in roots),'Archive work must not overlap inventoried roots');no_symlinks(work)
    objects={};tracked=set();git_records=[];(work/'git').mkdir(exist_ok=True)
    for i,entry in enumerate(repositories):
        path=Path(entry['path']);head,paths,refs=git_snapshot(path);need(head==entry['head'],'Source checkout HEAD changed since inventory: '+str(path));tracked|=paths;bundle=work/'git'/f'repository-{i:03d}.bundle'
        if not bundle.exists():
            temporary=bundle.with_suffix('.tmp');temporary.unlink(missing_ok=True);checked(['git','-C',str(path),'bundle','create',str(temporary),'--all','HEAD']);checked(['git','-C',str(path),'bundle','verify',str(temporary)]);temporary.replace(bundle)
        checked(['git','-C',str(path),'bundle','verify',str(bundle)]);digest=sha(bundle);objects[digest]={'bytes':bundle.stat().st_size,'source':str(bundle),'kind':'git_bundle'};git_records.append({'source':str(path),'head':head,'refs':refs,'bundle_sha256':digest,'bundle_name':bundle.name})
    # Pin main using an isolated clone, never a reset or fetch in a scientific checkout.
    snapshot=work/'source-snapshot'
    if not snapshot.exists():checked(['git','clone','--no-hardlinks','--no-checkout',str(repo),str(snapshot)]);checked(['git','-C',str(snapshot),'remote','set-url','origin',REMOTE])
    checked(['git','-C',str(snapshot),'fetch','origin','refs/heads/main:refs/remotes/origin/main']);base=checked(['git','-C',str(snapshot),'rev-parse','origin/main']);main_bundle=work/'git/current-main.bundle'
    if main_bundle.exists():need(checked(['git','-C',str(snapshot),'bundle','list-heads',str(main_bundle)]).split()[0]==base,'A prior interrupted snapshot has a different main commit; keep it and use a new --work directory')
    else:
        temporary=main_bundle.with_suffix('.tmp');temporary.unlink(missing_ok=True);checked(['git','-C',str(snapshot),'bundle','create',str(temporary),'refs/remotes/origin/main']);checked(['git','-C',str(snapshot),'bundle','verify',str(temporary)]);temporary.replace(main_bundle)
    digest=sha(main_bundle);objects[digest]={'bytes':main_bundle.stat().st_size,'source':str(main_bundle),'kind':'git_bundle'};git_records.append({'source':'current-origin-main','head':base,'refs':'refs/remotes/origin/main '+base,'bundle_sha256':digest,'bundle_name':main_bundle.name})
    groups={}
    for row in rows:groups.setdefault(row['sha256'],[]).append(row)
    for i,(digest,aliases) in enumerate(sorted(groups.items())):
        source=None
        for row in aliases:
            p=Path(row['path'])
            if not p.exists():continue
            no_symlinks(p)
            if p.stat().st_size==row['bytes'] and sha(p)==digest:source=p;break
        need(source is not None,'No unchanged source remains for content '+digest+'; no cleanup is permitted');objects[digest]={'bytes':aliases[0]['bytes'],'source':str(source),'kind':'inventoried_file'}
        if i%100==0:log('Source content confirmed',unique_objects_checked=i+1,total=len(groups))
    primary=next(g for g in git_records if g['source']==str(repo));fingerprint=hashlib.sha256(('\n'.join(sorted(objects))+'\n'+base).encode()).hexdigest()[:8];tag='pause-20261124-'+SPEC['inventory_id'].split('-')[-1]+'-'+fingerprint
    for row in rows:row['cleanup_action']=classify(Path(row['path']),tracked,roots)
    plan={'recorded_at':stamp(),'inventory_sha256':SPEC['inventory_sha256'],'inventory_id':SPEC['inventory_id'],'home':SPEC['home'],'package_sha256':sha(ROOT/'SHA256SUMS'),'main_commit':base,'tag':tag,'roots':roots,'symlinks':links,'files':rows,'objects':objects,'git':git_records,'primary_git':primary,'parts':partition(objects,SPEC['part_uncompressed_limit']),'required':load(ROOT/'KNOWN-STATE.json')['required_fields'],'source_snapshot':str(snapshot)}
    with gzip.open(work/'PLAN.json.gz','wt') as f:json.dump(plan,f,sort_keys=True,allow_nan=False)
    save(work/'IDENTITY.json',{'recorded_at':stamp(),'inventory_sha256':SPEC['inventory_sha256'],'package_sha256':sha(ROOT/'SHA256SUMS'),'plan_sha256':sha(work/'PLAN.json.gz'),'tag':tag,'main_commit':base})
    with gzip.open(work/'CLEANUP-PLAN.csv.gz','wt',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['path','bytes','sha256','action'])
        for row in rows:w.writerow([row['path'],row['bytes'],row['sha256'],row['cleanup_action']])
    summary={'recorded_at':stamp(),'status':'prepared_not_uploaded','tag':tag,'files':len(rows),'unique_objects':len(objects),'part_count':len(plan['parts']),'logical_gib':sum(r['bytes'] for r in rows)/GIB,'unique_payload_gib':sum(o['bytes'] for o in objects.values())/GIB,'planned_delete_files':sum(r['cleanup_action'].startswith('delete') for r in rows),'planned_delete_gib':sum(r['bytes'] for r in rows if r['cleanup_action'].startswith('delete'))/GIB,'planned_downloads_files':sum(r['cleanup_action']=='delete_verified_project_download' for r in rows),'full_data_verified':False,'source_files_deleted':0};save(work/'STATUS.json',summary);log('Archive plan prepared',**summary);return plan

def read_plan(work):
    identity=load(work/'IDENTITY.json');need(identity['inventory_sha256']==SPEC['inventory_sha256'] and identity['package_sha256']==sha(ROOT/'SHA256SUMS'),'Archive job identity differs');need(identity['plan_sha256']==sha(work/'PLAN.json.gz'),'Archive plan changed')
    with gzip.open(work/'PLAN.json.gz','rt') as f:return json.load(f)

def download(tag,name,directory):
    directory.mkdir(parents=True,exist_ok=True);need(not (directory/name).exists(),'Download destination must be fresh');checked(['gh','release','download',tag,'--repo',REPO,'--pattern',name,'--dir',str(directory)],capture=False);need((directory/name).is_file(),'Expected downloaded asset missing');return directory/name

def ensure_release(plan):
    snap=Path(plan['source_snapshot']);tag=plan['tag'];r=subprocess.run(['git','-C',str(snap),'ls-remote','--tags','origin','refs/tags/'+tag,'refs/tags/'+tag+'^{}'],capture_output=True,text=True);need(r.returncode==0,'Cannot check remote pause tag')
    if r.stdout.strip():
        lines=[line.split() for line in r.stdout.splitlines()];commit=next((x[0] for x in lines if x[1].endswith('^{}')),lines[0][0]);need(commit==plan['main_commit'],'Existing pause tag points elsewhere')
    else:
        existing=subprocess.run(['git','-C',str(snap),'rev-parse','--verify','refs/tags/'+tag],capture_output=True,text=True)
        if existing.returncode==0:need(checked(['git','-C',str(snap),'rev-parse',tag+'^{commit}'])==plan['main_commit'],'Local pause tag points elsewhere')
        else:checked(['git','-C',str(snap),'tag','-a',tag,plan['main_commit'],'-m','Matter Waves pause archive; inventory '+SPEC['inventory_id']])
        checked(['git','-C',str(snap),'push','origin','refs/tags/'+tag])
    probe=subprocess.run(['gh','api','repos/'+REPO+'/releases/tags/'+tag],capture_output=True,text=True)
    if probe.returncode!=0:
        need('404' in probe.stderr,'Cannot inspect release: '+probe.stderr);notes=Path(plan['source_snapshot']).parent/'RELEASE-NOTES.md';notes.write_text('# Matter Waves pause archive\n\nContent-addressed full-data snapshot for inventory '+SPEC['inventory_id']+'. Upload and verification are in progress while this release is a draft. No local deletion is permitted before the published verification receipt is complete.\n')
        checked(['gh','release','create',tag,'--repo',REPO,'--verify-tag','--draft','--title','Matter Waves pause archive — 24 November 2026','--notes-file',str(notes)],capture=False)
    return release(tag)

def checked_upload(plan,path):
    current=release(plan['tag']);by={x['name']:x for x in current['assets']};name=path.name;digest=sha(path)
    if name not in by:
        checked(['gh','release','upload',plan['tag'],str(path),'--repo',REPO],capture=False);current=release(plan['tag']);by={x['name']:x for x in current['assets']}
    asset=by[name];need(asset['size']==path.stat().st_size,'Existing asset size differs; no overwrite is attempted');remote_digest=asset.get('digest')
    if remote_digest:need(remote_digest=='sha256:'+digest,'Existing asset digest differs; no overwrite is attempted')
    return asset,digest

def expected_checkpoints(plan):
    result={}
    for item in plan['required']:
        label=item['label'];nodes=127 if label=='q2-reference' else 193 if 'cpu-193' in label else 177;expected={'nodes':nodes}
        if label=='latest/cases/exact-cg/endpoint.npz':expected.update(iteration=665,optimizer_memory=True)
        if label=='latest/cases/exact-cg/best.npz':expected.update(iteration=663,optimizer_memory=True)
        result.setdefault(item['sha256'],{}).update(expected)
    return result

def upload(work,repo):
    plan=read_plan(work)
    if (work/'VERIFIED-UPLOAD.json').exists() and (work/'PROOF-ASSET.json').exists():
        current=release(plan['tag'])
        if current['draft']:checked(['gh','release','edit',plan['tag'],'--repo',REPO,'--draft=false','--latest=false'],capture=False)
        current=verify_remote(work);status=load(work/'STATUS.json');status.update(status='uploaded_download_verified_ready_for_cleanup',full_data_verified=True,release_url=current['html_url']);save(work/'STATUS.json',status);return
    assert_idle(plan['files']);need(len(plan['parts'])+10<1000,'Release asset count would exceed the registered limit');need(shutil.disk_usage(work).free>=10*GIB,'Require 10 GiB free for bounded download/restore staging');current=ensure_release(plan)
    state=load(work/'TRANSFER.json') if (work/'TRANSFER.json').exists() else {'recorded_at':stamp(),'release_id':current['id'],'parts':{}}
    need(state['release_id']==current['id'],'Release identity changed');checkpoints=expected_checkpoints(plan);retained={d:work/'restore-check'/('checkpoint-'+d+'.npz') for d in checkpoints}
    for item in plan['git']:retained[item['bundle_sha256']]=work/'restore-check'/item['bundle_name']
    for i,part in enumerate(plan['parts']):
        name=part['name'];current=release(plan['tag']);assets={x['name']:x for x in current['assets']};old=state['parts'].get(name)
        if old and name in assets and assets[name]['id']==old['asset_id'] and assets[name]['size']==old['bytes'] and old.get('object_verification_passed'):
            need(not assets[name].get('digest') or assets[name]['digest']=='sha256:'+old['sha256'],'Previously verified asset changed')
            missing=any(d in retained and (not retained[d].is_file() or sha(retained[d])!=d) for d in part['objects'])
            if missing:
                with tempfile.TemporaryDirectory(prefix='restore-retry-',dir=work) as tmp:
                    downloaded=download(plan['tag'],name,Path(tmp));need(sha(downloaded)==old['sha256'],'Downloaded retry part differs');inspect_part(downloaded,part,plan['objects'],retained)
            continue
        part_path=work/'part-cache'/name;part_path.parent.mkdir(exist_ok=True);log('Building archive part',part=i+1,total=len(plan['parts']),objects=len(part['objects']))
        info=make_part(part_path,part,plan['objects']);need(info['bytes']<SPEC['asset_size_limit'],'Compressed part exceeds GitHub asset limit');asset,digest=checked_upload(plan,part_path)
        with tempfile.TemporaryDirectory(prefix='download-',dir=work) as tmp:
            downloaded=download(plan['tag'],name,Path(tmp));need(sha(downloaded)==digest,'Downloaded archive part differs');verified=inspect_part(downloaded,part,plan['objects'],retained)
        proofs={}
        for d in verified:
            if d in checkpoints:proofs[d]=checkpoint_check(retained[d],checkpoints[d])
            if plan['objects'][d]['kind']=='git_bundle':checked(['git','-C',str(repo),'bundle','verify',str(retained[d])])
        state['parts'][name]={'recorded_at':stamp(),'asset_id':asset['id'],'bytes':info['bytes'],'sha256':digest,'objects':verified,'object_verification_passed':True,'checkpoint_checks':proofs};save(work/'TRANSFER.json',state);part_path.unlink();log('Archive part downloaded and verified',part=i+1,total=len(plan['parts']),name=name)
    # Fresh code restore, using the bundle restored from downloaded release bytes.
    code=work/'restore-check/primary-code';primary=plan['primary_git'];bundle=retained[primary['bundle_sha256']]
    if not code.exists():checked(['git','clone','--no-checkout',str(bundle),str(code)])
    checked(['git','-C',str(code),'checkout','--detach',primary['head']]);need(checked(['git','-C',str(code),'rev-parse','HEAD'])==primary['head'],'Fresh code restore differs')
    for digest,expected in checkpoints.items():need(digest in retained and retained[digest].exists() and sha(retained[digest])==digest,'Critical checkpoint restore missing');checkpoint_check(retained[digest],expected)
    catalog={k:v for k,v in plan.items() if k!='objects'};catalog['objects']={k:{'bytes':v['bytes'],'kind':v['kind']} for k,v in plan['objects'].items()};catalog['parts']=[{**part,**{k:state['parts'][part['name']][k] for k in ['sha256','bytes','asset_id']}} for part in plan['parts']]
    manifest=work/'MATTER-WAVES-ARCHIVE.json.gz'
    with gzip.GzipFile(filename=str(manifest),mode='wb',mtime=0) as f:f.write(json.dumps(catalog,sort_keys=True,separators=(',',':')).encode())
    metadata=[]
    for path in [manifest,ROOT/'data/inventory-evidence.zip',ROOT/'RESTORE.md',ROOT/'restore-kit.zip']:
        asset,digest=checked_upload(plan,path)
        with tempfile.TemporaryDirectory(prefix='metadata-check-',dir=work) as tmp:need(sha(download(plan['tag'],path.name,Path(tmp)))==digest,'Downloaded archive metadata differs')
        metadata.append({'name':path.name,'sha256':digest,'bytes':path.stat().st_size,'asset_id':asset['id']})
    proof={'recorded_at':stamp(),'inventory_sha256':SPEC['inventory_sha256'],'plan_sha256':sha(work/'PLAN.json.gz'),'transfer_sha256':sha(work/'TRANSFER.json'),'release_id':state['release_id'],'tag':plan['tag'],'main_commit':plan['main_commit'],'verified_part_count':len(state['parts']),'verified_object_count':sum(len(x['objects']) for x in state['parts'].values()),'required_checkpoint_roles':len(plan['required']),'distinct_checkpoint_objects_loaded':len(checkpoints),'fresh_code_head':primary['head'],'metadata':metadata,'all_parts_downloaded_and_objects_rehashed':True,'cleanup_authorized_only_for_unchanged_whitelist':True}
    if not (work/'VERIFIED-UPLOAD.json').exists():save(work/'VERIFIED-UPLOAD.json',proof)
    else:
        old=load(work/'VERIFIED-UPLOAD.json');need(old['plan_sha256']==proof['plan_sha256'] and old['transfer_sha256']==proof['transfer_sha256'],'Interrupted published proof differs from current state')
    proofasset,digest=checked_upload(plan,work/'VERIFIED-UPLOAD.json')
    with tempfile.TemporaryDirectory(prefix='proof-check-',dir=work) as tmp:need(sha(download(plan['tag'],'VERIFIED-UPLOAD.json',Path(tmp)))==digest,'Published proof differs')
    save(work/'PROOF-ASSET.json',{'name':'VERIFIED-UPLOAD.json','sha256':digest,'asset_id':proofasset['id'],'bytes':(work/'VERIFIED-UPLOAD.json').stat().st_size})
    checked(['gh','release','edit',plan['tag'],'--repo',REPO,'--draft=false','--latest=false'],capture=False)
    verify_remote(work);status=load(work/'STATUS.json');status.update(status='uploaded_download_verified_ready_for_cleanup',full_data_verified=True,release_url=release(plan['tag'])['html_url']);save(work/'STATUS.json',status)

def verify_remote(work):
    plan=read_plan(work);proof=load(work/'VERIFIED-UPLOAD.json');state=load(work/'TRANSFER.json');current=release(plan['tag']);need(current['id']==proof['release_id'] and not current['draft'],'Archive release is not the verified published release');need(proof['all_parts_downloaded_and_objects_rehashed'],'No full download verification receipt')
    proof_asset=load(work/'PROOF-ASSET.json');need(sha(work/'VERIFIED-UPLOAD.json')==proof_asset['sha256'],'Download verification proof changed');need(proof['plan_sha256']==sha(work/'PLAN.json.gz') and proof['transfer_sha256']==sha(work/'TRANSFER.json'),'Plan or object verification state changed')
    assets={x['name']:x for x in current['assets']};expected=[{'name':name,**p} for name,p in state['parts'].items()]+proof['metadata']+[proof_asset]
    need(len(state['parts'])==len(plan['parts']),'Some parts remain unverified');verified=set()
    for part in plan['parts']:
        p=state['parts'][part['name']];need(set(p['objects'])==set(part['objects']) and p['object_verification_passed'],'Part content proof differs');verified.update(p['objects'])
    need(verified==set(plan['objects']),'Some data objects remain unverified')
    for item in expected:
        actual=assets.get(item['name']);need(actual and actual['id']==item['asset_id'] and actual['size']==item['bytes'],'Verified remote asset missing/replaced: '+item['name']);need(not actual.get('digest') or actual['digest']=='sha256:'+item['sha256'],'Verified remote digest changed')
    save(work/'LAST-REMOTE-CHECK.json',{'recorded_at':stamp(),'release_id':current['id'],'release_url':current['html_url'],'assets_checked':len(expected),'passed':True});return current

def journal_rows(path,repair=False):
    if not path.exists():return []
    raw=path.read_bytes();rows=[];position=0
    for i,line in enumerate(raw.splitlines(keepends=True)):
        try:row=json.loads(line)
        except (ValueError,UnicodeDecodeError):
            need(repair and position+len(line)==len(raw) and not line.endswith(b'\n'),'Deletion journal has an invalid completed record; stop for review')
            # An interrupted final write is retained separately, then safely retried.
            tail=path.with_name('DELETIONS-interrupted-tail-'+hashlib.sha256(line).hexdigest()[:12]+'.bin')
            if not tail.exists():tail.write_bytes(line)
            with path.open('r+b') as f:f.truncate(position);f.flush();os.fsync(f.fileno())
            break
        rows.append(row);position+=len(line)
    return rows


def cleanup(work):
    plan=read_plan(work);need(os.geteuid()!=0 and Path.home()==Path(plan['home']),'Cleanup must run as the inventoried account, without sudo');verify_remote(work);assert_idle(plan['files'])
    for item in plan['git']:
        if item['source']=='current-origin-main':continue
        head,_,refs=git_snapshot(Path(item['source']));need(head==item['head'] and refs==item['refs'],'Source Git history changed; cleanup is blocked')
    roots=[Path(r['path']) for r in plan['roots']];journal=work/'DELETIONS.jsonl';done=set()
    for row in journal_rows(journal,repair=True):
        if row['result'] in ['deleted','already_absent']:done.add(row['path'])
    planned=[r for r in plan['files'] if r['cleanup_action'].startswith('delete')];directories=set();retained=[];removed=0;bytes_removed=0
    with journal.open('a') as stream:
        for i,row in enumerate(planned):
            p=Path(row['path'])
            if str(p) in done:continue
            if i%250==0:verify_remote(work);assert_idle(plan['files']);log('Verified cleanup progress',processed=i,total=len(planned))
            result='already_absent'
            try:
                if p.exists() or p.is_symlink():exact_unlink(p,row['sha256'],roots);result='deleted';removed+=1;bytes_removed+=row['bytes']
                for parent in p.parents:
                    if parent in roots or parent==Path(plan['home'])/'Downloads' or parent==Path(plan['home']):break
                    directories.add(parent)
            except (OSError,RuntimeError) as exc:result='retained_changed_or_unsafe';retained.append({'path':str(p),'reason':str(exc)})
            item={'recorded_at':stamp(),'path':str(p),'sha256':row['sha256'],'bytes':row['bytes'],'result':result};stream.write(json.dumps(item)+'\n');stream.flush();os.fsync(stream.fileno())
    # Empty directories only; unlisted files and excluded caches prevent removal.
    for p in sorted(directories,key=lambda p:len(p.parts),reverse=True):
        try:no_symlinks(p);p.rmdir()
        except (OSError,RuntimeError):pass
    counts={};total_deleted=0;latest={}
    for row in journal_rows(journal):latest[row['path']]=row
    for row in latest.values():
        counts[row['result']]=counts.get(row['result'],0)+1
        if row['result']=='deleted':total_deleted+=row['bytes']
    receipt={'recorded_at':stamp(),'status':'cleanup_complete' if not retained else 'cleanup_complete_with_retained_changes','inventory_sha256':SPEC['inventory_sha256'],'release_url':verify_remote(work)['html_url'],'deletion_journal_sha256':sha(journal),'results':counts,'bytes_deleted_total':total_deleted,'retained_changes':retained,'git_tracked_and_runtime_files_retained':True,'unlisted_downloads_untouched':True,'new_files_since_inventory_untouched':True,'forced_recursive_deletions':0}
    save(work/'CLEANUP-RECEIPT.json',receipt)
    with gzip.open(work/'DELETIONS.jsonl.gz','wb') as target,journal.open('rb') as source:shutil.copyfileobj(source,target)
    # Publish an immutable-by-name cleanup receipt, keeping all previous assets.
    path=work/('cleanup-receipt-'+sha(work/'CLEANUP-RECEIPT.json')[:12]+'.json');shutil.copy2(work/'CLEANUP-RECEIPT.json',path);asset,digest=checked_upload(plan,path)
    with tempfile.TemporaryDirectory(prefix='cleanup-receipt-check-',dir=work) as tmp:need(sha(download(plan['tag'],path.name,Path(tmp)))==digest,'Cleanup receipt upload differs')
    save(work/'CLEANUP-ASSET.json',{'name':path.name,'asset_id':asset['id'],'sha256':digest,'bytes':path.stat().st_size});prune_staging(work);status=load(work/'STATUS.json');status.update(receipt);save(work/'STATUS.json',status);log('Verified local cleanup finished',**receipt)


def prune_staging(work):
    """Remove only generated, verified object copies, never source roots or code."""
    plan=read_plan(work);verify_remote(work);removed=0
    for item in plan['git']:
        p=work/'git'/item['bundle_name']
        if p.is_file():exact_unlink(p,item['bundle_sha256'],[work/'git']);removed+=1
    restore=work/'restore-check'
    for digest,expected in expected_checkpoints(plan).items():
        p=restore/('checkpoint-'+digest+'.npz')
        if p.is_file():exact_unlink(p,digest,[restore]);removed+=1
    for item in plan['git']:
        p=restore/item['bundle_name']
        if p.is_file():exact_unlink(p,item['bundle_sha256'],[restore]);removed+=1
    save(work/'STAGING-PRUNED.json',{'recorded_at':stamp(),'generated_verified_copies_removed':removed,'source_roots_affected':0})
