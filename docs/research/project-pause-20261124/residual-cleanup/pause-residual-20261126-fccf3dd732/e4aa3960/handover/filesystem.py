"""Explicit project roots, immutable file maps and quarantined exact deletion."""
import hashlib,json,os,re,stat
from pathlib import Path
from common import need,sha,load,save,stamp,log
from capsule import no_symlinks
TOKEN=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|https?://[^\s/]+:[^\s/@]+@)')
SECRET_NAMES={'.netrc','.git-credentials','id_rsa','id_ed25519','credentials.json'}

def signature(path):
    s=Path(path).lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns]

def discover(home,settings,work,workspace):
    protect={home/n for n in settings['keep_home']}|{work,workspace};found=[];outside=[]
    for parent in [home,home/'Downloads',home/'git-recovery']:
        if not parent.is_dir() or parent.is_symlink():continue
        for p in sorted(parent.iterdir()):
            if any(p==q or q in p.parents or p in q.parents for q in protect):continue
            if any(p.name.startswith(prefix) for prefix in settings['prefixes']):found.append(p)
            elif parent!=home/'git-recovery':outside.append(str(p))
    selected=[]
    for p in sorted(set(found),key=lambda x:(len(x.parts),str(x))):
        if not any(q in p.parents for q in selected):selected.append(p)
    return selected,outside

def environment_dir(path):
    return ((path.name in ['.venv','venv','env'] or path.name.endswith('-browser-env')) and (path/'pyvenv.cfg').is_file()) or (path.name=='node_modules' and ((path.parent/'package-lock.json').is_file() or (path.parent/'yarn.lock').is_file() or (path.parent/'pnpm-lock.yaml').is_file()))

def runtime(path,root):
    if '__pycache__' in path.relative_to(root).parts:return True
    for parent in [path,*path.parents]:
        if parent==root.parent:break
        if environment_dir(parent):return True
    return False

def secret(path):
    if path.name in SECRET_NAMES or path.name=='.env' or (path.name.startswith('.env.') and path.name not in ['.env.example','.env.sample','.env.template']):return True
    if path.name in ['config','config.worktree'] and '.git' in path.parts:
        with path.open('rb') as f:data=f.read(4*1024**2);return bool(TOKEN.search(data) or re.search(rb'(?im)^\s*(?:extraheader|password|token)\s*=',data))
    return False

def hash_pieces(path,chunk_bytes):
    before=signature(path);need(stat.S_ISREG(before[2]),'Non-regular content file');whole=hashlib.sha256();pieces=[];offset=0
    with path.open('rb') as stream:
        while offset<before[3]:
            h=hashlib.sha256();length=min(chunk_bytes,before[3]-offset);left=length
            while left:
                data=stream.read(min(left,4*1024**2));need(data,'Source truncated during scan');h.update(data);whole.update(data);left-=len(data)
            pieces.append({'sha256':h.hexdigest(),'bytes':length,'offset':offset});offset+=length
            if before[3]>=1024**3 and (offset%(1024**3)==0 or offset==before[3]):log('Hashing large remaining file',path=str(path),bytes_checked=offset,total_bytes=before[3])
        need(not stream.read(1),'Source grew during scan')
    need(signature(path)==before,'Source changed during scan: '+str(path))
    # Represent empty files as one verified empty content object.
    if not pieces:pieces=[{'sha256':whole.hexdigest(),'bytes':0,'offset':0}]
    return whole.hexdigest(),pieces,before

