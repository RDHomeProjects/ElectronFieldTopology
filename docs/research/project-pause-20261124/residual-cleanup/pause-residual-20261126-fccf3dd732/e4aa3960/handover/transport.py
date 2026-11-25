"""Local gh CLI transport with release IDs and exact asset verification."""
import json,os,shutil,subprocess,tempfile,time
from pathlib import Path
from common import need,sha,log,save,load,stamp

class Remote:
    def __init__(self,repository):self.repo=repository
    def api(self,path,method=None,fields=None):
        args=['gh','api',path,'--header','Cache-Control: no-cache','--header','Pragma: no-cache']
        if method:args+=['--method',method]
        if fields is not None:
            args+=['--input','-'];raw=json.dumps(fields).encode()
        else:raw=None
        result=subprocess.run(args,input=raw,capture_output=True);need(result.returncode==0,'GitHub API failed: '+result.stderr.decode(errors='replace')[-2500:]);return json.loads(result.stdout) if result.stdout.strip() else None
    def release(self,release_id):
        value=self.api(f'repos/{self.repo}/releases/{release_id}');assets=[];page=1
        while True:
            batch=self.api(f'repos/{self.repo}/releases/{release_id}/assets?per_page=100&page={page}');assets+=batch
            if len(batch)<100:break
            page+=1
        names=[a['name'] for a in assets];need(len(names)==len(set(names)),'Duplicate release asset names');value['assets']=assets;return value
    def find_release(self,tag):
        values=[];page=1
        while True:
            batch=self.api(f'repos/{self.repo}/releases?per_page=100&page={page}');values += [r for r in batch if r['tag_name']==tag]
            if len(batch)<100:break
            page+=1
        need(len(values)<=1,'Multiple releases share this tag; stop for review');return self.release(values[0]['id']) if values else None
    def download(self,asset,path):
        path=Path(path);need(not path.exists(),'Download destination must be fresh');path.parent.mkdir(parents=True,exist_ok=True)
        log('Downloading asset for verification',name=asset['name'],asset_id=asset['id'])
        with path.open('wb') as target:
            p=subprocess.run(['gh','api',f'repos/{self.repo}/releases/assets/{asset["id"]}','--header','Accept: application/octet-stream','--header','Cache-Control: no-cache'],stdout=target,stderr=subprocess.PIPE);target.flush();os.fsync(target.fileno())
        need(p.returncode==0,'Asset download failed: '+p.stderr.decode(errors='replace')[-2500:]);need(path.stat().st_size==asset['size'],'Downloaded asset size differs');return path
    def upload(self,release_id,tag,path):
        path=Path(path);expected=sha(path);current=self.release(release_id);need(current['tag_name']==tag,'Release ID/tag differs');asset=next((a for a in current['assets'] if a['name']==path.name),None)
        if asset is None:
            p=subprocess.run(['gh','release','upload',tag,str(path),'--repo',self.repo],capture_output=True,text=True)
            collision='already exists' in p.stderr.lower() or 'already_exists' in p.stderr.lower()
            need(p.returncode==0 or collision,'Release upload failed: '+p.stderr[-2500:])
            for attempt in range(5):
                asset=next((a for a in self.release(release_id)['assets'] if a['name']==path.name),None)
                if asset:break
                if attempt<4:time.sleep(min(2**attempt,8))
            need(asset is not None,'Uploaded/colliding asset not visible; preserve files and resume later')
        need(asset.get('state','uploaded')=='uploaded' and asset['size']==path.stat().st_size,'Existing asset is incomplete or has a different size; retained without overwrite')
        need(not asset.get('digest') or asset['digest']=='sha256:'+expected,'Existing asset SHA256 differs; no overwrite is permitted');return asset,expected
    def publish(self,release_id,tag):
        current=self.release(release_id);need(current['tag_name']==tag,'Release tag changed')
        if current['draft']:self.api(f'repos/{self.repo}/releases/{release_id}',method='PATCH',fields={'draft':False,'make_latest':'false'})
        current=self.release(release_id);need(not current['draft'],'Supplement release is still a draft');return current
    def ensure(self,tag,commit,workspace):
        p=subprocess.run(['git','-C',str(workspace),'ls-remote','--tags','origin','refs/tags/'+tag,'refs/tags/'+tag+'^{}'],capture_output=True,text=True);need(p.returncode==0,'Cannot inspect remote supplement tag')
        if p.stdout.strip():
            lines=[l.split() for l in p.stdout.splitlines()];actual=next((l[0] for l in lines if l[1].endswith('^{}')),lines[0][0]);need(actual==commit,'Existing supplement tag has a different commit')
        else:
            local=subprocess.run(['git','-C',str(workspace),'rev-parse','--verify','refs/tags/'+tag],capture_output=True,text=True)
            if local.returncode==0:
                value=subprocess.check_output(['git','-C',str(workspace),'rev-parse',tag+'^{commit}'],text=True).strip();need(value==commit,'Local supplement tag differs')
            else:subprocess.run(['git','-C',str(workspace),'tag','-a',tag,commit,'-m','Matter Waves final folder cleanup supplemental archive'],check=True)
            subprocess.run(['git','-C',str(workspace),'push','origin','refs/tags/'+tag],check=True)
        current=self.find_release(tag)
        if current:return current
        value=self.api(f'repos/{self.repo}/releases',method='POST',fields={'tag_name':tag,'target_commitish':commit,'name':'Matter Waves final folder cleanup — 26 November 2026','body':'Additional records and Git metadata preserved before the final scoped workstation folder cleanup. Download verification and final cleanup receipts are recorded separately.','draft':True,'make_latest':'false'})
        return self.release(value['id'])

def asset_matches(actual,expected):
    need(actual and actual['id']==expected['asset_id'] and actual['size']==expected['bytes'],'Verified release asset missing or replaced: '+expected['name'])
    need(not actual.get('digest') or actual['digest']=='sha256:'+expected['sha256'],'Verified asset digest differs: '+expected['name'])
