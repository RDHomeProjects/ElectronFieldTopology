"""Q3 retained-history observation controls; no evolution or field reconstruction.
Apache-2.0. AI-assisted implementation; original acceptance flags are preserved.
"""
import argparse,csv,hashlib,html,io,json,math,os,secrets,subprocess,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
if not __debug__:raise RuntimeError('Run without Python optimization')
ROOT=Path(__file__).resolve().parent
MERGE='50a1337739f5063bfb459c8d7111077b9ccffd33'
SOURCE_RUN='20261109t134425z-89d28344'
EVIDENCE='c066b7f2bab8308cf68945b0b6e5de837585775647634ffd721b3e84bee87517'
NATIVE='reports/s5-b/010-intermediate-q-survey/runs/'+SOURCE_RUN
def need(ok,s):
    if not ok:raise ValueError(s)
def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def norm(x):return math.sqrt(sum(v*v for v in x))
def fit(rows):
    need(len(rows)>=3,'Need at least three recorded observations')
    t=[r['time'] for r in rows];need(len(t)==len(set(t)) and t==sorted(t),'Repeated/unsorted observation times')
    mean=sum(t)/len(t);den=sum((v-mean)**2 for v in t);need(den>0,'Zero time span')
    return [sum((r['time']-mean)*r['centroid'][i] for r in rows)/den for i in range(3)]
def sample(rows,start,end,cadence):
    count=round((end-start)/cadence)
    if abs(start+count*cadence-end)>1e-10:return None
    selected=[]
    for i in range(count+1):
        t=start+i*cadence;matches=[r for r in rows if abs(r['time']-t)<1e-10]
        if len(matches)!=1:return None
        selected.append(matches[0])
    return selected if len(selected)>=3 else None
def read_zip(path):
    need(digest(path)==EVIDENCE,'Native evidence SHA-256 differs')
    z=zipfile.ZipFile(path);names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Invalid ZIP inventory/CRC')
    for n in names:need(not Path(n).is_absolute() and '..' not in Path(n).parts,'Unsafe member')
    ledger=json.loads(z.read('evidence-hashes.json'))['sha256'];need(set(names)==set(ledger)|{'evidence-hashes.json'},'Ledger coverage differs')
    for n,h in ledger.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Member hash differs: '+n)
    return z,json.loads(z.read('campaign.json')),json.loads(z.read('plan.json'))
def analyze(path):
    z,d,plan=read_zip(path);rows=[];baselines=[];missing=[];proxies=[]
    need(d['record_id']==SOURCE_RUN and d['status']=='complete_pending_review','Wrong source run/status')
    for key,c in d['cases'].items():
        if c['q']!=3 or c.get('final_time',0)<=0:continue
        hist=json.loads(z.read('cases/'+key+'/history-combined.json'))
        need(all(math.isfinite(v) for r in hist for v in r['centroid']),'Nonfinite centroid')
        vel=fit(hist);expected=[0.,0.,0.];expected[c['axis']]=c['beta']
        legacy=c['assessment']['legacy_motion']
        need(all(math.isclose(a,b,abs_tol=2e-12,rel_tol=1e-9) for a,b in zip(vel,legacy['fitted_centroid_velocity'])),'Original centroid fit does not replay')
        baselines.append({'case_id':key,'original_status':c['status'],'original_time':c['final_time'],'original_speed_error_fraction':legacy['speed_relative_error'],'original_checks':legacy['checks']})
        first=hist[0]
        proxies.append({'case_id':key,'initial_centroid':first['centroid'],'initial_momentum':first['momentum'],'initial_hamiltonian':first['energy'],'initial_continuum_energy':first['continuum_energy'],'momentum_over_hamiltonian':[v/first['energy'] for v in first['momentum']],'momentum_over_continuum_energy':[v/first['continuum_energy'] for v in first['momentum']],'scope':'Diagnostic ratios only, not substituted centroid velocities or a discrete conservation-law identity.'})
        for end in [.1,.2,.5]:
            if end>c['final_time']+1e-10:continue
            for start in [0.,.02,.04]:
                for cadence in [.01,.02,.04]:
                    selected=sample(hist,start,end,cadence)
                    if selected is None:
                        missing.append({'case_id':key,'start':start,'end':end,'cadence':cadence,'reason':'At least three exact matching observations unavailable; no interpolation'});continue
                    v=fit(selected);err=norm([a-b for a,b in zip(v,expected)])
                    endpoint=[(selected[-1]['centroid'][i]-selected[0]['centroid'][i])/(end-start) for i in range(3)]
                    rows.append({'case_id':key,'axis':c['axis'],'beta':c['beta'],'start':start,'end':end,'cadence':cadence,'observations':len(selected),'fitted_velocity':v,'endpoint_velocity':endpoint,'relative_speed_error_percent':100*err/abs(c['beta']) if c['beta'] else None,'absolute_rest_speed':err if not c['beta'] else None,'axial_speed_deficit_percent':100*(c['beta']-v[c['axis']])/c['beta'] if c['beta'] else None,'same_numeric_threshold_met':err/abs(c['beta'])<=plan['limits']['speed_relative'] if c['beta'] else err<=plan['limits']['rest_speed_absolute'],'scope':'Alternative observation fit; not a replacement acceptance decision.'})
    ranges=[]
    for key in sorted({r['case_id'] for r in rows}):
        common=[r for r in rows if r['case_id']==key and r['end']==.2 and r['relative_speed_error_percent'] is not None]
        if common:
            vals=[r['relative_speed_error_percent'] for r in common];ranges.append({'case_id':key,'window_end':.2,'minimum_percent':min(vals),'maximum_percent':max(vals),'fit_spread_percentage_points':max(vals)-min(vals),'crosses_one_percent':min(vals)<=1<max(vals),'scope':'Recorded cadence/start-window envelope; not an uncertainty interval or corrected speed.'})
    pairs=[]
    definitions=[('mesh_coarse_medium','q3-axial-coarse-fresh-z-dt0.01','q3-axial-medium-warm-z-dt0.01'),('mesh_medium_fine','q3-axial-medium-warm-z-dt0.01','q3-axial-fine-warm-z-dt0.01'),('orientation','q3-axial-fine-warm-z-dt0.01','q3-axial-fine-warm-x-dt0.01'),('domain','q3-axial-fine-warm-z-dt0.01','q3-axial-domain-warm-z-dt0.01'),('coarse_screen_cadence','q3-axial-coarse-fresh-screen-dt0.01','q3-axial-coarse-fresh-z-dt0.01')]
    for name,left,right in definitions:
        for end in [.1,.2]:
            a=next((r for r in rows if r['case_id']==left and r['start']==0 and r['end']==end and r['cadence']==.02),None);b=next((r for r in rows if r['case_id']==right and r['start']==0 and r['end']==end and r['cadence']==.02),None)
            if a and b:pairs.append({'comparison':name,'end':end,'cadence':.02,'left':left,'right':right,'left_error_percent':a['relative_speed_error_percent'],'right_error_percent':b['relative_speed_error_percent'],'difference_percentage_points':b['relative_speed_error_percent']-a['relative_speed_error_percent']})
    return {'source_run':SOURCE_RUN,'source_commit':d['source_commit'],'evidence_sha256':EVIDENCE,'scope':'Retained-history observation controls only. No fields reconstructed, no physical steps, no changed gates. Ratios do not establish a conservation identity. Missing observation times are skipped.','original_cases':baselines,'fit_rows':rows,'skipped_fits':missing,'initial_proxies':proxies,'matched_pairs':pairs,'fit_envelopes':ranges}