def scan_root(path,root_id,base_objects,chunk_bytes):
    root={'id':root_id,'path':str(path),'kind':'symlink' if path.is_symlink() else 'directory' if path.is_dir() else 'file','blocked':[],'files':[],'links':[],'directories':[],'git_paths':[]};objects={}
    if root['kind']=='symlink':root['blocked'].append('Top-level symlink is retained; its external target was not followed');return root,objects
    no_symlinks(path)
    if root['kind']=='directory':
        entries=[]
        for directory,dirs,files in os.walk(path,followlinks=False):
            parent=Path(directory);root['directories'].append(str(parent.relative_to(path)))
            if '.git' in dirs and not runtime(parent,path):root['git_paths'].append(str(parent))
            if '.git' in files and not runtime(parent,path):root['blocked'].append('External/worktree Git pointer retained: '+str(parent/'.git'))
            for name in list(dirs):
                p=parent/name
                if p.is_symlink():entries.append(p);dirs.remove(name)
            entries.extend(parent/n for n in files)
    else:entries=[path]
    for index,p in enumerate(sorted(entries)):
        if index and index%2000==0:log('Scanning remaining files',root=str(path),files_checked=index,total_files=len(entries))
        relative=p.relative_to(path).as_posix() if root['kind']=='directory' else p.name;info={'relative':relative,'path':str(p),'signature':signature(p),'mode':stat.S_IMODE(p.lstat().st_mode)}
        if p.is_symlink():
            target=os.readlink(p);info.update(target=target,rebuildable=runtime(p,path) if root['kind']=='directory' else False)
            # Non-runtime external links may point to uncaptured scientific data.
            resolved=p.resolve(strict=False)
            if not info['rebuildable'] and not (resolved==path or path in resolved.parents):root['blocked'].append('External symlink target needs separate preservation: '+str(p))
            root['links'].append(info);continue
        if not stat.S_ISREG(info['signature'][2]):root['blocked'].append('Special file retained: '+str(p));continue
        if secret(p):root['blocked'].append('Credential-bearing local configuration retained: '+str(p));continue
        digest,pieces,before=hash_pieces(p,chunk_bytes);info.update(sha256=digest,bytes=before[3],rebuildable=runtime(p,path) if root['kind']=='directory' else False)
        if info['rebuildable']:info['storage']='rebuildable'
        elif digest in base_objects and base_objects[digest]['bytes']==before[3]:info['storage']='base'
        else:
            info['storage']='supplement';info['pieces']=[{'sha256':x['sha256'],'bytes':x['bytes']} for x in pieces]
            for x in pieces:objects.setdefault(x['sha256'],{'bytes':x['bytes'],'source':str(p),'offset':x['offset'],'source_signature':before})
        root['files'].append(info)
    # Bare Git repositories are captured byte-for-byte and given an independent bundle.
    if root['kind']=='directory' and (path/'HEAD').is_file() and (path/'objects').is_dir() and (path/'refs').is_dir():root['git_paths'].append(str(path))
    return root,objects

def unchanged(root,path=None):
    path=Path(path or root['path']);need(path.exists() and not path.is_symlink(),'Root is missing or changed type')
    expected={x['relative']:x for x in root['files']+root['links']};seen=set();directories=set()
    if root['kind']=='directory':
        entries=[]
        for directory,dirs,files in os.walk(path,followlinks=False):
            parent=Path(directory);directories.add(str(parent.relative_to(path)))
            for name in list(dirs):
                p=parent/name
                if p.is_symlink():entries.append(p);dirs.remove(name)
            entries.extend(parent/n for n in files)
    else:entries=[path]
    for p in entries:
        relative=p.relative_to(path).as_posix() if root['kind']=='directory' else Path(root['path']).name;need(relative in expected,'New/unclassified file appeared: '+str(p));row=expected[relative];seen.add(relative)
        if 'target' in row:need(p.is_symlink() and os.readlink(p)==row['target'],'Symlink changed: '+str(p))
        else:need(p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'File changed: '+str(p))
    need(seen==set(expected),'Root file set changed; retain this folder')
    if root['kind']=='directory':need(directories==set(root['directories']),'Directory structure changed; retain this folder')
    return True

def unlink_exact(path,digest,quarantine):
    """Git files allowed only inside this verified job's quarantine."""
    path=Path(path);need(quarantine in path.parents,'Deletion target is outside job quarantine');no_symlinks(path)
    directory=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            n=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory);os.close(directory);directory=n
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
        try:
            before=os.fstat(fd);need(stat.S_ISREG(before.st_mode),'Non-regular deletion target');h=hashlib.sha256()
            while True:
                data=os.read(fd,4*1024**2)
                if not data:break
                h.update(data)
            after=os.fstat(fd);current=os.stat(path.name,dir_fd=directory,follow_symlinks=False);key=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            need(key(before)==key(after)==key(current) and h.hexdigest()==digest,'Deletion target changed; retained');os.unlink(path.name,dir_fd=directory)
        finally:os.close(fd)
    finally:os.close(directory)

def active_paths(candidates):
    blocked={};pid_self=os.getpid()
    for proc in Path('/proc').glob('[0-9]*'):
        if int(proc.name)==pid_self:continue
        try:
            if proc.stat().st_uid!=os.getuid():continue
            paths=[]
            try:paths.append(Path(os.readlink(proc/'cwd')))
            except OSError:pass
            try:args=(proc/'cmdline').read_bytes().split(b'\0')
            except OSError:args=[]
            for a in args:
                if a.startswith(b'/'):
                    try:paths.append(Path(a.decode()))
                    except UnicodeDecodeError:pass
            for root in candidates:
                if any(p==root or root in p.parents for p in paths):blocked.setdefault(str(root),[]).append(int(proc.name))
        except (OSError,ValueError):continue
    return blocked
