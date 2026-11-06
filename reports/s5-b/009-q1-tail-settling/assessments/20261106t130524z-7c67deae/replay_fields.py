"""Read-only NPZ diagnostic replay and separate NumPy energy/tail/region checks. Apache-2.0."""
import argparse,json,sys,time,hashlib
from pathlib import Path
from verify_assessment import verify,stamp,need,close,sha,RUN

def main():
 a=argparse.ArgumentParser();a.add_argument('--repo',type=Path,required=True);a.add_argument('--run',type=Path,required=True);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args()
 sys.path.insert(0,str(args.repo.resolve()/'src'))
 import numpy as np
 from electron_field_topology.sf_q1_metrics import measure
 from electron_field_topology.sf_time import Grid
 from electron_field_topology.sf_time_run import canonical_sha,state_sha,MODEL,SCHEME
 from electron_field_topology.skyrme import K,NORTH
 clock=time.monotonic();v=verify(args.evidence,args.repo);c=json.loads((args.run/'campaign.json').read_text());p=json.loads((args.run/'plan.json').read_text());cache={};rows=[];numeric=0;maximum={};finals={};starts={};regular_prev={}
 def compare(got,want,path=''):
  nonlocal numeric
  if isinstance(want,dict):
   for k,val in want.items():
    if k not in ['recorded_at','previous_preparation_stationarity_pass']:compare(got[k],val,path+'/'+k)
  elif isinstance(want,list):
   need(len(got)==len(want),'List length differs: '+path)
   for i,(x,y) in enumerate(zip(got,want)):compare(x,y,path+'/'+str(i))
  elif isinstance(want,bool):need(bool(got)==want,'Flag differs: '+path)
  elif isinstance(want,(int,float)):
   need(np.isfinite(got) and np.isclose(got,want,rtol=1e-8,atol=1e-11),'Numeric replay differs: '+path+f' {got} != {want}');numeric+=1;maximum[path.split('/')[-1]]=max(maximum.get(path.split('/')[-1],0),abs(float(got)-want))
  else:need(got==want,'Metadata differs: '+path)
 def independent_density(n,h):
  u=n-np.array([0.,0.,1.]);der=[];sigma=np.zeros(n.shape[:-1])
  for axis in range(3):
   pad=[(0,0)]*4;pad[axis]=(2,2);extended=np.pad(u,pad);idx=np.arange(n.shape[axis])+2
   der.append(sum(w*np.take(extended,idx+off,axis=axis) for off,w in [(-2,1.),(-1,-8.),(1,8.),(2,-1.)])/(12*h))
   plus=np.take(extended,idx+1,axis=axis);minus=np.take(extended,idx-1,axis=axis)
   sigma+=.5*np.sum(((plus-u)/h)**2+((u-minus)/h)**2,axis=-1)+(h*h/12)*np.sum(((plus-2*u+minus)/(h*h))**2,axis=-1)
  e2=sum(np.sum(d*d,axis=-1) for d in der);e4=sum(np.sum(np.cross(der[i],der[j])**2,axis=-1) for i,j in [(0,1),(0,2),(1,2)])
  return K*(e2+e4),float(K*np.sum(sigma+e4)*h**3)
 def region(na,ea,nb,eb,count):
  def sl(n):
   lo=(len(n)-count)//2;return (slice(lo,lo+count),)*3
  aa=na[sl(na)];bb=nb[sl(nb)];a=ea[sl(na)];b=eb[sl(nb)];norm=np.sqrt(np.sum((aa-NORTH)**2));energy=float(np.sum(a));delta=bb-aa
  return {'field_relative_l2':float(np.sqrt(np.sum(delta*delta))/norm),'field_absolute_rms':float(np.sqrt(np.mean(delta*delta))),'energy_relative_difference':abs(float(np.sum(b))-energy)/abs(energy),'density_relative_l1':float(np.sum(abs(b-a))/abs(energy))}
 for key,r in c['cases'].items():
  folder=args.run/'readmission'/key;g=Grid((r['nodes'],)*3,(r['length'],)*3,'fixed');obs=json.loads((folder/'observations.json').read_text());manifest=json.loads((folder/'manifest.json').read_text())
  states=[('initial.npz',r['initial'],0,r['initial_checkpoint_sha256'])]+[(x['snapshot'],x,x['iteration'],x['checkpoint_sha256']) for x in obs]+[('latest.npz',r['final'],r['result']['iterations'],r['final_checkpoint_sha256'])]
  for name,expected,it,digest in states:
   path=folder/name;need(sha(path)==digest,'Checkpoint file SHA differs: '+str(path))
   with np.load(path,allow_pickle=False) as d:
    n=d['field'].copy();rate=d['field_rate'].copy()
    need(n.dtype==rate.dtype==np.float64 and n.shape==rate.shape==g.shape+(3,) and np.isfinite(n).all() and np.max(abs(rate))==0,'Invalid full field/rate')
    need(str(d['model_id'])==MODEL and str(d['scheme'])==SCHEME and int(d['expected_q'])==1 and float(d['h'])==g.spacing[0],'NPZ model/grid differs')
    need(str(d['config_sha256'])==canonical_sha(r['relax_config']) and str(d['code_sha256'])==manifest['code_sha256'] and int(d['iteration'])==it,'NPZ provenance/iteration differs')
    need(np.max(abs(n[g.fixed_mask()]-NORTH))==0 and np.max(abs(np.sum(n*n,axis=-1)-1))<1e-10,'Full-field constraints differ')
   state=state_sha(n,rate);need(state==expected['state_sha256'],'Full field state SHA differs');del rate
   if state not in cache:
    print(json.dumps({'recorded_at':stamp(),'message':'Replaying unique field','case':key,'iteration':it}),flush=True)
    got=measure(n,g,1,p);e,ham=independent_density(n,g.spacing[0]);h=g.spacing[0];dv=h**3;axis=-r['length']/2+np.arange(r['nodes'])*h;shell=np.zeros(g.shape,dtype=bool)
    for j in range(3):
     shape=[1,1,1];shape[j]=r['nodes'];shell|=(abs(axis)>=r['length']/2-2).reshape(shape)
    energy=float(np.sum(e)*dv);se=float(np.sum(e[shell])*dv);frac=se/energy
    for x,y in [(energy,got['continuum_energy']),(ham,got['discrete_hamiltonian']),(se,got['shell_energy']),(frac,got['shell_fraction'])]:close(x,y)
    cache[state]={'metrics':got,'density':e,'independent':{'energy':energy,'hamiltonian':ham,'shell_energy':se,'tail_fraction':frac,'tail_abs_difference':abs(frac-got['shell_fraction']),'hamiltonian_abs_difference':abs(ham-got['discrete_hamiltonian'])}}
   got=cache[state]['metrics'];e=cache[state]['density'];subset={k:val for k,val in expected.items() if k in got};compare(got,subset)
   if name=='initial.npz':starts[key]=n.copy()
   if name=='latest.npz':finals[key]=(n.copy(),e)
   if name.startswith('observations/'):
    prev=regular_prev.get(key)
    if prev:
     pn,pe,pr=prev;own=region(pn,pe,n,e,73)
     for field,value in own.items():close(value,expected['previous_core_comparison'][field])
     close(abs(got['shell_fraction']-pr['shell_fraction']),expected['tail_fraction_change']);close(abs(got['shell_energy']-pr['shell_energy']),expected['shell_energy_change'])
    if expected['regular_observation']:regular_prev[key]=(n.copy(),e,got)
   rows.append({'case_id':key,'checkpoint':name,'iteration':it,'state_sha256':state,'sha256':digest,**cache[state]['independent']})
 source=starts['q1-n127-L20.16'];big=starts['q1-n139-L22.08'];ext=np.broadcast_to(NORTH,big.shape).copy();ext[6:-6,6:-6,6:-6]=source
 need(np.array_equal(big,ext),'Initial exact extension differs');need(state_sha(source,np.zeros_like(source))=='5d56a1586f7bae19c1ee90e208a096556ba3d226eddc1d2b870bee924fb7d832','Source state differs')
 pair=json.loads((args.run/'comparisons.json').read_text());na,ea=finals[pair['a']];nb,eb=finals[pair['b']];pairs=[]
 for r in pair['regions']:
  own=region(na,ea,nb,eb,r['common_nodes'])
  for k,value in own.items():close(value,r[k])
  pairs.append({'common_nodes':r['common_nodes'],**own})
 receipt={'replayed_at':stamp(),'run_id':RUN,'checkpoints_verified':len(rows),'unique_field_states_replayed':len(cache),'recorded_numeric_scalars_compared':numeric,'initial_embedding_bit_exact':True,'source_state_verified':True,'independent_energy_tail_evaluations':len(cache),'paired_regions_recomputed':len(pairs),'rows':rows,'pairs':pairs,'maximum_absolute_error_by_scalar':maximum,'wall_seconds':time.monotonic()-clock,'environment':{'python':sys.version,'numpy':np.__version__,'scipy':__import__('scipy').__version__},'scope':'Read-only diagnostic replay of eight unique fields in twelve NPZ files, plus separate NumPy D4 energy/tail/core computations. No optimizer or physical-time trajectory rerun; same-model diagnostic replay is not an independent physical validation.'}
 args.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:receipt[k] for k in ['replayed_at','checkpoints_verified','unique_field_states_replayed','recorded_numeric_scalars_compared','wall_seconds']},indent=2))
if __name__=='__main__':main()
