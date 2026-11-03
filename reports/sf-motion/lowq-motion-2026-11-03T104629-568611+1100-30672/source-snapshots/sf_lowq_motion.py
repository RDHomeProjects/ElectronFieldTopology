"""Checkpointed stationary low-Q readmission and bounded controlled motion campaign."""
import argparse
import fcntl
import json
from pathlib import Path
import signal
import sys
import time
import zipfile
import numpy as np
from .sf_checkpoints import atomic_json,timestamp
from .sf_dynamics_admission import sha
from .sf_readmission import relax
from .sf_time_run import run,canonical_sha,validate,initialize
from .sf_motion_metrics import evaluate,spatial_metrics
from .sf_time import Grid,densities


def plan_cases(config,seed_id,seed,checkpoint):
    q=seed['q'];size=seed['nodes'];length=seed['length'];cases=[]
    for beta,axis in [(0.,0)]+[(b,a) for b in config['betas'] for a in config['axes']]:
        gamma=1/np.sqrt(1-beta*beta)
        shape=[size]*3
        if beta:shape[axis]=2*int(np.ceil((size-1)*gamma/2))+1
        for dt in config['time_steps']:
            steps=round(config['duration']/dt)
            if abs(steps*dt-config['duration'])>1e-12:raise ValueError('Duration must be an integer number of each dt')
            name=f'{seed_id}-b{beta:g}-a{axis}-dt{dt:g}'
            initial={'kind':'boosted_lattice_checkpoint' if beta else 'lattice_checkpoint',
                     'path':str(Path(checkpoint).resolve()),'sha256':sha(checkpoint),'expected_q':q}
            if beta:initial.update(beta=beta,axis=axis)
            physical={'case_id':name,'grid':shape,'lengths':[length]*3,'boundary':'fixed','dt':dt,'steps':steps,
                      'diagnostic_every':config['diagnostic_every'],'checkpoint_every':config['checkpoint_every'],'initial':initial}
            validate(physical)
            assert length/(shape[axis]-1)<=length/(size-1)/gamma+1e-15
            cases.append({'id':name,'beta':beta,'axis':axis,'q':q,'seed_id':seed_id,'physical':physical})
    return cases


def merged_history(attempts):
    rows={}
    for attempt in attempts:
        for row in json.loads((Path(attempt)/'history.json').read_text()) if (Path(attempt)/'history.json').exists() else []:rows[row['step']]=row
    return [rows[i] for i in sorted(rows)]


def summarize(out,ledger):
    ledger['updated_at']=timestamp();atomic_json(out/'campaign.json',ledger)
    lines=['# Low-Q physical-time campaign','',f"UTC: {ledger['updated_at']['utc']}; Melbourne: {ledger['updated_at']['melbourne']}.",'',
           f"Status: **{ledger['status']}**. Completed cases: {len(ledger['cases'])}.",'',
           '| Rest candidate | Readmission | Relative force | Max acceleration | Hopf quadrature |',
           '|---|---|---:|---:|---:|']
    for name,r in ledger['seeds'].items():
        m=r['final'];lines.append(f"| {name} | {r['status']} | {m['relative_force_l2']:.4g} | {m['acceleration_max']:.4g} | {m['hopf_integral']:.6g} |")
    lines+=['','| Motion case | Status | Energy drift | Speed relative error | Shape error | Case gates |','|---|---|---:|---:|---:|---|']
    for name,row in ledger['cases'].items():
        m=row.get('assessment',{});lines.append(f"| {name} | {row['status']} | {m.get('max_energy_relative_drift','')} | {m.get('speed_relative_error','')} | {m.get('translated_static_field_relative_l2','')} | {m.get('bounded_case_gates_pass','')} |")
    lines+=['','Full fields/checkpoints and optional VTI/PVD previews remain local. Evidence.zip contains compact numerical records, not full fields.',
            'No isolated stability, high-Q motion, electromagnetic charge or electron acceptance follows from completion. Failed and skipped gates are retained.','']
    (out/'SUMMARY.md').write_text('\n'.join(lines))


