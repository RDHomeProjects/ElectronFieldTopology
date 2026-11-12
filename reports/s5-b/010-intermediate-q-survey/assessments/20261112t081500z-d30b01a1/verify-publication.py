"""Verify immutable uploaded observation evidence and replay all scalar results."""
from pathlib import Path
import hashlib,importlib.util,json,zipfile

def verify(report,native,cfg):
    def need(x,s):
        if not x:raise ValueError(s)
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    need(sha(report/'observation-evidence.zip')==cfg['observation_sha256'],'Uploaded observation ZIP differs')
    with zipfile.ZipFile(report/'observation-evidence.zip') as z:
        need(z.testzip() is None,'Observation ZIP CRC fails')
        names=z.namelist();need(len(names)==len(set(names)),'Duplicate members')
        ledger={}
        for line in z.read('SHA256SUMS').decode().splitlines():
            h,n=line.split('  ',1);need(n not in ledger,'Duplicate seal');ledger[n]=h
        need(set(ledger)==set(names)-{'SHA256SUMS'},'Observation seal coverage differs')
        for n,h in ledger.items():
            need(hashlib.sha256(z.read(n)).hexdigest()==h,'Observation member differs')
            need((report/n).read_bytes()==z.read(n),'Expanded observation member differs')
    need(sha(report/'diagnostic.py')=='ec45f242a063cc9acdcf9a7481992e95bdfcd791f03e2c2230ff599042d41f18','Observation instrument differs')
    spec=importlib.util.spec_from_file_location('observation_replay',report/'diagnostic.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    measured=json.loads((report/'observation-diagnostic.json').read_text());measured.pop('recorded_at')
    need(m.analyze(native/'evidence.zip')==measured,'Observation scalar replay differs')
    need(len(measured['fit_rows'])==133 and len(measured['matched_pairs'])==10,'Unexpected coverage')
    status=json.loads((report/'status.json').read_text());need(status['status']=='complete_pending_review','Incomplete observation run')
    return {'fit_rows':133,'matched_pairs':10,'scalar_replay':'exact'}
