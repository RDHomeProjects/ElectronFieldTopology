"""Reviewed local-cache cleanup, default preview. Apache-2.0.

No wildcard deletion. Source data stays in GitHub Releases; the active low-Q cache
and administrative checkout are retained. --apply is an explicit local action.
"""
import argparse
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile

ARCHIVE='20261104t023917z-b0d06afa'
REPO='RDHomeProjects/ElectronFieldTopology'
MERGED='f81ec578dbf3d929b46befea24fae81f8840913d'
INDEX_SHA='bf6339660e5fafd63c72d2ccc16fe4e88b53458ce7f3b8e13110699c369b04ea'
CATALOG_SHA='5d583809e6006fde21c1b6cf840aef851f698fbac5b4dd4c7a4fb83340f614dc'
ENGINE_SHA='0de33dcdd8ee357bd2350c85727911bc9eea2acb830fa2f2e8278aa193201131'
INVENTORY_SHA='ab08f893633962b3d282f3a9f506ecdb1ffc4410f1fb5c1fd59c63628c0ad363'
REVIEW_SHA='cb21cc64559e8d50868da022f2a73b6b5dde70e18c170048408d9200174f0f1a'
KEEPS={'r031','r036'}


def need(condition,message):
    if not condition:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while data:=f.read(8*1024*1024):h.update(data)
    return h.hexdigest()


def stamp():
    n=datetime.now(timezone.utc)
    return {'utc':n.isoformat(),'melbourne':n.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}


def log(message,**fields):print(json.dumps({'recorded_at':stamp(),'message':message,**fields}),flush=True)


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.partial');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)


def within(path,parent):return path==parent or path.is_relative_to(parent)