def comparisons(out,ledger,config):
    complete={k:v for k,v in ledger['cases'].items() if v['status']=='complete'};rows=[]
    # Compare all pairs with one controlled change, at the same physical time.
    for ka,a in complete.items():
        for kb,b in complete.items():
            if ka>=kb or a['beta']!=b['beta'] or a['axis']!=b['axis'] or a['q']!=b['q']:continue
            pa=a['physical'];pb=b['physical'];sa=ledger['seed_configs'][a['seed_id']];sb=ledger['seed_configs'][b['seed_id']]
            kind=None
            if a['seed_id']==b['seed_id'] and pa['dt']!=pb['dt']:kind='temporal'
            elif pa['dt']==pb['dt'] and sa['length']==sb['length'] and sa['nodes']!=sb['nodes']:kind='spatial'
            elif pa['dt']==pb['dt'] and abs(sa['length']/(sa['nodes']-1)-sb['length']/(sb['nodes']-1))<1e-12 and sa['length']!=sb['length']:kind='domain'
            if not kind:continue
            ma=a['assessment'];mb=b['assessment'];ea=ma['final']['continuum_energy'];eb=mb['final']['continuum_energy']
            rows.append({'a':ka,'b':kb,'kind':kind,'energy_relative_difference':abs(ea-eb)/max(abs(ea),abs(eb)),
                'centroid_velocity_difference':float(np.linalg.norm(np.array(ma['fitted_centroid_velocity'])-mb['fitted_centroid_velocity'])),
                'shape_error_a':ma['translated_static_field_relative_l2'],'shape_error_b':mb['translated_static_field_relative_l2']})
    # Two h / dt levels measure differences, not a convergence order. No automatic
    # global scientific acceptance from case flags or a single shrinking number.
    return {'recorded_at':timestamp(),'pairs':rows,'global_motion_acceptance':'scientific_review_required',
            'scope':'Controlled differences, not an inferred order or full stability proof; review source rest-state differences and finite-box effects.'}


