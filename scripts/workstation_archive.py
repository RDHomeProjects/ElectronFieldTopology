"""Archive project workspaces to verified release assets. Standard library; Apache-2.0.

No command deletes or relocates a source. Restore only targets a new directory.
"""
import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import zipfile

REPO='RDHomeProjects/ElectronFieldTopology'
TARGET='fe7ce72408b2d1ad86a41a3b97ecc8482a746e25'
CACHES={'.venv','venv','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'}
MIB=1024**2
GIB=1024**3
STOP_FILE=None
PROGRESS_FILE=None
LAST_PROGRESS={}


def timestamp():
    n=datetime.now(timezone.utc)
    return {'utc':n.isoformat(),'melbourne':n.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}


def log(message,**extra):
    event={'recorded_at':timestamp(),'message':message,**extra}
    if message!='WORKING':
        LAST_PROGRESS.clear();LAST_PROGRESS.update(event)
        if PROGRESS_FILE:save(PROGRESS_FILE,event)
    print(json.dumps(event),flush=True)


def checkpoint():
    if STOP_FILE and STOP_FILE.exists():raise InterruptedError('Cooperative stop requested; resume uses the same inventory and archive ID')


def need(condition,message):
    if not condition:raise ValueError(message)


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.partial')
    tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    tmp.replace(path)


def load(path):return json.loads(path.read_text())


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(8*MIB):h.update(block)
    return h.hexdigest()


def signature(path):
    s=path.lstat()
    return [s.st_size,s.st_mtime_ns,stat.S_IMODE(s.st_mode)]


