"""Local-only publication and execution facade."""
import argparse,subprocess,json,sys,uuid,os
from pathlib import Path
import publication as pub
import collector
ROOT=Path(__file__).resolve().parent
def latest_path(a):return a.publication/'.git/higher-q-last-collection.json'
def source_repo(a):return a.publication if (a.publication/'.git').exists() else a.repo
def collect(a):
 pub.verify();repo=source_repo(a);head=collector.git(repo,'rev-parse','HEAD').decode().strip();pointer=latest_path(a)
 if pointer.exists() and not a.new_collection:
  d=pub.load(pointer);out=Path(d['output'])
  pub.need(d['source_commit']==head and d['package_sha256']==pub.sha(ROOT/'SHA256SUMS') and d['field_roots']=={'Q2':str(a.q2_run),'Q8':str(a.q8_run)},'Collection identity changed; preserve old output and use --new-collection')
  collector.verify(out);pub.event('Existing matching collection retained',output=str(out));return out
 rid=pub.datetime.now(pub.timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+uuid.uuid4().hex[:8];out=repo/'artifacts/higher-q-reconciliation'/rid
 record=collector.collect(repo,out,a.q2_run,a.q8_run)
 pointer.parent.mkdir(parents=True,exist_ok=True);pub.save(pointer,{'output':str(out),'source_commit':head,'package_sha256':pub.sha(ROOT/'SHA256SUMS'),'field_roots':{'Q2':str(a.q2_run),'Q8':str(a.q8_run)},'recorded_at':pub.stamp()})
 pub.event('Local reconciliation collected',output=str(out),evidence=str(out/'evidence.zip'),report=str(out/'REPORT.html'),copied=record['copied_members'],deferred=len(record['deferred_members']));return out
def diagnose(a):
 pub.verify();pub.need(latest_path(a).is_file(),'Run collect first');prior=pub.load(latest_path(a));out=Path(prior['output']);collector.verify(out)
 pub.need(prior['source_commit']==collector.git(source_repo(a),'rev-parse','HEAD').decode().strip() and prior['package_sha256']==pub.sha(ROOT/'SHA256SUMS') and prior['field_roots']=={'Q2':str(a.q2_run),'Q8':str(a.q8_run)},'Collection/source identity changed; preserve and recollect')
 if (out/'DIAGNOSTIC-STATUS.json').exists():pub.event('Previous diagnostic receipt retained; use collect --new-collection for another attempt',output=str(out));return
 repo=source_repo(a);argv=['uv','run','--frozen','--python','3.12.14','python',str(ROOT/'diagnostics.py'),'--repo',str(repo),'--output',str(out),'--q2-run',str(a.q2_run),'--q8-run',str(a.q8_run)]
 env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1');pub.event('Starting read-only CPU motion-balance probes',argv=argv)
 r=subprocess.run(argv,cwd=repo,env=env)
 pub.save(out/'DIAGNOSTIC-STATUS.json',{'recorded_at':pub.stamp(),'exit_code':r.returncode,'status':'completed_pending_review' if r.returncode==0 else 'explicitly_blocked_diagnostic','relaxation_steps':0,'physical_time_steps':0,'scope':'CPU evaluation of already retained fields; no new trajectory. Nonzero exit is retained, not hidden.'})
 collector.report(out);collector.seal(out);pub.event('Diagnostic stage recorded',exit_code=r.returncode,evidence=str(out/'evidence.zip'),report=str(out/'REPORT.html'))
def main():
 p=argparse.ArgumentParser(description='Local Q22/Q18 reconciliation; no relaxation or physical-time trajectory')
 p.add_argument('mode',choices=['verify','install','publish','merge','collect','diagnose','run','status']);p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-repository-admin');p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-higher-q-reconciliation-20261117');p.add_argument('--q2-run',type=Path,default=Path.home()/'ElectronFieldTopology-repository-admin/artifacts/s5-b/010-intermediate-q-survey/20261109t134425z-89d28344');p.add_argument('--q8-run',type=Path,default=Path.home()/'ElectronFieldTopology-campaign2/artifacts/targeted-q-campaign2/20261115t141810z-c391d86a');p.add_argument('--new-collection',action='store_true');a=p.parse_args()
 for k in ['repo','publication','q2_run','q8_run']:setattr(a,k,getattr(a,k).expanduser().resolve())
 if a.mode=='verify':pub.verify()
 elif a.mode in ['install','publish','merge']:getattr(pub,a.mode)(a)
 elif a.mode=='collect':collect(a)
 elif a.mode=='diagnose':diagnose(a)
 elif a.mode=='run':collect(a);diagnose(a)
 else:
  m=pub.load(pub.marker(a.publication)) if pub.marker(a.publication).exists() else {'phase':'not_installed'};d=pub.load(latest_path(a)) if latest_path(a).exists() else None
  detail=pub.load(Path(d['output'])/'DIAGNOSTIC-STATUS.json') if d and (Path(d['output'])/'DIAGNOSTIC-STATUS.json').exists() else None
  pub.event('Reconciliation handover status',publication_phase=m.get('phase'),pr=m.get('pr'),collection=d,diagnostic=detail,relaxation_steps=0,physical_time_steps=0)
if __name__=='__main__':
 try:main()
 except Exception as e:pub.event('Reconciliation handover stopped',error=str(e));sys.exit(1)