def evidence(out):
    included=[]
    for p in sorted(out.rglob('*')):
        if not p.is_file() or any(x in ('preview','evidence.zip') for x in p.relative_to(out).parts):continue
        if p.suffix in ('.json','.md') and p.name!='evidence-hashes.json':included.append(p)
    hashes={str(p.relative_to(out)):sha(p) for p in included}
    atomic_json(out/'evidence-hashes.json',{'recorded_at':timestamp(),'sha256':hashes})
    with zipfile.ZipFile(out/'evidence.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in included+[out/'evidence-hashes.json']:z.write(p,str(p.relative_to(out)))


def campaign(config,out,profile=None,preparation_pass_limit=None):
    validate_campaign(config);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    lock=(out/'.campaign.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('This campaign is already running')
    digest=canonical_sha(config)
    files=['sf_lowq_motion.py','sf_readmission.py','sf_motion_metrics.py','sf_time.py','sf_time_run.py','sf_time_initial.py','sf_dynamics.py','skyrme.py']
    source={n:sha(Path(__file__).with_name(n)) for n in files}
    if (out/'campaign.json').exists():
        ledger=json.loads((out/'campaign.json').read_text())
        if ledger['config_sha256']!=digest or ledger['source_sha256']!=source:raise ValueError('Campaign source/config differs; preserve this run and use a new output')
    else:ledger={'started_at':timestamp(),'config_sha256':digest,'source_sha256':source,'seeds':{},'seed_configs':{},'cases':{}}
    ledger['status']='working';atomic_json(out/'plan.json',config);summarize(out,ledger)
    try:
        for seed in config['seeds']:
            sid=f"q{seed['q']}-n{seed['nodes']}-L{seed['length']:g}";seedout=out/'readmission'/sid
            full={**config['readmission'],**seed};ledger['seed_configs'][sid]=seed
            if ledger['seeds'].get(sid,{}).get('status') not in ('stationary','topology_unresolved','stationarity_unresolved'):
                ledger['seeds'][sid]=relax(full,seedout,preparation_pass_limit);summarize(out,ledger)
            admitted=ledger['seeds'][sid]['status']=='stationary'
            if ledger['seeds'][sid]['status']=='interrupted':raise KeyboardInterrupt
            if ledger['seeds'][sid]['status']=='checkpointed':ledger['status']='checkpointed';summarize(out,ledger);return ledger
            checkpoint=seedout/'latest.npz'
            if sha(checkpoint)!=ledger['seeds'][sid]['field_sha256']:raise ValueError('Readmission checkpoint changed after assessment')
            with np.load(checkpoint,allow_pickle=False) as data:rest=data['field'].copy();h=float(data['h'])
            for case in plan_cases(config,sid,seed,checkpoint):
                name=case['id'];dest=out/'cases'/name;dest.mkdir(parents=True,exist_ok=True)
                if case['beta'] and not admitted:
                    ledger['cases'][name]={**case,'status':'skipped_unadmitted_rest'};summarize(out,ledger);continue
                prior=ledger['cases'].get(name,{})
                if prior.get('status')=='complete':
                    if sha(Path(prior['attempts'][-1])/'final.npz')!=prior['final_checkpoint_sha256']:raise ValueError('Completed motion checkpoint changed')
                    continue
                attempts=prior.get('attempts',[]);resume=None
                if attempts and (Path(attempts[-1])/'latest.npz').exists():resume=Path(attempts[-1])/'latest.npz'
                attempt=dest/f'attempt-{len(attempts)+1:03d}';attempts.append(str(attempt))
                ledger['cases'][name]={**case,'status':'working','attempts':attempts};summarize(out,ledger)
                physical=case['physical'];grid=validate(physical);ni,vi,_=initialize(physical,grid)
                initial=spatial_metrics(ni,vi,grid,config['boundary_shell_width'])
                rest_grid=Grid(rest.shape[:3],(h*(len(rest)-1),)*3,'fixed')
                rest_data=densities(rest,np.zeros_like(rest),rest_grid)
                rest_energy=float(np.sum(rest_data['energy_density'])*h**3)
                stress=np.sum(rest_data['stress'],axis=(0,1,2))*h**3
                beta=case['beta'];axis=case['axis'];gamma=1/np.sqrt(1-beta*beta)
                tensor_p=beta*stress[axis,:].copy();tensor_p[axis]=gamma*beta*(rest_energy+stress[axis,axis])
                initial.update(rest_continuum_energy=rest_energy,rest_integrated_stress=stress.tolist(),
                    finite_box_tensor_energy=gamma*(rest_energy+beta*beta*stress[axis,axis]),
                    finite_box_tensor_momentum=tensor_p.tolist())
                result=run(physical,attempt,profile,resume=resume)
                ledger['cases'][name].update(status=result['status'],result=result,initial=initial)
                if result['status']!='complete':summarize(out,ledger);raise KeyboardInterrupt
                history=merged_history(attempts)
                with np.load(attempt/'final.npz',allow_pickle=False) as data:n=data['field'].copy();v=data['field_rate'].copy()
                assessment=evaluate(history,n,v,grid,rest,h,case['beta'],case['axis'],case['q'],config['boundary_shell_width'],config['limits'])
                assessment['rest_admitted']=admitted
                initial_history=history[0];particle_p=np.zeros(3);particle_p[axis]=gamma*beta*rest_energy
                particle_e=abs(initial_history['continuum_energy']/(gamma*rest_energy)-1)
                particle_m=float(np.linalg.norm(np.array(initial_history['momentum'])-particle_p)/(gamma*rest_energy))
                assessment.update(initial_particle_energy_relative_defect=particle_e,initial_particle_momentum_scaled_defect=particle_m,
                    initial_tensor_energy_relative_defect=abs(initial_history['continuum_energy']/initial['finite_box_tensor_energy']-1),
                    initial_tensor_momentum_scaled_defect=float(np.linalg.norm(np.array(initial_history['momentum'])-tensor_p)/(gamma*rest_energy)))
                assessment['checks']['initial_particle_relations']=bool(max(particle_e,particle_m)<=config['limits']['particle_relative'])
                assessment['initial_light_cone_margin_after_observation']=initial['initial_light_cone_clearance']-config['duration']
                assessment['checks']['initial_boundary_clearance']=assessment['initial_light_cone_margin_after_observation']>0
                assessment['bounded_case_gates_pass']=all(assessment['checks'].values()) and admitted
                atomic_json(dest/'history-combined.json',history);atomic_json(dest/'assessment.json',{'assessed_at':timestamp(),**assessment})
                ledger['cases'][name].update(assessment=assessment,final_checkpoint_sha256=sha(attempt/'final.npz'))
                summarize(out,ledger)
        ledger['status']='complete_pending_review'
    except KeyboardInterrupt:ledger['status']='stopped_checkpoint_retained'
    except Exception as error:
        ledger['status']='error';ledger['error']=str(error);summarize(out,ledger);evidence(out);raise
    atomic_json(out/'comparisons.json',comparisons(out,ledger,config));summarize(out,ledger);evidence(out)
    return ledger


def validate_campaign(c):
    if c.get('format')!='EFT-lowq-motion-v1' or not c['seeds']:raise ValueError('Explicit versioned campaign required')
    if (len(set(c['time_steps']))<2 or any(not np.isfinite(x) or x<=0 for x in c['time_steps'])
            or not np.isfinite(c['duration']) or c['duration']<=0
            or any(not np.isfinite(x) or not 0<x<=.3 for x in c['betas'])
            or any(type(a) is not int or a not in (0,1,2) for a in c['axes'])):raise ValueError('Declared low-speed/time controls required')
    ids=[]
    for s in c['seeds']:
        if (s['q'] not in (1,2) or type(s['nodes']) is not int or s['nodes']<9 or s['nodes']%2!=1
                or not np.isfinite(s['length']) or s['length']<=0 or not 0<s['seed_cutoff']<s['length']/2
                or not np.isfinite(s['seed_scale']) or s['seed_scale']<=0):raise ValueError('Invalid self-contained Q1/Q2 seed')
        ids.append((s['q'],s['nodes'],s['length']))
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate rest candidates')
    for key in ['relative_force_l2','acceleration_max','charge_relative_error','stagnation_relative_energy']:
        if not np.isfinite(c['readmission'][key]) or c['readmission'][key]<=0:raise ValueError('Positive readmission thresholds required')
    for key in ['iterations_per_pass','checkpoint_every']:
        if type(c['readmission'][key]) is not int or c['readmission'][key]<1:raise ValueError('Positive optimization batch/checkpoint intervals required')
    for key in ['diagnostic_every','checkpoint_every']:
        if type(c[key]) is not int or c[key]<1:raise ValueError('Positive physical diagnostic/checkpoint intervals required')
    if not 0<c['boundary_shell_width']<min(s['length'] for s in c['seeds'])/2:raise ValueError('Invalid boundary shell')
    for x in c['limits'].values():
        if not np.isfinite(x) or x<=0:raise ValueError('Positive physical diagnostic limits required')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',type=Path)
    a=p.parse_args();signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
    config=json.loads(a.config.read_text());profile=json.loads(a.profile.read_text()) if a.profile else None
    result=campaign(config,a.output,profile);print(json.dumps({'recorded_at':timestamp(),'status':result['status'],'output':str(a.output)},indent=2),flush=True)
    return 0 if result['status']=='complete_pending_review' else 2


if __name__=='__main__':sys.exit(main())
