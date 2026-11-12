if not __debug__:raise RuntimeError("Run without Python optimization")
"""Independent compact-record arithmetic audit; no field replay or evolution.
Apache-2.0. AI-assisted analysis of supplied numerical evidence.
"""
from pathlib import Path
import argparse, collections, hashlib, json, math, zipfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

EXPECTED_ZIP='c066b7f2bab8308cf68945b0b6e5de837585775647634ffd721b3e84bee87517'
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return sha(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def close(a,b):
    if isinstance(a,list):
        assert len(a)==len(b)
        for x,y in zip(a,b):close(x,y)
    else:assert math.isclose(a,b,rel_tol=2e-9,abs_tol=2e-13),(a,b)
def norm(v):return math.sqrt(sum(x*x for x in v))
def slope(rows):
    t=[r['time'] for r in rows];mean=sum(t)/len(t);den=sum((x-mean)**2 for x in t)
    return [sum((r['time']-mean)*r['centroid'][k] for r in rows)/den for k in range(3)]
def audit(evidence,receipt,summary):
    raw=Path(evidence).read_bytes();assert sha(raw)==EXPECTED_ZIP
    z=zipfile.ZipFile(Path(evidence));assert z.testzip() is None
    names=z.namelist();assert len(names)==len(set(names))
    for name in names:
        p=Path(name);assert not p.is_absolute() and '..' not in p.parts
    load=lambda n:json.loads(z.read(n))
    ledger=load('evidence-hashes.json')['sha256'];assert set(names)==set(ledger)|{'evidence-hashes.json'}
    for name,h in ledger.items():assert sha(z.read(name))==h,name
    assert z.read('SUMMARY.md')==Path(summary).read_bytes()
    attest=json.loads(Path(receipt).read_text());assert attest['evidence_sha256']==EXPECTED_ZIP
    d=load('campaign.json');plan=load('plan.json');comparisons=load('comparisons.json')['rows']
    assert d['status']=='complete_pending_review' and d['phase']=='complete'
    assert d['record_id']==attest['record_id'] and d['source_commit']==attest['source_commit']
    assert canonical(plan)==d['config_sha256']==attest['config_sha256']
    assert len(ledger)==attest['compact_hashed_members']==238
    assert len(d['rest'])==attest['rest_records']==18
    assert len(d['cases'])==attest['case_records']==15
    assert d['comparisons']==comparisons
    rest=[];cases=[];endpoint_count=0;history_total=0
    for name,row in d['rest'].items():
        hist=load('rest/'+name+'/history.json');last=hist[-1];m=row['final']['stationarity']
        for key in ['energy','relative_force_l2','acceleration_max','hopf_integral','minimum_corner_cone','unit_error']:close(m[key],last[key])
        stationary=(m['relative_force_l2']<=plan['readmission']['relative_force_l2'] and m['acceleration_max']<=plan['readmission']['acceleration_max'] and abs(abs(m['hopf_integral'])-row['q'])/row['q']<=plan['readmission']['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<1e-10)
        assert stationary==(row['status']=='stationary'),name
        rest.append({'id':name,'q':row['q'],'status':row['status'],'iterations':last['iteration'],'calls':row['calls_allocated'],'energy':m['energy'],'force':m['relative_force_l2'],'acceleration':m['acceleration_max'],'force_over_limit':m['relative_force_l2']/plan['readmission']['relative_force_l2'],'acceleration_over_limit':m['acceleration_max']/plan['readmission']['acceleration_max'],'tail_percent':100*row['final']['tail']['fraction'],'minimum_recorded_force':min(x['relative_force_l2'] for x in hist),'reason':row.get('reason')})
    for name,row in d['cases'].items():
        ad=row['admission'];checks={'projection':ad['projection']['passed'],'initial_shape':ad['initial_legacy_shape_floor']<=plan['limits']['shape_relative'],'initial_tail':ad['initial_tail']['fraction']<=plan['initial_tail_reserve'],'predicted_tail':ad['predicted_coasting_tail']['fraction']<=plan['initial_tail_reserve'],'width3_guard':ad['expanded_guard']['fraction']<=plan['expanded_guard_limit']}
        assert all(checks.values())==ad['passed']
        item={'id':name,'q':row['q'],'status':row['status'],'time':row.get('final_time'),'requested_time':row['duration'],'beta':row['beta'],'axis':row['axis'],'dt':row['dt'],'admission_failures':[k for k,v in checks.items() if not v],'initial_tail_percent':100*ad['initial_tail']['fraction'],'width3_guard_percent':100*ad['expanded_guard']['fraction']}
        if row.get('final_time',0)>0:
            hist=load('cases/'+name+'/history-combined.json');history_total+=len(hist)
            times=[x['time'] for x in hist];assert len(times)==len(set(times)) and times==sorted(times)
            def recalc(rows,want):
                nonlocal endpoint_count
                fit=slope(rows);target=[0.,0.,0.];target[row['axis']]=row['beta'];err=norm([a-b for a,b in zip(fit,target)])
                e0=rows[0]['energy'];p0=rows[0]['momentum']
                energy=max(abs(r['energy']-e0)/abs(e0) for r in rows)
                momentum=max(norm([a-b for a,b in zip(r['momentum'],p0)])/abs(e0) for r in rows)
                close(fit,want['fitted_centroid_velocity']);close(err,want['speed_absolute_error']);close(energy,want['max_energy_relative_drift']);close(momentum,want['max_momentum_drift_over_initial_energy'])
                if row['beta']:close(err/abs(row['beta']),want['speed_relative_error'])
                assert want['checks']['speed']==(err/abs(row['beta'])<=plan['limits']['speed_relative'] if row['beta'] else err<=plan['limits']['rest_speed_absolute'])
                assert want['checks']['energy']==(energy<=plan['limits']['energy_relative'])
                assert want['checks']['momentum']==(momentum<=plan['limits']['momentum_scaled'])
                assert all(want['checks'].values())==want['bounded_case_gates_pass']
                endpoint_count+=1
                return fit,err
            for t,m in row['milestones'].items():recalc([r for r in hist if r['time']<=float(t)+1e-12],m['assessment']['legacy_motion'])
            a=row['assessment'];m=a['legacy_motion'];fit,err=recalc(hist,m)
            observed=max(r['boundary_tail']['fraction'] for r in hist)
            close(observed,a['maximum_observed_tail_fraction'])
            assert a['tail_pass_all_observations']==all(r['boundary_tail']['fraction']<=plan['limits']['tail_fraction'] for r in hist)
            if row['status']=='screen_pass':assert m['bounded_case_gates_pass'] and a['tail_pass_all_observations'] and row['final_time']>=row['duration']-1e-12
            if row['status']=='screen_failed':assert not m['bounded_case_gates_pass']
            item.update(velocity=fit,speed_error_percent=100*err/abs(row['beta']) if row['beta'] else None,rest_speed=err if not row['beta'] else None,shape_error_percent=100*m['translated_static_field_relative_l2'],tail_percent=100*observed,failed_gates=[k for k,v in m['checks'].items() if not v],energy_relative_drift=m['max_energy_relative_drift'],momentum_scaled_drift=m['max_momentum_drift_over_initial_energy'],initial_state_sha256=row['initial_state_sha256'])
        cases.append(item)
    fine=[d['cases']['q3-axial-fine-warm-z-dt'+x] for x in ['0.02','0.01','0.005']]
    assert len({r['initial_state_sha256'] for r in fine})==1
    orders=[]
    for w in comparisons['q3-temporal']['matched_windows']:
        for key,kind in [('field_relative_l2','field'),('rate_relative_l2','rate')]:
            order=math.log2(w['coarse_medium'][key]/w['medium_fine'][key]);close(order,w[kind+'_order']['order']);orders.append({'time':w['time'],'kind':kind,'order':order})
    now=datetime.now(timezone.utc)
    return {'recorded_at':{'utc':now.isoformat(),'melbourne':now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()},'source_run':d['record_id'],'source_commit':d['source_commit'],'evidence_sha256':sha(raw),'status':'compact_record_checks_passed','verified_here':{'compact_hashed_members':len(ledger),'zip_members':len(names),'summary_byte_exact':True,'config_canonical_hash':True,'rest_endpoint_metric_sets':len(rest),'evolved_cases_with_history_arithmetic':sum(r.get('time',0) is not None and r.get('time',0)>0 for r in cases),'history_rows':history_total,'milestone_and_final_assessment_recalculations':endpoint_count,'identical_fine_dt_initial_state_hash':True,'descriptive_order_arithmetic':orders},'workstation_attestation':attest,'limits':['112 sealed field/curve files were verified on the workstation according to its receipt; those files are absent here and were not independently rehashed here.','Centroid, energy, momentum and tail history arithmetic was recalculated from authenticated records. Shape/topology and field differences require full-field replay; their numerical values remain recorded measurements.','No numerical source commit object was fetched; source/lock verification is the workstation attestation.','No new optimization, physical-time evolution, threshold change or GitHub interaction.'],'counts':{'rest':dict(collections.Counter(r['status'] for r in rest)),'cases':dict(collections.Counter(r['status'] for r in cases))},'rest':rest,'cases':cases,'comparisons':comparisons}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--summary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists(),'Choose a new output path'
    result=audit(a.evidence,a.receipt,a.summary);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'verified_here':result['verified_here'],'counts':result['counts'],'output':str(a.output)}))
