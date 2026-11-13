"""Audit the six-case scalar study and preserve earlier evidence checks."""
import hashlib,importlib.util,json,math,zipfile
from pathlib import Path

def verify(report,native,cfg):
    def need(x,s):
        if not x:raise ValueError(s)
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location('prior_audit',report/'verify-initial-field.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.verify(report,native,cfg)
    need(sha(report/'initialization-evidence.zip')==cfg['initialization_evidence_sha256'],'Initialization ZIP differs')
    with zipfile.ZipFile(report/'initialization-evidence.zip') as z:
        need(z.testzip() is None,'Study ZIP CRC fails');names=z.namelist();need(len(names)==len(set(names)),'Duplicate member')
        ledger={n:h for h,n in (line.split('  ',1) for line in z.read('SHA256SUMS').decode().splitlines())};need(set(ledger)==set(names)-{'SHA256SUMS'},'Study seal coverage differs')
        for n,h in ledger.items():need(hashlib.sha256(z.read(n)).hexdigest()==h and (report/'initialization'/n).read_bytes()==z.read(n),'Study member differs')
        d=json.loads(z.read('study.json'));need(d['status']=='complete_pending_review' and len(d['cases'])==6,'Study incomplete')
        need({k:v for k,v in d.items() if k!='cases'}|{'completed_cases':6}==json.loads(z.read('status.json')),'Status differs')
        for name,key in [('sf_q3_initialization.py','script_sha256'),('sf_initial_centroid.py','metrics_sha256')]:need(hashlib.sha256(z.read(name)).hexdigest()==d[key],'Study instrument differs')
    with zipfile.ZipFile(native/'evidence.zip') as z:source=json.loads(z.read('campaign.json'))
    need(d['source_evidence_sha256']==cfg['evidence_sha256'] and d['rest_checkpoint_sha256']==source['rest'][d['rest_id']]['checkpoint_sha256'],'Source/rest identity differs')
    with zipfile.ZipFile(report/'initial-field-evidence.zip') as z:old=json.loads(z.read('field-diagnostic.json'))
    for r in d['cases']:
        axis=r['axis'];error=100*math.sqrt(sum((v-(.3 if i==axis else 0))**2 for i,v in enumerate(r['continuum_centroid_rate'])))/.3
        need(math.isclose(error,r['initial_speed_error_percent'],rel_tol=1e-13),'Speed error differs')
        if r['nominal_lab_nodes']==145:
            key='q3-axial-fine-warm-'+['x','y','z'][axis]+'-dt0.01';need(r['historical_state_matches'] and r['state_sha256']==source['cases'][key]['initial_state_sha256'],'Fine state differs')
            previous=next(c for c in old['cases'] if c['case_id']==key)
            for name,value in previous.items():
                if name in r:need(value==r[name],'Fine diagnostic replay differs: '+name)
    return {'initialization_cases':6,'prior_initial_cases':9,'scope':'Compact audit only; no independent production array replay'}
