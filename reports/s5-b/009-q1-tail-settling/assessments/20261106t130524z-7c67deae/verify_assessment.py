"""Read-only S5-B-009 compact integrity, scalar and stopping-policy replay. Apache-2.0."""
import argparse,hashlib,json,math,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
RUN='20261105t212644z-103ef9f4'
SOURCE='a8249de8eee6f91fd217c028e80dc8edf0ea3acc'
EVIDENCE='5cc3460d8fa9ddeb6525757ccebfad471088ea6103e248aaa2198a8f24beef27'
KEYS=['q1-n127-L20.16','q1-n139-L22.08']
def stamp():
 t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(x,message):
 if not x:raise ValueError(message)
def close(a,b):need(math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-11),f'Numeric mismatch: {a} != {b}')
def admitted(m,p):return m['relative_force_l2']<=p['relative_force_l2'] and m['acceleration_max']<=p['acceleration_max'] and abs(abs(m['hopf_integral'])-1)<=p['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<1e-10

def stable(rows,p):
 regular=[r for r in rows if r['regular_observation']];k=p['stable_intervals']
 if len(regular)<k+1:return False
 last=regular[-k-1:]
 return all(b['iteration']-a['iteration']==p['observe_every'] and all(isinstance(b.get(key),(float,int)) and math.isfinite(b[key]) and b[key]<=p[key] for key in ['tail_fraction_change','shell_energy_change','core_field_relative_change','hamiltonian_relative_change']) for a,b in zip(last,last[1:]))

def verify(evidence,repo=None):
 need(sha(evidence)==EVIDENCE,'Compact ZIP SHA-256 differs')
 with zipfile.ZipFile(evidence) as z:
  names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Duplicate/corrupt archive member')
  for name in names:need(not Path(name).is_absolute() and '..' not in Path(name).parts,'Unsafe compact member')
  ledger=json.loads(z.read('evidence-hashes.json'))['sha256'];need(set(names)==set(ledger)|{'evidence-hashes.json'},'Incomplete member coverage')
  for n,h in ledger.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Payload digest mismatch: '+n)
  c=json.loads(z.read('campaign.json'));p=json.loads(z.read('plan.json'));pairs=json.loads(z.read('comparisons.json'))
  need(c['record_id']==RUN and c['source_commit']==SOURCE,'Run/source identity differs');need(list(c['cases'])==KEYS,'Paired coverage differs')
  need(c['status']=='complete_with_unresolved_pending_review','Native completion label changed')
  need(p['tail_fraction_limit']==.001 and p['shell_width']==2. and p['spacing']==.16,'Original shell convention differs')
  need(hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()==c['config_sha256'],'Plan hash differs')
  if repo:
   for n,h in c['source_sha256'].items():need(sha(Path(repo)/'src/electron_field_topology'/n)==h,'Native numerical source differs: '+n)
   canonical=Path(repo)/f'reports/s5-b/009-q1-tail-settling/runs/{RUN}'
   need(sha(canonical/'evidence.zip')==EVIDENCE,'Git-hosted ZIP differs')
  rows=[]
  for key,r in c['cases'].items():
   result=json.loads(z.read(f'readmission/{key}/result.json'));obs=json.loads(z.read(f'readmission/{key}/observations.json'));h=json.loads(z.read(f'readmission/{key}/history.json'))
   need(result==r['result'],'Case/result differs');need(result['reason']=='Armijo search stalled' and result['status']=='stationarity_unresolved','Stop reason/status differs')
   f=r['final'];frac=f['shell_energy']/f['continuum_energy'];close(frac,f['shell_fraction']);need((frac<=p['tail_fraction_limit'])==f['tail_gate_pass'],'Tail flag differs')
   force=admitted(f['stationarity'],p['readmission']);need(force==f['preparation_stationarity_pass'],'Strict endpoint flag differs')
   need(obs[-1]['iteration']==result['iterations'] and not obs[-1]['regular_observation'],'Irregular final observation label differs')
   for x in obs:
    close(x['shell_fraction'],x['shell_energy']/x['continuum_energy']);need(x['regular_observation']==(x['iteration']%100==0),'Regular observation flag differs')
    need(admitted(x['stationarity'],p['readmission'])==x['preparation_stationarity_pass'],'Observation force flag differs')
   ends=[x for x in h if 'optimizer_message' in x];need(len(ends)==3,'Pass-ending coverage differs')
   need(all(abs(b['energy']-a['energy'])/a['energy']<p['readmission']['stagnation_relative_energy'] for a,b in zip(ends,ends[1:])),'Declared stagnant-pass condition differs')
   rows.append({'case_id':key,'iterations':result['iterations'],'reason':result['reason'],'native_status':result['status'],'tail_percent':100*frac,'tail_gate_pass':f['tail_gate_pass'],'strict_endpoint_stationarity_pass':force,'three_regular_intervals_stable':stable(obs,p),'final_observation_regular':obs[-1]['regular_observation'],'prescribed_settling_pass':force and stable(obs,p) and obs[-1]['regular_observation'],'pass_end_iterations':[x['iteration'] for x in ends],
    'final_relative_force':f['stationarity']['relative_force_l2'],'final_acceleration_max':f['stationarity']['acceleration_max'],'final_hamiltonian':f['discrete_hamiltonian'],'source_core_relative_change':obs[-1].get('core_field_relative_change')})
  for region in pairs['regions']:need(region['field_relative_l2']>0 and region['density_relative_l1']>0,'Domain differences unexpectedly changed')
  return {'verified_at':stamp(),'run_id':RUN,'source_commit':SOURCE,'evidence_sha256':EVIDENCE,'archive_members':len(names),'payload_hashes_verified':len(ledger),'native_source_files_verified':len(c['source_sha256']) if repo else 0,'cases':rows,'domain_regions':pairs['regions'],
    'disposition':'Q1 L20.16 tail failure retained; L22.08 shell and strict endpoint pass with stable preceding intervals, prescribed regular-endpoint settling certificate unmet; domain sensitivity remains',
    'scope':'Compact hashes and recorded scalar/controller logic replayed. No optimization path or physical-time evolution rerun; full fields require separate replay.'}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--repo',type=Path);a.add_argument('--output',type=Path,required=True);v=a.parse_args();r=verify(v.evidence,v.repo);v.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['verified_at','archive_members','payload_hashes_verified','disposition']},indent=2))
