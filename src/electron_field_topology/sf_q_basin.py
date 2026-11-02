"""Resumable Q18 basin and Q17/Q19 comparison; static fields, not physical time.

Jennings 1412.8597v2 Eqs.2.1,2.4,2.7 and Table 1; ADR-0008.
No overall wall-time cap. Each pass retains an independently audited endpoint.
Apache-2.0. See docs/plans/q18-neighbour-run.md for controls and limits.
"""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import zipfile

import numpy as np
from .sf_checkpoints import atomic_json, load_field, sha, timestamp
from .sf_campaign import basic_gates, analysis_signature
from .sf_q22_closure import endpoint, eligible, stalled, compare_energy, stamp_case, code_hashes
from .sf_relax import validate

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT/'experiments/configs/sf-j2015'
PLAN = CONFIGS/'q18-neighbours.json'
TERMINAL = {'stationary','stationary_scalar_failure','stalled','numerical_fault','audit_incomplete','dependency_unresolved','control_failure'}


def read(path): return json.loads(Path(path).read_text())


def announce(*parts):
    print(json.dumps({'recorded_at':timestamp(),'message':' '.join(str(p) for p in parts)}),flush=True)


def stream_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def published_checkpoints():
    """Read committed manifests, including small evidence archives; no fields extracted."""
    result={}
    def add(m,r,source):
        try:
            c=r['config']; gates=basic_gates(r)
            if (c['expected_q'] not in (18,22) or not m.get('source_unchanged_during_run')
                    or not m.get('device_validation',{}).get('passed')
                    or not all(gates[k] for k in ('initial_charge','final_charge','resolved_cells','unit_norm','endpoint_cpu_audit'))): return
            digest=m['artifacts_sha256']['final.npz']
            result[digest]={'config':c,'final':r['final'],'stationary':eligible(r),'record':source}
        except (KeyError,TypeError,ValueError): return
    for p in sorted((ROOT/'reports/s5-a').rglob('manifest.json')):
        if (p.parent/'result.json').is_file(): add(read(p),read(p.parent/'result.json'),str(p.relative_to(ROOT)))
    for p in sorted((ROOT/'reports/s5-a').rglob('evidence.zip')):
        with zipfile.ZipFile(p) as z:
            names=set(z.namelist())
            for name in sorted(names):
                if not name.endswith('/manifest.json'): continue
                other=name[:-len('manifest.json')]+'result.json'
                if other in names:
                    add(json.loads(z.read(name)),json.loads(z.read(other)),str(p.relative_to(ROOT))+':'+name)
    return result


def inventory(roots):
    known=published_checkpoints(); recognized=[]; unknown=[]; seen=set()
    for root in roots:
        root=Path(root).expanduser().resolve()
        if not root.is_dir(): continue
        for path in sorted(root.rglob('final.npz')):
            if not any(label in str(path).lower() for label in ('q18','q22')): continue
            path=path.resolve()
            if path in seen: continue
            seen.add(path); announce('INVENTORY',path)
            digest=stream_sha(path)
            if digest in known:
                recognized.append({'path':str(path),'sha256':digest,**known[digest]})
            else: unknown.append({'path':str(path),'sha256':digest,'disposition':'not matched to a committed endpoint; not reused'})
    return {'recorded_at':timestamp(),'roots':[str(Path(p).expanduser().resolve()) for p in roots],
            'verified_fields':recognized,'unmatched_fields':unknown,
            'historical_q18':'available' if any(x['config']['expected_q']==18 for x in recognized) else 'no verified field found; fresh reconstruction',
            'scope':'exact committed checkpoint hashes; missing fields are not fabricated; original files remain in place'}


def prepare_config(stage,checkpoint=None,plan=None):
    plan=read(PLAN) if plan is None else plan
    c=copy.deepcopy(stage['template'])
    c.pop('initial_checkpoint',None)
    c.update(case=stage['id'],n=stage['n'],h=stage['h'],iterations=plan['pass_iterations'],
             seconds=plan['pass_seconds'],record_every=25,precondition_length=stage['length'],prepared_at=timestamp(),
             initialization='fresh_seed' if checkpoint is None else 'checkpoint_continuation')
    if checkpoint is not None: c['initial_checkpoint']=str(Path(checkpoint).resolve())
    validate(c)
    return c


