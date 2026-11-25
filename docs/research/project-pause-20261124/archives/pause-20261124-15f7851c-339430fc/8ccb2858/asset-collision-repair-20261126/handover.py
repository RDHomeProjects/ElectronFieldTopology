#!/usr/bin/env python3
"""Resume the verified 69-part archive after a metadata asset-name collision."""
import argparse,fcntl,hashlib,importlib,importlib.util,json,os,shutil,subprocess,sys,zipfile
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent

def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for c in iter(lambda:f.read(8*1024**2),b''):h.update(c)
    return h.hexdigest()

def verify_self():
    entries={}
    for line in (ROOT/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1);p=Path(name)
        if p.is_absolute() or '..' in p.parts or name in entries or digest(ROOT/name)!=expected:raise RuntimeError('Repair payload checksum differs: '+name)
        entries[name]=expected
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256SUMS' and '__pycache__' not in p.parts}
    if actual!=set(entries):raise RuntimeError('Repair checksum coverage differs')
    return len(entries)

def load_original(package):
    if digest(package/'SHA256SUMS')!='f86092d2acb08acec88515f301533dddf062ab5c24c490596e9beee02dc98c8b':raise RuntimeError('Original package identity differs; use the unchanged delivered pause-archive package')
    sys.path.insert(0,str(package));module=importlib.import_module('archive');module.verify_package();return module

def preserve_repair(archive,work):
    destination=work/'asset-collision-repair-20261126';destination.mkdir(exist_ok=True)
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:continue
        target=destination/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():archive.need(digest(target)==digest(p),'Recorded repair payload differs')
        else:shutil.copyfile(p,target)
    return destination

def augment_publication(archive,publication,repo,pub,work):
    state=publication.execute('install',repo,pub,work)
    if state['phase']!='applied':return state
    plan=archive.read_plan(work);snapshot=archive.sha(work/'CLEANUP-RECEIPT.json');prefix=publication.DOC/'archives'/plan['tag']/snapshot[:8]/'asset-collision-repair-20261126';paths=[]
    for p in sorted((work/'asset-collision-repair-20261126').rglob('*')):
        if p.is_file():
            relative=prefix/p.relative_to(work/'asset-collision-repair-20261126');target=pub/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():archive.need(digest(target)==digest(p),'Published repair record differs')
            else:shutil.copyfile(p,target)
            name=relative.as_posix();state['immutable_files'][name]=digest(p);paths.append(name)
    for name in ['DRAFT-RELEASE-ID.json','DRAFT-REPAIR-APPLIED.json','ASSET-REPAIR-APPLIED.json','ASSET-COMPARISONS.jsonl','ASSET-COLLISION-DIAGNOSTIC.json']:
        p=work/name
        if p.is_file():
            relative=prefix/name;target=pub/relative
            if target.exists():archive.need(digest(target)==digest(p),'Pinned repair provenance differs')
            else:shutil.copyfile(p,target)
            state['immutable_files'][relative.as_posix()]=digest(p);paths.append(relative.as_posix())
    publication.cmd(pub,['git','add','-f','--',*paths]);state['stage_paths']=sorted(set(state['stage_paths'])|set(paths));archive.save(publication.marker(pub),state);publication.checks(pub,state);return state

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','preflight','upload','verify-remote','cleanup','install','publish','merge','collect','status']);p.add_argument('--package',type=Path,default=Path.home()/'Downloads/ElectronFieldTopology-pause-archive-20261124');p.add_argument('--work',type=Path,default=Path.home()/'MatterWaves-PauseArchive/20261124t103512z-15f7851c');p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-adaptive-q-screen-20261117');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-pause-archive-publication-20261124');a=p.parse_args();count=verify_self();archive=load_original(a.package.absolute());work=a.work.absolute();archive.need(work.is_dir(),'Use the existing prepared archive job; do not create a new one');archive.no_symlinks(work)
    with (work/'SESSION.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another archive/cleanup command is running; leave it running')
        plan=archive.read_plan(work);archive.need(plan['tag']=='pause-20261124-15f7851c-339430fc' and plan['main_commit']=='8d3f5d8bc31cf36b09283d390f9eeba0b696fafd','Prepared archive differs from the supplied terminal log; preserve it and seek an identity-specific repair');preserve_repair(archive,work)
        from asset_api import install as install_assets
        audit_manifest=install_assets(archive,work)
        from draft_api import install
        install(archive,work)
        provenance=work/'ASSET-REPAIR-APPLIED.json'
        if not provenance.exists():archive.save(provenance,{'recorded_at':archive.stamp(),'repair_sha256':digest(ROOT/'SHA256SUMS'),'original_package_sha256':digest(a.package/'SHA256SUMS'),'plan_sha256':digest(work/'PLAN.json.gz'),'tag':plan['tag'],'data_files_deleted_by_repair':0,'original_package_modified':False})
        if a.mode=='verify':archive.log('Archive asset repair and original archive plan verified',repair_files=count,tag=plan['tag'],parts=len(plan['parts']),source_deletions=0);return
        if a.mode=='preflight':
            current=archive.ensure_release(plan);archive.log('Existing release located by ID',release_id=current['id'],tag=current['tag_name'],draft=current['draft'],assets=len(current['assets']),source_deletions=0);audit_manifest(plan)
        elif a.mode=='upload':archive.upload(work,a.repo)
        elif a.mode=='verify-remote':archive.log('Verified archive confirmed',release_url=archive.verify_remote(work)['html_url'])
        elif a.mode=='cleanup':archive.cleanup(work)
        elif a.mode=='status':archive.log('Archive status',status=archive.load(work/'STATUS.json'),parts_download_verified=len(archive.load(work/'TRANSFER.json')['parts']) if (work/'TRANSFER.json').exists() else 0,part_count=len(plan['parts']),upload_proof_present=(work/'VERIFIED-UPLOAD.json').exists(),pinned_release=archive.load(work/'DRAFT-RELEASE-ID.json') if (work/'DRAFT-RELEASE-ID.json').exists() else None)
        elif a.mode=='collect':
            original=importlib.util.spec_from_file_location('original_pause_handover',a.package/'handover.py');module=importlib.util.module_from_spec(original);original.loader.exec_module(module);output=module.collect(work)
            # Add small repair provenance and reseal the collection.
            with zipfile.ZipFile(output) as z:payload={n:z.read(n) for n in z.namelist() if n!='SHA256SUMS'}
            for name in ['DRAFT-RELEASE-ID.json','DRAFT-REPAIR-APPLIED.json','ASSET-REPAIR-APPLIED.json','ASSET-COMPARISONS.jsonl','ASSET-COLLISION-DIAGNOSTIC.json']:
                if (work/name).is_file():payload[name]=(work/name).read_bytes()
            payload['SHA256SUMS']=''.join(hashlib.sha256(v).hexdigest()+'  '+n+'\n' for n,v in sorted(payload.items())).encode()
            temporary=output.with_suffix('.tmp')
            with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
                for n,v in payload.items():z.writestr(n,v)
            temporary.replace(output);archive.log('Completion evidence with repair provenance ready',output=str(output),sha256=digest(output))
        else:
            import publication
            state=augment_publication(archive,publication,a.repo,a.publication,work) if a.mode=='install' else publication.execute(a.mode,a.repo,a.publication,work);archive.log('Archive publication',phase=state['phase'],pr=state.get('pr'))
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.CalledProcessError) as exc:
        now=datetime.now(timezone.utc);print(json.dumps({'recorded_at':{'utc':now.isoformat(),'melbourne':now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()},'message':'Archive asset repair stopped','error':str(exc)}),flush=True);sys.exit(1)
