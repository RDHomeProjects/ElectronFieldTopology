"""Hash-pinned selective recovery of retained higher-Q/low-Q reference fields. Apache-2.0.

Reads selected byte ranges from existing uncompressed Release tar segments. The exact
member SHA, metadata, root manifest and Git catalog anchor each restored field.
No archive is rewritten; no assumption that a coarse field is a stationary state.
"""
import hashlib,json,os,re,tarfile,time,urllib.error,urllib.request
from pathlib import Path
from .sf_checkpoints import timestamp,atomic_json
ROOT=Path(__file__).resolve().parents[2]
REPO='RDHomeProjects/ElectronFieldTopology'
GIB=1024**3

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(8*1024**2):h.update(block)
    return h.hexdigest()
def event(message,**data):print(json.dumps({'recorded_at':timestamp(),'message':message,**data}),flush=True)
def load(path):return json.loads(Path(path).read_text())

def member_position(manifest,name):
    """Recreate the unchanged archive writer's PAX header/padding offsets."""
    offset=0;found=[]
    for f in manifest['files']:
        i=tarfile.TarInfo(f['archive_path']);i.size=f['size'];i.mode=f['mode'];i.mtime=f['mtime_ns']//10**9
        position=offset+len(i.tobuf(format=tarfile.PAX_FORMAT))
        if f['archive_path']==name:found.append((position,f))
        offset=position+512*((f['size']+511)//512)
    need(len(found)==1,'Requested archive member missing or duplicated');return found[0]

def authenticate(spec,repo=ROOT):
    repo=Path(repo);catalog=load(repo/'data/archives'/spec['archive_id']/'CATALOG.json')
    index_path=repo/spec['index'];manifest_path=repo/spec['manifest'];index=load(index_path);manifest=load(manifest_path)
    need(sha(index_path)==catalog['index_sha256'],'Source archive index differs from Git catalog')
    roots=[r for r in index['roots'] if r['id']==spec['root_id']];need(len(roots)==1,'Source root identity differs');root=roots[0]
    need(sha(manifest_path)==root['manifest']['sha256'],'Source root manifest differs from anchored index')
    need(catalog['tag']==index['tag'] and catalog['repo']==index['repo']==REPO,'Unexpected source release')
    position,f=member_position(manifest,spec['archive_path'])
    need(position==spec['tar_offset'] and f['sha256']==spec['sha256'] and f['size']==spec['bytes'],'Source member identity/offset differs')
    need(all(p['bytes']>0 and re.fullmatch(r'r[0-9]{3}-part-[0-9]{5}\.tarpart',p['name']) for p in root['parts']),'Invalid source part descriptors')
    return catalog,index,root

def fetch_range(url,start,size,total):
    """Accept exactly the requested bytes; an ignored Range never becomes a bulk read."""
    last=None
    for attempt in range(3):
        try:
            request=urllib.request.Request(url+'?eft-select='+str(time.time_ns()),headers={'Range':f'bytes={start}-{start+size-1}','User-Agent':'ElectronFieldTopology-selective-restore'})
            with urllib.request.urlopen(request,timeout=90) as r:
                if r.status!=206:raise NotImplementedError('Server did not honor byte ranges')
                need(r.headers.get('Content-Range')==f'bytes {start}-{start+size-1}/{total}','Source Range metadata differs')
                data=r.read(size+1)
            need(len(data)==size,'Truncated/oversized source range');return data
        except urllib.error.HTTPError as error:
            if error.code not in [429,500,502,503,504]:raise
            last=error
        except (TimeoutError,urllib.error.URLError) as error:last=error
        if attempt<2:time.sleep(.5*(attempt+1))
    raise ValueError('Source range download failed after three read retries: '+str(last))

def full_part(url,part,cache):
    """Bounded fallback when Range is unsupported; authenticate the entire required part."""
    target=cache/part['name']
    if target.exists():need(target.stat().st_size==part['bytes'] and sha(target)==part['sha256'],'Cached source tarpart changed');return target
    tmp=target.with_suffix('.partial');event('Range unavailable; downloading one required source part',name=part['name'],bytes=part['bytes'])
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ElectronFieldTopology-selective-restore'}),timeout=90) as r,tmp.open('wb') as f:
            count=0
            while block:=r.read(8*1024**2):
                count+=len(block);need(count<=part['bytes'],'Oversized archive part');f.write(block)
        need(tmp.stat().st_size==part['bytes'] and sha(tmp)==part['sha256'],'Full fallback part SHA differs');tmp.replace(target)
    finally:tmp.unlink(missing_ok=True)
    return target

def recover(spec,cache,repo=ROOT):
    catalog,index,root=authenticate(spec,repo);cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    target=cache/(spec['key']+'-'+spec['sha256'][:16]+'.npz')
    if target.exists():need(sha(target)==spec['sha256'],'Cached source field changed');return target
    start=spec['tar_offset'];remaining=spec['bytes'];cursor=0;tmp=target.with_suffix('.partial');ranges=[]
    try:
        with tmp.open('wb') as output:
            for part in root['parts']:
                end=cursor+part['bytes']
                if cursor<=start<end and remaining:
                    offset=start-cursor;count=min(remaining,end-start);url=f"https://github.com/{REPO}/releases/download/{catalog['tag']}/{part['name']}"
                    event('Recovering selected scientific input',key=spec['key'],part=part['name'],offset=offset,bytes=count)
                    try:data=fetch_range(url,offset,count,part['bytes']);method='range'
                    except NotImplementedError:
                        p=full_part(url,part,cache)
                        with p.open('rb') as f:f.seek(offset);data=f.read(count)
                        method='whole-part-hash-verified'
                    output.write(data);ranges.append({'part':part['name'],'offset':offset,'bytes':count,'method':method});remaining-=count;start+=count
                cursor=end
        need(remaining==0 and tmp.stat().st_size==spec['bytes'] and sha(tmp)==spec['sha256'],'Recovered member SHA/size differs; no field accepted')
        tmp.replace(target);atomic_json(target.with_suffix('.json'),{'recorded_at':timestamp(),'source':spec,'range_reads':ranges,'scope':'Selected member hash verified against anchored manifest. Other files/parts were not re-downloaded.'})
    finally:tmp.unlink(missing_ok=True)
    return target

def validate_field(path,spec):
    import numpy as np
    from .skyrme import NORTH
    need(sha(path)==spec['sha256'],'Source field SHA differs')
    with np.load(path,allow_pickle=False) as d:
        n=d['field'].copy();need(n.dtype==np.float64 and n.shape==(spec['nodes'],)*3+(3,) and np.isfinite(n).all(),'Source field precision/geometry invalid')
        need(str(d['model_id'])==spec['model'] and int(d['expected_q'])==spec['q'] and abs(float(d['h'])-spec['length']/(spec['nodes']-1))<1e-14,'Source model/spacing/Q differs')
        if spec['model']=='SF-relativistic-neutral-v1':
            from .sf_time_run import SCHEME
            need(str(d['scheme'])==SCHEME and np.max(abs(d['field_rate']))==0,'Reference must be an exact-scheme rest state')
        need(np.max(abs(np.sum(n*n,axis=-1)-1))<1e-10,'Source unit constraint invalid')
        for axis in range(3):
            for sl in [slice(0,2),slice(-2,None)]:
                cut=[slice(None)]*3;cut[axis]=sl;need(np.max(abs(n[tuple(cut)]-NORTH))<1e-12,'Source held layers differ')
        metadata={k:str(d[k]) for k in ['model_id','expected_q','h','config_sha256']}
    return n,{'recorded_at':timestamp(),'path':str(Path(path).resolve()),'sha256':spec['sha256'],'metadata':metadata}