def build_plan(receipt):
    plan=read(PLAN); stages=[]
    if plan['overall_wall_seconds'] is not None: raise ValueError('No overall time cap is permitted')
    for q in (1,2):
        c=read(CONFIGS/f'q{q}-65.json')
        stages.append({'id':f'q{q}-control','branch':f'q{q}-control','role':'control','q':q,'n':65,'h':.24,'length':.5,'template':c})
    c=read(CONFIGS/'q22-129.json')
    control={'id':'q22-control','branch':'q22-control','role':'control','q':22,'n':129,'h':.12,'length':.5,'template':c}
    matching=[x for x in receipt['verified_fields'] if x['config']['expected_q']==22 and x['stationary']
              and x['config']['n']==129 and abs(x['config']['h']-.12)<1e-12 and x['config'].get('seed',{}).get('kind')=='cable']
    if matching:
        item=sorted(matching,key=lambda x:x['sha256'])[0]
        control.update(checkpoint=item['path'],checkpoint_sha256=item['sha256'],template=item['config'])
    stages.append(control)
    # All coarse screens precede expensive refinements. Each branch changes one input.
    for branch in plan['branches']:
        q=branch['q']; c=read(CONFIGS/'q18-97.json'); c['expected_q']=q
        c.pop('published_energy',None)
        c['source_comparison_energy']=plan['source_energies'][str(q)]
        c['seed'].update(alpha={17:5,18:2,19:6}[q],beta={17:1,18:2,19:1}[q],scale=branch['scale'])
        n=97 if q==18 else 129
        stages.append({'id':branch['id']+f'-{n}','branch':branch['id'],'role':'screen','q':q,'n':n,'h':15.36/(n-1),
                       'length':branch['length'],'template':c,'changed_input':branch['changed_input']})
    for branch in plan['branches']:
        q=branch['q']; first=next(s for s in stages if s['branch']==branch['id'])
        prior=first['id']
        for n in ([129,161,193] if q==18 else [161,193]):
            stage={**first,'id':branch['id']+f'-{n}','role':'refinement','n':n,'h':15.36/(n-1),'from':prior}
            stages.append(stage); prior=stage['id']
        stages.append({**first,'id':branch['id']+'-domain','role':'domain','n':193,'h':.096,'from':branch['id']+'-161'})
    # A historical Q18 field is a separate outcome, never substituted for a fresh seed.
    matches=[x for x in receipt['verified_fields'] if x['config']['expected_q']==18 and x['stationary']]
    if matches:
        item=max(matches,key=lambda x:x['config']['n']); c=item['config']
        stages.append({'id':'q18-retained-audit','branch':'q18-retained','role':'retained','q':18,'n':c['n'],'h':c['h'],
                       'length':.5,'template':c,'checkpoint':item['path'],'checkpoint_sha256':item['sha256']})
    plan['stages']=stages
    for stage in stages: prepare_config(stage,plan=plan)
    return plan


def clean_commit():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('Commit the run tooling before computation; keep the run checkout unchanged')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def execute(argv,log,seconds):
    """Timestamped logs, soft SIGINT at a pass deadline, time for endpoint audits."""
    with Path(log).open('w') as f:
        f.write(json.dumps({'started_at':timestamp(),'argv':argv})+'\n'); f.flush()
        p=subprocess.Popen(argv,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+seconds
            while p.poll() is None:
                if time.monotonic()>=deadline:
                    p.send_signal(signal.SIGINT)
                    try:p.wait(timeout=300)
                    except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=30)
                    status='timeout';break
                try:p.wait(timeout=min(30,max(.1,deadline-time.monotonic())))
                except subprocess.TimeoutExpired:announce('WORKING',Path(log).stem)
            else: status='completed' if p.returncode==0 else 'failed'
        except KeyboardInterrupt:
            p.send_signal(signal.SIGINT)
            try:p.wait(timeout=300)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=30)
            raise
        finally:
            f.write(json.dumps({'finished_at':timestamp(),'returncode':p.poll()})+'\n')
    return {'status':status,'returncode':p.returncode}


