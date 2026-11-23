"""Independent compact-evidence checks; no production fields or GitHub access."""
import argparse,csv,hashlib,io,json,math,zipfile
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np

def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def gates(m,q,p):
    finite=all(np.isfinite(m[k]) for k in ['relative_force_l2','acceleration_max','hopf_integral','minimum_corner_cone','unit_error','tail_fraction','guard_fraction'])
    rep=bool(finite and abs(abs(m['hopf_integral'])-q)/q<=p['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<p['unit_limit'])
    station=bool(rep and m['relative_force_l2']<=p['force_limit'] and m['acceleration_max']<=p['acceleration_limit']);boundary=bool(finite and m['tail_fraction']<=p['initial_tail_limit'] and m['guard_fraction']<=p['tail_guard_limit'])
    return dict(representation=rep,strict_stationary=station,boundary_admitted=boundary,all_readiness_gates=station and boundary)
def window(history,horizon):
    rows=[r for r in history if horizon-10<r['accepted_step']<=horizon]
    if len(rows)!=10:return {'eligible':False}
    f=float(np.median([r['metrics']['relative_force_l2'] for r in rows]));a=float(np.median([r['metrics']['acceleration_max'] for r in rows]));return {'eligible':all(r['gates']['representation'] and r['gates']['boundary_admitted'] for r in rows),'force':f,'acceleration':a,'joint':max(f/1e-4,a/1e-3)}
def models(x,y):
    x=np.asarray(x);y=np.asarray(y);scale=max(float(np.ptp(y)),.05*float(np.median(abs(y))),1e-12);result=[]
    for name,degree in [('linear',1),('quadratic',2),('exponential',1)]:
        if name=='exponential' and min(y)<=0:continue
        predictions=[];constants=[]
        for i in range(len(x)):
            keep=np.arange(len(x))!=i;coef=np.polyfit(x[keep],np.log(y[keep]) if name=='exponential' else y[keep],degree);v=np.polyval(coef,x[i]);predictions.append(float(np.exp(np.clip(v,-700,700))) if name=='exponential' else float(v));constants.append(float(np.mean(y[keep])))
        error=float(np.mean((np.asarray(predictions)-y)**2));ce=float(np.mean((np.asarray(constants)-y)**2));skill=0. if ce<=1e-24 else 1-error/ce;coef=np.polyfit(x,np.log(y) if name=='exponential' else y,degree)
        result.append({'model':name,'coefficients_highest_power_first':coef.tolist(),'loo_range_nrmse':float(np.sqrt(error)/scale),'loo_skill_vs_constant':skill,'loo_rmse':float(np.sqrt(error)),'eligible':bool(np.sqrt(error)/scale<=.25 and skill>=.1)})
    return result

def assess(evidence,out):
    out.mkdir(parents=True,exist_ok=True);checks={};archive_sha=hashlib.sha256(evidence.read_bytes()).hexdigest();assert archive_sha=='36f7e89797230762ad9dec9385d9132543581835b82e60c7610ef33f3ab219d8','This review is pinned to the supplied completed archive'
    with zipfile.ZipFile(evidence) as z:
        names=z.namelist();assert len(names)==len(set(names));assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names);assert z.testzip() is None
        hashes={}
        for line in z.read('SHA256SUMS').decode().splitlines():
            h,n=line.split('  ',1);assert n not in hashes and hashlib.sha256(z.read(n)).hexdigest()==h;hashes[n]=h
        assert set(names)==set(hashes)|{'SHA256SUMS'};checks['compact_unique_safe_paths_CRC_and_complete_hash_coverage']=True
        package={}
        for line in z.read('handover/SHA256SUMS').decode().splitlines():
            h,n=line.split('  ',1);assert hashlib.sha256(z.read('handover/'+n)).hexdigest()==h;package[n]=h
        assert {n[len('handover/'):] for n in names if n.startswith('handover/')}==set(package)|{'SHA256SUMS'}
        identity=json.loads(z.read('identity.json'));assert hashlib.sha256(z.read('handover/SHA256SUMS')).hexdigest()==identity['package_sha256'];checks['embedded_package_complete_and_identity_matched']=True
        r=json.loads(z.read('record.json'));plan=json.loads(z.read('handover/PLAN.json'));p=plan['registered_gates'];spec=json.loads(z.read('handover/SOURCE.json'));ledger=json.loads(z.read('BULK-LEDGER.json'));fields=json.loads(z.read('FIELD-MANIFEST.json'))['fields'];fm={f['path']:f for f in fields};cases=r['cases'];fit=json.loads(z.read('CURVE-FITS.json'))
        q2=json.loads(z.read('Q2-CONTROL.json'));assert gates(q2['metrics'],2,p)==q2['gates'] and q2['gates']['all_readiness_gates'] and q2['source_sha256']==spec['q2']['sha256'] and q2['source_modified'] is False
        for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:assert np.isclose(q2['metrics'][k],spec['q2']['expected'][k],rtol=1e-6,atol=1e-10)
        checks['unchanged_Q2_control_replay_and_gates']=True
        assert r['source']['endpoint_sha256']==spec['endpoint_sha256']=='013d37612b81c80328b9a7fe24c1d0a1d8dfda3315790bad9b89a1081a5303c2';assert hashlib.sha256(z.read('handover/data/completed-evidence.zip')).hexdigest()==spec['evidence_sha256'];checks['final_parent_and_prior_evidence_identity']=True
        gate_count=0;measurements=[];endpoints=[];timing={k:0. for k in ['optimizer_seconds','backend_audit_seconds','metrics_seconds','checkpoint_seconds']};attempts=0;backend_audits=[];regional=[]
        for c in cases:
            cid=c['case']['id'];history=c['history'];assert len(history)==81 and c['accepted_steps']==80
            charges=json.loads(z.read('cases/'+cid+'/attempt-ledger.json'));assert len(charges)==80 and all(x['attempt']==i+1 and x['charged_before_execution'] for i,x in enumerate(charges));attempts+=len(charges)
            control=json.loads(z.read('cases/'+cid+'/control.json'));assert canonical(control['history'])==control['history_sha256'];assert control['history']==history
            for h in history:
                assert h['iteration']==545+h['accepted_step'];assert gates(h['metrics'],21,p)==h['gates'];gate_count+=1
                for k in timing:timing[k]+=h.get('timing',{}).get(k,0.)
                if 'backend_audit' in h:assert h['backend_audit']['passed'];backend_audits.append(h['backend_audit'])
                measurements.append({'observed_utc':h['recorded_at']['utc'],'observed_melbourne':h['recorded_at']['melbourne'],'case':cid,'nodes':c['case']['nodes'],'spacing':c['spacing'][0],'accepted_step':h['accepted_step'],'native_iteration':h['iteration'],**{k:h['metrics'][k] for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction','max_neighbour_angle']}})
            assert all(b['metrics']['energy']<=a['metrics']['energy']+2e-12 for a,b in zip(history,history[1:]));assert history[55]['iteration']==600 and history[55]['alpha']==1.
            for hh in [30,60,80]:
                expected=window(history,hh);actual=c['windows'][str(hh)];assert expected['eligible']==actual['eligible']
                for k in ['force','acceleration','joint']:assert np.isclose(expected[k],actual[k],rtol=1e-12,atol=1e-15)
            for n in [c['best_retained']['path'],'endpoint.npz',control['checkpoint']]:
                rel='cases/'+cid+'/'+n;seal=json.loads(z.read(rel[:-4]+'.seal.json'));assert seal['sha256']==fm[rel]['sha256'] and seal['identity_sha256']==control['identity']
            best_row=next(h for h in history if h['accepted_step']==c['best_retained']['accepted_step']);best_score=max(best_row['metrics']['relative_force_l2']/1e-4,best_row['metrics']['acceleration_max']/1e-3);assert np.isclose(best_score,c['best_retained']['score']) and np.isclose(best_score,min(max(h['metrics']['relative_force_l2']/1e-4,h['metrics']['acceleration_max']/1e-3) for h in history));assert c['best_retained']['sha256']==fm['cases/'+cid+'/'+c['best_retained']['path']]['sha256'];assert c['endpoint_sha256']==fm['cases/'+cid+'/endpoint.npz']['sha256']
            w80=window(history,80);m0=history[0]['metrics'];m=history[-1]['metrics'];early=[h for h in history if 61<=h['accepted_step']<=70];f61=float(np.median([h['metrics']['relative_force_l2'] for h in early]));a61=float(np.median([h['metrics']['acceleration_max'] for h in early]));init=json.loads(z.read('cases/'+cid+'/INITIALIZATION.json'))
            endpoints.append({'observed_utc':c['final']['recorded_at']['utc'],'observed_melbourne':c['final']['recorded_at']['melbourne'],'case':cid,'nodes':c['case']['nodes'],'spacing':c['spacing'][0],'initial_force':m0['relative_force_l2'],'initial_acceleration':m0['acceleration_max'],'final_energy':m['energy'],'final_force':m['relative_force_l2'],'final_acceleration':m['acceleration_max'],'median_force_71_80':w80['force'],'median_acceleration_71_80':w80['acceleration'],'median_joint_71_80':w80['joint'],'last_window_force_ratio':w80['force']/f61,'last_window_acceleration_ratio':w80['acceleration']/a61,'final_angle_degrees':m['max_neighbour_angle']*180/np.pi,'initial_max_norm_departure':init.get('normalization_correction'),'initial_fixed_layer_correction':init['held_layer_correction'],'all_readiness_gates':c['final']['gates']['all_readiness_gates'],'best_instantaneous_score':c['best_retained']['score']})
        assert attempts==r['charged_optimizer_attempts']==480 and len(backend_audits)==480;checks['all_486_Q21_observations_gates_windows_energy_and_native_phase']=True;checks['480_attempts_audits_checkpoint_cross_references']=True
        for row in ledger['rows']:
            if row['status']=='native_D4_replayed':assert gates(row['metrics'],row['q_label'],p)==row['gates'];gate_count+=1
        checks['all_118_replayed_bulk_gate_decisions']=True
        baseline=next(c for c in cases if c['case']['id']=='mesh-129');eligible=[]
        for c in cases:
            if c['case']['start']=='exact' or c['case']['nodes']==129:continue
            ok=True
            for h in [30,80]:
                a=window(c['history'],h);b=window(baseline['history'],h);ok&=a['joint']<=.95*b['joint'] and all(a[k]<=1.1*b[k] for k in ['force','acceleration'])
            if ok:eligible.append(c['case']['id'])
        selection=json.loads(z.read('SELECTION.json'));assert not eligible and selection['mode']=='no_persistent_measured_joint_benefit';checks['selection_and_unused_budget_recomputed']=True
        points=fit['responses'];refits={}
        for key in ['joint','force','acceleration']:
            vals=models([x['spacing'] for x in points],[x[key] for x in points]);refits[key]=vals
            for expected,actual in zip(vals,fit['fits'][key]['models']):
                assert expected['eligible']==actual['eligible'];assert np.isclose(expected['loo_range_nrmse'],actual['loo_range_nrmse'],rtol=1e-8,atol=1e-10);assert np.isclose(expected['loo_skill_vs_constant'],actual['loo_skill_vs_constant'],rtol=1e-8,atol=1e-9)
        checks['all_nine_registered_fit_scores_and_eligibility_recomputed']=True
        bulkrows=[];unique={};scope_counts={}
        for x in ledger['rows']:
            path=x['relative_home_path'];category='static_or_stationary_endpoint'
            if '/artifacts/s5-b/' in path and '/cases/' in path:category='physical_time_case_checkpoint_separate_audit'
            elif x['status']=='deferred' and '20261114t120027z' in path:category='secondary_incomplete_run_not_original_source'
            scope_counts[category]=scope_counts.get(category,0)+1
            if x['status']=='native_D4_replayed':unique.setdefault((x['q_label'],tuple(x['shape']),tuple(x['lengths']),x['array_sha256']),[]).append(x['id'])
            bulkrows.append({'observed_utc':x['recorded_at']['utc'],'observed_melbourne':x['recorded_at']['melbourne'],'candidate':x['id'],'q':x['q_label'],'source':path,'reported_status':x['status'],'review_scope':category,'reason':x.get('reason',''),'strict_stationary':x.get('gates',{}).get('strict_stationary'),'boundary_admitted':x.get('gates',{}).get('boundary_admitted'),'all_readiness':x.get('gates',{}).get('all_readiness_gates')})
        assert len(ledger['rows'])==189 and len(unique)==100;checks['catalogue_counts_scope_and_duplicate_measurement_accounting']=True
        spatial=json.loads(z.read('SPATIAL-COMPARISON.json'))
        for x in spatial['comparisons']:
            c=next(c for c in cases if c['case']['nodes']==x['nodes']);a=next(h for h in c['history'] if h['accepted_step']==x['horizon']);b=next(h for h in baseline['history'] if h['accepted_step']==x['horizon']);delta=abs(a['metrics']['energy']-b['metrics']['energy'])/abs(b['metrics']['energy']);assert np.isclose(delta,x['energy_relative_difference'],rtol=1e-12);assert x['energy_difference_within_original_limit']==(delta<=p['mesh_energy_limit'])
        checks['original_2_percent_energy_diagnostic_recomputed']=True
        for name in ['FINAL-BASELINE-REPLAY.json','EARLIER-BEST-COMPARISON.json','SELECTED-SHIFT-CONTRAST.json','cases/mesh-129/FINAL-LOCALIZATION.json']:
            obj=json.loads(z.read(name));d=obj.get('localized',obj)
            for k in ['force','acceleration']:
                rr=d['regions'][k];assert np.isclose(sum(x['squared_residual_fraction'] for x in rr['regions'].values()),1,atol=1e-9);assert np.isclose(sum(rr['spectrum']['power_fractions']),1,atol=1e-9)
            regional.append({'source':name,'force_core_fraction':d['regions']['force']['regions']['core_neighborhood']['squared_residual_fraction'],'acceleration_core_fraction':d['regions']['acceleration']['regions']['core_neighborhood']['squared_residual_fraction']})
        checks['regional_and_spectral_fraction_internal_consistency']=True
        measured=[x for x in endpoints if x['case']!='exact-control'];angle_fits=models([x['spacing'] for x in measured],[x['final_angle_degrees'] for x in measured]);predictions=[]
        for m in angle_fits:
            co=m['coefficients_highest_power_first'];kind=m['model']
            if kind=='linear':root=(30-co[1])/co[0]
            elif kind=='exponential':root=(np.log(30)-co[1])/co[0]
            else:root=min([r.real for r in np.roots([co[0],co[1],co[2]-30]) if abs(r.imag)<1e-8],key=lambda h:abs(h-.17))
            value=np.polyval(co,30.72/176);predictions.append({**m,'spacing_for_30_degrees':float(root),'nodes_for_30_degrees':float(30.72/root+1),'predicted_angle_at_177':float(np.exp(value) if kind=='exponential' else value),'status':'post_hoc_geometric_warning_extrapolation_not_stationarity_prediction','confidence_interval':False})
        start=datetime.fromisoformat(identity['recorded_at']['utc']);end=datetime.fromisoformat(json.loads(z.read('status.json'))['recorded_at']['utc']);launch_seconds=(end-start).total_seconds();bulk_seconds=sum(x['wall_seconds'] for x in ledger['rows']);timing.update(bulk_audit_seconds=bulk_seconds,other_tracked_worker_seconds=r['elapsed_seconds']-bulk_seconds-sum(timing.values()),before_tracked_worker_interval_seconds=launch_seconds-r['elapsed_seconds'])
        telemetry=json.loads(z.read('TELEMETRY-FROZEN.json'));checks['zero_physical_time_and_no_recorded_hard_limit_or_OOM']=r['physical_time_steps']==0 and all(telemetry['cgroup']['memory.events'][k]==0 for k in ['max','oom','oom_kill'])
        report={'reviewed_at':stamp(),'source_archive_sha256':archive_sha,'source_run':identity['run_id'],'status':'compact_review_complete_full_fields_not_replayed_here','checks':checks,'compact_payloads':len(hashes),'embedded_payloads':len(package),'q21_observations':486,'charged_attempts':480,'unused_budget':240,'retained_full_fields':len(fields),'retained_field_bytes':sum(f['bytes'] for f in fields),'bulk_replayed':118,'bulk_deferred':71,'unique_replayed_charge_geometry_field_tuples':len(unique),'bulk_scope_counts':scope_counts,'bulk_passing_rows':sum(x.get('gates',{}).get('all_readiness_gates',False) for x in ledger['rows']),'strict_stationary_rows':sum(x.get('gates',{}).get('strict_stationary',False) for x in ledger['rows']),'gate_records_recomputed':gate_count,'launch_to_complete_seconds':launch_seconds,'tracked_worker_seconds':r['elapsed_seconds'],'timing_seconds':timing,'registered_refits':refits,'post_hoc_angle_models':predictions,'regional_summaries':regional,'endpoints':endpoints,'limits':['No full NPZ arrays are included; full-field CRC/hash/metric replay and finer-grid morphology were not independently performed here.','Registered-case and bulk measurement values were assessed from compact records, not newly simulated.','Post-hoc angle extrapolations are not registered optimum tests, confidence intervals or stability criteria.','No live GitHub state was queried; PR95 refers to preparation according to the supplied terminal and saved receipt.']}
        write(out/'INDEPENDENT-REVIEW.json',report)
        for name,rows in [('ENDPOINTS.csv',endpoints),('BULK-SCOPE-REVIEW.csv',bulkrows),('MEASUREMENTS.csv',measurements)]:
            buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows);(out/name).write_text(buf.getvalue())
        write(out/'ANGLE-EXPLORATION.json',{'reviewed_at':stamp(),'models':predictions,'warning':'Exploratory finite-horizon geometry relationship only; no physical or numerical admission is inferred.'})
        return report,r,ledger

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();report,_,_=assess(args.evidence,args.output);print(json.dumps({'status':report['status'],'checks':report['checks'],'source_sha256':report['source_archive_sha256']}))
