"""Checkpointed bounded dependency studies; Apache-2.0."""
import argparse,csv,hashlib,json,os,platform,secrets,shutil,signal,subprocess,sys,time,zipfile
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from numerics import case,load_reference,sha,SOURCE_HASHES
from dependencies import choose,fit_models,predict,feature_width
from qualification import qualify

PACKAGE=Path(__file__).resolve().parent
def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def write(path,data):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');temp.replace(path)
def code_hashes():return {p.name:sha(p) for p in PACKAGE.iterdir() if p.suffix in ['.py','.json'] and p.name not in ['host-qualification.json','VALIDATION.json']}
def snapshot_package(destination):
    for f in PACKAGE.rglob('*'):
        if f.is_file() and '__pycache__' not in f.parts:
            target=destination/f.relative_to(PACKAGE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
def environment(repo):
    import scipy
    r=subprocess.run(['git','rev-parse','HEAD'],cwd=repo,capture_output=True,text=True,check=True)
    dirty=subprocess.run(['git','status','--porcelain','--untracked-files=no'],cwd=repo,capture_output=True,text=True,check=True)
    return {'source_commit':r.stdout.strip(),'tracked_worktree_status':dirty.stdout,'source_sha256':SOURCE_HASHES,'dependency_sha256':{n:sha(repo/n) for n in ['pyproject.toml','uv.lock']},'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform(),'machine':platform.machine(),'processor':platform.processor(),'cpu_count':os.cpu_count(),'thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},'package_sha256':code_hashes()}
def qualification_receipt(repo):
    result=qualify(repo);return {'recorded_at':stamp(),'environment':environment(repo),**result}
def params_for(block,level,cfg):
    p={'nodes':cfg['nodes'],'length':cfg['length'],'duration':cfg['baseline_duration'],'field':block['field'],'angle_degrees':0.,'rotation_code':None,'steps':48}
    if block['variable']=='dt':p['steps']=int(level);x=p['duration']/level
    elif block['variable']=='duration':p['steps']=int(level);p['duration']=level*cfg['fixed_dt'];x=p['duration']
    else:p['angle_degrees']=float(level);x=float(level)
    return p,float(x)

