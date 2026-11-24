"""Inventory and additive pause-document publication, all on the zbook."""
import argparse,json,shutil,sys,zipfile
from pathlib import Path
from common import ROOT,load,save,sha,stamp,need,log,verify_package,verify_zip

def latest(destination):
    marker=destination/'LATEST.json';need(marker.exists(),'No inventory exists; run inventory first');out=Path(load(marker)['output']);need(out.is_dir(),'Recorded inventory directory is missing');return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','inventory','status','collect','install','publish','merge']);p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-adaptive-q-screen-20261117');p.add_argument('--root',type=Path,action='append',default=[]);p.add_argument('--destination',type=Path,default=Path.home()/'MatterWaves-PauseInventory');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-pause-publication-20261124');p.add_argument('--resume',action='store_true');a=p.parse_args();repo=a.repo.expanduser().resolve();destination=a.destination.expanduser().resolve();publication=a.publication.expanduser().resolve()
    if a.mode=='verify':log('Pause inventory package verified',**verify_package(),scientific_steps=0)
    elif a.mode=='inventory':
        from inventory import run
        need(repo.is_dir(),'Numerical checkout missing; supply --repo with its current location')
        resume=latest(destination) if a.resume else None
        if resume:a.root=list(dict.fromkeys([Path(p) for p in load(resume/'ROOTS.json')['additional_roots']]+a.root))
        run(Path.home(),repo,[p.expanduser().resolve() for p in a.root],destination,publication,resume)
    elif a.mode=='status':
        if (destination/'LATEST.json').exists():
            out=latest(destination);log('Pause inventory status',output=str(out),status=load(out/'status.json'),restart_document=str(out/'PAUSE-AND-RESUME.md'),evidence=str(out/'inventory-evidence.zip'))
        else:log('No pause inventory created')
        marker=publication/'.git/pause-publication.json'
        if marker.exists():log('Pause documentation publication',**{k:load(marker).get(k) for k in ['phase','pr']})
    elif a.mode=='collect':
        out=latest(destination);need(load(out/'status.json')['status'] in ['inventory_complete_review_required','inventory_incomplete_errors_require_review'],'Finish inventory before collecting metadata');hashes=verify_zip(out/'inventory-evidence.zip')
        for name in ['identity.json','status.json','SUMMARY.json','PAUSE-AND-RESUME.md']:need(sha(out/name)==hashes[name],'Local inventory differs from sealed metadata: '+name)
        digest=sha(out/'inventory-evidence.zip');dest=Path.home()/'Downloads'/('ElectronFieldTopology-pause-inventory-'+load(out/'identity.json')['inventory_id']+'-'+digest[:8]+'-evidence.zip');need(not dest.exists() or sha(dest)==digest,'Existing collection name has different content; retain it and collect the new inventory separately');shutil.copy2(out/'inventory-evidence.zip',dest);log('Inventory metadata collected',file=str(dest),sha256=sha(dest),scientific_field_arrays_included=False)
    else:
        from publication import execute
        out=latest(destination);need(load(out/'status.json')['status'] in ['inventory_complete_review_required','inventory_incomplete_errors_require_review'],'Finish or resume inventory before staging documentation');state=execute(a.mode,repo,publication,out);log('Pause documentation publication',**{k:state.get(k) for k in ['phase','pr']},full_scientific_data_uploaded=False)
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:log('Pause inventory interrupted; resume the same inventory to reuse unchanged hashes');raise SystemExit(130)
    except Exception as exc:log('Pause inventory handover stopped',error=str(exc));raise SystemExit(1)
