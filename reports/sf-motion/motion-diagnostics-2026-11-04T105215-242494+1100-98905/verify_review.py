#!/usr/bin/env python3
"""Verify compact diagnostic records and independently recompute review statistics.

Full scientific fields are not in either archive. No new full-field calculation
or validation of the underlying field sampler is claimed by this script.
"""
import argparse, collections, csv, hashlib, io, json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import zipfile
import numpy as np

DIAGNOSTIC_SHA='4e5978e94243165fdde882536c57ca2f5268abfbfad2d67a55c1f8fe5a9127d4'
ORIGINAL_SHA='780cfff1d5be5fe9e61b238206aceb6a6f47a82350e8ce257c76cc79f56d8784'

def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return sha(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def timestamp():
    n=datetime.now(ZoneInfo('UTC'))
    return {'utc':n.isoformat(),'melbourne':n.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def close(a,b,label):assert np.allclose(a,b,rtol=1e-10,atol=3e-13),(label,a,b)
def fit(rows):
    t=np.array([r['time'] for r in rows]);x=np.array([r['centroid'] for r in rows])
    return np.linalg.lstsq(np.stack([t-t[0],np.ones(len(t))],axis=-1),x,rcond=None)[0][0]
def checked(path,expected):
    assert sha(Path(path).read_bytes())==expected,('Archive digest differs',str(path))
    z=zipfile.ZipFile(path);names=z.namelist()
    assert len(names)==len(set(names)) and z.testzip() is None
    hashes=json.loads(z.read('evidence-hashes.json'))['sha256']
    assert set(names)==set(hashes)|{'evidence-hashes.json'}
    for name,h in hashes.items():assert sha(z.read(name))==h,('Member differs',name)
    return z,len(hashes)

def verify(diagnostic,original,summary,source_dir):
    z,n=checked(diagnostic,DIAGNOSTIC_SHA);o,on=checked(original,ORIGINAL_SHA)
    read=lambda name:json.loads(z.read(name))
    d=read('diagnostic.json');m=read('manifest.json');inv=read('inventory.json');cfg=read('config.json')
    old=json.loads(o.read('campaign.json'));pairs_old=json.loads(o.read('comparisons.json'))['pairs']
    assert z.read('SUMMARY.md')==Path(summary).read_bytes()
    assert canonical(cfg)==d['config_sha256']==m['config_sha256'] and cfg==m['config']
    assert cfg['evidence_sha256']==ORIGINAL_SHA==inv['evidence_sha256']
    assert d['status']=='complete_pending_review' and d['expected']=={'seeds':6,'cases':60,'pairs':70}
    assert len(d['seeds'])==6 and len(d['cases'])==60 and len(d['pairs'])==70
    assert set(d['seeds'])==set(old['seeds']) and set(d['cases'])==set(old['cases'])
    assert inv['ready'] and not inv['missing_or_changed'] and len(inv['files'])==126
    assert len({r['relative_path'] for r in inv['files']})==126
    expected_files={f'readmission/{sid}/latest.npz':s['field_sha256'] for sid,s in old['seeds'].items()}
    for name,c in old['cases'].items():
        prefix='cases/'+name+'/'+Path(c['attempts'][-1]).name+'/'
        expected_files[prefix+'initial.npz']=None
        expected_files[prefix+'final.npz']=c['final_checkpoint_sha256']
    assert set(expected_files)=={r['relative_path'] for r in inv['files']}
    for r in inv['files']:
        assert r['expected_sha256']==expected_files[r['relative_path']]
        if r['expected_sha256']:assert r['sha256']==r['expected_sha256'] and r['status']=='verified'
        else:assert r['status']=='present_metadata_and_state_checked_during_audit'
    fingerprint=canonical({'evidence':ORIGINAL_SHA,'files':{r['relative_path']:r['sha256'] for r in inv['files']}})
    assert fingerprint==inv['input_fingerprint']==d['input_fingerprint']==m['input_fingerprint']
    assert d['source_sha256']==m['source_sha256']
    for name,h in m['source_sha256'].items():assert sha((Path(source_dir)/name).read_bytes())==h,name
    assert len(m['source_sha256'])==13 and not m['git_worktree_dirty']
    assessed=timestamp();case_rows=[];numeric_replays=0;flags=collections.Counter()
    for name,r in d['cases'].items():
        assert r==read('cases/'+name+'.json') and r['case_id']==name
        assert r['initial_state_reconstructed_bit_exact']
        olda=old['cases'][name]['assessment'];a=r['recomputed_endpoint']
        expected={}
        for k in ['translated_static_field_relative_l2','speed_absolute_error','max_energy_relative_drift','max_momentum_drift_over_initial_energy']:
            expected[k]=bool(np.isclose(a[k],olda[k],rtol=cfg['replay_rtol'],atol=cfg['replay_atol']))
        for k in ['continuum_energy','radius_99','boundary_shell_energy_fraction','hopf_integral','minimum_corner_cone']:
            expected[k]=bool(np.isclose(a['final'][k],olda['final'][k],rtol=cfg['replay_rtol'],atol=cfg['replay_atol']))
        assert expected==r['replay_matches'] and r['all_replays_match']==all(expected.values())
        assert all(expected.values());numeric_replays+=len(expected)
        assert r['original_case_checks']==olda['checks']
        for k,v in a['checks'].items():assert v==olda['checks'][k]
        flags.update(k for k,v in olda['checks'].items() if not v)
        t=r['initial_transport']
        if r['beta']:
            other=name.replace('-dt0.01','-dt0.02') if r['dt']==.01 else name.replace('-dt0.02','-dt0.01')
            assert t==d['cases'][other]['initial_transport']
        case_rows.append({'assessed_utc':assessed['utc'],'assessed_melbourne':assessed['melbourne'],
          'case_id':name,'seed_id':r['seed_id'],'q':old['cases'][name]['q'],'beta':r['beta'],'axis':r['axis'],'dt':r['dt'],
          'initial_reference_error':r['initial_reference_field_relative_l2'],
          'initial_rate_mismatch':t['rate_relative_l2'],'initial_acceleration_mismatch_rms':t['tangent_acceleration_difference_rms'],
          'initial_acceleration_mismatch_relative':t['tangent_acceleration_relative_l2'],
          'shape_error':a['translated_static_field_relative_l2'],'all_endpoint_replays_match':r['all_replays_match']})
    csv_rows=list(csv.DictReader(io.StringIO(z.read('case-metrics.csv').decode())))
    assert len(csv_rows)==60 and {r['case_id'] for r in csv_rows}==set(d['cases'])
    assert b'\r' not in z.read('case-metrics.csv')
    for r in csv_rows:
        close(float(r['shape_relative_l2']),d['cases'][r['case_id']]['recomputed_endpoint']['translated_static_field_relative_l2'],'CSV shape')
    metric_rows=[]
    for sid,s in d['seeds'].items():
        assert s==read('seeds/'+sid+'.json') and s['seed_id']==sid
        G=np.array(s['classical_metric']['metric']);ev=np.linalg.eigvalsh(G)
        close(G,G.T,'metric symmetry');close(ev,s['classical_metric']['eigenvalues'],'metric eigenspectrum')
        close(np.diag(G)[3:6],s['classical_metric']['rotational_diagonal'],'rotation diagonal')
        close(G[6,6],s['classical_metric']['internal_phase_inertia'],'phase inertia')
        assert min(ev)>=-1e-12
        ref=old['cases'][f'{sid}-b0-a0-dt0.01']['initial']
        for k in ['continuum_energy','radius_99','boundary_shell_energy_fraction','hopf_integral','minimum_corner_cone']:
            close(s['spatial'][k],ref[k],'rest '+k)
        q=old['seed_configs'][sid]['q'];E=s['spatial']['continuum_energy']
        combination=G[5,5]+2*q*G[5,6]+q*q*G[6,6]
        metric_rows.append({'assessed_utc':assessed['utc'],'assessed_melbourne':assessed['melbourne'],
          'seed_id':sid,'q':q,'energy':E,'rotation_x':G[3,3],'rotation_y':G[4,4],'rotation_z':G[5,5],
          'internal_phase':G[6,6],'smallest_gram_eigenvalue':ev[0],
          'axial_combination_norm_squared':combination,
          'axial_combination_normalized':combination/(G[5,5]+q*q*G[6,6]),
          'rotation_phase_correlation':G[5,6]/np.sqrt(G[5,5]*G[6,6])})
    expected_pairs={(p['a'],p['b'],p['kind']) for p in pairs_old};seen=set();pair_rows=[]
    for key,p in d['pairs'].items():
        assert p==read('pairs/'+key+'.json') and key==p['a']+'__'+p['b']
        seen.add((p['a'],p['b'],p['kind']))
        assert [s['sampling_nodes'] for s in p['samples']]==cfg['comparison_grids']
        lengths=[*old['cases'][p['a']]['physical']['lengths'],*old['cases'][p['b']]['physical']['lengths']]
        side=min(lengths)-2*cfg['shell_width']
        for sample in p['samples']:
            close(sample['cube_side'],side,'cube side');close(sample['spacing'],side/(sample['sampling_nodes']-1),'comparison spacing')
            assert all(np.isfinite(sample[k]) and sample[k]>=0 for k in ['field_relative_l2','field_rms','rate_relative_l2','rate_rms','rate_difference_over_field_scale'])
        row={'assessed_utc':assessed['utc'],'assessed_melbourne':assessed['melbourne'],
          'a':p['a'],'b':p['b'],'kind':p['kind'],'q':old['cases'][p['a']]['q'],
          'beta':old['cases'][p['a']]['beta'],'axis':old['cases'][p['a']]['axis'],'dt':old['cases'][p['a']]['physical']['dt'],
          'field_difference_33':p['samples'][0]['field_relative_l2'],'field_difference_49':p['samples'][1]['field_relative_l2'],
          'field_difference_65':p['samples'][2]['field_relative_l2']}
        if p['kind']=='temporal':
            ha=json.loads(o.read('cases/'+p['a']+'/history-combined.json'));hb=json.loads(o.read('cases/'+p['b']+'/history-combined.json'))
            aa={round(r['time'],12):r for r in ha};bb={round(r['time'],12):r for r in hb};times=sorted(aa.keys()&bb.keys())
            av=fit([aa[t] for t in times]);bv=fit([bb[t] for t in times])
            close(av,p['centroid']['velocity_a'],'common-time fit a');close(bv,p['centroid']['velocity_b'],'common-time fit b')
            close(np.linalg.norm(av-bv),p['centroid']['common_time_velocity_difference'],'common-time difference')
            row.update(full_field_difference=p['full_grid_difference']['field_relative_l2'],common_time_velocity_difference=float(np.linalg.norm(av-bv)))
        pair_rows.append(row)
    assert expected_pairs==seen and len(seen)==70
    # Range statements are derived from the retained values; no field samples are reconstructed here.
    moving=[r for r in case_rows if r['beta']]
    stats={'initial_rate_range':[min(r['initial_rate_mismatch'] for r in moving),max(r['initial_rate_mismatch'] for r in moving)],
      'initial_reference_error_max':max(r['initial_reference_error'] for r in case_rows),
      'temporal_full_field_difference_max':max(r['full_field_difference'] for r in pair_rows if r['kind']=='temporal'),
      'common_time_velocity_difference_max':max(r['common_time_velocity_difference'] for r in pair_rows if r['kind']=='temporal')}
    for kind in ['spatial','domain']:
        stats[kind]={str(q):[min(r['field_difference_65'] for r in pair_rows if r['kind']==kind and r['q']==q),
                                  max(r['field_difference_65'] for r in pair_rows if r['kind']==kind and r['q']==q)] for q in [1,2]}
    return {'assessed_at':assessed,'diagnostic_archive_sha256':DIAGNOSTIC_SHA,'original_archive_sha256':ORIGINAL_SHA,
      'diagnostic_hashed_members':n,'original_hashed_members':on,'source_files_matched':len(m['source_sha256']),
      'input_files_linked':len(inv['files']),'endpoint_numeric_checks_replayed':numeric_replays,'endpoint_mismatches':0,
      'initial_states_reported_bit_exact':60,'rest_metrics_checked':6,'pairs_checked':len(pair_rows),
      'original_failed_check_counts':dict(flags),'original_case_passes':sum(c['assessment']['bounded_case_gates_pass'] for c in old['cases'].values()),
      'diagnostic_git_commit':m['git_commit'],'statistics':stats,'cases':case_rows,'kinetic_metrics':metric_rows,'pairs':pair_rows,
      'disposition':'endpoint_replay_confirmed; initialization_and_domain_sensitivity; global_motion_gate_open',
      'scope':'Compact-record/hash/algebra/eigenspectrum review; reported full-field calculations are authenticated but not rerun here without the full scientific fields. No independent audit of every original field checkpoint or diagnostic formula is claimed.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--diagnostic',type=Path,required=True);p.add_argument('--original',type=Path,required=True)
    p.add_argument('--summary',type=Path,required=True);p.add_argument('--sources',type=Path,default=Path(__file__).parent/'source-snapshots');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=verify(a.diagnostic,a.original,a.summary,a.sources);a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'review-verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for key,name in [('cases','case-analysis.csv'),('kinetic_metrics','kinetic-metrics.csv'),('pairs','pair-analysis.csv')]:
        rows=result[key];columns=list(dict.fromkeys(k for r in rows for k in r))
        with (a.output/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps({k:v for k,v in result.items() if k not in ['cases','kinetic_metrics','pairs']},indent=2))

if __name__=='__main__':main()
