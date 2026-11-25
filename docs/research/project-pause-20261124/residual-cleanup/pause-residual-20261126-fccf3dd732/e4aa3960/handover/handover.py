#!/usr/bin/env python3
"""Remaining project folders: scan, preserve, verify, remove and record."""
import argparse,fcntl,hashlib,json,os,shlex,shutil,sys,zipfile
from pathlib import Path
from common import ROOT,need,sha,load,save,stamp,log,verify_manifest

def setup(work):
    verify_manifest(ROOT);work.mkdir(parents=True,exist_ok=True)
    from capsule import no_symlinks
    no_symlinks(work);target=work/('tools-'+sha(ROOT/'SHA256SUMS')[:12])
    if not target.exists():
        target.mkdir()
        for p in ROOT.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                dest=target/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    verify_manifest(target)
    script='#!/usr/bin/env bash\nset -euo pipefail\nexport PYTHONDONTWRITEBYTECODE=1\nexec /usr/bin/python3 '+shlex.quote(str(target/'handover.py'))+' "$@" --work '+shlex.quote(str(work))+'\n';launcher=work/'RUN.sh'
    if launcher.exists():need(launcher.read_text()==script,'This work directory has another toolset; keep it and choose a fresh --work directory')
    else:launcher.write_text(script);launcher.chmod(0o700)
    log('Retained final-cleanup launcher ready',launcher=str(launcher),source_package_can_be_removed_after_verified_archive=True);return target

def collect(work):
    names=['STATUS.json','REPORT.md','IDENTITY.json','CLEANUP-RECEIPT.json','VERIFIED-SUPPLEMENT.json','PROOF-ASSET.json','RESIDUAL-MANIFEST.json.gz','LAST-REMOTE-CHECK.json','base/BASE-CHECK.json'];payload={n:(work/n).read_bytes() for n in names if (work/n).exists()}
    if (work/'DELETIONS.jsonl').exists():
        import gzip
        payload['DELETIONS.jsonl.gz']=gzip.compress((work/'DELETIONS.jsonl').read_bytes(),mtime=0)
    payload['SHA256SUMS']=''.join(hashlib.sha256(v).hexdigest()+'  '+n+'\n' for n,v in sorted(payload.items())).encode();out=work/'completion-evidence.zip'
    with zipfile.ZipFile(out.with_suffix('.tmp'),'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in payload.items():z.writestr(n,v)
    out.with_suffix('.tmp').replace(out);log('Final folder cleanup evidence ready',output=str(out),sha256=sha(out));return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['setup','verify','scan','archive','verify-remote','cleanup','install','publish','merge','collect','status']);p.add_argument('--work',type=Path,default=Path.home()/'MatterWaves-FinalCleanup');a=p.parse_args();count=verify_manifest(ROOT)
    if a.mode=='verify':log('Final folder cleanup package verified',payload_files=count,scientific_steps=0);return
    from engine import SETTINGS,scan,archive,cleanup,verify_remote,read_plan
    from transport import Remote
    need(os.geteuid()!=0 and Path.home()==Path(SETTINGS['home']),'Run as the inventoried rd account, without sudo');home=Path.home();work=a.work.absolute();need(home in work.parents and work!=home/'Downloads' and not (home/'Downloads' in work.parents),'Keep final controls in a dedicated home directory outside Downloads');workspace=home/'MatterWaves-Workspace'
    if a.mode=='setup':setup(work);return
    need(work in ROOT.parents,'Run setup first, then use the retained control-directory RUN.sh so the Downloads package can be removed')
    if a.mode=='status':
        status=load(work/'STATUS.json') if (work/'STATUS.json').exists() else {'status':'not_scanned'};transfer=load(work/'TRANSFER.json') if (work/'TRANSFER.json').exists() else {'parts':{}};log('Final folder cleanup status',work=str(work),status=status,parts_download_verified=len(transfer['parts']));return
    with (work/'SESSION.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another final-cleanup command is running')
        remote=Remote(SETTINGS['repository'])
        if a.mode=='scan':scan(home,work,workspace,remote)
        elif a.mode=='archive':archive(work,remote)
        elif a.mode=='verify-remote':log('Base and supplemental archive identities verified',release_url=verify_remote(work,remote)['html_url'])
        elif a.mode=='cleanup':cleanup(work,remote)
        elif a.mode=='collect':collect(work)
        elif a.mode=='status':log('Final folder cleanup status',work=str(work),status=load(work/'STATUS.json') if (work/'STATUS.json').exists() else {'status':'not_scanned'})
        else:
            import publication
            state=publication.execute(a.mode,workspace,work/'publication',work)
            if a.mode=='merge' and state['phase']=='merged':
                from engine import command
                command(['git','-C',str(workspace),'fetch','origin','refs/heads/main:refs/remotes/origin/main'])
                if command(['git','-C',str(workspace),'branch','--show-current'])=='main' and not command(['git','-C',str(workspace),'status','--porcelain']):command(['git','-C',str(workspace),'merge','--ff-only','origin/main'])
            log('Final cleanup publication status',phase=state['phase'],pr=state.get('pr'))
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,__import__('subprocess').CalledProcessError) as exc:log('Final folder cleanup stopped',error=str(exc));sys.exit(1)