def git(root,*args,check=True):
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    p=subprocess.run(['git','--no-optional-locks','-C',str(root),*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if check and p.returncode:raise ValueError('Git read failed for '+str(root)+': '+p.stderr.decode(errors='replace')[-1200:])
    return p


def git_state(root):
    head=git(root,'rev-parse','HEAD').stdout.decode().strip()
    refs=git(root,'for-each-ref','--format=%(refname) %(objectname)').stdout.decode().splitlines()
    symbolic=git(root,'symbolic-ref','-q','HEAD',check=False).stdout.decode().strip()
    index=Path(git(root,'rev-parse','--path-format=absolute','--git-path','index').stdout.decode().strip())
    return {'head':head,'head_ref':symbolic,'refs':refs,'index_sha256':digest(index) if index.exists() else None,
            'object_format':git(root,'rev-parse','--show-object-format').stdout.decode().strip(),
            'status':git(root,'status','--porcelain=v1','--untracked-files=all').stdout.decode(),
            'object_ids':sorted(git(root,'cat-file','--batch-all-objects','--batch-check=%(objectname)').stdout.decode().splitlines())}


def secret_name(name):
    return name in {'.env','.netrc','.git-credentials','.pypirc','id_rsa','id_ed25519','credentials.json'} or name.startswith('.env.') or name.endswith(('.key','.pem','.p12','.pfx'))


def scan_root(source):
    """Metadata-only inventory; no symlink traversal and no Git index refresh."""
    files=[];directories=[];excluded=[];gitdirs=[];blockers=[]
    if source.is_symlink():return {'files':[],'directories':[],'excluded':[],'gitdirs':[],'blockers':['Root is a symlink: '+str(source)]}
    if source.is_file():
        paths=[(source,source.name)]
    else:
        paths=[]
        def error(e):blockers.append(str(e))
        for folder,dirs,names in os.walk(source,followlinks=False,onerror=error):
            parent=Path(folder);rel=parent.relative_to(source)
            directories.append(rel.as_posix())
            if '.git' in dirs or '.git' in names:
                gitdirs.append(rel.as_posix())
                if '.git' in dirs:dirs.remove('.git')
                if '.git' in names:names.remove('.git')
            for d in list(dirs):
                p=parent/d
                if d in CACHES:
                    dirs.remove(d);excluded.append((rel/d).as_posix())
                elif p.is_symlink():
                    dirs.remove(d);blockers.append('Directory symlink requires explicit target accounting: '+str(p))
            paths.extend((parent/n,(rel/n).as_posix()) for n in names)
    for p,relative in paths:
        try:
            if '\\' in relative:
                blockers.append('Unsupported backslash in source filename: '+str(p));continue
            s=p.lstat()
            if not stat.S_ISREG(s.st_mode):blockers.append('Non-regular file requires explicit accounting: '+str(p));continue
            if secret_name(p.name):blockers.append('Credential/private-key-like filename excluded from public publication: '+str(p));continue
            files.append({'path':relative,'signature':signature(p)})
        except OSError as e:blockers.append(str(e))
    return {'files':sorted(files,key=lambda x:x['path']),'directories':sorted(directories),
            'excluded':sorted(excluded),'gitdirs':sorted(gitdirs),'blockers':blockers}


def discover(home):
    return sorted({p.absolute() for parent in [home,home/'Downloads'] if parent.exists()
                   for p in parent.glob('ElectronFieldTopology*')},key=str)


def inventory(home,work,include=()):
    home=home.expanduser().resolve();work=work.expanduser().resolve()
    sources=sorted(set(discover(home))|{p.expanduser().absolute() for p in include},key=str)
    need(all(p.exists() or p.is_symlink() for p in sources),'An explicitly included source is missing')
    sources=[p for p in sources if not any(p!=q and p.is_relative_to(q) for q in sources)]
    need(sources,'No ElectronFieldTopology project paths found')
    need(not any(work==p or work.is_relative_to(p) for p in sources),'Archive work folder must be outside all selected sources')
    work.mkdir(parents=True,exist_ok=True)
    archive_id=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz').lower()+'-'+secrets.token_hex(4)
    session=work/archive_id;session.mkdir()
    roots=[]
    for i,source in enumerate(sources,1):
        log('Inventorying source',path=str(source))
        scan=scan_root(source)
        gs=[]
        for name in scan['gitdirs']:
            g=source/Path(name)
            try:
                state=git_state(g);gs.append({'path':name,'state':state})
            except ValueError as e:scan['blockers'].append(str(e))
        location='downloads' if source.parent==home/'Downloads' else 'home' if source.parent==home else 'extra'
        roots.append({'id':f'r{i:03d}','source':str(source),'location':location,
                      'name':source.name,'kind':'file' if source.is_file() else 'directory','scan':scan,'git':gs,
                      'logical_bytes':sum(f['signature'][0] for f in scan['files']),
                      'field_files':sum(Path(f['path']).suffix.lower() in {'.npz','.npy','.h5','.hdf5'} for f in scan['files'])})
    record={'schema_version':1,'recorded_at':timestamp(),'archive_id':archive_id,'home':str(home),
            'roots':roots,'cache_policy':sorted(CACHES),'source_deletion_supported':False}
    save(session/'inventory.json',record);save(work/'latest.json',{'session':str(session)})
    total=sum(r['logical_bytes'] for r in roots)
    lines=['# Workstation archive inventory','',json.dumps(record['recorded_at']),
           '',f'Archive ID: {archive_id}. No source changes or uploads performed.',
           '', '| Root | Retained logical GiB | Field files | Git stores | Blockers |','|---|---:|---:|---:|---:|']
    for r in roots:lines.append(f'| {r["source"]} | {r["logical_bytes"]/GIB:.4f} | {r["field_files"]} | {len(r["git"])} | {len(r["scan"]["blockers"])} |')
    lines+=['',f'Total retained file bytes: {total:,} ({total/GIB:.3f} GiB), before Git object packs and tar headers.',
            f'Available archive-work disk: {shutil.disk_usage(work).free/GIB:.2f} GiB.',
            'Archive staging requires roughly the largest retained root plus 2 GiB headroom, not the sum of every root.',
            'Source files are not deduplicated or recompressed. Existing ZIP/NPZ bytes are preserved.',
            'Cache directories are explicitly omitted; Git graphs/index states are separately packed. Git credentials/config/hooks are not uploaded.',
            'Full file hashing occurs during archive creation. This metadata inventory alone does not authorize cleanup.']
    for r in roots:
        if r['scan']['excluded']:lines+=['',r['source']+' — rebuildable exclusions:',*['- '+p for p in r['scan']['excluded']]]
        if r['scan']['blockers']:lines+=['',r['source']+' — BLOCKERS:',*['- '+p for p in r['scan']['blockers']]]
    (session/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    with zipfile.ZipFile(session/'inventory-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in ['inventory.json','SUMMARY.md']:z.write(session/name,name)
    log('Inventory complete',session=str(session),logical_bytes=total,roots=len(roots),blockers=sum(len(r['scan']['blockers']) for r in roots),evidence=str(session/'inventory-evidence.zip'))
    return session


def assert_unchanged(root):
    source=Path(root['source']);current=scan_root(source)
    need(current==root['scan'],'Source contents or metadata changed since inventory: '+str(source)+'; take a new inventory. Nothing was deleted.')
    for g in root['git']:need(git_state(source/Path(g['path']))==g['state'],'Git state changed since inventory: '+str(source))


def snapshot_git(root,destination,expected):
    """All object types (including unreachable objects), refs, HEAD and split-index state.

    Local config/credential helpers and hooks are intentionally not published.
    """
    destination.mkdir(parents=True)
    objects='\n'.join(expected['object_ids'])+'\n'
    with (destination/'objects.pack').open('wb') as out:
        p=subprocess.run(['git','--no-optional-locks','-C',str(root),'pack-objects','--stdout'],input=objects.encode(),stdout=out,stderr=subprocess.PIPE,
                         env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
    need(p.returncode==0,'Git object snapshot failed: '+p.stderr.decode(errors='replace'))
    save(destination/'state.json',expected)
    index=Path(git(root,'rev-parse','--path-format=absolute','--git-path','index').stdout.decode().strip())
    if index.exists():shutil.copy2(index,destination/'index')
    for f in index.parent.glob('sharedindex.*'):shutil.copy2(f,destination/f.name)
    (destination/'reflog.txt').write_bytes(git(root,'reflog','show','--all','--date=iso-strict','--format=%H %gD %gs').stdout)
    need(git_state(root)==expected,'Git store changed while it was copied: '+str(root))


class PartWriter:
    def __init__(self,folder,prefix,limit):
        self.folder=folder;self.prefix=prefix;self.limit=limit;self.file=None;self.used=0;self.paths=[]
    def write(self,data):
        original=len(data);view=memoryview(data)
        while view:
            if self.file is None:
                path=self.folder/f'{self.prefix}-part-{len(self.paths)+1:05d}.tarpart'
                self.file=path.open('wb');self.paths.append(path);self.used=0
            n=min(len(view),self.limit-self.used);self.file.write(view[:n]);self.used+=n;view=view[n:]
            if self.used==self.limit:self.file.close();self.file=None
        return original
    def close(self):
        if self.file:self.file.close();self.file=None


class SequenceReader(io.RawIOBase):
    def __init__(self,paths,fetch=None):self.paths=iter(paths);self.fetch=fetch;self.current=None;self.remove=None
    def readable(self):return True
    def readinto(self,b):
        while True:
            if self.current is None:
                try:item=next(self.paths)
                except StopIteration:return 0
                path=self.fetch(item) if self.fetch else item
                self.current=Path(path).open('rb');self.remove=path if self.fetch else None
            n=self.current.readinto(b)
            if n:return n
            self.current.close();self.current=None
            if self.remove:Path(self.remove).unlink();self.remove=None
    def close(self):
        if self.current:self.current.close();self.current=None
        if self.remove:Path(self.remove).unlink(missing_ok=True);self.remove=None
        super().close()


def verify_tar(reader,manifest,destination=None):
    need(manifest['location'] in {'home','downloads','extra'} and manifest['name'] not in {'','.','..'} and Path(manifest['name']).name==manifest['name'], 'Unsafe original root name')
    for name in [*manifest['directories'],*manifest['git_locations']]:
        q=PurePosixPath(name)
        need(not q.is_absolute() and '..' not in q.parts and '\\' not in name,'Unsafe manifest directory')
    expected={f['archive_path']:f for f in manifest['files']};seen=set()
    with tarfile.open(fileobj=reader,mode='r|') as tar:
        for item in tar:
            q=PurePosixPath(item.name)
            need(not q.is_absolute() and '..' not in q.parts and '\\' not in item.name,'Unsafe archive member')
            need(item.isfile() and item.name in expected and item.name not in seen,'Unexpected, duplicate or non-regular archive member: '+item.name)
            f=expected[item.name];need(item.size==f['size'] and item.mode==f['mode'],'Archive metadata mismatch')
            h=hashlib.sha256();stream=tar.extractfile(item)
            out=None;target=None
            if destination:
                target=destination/Path(item.name);target.parent.mkdir(parents=True,exist_ok=True)
                need(not target.exists(),'Restore refuses to overwrite '+str(target));out=target.open('xb')
            try:
                while block:=stream.read(8*MIB):
                    h.update(block)
                    if out:out.write(block)
            finally:
                if out:out.close()
            need(h.hexdigest()==f['sha256'],'Restored payload SHA-256 mismatch: '+item.name)
            if target:
                target.chmod(f['mode']);os.utime(target,ns=(f['mtime_ns'],f['mtime_ns']))
            seen.add(item.name)
    # Consume the complete stream to verify trailing assets/padding, too.
    while reader.read(8*MIB):pass
    need(seen==set(expected),'Archive file coverage differs from inventory')
    return len(seen)


def build_root(root,folder,limit):
    assert_unchanged(root)
    folder.mkdir(parents=True,exist_ok=False)
    save(folder/'staging-owner.json',{'source':root['source'],'id':root['id']})
    source=Path(root['source']);files=[];inputs={}
    for i,g in enumerate(root['git']):snapshot_git(source/Path(g['path']),folder/'git'/f'g{i:03d}',g['state'])
    for i,entry in enumerate(root['scan']['files']):
        checkpoint()
        path=source/entry['path'] if source.is_dir() else source
        need(signature(path)==entry['signature'],'Source changed before hashing: '+str(path))
        h=digest(path);need(signature(path)==entry['signature'],'Source changed while hashing: '+str(path))
        name='files/'+entry['path'];inputs[name]=path
        files.append({'archive_path':name,'size':entry['signature'][0],'mtime_ns':entry['signature'][1],
                      'mode':entry['signature'][2],'sha256':h})
        if i%50==0:log('Hashing source files',root=root['id'],completed=i+1,total=len(root['scan']['files']))
    for path in sorted((folder/'git').rglob('*')) if (folder/'git').exists() else []:
        if path.is_file():
            name=path.relative_to(folder).as_posix();inputs[name]=path;s=path.stat()
            files.append({'archive_path':name,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'mode':stat.S_IMODE(s.st_mode),'sha256':digest(path)})
    manifest={'schema_version':1,'recorded_at':timestamp(),'id':root['id'],'name':root['name'],'location':root['location'],
              'kind':root['kind'],'directories':root['scan']['directories'],'cache_exclusions':root['scan']['excluded'],
              'git_locations':[g['path'] for g in root['git']],'files':files}
    save(folder/(root['id']+'-manifest.json'),manifest)
    need(shutil.disk_usage(folder).free>sum(f['size'] for f in files)+2*limit+64*MIB,'Insufficient staging disk; choose a larger --work location. Sources are unchanged.')
    writer=PartWriter(folder,root['id'],limit)
    try:
        with tarfile.open(fileobj=writer,mode='w|',format=tarfile.PAX_FORMAT) as tar:
            for f in files:
                checkpoint()
                info=tarfile.TarInfo(f['archive_path']);info.size=f['size'];info.mode=f['mode'];info.mtime=f['mtime_ns']//10**9
                with inputs[f['archive_path']].open('rb') as stream:tar.addfile(info,stream)
    finally:writer.close()
    assert_unchanged(root)
    with io.BufferedReader(SequenceReader(writer.paths)) as reader:verify_tar(reader,manifest)
    result={'id':root['id'],'manifest':{'name':root['id']+'-manifest.json','sha256':digest(folder/(root['id']+'-manifest.json'))},
            'name':root['name'],'location':root['location'],'kind':root['kind'],
            'parts':[{'name':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in writer.paths],
            'files':len(files),'source_files':len(root['scan']['files']),'payload_bytes':sum(f['size'] for f in files)}
    save(folder/'parts.json',result)
    return result


class GitHub:
    def __init__(self,repo,tag):
        need(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo),'Invalid repository')
        need(re.fullmatch(r'archive-workstation-[a-z0-9-]+',tag),'Invalid archive tag')
        self.repo=repo;self.tag=tag
    def run(self,*args,check=True):
        p=subprocess.run(['gh',*args,'--repo',self.repo],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if check and p.returncode:raise ValueError('GitHub CLI failed: '+p.stderr.decode(errors='replace')[-1500:])
        return p
    def ensure(self,target,notes):
        p=self.run('release','view',self.tag,'--json','tagName,targetCommitish,isDraft',check=False)
        if p.returncode:
            self.run('release','create',self.tag,'--draft','--target',target,'--title','Workstation research archive '+self.tag,'--notes-file',str(notes))
        else:
            d=json.loads(p.stdout);need(d['targetCommitish']==target,'Existing release target differs')
    def download(self,name,folder,expected=None):
        need(re.fullmatch(r'[A-Za-z0-9_.-]+',name),'Invalid asset name')
        folder.mkdir(parents=True,exist_ok=True)
        self.run('release','download',self.tag,'--pattern',name,'--dir',str(folder))
        path=folder/name
        need(path.is_file(),'Missing downloaded asset '+name)
        if expected:need(digest(path)==expected,'Downloaded release asset SHA-256 mismatch: '+name)
        return path
    def upload(self,path,tmp):
        # Existing same-name assets are compared, never clobbered or silently replaced.
        with tempfile.TemporaryDirectory(prefix='eft-existing-',dir=tmp) as d:
            p=self.run('release','download',self.tag,'--pattern',path.name,'--dir',d,check=False)
            if p.returncode==0:
                need(digest(Path(d)/path.name)==digest(path),'An existing release asset has different bytes: '+path.name)
                return
        self.run('release','upload',self.tag,str(path))
    def publish(self):self.run('release','edit',self.tag,'--draft=false','--latest=false')


def verify_remote_root(gh,root_index,tmp,destination=None):
    with tempfile.TemporaryDirectory(prefix='eft-remote-read-',dir=tmp) as folder:
        folder=Path(folder)
        m=gh.download(root_index['manifest']['name'],folder,root_index['manifest']['sha256']);manifest=load(m)
        need(re.fullmatch(r'r[0-9]+',root_index['id']) and manifest['id']==root_index['id'],'Archive root identity differs')
        def fetch(part):
            checkpoint()
            log('Downloading and verifying archive part',root=root_index['id'],asset=part['name'])
            return gh.download(part['name'],folder,part['sha256'])
        with io.BufferedReader(SequenceReader(root_index['parts'],fetch)) as stream:count=verify_tar(stream,manifest,destination)
        need(count==root_index['files'],'Root payload file count differs from the master index')
    return manifest,count


def archive(session,repo,target,part_size):
    inv=load(session/'inventory.json')
    need(not any(r['scan']['blockers'] for r in inv['roots']),'Inventory has blockers. Review SUMMARY.md; nothing was uploaded or deleted.')
    need(MIB<=part_size<=GIB,'Part size must be between 1 MiB and 1 GiB')
    if (session/'CATALOG.json').exists():
        catalog=load(session/'CATALOG.json')
        need(catalog['repo']==repo,'Existing archive repository differs')
        verify(session);log('Completed archive retained; no sources overwritten');return
    tag='archive-workstation-'+inv['archive_id'];gh=GitHub(repo,tag)
    state_path=session/'archive-state.json'
    state=load(state_path) if state_path.exists() else {'schema_version':1,'archive_id':inv['archive_id'],'repo':repo,'tag':tag,'target':target,'tool_sha256':digest(Path(__file__)),'roots':[]}
    need((state['repo'],state['tag'],state['target'])==(repo,tag,target),'Archive destination/provenance changed on resume')
    need(state['tool_sha256']==digest(Path(__file__)),'Archive tool version changed on resume; keep the original package or take a new inventory')
    notes=session/'RELEASE-NOTES.md'
    notes.write_text('# Complete workstation research snapshot\n\n'+json.dumps(timestamp())+'\n\nSource bytes and Git object stores; compact repository catalog is separate. No scientific acceptance implied. Rebuildable Python caches/environments and Git credential/config/hooks are excluded. Each root is a separate, timestamped snapshot.\n')
    gh.ensure(target,notes)
    for root in inv['roots']:
        checkpoint()
        if any(r['id']==root['id'] for r in state['roots']):
            log('Previously verified archive root retained on resume',root=root['id']);continue
        folder=session/'staging'/root['id']
        if (folder/'parts.json').exists():
            idx=load(folder/'parts.json')
            for p in idx['parts']:need(digest(folder/p['name'])==p['sha256'],'Staged part changed')
            need(digest(folder/idx['manifest']['name'])==idx['manifest']['sha256'],'Staged manifest changed')
        else:
            # Generated incomplete cache is rebuilt only while the original inputs remain.
            if folder.exists():
                assert_unchanged(root)
                need(load(folder/'staging-owner.json')=={'source':root['source'],'id':root['id']},'Unknown staging folder; preserving it')
                old_manifest=folder/(root['id']+'-manifest.json')
                if old_manifest.exists():
                    for f in load(old_manifest)['files']:
                        if f['archive_path'].startswith('files/'):
                            source=Path(root['source'])
                            source=source/Path(f['archive_path']).relative_to('files') if source.is_dir() else source
                            need(digest(source)==f['sha256'],'Original bytes differ from incomplete archive; preserving both')
                shutil.rmtree(folder)
            log('Building source archive',root=root['id'],source=root['source'])
            idx=build_root(root,folder,part_size)
        for part in [idx['manifest'],*idx['parts']]:
            checkpoint()
            log('Uploading release asset',asset=part['name']);gh.upload(folder/part['name'],session)
        _,count=verify_remote_root(gh,idx,session)
        idx['verified_at']=timestamp();idx['remote_files_verified']=count;state['roots'].append(idx);save(state_path,state)
        # Only generated staging tarparts are removed; original source paths are untouched.
        for part in idx['parts']:(folder/part['name']).unlink()
        if (folder/'git').exists():shutil.rmtree(folder/'git')
        log('Remote root verified; generated staging parts removed',root=root['id'],files=count)
    state.setdefault('completed_at',timestamp())
    index=session/'ARCHIVE.json';save(index,state)
    restore=session/'RESTORE.py';shutil.copy2(Path(__file__),restore)
    # The public index anchors the restore tool and every root/part manifest.
    state['restore_tool_sha256']=digest(restore);save(index,state);save(state_path,state)
    gh.upload(index,session);gh.upload(restore,session)
    gh.publish()
    catalog={'schema_version':1,'recorded_at':timestamp(),'archive_id':inv['archive_id'],'repo':repo,'tag':tag,
             'release_url':f'https://github.com/{repo}/releases/tag/{tag}','index_sha256':digest(index),
             'restore_tool_sha256':digest(restore),'roots':len(state['roots']),
             'files':sum(r['files'] for r in state['roots']),'payload_bytes':sum(r['payload_bytes'] for r in state['roots']),
             'scope':'Remote tar payloads downloaded and SHA-256-verified for every member; no source deletion performed.'}
    save(session/'CATALOG.json',catalog)
    verify(session)  # Re-read the final public index and every root after publication.
    log('All selected roots archived and verified',catalog=str(session/'CATALOG.json'),release=catalog['release_url'])


def remote_index(catalog,tmp):
    gh=GitHub(catalog['repo'],catalog['tag'])
    with tempfile.TemporaryDirectory(prefix='eft-index-',dir=tmp) as d:
        p=gh.download('ARCHIVE.json',Path(d),catalog['index_sha256']);idx=load(p)
    need(idx['repo']==catalog['repo'] and idx['tag']==catalog['tag'],'Archive identity mismatch')
    return gh,idx


def verify(session):
    prior=session/'VERIFIED.json'
    if prior.exists():prior.replace(session/'VERIFIED.previous.json')
    catalog=load(session/'CATALOG.json');gh,idx=remote_index(catalog,session);counts={}
    for root in idx['roots']:
        _,n=verify_remote_root(gh,root,session);counts[root['id']]=n
    receipt={'recorded_at':timestamp(),'catalog_sha256':digest(session/'CATALOG.json'),'index_sha256':catalog['index_sha256'],
             'repo':catalog['repo'],'tag':catalog['tag'],'root_file_counts':counts,'status':'all_remote_bytes_verified',
             'source_deletion_supported':False}
    save(session/'VERIFIED.json',receipt);log('Remote archive verification complete',files=sum(counts.values()))
    return receipt


def restore_git(payload,target):
    state=load(payload/'state.json');gitdir=target/'.git'
    need(not gitdir.exists(),'Restore refuses an existing Git store')
    target.mkdir(parents=True,exist_ok=True)
    need(state['object_format'] in {'sha1','sha256'},'Unsupported Git object format')
    subprocess.run(['git','init','--bare','--quiet','--object-format='+state['object_format'],str(gitdir)],check=True)
    with (payload/'objects.pack').open('rb') as f:
        subprocess.run(['git','--git-dir',str(gitdir),'index-pack','--stdin'],stdin=f,stdout=subprocess.DEVNULL,check=True)
    for line in state['refs']:
        name,oid=line.split(' ',1)
        need(name.startswith('refs/') and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}',oid),'Invalid restored Git ref')
        subprocess.run(['git','--git-dir',str(gitdir),'update-ref',name,oid],check=True)
    if state['head_ref']:subprocess.run(['git','--git-dir',str(gitdir),'symbolic-ref','HEAD',state['head_ref']],check=True)
    else:subprocess.run(['git','--git-dir',str(gitdir),'update-ref','--no-deref','HEAD',state['head']],check=True)
    subprocess.run(['git','--git-dir',str(gitdir),'config','core.bare','false'],check=True)
    subprocess.run(['git','--git-dir',str(gitdir),'config','remote.origin.url','https://github.com/'+REPO+'.git'],check=True)
    if (payload/'index').exists():shutil.copy2(payload/'index',gitdir/'index')
    for p in payload.glob('sharedindex.*'):shutil.copy2(p,gitdir/p.name)
    restored=git_state(target)
    need(restored['object_ids']==state['object_ids'] and restored['refs']==state['refs'] and restored['head']==state['head'],
         'Restored Git graph does not match the snapshot')


def restore(catalog_path,destination,root_ids):
    catalog=load(catalog_path);need(not destination.exists(),'Restore destination must be a new directory')
    destination.mkdir(parents=True)
    gh,idx=remote_index(catalog,destination)
    selected=[r for r in idx['roots'] if not root_ids or r['id'] in root_ids]
    need(selected and (not root_ids or {r['id'] for r in selected}==set(root_ids)),'Unknown restore root ID')
    for root in selected:
        payload=destination/(root['id']+'-payload');payload.mkdir()
        manifest,_=verify_remote_root(gh,root,destination,payload)
        target=destination/manifest['location']
        if manifest['location']=='extra':target=target/root['id']
        target=target/manifest['name']
        need(not target.exists(),'Restore target already exists')
        if manifest['kind']=='file':
            target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(payload/'files'/manifest['name']),str(target))
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            if (payload/'files').exists():shutil.move(str(payload/'files'),str(target))
            else:target.mkdir()
            for d in manifest['directories']:(target/d).mkdir(parents=True,exist_ok=True)
            for i,g in enumerate(manifest['git_locations']):restore_git(payload/'git'/f'g{i:03d}',target/Path(g))
        log('Restored verified source root',root=root['id'],path=str(target))
    save(destination/'RESTORATION.json',{'recorded_at':timestamp(),'catalog':catalog,'roots':[r['id'] for r in selected],
         'scope':'Exact payload bytes/modes restored. Local credentials, hooks and rebuildable environments are not restored. Recorded absolute source paths remain historical; use explicit restored source roots with analysis tools.'})


def cleanup_plan(session):
    verify(session)  # A cleanup review uses fresh remote data, not a stale receipt.
    receipt=load(session/'VERIFIED.json');catalog=load(session/'CATALOG.json')
    need(receipt['catalog_sha256']==digest(session/'CATALOG.json') and receipt['index_sha256']==catalog['index_sha256'], 'Verification receipt differs from catalog')
    inv=load(session/'inventory.json');gh,idx=remote_index(catalog,session)
    need(set(receipt['root_file_counts'])=={r['id'] for r in inv['roots']},'Not every selected root was verified')
    rows=[]
    for root in inv['roots']:
        try:assert_unchanged(root);status='archived_and_unchanged'
        except (ValueError,OSError) as e:status='KEEP_SOURCE_CHANGED: '+str(e)
        rows.append({'id':root['id'],'path':root['source'],'status':status,
                     'retained_bytes':root['logical_bytes'],'excluded_rebuildable_directories':root['scan']['excluded']})
    save(session/'CLEANUP-REVIEW.json',{'recorded_at':timestamp(),'release':catalog['release_url'],'roots':rows,
        'deletion_performed':False,'instruction':'Review which checkout to retain and any changed roots. This tool has no source-delete command. Publish CATALOG.json in Git before any manual cleanup.'})
    log('Cleanup review written; no deletion performed',path=str(session/'CLEANUP-REVIEW.json'))


def registration(session):
    catalog=load(session/'CATALOG.json');receipt=load(session/'VERIFIED.json')
    need(re.fullmatch(r'[0-9]{8}t[0-9]{6}z-[0-9a-f]{8}',catalog['archive_id']),'Invalid archive ID')
    need(receipt['catalog_sha256']==digest(session/'CATALOG.json') and receipt['index_sha256']==catalog['index_sha256']
         and receipt['status']=='all_remote_bytes_verified','Archive lacks matching successful remote verification')
    dest=session/'registration'/'data'/'archives'/catalog['archive_id'];dest.mkdir(parents=True,exist_ok=True)
    for name in ['CATALOG.json','VERIFIED.json']:shutil.copy2(session/name,dest/name)
    idx=load(session/'ARCHIVE.json')
    lines=['# Verified workstation archive','',json.dumps(catalog['recorded_at']),
           '',f'Release: {catalog["release_url"]}',f'ARCHIVE.json SHA-256: `{catalog["index_sha256"]}`',
           '',f'{catalog["roots"]} roots; {catalog["files"]} archived payload files; {catalog["payload_bytes"]:,} payload bytes.',
           '', '| Root ID | Original location | Name | Payload files |','|---|---|---|---:|']
    for r in idx['roots']:lines.append(f'| {r["id"]} | {r["location"]} | {r["name"]} | {r["files"]} |')
    lines+=['','Release tarparts are at most 1 GiB each. They include all selected non-cache source files and complete Git object packs with refs, HEAD and index state.',
            'This is a current-workstation snapshot, not proof that missing historical fields have been recovered.',
            'Virtual environments/caches and local Git credentials/config/hooks are excluded. Numerical results and recorded absolute paths are not rewritten.',
            '', 'Restore to a new directory with the repository archive tool and this CATALOG.json. Select root IDs when only one dataset is needed.',
            'No source deletion was performed by archival or verification. Keep this catalog in the repository before reviewing local cleanup.']
    (dest/'README.md').write_text('\n'.join(lines)+'\n')
    log('Git catalog registration files prepared',path=str(dest))
    return dest


def main():
    global STOP_FILE,PROGRESS_FILE
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['inventory','archive','verify','restore','cleanup-plan','catalog'])
    p.add_argument('--home',type=Path,default=Path.home())
    p.add_argument('--work',type=Path,default=Path.home()/'EFT-archive-work')
    p.add_argument('--session',type=Path)
    p.add_argument('--include',type=Path,nargs='*',default=[],help='Additional explicit project/cache roots, e.g. a consolidated workspace under Projects')
    p.add_argument('--repo',default=REPO);p.add_argument('--target',default=TARGET)
    p.add_argument('--part-mib',type=int,default=1024)
    p.add_argument('--catalog',type=Path);p.add_argument('--destination',type=Path);p.add_argument('--roots',nargs='*')
    a=p.parse_args()
    if a.command=='inventory':inventory(a.home,a.work,a.include);return
    if a.command=='restore':
        need(a.catalog and a.destination,'Restore requires --catalog and --destination')
        restore(a.catalog.expanduser().resolve(),a.destination.expanduser().absolute(),a.roots);return
    session=a.session.expanduser().resolve() if a.session else Path(load(a.work.expanduser()/'latest.json')['session'])
    inv=load(session/'inventory.json')
    need(inv.get('schema_version')==1 and inv.get('archive_id')==session.name
         and re.fullmatch(r'[0-9]{8}t[0-9]{6}z-[0-9a-f]{8}',session.name),'Not an archive inventory session; no lock or output was created')
    import fcntl
    lock=(session/'operation.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('Another archive/verification operation is active for this session')
    STOP_FILE=session/'STOP';PROGRESS_FILE=session/'progress.json'
    done=threading.Event()
    def heartbeat():
        while not done.wait(30):
            save(session/'heartbeat.json',timestamp());log('WORKING',last_progress=dict(LAST_PROGRESS))
    threading.Thread(target=heartbeat,daemon=True).start()
    try:
        if a.command=='archive':archive(session,a.repo,a.target,a.part_mib*MIB)
        elif a.command=='verify':verify(session)
        elif a.command=='catalog':registration(session)
        else:cleanup_plan(session)
    finally:done.set();lock.close()


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError,KeyError) as error:
        log('STOPPED; original source paths remain untouched',error=str(error));sys.exit(1)