def verify_package():
    for line in (ROOT/'SHA256SUMS').read_text().splitlines():
        h,n=line.split('  ',1);need(digest(ROOT/n)==h,'Package differs: '+n)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['run','status','verify'],nargs='?',default='run');p.add_argument('--repo',type=Path,default=Path.home()/'ElectronFieldTopology-repository-admin');a=p.parse_args();verify_package();repo=a.repo.expanduser().resolve();pointer=repo/'artifacts/Q3-OBSERVATION-DIAGNOSTIC-CURRENT'
    if a.mode=='verify':print(json.dumps({'recorded_at':stamp(),'status':'package_verified'}));return
    if a.mode=='status':
        need(pointer.exists(),'No diagnostic output pointer yet');out=Path(pointer.read_text().strip());print((out/'status.json').read_text());return
    subprocess.run(['git','merge-base','--is-ancestor',MERGE,'HEAD'],cwd=repo,check=True)
    need(not subprocess.check_output(['git','diff','--name-only'],cwd=repo,text=True).strip() and not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=repo,text=True).strip(),'Tracked checkout changes found; preserve them and use a clean source checkout')
    out=repo/'artifacts/q3-observation-diagnostic'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4));out.mkdir(parents=True)
    record={'recorded_at':stamp(),'status':'working','output':str(out),'source_run':SOURCE_RUN,'script_sha256':digest(Path(__file__)),'checkout_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()};save(out/'status.json',record);pointer.write_text(str(out)+'\n')
    try:
        result=analyze(repo/NATIVE/'evidence.zip');result['recorded_at']=stamp();save(out/'observation-diagnostic.json',result)
        with (out/'fit-envelopes.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(result['fit_envelopes'][0]),lineterminator='\n');w.writeheader();w.writerows(result['fit_envelopes'])
        content='<h1>Q3 observation diagnostic</h1><p>'+html.escape(json.dumps(result['recorded_at']))+'</p><p>Alternative fitting controls; original pass/fail flags remain unchanged. No new trajectories or physical convergence claim.</p><table><tr><th>Case</th><th>Minimum error %</th><th>Maximum error %</th><th>Crosses 1%?</th></tr>'
        for r in result['fit_envelopes']:content+='<tr><td>'+html.escape(r['case_id'])+'</td><td>'+str(r['minimum_percent'])+'</td><td>'+str(r['maximum_percent'])+'</td><td>'+str(r['crosses_one_percent'])+'</td></tr>'
        (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Q3 observation diagnostic</title><style>body{font:16px/1.6 system-ui;padding:28px;color:#18324a}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}table{border-collapse:collapse}</style>'+content+'</table><p>See observation-diagnostic.json for matched comparisons, original flags, initial momentum/energy proxies and skipped unavailable observation fits.</p></html>')
        shutil_source=Path(__file__).read_bytes();(out/'diagnostic.py').write_bytes(shutil_source)
        record.update(status='complete_pending_review',finished_at=stamp(),fit_rows=len(result['fit_rows']),matched_pairs=len(result['matched_pairs']));save(out/'status.json',record)
        (out/'SHA256SUMS').write_text(''.join(digest(x)+'  '+x.name+'\n' for x in sorted(out.iterdir()) if x.is_file()))
        with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.iterdir()):
                if f.is_file() and f.name!='evidence.zip':z.write(f,f.name)
        print(json.dumps(record));print('Upload: '+str(out/'evidence.zip'));print('Browser report: '+str(out/'REPORT.html'))
    except Exception as e:record.update(status='error',error=str(e),finished_at=stamp());save(out/'status.json',record);raise
if __name__=='__main__':main()