def run(repo,out,smoke=False):
    cfg=json.loads((PACKAGE/'PLAN.json').read_text())
    if smoke:cfg['nodes']=17;cfg['adaptive']['max_additions']=2;cfg['adaptive']['hopfion_max_additions']=2;cfg['late_time_dt_checks']=[480]
    identity=environment(repo);load_reference(repo)
    if not out.exists():out.mkdir(parents=True)
    (out/'cases').mkdir(exist_ok=True);(out/'fields').mkdir(exist_ok=True);(out/'blocks').mkdir(exist_ok=True)
    record_path=out/'record.json'
    if record_path.exists():
        old=json.loads(record_path.read_text())
        if old['environment']!=identity or old['config']!=cfg:raise ValueError('Resume identity/source/dependency/config mismatch; start a new run')
        record=old
    else:
        record={'recorded_at':stamp(),'status':'working','role':'smoke' if smoke else 'local-bounded-validation','environment':identity,'config':cfg,'blocks':[],'scope':cfg['scope'],'AI_assistance':'Code and analysis prepared with AI assistance; not independent scientific peer review.'};write(record_path,record)
    status={'recorded_at':stamp(),'status':'working','pid':os.getpid(),'output':str(out),'phase':'qualification','completed_cases':len(list((out/'cases').glob('*.json')))}
    def heartbeat(operation=None,step=None,total=None):
        status.update(recorded_at=stamp(),heartbeat=stamp(),wall_seconds=time.monotonic()-start)
        if operation is not None:
            if operation!=status.get('operation'):status['current_step']=0;status['total_steps']=operation.get('steps')
            status['operation']=operation
        if step is not None:status['current_step']=step;status['total_steps']=total
        write(out/'status.json',status)
    start=time.monotonic()
    def interrupted(sig,frame):raise KeyboardInterrupt('Signal '+str(sig))
    signal.signal(signal.SIGTERM,interrupted)
    heartbeat()
    try:
        qp=out/'qualification.json'
        if qp.exists():q=json.loads(qp.read_text())
        else:q=qualification_receipt(repo);write(qp,q)
        if q['status']!='qualification_passed' or q['environment']!=identity:raise ValueError('Local numerical qualification failed or changed')
        def measurement(params):
            key=hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()[:16];dest=out/'cases'/(key+'.json');field=out/'fields'/(key+'.npz')
            if dest.exists():
                r=json.loads(dest.read_text())
                if r['parameters']!=params:raise ValueError('Case key collision')
                if not smoke and (not field.exists() or sha(field)!=r['state']['sha256']):raise ValueError('Completed field state missing or changed')
                return key,r
            if len(list((out/'cases').glob('*.json')))>=cfg['max_case_count']:raise ValueError('Bounded case count exhausted')
            if not smoke and shutil.disk_usage(out).free<3*1024**3:raise ValueError('Less than 3 GiB free; preserved completed cases')
            operation={'case_id':key,**params};heartbeat(operation)
            print(json.dumps({'recorded_at':stamp(),'message':'START case',**operation}),flush=True)
            r=case(params,repo,field if not smoke else None,lambda i,n:heartbeat(operation,i,n));r['finished_at']=stamp();write(dest,r)
            status['completed_cases']=len(list((out/'cases').glob('*.json')));heartbeat(operation,params['steps'],params['steps'])
            print(json.dumps({'recorded_at':stamp(),'message':'FINISHED case','case_id':key,'sync_native_error':r['sync_native_error'],'wall_seconds':r['wall_seconds']}),flush=True)
            return key,r
        completed=[]
        for block in cfg['blocks']:
            status['phase']=block['id'];heartbeat();bp=out/'blocks'/block['id'];bp.mkdir(exist_ok=True)
            options={**cfg['adaptive'],'max_additions':cfg['adaptive']['hopfion_max_additions'] if block['field']=='hopfion' else cfg['adaptive']['max_additions']}
            rows=[];reserved=set(block['validation']);used=set(block['seed']);journal=[];successive=0;stop='budget_exhausted'
            def get(level,role):
                parameters,x=params_for(block,level,cfg);key,r=measurement(parameters)
                return {'level':level,'x':x,'y':r['sync_native_error'],'role':role,'case_id':key,'measured_at':r['finished_at']}
            for level in block['seed']:rows.append(get(level,'seed_development'))
            for round_index in range(options['max_additions']):
                candidates=[{'level':level,'x':params_for(block,level,cfg)[1]} for level in range(block['candidates'][0],block['candidates'][1]+1) if level not in used|reserved]
                selection=choose(rows,candidates,options)
                if selection is None:stop='candidate_space_exhausted';break
                selection={**selection,'round':round_index+1}
                selection_path=bp/f'selection-{round_index+1:02d}.json'
                if selection_path.exists():
                    previous=json.loads(selection_path.read_text())
                    if {k:v for k,v in previous.items() if k!='recorded_at'}!=selection:raise ValueError('Adaptive resume selection changed')
                    selection=previous
                else:selection={'recorded_at':stamp(),**selection};write(selection_path,selection)
                # Choice is sealed before the measurement; no validation access.
                journal.append(selection);row=get(selection['level'],'adaptive_development');rows.append(row);used.add(selection['level'])
                residual=abs(row['y']-selection['predicted_y']);primary=fit_models(rows)[0];width=feature_width(rows,primary,options)
                good=residual<=options['prediction_tolerance_fraction'] and width<=options['feature_bracket_fraction'];successive=successive+1 if good else 0
                write(bp/'development.json',{'rows':rows,'last_prediction_residual':residual,'largest_feature_bracket_fraction':width})
                if round_index+1>=options['min_additions'] and successive>=2:stop='refinement_tolerances_met';break
            frozen_path=bp/'frozen-fit.json';frozen={'models':fit_models(rows),'rows':rows,'stop_reason':stop,'adaptive_budget':options['max_additions']}
            if frozen_path.exists():
                previous=json.loads(frozen_path.read_text())
                if {k:v for k,v in previous.items() if k!='recorded_at'}!=frozen:raise ValueError('Frozen model mismatch on resume')
                frozen=previous
            else:frozen={'recorded_at':stamp(),**frozen};write(frozen_path,frozen)
            validation=[get(level,'validation') for level in block['validation']]
            for model in frozen['models']:
                residuals=np.array([float(predict(model,r['x']))-r['y'] for r in validation]);model['validation_rmse']=float(np.sqrt(np.mean(residuals**2)));model['validation_max_abs_error']=float(max(abs(residuals)))
            result={'id':block['id'],'variable':block['variable'],'field':block['field'],'development':rows,'validation':validation,'frozen_at':frozen['recorded_at'],'stop_reason':stop,'models':frozen['models'],'selection_journal':journal,'empirical_prediction_check':bool(frozen['models'][0]['validation_max_abs_error']<=cfg['adaptive']['validation_tolerance_fraction']),'operating_conditions':'not_selected: no accuracy budget declared','scope':'Primary model selected by development leave-one-out residual, frozen before block validation; validation does not select the winning model.'}
            write(bp/'result.json',result);completed.append(result);record['blocks']=completed;write(record_path,record)
        status['phase']='matched-controls';heartbeat()
        controls=[]
        for code in cfg['packet_cubic_rotation_controls']:
            p={'nodes':cfg['nodes'],'length':8.,'field':'packet','duration':1.,'steps':240,'angle_degrees':0.,'rotation_code':code};key,r=measurement(p);controls.append({'kind':'periodic_cubic_rotation','case_id':key,'rotation_code':code})
        for field_kind in ['hopfion','packet']:
            for steps in cfg['late_time_dt_checks']:
                p={'nodes':cfg['nodes'],'length':8.,'field':field_kind,'duration':1.,'steps':steps,'angle_degrees':0.,'rotation_code':None};key,r=measurement(p);controls.append({'kind':'late_time_dt_interaction_check','case_id':key,'field':field_kind,'steps':steps})
        # Packet comparison remains meaningful only if the exact-solution
        # Fourier control and periodic discrete invariants also hold.
        cases=[json.loads(f.read_text()) for f in sorted((out/'cases').glob('*.json'))]
        packet_checks=[{'case_id':f.stem,'fourier_exact_pass':r['fourier']['exact_error']<1e-10,'fourier_energy_pass':abs(r['fourier']['energy_relative_change'])<1e-10,'yee_modified_energy_pass':r['modified_energy_relative_drift']<1e-10,'yee_divergence_preservation_pass':r['max_discrete_divergence_change_normalized']<1e-10} for f in sorted((out/'cases').glob('*.json')) for r in [json.loads(f.read_text())] if r['parameters']['field']=='packet']
        record.update(status='complete_pending_review',finished_at=stamp(),controls=controls,packet_numerical_checks=packet_checks,all_packet_controls_pass=all(all(v for k,v in r.items() if k!='case_id') for r in packet_checks),completed_cases=len(cases));write(record_path,record)
        from render_report import render
        render(out)
        payload=out/'package';payload.mkdir(exist_ok=True)
        snapshot_package(payload)
        fields=[]
        for f in sorted((out/'fields').glob('*.npz')):
            with zipfile.ZipFile(f) as z:
                if z.testzip() is not None:raise ValueError('NPZ CRC failed: '+str(f))
            fields.append({'file':str(f.relative_to(out)),'sha256':sha(f),'bytes':f.stat().st_size})
        write(out/'field-manifest.json',{'recorded_at':stamp(),'files':fields,'scope':'Float64 local fields excluded from compact evidence; do not delete before a separately verified archive.'})
        status.update(status='complete_pending_review',phase='complete',finished_at=stamp(),evidence=str(out/'evidence.zip'),report=str(out/'REPORT.html'));heartbeat()
        files=[f for f in out.rglob('*') if f.is_file() and 'fields' not in f.relative_to(out).parts and f.name not in ['runner.log','evidence.zip'] and f!=out/'SHA256SUMS' and not f.name.endswith('.tmp')]
        (out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.relative_to(out).as_posix()+'\n' for f in sorted(files)))
        with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in files+[out/'SHA256SUMS']:z.write(f,f.relative_to(out).as_posix())
        print('Upload: '+str(out/'evidence.zip'),flush=True);print('Browser report: '+str(out/'REPORT.html'),flush=True)
    except BaseException as e:
        status.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'error',error=str(e));heartbeat();raise

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['run','qualify']);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args();repo=a.repo.expanduser().resolve();out=a.output.expanduser().resolve()
    if a.mode=='qualify':
        out.mkdir(parents=True,exist_ok=False);r=qualification_receipt(repo);write(out/'qualification.json',r);print(json.dumps(r));return 0 if r['status']=='qualification_passed' else 1
    run(repo,out,a.smoke);return 0
if __name__=='__main__':raise SystemExit(main())
