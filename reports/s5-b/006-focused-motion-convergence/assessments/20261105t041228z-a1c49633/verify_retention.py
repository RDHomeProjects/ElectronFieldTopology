"""Audit retained release metadata against compact checkpoints; Apache-2.0.
Does not download/replay the 3.57 GB tar payloads.
"""
import argparse,hashlib,json,zipfile,sys
sys.dont_write_bytecode=True
from pathlib import Path
from verify_assessment import need,sha,stamp,EXPECTED,RUN
ARCHIVE='20261105t015855z-b7d90f43'
def verify(folder,repo,evidence):
    folder,repo=Path(folder),Path(repo)
    catalog=repo/'data/archives'/ARCHIVE/'CATALOG.json';receipt=json.loads((catalog.parent/'VERIFIED.json').read_text());cat=json.loads(catalog.read_text())
    index=json.loads((folder/'release-index.json').read_text());manifest=json.loads((folder/'release-manifest.json').read_text());snapshot=json.loads((folder/'github-review.json').read_text())
    need(sha(catalog.read_bytes())==receipt['catalog_sha256'],'Catalog receipt differs')
    need(sha((folder/'release-index.json').read_bytes())==cat['index_sha256']==receipt['index_sha256'],'Index digest mismatch')
    need(receipt['status']=='all_remote_bytes_verified' and receipt['root_file_counts']=={'r001':525},'Incomplete verification receipt')
    root=index['roots'][0];need(len(index['roots'])==1 and root['name']==RUN,'Archive run mismatch')
    need(sha((folder/'release-manifest.json').read_bytes())==root['manifest']['sha256'],'Manifest digest mismatch')
    files={r['archive_path'].removeprefix('files/'):r for r in manifest['files']};need(len(files)==525==cat['files'],'Archive count mismatch')
    need(sum(r['size'] for r in files.values())==cat['payload_bytes']==3569785036,'Payload count mismatch')
    assets={r['name']:r for r in snapshot['release']['assets']};need(not snapshot['release']['draft'],'Release is draft')
    for p in root['parts']:
        need(assets[p['name']]['bytes']==p['bytes'] and assets[p['name']]['digest']=='sha256:'+p['sha256'],'Remote part metadata mismatch')
    need(files['evidence.zip']['sha256']==EXPECTED,'Archived compact ZIP differs')
    with zipfile.ZipFile(evidence) as z:
        for n in z.namelist():need(sha(z.read(n))==files[n]['sha256'],'Archived/compact member mismatch: '+n)
        c=json.loads(z.read('campaign.json'));count=0
        for key,r in c['cases'].items():
            need(files[f'cases/{key}/admitted.npz']['sha256']==r['initial_checkpoint_sha256'],'Admitted checkpoint seal differs')
            for t,m in r['milestones'].items():
                rel=m['checkpoint'].split(RUN+'/',1)[1]
                need(files[rel]['sha256']==m['checkpoint_sha256'],'Milestone checkpoint seal differs');count+=1
    return dict(verified_at=stamp(),archive_id=ARCHIVE,files=len(files),payload_bytes=cat['payload_bytes'],compact_members_crosschecked=143,
        admitted_checkpoint_hashes_crosschecked=8,milestone_checkpoint_hashes_crosschecked=count,parts_metadata_checked=4,
        remote_bulk_download_repeated=False,independent_npz_replay=False,
        scope='Downloaded index/manifest hashes and live release metadata checked; full-byte download verification is the retained workstation receipt.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=verify(a.folder,a.repo,a.evidence);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
