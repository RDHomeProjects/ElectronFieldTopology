"""Compare and safely reuse a release asset after a duplicate-name response."""
import json,os,subprocess,tempfile,time
from pathlib import Path

def install(archive,work):
    def api(path):
        return json.loads(archive.checked(['gh','api',path,'--header','Cache-Control: no-cache','--header','Pragma: no-cache']))
    archive.api=api
    def find(plan,name):
        current=archive.release(plan['tag']);matches=[x for x in current['assets'] if x['name']==name]
        archive.need(len(matches)<=1,'Duplicate exact asset names; stop for review')
        if not matches:
            similar=[x['name'] for x in current['assets'] if x['name'].casefold()==name.casefold()]
            archive.need(not similar,'A differently cased asset name conflicts; it is retained: '+repr(similar))
        return matches[0] if matches else None
    def binary(asset,path):
        command=['gh','api',f'repos/{archive.REPO}/releases/assets/{asset["id"]}','--header','Accept: application/octet-stream','--header','Cache-Control: no-cache']
        archive.log('Downloading exact asset ID for comparison',asset_id=asset['id'],name=asset['name'])
        with path.open('wb') as stream:
            result=subprocess.run(command,stdout=stream,stderr=subprocess.PIPE)
            stream.flush();os.fsync(stream.fileno())
        archive.need(result.returncode==0,'Asset-ID download failed: '+result.stderr.decode(errors='replace')[-3000:])
    def verify(plan,path,asset,reason):
        expected=archive.sha(path);size=path.stat().st_size
        archive.need(asset.get('state','uploaded')=='uploaded','Existing asset is incomplete; retained without replacement: '+str(asset['id']))
        archive.need(asset['size']==size,'Existing asset size differs; no overwrite/deletion: '+path.name+' (remote '+str(asset['size'])+', local '+str(size)+')')
        server=asset.get('digest');archive.need(not server or server=='sha256:'+expected,'Existing asset SHA256 differs; no overwrite/deletion: '+path.name)
        with tempfile.TemporaryDirectory(prefix='asset-compare-',dir=work) as tmp:
            downloaded=Path(tmp)/path.name;binary(asset,downloaded);actual=archive.sha(downloaded)
            archive.need(downloaded.stat().st_size==size and actual==expected,'Existing asset bytes differ; retained without replacement: '+path.name+'; local SHA256 '+expected+'; downloaded SHA256 '+actual)
        # Confirm the comparison downloaded the still-selected asset identity.
        again=find(plan,path.name);archive.need(again and again['id']==asset['id'] and again['size']==size,'Asset changed during comparison; cleanup is blocked')
        archive.need(not again.get('digest') or again['digest']=='sha256:'+expected,'Asset digest changed during comparison')
        row={'recorded_at':archive.stamp(),'name':path.name,'asset_id':asset['id'],'sha256':expected,'bytes':size,'download_comparison_passed':True,'reason':reason,'remote_assets_deleted':0,'remote_assets_overwritten':0}
        with (work/'ASSET-COMPARISONS.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n');stream.flush();os.fsync(stream.fileno())
        archive.log('Existing or newly uploaded asset bytes verified',name=path.name,asset_id=asset['id'],reason=reason)
        return again,expected
    def checked_upload(plan,path):
        path=Path(path);asset=find(plan,path.name);reason='existing asset reused'
        if asset is None:
            error=None
            try:archive.checked(['gh','release','upload',plan['tag'],str(path),'--repo',archive.REPO])
            except RuntimeError as exc:
                error=exc
                # Auth/access and validation failures stop. Only a name collision
                # can be reconciled by finding and downloading that exact asset.
                text=str(exc).lower()
                if not ('already exists' in text or 'already_exists' in text):raise
            for attempt in range(5):
                asset=find(plan,path.name)
                if asset:break
                if attempt<4:time.sleep(min(2**attempt,8))
            if asset is None:
                if error:raise RuntimeError('GitHub reports a name collision but fresh listings do not expose the asset. No overwrite/delete attempted. '+str(error))
                raise RuntimeError('Upload returned success but the asset is not visible; safely rerun the same repair later')
            reason='duplicate-name response reconciled' if error else 'new upload confirmed'
        return verify(plan,path,asset,reason)
    def audit(plan):
        path=Path(work)/'MATTER-WAVES-ARCHIVE.json.gz';asset=find(plan,path.name)
        diagnostic={'recorded_at':archive.stamp(),'tag':plan['tag'],'local_manifest_present':path.is_file(),'local_manifest_sha256':archive.sha(path) if path.is_file() else None,'local_manifest_bytes':path.stat().st_size if path.is_file() else None,'listed_manifest_asset':asset,'remote_assets_modified':0}
        archive.save(Path(work)/'ASSET-COLLISION-DIAGNOSTIC.json',diagnostic)
        if asset is None:archive.log('Manifest not currently listed; upload mode will reconcile any duplicate response',name=path.name);return
        archive.need(path.is_file(),'Local manifest missing; preserve remote asset and rerun upload to regenerate it from the frozen plan')
        verify(plan,path,asset,'read-only manifest preflight')
    archive.checked_upload=checked_upload
    return audit
