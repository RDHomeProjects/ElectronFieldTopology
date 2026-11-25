"""Bounded content-addressed parts and strict restore checks; no extraction by path."""
import ast,gzip,hashlib,io,json,math,os,shutil,stat,struct,tarfile,tempfile,zipfile
from pathlib import Path,PurePosixPath
from common import need,sha,save,load,stamp
CHUNK=4*1024**2

def signature(path):
    s=Path(path).stat(follow_symlinks=False);return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns]

def no_symlinks(path):
    p=Path(path);need(p.is_absolute(),'Absolute file path required')
    for parent in [*reversed(p.parents),p]:need(not parent.is_symlink(),'Symlink in source/deletion path: '+str(parent))

def partition(objects,limit):
    bins=[];sizes=[]
    for digest,obj in sorted(objects.items(),key=lambda x:(-x[1]['bytes'],x[0])):
        cost=((obj['bytes']+511)//512+1)*512;need(cost+10240<=limit,'Object exceeds registered part geometry: '+digest)
        target=next((i for i,v in enumerate(sizes) if v+cost+10240<=limit),None)
        if target is None:target=len(bins);bins.append([]);sizes.append(0)
        bins[target].append(digest);sizes[target]+=cost
    return [{'name':f'data-{i:04d}.tar.gz','objects':sorted(items),'uncompressed_bytes':sizes[i]} for i,items in enumerate(bins)]

class DigestReader:
    def __init__(self,stream):self.stream=stream;self.digest=hashlib.sha256();self.count=0
    def read(self,size=-1):
        value=self.stream.read(size);self.digest.update(value);self.count+=len(value);return value

def make_part(path,part,objects):
    path=Path(path);temporary=path.with_suffix('.tmp');path.parent.mkdir(parents=True,exist_ok=True)
    with temporary.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=3) as compressed,tarfile.open(fileobj=compressed,mode='w|',format=tarfile.USTAR_FORMAT) as archive:
        for digest in part['objects']:
            obj=objects[digest];source=Path(obj['source']);no_symlinks(source);before=signature(source);need(before[2]==obj['bytes'],'Source size changed: '+str(source))
            info=tarfile.TarInfo('objects/'+digest);info.size=obj['bytes'];info.mode=0o444;info.mtime=0;info.uid=info.gid=0
            with source.open('rb') as stream:
                reader=DigestReader(stream);archive.addfile(info,reader)
                need(reader.count==obj['bytes'] and reader.digest.hexdigest()==digest,'Source hash changed: '+str(source))
            need(signature(source)==before,'Source changed during part build: '+str(source))
    temporary.replace(path);return {'name':part['name'],'sha256':sha(path),'bytes':path.stat().st_size}

def numpy_header(stream):
    need(stream.read(6)==b'\x93NUMPY','Invalid NPY signature');version=stream.read(2);need(version[0] in [1,2,3],'Unsupported NPY version');size=struct.unpack('<H' if version[0]==1 else '<I',stream.read(2 if version[0]==1 else 4))[0];need(size<=65536,'Oversized NPY header');header=ast.literal_eval(stream.read(size).decode('utf-8' if version[0]==3 else 'latin1'));need(isinstance(header,dict),'Invalid NPY header');return header

def checkpoint_check(path,expectation):
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None,'Restored checkpoint CRC failed');key='n.npy' if 'n.npy' in z.namelist() else 'field.npy';need(key in z.namelist(),'No native field array in restored checkpoint')
        with z.open(key) as stream:h=numpy_header(stream)
        need(h['descr'] in ['<f8','=f8'] and tuple(h['shape'])==(expectation['nodes'],)*3+(3,),'Restored field precision/shape differs')
        iteration=None
        if 'iteration.npy' in z.namelist():
            with z.open('iteration.npy') as stream:
                meta=numpy_header(stream);need(meta['descr'] in ['<i8','=i8'],'Unsupported native iteration type');iteration=struct.unpack('<q',stream.read(8))[0]
        if expectation.get('iteration') is not None:need(iteration==expectation['iteration'],'Restored native iteration differs')
        alpha=None
        if expectation.get('optimizer_memory'):
            need('alpha.npy' in z.namelist(),'Restored continuation alpha missing')
            with z.open('alpha.npy') as stream:
                header=numpy_header(stream);need(header['descr'] in ['<f8','=f8'] and tuple(header['shape'])==(),'Invalid continuation alpha header');alpha=struct.unpack('<d',stream.read(8))[0]
            need(math.isfinite(alpha) and alpha>0,'Invalid continuation alpha')
            for key in ['old_g.npy','old_z.npy','direction.npy']:
                need(key in z.namelist(),'Restored continuation memory missing')
                with z.open(key) as stream:header=numpy_header(stream)
                need(header['descr'] in ['<f8','=f8'] and tuple(header['shape'])==(expectation['nodes'],)*3+(3,),'Restored optimizer-memory geometry differs')
    return {'passed':True,'nodes':expectation['nodes'],'iteration':iteration,'optimizer_memory_checked':bool(expectation.get('optimizer_memory')),'alpha':alpha}

def inspect_part(path,part,objects,retain):
    expected=set(part['objects']);seen=set();proof=[]
    with tarfile.open(path,mode='r|gz') as archive:
        for member in archive:
            need(member.isfile() and member.name.startswith('objects/'),'Unexpected archive member type/name');digest=member.name[8:]
            need(digest in expected and digest not in seen and member.name=='objects/'+digest,'Unexpected or duplicate content member');need(member.size==objects[digest]['bytes'],'Restored object size differs')
            target=retain.get(digest);handle=None;temporary=None
            if target:
                target=Path(target);target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix('.tmp');handle=temporary.open('wb')
            h=hashlib.sha256();count=0
            try:
                stream=archive.extractfile(member)
                while True:
                    chunk=stream.read(CHUNK)
                    if not chunk:break
                    h.update(chunk);count+=len(chunk)
                    if handle:handle.write(chunk)
            finally:
                if handle:handle.flush();os.fsync(handle.fileno());handle.close()
            need(count==member.size and h.hexdigest()==digest,'Downloaded object hash mismatch')
            if temporary:temporary.replace(target)
            seen.add(digest);proof.append(digest)
    need(seen==expected,'Archive part has missing objects');return proof

def exact_unlink(path,expected,allowed_roots):
    """Delete only the rehashed regular file through verified, non-symlink parents."""
    path=Path(path);need(any(path==r or r in path.parents for r in allowed_roots),'Deletion is outside the recorded roots');need('.git' not in path.parts,'Git internals are protected');no_symlinks(path)
    directory=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            nextfd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory);os.close(directory);directory=nextfd
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
        try:
            before=os.fstat(fd);need(stat.S_ISREG(before.st_mode),'Deletion target is not a regular file');h=hashlib.sha256()
            while True:
                chunk=os.read(fd,CHUNK)
                if not chunk:break
                h.update(chunk)
            after=os.fstat(fd);current=os.stat(path.name,dir_fd=directory,follow_symlinks=False)
            need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'Deletion target changed during verification')
            need((current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns,current.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'Deletion path changed during verification')
            need(h.hexdigest()==expected,'Deletion target content changed; retained');os.unlink(path.name,dir_fd=directory)
        finally:os.close(fd)
    finally:os.close(directory)
