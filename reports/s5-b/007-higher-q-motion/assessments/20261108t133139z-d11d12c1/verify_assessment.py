"""Read-only compact evidence and original-gate replay. Apache-2.0."""
import argparse,csv,hashlib,io,json,math,subprocess,zipfile
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from zoneinfo import ZoneInfo

RUN='20261108t022631z-7e649031'
BASE='92a5cc24c2b8192ed0b2b9d64e2e0a42f8414529'
RUN_PATH=Path('reports/s5-b/007-higher-q-motion/runs')/RUN
CONFIG_SHA='484b45180757ed8bcd1bf1fe82353c898d7080352a8ff8c85c1fe9de6609feac'
EVIDENCE_SHA='2da85f6fcc5cb49d4451142a3d6b6ef129b6cbf41c141a2d51c8a226b13fa891'

def stamp():
    now=datetime.now(timezone.utc)
    return {'utc':now.isoformat(),'melbourne':now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def need(ok,message):
    if not ok:raise ValueError(message)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def close(a,b,rel=1e-8,abs_tol=1e-11):
    need(math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=rel,abs_tol=abs_tol),f'Numeric disagreement {a} versus {b}')
def write_json(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def csv_file(path,rows):
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def checksums(folder):
    folder=Path(folder);seen=set()
    for line in (folder/'SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1);p=PurePosixPath(name)
        need(not p.is_absolute() and '..' not in p.parts and name not in seen,'Unsafe/duplicate checksum path')
        need(sha(folder/name)==digest,'Checksum differs '+name);seen.add(name)
    need(seen=={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name!='SHA256SUMS'},'Checksum coverage differs')
    return len(seen)

def verify(repo):
    repo=Path(repo).resolve();run=repo/RUN_PATH;checksums(run)
    need(sha(run/'evidence.zip')==EVIDENCE_SHA,'Evidence ZIP differs')
    with zipfile.ZipFile(run/'evidence.zip') as z:
        names=z.namelist();need(len(names)==len(set(names))==41,'Unexpected ZIP coverage');need(z.testzip() is None,'ZIP CRC failure')
        for name in names:
            p=PurePosixPath(name);need(not p.is_absolute() and '..' not in p.parts,'Unsafe evidence member')
        ledger=json.loads(z.read('evidence-hashes.json'));need(set(ledger['sha256'])==set(names)-{'evidence-hashes.json'},'Evidence ledger coverage differs')
        for name,h in ledger['sha256'].items():need(hashlib.sha256(z.read(name)).hexdigest()==h,'Evidence payload differs '+name)
        for p in run.iterdir():
            if p.name in names:need(p.read_bytes()==z.read(p.name),'Published/ZIP duplicate differs '+p.name)
        load=lambda name:json.loads(z.read(name))
        c=load('campaign.json');p=load('plan.json');need(c['record_id']==RUN and c['source_commit']=='8c2c9ed492f35a6cc0615085f8ca42479a6227e0','Run identity differs')
        need(canonical(p)==c['config_sha256']==CONFIG_SHA,'Config differs')
        for name,h in c['source_sha256'].items():need(sha(repo/'src/electron_field_topology'/name)==h,'Numerical source changed '+name)
        need(c['status']=='complete_pending_review' and set(c['rest'])=={'q2','q17','q19'} and set(c['cases'])=={'q2-dt0.01'} and not c['temporal'],'Run coverage differs')
        need(p['readmission']['relative_force_l2']==1e-4 and p['readmission']['acceleration_max']==1e-3 and p['maximum_readmission_calls']==4,'Preparation gate changed')
        need(p['limits']==json.loads((repo/'experiments/configs/sf-motion/lowq-motion.json').read_text())['limits'],'Original motion limits changed')
        rest_rows=[];history_rows=[]
        for key,r in c['rest'].items():
            q=r['q'];m=r['final']['stationarity'];initial=r['initial']['stationarity'];h=load('rest/'+key+'/history.json')
            native=load('rest/'+key+'/result.json') if key!='q2' else None
            if native:
                ends=[v for v in h if 'optimizer_message' in v]
                need(r['status']=='preparation_unresolved' and r['optimizer_calls_allocated']==4 and native['status']=='checkpointed' and native['reason'] is None,'Unexpected preparation outcome')
                need(native['iterations']==200 and native['passes']==4 and [v['iteration'] for v in ends]==[50,100,150,200],'Preparation allocation differs')
                need(all(v['optimizer_message']=='iteration batch complete' for v in ends),'Native optimizer failure requires separate review')
                need(all(h[i]['energy']<=h[i-1]['energy']+1e-12 for i in range(1,len(h))),'Sampled objective increased')
                for v in h:need(abs(abs(v['hopf_integral'])-q)/q<=.05 and v['minimum_corner_cone']>0 and v['unit_error']<1e-10,'Sampled topology/constraints failed')
                need(m['relative_force_l2']>1e-4 and m['acceleration_max']>1e-3 and 'admission' not in r,'Higher-Q admission/absence differs')
            else:need(r['status']=='admitted' and r['optimizer_calls_allocated']==0,'Q2 reference differs')
            for v in h:
                history_rows.append({'model':key,'native_utc':v['recorded_at']['utc'],'native_melbourne':v['recorded_at']['melbourne'],'iteration':v['iteration'],'pass_index':v['pass_index'],'energy':v['energy'],'relative_force_l2':v['relative_force_l2'],'acceleration_max':v['acceleration_max'],'hopf_integral':v['hopf_integral'],'minimum_corner_cone':v['minimum_corner_cone'],'batch_end':bool('optimizer_message' in v),'objective_calls':v.get('objective_calls','')})
            rest_rows.append({'model':key,'status':r['status'],'calls':r['optimizer_calls_allocated'],'energy_initial':initial['energy'],'energy_final':m['energy'],'energy_drop_percent':100*(initial['energy']-m['energy'])/initial['energy'],'force_initial':initial['relative_force_l2'],'force_final':m['relative_force_l2'],'force_limit_ratio':m['relative_force_l2']/1e-4,'acceleration_initial':initial['acceleration_max'],'acceleration_final':m['acceleration_max'],'acceleration_limit_ratio':m['acceleration_max']/1e-3,'hopf_final':m['hopf_integral'],'hopf_error_percent':100*abs(abs(m['hopf_integral'])-q)/q,'cone_final':m['minimum_corner_cone'],'rest_tail_percent':100*r['final']['tail']['fraction']})
        hist=load('cases/q2-dt0.01/history-combined.json');need([v['step'] for v in hist]==list(range(21)),'History steps differ')
        r=c['cases']['q2-dt0.01'];milestones=[]
        for t,row in r['milestones'].items():
            a=row['assessment'];m=a['legacy_motion'];end=float(t);hh=[v for v in hist if v['time']<=end+1e-12];first=hh[0];e0=first['energy']
            # Independent scalar least-squares implementation, no solver/metrics imports.
            ts=[v['time'] for v in hh];mean=sum(ts)/len(ts);den=sum((v-mean)**2 for v in ts)
            vel=[sum((v['time']-mean)*v['centroid'][i] for v in hh)/den for i in range(3)]
            speed=math.sqrt(sum((vel[i]-(.3 if i==2 else 0))**2 for i in range(3)))/.3
            energy=max(abs(v['energy']-e0)/abs(e0) for v in hh)
            momentum=max(math.sqrt(sum((v['momentum'][i]-first['momentum'][i])**2 for i in range(3)))/abs(e0) for v in hh)
            tail=max(v['boundary_tail']['fraction'] for v in hh)
            close(speed,m['speed_relative_error']);close(energy,m['max_energy_relative_drift']);close(momentum,m['max_momentum_drift_over_initial_energy']);close(tail,a['maximum_observed_tail_fraction'])
            checks={'energy':energy<=p['limits']['energy_relative'],'momentum':momentum<=p['limits']['momentum_scaled'],'constraints':max(max(v['unit_error'],v['tangency_error']) for v in hh)<1e-10,'shape':m['translated_static_field_relative_l2']<=p['limits']['shape_relative'],'speed':speed<=p['limits']['speed_relative'],'topology':abs(abs(m['final']['hopf_integral'])-2)/2<=p['limits']['charge_relative_error'] and m['final']['minimum_corner_cone']>0,'tail':m['final']['boundary_shell_energy_fraction']<=p['limits']['tail_fraction']}
            need(checks==m['checks'] and all(checks.values()) and not row['decision']['stop'],'Original Q2 gate differs')
            need(all(v['original_tail_pass'] and v['tail_warning_clear'] for v in hh),'Tail observation differs')
            milestones.append({'time':end,'speed_percent':100*speed,'shape_percent':100*m['translated_static_field_relative_l2'],'energy_drift':energy,'momentum_drift':momentum,'max_tail_percent':100*tail,'original_gates_passed':sum(checks.values()),'stopped':row['decision']['stop']})
        elapsed=(datetime.fromisoformat(json.loads((run/'exit.json').read_text())['recorded_at']['utc'])-datetime.fromisoformat(c['started_at']['utc'])).total_seconds()
        result={'recorded_at':stamp(),'run':RUN,'source_commit':c['source_commit'],'config_sha256':CONFIG_SHA,'evidence_sha256':EVIDENCE_SHA,'archive_members':len(names),'hashed_members':len(ledger['sha256']),'numerical_source_files':len(c['source_sha256']),'rest_candidates':3,'higher_q_iterations_each':200,'higher_q_motion_cases':0,'q2_motion_cases':1,'q2_observations':len(hist),'q2_milestones':len(milestones),'q2_original_gates_each_milestone':7,'wall_seconds_from_timestamps':elapsed,'rest':rest_rows,'milestones':milestones,'optimizer_history':history_rows,'disposition':'q2_short_reference_pass; q17_q19_preparation_unresolved; higher_q_motion_not_tested','scope':'Compact scalar/provenance replay; shapes and topology values require separate full-field replay.'}
        return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args();v=verify(a.repo)
    if a.output:
        a.output.mkdir(parents=True,exist_ok=True);write_json(a.output/'compact-verification.json',v)
        for name,key in [('rest-metrics.csv','rest'),('optimizer-history.csv','optimizer_history'),('q2-milestones.csv','milestones')]:
            csv_file(a.output/name,[{'assessed_utc':v['recorded_at']['utc'],'assessed_melbourne':v['recorded_at']['melbourne'],**row} for row in v[key]])
    print(json.dumps({k:v[k] for k in ['recorded_at','archive_members','hashed_members','numerical_source_files','q2_observations','disposition']}))
if __name__=='__main__':main()
