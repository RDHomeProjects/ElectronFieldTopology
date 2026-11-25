"""Draft-aware release discovery. Installed in memory; original pack stays sealed."""
import json,subprocess
from pathlib import Path

class MissingRelease(RuntimeError):pass

def install(archive,work):
    need,save,load=archive.need,archive.save,archive.load
    pin=Path(work)/'DRAFT-RELEASE-ID.json'
    api=archive.api
    def resolve(tag):
        if pin.exists():
            identity=load(pin);need(identity['tag']==tag and identity['repository']==archive.REPO,'Pinned release tag/repository changed')
            value=api(f'repos/{archive.REPO}/releases/{identity["release_id"]}')
            need(value['id']==identity['release_id'] and value['tag_name']==tag,'Pinned release identity/tag differs');return value
        candidates=[];page=1
        while True:
            batch=api(f'repos/{archive.REPO}/releases?per_page=100&page={page}')
            need(isinstance(batch,list),'Unexpected release-list response');candidates.extend(x for x in batch if x.get('tag_name')==tag)
            if len(batch)<100:break
            page+=1
        need(len(candidates)<=1,'Multiple releases use the archive tag; no release is selected or modified')
        if not candidates:raise MissingRelease('Existing archive draft not found in authenticated release listing. No replacement release is created; check gh authentication/Contents access on the zbook.')
        value=candidates[0];need(isinstance(value.get('id'),int) and value['id']>0,'Invalid release ID')
        save(pin,{'recorded_at':archive.stamp(),'repository':archive.REPO,'tag':tag,'release_id':value['id'],'draft_at_discovery':bool(value.get('draft'))})
        return value
    def release(tag):
        value=resolve(tag);assets=[];page=1
        while True:
            batch=api(f'repos/{archive.REPO}/releases/{value["id"]}/assets?per_page=100&page={page}');need(isinstance(batch,list),'Unexpected asset-list response');assets+=batch
            if len(batch)<100:break
            page+=1
        names=[x['name'] for x in assets];need(len(names)==len(set(names)),'Duplicate release asset names');value['assets']=assets;return value
    def ensure(plan):
        snap=Path(plan['source_snapshot']);tag=plan['tag'];result=subprocess.run(['git','-C',str(snap),'ls-remote','--tags','origin','refs/tags/'+tag,'refs/tags/'+tag+'^{}'],capture_output=True,text=True);need(result.returncode==0,'Cannot verify the existing remote archive tag')
        lines=[line.split() for line in result.stdout.splitlines()];need(bool(lines),'The already-created remote archive tag is missing; no replacement is created')
        commit=next((x[0] for x in lines if x[1].endswith('^{}')),lines[0][0]);need(commit==plan['main_commit'],'Existing remote tag points to a different source commit')
        value=release(tag);need(value['tag_name']==tag,'Archive release tag differs');return value
    archive.release=release;archive.ensure_release=ensure
    return release
