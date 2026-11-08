"""Authenticate the published archive chain and retained replay receipts; no bulk download."""
import argparse,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ARCHIVE='20261107t233600z-d1c399ad';RUN='20261106t212927z-589f5f5d'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp():
 t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def verify(folder,repo):
 folder,repo=Path(folder),Path(repo);catalog=json.loads((repo/'data/archives'/ARCHIVE/'CATALOG.json').read_text());receipt=json.loads((repo/'data/archives'/ARCHIVE/'VERIFIED.json').read_text());index=json.loads((folder/'release-index.json').read_text());m=json.loads((folder/'release-manifest.json').read_text());download=json.loads((folder/'download-verification.json').read_text());full=json.loads((folder/'full-field-verification.json').read_text())
 assert receipt['catalog_sha256']==sha(repo/'data/archives'/ARCHIVE/'CATALOG.json') and receipt['status']=='all_remote_bytes_verified'
 assert catalog['index_sha256']==sha(folder/'release-index.json')==download['archive_index_sha256']
 assert index['roots'][0]['manifest']['sha256']==sha(folder/'release-manifest.json')==download['manifest_sha256']
 assert catalog['restore_tool_sha256']==sha(repo/'scripts/workstation_archive.py')==download['restore_tool_sha256']
 assert index['roots'][0]['name']==RUN and len(index['roots'])==1
 assert len(m['files'])==catalog['files']==download['payload_files_verified']==full['full_payload_files_verified']==128
 assert sum(f['size'] for f in m['files'])==catalog['payload_bytes']==download['payload_bytes']==6048737963
 assert len([f for f in m['files'] if f['archive_path'].endswith('.npz')])==full['npz_files_verified']==52
 assert download['all_payload_bytes_independently_downloaded_and_hash_verified'] and len(download['tar_segments'])==6
 assert full['run_id']==RUN and len(full['temporal_comparisons_recomputed'])==8
 return {'verified_at':stamp(),'archive_id':ARCHIVE,'payload_files':128,'npz_files':52,'payload_bytes':6048737963,'archive_chain_and_replay_receipts_match':True,'fresh_bulk_download_performed':False,'scope':'Verifies the published catalog and saved independent replay receipts. To independently re-download arrays, restore the Release then run replay_fields.py.'}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--repo',type=Path,required=True);a.add_argument('--folder',type=Path,required=True);a.add_argument('--output',type=Path,required=True);x=a.parse_args();r=verify(x.folder,x.repo);x.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
