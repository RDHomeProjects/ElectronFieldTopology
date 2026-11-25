#!/usr/bin/env python3
"""Restore verified GitHub Release bytes into a fresh directory; standard library."""
import argparse,gzip,json,os,shutil,subprocess,tempfile
from pathlib import Path,PurePosixPath
from common import sha,need,save,load,stamp,log
from capsule import inspect_part,no_symlinks

def safe_relative(name):
    p=PurePosixPath(name);need(not p.is_absolute() and '..' not in p.parts and '\\' not in name and '\x00' not in name,'Unsafe restore path');return p

def install_file(source,target,digest):
    no_symlinks(target);target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():need(target.is_file() and sha(target)==digest,'Existing restore file differs: '+str(target));return
    temporary=target.with_name(target.name+'.archive-tmp');need(not temporary.exists(),'Restore temporary file exists; inspect/remove it before retry: '+str(temporary));shutil.copyfile(source,temporary);need(sha(temporary)==digest,'Restored copy hash differs');temporary.replace(target)

def restore(manifest,proof,destination,mode='restart',root_ids=None,fetch=None):
    with gzip.open(manifest,'rt') as stream:plan=json.load(stream)
    verification=load(proof);entry=next(x for x in verification['metadata'] if x['name']=='MATTER-WAVES-ARCHIVE.json.gz');need(sha(manifest)==entry['sha256'],'Manifest differs from uploaded verification proof');need(verification['all_parts_downloaded_and_objects_rehashed'] and verification['tag']==plan['tag'],'Invalid archive proof')
    destination=Path(destination).absolute();no_symlinks(destination);identity=destination/'RESTORE-JOB.json'
    if identity.exists():need(load(identity)['manifest_sha256']==sha(manifest) and load(identity)['mode']==mode and load(identity)['roots']==sorted(root_ids or []),'Different restore job already uses this directory')
    else:
        need(not destination.exists() or not any(destination.iterdir()),'Choose a fresh restore directory');destination.mkdir(parents=True,exist_ok=True);save(identity,{'recorded_at':stamp(),'manifest_sha256':sha(manifest),'mode':mode,'roots':sorted(root_ids or [])})
    roots={x['id']:x for x in plan['roots']};targets={};git_items=plan['git'] if mode=='full' else [plan['primary_git']]
    def target(digest,path):targets.setdefault(digest,[]).append(path)
    for item in git_items:target(item['bundle_sha256'],destination/'bundles'/item['bundle_name'])
    if mode=='restart':
        for item in plan['required']:target(item['sha256'],destination/'code/numerical'/safe_relative(item['relative_to_numerical_repo']))
        # Bring the actual run identities, per-checkpoint seals, source settings,
        # measurements and frozen handover alongside the numerical state.
        required_paths=[safe_relative(x['relative_to_numerical_repo']) for x in plan['required']]
        run_prefixes={str(Path(*p.parts[:3]))+'/' for p in required_paths if len(p.parts)>=4}
        primary_path=Path(plan['primary_git']['source'])
        for row in plan['files']:
            original=Path(row['path'])
            if primary_path not in original.parents:continue
            relative=original.relative_to(primary_path).as_posix()
            if any(relative.startswith(prefix) for prefix in run_prefixes) and not relative.endswith('.npz'):
                target(row['sha256'],destination/'code/numerical'/safe_relative(relative))
    else:
        if root_ids:need(set(root_ids)<=set(roots),'Unknown selected root ID')
        for row in plan['files']:
            if root_ids and row['root_id'] not in root_ids:continue
            base=roots[row['root_id']];relative=safe_relative(row['relative_path']) if base['kind']=='directory' else PurePosixPath(Path(base['path']).name)
            target(row['sha256'],destination/'roots'/row['root_id']/relative)
    # Clone source before adding field files. This permits native iteration restart.
    pending={d for d,paths in targets.items() if any(not p.is_file() or sha(p)!=d for p in paths)}
    planned=sum(plan['objects'][d]['bytes']*len(targets[d]) for d in pending);need(shutil.disk_usage(destination).free>=planned+2*1024**3,'Insufficient free disk for requested restore plus bounded staging')
    if fetch is None:
        def fetch(name,folder):
            subprocess.run(['gh','release','download',plan['tag'],'--repo','RDHomeProjects/ElectronFieldTopology','--pattern',name,'--dir',str(folder)],check=True);return folder/name
    primary=plan['primary_git'];code=destination/'code/numerical'
    def clone_if_ready():
        bundle=destination/'bundles'/primary['bundle_name']
        # Deduplicated bundle hashes may have another retained name as well.
        if not bundle.is_file():return
        if not (code/'.git').exists():
            need(not code.exists() or not any(code.iterdir()),'Code destination contains files before Git restore');code.parent.mkdir(parents=True,exist_ok=True);subprocess.run(['git','clone','--no-checkout',str(bundle),str(code)],check=True)
        result=subprocess.run(['git','-C',str(code),'rev-parse','HEAD'],capture_output=True,text=True)
        if result.returncode!=0 or result.stdout.strip()!=primary['head']:subprocess.run(['git','-C',str(code),'checkout','--detach',primary['head']],check=True)
        else:subprocess.run(['git','-C',str(code),'checkout','--detach',primary['head']],check=True)
    # Bundle-containing parts first, so checkpoint paths are created after Git clone.
    bundle_hashes={x['bundle_sha256'] for x in git_items};parts=sorted(plan['parts'],key=lambda p:(primary['bundle_sha256'] not in p['objects'],not bool(set(p['objects'])&bundle_hashes)))
    for part in parts:
        selected=set(part['objects'])&pending
        if not selected:continue
        with tempfile.TemporaryDirectory(prefix='restore-part-',dir=destination) as tmp:
            folder=Path(tmp);path=fetch(part['name'],folder);need(sha(path)==part['sha256'],'Release part SHA differs');objects={d:folder/('object-'+d) for d in selected};inspect_part(path,part,plan['objects'],objects)
            for d in selected&bundle_hashes:
                for p in targets[d]:install_file(objects[d],p,d)
            clone_if_ready()
            for d in selected-bundle_hashes:
                for p in targets[d]:install_file(objects[d],p,d)
        log('Restore part verified',name=part['name'],selected_objects=len(selected))
    clone_if_ready()
    for digest,paths in targets.items():
        for p in paths:need(p.is_file() and sha(p)==digest,'Final restore check failed: '+str(p))
    save(destination/'ORIGINAL-ROOTS.json',plan['roots']);save(destination/'RESTORE-COMPLETE.json',{'recorded_at':stamp(),'tag':plan['tag'],'mode':mode,'logical_files_verified':sum(map(len,targets.values())),'source_head':primary['head'],'symlinks_restored':0,'runtime_environments':'Recreate with pinned uv locks; runtime symlinks are listed in the archive manifest but not recreated','no_scientific_steps_executed':True});return destination

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--proof',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--mode',choices=['restart','full'],default='restart');p.add_argument('--root',action='append',default=[]);a=p.parse_args();restore(a.manifest,a.proof,a.destination,a.mode,a.root)
if __name__=='__main__':main()
