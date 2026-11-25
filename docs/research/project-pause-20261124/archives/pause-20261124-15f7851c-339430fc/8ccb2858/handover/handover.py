#!/usr/bin/env python3
"""Archive first, download verify, then delete unchanged inventoried records."""
import argparse,fcntl,json,os,subprocess,sys,zipfile
from pathlib import Path
import archive
from common import ROOT,sha,save,load,stamp,need,log

def collect(work):
    archive.read_plan(work);output=work/'completion-evidence.zip';names=['STATUS.json','IDENTITY.json','VERIFIED-UPLOAD.json','PROOF-ASSET.json','CLEANUP-RECEIPT.json','CLEANUP-ASSET.json','LAST-REMOTE-CHECK.json','STAGING-PRUNED.json','MATTER-WAVES-ARCHIVE.json.gz','DELETIONS.jsonl.gz']
    payload={name:(work/name).read_bytes() for name in names if (work/name).is_file()};payload['RESTORE.md']=(ROOT/'RESTORE.md').read_bytes();payload['KNOWN-STATE.json']=(ROOT/'KNOWN-STATE.json').read_bytes()
    import hashlib
    payload['SHA256SUMS']=''.join(hashlib.sha256(value).hexdigest()+'  '+name+'\n' for name,value in sorted(payload.items())).encode()
    with zipfile.ZipFile(output.with_suffix('.tmp'),'w',zipfile.ZIP_DEFLATED) as z:
        for name,value in payload.items():z.writestr(name,value)
    output.with_suffix('.tmp').replace(output);log('Archive/cleanup assessment evidence ready',output=str(output),sha256=sha(output));return output

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','prepare','upload','verify-remote','cleanup','install','publish','merge','status','collect']);p.add_argument('--work',type=Path,default=Path.home()/'MatterWaves-PauseArchive/20261124t103512z-15f7851c');p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-adaptive-q-screen-20261117');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-pause-archive-publication-20261124');a=p.parse_args();a.work=a.work.absolute();a.repo=a.repo.absolute();a.publication=a.publication.absolute()
    if a.mode=='verify':log('Archive handover and sealed inventory verified',files=archive.verify_package(),inventory=archive.SPEC['inventory_id'],scientific_steps=0);return
    a.work.mkdir(parents=True,exist_ok=True);archive.no_symlinks(a.work)
    with (a.work/'SESSION.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another archive/cleanup command holds the session lock; leave it running')
        if a.mode=='prepare':archive.prepare(a.work,a.repo)
        elif a.mode=='upload':archive.verify_package();archive.upload(a.work,a.repo)
        elif a.mode=='verify-remote':log('Published archive assets confirmed',release_url=archive.verify_remote(a.work)['html_url'])
        elif a.mode=='cleanup':archive.verify_package();archive.cleanup(a.work)
        elif a.mode=='collect':collect(a.work)
        elif a.mode=='status':
            log('Archive/cleanup status',work=str(a.work),status=load(a.work/'STATUS.json') if (a.work/'STATUS.json').exists() else {'status':'not_prepared'},last_remote_check=load(a.work/'LAST-REMOTE-CHECK.json') if (a.work/'LAST-REMOTE-CHECK.json').exists() else None)
            import publication
            if publication.marker(a.publication).exists():log('Publication status',content=load(publication.marker(a.publication)))
        else:
            import publication
            state=publication.execute(a.mode,a.repo,a.publication,a.work);log('Archive completion publication',phase=state['phase'],pr=state.get('pr'))
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.CalledProcessError) as exc:log('Archive handover stopped',error=str(exc));sys.exit(1)