def recover_field(case,stage,config_sha):
    """Prefer an audited final; rolling fields need a new independent initial audit."""
    case=Path(case)
    try:
        r=endpoint(case)
        if (r['config']['expected_q']!=stage['q'] or r['config']['n']!=stage['n']
                or abs(r['config']['h']-stage['h'])>1e-12 or sha(case/'config.json')!=config_sha):
            raise ValueError('Audited endpoint geometry/configuration mismatch')
        return case/'final.npz',{'kind':'audited_endpoint','result_status':r['status']}
    except (ValueError,OSError,KeyError): pass
    errors=[]
    for name in ('latest.npz','previous.npz'):
        path=case/name
        try:
            with np.load(path,allow_pickle=False) as d:
                if (d['field'].dtype!=np.float64 or str(d['model_id'])!='SF-J2015-static'
                        or float(d['expected_q'])!=stage['q'] or str(d['config_sha256'])!=config_sha
                        or d['field'].shape!=(stage['n'],stage['n'],stage['n'],3)
                        or abs(float(d['h'])-stage['h'])>1e-12):
                    raise ValueError('Rolling checkpoint provenance/geometry mismatch')
            load_field(path,stage['n'],stage['h'],stage['q'])
            return path,{'kind':'rolling_recovery','sha256':stream_sha(path),'requires_new_initial_cpu_gpu_audit':True,'rejected_candidates':errors}
        except (ValueError,OSError,KeyError,EOFError,zipfile.BadZipFile) as e:errors.append(name+': '+str(e))
    raise ValueError('No recoverable endpoint/rolling field: '+'; '.join(errors))


def analyse(out,state,plan,stage,executor):
    job=state['stages'][stage['id']]
    if not job.get('directory'):return
    case=out/job['directory']; folder=out/'analysis'/case.name
    if not (case/'final.npz').is_file():return
    tasks=[('topology',[sys.executable,'scripts/analyse_static_fields.py','--case',str(case),'--output',str(folder),'--phases',
                         *(['initial','final'] if stage['role']=='screen' else ['final'])]),
           ('links',[sys.executable,'-m','electron_field_topology.sf_q_basin','--curve-audit',str(folder)]),
           ('scaling',[sys.executable,'scripts/check_static_scaling.py','--checkpoint',str(case/'final.npz'),'--output',str(folder)])]
    if stage['q'] in (1,2):tasks=tasks[-1:]
    for name,argv in tasks:
        key=case.name+'-'+name; signature=analysis_signature(argv)
        if name=='links':
            inputs={p.name:sha(p) for p in folder.glob('*') if p.suffix=='.npz' or p.name=='topology.json'}
            signature=hashlib.sha256(json.dumps([signature,inputs],sort_keys=True).encode()).hexdigest()
        old=state['analysis'].get(key,{})
        if old.get('status')=='completed' and old.get('signature')==signature:continue
        if code_hashes()!=state['code_sha256']:raise ValueError('Source changed during analysis')
        folder.mkdir(parents=True,exist_ok=True)
        started=timestamp(); log=out/'logs'/(key+'-'+str(time.time_ns())+'.log')
        state['analysis'][key]={'status':'running','signature':signature,'started_at':started}
        atomic_json(out/'campaign.json',state)

        before={p:sha(p) for p in folder.glob('*.json')}
        try:result=executor(argv,log,plan['analysis_job_seconds'])
        except KeyboardInterrupt:
            state['analysis'][key].update(status='interrupted',finished_at=timestamp());raise
        finally:
            for p in folder.glob('*.json'):
                if before.get(p)==sha(p):continue
                data=read(p)
                if isinstance(data,dict):
                    data['record_timestamps']={'started_at':started,'finished_at':timestamp()};atomic_json(p,data)
        state['analysis'][key]={**result,'signature':signature,'started_at':started,'finished_at':timestamp(),'log':str(log.relative_to(out))}
        atomic_json(out/'campaign.json',state)


