"""Audit PR50 retained records and finite curves; full fields remain local.

Apache-2.0. Source equations: Jennings 1412.8597v2; no new solver or GPU run.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
import random
import subprocess
import zipfile

import numpy as np
from electron_field_topology.sf_checkpoints import timestamp
from electron_field_topology.sf_topology import canonical_gauss, jones_a, resample, cable_reference, diagram_analysis
from electron_field_topology.linking import gauss_link, closed_curve
from spherogram import Link

ROOT=Path(__file__).resolve().parents[3]
REPORT=ROOT/'reports/q18-neighbours/q18-neighbours-20261102T022100+1100-165739'
RUN_COMMIT='c28323ee925371559218c2bc699e6d2804b796bf'
RESULT_COMMIT='ba456fd0921cb443a5d05234ae5ffffc6a71aa5e'
ARCHIVE_SHA='409560f01dbef378c3f1d03db683389d3d931b2a2922ee2ffe9aaed3c3acfed6'
SOURCE_E={17:10.952,18:10.838,19:12.008,22:12.509}


def require(condition,message):
    if not condition:raise ValueError(message)


def digest(data):return hashlib.sha256(data).hexdigest()
def key(value):return json.dumps(value,sort_keys=True)
def source_blob(path):return subprocess.check_output(['git','show',RUN_COMMIT+':'+path],cwd=ROOT)


def scalar_gates(r):
    a,b,c=r['initial'],r['final'],r['config'];q=c['expected_q']
    return {'initial_charge':abs(abs(a['hopf_integral'])-q)/q<=.05,
            'final_charge':abs(abs(b['hopf_integral'])-q)/q<=.05,
            'resolved_cells':min(a['minimum_corner_cone'],b['minimum_corner_cone'])>0,
            'unit_norm':b['unit_error']<1e-12,'stationary':b['cpu_tangent_gradient_rms']<1e-3,
            'virial':b['virial_residual']<.05,
            'endpoint_cpu_audit':bool(b['cpu_endpoint_audit']) and all(x['passed'] for x in b['cpu_endpoint_audit'].values()),
            'completed_without_numerical_fault':r['status'] in ('gradient_stationary','iteration_budget','time_budget','residual_not_stationary')}


def audit_scalars(records):
    read=lambda name:json.loads(records[name])
    state,plan,summary=[read(n) for n in ('campaign.json','plan.json','summary.json')]
    require(state['git_commit']==RUN_COMMIT and summary['git_commit']==RUN_COMMIT,'Run commit differs')
    require(summary['source_unchanged'] and state['overall_wall_seconds'] is None,'Source changed or overall cap added')
    require(digest(records['plan.json'])==state['plan_sha256'],'Frozen plan hash differs')
    for name,expected in state['code_sha256'].items():require(digest(source_blob(name))==expected,'Recorded source/lock/config: '+name)
    source_count=len(state['code_sha256']);missing=set();passes=0;audits=0;history_increase=0.;statuses=Counter();endpoints={};rows={}
    require(len(plan['stages'])==31 and len(state['stages'])==31,'Expected 31-stage campaign')
    for stage in plan['stages']:
        name=stage['id'];job=state['stages'][name];previous=None
        require(job['status']=='stationary','Stage not stationary: '+name)
        for attempt in job['attempts']:
            case=attempt['directory'];r=read(case+'/result.json');c=read(case+'/config.json');m=read(case+'/manifest.json');history=read(case+'/history.json')
            require(r['config']==c and r['history']==history and r['final']==history[-1],'Case configuration/history differs: '+case)
            require(digest(records[case+'/config.json'])==attempt['config_sha256']==m['config_sha256'],'Case config hash differs')
            require(read('configs/'+Path(case).name+'.json')==c,'Prepared config differs')
            require((c['n'],c['h'],c['expected_q'])==(stage['n'],stage['h'],stage['q']),'Geometry/degree differs')
            require(c['seed']==stage['template']['seed'] and c['precondition_length']==stage['length'],'One-factor control changed')
            require(m['git_commit']==RUN_COMMIT and not m['dirty_tree'] and m['source_unchanged_during_run'],'Run code provenance failed')
            require(m['backend']=='cuda-float64' and m['device_validation']['passed'],'CUDA validation absent')
            require(all(x['passed'] for x in m['device_validation']['checks'].values()),'Device check failed')
            require(m['lock_sha256']==state['code_sha256']['uv.lock'],'Lock hash differs')
            require(all(state['code_sha256'][p]==h for p,h in m['source_sha256'].items()),'Numerical source hash differs')
            for item,expected in m['artifacts_sha256'].items():
                member=case+'/'+item
                if member in records:require(digest(records[member])==expected,'Case artifact hash: '+member)
                else:
                    require(item.endswith('.npz'),'Non-field artifact missing: '+member);missing.add(member)
            cp=c.get('initial_checkpoint')
            if previous:
                parent=previous
            elif stage.get('from'):
                parent=state['stages'][stage['from']]['directory']
            else:parent=None
            if parent:
                pm=read(parent+'/manifest.json')
                require(cp and Path(cp).parent.name==Path(parent).name,'Checkpoint parent differs')
                require(attempt['input_sha256']==m['initial_checkpoint_sha256']==pm['artifacts_sha256']['final.npz'],'Checkpoint lineage hash differs')
            elif stage.get('checkpoint'):
                matches=[x for x in state['inventory']['verified_fields'] if x['sha256']==stage['checkpoint_sha256'] and x['path']==stage['checkpoint']]
                require(len(matches)==1,'Historical field receipt missing')
                item=matches[0];ref=item['record']
                if ':' in ref:
                    archive,member=ref.split(':',1)
                    with zipfile.ZipFile(BytesIO(source_blob(archive))) as z:old=json.loads(z.read(member))
                else:old=json.loads(source_blob(ref))
                require(old['artifacts_sha256']['final.npz']==stage['checkpoint_sha256']==m['initial_checkpoint_sha256']==attempt['input_sha256'],'Retained reference hash differs')
            else:require(cp is None and attempt['input_sha256'] is None,'Fresh field unexpectedly replaced')
            for phase in ('initial','final'):
                item=r[phase];require(all(x['passed'] for x in item['cpu_endpoint_audit'].values()),'CPU endpoint check failed')
                require(abs(item['e2']+item['e4']-item['energy'])<1e-11,'Energy components inconsistent')
                require(abs(abs(item['e2']-item['e4'])/item['energy']-item['virial_residual'])<1e-12,'Virial identity differs')
                require(abs(item['cpu_tangent_gradient_rms']-item['tangent_gradient_rms'])<1e-9,'CPU/GPU residual differs')
                require(set(item['recorded_at'])=={'utc','melbourne'},'Missing endpoint timestamps')
                audits+=1
            values=[v['energy'] for v in history];changes=[b-a for a,b in zip(values,values[1:])]
            history_increase=max([history_increase]+changes)
            require(all(b-a<=1e-10*max(1.,abs(a)) for a,b in zip(values,values[1:])),'Nonmonotone recorded history')
            if previous:
                old=read(previous+'/result.json')['final']['energy']
                require(abs(r['initial']['energy']-old)<1e-10*max(1.,abs(old)),'Same-grid restart energy differs')
            require(attempt['status']=='completed' and attempt['returncode']==0,'Pass did not complete')
            statuses[r['status']]+=1;passes+=1;previous=case
        require(previous==job['directory'],'Final attempt selection differs')
        r=read(previous+'/result.json');f=r['final'];g=scalar_gates(r);endpoints[name]=r
        require(all(g.values()),'Final scalar gate failed: '+name)
        require(f==summary['stages'][name]['final'],'Summary endpoint differs')
        require(all(summary['stages'][name]['gates'][k]==v for k,v in g.items()),'Summary gates differ')
        folder='analysis/'+Path(previous).name;sc=read(folder+'/scaling.json')
        require(sc['checkpoint_sha256']==read(previous+'/manifest.json')['artifacts_sha256']['final.npz'],'Scaling field hash differs')
        require(len(sc['rows'])==5 and len(sc['finite_difference_comparisons'])==2,'Scaling audit incomplete')
        require(all(x['minimum_corner_cone']>0 for x in sc['rows']),'Scaling cell unresolved')
        require(all(abs(x['normalized_energy_derivative'])<.05 and abs(x['difference_from_e2_minus_e4'])<.05 for x in sc['finite_difference_comparisons']),'Independent scaling gate failed')
        q=stage['q'];source=SOURCE_E.get(q);delta=abs(f['energy']-source)/source if source else None
        # An absent published_energy produces a vacuous True in the runner.
        # Here research/source comparisons are explicitly recomputed instead.
        if source:require(delta<.03,'Explicit source-energy comparison failed')
        rows[name]={'q':q,'n':stage['n'],'h':stage['h'],'side_length':(stage['n']-1)*stage['h'],'branch':stage['branch'],'role':stage['role'],
                    'energy':f['energy'],'cpu_residual':f['cpu_tangent_gradient_rms'],'signed_hopf':f['hopf_integral'],
                    'relative_hopf_error':abs(abs(f['hopf_integral'])-q)/q,'virial':f['virial_residual'],'unit_error':f['unit_error'],
                    'minimum_corner_cone':f['minimum_corner_cone'],'gates':g,'independent_scaling':True,
                    'source_energy_reference':source,'relative_source_energy_difference':delta,'passes':len(job['attempts']),
                    'max_dilation_derivative':max(abs(x['normalized_energy_derivative']) for x in sc['finite_difference_comparisons']),
                    'max_dilation_identity_defect':max(abs(x['difference_from_e2_minus_e4']) for x in sc['finite_difference_comparisons'])}
    require(len(state['analysis'])==89 and all(x['status']=='completed' and x['returncode']==0 for x in state['analysis'].values()),'Analysis jobs incomplete')
    comparisons={}
    for name,entry in summary['comparisons'].items():
        a,b=name.split('__');ra,rb=rows[a],rows[b];ranking=entry['status']=='eligible'
        require(ra['q']==rb['q'],'Different Q values ranked together')
        domain=b.endswith('-domain')
        if domain:require(ra['h']==rb['h'] and rb['side_length']>ra['side_length'],'Domain geometry differs')
        else:require(abs(ra['side_length']-rb['side_length'])<1e-12,'Box differs')
        if ranking:require(ra['n']==rb['n'] and ra['h']==rb['h'],'Ranking meshes differ')
        difference=abs(rb['energy']-ra['energy'])/ra['energy']
        require(abs(difference-entry['relative_energy_change'])<1e-14,'Summary comparison differs')
        if not ranking:require(difference<.02 and entry['status']=='pass','Energy convergence gate failed')
        comparisons[name]={'relative_energy_difference':difference,'kind':'ranking' if ranking else 'domain' if domain else 'mesh','scalar_eligible':True}
    span=(datetime.fromisoformat(state['updated_at']['utc'])-datetime.fromisoformat(state['started_at']['utc'])).total_seconds()
    return {'stages':rows,'comparisons':comparisons,'provenance':{'run_commit':RUN_COMMIT,'results_commit':RESULT_COMMIT,'source_lock_config_hashes':source_count,
            'passes':passes,'solver_statuses':dict(statuses),'cpu_endpoint_audits':audits,'analysis_jobs':len(state['analysis']),
            'bulk_field_files_not_in_archive':len(missing),'largest_recorded_energy_increase':history_increase,
            'tracked_state_span_seconds':span,'solver_wall_seconds':summary['solver_wall_seconds'],'started_at':state['started_at'],'last_state_update':state['updated_at'],
            'refreshed_collection_at':summary['generated_at'],'historical_q18':state['inventory']['historical_q18']}}


def topology_audit(records):
    read=lambda name:json.loads(records[name]);state=read('campaign.json');rows={};counts=Counter();poly_cache={}
    references={}
    for sign in (-1,1):
        link=Link(braid_closure=[sign]*7)
        references[key(canonical_gauss(link))]=jones_a(link)
    # Independent polynomial curve, not a name inferred from the observed shape.
    cable=diagram_analysis(cable_reference(256));cable_poly=cable['jones_A']
    worst_gauss_replay=0.;worst_gauss_integer=0.;gauss_nonmonotone=0
    rng_state=random.getstate();random.seed(35)
    try:
        for name,job in state['stages'].items():
            if name in ('q1-control','q2-control'):continue
            folder='analysis/'+Path(job['directory']).name;data=read(folder+'/topology.json')
            manifest=read(job['directory']+'/manifest.json');independent=read(folder+'/independent-links.json');output={}
            for phase,field in data['phases'].items():
                require(field['checkpoint_sha256']==manifest['artifacts_sha256'][phase+'.npz'],'Topology references wrong field')
                targets={}
                for target,t in field['targets'].items():
                    require(t['status']=='closed_components','Unresolved preimage')
                    member=folder+f'/{phase}-{target}-curves.npz'
                    with np.load(BytesIO(records[member]),allow_pickle=False) as archive:
                        curves=[archive[f'curve_{i}'] for i in range(t['components'])]
                    require(len(curves)==len(t['components_data']),'Component count differs')
                    classes=[]
                    for curve,component in zip(curves,t['components_data']):
                        closed_curve(curve);require(len(component['diagrams'])==9,'Missing diagram resolution/view')
                        observed=[]
                        for d in component['diagrams']:
                            if not d['pd']:
                                require(d['crossings']==0 and d['diagram']=='unknot','Empty PD misclassified');label='unknot'
                            else:
                                link=Link(d['pd']);require(len(link.link_components)==1,'Single-curve input diagram has wrong component count')
                                random.seed(35);link.simplify('global',type_III_limit=100)
                                require(len(link.crossings)==d['crossings'],'Replayed simplified crossing count differs')
                                word=canonical_gauss(link);wkey=key(word)
                                require(key(word)==key(d['canonical_gauss']),'Replayed Gauss word differs')
                                if wkey not in poly_cache:poly_cache[wkey]=jones_a(link)
                                polynomial=poly_cache[wkey]
                                require(polynomial==d['jones_A'],'Recomputed exact Jones polynomial differs')
                                if not link.crossings:
                                    require(link.unlinked_unknot_components==1,'Simplifier lost trivial-component count')
                                    label='unknot'
                                elif wkey in references:
                                    require(polynomial==references[wkey],'Two-strand seven-crossing reference differs');label='K72_finite_diagram'
                                elif polynomial==cable_poly:label='cable_polynomial_compatible'
                                else:label='unclassified'
                            observed.append(label);counts['component_diagrams_replayed']+=1
                        require(len(set(observed))==1,'Inconsistent component identification')
                        classes.append(observed[0])
                    pairs=[]
                    independent_target=independent['targets'][phase+'-'+target]
                    require(independent_target['curves_sha256']==digest(records[member]),'Independent-link curve hash differs')
                    require(independent_target['checkpoint_sha256']==field['checkpoint_sha256'],'Independent-link field hash differs')
                    for p in t['pairwise_link_checks']:
                        values=[x['linking_number'] for x in p['observations']]
                        require(len(values)==6 and len(set(values))==1,'Diagram linking inconsistent')
                        integer=values[0];samples=[]
                        stored=next(x for x in independent_target['pairs'] if x['first']==p['first'] and x['second']==p['second'])
                        require(stored['signed_diagram_link']==integer,'Stored pair link differs')
                        errors=[]
                        for n in (256,384,512):
                            v=gauss_link(resample(curves[p['first']],n),resample(curves[p['second']],n))
                            old=next(x for x in stored['gauss_samples'] if x['segments']==[n,n])
                            delta=abs(v['linking_integral']-old['linking_integral']);worst_gauss_replay=max(worst_gauss_replay,delta)
                            require(delta<1e-12,'Independent Gauss replay differs')
                            err=abs(v['linking_integral']-integer);errors.append(err);worst_gauss_integer=max(worst_gauss_integer,err)
                            samples.append({'segments':n,'gauss_integral':v['linking_integral'],'difference_from_signed_diagram':err,
                                            'minimum_polygon_separation':v['minimum_polygon_separation']})
                            counts['gauss_samples_recomputed']+=1
                        if not all(b<=a for a,b in zip(errors,errors[1:])):gauss_nonmonotone+=1
                        pairs.append({'first':p['first'],'second':p['second'],'signed_diagram_link':integer,'samples':samples})
                        counts['diagram_pair_projections_checked']+=6
                    targets[target]={'components':len(curves),'component_classes':classes,'pairs':pairs,'checkpoint_sha256':field['checkpoint_sha256']}
                output[phase]=targets
            rows[name]=output;print('TOPOLOGY',name,flush=True)
    finally:random.setstate(rng_state)
    return {'stages':rows,'counts':dict(counts),'largest_gauss_replay_difference':worst_gauss_replay,
            'largest_gauss_integer_difference':worst_gauss_integer,'pairs_with_nonmonotone_gauss_error':gauss_nonmonotone,
            'reference':'closures of the explicit two-strand braids sigma1^+/-7; Eq3.7 polynomial cable curve',
            'scope':'replayed finite diagrams and quadrature; no formal move trace or continuum isotopy certificate'}


def audit(include_topology=True):
    raw=(REPORT/'evidence.zip').read_bytes();require(digest(raw)==ARCHIVE_SHA,'Archive SHA-256 differs')
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        names=archive.namelist();require(len(names)==len(set(names)),'Duplicate archive members')
        records={name:archive.read(name) for name in names}
    envelope=json.loads(records['evidence-hashes.json'])
    require(set(names)==set(envelope['files'])|{'evidence-hashes.json'},'Archive hash coverage differs')
    for name,item in envelope['files'].items():require(digest(records[name])==item['sha256'],'Archive member differs: '+name)
    for name in ('campaign.json','summary.json','SUMMARY.md','plan.json','evidence-hashes.json'):
        require((REPORT/name).read_bytes()==records[name],'Readable published copy differs: '+name)
    result={'assessed_at':timestamp(),'assessment_script_sha256':digest(Path(__file__).read_bytes()),
            'archive':{'sha256':ARCHIVE_SHA,'bytes':len(raw),'members':len(names),'hashed_members':len(envelope['files'])},
            **audit_scalars(records),'topology':{'checked':False},
            'scope':'independent record/finite-curve review; reported full-field CPU/GPU audits are verified as records, not rerun here'}
    if include_topology:
        result['topology']={'checked':True,**topology_audit(records)}
        result['disposition']='bounded_Q17_Q19_branch_benchmarks_supported; Q18_three_component_link_robust_in_tested_controls; hyperbolic_reproduction_not_obtained'
    else:result['disposition']='scalar_records_verified; topology_review_pending'
    result['assessment_finished_at']=timestamp()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);p.add_argument('--scalars-only',action='store_true');a=p.parse_args()
    if a.output and a.output.exists():raise FileExistsError('Use a new ledger path; retained assessment will not be overwritten')
    result=audit(not a.scalars_only)
    if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('assessed_at','assessment_finished_at','archive','provenance','disposition')},indent=2))


if __name__=='__main__':main()
