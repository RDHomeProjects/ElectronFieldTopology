"""Verify observation replay and source-linked initial-field diagnostic receipts."""
import hashlib,importlib.util,json,math,zipfile
from pathlib import Path

def verify(report,native,cfg):
    def need(x,s):
        if not x:raise ValueError(s)
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location('obs',report/'verify-observation.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.verify(report,native,cfg)
    need(sha(report/'initial-field-evidence.zip')==cfg['field_evidence_sha256'],'Uploaded field diagnostic differs')
    with zipfile.ZipFile(report/'initial-field-evidence.zip') as z:
        need(z.testzip() is None,'Field ZIP CRC fails');names=z.namelist();need(len(names)==len(set(names)),'Duplicate field member')
        hashes={n:h for h,n in (line.split('  ',1) for line in z.read('SHA256SUMS').decode().splitlines())};need(set(hashes)==set(names)-{'SHA256SUMS'},'Field seal coverage differs')
        for n,h in hashes.items():need(hashlib.sha256(z.read(n)).hexdigest()==h and (report/'initial-field'/n).read_bytes()==z.read(n),'Field member differs')
        d=json.loads(z.read('field-diagnostic.json'));status=json.loads(z.read('status.json'));need({k:v for k,v in d.items() if k!='cases'}==status,'Field status differs')
        need(hashlib.sha256(z.read('field_diagnostic.py')).hexdigest()==d['script_sha256']=='5c404133768fca455b2a21947fea76414800e73384d957cd83572c87b84566ba','Field instrument differs')
    need(d['status']=='complete_pending_review' and len(d['cases'])==9,'Field run incomplete');need([r['case_id'] for r in d['cases']]==d['selected_cases'],'Field case coverage differs')
    with zipfile.ZipFile(native/'evidence.zip') as z:
        source=json.loads(z.read('campaign.json'));need(d['source_run']==source['record_id']==cfg['run_id'],'Source identity differs')
        need(d['dependency_sha256']==source['dependency_sha256'],'Measured locks differ')
        for n,h in d['kernel_sha256'].items():need(source['source_sha256'][n]==h,'Kernel identity differs')
        def close(x,y):
            if isinstance(x,list):return isinstance(y,list) and len(x)==len(y) and all(close(a,b) for a,b in zip(x,y))
            return math.isfinite(x) and math.isfinite(y) and math.isclose(x,y,rel_tol=2e-11,abs_tol=2e-12)
        for r in d['cases']:
            s=source['cases'][r['case_id']];i=json.loads(z.read('cases/'+r['case_id']+'/history-combined.json'))[0]
            need(r['checkpoint_sha256']==s['initial_checkpoint_sha256'] and r['original_status']==s['status'],'Case seals/status differ')
            need(r['historical_fit_velocity']==s['assessment']['legacy_motion']['fitted_centroid_velocity'],'Historical fit differs')
            for a,b in [('continuum_energy','continuum_energy'),('hamiltonian','energy'),('momentum','momentum'),('continuum_centroid','centroid')]:need(close(r[a],i[b]),'Initial scalar differs')
            for j in range(3):need(abs(r['continuum_centroid_rate'][j]-r['momentum_over_continuum_energy'][j]-r['weighted_continuity_residual_over_energy'][j]-r['discrete_summation_term'][j])<1e-10,'Moment decomposition differs')
            need(min(q['continuum_absolute_rms'] for q in r['directional_probes'])<1e-8 and min(q['hamiltonian_absolute_rms'] for q in r['directional_probes'])<1e-8,'Density probes fail')
    return {'initial_cases':9,'observation_fits':133,'matched_pairs':10,'scope':'Compact evidence cross-check; no independent full-field replay'}