def audit_curve_links(folder):
    """Independent Gauss integrals on retained curves; report unresolved geometry."""
    from .linking import gauss_link
    from .sf_topology import resample
    folder=Path(folder);top=read(folder/'topology.json');output={}
    for phase,data in top.get('phases',{}).items():
        for target,entry in data.get('targets',{}).items():
            path=folder/f'{phase}-{target}-curves.npz'
            if not path.is_file():continue
            with np.load(path,allow_pickle=False) as z:
                curves=[z[k] for k in sorted(z.files,key=lambda k:int(k.split('_')[-1]))]
            pairs=[]
            for i in range(len(curves)):
                for j in range(i+1,len(curves)):
                    samples=[]
                    diagram=next((x for x in entry.get('pairwise_link_checks',[]) if x['first']==i and x['second']==j),{})
                    values=[x['linking_number'] for x in diagram.get('observations',[]) if 'linking_number' in x]
                    reference=values[0] if len(values)==6 and len(set(values))==1 else None
                    for count in (256,384,512):
                        try:
                            result=gauss_link(resample(curves[i],count),resample(curves[j],count))
                            samples.append({'segments':count,**result})
                        except ValueError as e:samples.append({'segments':count,'status':'unresolved','reason':str(e)})
                    pairs.append({'first':i,'second':j,'signed_diagram_link':reference,'gauss_samples':samples,
                                  'absolute_differences':[abs(x['linking_integral']-reference) for x in samples if reference is not None and 'linking_integral' in x]})
            output[phase+'-'+target]={'checkpoint_sha256':data['checkpoint_sha256'],'curves_sha256':sha(path),'components':len(curves),'pairs':pairs}
    report={'recorded_at':timestamp(),'targets':output,'scope':'independent Gauss quadrature on finite curves; no continuum isotopy or unique knot certificate'}
    atomic_json(folder/'independent-links.json',report)
    announce('Independent finite-curve Gauss audit',folder)
    return report


def collect(out,state=None):
    out=Path(out); state=read(out/'campaign.json') if state is None else state
    plan=read(out/'plan.json'); rows={}; results={}; comparisons={}
    for stage in plan['stages']:
        key=stage['id'];job=state['stages'].get(key,{'status':'not_started'})
        row={'execution':job['status'],'q':stage['q'],'role':stage['role'],'n':stage['n'],'h':stage['h'],'branch':stage['branch']}
        if job.get('directory'):
            case=out/job['directory']
            try:
                r=endpoint(case);results[key]=r
                row.update(final=r['final'],gates=basic_gates(r),solver_status=r['status'],checkpoint_sha256=sha(case/'final.npz'))
                row['energy_per_Q_three_quarters']=r['final']['energy']/stage['q']**.75
                source=plan['source_energies'].get(str(stage['q']))
                if source:row['source_energy_relative_difference']=abs(r['final']['energy']-source)/source
                folder=out/'analysis'/case.name
                if (folder/'topology.json').exists():
                    top=read(folder/'topology.json').get('phases',{}).get('final',{})
                    if top.get('checkpoint_sha256')==row['checkpoint_sha256']:
                        row['preimage_components']={k:v.get('components') for k,v in top.get('targets',{}).items()}
                        row['topology_scope']='finite diagrams; identity and cross-mesh consistency require scientific review'
                if (folder/'scaling.json').exists():
                    sc=read(folder/'scaling.json')
                    row['scaling_gate']=(sc.get('checkpoint_sha256')==row['checkpoint_sha256'] and bool(sc.get('finite_difference_comparisons'))
                        and all(abs(x['normalized_energy_derivative'])<.05 and abs(x['difference_from_e2_minus_e4'])<.05 for x in sc['finite_difference_comparisons']))
            except (ValueError,OSError,KeyError) as e:row['audit_unresolved']=str(e)
        rows[key]=row
    for branch in plan['branches']:
        b=branch['id']
        for a,z,kind in [(b+'-129',b+'-161','mesh'),(b+'-161',b+'-193','mesh'),(b+'-161',b+'-domain','domain')]:
            comparisons[a+'__'+z]=compare_energy(results[a],results[z],kind) if a in results and z in results else {'status':'unresolved'}
        if branch['q']==18 and b!='q18-baseline':
            a,z='q18-baseline-193',b+'-193'
            comparisons[a+'__'+z]=compare_energy(results[a],results[z],'ranking') if a in results and z in results else {'status':'unresolved'}
    solver_wall=sum(a.get('wall_seconds',0) for j in state['stages'].values() for a in j.get('attempts',[]))
    summary={'generated_at':timestamp(),'started_at':state['started_at'],'git_commit':state['git_commit'],
             'stages':rows,'comparisons':comparisons,'analysis':state['analysis'],'solver_wall_seconds':solver_wall,
             'overall_wall_seconds_cap':None,'disposition':'partial_pending_scientific_review',
             'scope':'static neutral unit-vector model; linked outcomes retained; no automatic reproduction, dynamics, electric charge or electron acceptance',
             'fields_location':str(out.resolve()),'historical_inputs':state['inventory'],
             'source_unchanged':state['code_sha256']==code_hashes()}
    atomic_json(out/'summary.json',summary)
    lines=['# Q18 basin and neighbouring-Q study','',json.dumps(summary['generated_at']), '', summary['scope'], '',
           '| Stage | State | Energy | CPU residual |','|---|---|---:|---:|']
    for key,row in rows.items():
        f=row.get('final',{});lines.append(f"| {key} | {row['execution']} | {f.get('energy','')} | {f.get('cpu_tangent_gradient_rms','')} |")
    lines+=['','Mesh/domain entries are energy-only diagnostics; topology consistency and independent scaling need separate review.',
            'Full float64 fields stay in this campaign. Keep the entire directory for restart and later topology assessment.']
    (out/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    files=[p for p in out.rglob('*') if p.is_file() and p.name!='evidence-hashes.json' and
           (p.suffix in ('.json','.md','.log','.svg') or (p.suffix=='.npz' and p.relative_to(out).parts[0]=='analysis'))]
    hashes={'generated_at':timestamp(),'files':{str(p.relative_to(out)):{'sha256':stream_sha(p),'modified_at':timestamp_from_mtime(p)} for p in files}}
    atomic_json(out/'evidence-hashes.json',hashes)
    with zipfile.ZipFile(out/'evidence.zip.tmp','w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[out/'evidence-hashes.json']:z.write(p,p.relative_to(out))
    os.replace(out/'evidence.zip.tmp',out/'evidence.zip')
    return summary


def timestamp_from_mtime(path):
    from datetime import datetime,timezone
    from zoneinfo import ZoneInfo
    t=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)
    return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}


