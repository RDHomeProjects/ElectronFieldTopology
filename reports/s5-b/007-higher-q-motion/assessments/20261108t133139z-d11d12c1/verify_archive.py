"""Check downloaded Release assets and every archived member; optionally restore to a new folder."""
import argparse,importlib.util,io,json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
from verify_assessment import sha,need,stamp,write_json

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',type=Path,required=True);p.add_argument('--restore',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();here=Path(__file__).resolve().parent;receipt=json.loads((here/'archive-verification.json').read_text())
    for f in receipt['assets']:
        path=a.assets/f['name'];need(path.stat().st_size==f['size'] and sha(path)==f['sha256'],'Release asset differs '+f['name'])
    index=json.loads((a.assets/'ARCHIVE.json').read_text());need(len(index['roots'])==1,'Unexpected roots');root=index['roots'][0];need(root['id']=='r001' and root['files']==79,'Unexpected root');need(sha(a.assets/root['manifest']['name'])==root['manifest']['sha256'],'Manifest/index differ')
    manifest=json.loads((a.assets/root['manifest']['name']).read_text());need(manifest==json.loads((here/'release-manifest.json').read_text()),'Pinned manifest differs')
    if a.restore:need(not a.restore.exists(),'Restore requires a new destination');a.restore.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('verified_archive_tool',a.assets/'RESTORE.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    count=m.verify_tar(io.BufferedReader(m.SequenceReader([a.assets/f['name'] for f in root['parts']])),manifest,a.restore)
    result={'recorded_at':stamp(),'tag':index['tag'],'assets_verified':len(receipt['assets']),'payload_files_verified':count,'payload_bytes':sum(f['size'] for f in manifest['files']),'restored_to':str(a.restore.resolve()/'files') if a.restore else None,'method':'Pinned asset digests plus exact tar member size/mode/SHA-256 and manifest coverage, using pinned restore tool.'};write_json(a.output,result);print(json.dumps(result))
if __name__=='__main__':main()
