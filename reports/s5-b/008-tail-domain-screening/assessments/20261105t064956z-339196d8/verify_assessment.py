"""Authenticate and assess S5-B-008 compact results; standard library, Apache-2.0.

Full NPZ replay is a separate explicit command, never implied by scalar auditing.
"""
import argparse,csv,hashlib,io,json,math,statistics,zipfile
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
EXPECTED='721c3b28762ddf5880ec8cfbaeb65c08097b86fc01bc53c37d13ef1410c5b4fa'
RUN='20261105t053203z-576d1edc'
SOURCE='56bc6b5e442fecbf923f9eec8fcb227eaceff976'
ARCHIVE='20261105t063134z-4cd07212'
def need(ok,message):
    if not ok:raise ValueError(message)
def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def close(a,b):need(math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-14),f'Scalar mismatch: {a} != {b}')
def admitted(m,q,c):return m['relative_force_l2']<=c['relative_force_l2'] and m['acceleration_max']<=c['acceleration_max'] and abs(abs(m['hopf_integral'])-q)/q<=c['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<1e-10

def verify(evidence,repo):
    repo=Path(repo);raw=Path(evidence).read_bytes();need(sha(raw)==EXPECTED,'Unexpected evidence SHA-256')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist();need(len(set(names))==len(names) and z.testzip() is None,'Duplicate/corrupt ZIP')
        need(all(not Path(n).is_absolute() and '..' not in Path(n).parts and '\\' not in n for n in names),'Unsafe ZIP member')
        need(sum(i.file_size for i in z.infolist())<20_000_000,'Unexpected ZIP expansion')
        get=lambda n:json.loads(z.read(n));hashes=get('evidence-hashes.json')['sha256']
        need(set(names)==set(hashes)|{'evidence-hashes.json'},'Member ledger coverage differs')
        for n,h in hashes.items():need(sha(z.read(n))==h,'Member hash differs: '+n)
        c=get('campaign.json');plan=get('plan.json');inv=get('inventory.json');pairs=get('comparisons.json')['pairs']
        need(c['record_id']==RUN and c['source_commit']==SOURCE and not c['source_worktree_dirty'],'Run/source identity mismatch')
        need(c['status']=='complete_pending_review' and len(c['cases'])==6,'Completion mismatch')
        need(canonical(plan)==c['config_sha256'] and canonical(inv['files'])==c['input_fingerprint']==inv['input_fingerprint'],'Plan/input digest mismatch')
        need(plan['spacing']==.16 and plan['tail_fraction_limit']==.001 and plan['shell_width']==2.,'Original scientific settings changed')
        need(plan['domains']==[{'nodes':101,'length':16.},{'nodes':113,'length':17.92},{'nodes':127,'length':20.16}],'Requested matrix differs')
        for n,h in c['source_sha256'].items():need(sha((repo/'src/electron_field_topology'/n).read_bytes())==h,'Scientific source differs: '+n)
        expected={(q,n,l) for q in [1,2] for n,l in [(101,16.),(113,17.92),(127,20.16)]}
        need({(r['q'],r['nodes'],r['length']) for r in c['cases'].values()}==expected,'Case coverage differs')
        oldpath=repo/'reports/sf-motion/lowq-motion-2026-11-03T104629-568611+1100-30672/evidence.zip'
        need(sha(oldpath.read_bytes())==plan['source_evidence_sha256'],'Original compact source archive differs')
        with zipfile.ZipFile(oldpath) as oldzip:old=json.loads(oldzip.read('campaign.json'))
        for sid in plan['source_seeds']:
            need(inv['files'][f'readmission/{sid}/latest.npz']==old['seeds'][sid]['field_sha256'],'Original rest checkpoint hash reference differs')
        rows=[];passes=0
        for key,r in c['cases'].items():
            prefix='readmission/'+key;cfg=get(prefix+'/config.json');hist=get(prefix+'/history.json');manifest=get(prefix+'/manifest.json')
            need(cfg==r['relax_config']==manifest['config'] and canonical(cfg)==manifest['config_sha256'],'Readmission config mismatch')
            need(get(prefix+'/result.json')==r['result'],'Result/ledger mismatch')
            ta=get(prefix+'/tail-assessment.json');need(ta['initial']==r['initial'] and ta['final']==r['final'],'Tail assessment mismatch')
            need(get(prefix+'/embedding.json')==r['embedding'],'Embedding metadata mismatch')
            need(r['embedding']['padding_nodes_each_face']==(r['nodes']-101)//2 and r['embedding']['source_core_copied_bit_exact'],'Embedding declaration differs')
            for n,h in manifest['code_hashes'].items():need(c['source_sha256'][n]==h,'Optimizer source differs')
            need(canonical(manifest['code_hashes'])==manifest['code_sha256'],'Optimizer source-map digest mismatch')
            need(r['status']==r['result']['status']=='stationary','Non-stationary case present')
            need(r['result']['field_sha256']==r['final_checkpoint_sha256']==r['resume_checkpoint_sha256'],'Checkpoint seals disagree')
            need(cfg['external_initial']['initial_state_sha256']==r['initial']['state_sha256'],'Initial state identity differs')
            need(len(hist)>=2 and hist[0]['iteration']==0 and hist[-1]['iteration']==r['result']['iterations'],'History endpoint mismatch')
            need(all(b['energy']<=a['energy']+1e-12 for a,b in zip(hist,hist[1:])),'Optimization energy increased')
            for state in ['initial','final']:
                m=r[state];close(m['shell_fraction'],m['shell_energy']/m['continuum_energy'])
                need(m['tail_gate_pass']==(m['shell_fraction']<=.001),'Tail gate mismatch')
                need(m['preparation_stationarity_pass']==admitted(m['stationarity'],r['q'],plan['readmission']),'Stationarity gate mismatch')
                need(m['fixed_field_max']==0,'Fixed layers failed')
            need(r['final']['original_stationarity_pass']==admitted(r['final']['stationarity'],r['q'],inv['original_readmission']),'Original stationarity flag differs')
            a,b=r['initial'],r['final'];passes+=int(b['tail_gate_pass'])
            rows.append({'case_id':key,'q':r['q'],'nodes':r['nodes'],'length':r['length'],'iterations':r['result']['iterations'],
                'initial_tail_fraction':a['shell_fraction'],'final_tail_fraction':b['shell_fraction'],'tail_gate_pass':b['tail_gate_pass'],
                'final_shell_energy':b['shell_energy'],'continuum_energy':b['continuum_energy'],'discrete_hamiltonian':b['discrete_hamiltonian'],
                'optimization_energy_relative_change':b['discrete_hamiltonian']/a['discrete_hamiltonian']-1,
                'outside_original_inner_cube_energy':b['outside_original_inner_cube_energy'],'outside_original_box_energy':b['outside_original_box_energy'],
                'radius_99':b['radius_99'],'relative_force':b['stationarity']['relative_force_l2'],'max_acceleration':b['stationarity']['acceleration_max'],
                'hopf_integral':b['stationarity']['hopf_integral'],'stress_trace_over_continuum_energy':sum(b['integrated_stress'][i][i] for i in range(3))/b['continuum_energy']})
        table=list(csv.DictReader(io.StringIO(z.read('tail-metrics.csv').decode())))
        need(len(table)==6,'CSV row coverage mismatch')
        for row in table:
            case=c['cases'][row['case_id']]
            close(float(row['initial_tail_fraction']),case['initial']['shell_fraction']);close(float(row['final_tail_fraction']),case['final']['shell_fraction'])
        need(len(pairs)==6 and all(p['both_preparation_stationary'] for p in pairs),'Pair coverage/qualification mismatch')
        for p in pairs:
            need(p['common_core']['common_nodes']==73 and p['common_core']['common_side']==11.52 and p['original_footprint']['common_nodes']==101,'Pair regions differ')
    return {'verified_at':stamp(),'record_id':RUN,'source_commit':SOURCE,'archive_sha256':EXPECTED,'archive_members':len(names),'hashed_members':len(hashes),
        'source_files_checked':len(c['source_sha256']),'stationary_cases':6,'tail_passes':passes,'tail_failures':6-passes,'iterations':sum(r['iterations'] for r in rows),
        'rows':rows,'pairs':pairs,'disposition':'Q2_stationary_tail_mitigation; Q1_tail_open; full_field_domain_sensitivity_remains',
        'verification_scope':'Compact/scalar audit only. Separately retained full-field replay provides NPZ verification.'}

def retention(folder,repo,run=None):
    folder,repo=Path(folder),Path(repo);catpath=repo/'data/archives'/ARCHIVE/'CATALOG.json';cat=json.loads(catpath.read_text());receipt=json.loads((catpath.parent/'VERIFIED.json').read_text())
    indexpath=folder/'release-index.json';mpath=folder/'release-manifest.json';index=json.loads(indexpath.read_text());m=json.loads(mpath.read_text())
    need(sha(catpath.read_bytes())==receipt['catalog_sha256'] and sha(indexpath.read_bytes())==cat['index_sha256']==receipt['index_sha256'],'Catalog/index seal differs')
    need(receipt['status']=='all_remote_bytes_verified' and receipt['root_file_counts']=={'r001':74},'Verification receipt incomplete')
    root=index['roots'][0];need(len(index['roots'])==1 and root['name']==RUN and root['files']==74,'Archive run/count mismatch')
    need(sha(mpath.read_bytes())==root['manifest']['sha256'],'Manifest SHA differs')
    need(len(m['files'])==74 and sum(f['size'] for f in m['files'])==cat['payload_bytes']==297809632,'Payload coverage differs')
    count=0
    if run is not None:
        run=Path(run)
        for f in m['files']:
            p=Path(f['archive_path']);need(p.parts[0]=='files' and '..' not in p.parts,'Unsafe archive path')
            b=(run/Path(*p.parts[1:])).read_bytes();need(len(b)==f['size'] and sha(b)==f['sha256'],'Retained file mismatch: '+str(p));count+=1
    return {'verified_at':stamp(),'archive_id':ARCHIVE,'files':74,'payload_bytes':cat['payload_bytes'],'local_full_run_member_hashes_replayed':count,
        'bulk_part_download_performed_by_this_function':False,'scope':'Catalog/index/manifest audit; local field replay is separately recorded. Default metadata mode does not download bulk payload.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--retention-folder',type=Path);p.add_argument('--full-run',type=Path)
    a=p.parse_args();r=verify(a.evidence,a.repo)
    if a.retention_folder:r['retention']=retention(a.retention_folder,a.repo,a.full_run)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['verified_at','archive_members','stationary_cases','tail_passes','tail_failures','disposition']},indent=2))
