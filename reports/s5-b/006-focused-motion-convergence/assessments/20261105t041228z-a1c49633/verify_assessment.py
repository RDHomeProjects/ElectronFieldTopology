"""Recompute S5-B-006 compact-record assessment; Apache-2.0.

Field-derived diagnostics are audited/rethresholded, not independently recomputed
from NPZ. Scalar history reductions and centroid regressions are replayed here.
"""
import argparse,collections,csv,hashlib,io,json,math,statistics,zipfile
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
EXPECTED='4ced49b9bc30deb186c5cacfc634870a96fe2c36ae6643db79fa2fdd2fdf0db5'
SOURCE='1e3a4ed64ee68bc014846923e4b75845a5c20cf5'
RUN='20261104t142830z-d061b67b'
OLD='reports/sf-motion/lowq-motion-2026-11-03T104629-568611+1100-30672/evidence.zip'
def need(ok,msg):
    if not ok:raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def stamp():
    t=datetime.now(timezone.utc);return dict(utc=t.isoformat(),melbourne=t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat())
def close(a,b):need(math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-14),f'Scalar mismatch {a} != {b}')
def bounds(v):return dict(min=min(v),max=max(v),median=statistics.median(v))
def verify(evidence,repo):
    repo=Path(repo);b=Path(evidence).read_bytes();need(sha(b)==EXPECTED,'Unexpected compact evidence SHA-256')
    old=(repo/OLD).read_bytes();need(sha(old)=='780cfff1d5be5fe9e61b238206aceb6a6f47a82350e8ce257c76cc79f56d8784','Original evidence differs')
    with zipfile.ZipFile(io.BytesIO(old)) as oz:limits=json.loads(oz.read('plan.json'))['limits']
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        names=z.namelist();need(len(names)==len(set(names)),'Duplicate members')
        need(all(not Path(n).is_absolute() and '..' not in Path(n).parts and '\\' not in n for n in names),'Unsafe member')
        need(sum(i.file_size for i in z.infolist())<30_000_000 and z.testzip() is None,'ZIP expansion/CRC failure')
        get=lambda p:json.loads(z.read(p))
        hashes=get('evidence-hashes.json')['sha256'];need(set(names)==set(hashes)|{'evidence-hashes.json'},'Incomplete member ledger')
        for n,h in hashes.items():need(sha(z.read(n))==h,'Member digest mismatch: '+n)
        c=get('campaign.json');cfg=get('plan.json');inv=get('inventory.json');controls=get('controls.json')
        need(c['record_id']==RUN and c['source_commit']==SOURCE and not c['source_worktree_dirty'],'Source/run provenance mismatch')
        need(c['status']=='complete_pending_review' and c['expected_cases']==8 and len(c['cases'])==8,'Completion mismatch')
        need(cfg==c['config'] and canonical(cfg)==c['config_sha256'],'Config mismatch')
        need(cfg['milestone_times']==[1.,2.,3.] and cfg['dt']==.01 and cfg['beta']==.3,'Unexpected experiment')
        need(canonical(inv['files'])==inv['input_fingerprint']==c['input_fingerprint'],'Input map mismatch')
        need(canonical(c['source_sha256'])==c['code_sha256'],'Code map mismatch')
        for n,h in c['source_sha256'].items():need(sha((repo/'src/electron_field_topology'/n).read_bytes())==h,'Numerical source mismatch: '+n)
        need(c['controls']==controls and controls['interpolation']['passed'] and controls['fixed_layers']['passed'],'Controls mismatch')
        need(len(c['admissions'])==48,'Admission count mismatch')
        for r in c['admissions'].values():
            passed=(r['fixed_field_max']==r['fixed_rate_max']==0 and r['unit_max']<1e-10 and r['tangency_max']<1e-10 and r['free_field_correction_max']<1e-12 and r['free_rate_correction_max']<1e-12)
            need(passed==r['passed'] and passed,'Admission gate mismatch')
        rows=[];fail=collections.Counter();replayed=0
        for key,r in c['cases'].items():
            need(r['status']=='complete' and r['admission']==get(f'cases/{key}/admission.json'),'Case/admission mismatch')
            need(r['admission']['original_raw_replay_bit_exact'],'Missing old-initial replay flag')
            h=get(f'cases/{key}/history-combined.json');need([x['step'] for x in h]==list(range(0,301,5)),'History coverage mismatch')
            need(len(r['attempts'])==3,'Unexpected attempt count')
            combined={}
            for ai,start in enumerate([0,100,200]):
                ap=f'cases/{key}/attempt-{ai:03d}';m=get(ap+'/manifest.json');result=get(ap+'/result.json')
                need(m['git_commit']==SOURCE and not m['git_worktree_dirty'] and m['physics']==r['physics'],'Attempt provenance mismatch')
                need(m['initial']['start_step']==start,'Resume step mismatch')
                for n,digest in m['physics_source_sha256'].items():need(digest==c['source_sha256'][n],'Kernel digest mismatch')
                need(result['step']==start+100,'Attempt endpoint mismatch')
                for hr in get(ap+'/history.json'):combined[hr['step']]=hr
            for hr in h:
                for k in ['energy','momentum','centroid','time','unit_error','tangency_error']:need(hr[k]==combined[hr['step']][k],'Combined history differs')
            for t in [1.,2.,3.]:
                ms=r['milestones'][str(t)];need(ms==get(f'cases/{key}/milestone-{int(t*100):06d}.json'),'Milestone/ledger mismatch')
                a=ms['assessment'];hist=[x for x in h if x['time']<=t];e0=hist[0]['energy'];p0=hist[0]['momentum']
                ed=max(abs(x['energy']-e0)/abs(e0) for x in hist)
                pd=max(math.sqrt(sum((v-w)**2 for v,w in zip(x['momentum'],p0)))/abs(e0) for x in hist)
                mean=statistics.mean(x['time'] for x in hist);den=sum((x['time']-mean)**2 for x in hist)
                slope=[sum((x['time']-mean)*x['centroid'][j] for x in hist)/den for j in range(3)]
                speed=math.sqrt(sum((v-(.3 if j==r['axis'] else 0))**2 for j,v in enumerate(slope)))/.3
                close(ed,a['max_energy_relative_drift']);close(pd,a['max_momentum_drift_over_initial_energy']);close(speed,a['speed_relative_error'])
                for x,y in zip(slope,a['fitted_centroid_velocity']):close(x,y)
                checks={'energy':ed<=limits['energy_relative'],'momentum':pd<=limits['momentum_scaled'],
                    'constraints':max(max(x['unit_error'],x['tangency_error']) for x in hist)<1e-10,
                    'shape':a['translated_static_field_relative_l2']<=limits['shape_relative'],'speed':speed<=limits['speed_relative'],
                    'topology':abs(abs(a['final']['hopf_integral'])-r['q'])/r['q']<=limits['charge_relative_error'] and a['final']['minimum_corner_cone']>0,
                    'tail':a['final']['boundary_shell_energy_fraction']<=limits['tail_fraction']}
                need(checks==a['checks'] and all(checks.values())==a['bounded_case_gates_pass'],'Scientific gate mismatch')
                need(a['r99_cone_window_clear']==(t<r['admission']['initial_spatial']['initial_light_cone_clearance']),'r99 indicator mismatch')
                for k,v in checks.items():
                    if not v:fail[k]+=1
                co=a['comoving_own_initial'];close(co['cube_side'],12-.6*t);need(co['sampling_nodes']==33,'Comoving sampling mismatch')
                rows.append(dict(case_id=key,q=r['q'],axis=r['axis'],method=r['method'],time=t,energy_drift=ed,momentum_scaled=pd,speed_relative=speed,
                    shape=a['translated_static_field_relative_l2'],tail=a['final']['boundary_shell_energy_fraction'],hopf=a['final']['hopf_integral'],
                    comoving_raw=co['comparison']['raw_relative_l2'],comoving_registered=co['comparison']['phase_registered_relative_l2'],
                    phase=co['comparison']['global_internal_phase_radians'],r99_clear=a['r99_cone_window_clear'],failed=';'.join(k for k,v in checks.items() if not v)))
                replayed+=1
        pairs=get('method-pairs.json');need(len(pairs)==12,'Method-pair coverage mismatch')
    comparisons=[];lookup={(r['q'],r['axis'],r['method'],r['time']):r for r in rows}
    for q in [1,2]:
        for axis in [0,2]:
            for t in [1.,2.,3.]:
                a=lookup[q,axis,'trilinear',t];b=lookup[q,axis,'cubic',t]
                comparisons.append(dict(q=q,axis=axis,time=t,shape_reduction=1-b['shape']/a['shape'],comoving_raw_reduction=1-b['comoving_raw']/a['comoving_raw'],
                    comoving_registered_reduction=1-b['comoving_registered']/a['comoving_registered'],speed_change=b['speed_relative']-a['speed_relative'],**{k:v for k,v in pairs[f'q{q}-n101-L16-a{axis}-t{t:g}'].items() if isinstance(v,(float,int))}))
    return dict(verified_at=stamp(),run_id=RUN,source_commit=SOURCE,archive_sha256=EXPECTED,archive_members=len(names),hashed_members=len(hashes),
        scalar_milestones_replayed=replayed,source_files_checked=len(c['source_sha256']),admissions=48,admissions_passed=48,
        raw_boundary_leaks=sum(r['raw_fixed_field_max']>1e-10 or r['raw_fixed_rate_max']>1e-10 for r in c['admissions'].values()),
        admission_maxima={k:max(r[k] for r in c['admissions'].values()) for k in ['raw_fixed_field_max','raw_fixed_rate_max','free_field_correction_max','free_rate_correction_max','unit_max','tangency_max']},
        limits=limits,failures=dict(fail),bounded_milestone_passes=sum(not r['failed'] for r in rows),rows=rows,comparisons=comparisons,
        full_npz_replay_performed=False,raw_transport_label='Old trilinear baseline in every case, including cubic rows; not cubic-before-projection.',
        disposition='cubic_candidate_retained; all_tail_gates_fail; speed_tradeoff; convergence_and_isolation_open')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=verify(a.evidence,a.repo);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['verified_at','archive_members','scalar_milestones_replayed','admissions_passed','failures','disposition']},indent=2))
