"""Verify compact evidence and replay receipts; no solver or network. Apache-2.0."""
from pathlib import Path
from collections import Counter
import argparse,gzip,hashlib,importlib.util,json,math

if not __debug__:raise RuntimeError('Run verification without Python optimization.')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def verify(report,native,cfg):
    covered=set()
    for line in (report/'SHA256SUMS').read_text().splitlines():
        h,n=line.split('  ',1);p=report/n
        assert n not in covered and not Path(n).is_absolute() and '..' not in Path(n).parts
        assert not p.is_symlink() and p.is_file() and sha(p)==h,n
        covered.add(n)
    actual={p.relative_to(report).as_posix() for p in report.rglob('*') if p.is_file() and p.name!='SHA256SUMS' and '__pycache__' not in p.parts}
    assert actual==covered
    assert hashlib.sha256(gzip.decompress((report/'workstation-publication-log.txt.gz').read_bytes())).hexdigest()==cfg['publication_log_sha256']
    assert sha(native/'evidence.zip')==cfg['evidence_sha256']
    spec=importlib.util.spec_from_file_location('eft_compact_assessment',report/'verify_compact.py');tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    compact=tool.audit(native/'evidence.zip',report/'workstation-integrity.json',native/'SUMMARY.md')
    previous=load(report/'compact-assessment-metrics.json')
    # Timestamps identify this repeat audit; all measured/derived values must agree.
    compact.pop('recorded_at');previous.pop('recorded_at');assert compact==previous
    r=load(report/'field-replay.json');d=load(native/'campaign.json')
    assert sha(report/'field-replay.json')==cfg['replay_sha256']
    assert r['run']==d['record_id']==cfg['run_id'] and r['case_selection'] is None
    assert r['audit']['source_commit']==d['source_commit']==cfg['source_commit']
    assert r['audit']['config_sha256']==d['config_sha256']
    assert r['audit']['evidence_sha256']==cfg['evidence_sha256']
    assert r['numeric_comparisons']=={'numeric':1588,'max_absolute_difference':0.0}
    count=0;maximum=0.
    def compare(got,want):
        nonlocal count,maximum
        if isinstance(want,dict):
            for k,v in want.items():
                if k not in {'recorded_at','scope','topology_scope'}:compare(got[k],v)
        elif isinstance(want,list):
            assert len(got)==len(want)
            for a,b in zip(got,want):compare(a,b)
        elif isinstance(want,bool):assert got is want
        elif isinstance(want,(int,float)):
            assert math.isfinite(got) and math.isclose(got,want,rel_tol=1e-8,abs_tol=1e-11)
            maximum=max(maximum,abs(got-want));count+=1
        else:assert got==want
    assert {(x['rest_id'],x['role']) for x in r['rest']}=={(key,role) for key in d['rest'] for role in ['initial','final']}
    for x in r['rest']:compare(x['metrics'],d['rest'][x['rest_id']][x['role']])
    assert {x['case_id'] for x in r['cases']}==set(d['cases'])
    endpoints=0
    for x in r['cases']:
        c=d['cases'][x['case_id']];assert x.get('native_status',x.get('status'))==c['status']
        expected_times={float(k) for k in c['milestones']} if c.get('final_time',0)>0 else set()
        if c.get('final_time',0)>0:expected_times.add(c['final_time'])
        assert {e['time'] for e in x.get('endpoints',[])}==expected_times
        for e in x.get('endpoints',[]):
            milestone=c['milestones'][str(e['time'])];want=milestone['assessment']
            compare(e['legacy_motion'],want['legacy_motion']);compare(e['projected_cubic_reference_raw'],want['projected_cubic_reference_raw'])
            assert e['state_sha256']==milestone['state_sha256'];endpoints+=1
    assert {x['id'] for x in r['comparisons']}==set(d['comparisons'])
    for x in r['comparisons']:compare(x['replayed'],d['comparisons'][x['id']])
    assert (len(r['rest']),endpoints,len(r['cases']),len(r['comparisons']),count,maximum)==(36,25,15,10,1313,0.)
    proof=load(report/'publication-receipts.json');a=proof['archive'];m=proof['merge']
    assert a['runner_alive'] is False and a['state']['status']=='complete'
    assert a['catalog_present'] and a['verification_present']
    assert m['merge_commit']==cfg['required_merge'] and a['state']['catalog']==cfg['archive_path']+'/CATALOG.json'
    result={'status':'passed','compact_hashed_members':238,'rest_metric_sets':36,'evolved_endpoints':25,'case_records':15,'matched_comparisons':10,'uploaded_numeric_values_crosschecked':count,'uploaded_max_absolute_difference':maximum,'workstation_replay_numeric_comparisons':1588,'workstation_full_field_seals':112,'scope':'Compact arithmetic and supplied replay values cross-checked here; full arrays were re-evaluated by the recorded workstation replay, not downloaded or replayed by this script.'}
    print(json.dumps(result),flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);a=p.parse_args();here=Path(__file__).resolve().parent
    cfg=load(here/'verification-config.json');verify(here,a.repo/cfg['run_path'],cfg)