def git(root,*args):
    return subprocess.check_output(['git','--no-optional-locks','-C',str(root),*args],text=True,
                                   env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')).strip()


def load_engine(path):
    need(sha(path)==ENGINE_SHA,'Archive helper version differs; preserving all sources')
    spec=importlib.util.spec_from_file_location('reviewed_archive_engine',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def deletion_order(candidates,edges):
    """Edges are (dependent worktree, Git-store owner); dependents go first."""
    remaining=set(candidates);result=[]
    while remaining:
        ready=sorted(x for x in remaining if not any(owner==x and dep in remaining for dep,owner in edges))
        need(ready,'Git dependency cycle: preserve these roots for review')
        result+=ready;remaining.difference_update(ready)
    return result


def git_dependencies(roots,keepers):
    candidates=set(roots)-set(keepers);stores={};relations=[]
    def owner(path):
        return next((rid for rid,r in roots.items() if r['kind']=='directory' and within(path,Path(r['source']).resolve())),None)
    for rid,r in roots.items():
        for g in r['git']:
            location=Path(r['source'])/g['path']
            common=Path(git(location,'rev-parse','--path-format=absolute','--git-common-dir')).resolve()
            holder=owner(common);stores[(rid,g['path'])]=(location,common,holder)
            if holder and holder!=rid:relations.append((rid,holder))
    reasons={}
    # Preserve a Git-store owner needed by any keeper or unlisted surviving worktree.
    changed=True
    while changed:
        changed=False
        for (rid,_),(location,common,holder) in stores.items():
            if not holder or holder not in candidates:continue
            required=rid not in candidates
            out=subprocess.check_output(['git','--no-optional-locks','-C',str(location),'worktree','list','--porcelain','-z'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
            for item in out.split(b'\0'):
                if item.startswith(b'worktree '):
                    p=Path(os.fsdecode(item[len(b'worktree '):])).resolve()
                    if p.exists() and owner(p) not in candidates:required=True
            if required:
                candidates.remove(holder);reasons[holder]='Git store is needed by a retained or unlisted worktree';changed=True
    edges=[(d,o) for d,o in relations if d in candidates and o in candidates]
    return deletion_order(candidates,edges),reasons,stores


def mountpoints():
    points=[]
    for row in Path('/proc/self/mountinfo').read_text().splitlines():
        value=row.split()[4]
        value=re.sub(r'\\([0-7]{3})',lambda m:chr(int(m.group(1),8)),value)
        points.append(Path(value).resolve())
    return points


def check_scope(root,home,mounts):
    p=Path(root['source'])
    need(p.is_absolute() and p.parent in {home,home/'Downloads'} and p.name.startswith('ElectronFieldTopology'), 'Path is outside the reviewed project scope: '+str(p))
    need(p.exists() and not p.is_symlink(),'Missing or symlinked source; preserve it: '+str(p))
    need(not within(Path.cwd().resolve(),p.resolve()),'Run from Home rather than inside a folder selected for removal')
    if p.is_dir():need(not any(within(m,p.resolve()) for m in mounts),'A mount exists in this source; preserve it: '+str(p))


def check_source(engine,root,manifest,full_hash):
    engine.assert_unchanged(root)
    expected={f['archive_path'][len('files/'):]:f for f in manifest['files'] if f['archive_path'].startswith('files/')}
    need(set(expected)=={f['path'] for f in root['scan']['files']},'Archive/source file coverage differs: '+root['id'])
    if full_hash:
        for i,(relative,f) in enumerate(expected.items()):
            p=Path(root['source'])/relative if root['kind']=='directory' else Path(root['source'])
            before=engine.signature(p);need(sha(p)==f['sha256'],'Source bytes changed; nothing has been deleted: '+str(p))
            need(engine.signature(p)==before,'Source changed during hash check: '+str(p))
            if i%100==0:log('Checking original local bytes',root=root['id'],files_checked=i+1,total=len(expected))
        engine.assert_unchanged(root)


def backup_private_git(stores,selected,destination):
    """Small credential/config/hook files stay local in the keeper's ignored artifacts."""
    for (rid,relative),(location,common,_) in stores.items():
        if rid not in selected:continue
        gitdir=Path(git(location,'rev-parse','--absolute-git-dir'))
        lfs=common/'lfs/objects'
        need(not lfs.exists() or not any(p.is_file() for p in lfs.rglob('*')), 'Uncatalogued Git LFS cache found; preserve '+str(location))
        target=destination/rid/hashlib.sha256(relative.encode()).hexdigest()[:8]
        target.mkdir(parents=True,mode=0o700);target.chmod(0o700)
        for name,path in [('config',common/'config'),('config.worktree',gitdir/'config.worktree')]:
            if path.is_file():shutil.copy2(path,target/name)
        if (common/'hooks').exists():shutil.copytree(common/'hooks',target/'hooks',symlinks=True)


def apply_sources(engine,ordered,roots,receipt,path):
    for rid in ordered:
        root=roots[rid];p=Path(root['source'])
        # All full hashes passed first; repeat fast source checks immediately before removal.
        engine.assert_unchanged(root)
        need(not p.is_symlink(),'Root changed into a symlink; stopped')
        if p.is_dir():shutil.rmtree(p)
        else:p.unlink()
        receipt['removed'].append({'id':rid,'path':str(p),'removed_at':stamp()});save(path,receipt)
        log('Removed archived local copy',root=rid,path=str(p))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply',action='store_true',help='Permanently remove only validated obsolete local copies after all local hashes pass')
    p.add_argument('--session',type=Path,default=Path.home()/'EFT-archive-work'/ARCHIVE)
    p.add_argument('--repository',type=Path,default=Path.home()/'ElectronFieldTopology-repository-admin')
    a=p.parse_args();home=Path.home().absolute();session=a.session.expanduser().resolve();repo=a.repository.expanduser().resolve()
    need(str(home)=='/home/rd','This plan is scoped to the reviewed /home/rd workstation')
    need(sha(session/'inventory.json')==INVENTORY_SHA,'Original inventory differs from the reviewed upload')
    need(sha(session/'CLEANUP-REVIEW.json')==REVIEW_SHA,'Cleanup review differs from the reviewed upload')
    inv=json.loads((session/'inventory.json').read_text());review=json.loads((session/'CLEANUP-REVIEW.json').read_text())
    roots={r['id']:r for r in inv['roots']};rows={r['id']:r for r in review['roots']}
    need(inv['archive_id']==ARCHIVE and set(roots)==set(rows) and len(roots)==38,'Review coverage differs')
    for rid,r in roots.items():need(rows[rid]['path']==r['source'],'Review/source path mismatch')
    need(Path(roots['r036']['source']).resolve()==repo,'Retained administrative checkout path differs')
    need(roots['r031']['source']==str(home/'ElectronFieldTopology-lowq-motion'),'Active low-Q cache differs')
    engine=load_engine(repo/'scripts/workstation_archive.py')
    ordered,extra_keeps,stores=git_dependencies(roots,KEEPS)
    for rid in ordered:need(rows[rid]['status']=='archived_and_unchanged','A changed source is not eligible: '+rid)
    mounts=mountpoints()
    for rid in ordered:check_scope(roots[rid],home,mounts)
    subprocess.run(['git','-C',str(repo),'fetch','origin','main'],check=True)
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',MERGED,'origin/main'],check=True)
    rel='data/archives/'+ARCHIVE+'/CATALOG.json'
    published=subprocess.check_output(['git','-C',str(repo),'show',MERGED+':'+rel])
    need(hashlib.sha256(published).hexdigest()==CATALOG_SHA,'Merged Git catalog differs')
    need(sha(repo/rel)==CATALOG_SHA and sha(session/'CATALOG.json')==CATALOG_SHA,'Local and published catalogs differ')
    catalog=json.loads(published);verified=json.loads((session/'VERIFIED.json').read_text())
    need(verified['status']=='all_remote_bytes_verified' and verified['catalog_sha256']==CATALOG_SHA and verified['index_sha256']==INDEX_SHA,'Successful verification receipt is missing or differs')
    with tempfile.TemporaryDirectory(prefix='eft-cleanup-metadata-') as temporary:
        temporary=Path(temporary);gh,index=engine.remote_index(catalog,temporary)
        meta=json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/releases/tags/'+catalog['tag']],text=True))
        expected={'ARCHIVE.json':INDEX_SHA,'RESTORE.py':ENGINE_SHA}
        for r in index['roots']:
            for item in [r['manifest'],*r['parts']]:expected[item['name']]=item['sha256']
        assets={x['name']:x for x in meta['assets']}
        need(not meta['draft'] and set(assets)==set(expected),'Published release asset coverage changed')
        for name,h in expected.items():need(assets[name]['state']=='uploaded' and assets[name].get('digest')=='sha256:'+h,'Release asset digest changed: '+name)
        need(verified['root_file_counts']=={r['id']:r['files'] for r in index['roots']},'Verification coverage differs from the index')
        index_roots={r['id']:r for r in index['roots']}
        for rid in ordered:
            log('Validating cleanup candidate',root=rid,path=roots[rid]['source'],full_hash=a.apply)
            m=index_roots[rid]['manifest'];cached=session/'staging'/rid/m['name']
            if cached.is_file() and sha(cached)==m['sha256']:manifest=json.loads(cached.read_text())
            else:
                f=gh.download(m['name'],temporary,m['sha256']);manifest=json.loads(f.read_text())
            check_source(engine,roots[rid],manifest,a.apply)
    plan={'recorded_at':stamp(),'archive_id':ARCHIVE,'review_sha256':REVIEW_SHA,'index_sha256':INDEX_SHA,
          'keep':[roots[rid]['source'] for rid in sorted(KEEPS|set(extra_keeps))],
          'additional_keep_reasons':extra_keeps,'remove_in_order':[{'id':rid,'path':roots[rid]['source'],'retained_bytes':roots[rid]['logical_bytes']} for rid in ordered],
          'recorded_file_bytes':sum(roots[rid]['logical_bytes'] for rid in ordered),'source_deletion_performed':False}
    event_id=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz').lower()+'-'+secrets.token_hex(4)
    out=session/'local-cleanup'/event_id;out.mkdir(parents=True)
    save(out/'PLAN.json',plan)
    print(json.dumps(plan,indent=2))
    if not a.apply:
        log('Preview complete; nothing removed. Use --apply for permanent local removal after full file hashing.',plan=str(out/'PLAN.json'));return
    # This folder is ignored by Git; private local settings are never published.
    private=repo/'artifacts/private-git-settings'/event_id
    subprocess.run(['git','-C',str(repo),'check-ignore','--quiet',str(private/'config')],check=True)
    private.mkdir(parents=True,mode=0o700);private.chmod(0o700)
    backup_private_git(stores,set(ordered),private)
    receipt={'recorded_at':stamp(),'archive_id':ARCHIVE,'plan':plan,'private_git_settings':str(private),'removed':[],'status':'in_progress'}
    receipt_path=out/'RECEIPT.json';save(receipt_path,receipt)
    apply_sources(engine,ordered,roots,receipt,receipt_path)
    receipt['status']='complete';receipt['completed_at']=stamp();save(receipt_path,receipt)
    # Append an auditable, small receipt and the exact cleanup program to the kept repo.
    public=repo/'data/archives'/ARCHIVE/'cleanup'/event_id;public.mkdir(parents=True)
    for name in ['PLAN.json','RECEIPT.json']:shutil.copy2(out/name,public/name)
    shutil.copy2(Path(__file__),public/'CLEANUP.py')
    (public/'README.md').write_text('# Verified local-cache cleanup\n\n'+json.dumps(receipt['completed_at'])+'\n\nArchived obsolete local copies were removed after source hashes, Git state, release digests and merged catalog checks. The administrative checkout, active low-Q cache and any shared Git owner required by retained worktrees remain. Small private Git settings/hooks backups stay under ignored artifacts; they are not uploaded.\n')
    (public/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(public.iterdir()) if f.is_file() and f.name!='SHA256SUMS'))
    log('Cleanup complete; retained source data and cloud archive unchanged',removed=len(ordered),receipt=str(receipt_path),git_receipt=str(public))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError,KeyError) as e:
        log('Cleanup stopped; inspect any receipt for completed removals',error=str(e));sys.exit(1)