def run(output,roots=(),resume=False,_executor=None):
    executor=execute if _executor is None else _executor
    out=Path(output).expanduser().resolve(); commit=clean_commit()
    if not resume:out.mkdir(parents=True,exist_ok=False)
    if not (out/'campaign.json').exists() and resume:raise ValueError('No existing campaign to resume')
    with (out/'run.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('This campaign is already running') from None
        if resume:
            state=read(out/'campaign.json');plan=read(out/'plan.json')
            if state['git_commit']!=commit or state['code_sha256']!=code_hashes() or state['plan_sha256']!=sha(out/'plan.json'):
                raise ValueError('Code, commit or frozen plan changed; use the original run checkout')
        else:
            for folder in ('cases','configs','analysis','logs'):(out/folder).mkdir()
            receipt=inventory(roots);plan=build_plan(receipt)
            for item in receipt['verified_fields']:
                if out.is_relative_to(Path(item['path']).parent):raise ValueError('Separate output from historical fields')
            atomic_json(out/'plan.json',plan)
            state={'started_at':timestamp(),'git_commit':commit,'code_sha256':code_hashes(),'plan_sha256':sha(out/'plan.json'),
                   'inventory':receipt,'stages':{},'analysis':{},'overall_wall_seconds':None}
        def save():
            state['updated_at']=timestamp();atomic_json(out/'campaign.json',state)
        save();collect(out,state)
        try:
            state.pop('interrupted',None)
            for stage in plan['stages']:
                key=stage['id'];job=state['stages'].setdefault(key,{'status':'not_started','attempts':[],'progress':[]})
                if stage['q']>2:
                    controls=['q1-control','q2-control']+(['q22-control'] if stage['q']!=22 else [])
                    if any(state['stages'].get(k,{}).get('status')!='stationary' for k in controls):
                        job.update(status='control_failure');save();continue
                if job['status'] in TERMINAL:
                    if job.get('directory'):analyse(out,state,plan,stage,executor)
                    continue
                checkpoint=None
                if stage.get('from'):
                    dep=state['stages'].get(stage['from'],{})
                    try:
                        parent=out/dep['directory'];endpoint(parent);checkpoint=parent/'final.npz'
                    except (KeyError,OSError,ValueError):
                        job['status']='dependency_unresolved';save();continue
                elif stage.get('checkpoint'):
                    checkpoint=Path(stage['checkpoint'])
                    if stream_sha(checkpoint)!=stage['checkpoint_sha256']:raise ValueError('Historical checkpoint changed')
                if job.get('directory'):
                    try:
                        checkpoint,recovery=recover_field(out/job['directory'],stage,job['config_sha256'])
                        job['recovery']={**recovery,'recorded_at':timestamp()}
                    except (OSError,ValueError) as e:
                        job.update(status='audit_incomplete',reason=str(e));save();continue
                while True:
                    if code_hashes()!=state['code_sha256']:raise ValueError('Source changed during the study')
                    if shutil.disk_usage(out).free < 12*stage['n']**3*3*8:
                        job['status']='disk_space_pause';state['interrupted']=True;save();return state
                    index=len(job['attempts'])+1;name=f'{key}-pass{index:04d}'
                    case=out/'cases'/name;config=out/'configs'/(name+'.json')
                    c=prepare_config(stage,checkpoint,plan);atomic_json(config,c)
                    attempt={'directory':str(case.relative_to(out)),'config_sha256':sha(config),'status':'running','started_at':timestamp(),
                             'input_sha256':stream_sha(checkpoint) if checkpoint else None,'initialization':c['initialization']}
                    job['attempts'].append(attempt);job.update(attempt);save()
                    announce('RUN',name,'n',stage['n'],'q',stage['q'],'ell',stage['length'],'no overall time cap')
                    argv=[sys.executable,'-m','electron_field_topology.sf_relax','--backend','gpu','--config',str(config),'--output',str(case)]
                    began=time.monotonic()
                    try:outcome=executor(argv,out/'logs'/(name+'.log'),plan['pass_seconds']+plan['audit_grace_seconds'])
                    except KeyboardInterrupt:
                        attempt.update(status='interrupted',finished_at=timestamp(),wall_seconds=time.monotonic()-began)
                        job['status']='interrupted';state['interrupted']=True;save();raise
                    attempt.update(outcome,finished_at=timestamp(),wall_seconds=time.monotonic()-began)
                    if case.exists():stamp_case(case,attempt['started_at'],attempt['finished_at'])
                    try:r=endpoint(case)
                    except (ValueError,OSError,KeyError) as e:
                        job.update(status='audit_incomplete',reason=str(e));save();break
                    checkpoint=case/'final.npz';f=r['final'];job['progress'].append({'energy':f['energy'],'residual':f['cpu_tangent_gradient_rms']})
                    attempt.update(solver_status=r['status'],energy=f['energy'],residual=f['cpu_tangent_gradient_rms'])
                    if r['status']=='interrupted' or outcome['status']=='timeout':
                        job['status']='interrupted';state['interrupted']=True;save();break
                    if outcome['status']!='completed':job['status']='numerical_fault'
                    elif f['cpu_tangent_gradient_rms']<1e-3:
                        passed=eligible(r) and (stage['role']!='control' or all(basic_gates(r).values()))
                        job['status']='stationary' if passed else 'stationary_scalar_failure'
                    elif stalled(job['progress'],plan):job['status']='stalled'
                    else:job['status']='running'
                    save();collect(out,state)
                    if job['status']!='running':break
                if job.get('directory'):analyse(out,state,plan,stage,executor)
                save();collect(out,state)
                if state.get('interrupted'):break
        except KeyboardInterrupt:
            state['interrupted']=True
            announce('Interrupted; accepted rolling fields retained. Rerun with --resume.')
        except Exception as e:
            state['error']={'recorded_at':timestamp(),'type':type(e).__name__,'message':str(e)};raise
        finally:
            save();collect(out,state);announce('SUMMARY',out/'SUMMARY.md','EVIDENCE',out/'evidence.zip')
    return state


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path)
    p.add_argument('--search-root',type=Path,action='append',default=[])
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--preflight',action='store_true')
    mode.add_argument('--collect',action='store_true')
    mode.add_argument('--resume',action='store_true')
    mode.add_argument('--curve-audit',type=Path)
    a=p.parse_args()
    if a.curve_audit:audit_curve_links(a.curve_audit);return
    if a.preflight:
        receipt=inventory(a.search_root);plan=build_plan(receipt)
        print(json.dumps({'recorded_at':timestamp(),'inventory':receipt,'planned_stages':len(plan['stages']),
                          'overall_wall_seconds':None,'branches':plan['branches']},indent=2));return
    if not a.output:p.error('--output is required')
    if a.collect:
        with (a.output/'run.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:p.error('Study is running; use the current evidence snapshot')
            collect(a.output)
        return
    state=run(a.output,a.search_root,a.resume)
    if state and state.get('interrupted'):raise SystemExit(130)
    if state and any(j['status'] in ('numerical_fault','audit_incomplete','control_failure') for j in state['stages'].values()):raise SystemExit(2)


if __name__=='__main__':main()
