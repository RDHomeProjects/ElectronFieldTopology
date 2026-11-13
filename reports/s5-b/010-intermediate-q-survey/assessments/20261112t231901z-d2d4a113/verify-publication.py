"""Check immutable completed boundary evidence and prior compact audit chain."""
import hashlib,importlib.util,json,math,zipfile
from pathlib import Path

def verify(report,native,cfg):
    def need(x,s):
        if not x:raise ValueError(s)
    s=importlib.util.spec_from_file_location('earlier',report/'verify-initialization.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.verify(report,native,cfg)
    need(hashlib.sha256((report/'sampling-boundary-evidence.zip').read_bytes()).hexdigest()==cfg['sampling_evidence_sha256'],'Sampling ZIP differs')
    with zipfile.ZipFile(report/'sampling-boundary-evidence.zip') as z:
        need(z.testzip() is None,'CRC fails');names=z.namelist();need(len(names)==len(set(names)),'Duplicate members')
        ledger={n:h for h,n in (l.split('  ',1) for l in z.read('SHA256SUMS').decode().splitlines())};need(set(ledger)==set(names)-{'SHA256SUMS'},'Seal coverage differs')
        for n,h in ledger.items():need(hashlib.sha256(z.read(n)).hexdigest()==h and (report/'sampling-boundary'/n).read_bytes()==z.read(n),'Expanded member differs')
        d=json.loads(z.read('study.json'));need(d['status']=='complete_pending_review' and len(d['cases'])==12,'Boundary study incomplete')
        need(json.loads(z.read('status.json'))=={k:v for k,v in d.items() if k!='cases'}|{'completed_cases':12},'Status differs')
        need(hashlib.sha256(z.read('sf_q3_sampling_boundary.py')).hexdigest()==d['script_sha256']=='d82081f5757b39903b6430991da0b1a6270d7b33eda753e7e9f34e6285fe9436','Boundary instrument differs')
        for n,h in d['helper_sha256'].items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Helper differs')
    with zipfile.ZipFile(native/'evidence.zip') as z:source=json.loads(z.read('campaign.json'))
    need(d['rest_checkpoint_sha256']==source['rest']['q3-axial-fine-warm']['checkpoint_sha256'],'Rest identity differs')
    for r in d['cases']:
        a=r['axis'];err=100*math.sqrt(sum((x-(.3 if i==a else 0))**2 for i,x in enumerate(r['continuum_centroid_rate'])))/.3;need(abs(err-r['initial_speed_error_percent'])<1e-12,'Error differs')
        if r['id'].endswith('145-native'):
            key='q3-axial-fine-warm-'+['x','y','z'][a]+'-dt0.01';need(r['state_sha256']==source['cases'][key]['initial_state_sha256'],'Fine state differs')
    return {'sampling_cases':12,'initialization_cases':6,'scope':'Compact audit; no independent full-array replay'}
