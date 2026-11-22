"""Record all completed Q21 conditioning evidence and the subsequent scientific review."""
import argparse
from pathlib import Path
from common import ROOT,load,log,need,stamp
from verification import local,package
import publication

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','install','record-results','publish','merge','status']);p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-adaptive-q-screen-20261117');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-Q21-conditioning-results-record-20261123');p.add_argument('--run',type=Path,help='Exact retained run location; its pinned identity must still match');p.add_argument('--package-only',action='store_true',help='Verify download only; allowed solely with verify');a=p.parse_args();repo=a.repo.expanduser().resolve();pub=a.publication.expanduser().resolve();run=a.run.expanduser().resolve() if a.run else None
    need(not a.package_only or a.mode=='verify','--package-only is allowed only with verify')
    if a.mode=='verify':
        if a.package_only:log('Downloaded record package and completed scientific records verified',**package()[3])
        else:
            r=local(repo,run,reuse=False);log('All completed results and retained fields verified',fields=len(r['fields']),field_bytes=r['retained_field_bytes'],evidence_sha256=r['evidence_sha256'],new_optimizer_attempts=0,physical_time_steps=0)
    elif a.mode=='status':
        package()
        if not (pub/'.git').exists() or not publication.marker(pub).exists():log('No publication prepared by this record handover',new_optimizer_attempts=0);return
        s=load(publication.marker(pub));remote_error=None
        if s['phase'] in ['published','merged']:
            try:
                pr=publication.view(pub,s['pr']['url'])
                if pr['state']=='MERGED':s=publication.finalize_merge(pub,s,pr)
            except Exception as e:remote_error=str(e)
        spec=load(ROOT/'SOURCE.json');raw_path,review_path,_=publication.paths(spec)
        log('Completed results and scientific review publication status',phase=s['phase'],pr=s.get('pr'),merged_verification=s.get('merged_verification'),remote_check_error=remote_error,local_assessment_browser=str(pub/s.get('review_path',review_path)/'ASSESSMENT.html'),local_results_browser=str(pub/s.get('raw_path',raw_path)/'REPORT.html'),verified_retained_fields=len(s['local_verification']['fields']),new_optimizer_attempts=0,physical_time_steps=0)
    else:publication.execute(a.mode,repo,pub,run)

if __name__=='__main__':
    try:main()
    except Exception as e:log('Results-record handover stopped',error=str(e));raise SystemExit(1)
