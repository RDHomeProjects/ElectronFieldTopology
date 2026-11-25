"""Verify the base, preserve residual data, then remove exact frozen roots."""
import gzip,hashlib,io,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
from common import ROOT,need,sha,save,load,stamp,log
from capsule import partition,inspect_part,no_symlinks
from filesystem import discover,scan_root,hash_pieces,signature,unchanged,unlink_exact,active_paths
from transport import Remote,asset_matches
GIB=1024**3
SETTINGS=load(ROOT/'SETTINGS.json')

def command(args,cwd=None,raw=False):
    log('Workstation command',argv=args[:8]);p=subprocess.run(args,cwd=cwd,capture_output=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'));need(p.returncode==0,'Command failed: '+repr(args[:6])+'\n'+p.stderr.decode(errors='replace')[-2500:]);return p.stdout if raw else p.stdout.decode().strip()

def gzsave(path,value):
    temporary=path.with_suffix('.tmp')
    with temporary.open('wb') as raw,gzip.GzipFile(fileobj=raw,filename='',mode='wb',mtime=0) as f:f.write(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    temporary.replace(path)
def gzload(path):
    with gzip.open(path,'rt') as f:return json.load(f)

def workspace_prepare(home,work,workspace):
    if not workspace.exists():
        source=next((p for p in [home/'ElectronFieldTopology-pause-archive-publication-20261124',home/'ElectronFieldTopology-repository-admin'] if (p/'.git').is_dir()),None);need(source,'No local project checkout found to seed the retained workspace')
        command(['git','clone','--no-hardlinks','--no-checkout',str(source),str(workspace)]);command(['git','-C',str(workspace),'remote','set-url','origin',SETTINGS['remote']]);command(['git','-C',str(workspace),'fetch','origin','refs/heads/main:refs/remotes/origin/main'])
        exists=subprocess.run(['git','-C',str(workspace),'show-ref','--verify','refs/heads/main'],capture_output=True).returncode==0
        command(['git','-C',str(workspace),'switch','main'] if exists else ['git','-C',str(workspace),'switch','-c','main','--track','origin/main']);command(['git','-C',str(workspace),'merge','--ff-only','origin/main'])
    need((workspace/'.git').is_dir() and not workspace.is_symlink(),'Retained workspace is not a regular Git checkout');origin=command(['git','-C',str(workspace),'remote','get-url','origin']);need(origin in [SETTINGS['remote'],SETTINGS['remote'].removesuffix('.git'),'git@github.com:'+SETTINGS['repository']+'.git'],'Retained workspace belongs to another project')
    command(['git','-C',str(workspace),'fetch','origin','refs/heads/main:refs/remotes/origin/main']);command(['git','-C',str(workspace),'merge-base','--is-ancestor',SETTINGS['closure_commit'],'origin/main']);return command(['git','-C',str(workspace),'rev-parse','origin/main'])

def base_check(home,work,workspace,remote):
    base=work/'base';base.mkdir(exist_ok=True);control=home/SETTINGS['original_control'];prefix=SETTINGS['closure_record']
    # Pin trust to the exact merged completion record, not a mutable status field.
    proof_bytes=command(['git','-C',str(workspace),'show',SETTINGS['closure_commit']+':'+prefix+'/VERIFIED-UPLOAD.json'],raw=True);proof=json.loads(proof_bytes);pin_bytes=command(['git','-C',str(workspace),'show',SETTINGS['closure_commit']+':'+prefix+'/PROOF-ASSET.json'],raw=True);pin=json.loads(pin_bytes);need(hashlib.sha256(proof_bytes).hexdigest()==pin['sha256'],'Merged archive proof hash differs')
    value=remote.release(SETTINGS['base_release_id']);need(value['tag_name']==SETTINGS['base_tag'] and not value['draft'],'Original verified archive is not published');assets={a['name']:a for a in value['assets']};asset_matches(assets.get(pin['name']),pin)
    with tempfile.TemporaryDirectory(prefix='base-proof-',dir=work) as tmp:
        p=remote.download(assets[pin['name']],Path(tmp)/pin['name']);need(sha(p)==pin['sha256'],'Downloaded base proof differs from merged record')
    need(proof['all_parts_downloaded_and_objects_rehashed'],'Base full-data download proof is missing')
    manifest_info=next(m for m in proof['metadata'] if m['name']=='MATTER-WAVES-ARCHIVE.json.gz');asset_matches(assets.get(manifest_info['name']),manifest_info)
    with tempfile.TemporaryDirectory(prefix='base-manifest-',dir=work) as tmp:
        p=remote.download(assets[manifest_info['name']],Path(tmp)/manifest_info['name']);need(sha(p)==manifest_info['sha256'],'Base manifest download differs');shutil.copyfile(p,base/'MATTER-WAVES-ARCHIVE.json.gz')
    manifest=gzload(base/'MATTER-WAVES-ARCHIVE.json.gz');need(manifest['tag']==SETTINGS['base_tag'],'Wrong base manifest tag');seen=set()
    for part in manifest['parts']:
        asset_matches(assets.get(part['name']),{'name':part['name'],**part});seen.update(part['objects'])
    need(seen==set(manifest['objects']) and len(manifest['parts'])==69,'Original archive object/part coverage differs')
    for m in proof['metadata']:asset_matches(assets.get(m['name']),m)
    (base/'VERIFIED-UPLOAD.json').write_bytes(proof_bytes);(base/'PROOF-ASSET.json').write_bytes(pin_bytes)
    save(base/'BASE-CHECK.json',{'recorded_at':stamp(),'published_release':value['html_url'],'release_id':value['id'],'proof_sha256':pin['sha256'],'manifest_sha256':manifest_info['sha256'],'parts':len(manifest['parts']),'passed':True,'closure_commit':SETTINGS['closure_commit']});return manifest

def base_recheck(work,remote):
    proof=load(work/'base/VERIFIED-UPLOAD.json');pin=load(work/'base/PROOF-ASSET.json');need(sha(work/'base/VERIFIED-UPLOAD.json')==pin['sha256'],'Cached base proof changed');manifest=gzload(work/'base/MATTER-WAVES-ARCHIVE.json.gz');info=next(x for x in proof['metadata'] if x['name']=='MATTER-WAVES-ARCHIVE.json.gz');need(sha(work/'base/MATTER-WAVES-ARCHIVE.json.gz')==info['sha256'],'Cached base manifest changed');value=remote.release(SETTINGS['base_release_id']);need(not value['draft'] and value['tag_name']==SETTINGS['base_tag'],'Base archive no longer published');assets={a['name']:a for a in value['assets']}
    for part in manifest['parts']:asset_matches(assets.get(part['name']),{'name':part['name'],**part})
    for x in proof['metadata']+[pin]:asset_matches(assets.get(x['name']),x)
    return manifest

def add_generated(path,objects,chunk_bytes):
    digest,pieces,sig=hash_pieces(path,chunk_bytes)
    for x in pieces:objects.setdefault(x['sha256'],{'bytes':x['bytes'],'source':str(path),'offset':x['offset'],'source_signature':sig})
    return {'sha256':digest,'bytes':sig[3],'pieces':[{'sha256':x['sha256'],'bytes':x['bytes']} for x in pieces]}

def scan(home,work,workspace,remote):
    if (work/'PLAN.json.gz').exists():log('Frozen cleanup plan retained; use archive to resume');return read_plan(work)
    need(shutil.disk_usage(work).free>=SETTINGS['minimum_free_gib']*GIB,'Require at least 20 GiB free for bounded transfer and restoration checks');commit=workspace_prepare(home,work,workspace);base=base_check(home,work,workspace,remote);paths,outside=discover(home,SETTINGS,work,workspace);active=active_paths(paths);roots=[];objects={};git=[];(work/'git-bundles').mkdir(exist_ok=True)
    save(work/'STATUS.json',{'recorded_at':stamp(),'status':'scanning_remaining_roots','roots_total':len(paths),'source_roots_removed':0})
    for i,path in enumerate(paths):
        save(work/'STATUS.json',{'recorded_at':stamp(),'status':'scanning_remaining_roots','current_root':str(path),'roots_checked':i,'roots_total':len(paths),'source_roots_removed':0})
        log('Inspecting remaining project root',index=i+1,total=len(paths),path=str(path));root,new=scan_root(path,f'root-{i:04d}',base['objects'],SETTINGS['chunk_bytes'])
        if path.lstat().st_dev!=work.stat().st_dev:root['blocked'].append('Different filesystem is retained without forced relocation')
        if str(path) in active:root['blocked'].append('Active process uses this folder: '+str(active[str(path)]))
        objects.update({d:o for d,o in new.items() if d not in objects});roots.append(root)
        if root['blocked']:continue
        for j,repo in enumerate(root['git_paths']):
            try:
                bundle=work/'git-bundles'/f'{root["id"]}-{j:03d}.bundle';temporary=bundle.with_suffix('.tmp');temporary.unlink(missing_ok=True)
                head=command(['git','-C',repo,'rev-parse','HEAD']);refs=command(['git','-C',repo,'for-each-ref','--format=%(refname) %(objectname)']);command(['git','-C',repo,'bundle','create',str(temporary),'--all','HEAD']);command(['git','-C',repo,'bundle','verify',str(temporary)]);temporary.replace(bundle);record=add_generated(bundle,objects,SETTINGS['chunk_bytes']);git.append({'root_id':root['id'],'repository':repo,'head':head,'refs':refs,'bundle_name':bundle.name,**record})
            except (OSError,RuntimeError) as exc:
                root['blocked'].append('Git history requires review before folder removal: '+str(exc))
    # Content for blocked roots remains local; omit needless new uploads for it.
    needed={x['sha256'] for r in roots if not r['blocked'] for f in r['files'] if f['storage']=='supplement' for x in f['pieces']}|{x['sha256'] for g in git for x in g['pieces']};objects={d:o for d,o in objects.items() if d in needed}
    tag='pause-residual-20261126-'+hashlib.sha256(json.dumps({'roots':roots,'objects':sorted(objects),'commit':commit},sort_keys=True).encode()).hexdigest()[:10]
    plan={'recorded_at':stamp(),'package_sha256':sha(ROOT/'SHA256SUMS'),'home':str(home),'workspace':str(workspace),'main_commit':commit,'tag':tag,'base_tag':SETTINGS['base_tag'],'base_release_id':SETTINGS['base_release_id'],'base_manifest_sha256':sha(work/'base/MATTER-WAVES-ARCHIVE.json.gz'),'base_proof_sha256':sha(work/'base/VERIFIED-UPLOAD.json'),'base_pin_sha256':sha(work/'base/PROOF-ASSET.json'),'roots':roots,'objects':objects,'git':git,'parts':partition(objects,SETTINGS['part_bytes']),'out_of_scope_retained':outside,'protected':[str(home/n) for n in SETTINGS['keep_home']],'scientific_steps':0};gzsave(work/'PLAN.json.gz',plan);save(work/'IDENTITY.json',{'recorded_at':stamp(),'plan_sha256':sha(work/'PLAN.json.gz'),'package_sha256':sha(ROOT/'SHA256SUMS'),'tag':tag})
    summary={'recorded_at':stamp(),'status':'scanned_not_deleted','roots_discovered':len(roots),'eligible_roots':sum(not r['blocked'] for r in roots),'blocked_roots':[{'path':r['path'],'reasons':r['blocked']} for r in roots if r['blocked']],'files':sum(len(r['files']) for r in roots),'existing_archive_files':sum(f['storage']=='base' for r in roots for f in r['files']),'rebuildable_files':sum(f['storage']=='rebuildable' for r in roots for f in r['files']),'new_unique_gib':sum(o['bytes'] for o in objects.values())/GIB,'supplement_parts':len(plan['parts']),'git_bundles':len(git),'source_roots_removed':0,'keep_workspace':str(workspace)};save(work/'STATUS.json',summary);write_report(work,plan,summary);log('Final folder cleanup plan ready',**summary);return plan

def read_plan(work):
    identity=load(work/'IDENTITY.json');need(identity['package_sha256']==sha(ROOT/'SHA256SUMS') and identity['plan_sha256']==sha(work/'PLAN.json.gz'),'Frozen job or tool identity changed');return gzload(work/'PLAN.json.gz')

def make_part(path,part,objects):
    temporary=path.with_suffix('.tmp');path.parent.mkdir(exist_ok=True)
    with temporary.open('wb') as raw,gzip.GzipFile(fileobj=raw,filename='',mode='wb',mtime=0,compresslevel=3) as compressed,tarfile.open(fileobj=compressed,mode='w|',format=tarfile.USTAR_FORMAT) as tar:
        for digest in part['objects']:
            obj=objects[digest];source=Path(obj['source']);no_symlinks(source);need(signature(source)==obj['source_signature'],'Source changed since frozen scan: '+str(source));h=hashlib.sha256();left=obj['bytes']
            info=tarfile.TarInfo('objects/'+digest);info.size=left;info.mode=0o444;info.mtime=0
            class Reader:
                def read(self,size=-1):
                    nonlocal left
                    data=stream.read(min(left,size if size>=0 else left));left-=len(data);h.update(data);return data
            with source.open('rb') as stream:stream.seek(obj['offset']);tar.addfile(info,Reader())
            need(left==0 and h.hexdigest()==digest and signature(source)==obj['source_signature'],'Source chunk changed during packaging')
    temporary.replace(path);return sha(path)

def archive(work,remote):
    plan=read_plan(work);need(sha(work/'base/MATTER-WAVES-ARCHIVE.json.gz')==plan['base_manifest_sha256'] and sha(work/'base/VERIFIED-UPLOAD.json')==plan['base_proof_sha256'] and sha(work/'base/PROOF-ASSET.json')==plan['base_pin_sha256'],'Frozen base metadata changed');base_recheck(work,remote)
    if (work/'PROOF-ASSET.json').exists():
        verify_remote(work,remote,allow_draft=True);remote.publish(load(work/'VERIFIED-SUPPLEMENT.json')['release_id'],plan['tag']);verify_remote(work,remote);log('Supplement already verified; no data re-upload required');return
    release=remote.ensure(plan['tag'],plan['main_commit'],Path(plan['workspace']));state=load(work/'TRANSFER.json') if (work/'TRANSFER.json').exists() else {'recorded_at':stamp(),'release_id':release['id'],'parts':{}};need(state['release_id']==release['id'],'Supplement release ID changed');keep={d:work/'restore-check/chunks'/d for g in plan['git'] for d in [p['sha256'] for p in g['pieces']]}
    for i,part in enumerate(plan['parts']):
        current=remote.release(release['id']);assets={a['name']:a for a in current['assets']};old=state['parts'].get(part['name'])
        if old:
            asset_matches(assets.get(part['name']),{'name':part['name'],**old});missing=any(d in keep and (not keep[d].exists() or sha(keep[d])!=d) for d in part['objects'])
            if missing:
                with tempfile.TemporaryDirectory(prefix='restore-retry-',dir=work) as tmp:
                    p=remote.download(assets[part['name']],Path(tmp)/part['name']);need(sha(p)==old['sha256'],'Retry download differs');inspect_part(p,part,plan['objects'],keep)
            continue
        need(shutil.disk_usage(work).free>=10*GIB,'Require 10 GiB free for remaining bounded staging');log('Packaging additional data',part=i+1,total=len(plan['parts']));path=work/'part-cache'/part['name'];digest=make_part(path,part,plan['objects']);asset,_=remote.upload(release['id'],plan['tag'],path)
        with tempfile.TemporaryDirectory(prefix='verify-part-',dir=work) as tmp:
            p=remote.download(asset,Path(tmp)/part['name']);need(sha(p)==digest,'Supplement part download differs');seen=inspect_part(p,part,plan['objects'],keep)
        state['parts'][part['name']]={'recorded_at':stamp(),'asset_id':asset['id'],'bytes':path.stat().st_size,'sha256':digest,'objects':seen,'objects_verified':True};save(work/'TRANSFER.json',state);path.unlink();log('Additional archive part downloaded and verified',part=i+1,total=len(plan['parts']))
    if not (work/'TRANSFER.json').exists():save(work/'TRANSFER.json',state)
    checks=[]
    for g in plan['git']:
        bundle=work/'restore-check'/g['bundle_name'];bundle.parent.mkdir(exist_ok=True)
        with bundle.open('wb') as f:
            for piece in g['pieces']:
                p=keep[piece['sha256']];need(p.exists() and sha(p)==piece['sha256'],'Restored Git bundle chunk missing');
                with p.open('rb') as s:shutil.copyfileobj(s,f)
        need(sha(bundle)==g['sha256'],'Reconstructed Git bundle hash differs')
        # Only a tool-created temporary clone is recursively discarded by the
        # temporary-directory context; original roots use exact journaled unlink.
        with tempfile.TemporaryDirectory(prefix='git-restore-',dir=work) as tmp:
            clone=Path(tmp)/'code';command(['git','clone','--no-checkout',str(bundle),str(clone)]);command(['git','-C',str(clone),'checkout','--detach',g['head']]);need(command(['git','-C',str(clone),'rev-parse','HEAD'])==g['head'],'Git source restore HEAD differs');checks.append({'repository':g['repository'],'head':g['head'],'bundle_sha256':g['sha256'],'fresh_clone_passed':True})
    catalog={k:v for k,v in plan.items() if k!='objects'};catalog['objects']={d:{'bytes':o['bytes']} for d,o in plan['objects'].items()};catalog['parts']=[{**p,**{k:state['parts'][p['name']][k] for k in ['asset_id','bytes','sha256']}} for p in plan['parts']];catalog['release_id']=release['id'];gzsave(work/'RESIDUAL-MANIFEST.json.gz',catalog)
    metadata=[]
    for path in [work/'RESIDUAL-MANIFEST.json.gz',ROOT/'RESTORE.md',ROOT/'restore-kit.zip']:
        a,d=remote.upload(release['id'],plan['tag'],path)
        with tempfile.TemporaryDirectory(prefix='verify-metadata-',dir=work) as tmp:need(sha(remote.download(a,Path(tmp)/path.name))==d,'Supplement metadata download differs')
        metadata.append({'name':path.name,'asset_id':a['id'],'bytes':path.stat().st_size,'sha256':d})
    proof_path=work/'VERIFIED-SUPPLEMENT.json'
    if not proof_path.exists():save(proof_path,{'recorded_at':stamp(),'tag':plan['tag'],'release_id':release['id'],'plan_sha256':sha(work/'PLAN.json.gz'),'transfer_sha256':sha(work/'TRANSFER.json'),'base_manifest_sha256':plan['base_manifest_sha256'],'objects_download_verified':len(plan['objects']),'all_new_objects_downloaded_and_rehashed':True,'git_restore_checks':checks,'metadata':metadata})
    proof=load(proof_path);need(proof['plan_sha256']==sha(work/'PLAN.json.gz') and proof['transfer_sha256']==sha(work/'TRANSFER.json'),'Previous proof differs');a,d=remote.upload(release['id'],plan['tag'],proof_path)
    with tempfile.TemporaryDirectory(prefix='verify-proof-',dir=work) as tmp:need(sha(remote.download(a,Path(tmp)/proof_path.name))==d,'Supplement proof download differs')
    save(work/'PROOF-ASSET.json',{'name':proof_path.name,'asset_id':a['id'],'bytes':proof_path.stat().st_size,'sha256':d});remote.publish(release['id'],plan['tag']);verify_remote(work,remote);status=load(work/'STATUS.json');status.update(status='all_residual_data_verified_ready_for_cleanup',supplement_release_url=remote.release(release['id'])['html_url']);save(work/'STATUS.json',status);write_report(work,plan,status)

def verify_remote(work,remote,allow_draft=False):
    plan=read_plan(work);need(sha(work/'base/MATTER-WAVES-ARCHIVE.json.gz')==plan['base_manifest_sha256'] and sha(work/'base/VERIFIED-UPLOAD.json')==plan['base_proof_sha256'] and sha(work/'base/PROOF-ASSET.json')==plan['base_pin_sha256'],'Frozen base metadata changed');base_recheck(work,remote);proof=load(work/'VERIFIED-SUPPLEMENT.json');pin=load(work/'PROOF-ASSET.json');need(sha(work/'VERIFIED-SUPPLEMENT.json')==pin['sha256'],'Supplement proof changed');need(proof['plan_sha256']==sha(work/'PLAN.json.gz') and proof['transfer_sha256']==sha(work/'TRANSFER.json'),'Supplement job or transfer proof changed');need(proof['all_new_objects_downloaded_and_rehashed'],'No complete residual download proof');state=load(work/'TRANSFER.json');value=remote.release(proof['release_id']);need((allow_draft or not value['draft']) and value['tag_name']==plan['tag'],'Supplement is not the verified published release');assets={a['name']:a for a in value['assets']};seen=set();need(set(state['parts'])=={p['name'] for p in plan['parts']},'Part coverage differs')
    for p in plan['parts']:
        item=state['parts'][p['name']];need(item['objects_verified'] and set(item['objects'])==set(p['objects']),'Part object coverage differs');seen.update(item['objects']);asset_matches(assets.get(p['name']),{'name':p['name'],**item})
    need(seen==set(plan['objects']),'Some residual objects unverified')
    for item in proof['metadata']+[pin]:asset_matches(assets.get(item['name']),item)
    save(work/'LAST-REMOTE-CHECK.json',{'recorded_at':stamp(),'base_and_supplement_verified':True,'supplement_published':not value['draft'],'supplement_release_url':value['html_url']});return value

def append_journal(path,row):
    with path.open('a') as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
def journal(path):
    if not path.exists():return []
    data=path.read_bytes();rows=[];offset=0
    for line in data.splitlines(keepends=True):
        try:row=json.loads(line)
        except ValueError:
            need(offset+len(line)==len(data) and not line.endswith(b'\n'),'Invalid completed deletion journal record');(path.parent/'interrupted-journal-tail.bin').write_bytes(line)
            with path.open('r+b') as f:f.truncate(offset);f.flush();os.fsync(f.fileno())
            break
        rows.append(row);offset+=len(line)
    return rows

def cleanup(work,remote):
    plan=read_plan(work);verify_remote(work,remote);quarantine=work/'quarantine';quarantine.mkdir(exist_ok=True);events=work/'DELETIONS.jsonl';events.touch(exist_ok=True);done={r['key'] for r in journal(events) if r['result'] in ['deleted','already_absent_after_verified_quarantine']};roots_done=[];retained=[]
    for root in plan['roots']:
        original=Path(root['path']);moved=quarantine/root['id']
        if root['blocked']:retained.append({'path':str(original),'reason':root['blocked']});continue
        try:
            verify_remote(work,remote)
            if original.exists() or original.is_symlink():
                need(not moved.exists(),'Both original and quarantined root exist; preserve both for review');need(not active_paths([original]),'A process is using this root; retained');unchanged(root);no_symlinks(original.parent);need(original.parent.stat().st_dev==quarantine.stat().st_dev,'Root is on another filesystem; retained without copying or forced deletion');os.rename(original,moved);append_journal(events,{'recorded_at':stamp(),'key':root['id']+':root-moved','result':'root_moved','original':str(original),'quarantine':str(moved)})
            elif not moved.exists():
                append_journal(events,{'recorded_at':stamp(),'key':root['id']+':root-removed','result':'root_already_absent','original':str(original)});roots_done.append(str(original));continue
            no_symlinks(moved);need(not active_paths([moved]),'A process uses the quarantined root; retained without pruning')
            # A resumed partial prune uses per-file receipts; no recursive deletion.
            for index,row in enumerate(root['files']):
                if index%2000==0:log('Removing verified files from redundant root',root=root['path'],processed=index,total=len(root['files']))
                key=root['id']+':'+row['relative'];target=moved/row['relative'] if root['kind']=='directory' else moved
                if key in done:continue
                if not target.exists():
                    append_journal(events,{'recorded_at':stamp(),'key':key,'path':row['path'],'bytes':0,'storage':row['storage'],'result':'already_absent_after_verified_quarantine'});done.add(key);continue
                else:unlink_exact(target,row['sha256'],quarantine)
                append_journal(events,{'recorded_at':stamp(),'key':key,'path':row['path'],'bytes':row['bytes'],'storage':row['storage'],'result':'deleted'});done.add(key)
            for row in root['links']:
                key=root['id']+':'+row['relative'];target=moved/row['relative']
                if key in done:continue
                if not target.exists() and not target.is_symlink():
                    append_journal(events,{'recorded_at':stamp(),'key':key,'path':row['path'],'bytes':0,'storage':'link','result':'already_absent_after_verified_quarantine'});done.add(key);continue
                no_symlinks(target.parent);need(target.is_symlink() and os.readlink(target)==row['target'],'Quarantined link changed; retained');target.unlink();append_journal(events,{'recorded_at':stamp(),'key':key,'path':row['path'],'bytes':0,'storage':'rebuildable' if row['rebuildable'] else 'supplement_link_record','result':'deleted'});done.add(key)
            if root['kind']=='directory':
                for relative in sorted(root['directories'],key=lambda s:len(Path(s).parts),reverse=True):
                    p=moved/relative
                    if p.exists():no_symlinks(p);p.rmdir()
            need(not moved.exists() and not moved.is_symlink(),'Nonempty quarantined root retained');append_journal(events,{'recorded_at':stamp(),'key':root['id']+':root-removed','result':'root_removed','original':str(original)});
            if original.exists() or original.is_symlink():retained.append({'path':str(original),'reason':'A new root appeared at the original path; it was not touched'})
            else:roots_done.append(str(original))
            log('Verified redundant root removed',path=str(original))
        except (OSError,RuntimeError) as exc:retained.append({'path':str(original),'quarantine':str(moved) if moved.exists() else None,'reason':str(exc)});log('Root retained for review',path=str(original),reason=str(exc))
    rows=journal(events);deletions={r['key']:r for r in rows if r['result']=='deleted'};receipt={'recorded_at':stamp(),'status':'folder_cleanup_complete' if not retained else 'folder_cleanup_complete_with_retained_items','roots_removed':roots_done,'root_count_removed':len(roots_done),'files_and_links_removed':len(deletions),'bytes_deleted':sum(r['bytes'] for r in deletions.values()),'retained_items':retained,'protected':plan['protected'],'unrelated_home_and_download_items_untouched':True,'base_and_supplement_download_proofs_required':True,'forced_recursive_deletions':0,'journal_sha256':sha(events) if events.exists() else None,'scientific_steps':0};save(work/'CLEANUP-RECEIPT.json',receipt)
    status=load(work/'STATUS.json');status.update(receipt);status['source_roots_removed']=receipt['root_count_removed'];save(work/'STATUS.json',status);write_report(work,plan,status)
    # Prune only this job's generated restoration copies using their exact hashes.
    for g in plan['git']:
        for p in [work/'git-bundles'/g['bundle_name'],work/'restore-check'/g['bundle_name']]:
            if p.is_file() and sha(p)==g['sha256']:p.unlink()
    for d in {p['sha256'] for g in plan['git'] for p in g['pieces']}:
        p=work/'restore-check/chunks'/d
        if p.is_file() and sha(p)==d:p.unlink()
    log('Final folder cleanup finished',**receipt)

def write_report(work,plan,status):
    lines=['# Final Matter Waves workstation folder cleanup','', 'Status: **'+status['status']+'**. No scientific steps were run.','', 'Base archive: '+SETTINGS['base_tag']+'. Supplemental archive: '+plan['tag']+'.','', 'Keep one working checkout at `'+plan['workspace']+'`, the original pause controls, and this final cleanup control directory. Unrelated items are outside scope.','', '| Folder | Planned disposition |','|---|---|']
    removed=set(status.get('roots_removed',[]))
    for root in plan['roots']:
        state='Removed' if root['path'] in removed else 'Retain: '+'; '.join(root['blocked']) if root['blocked'] else 'Archive/match, verify, then remove';lines.append('| '+root['path'].replace('|','\\|')+' | '+state.replace('|','\\|')+' |')
    lines+=['','## Retained items','',json.dumps(status.get('retained_items',[]),indent=2),'','Read RESTORE.md from the supplemental release to reconstruct selected folders. Changes after scanning are retained and need a new scan/job, never a bypass of the frozen plan.',''];(work/'REPORT.md').write_text('\n'.join(lines))
