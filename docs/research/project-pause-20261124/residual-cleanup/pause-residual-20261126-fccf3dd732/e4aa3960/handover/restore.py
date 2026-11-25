#!/usr/bin/env python3
"""Restore selected residual project roots from base and supplemental assets."""
import argparse,gzip,json,os,shutil,tempfile
from pathlib import Path,PurePosixPath
from common import need,sha,save,load,stamp,log
from capsule import inspect_part,no_symlinks
from transport import Remote

def read(path):
    with gzip.open(path,'rt') as f:return json.load(f)
def safe(name):
    p=PurePosixPath(name);need(not p.is_absolute() and '..' not in p.parts and '\\' not in name,'Unsafe restore path');return p

def restore(manifest_path,proof_path,base_path,destination,root_ids=None,remote=None):
    plan=read(manifest_path);proof=load(proof_path);info=next(x for x in proof['metadata'] if x['name']=='RESIDUAL-MANIFEST.json.gz');need(sha(manifest_path)==info['sha256'] and sha(base_path)==plan['base_manifest_sha256']==proof['base_manifest_sha256'],'Manifest proof binding differs');need(proof['all_new_objects_downloaded_and_rehashed'],'Incomplete supplement verification');base=read(base_path);roots=[r for r in plan['roots'] if not r['blocked'] and (not root_ids or r['id'] in root_ids)];need(not root_ids or {r['id'] for r in roots}==set(root_ids),'Unknown or retained/unarchived root requested');destination=Path(destination).absolute();no_symlinks(destination);identity=destination/'RESTORE-JOB.json'
    if identity.exists():need(load(identity)['manifest_sha256']==sha(manifest_path) and load(identity)['roots']==sorted(r['id'] for r in roots),'Another restore job uses this destination')
    else:
        need(not destination.exists() or not any(destination.iterdir()),'Use a fresh restore destination');destination.mkdir(parents=True,exist_ok=True);save(identity,{'recorded_at':stamp(),'manifest_sha256':sha(manifest_path),'roots':sorted(r['id'] for r in roots)})
    remote=remote or Remote('RDHomeProjects/ElectronFieldTopology');wanted={'base':{},'supplement':{}};outputs=[]
    def put(store,pieces,target,whole,size,mode):
        no_symlinks(target)
        if target.exists():need(target.is_file() and sha(target)==whole,'Existing restored file differs: '+str(target));return
        target.parent.mkdir(parents=True,exist_ok=True);partial=target.with_name(target.name+'.restore-partial');no_symlinks(partial)
        with partial.open('a+b') as f:f.truncate(size)
        offset=0
        for piece in pieces:wanted[store].setdefault(piece['sha256'],[]).append((partial,offset,piece['bytes']));offset+=piece['bytes']
        need(offset==size,'File chunk geometry differs');outputs.append((partial,target,whole,mode))
    for root in roots:
        prefix=destination/'roots'/root['id']
        for row in root['files']:
            if row['storage']=='rebuildable':continue
            p=prefix/safe(row['relative']);pieces=[{'sha256':row['sha256'],'bytes':row['bytes']}] if row['storage']=='base' else row['pieces'];put(row['storage'],pieces,p,row['sha256'],row['bytes'],row['mode'])
    for g in plan['git']:
        if g['root_id'] in {r['id'] for r in roots}:put('supplement',g['pieces'],destination/'bundles'/safe(g['bundle_name']),g['sha256'],g['bytes'],0o600)
    pending=sum(p.stat().st_size for p,_,_,_ in outputs);need(shutil.disk_usage(destination).free>=pending+4*1024**3,'Need space for restored files plus 4 GiB bounded staging')
    for store,catalog,rid in [('base',base,plan['base_release_id']),('supplement',plan,plan['release_id'])]:
        for part in catalog['parts']:
            selected=set(part['objects'])&set(wanted[store])
            if not selected:continue
            asset={'id':part['asset_id'],'name':part['name'],'size':part['bytes']}
            with tempfile.TemporaryDirectory(prefix='part-',dir=destination) as tmp:
                folder=Path(tmp);archive=remote.download(asset,folder/part['name']);need(sha(archive)==part['sha256'],'Restoration part SHA differs');retained={d:folder/d for d in selected};inspect_part(archive,part,catalog['objects'],retained)
                for digest in selected:
                    for path,offset,count in wanted[store][digest]:
                        with path.open('r+b') as target,retained[digest].open('rb') as source:target.seek(offset);shutil.copyfileobj(source,target);target.flush();os.fsync(target.fileno())
            log('Restore part downloaded and verified',store=store,name=part['name'])
    for temporary,target,digest,mode in outputs:need(sha(temporary)==digest,'Reconstructed whole-file SHA differs: '+str(target));temporary.chmod(mode&0o777);temporary.replace(target)
    for root in roots:
        prefix=destination/'roots'/root['id'];prefix.mkdir(parents=True,exist_ok=True)
        for link in root['links']:
            if link['rebuildable']:continue
            target=prefix/safe(link['relative']);no_symlinks(target.parent);target.parent.mkdir(parents=True,exist_ok=True);original=Path(link['path']);resolved=(original.parent/Path(link['target'])).resolve(strict=False) if not Path(link['target']).is_absolute() else Path(link['target']);relative=resolved.relative_to(Path(root['path']));mapped=prefix/relative;value=os.path.relpath(mapped,target.parent)
            if target.is_symlink():need(os.readlink(target)==value,'Existing restore link differs')
            else:need(not target.exists(),'Existing restore link target is occupied');target.symlink_to(value)
    save(destination/'ORIGINAL-ROOTS.json',[{'id':r['id'],'original':r['path']} for r in roots]);save(destination/'RESTORE-COMPLETE.json',{'recorded_at':stamp(),'roots':len(roots),'restored_files':len(outputs),'all_reconstructed_file_hashes_passed':True,'rebuildable_environments_omitted':True,'scientific_steps':0});return destination

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--proof',type=Path,required=True);p.add_argument('--base-manifest',type=Path,required=True);p.add_argument('--destination',type=Path);p.add_argument('--root',action='append',default=[]);p.add_argument('--list',action='store_true');a=p.parse_args()
    if a.list:
        for r in read(a.manifest)['roots']:print(r['id'],r['path'],'RETAINED/UNARCHIVED' if r['blocked'] else 'RESTORABLE')
    else:need(a.destination,'Supply --destination or --list');restore(a.manifest,a.proof,a.base_manifest,a.destination,a.root)
if __name__=='__main__':main()
