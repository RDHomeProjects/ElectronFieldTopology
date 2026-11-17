import argparse,os,sys
from pathlib import Path
from common import log
import publication as pub
import runtime
def main():
 p=argparse.ArgumentParser(description='Publish and run bounded adaptive Q17-Q32 screening')
 p.add_argument('mode',choices=['verify','install','publish','merge','preflight','benchmark','run','resume','status','stop'])
 p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-reconciliation-results-20261117')
 p.add_argument('--publication',type=Path,default=Path.home()/'ElectronFieldTopology-adaptive-q-screen-20261117')
 p.add_argument('--backend',choices=['auto','cpu','cuda'],default='auto');p.add_argument('--cpu-threads',type=int,default=4);p.add_argument('--new-run',action='store_true');p.add_argument('--no-restore',action='store_true');a=p.parse_args();a.repo=a.repo.expanduser().resolve();a.publication=a.publication.expanduser().resolve()
 if a.mode=='verify':pub.verify()
 elif a.mode in ('install','publish','merge'):getattr(pub,a.mode)(a)
 elif a.mode in ('preflight','benchmark'):runtime.foreground(a,a.mode)
 elif a.mode in ('run','resume'):runtime.start(a)
 elif a.mode=='stop':runtime.stop(a)
 else:
  m=pub.load(pub.marker(a.publication)) if pub.marker(a.publication).exists() else {'phase':'not_installed'};log('Publication status',phase=m['phase'],pr=m.get('pr'));runtime.status(a)
if __name__=='__main__':
 try:main()
 except Exception as e:log('Adaptive handover stopped',error=str(e));sys.exit(1)
