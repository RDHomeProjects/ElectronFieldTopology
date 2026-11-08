"""Recompute the temporal study from restored full-precision NPZ states, without evolution."""
import argparse,hashlib,json,sys,time
from pathlib import Path,PurePosixPath
from verify_assessment import verify,stamp,need,close,sha,RUN

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--repo',type=Path,required=True);a.add_argument('--run',type=Path,required=True);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--manifest',type=Path,default=Path(__file__).with_name('release-manifest.json'));a.add_argument('--output',type=Path,required=True);x=a.parse_args();sys.path.insert(0,str(x.repo.resolve()/'src'))
 import numpy as np
 import scipy
 from electron_field_topology.sf_time import Grid,diagnostics,densities,retract,acceleration
 from electron_field_topology.sf_time_run import state_sha,canonical_sha,MODEL,SCHEME
 from electron_field_topology.sf_q1_metrics import measure
 from electron_field_topology.sf_motion_metrics import evaluate
 from electron_field_topology.sf_temporal import coast_reference,own_comoving
 from electron_field_topology.sf_temporal_metrics import observed_order,geodesic_control
 from electron_field_topology.sf_boost_study import rate_metrics
 from electron_field_topology.skyrme import K,NORTH
 clock=time.monotonic();verified=verify(x.evidence,x.repo);c=json.loads((x.run/'campaign.json').read_text());p=json.loads((x.run/'plan.json').read_text());need(c['record_id']==RUN,'Unexpected restored run')
 numerical=0;worst={}
 def compare(got,want,path=''):
  nonlocal numerical
  if isinstance(want,dict):
   for k,v in want.items():
    if k not in {'recorded_at','scope','reference_label','topology_scope'}:compare(got[k],v,path+'/'+k)
  elif isinstance(want,list):
   need(len(got)==len(want),'List length differs '+path)
   for i,(v,w) in enumerate(zip(got,want)):compare(v,w,path+'/'+str(i))
  elif isinstance(want,bool):need(bool(got)==want,'Boolean differs '+path)
  elif isinstance(want,(int,float)):
   close(float(got),float(want),rel=1e-8,abs=1e-11);numerical+=1;worst[path.split('/')[-1]]=max(worst.get(path.split('/')[-1],0),abs(float(got)-float(want)))
  else:need(got==want,'Metadata differs '+path)
 def log(message,**d):print(json.dumps({'recorded_at':stamp(),'message':message,**d}),flush=True)
 def local(old):
  parts=PurePosixPath(old).parts;need(parts.count(RUN)==1 and '..' not in parts,'Unrecognized archived path');return x.run/Path(*parts[parts.index(RUN)+1:])
 def load(path):
  with np.load(path,allow_pickle=False) as z:return z['field'].copy(),z['field_rate'].copy()
 def independent(n,v,g):
  # Explicit sigma+two-form energy and kinetic contractions, independent of sf_time.densities/currents.
  u=n-NORTH;ds=[];sigma=np.zeros(g.shape)
  for axis,h in enumerate(g.spacing):
   pads=[(0,0)]*4;pads[axis]=(2,2);ext=np.pad(u,pads);indices=np.arange(g.shape[axis])+2
   at=lambda offset:np.take(ext,indices+offset,axis=axis)
   d=(at(-2)-8*at(-1)+8*at(1)-at(2))/(12*h);ds.append(d)
   plus=at(1);minus=at(-1);sigma+=.5*np.sum(((plus-u)/h)**2+((u-minus)/h)**2,axis=-1)+(h*h/12)*np.sum(((plus-2*u+minus)/(h*h))**2,axis=-1)
  e2=sum(np.sum(d*d,axis=-1) for d in ds);e4=sum(np.sum(np.cross(ds[i],ds[j])**2,axis=-1) for i,j in [(0,1),(0,2),(1,2)])
  kinetic=np.sum(v*v,axis=-1)+sum(np.sum(np.cross(v,d)**2,axis=-1) for d in ds)
  e=K*(kinetic+e2+e4);ham=K*(kinetic+sigma+e4);mom=2*((1+e2)[...,None]*v-sum(d*np.sum(v*d,axis=-1)[...,None] for d in ds))
  dv=float(np.prod(g.spacing));energy=float(np.sum(e)*dv);points=g.points();shell=np.any(abs(points)>=np.asarray(g.lengths)/2-2.,axis=-1)
  return {'continuum_energy':energy,'energy':float(np.sum(ham)*dv),'momentum':[-K*float(np.sum(mom*d)*dv) for d in ds],'centroid':(np.sum(points*e[...,None],axis=(0,1,2))*dv/energy).tolist(),'tail_fraction':float(np.sum(e[shell])*dv/energy),'shell_energy':float(np.sum(e[shell])*dv)}
 def difference(a,av,b,bv,count=None):
  if count:
   sl=tuple(slice((s-count)//2,(s+count)//2) for s in a.shape[:3]);a,av,b,bv=a[sl],av[sl],b[sl],bv[sl]
  diff=a-b;vd=av-bv
  return {'field_relative_l2':float(np.sqrt(np.sum(diff*diff))/max(np.sqrt(np.sum((b-NORTH)**2)),1e-30)),'rate_relative_l2':float(np.sqrt(np.sum(vd*vd))/max(np.sqrt(np.sum(bv*bv)),1e-30)),'combined_absolute_rms':float(np.sqrt(np.mean(diff*diff+vd*vd)))}
 manifest=json.loads(x.manifest.read_text());log('Authenticating all restored payload members',count=len(manifest['files']));filecount=0
 for f in manifest['files']:
  rp=PurePosixPath(f['archive_path']);need(rp.parts[0]=='files' and '..' not in rp.parts,'Unsafe manifest path');path=x.run/Path(*rp.parts[1:]);need(path.stat().st_size==f['size'] and sha(path)==f['sha256'],'Restored file changed '+str(path));filecount+=1
 npzrows=[];states=set();log('Checking all NPZ model/state/constraint records')
 for f in manifest['files']:
  if not f['archive_path'].endswith('.npz'):continue
  rp=Path(f['archive_path']).relative_to('files');path=x.run/rp
  if rp.parts[0]=='rest':r=c['domains'][rp.parts[1]];g=Grid((r['nodes'],)*3,(r['length'],)*3,'fixed');mf=json.loads((path.parent/'manifest.json').read_text());cfg=canonical_sha(r['relax_config']);model='rest'
  else:r=c['cases'][rp.parts[1]];phy=r['physical'];g=Grid(tuple(phy['grid']),tuple(phy['lengths']),'fixed');mf=json.loads((local(r['attempts'][0])/'manifest.json').read_text());cfg=canonical_sha(phy);model=r['model']
  with np.load(path,allow_pickle=False) as z:
   n=z['field'].copy();v=z['field_rate'].copy();need(n.dtype==v.dtype==np.float64 and n.shape==v.shape==g.shape+(3,) and np.isfinite(n).all() and np.isfinite(v).all(),'Invalid NPZ field');need(str(z['model_id'])==MODEL and str(z['scheme'])==SCHEME,'NPZ model differs')
   state=state_sha(n,v);need(np.max(abs(np.sum(n*n,axis=-1)-1))<1e-10 and np.max(abs(np.sum(n*v,axis=-1)))<1e-10 and np.max(abs(n[g.fixed_mask()]-NORTH))==0 and np.max(abs(v[g.fixed_mask()]))==0,'NPZ constraints differ')
   if model=='rest':need(str(z['config_sha256'])==cfg and str(z['code_sha256'])==mf['code_sha256'] and float(z['h'])==g.spacing[0] and np.max(abs(v))==0,'Static checkpoint provenance differs')
   else:
    need(str(z['physics_sha256'])==cfg,'Moving checkpoint physics differs')
    if mf:need(str(z['code_sha256'])==mf['code_sha256'],'Moving numerical source differs')
    need(float(z['time'])==int(z['step'])*r['dt'],'Moving checkpoint time differs')
  npzrows.append({'path':str(rp),'sha256':f['sha256'],'state_sha256':state,'shape':list(g.shape)});states.add(state);del n,v
 rest={};independent_rows=[];restrows=[];warmstarts=[]
 for model in p['models']:
  key=c['selected_domains'][model['id']];r=c['domains'][key];folder=x.run/'rest'/key;g=Grid((r['nodes'],)*3,(r['length'],)*3,'fixed');n,v=load(folder/'latest.npz');need(state_sha(n,v)==r['rest_final']['state_sha256'],'Final rest state differs');log('Replaying stationary full field',model=model['id'])
  actual=measure(n,g,model['q'],p);compare(actual,r['rest_final'],'rest/'+key);ind=independent(n,v,g)
  for k,want in [('energy',actual['discrete_hamiltonian']),('continuum_energy',actual['continuum_energy']),('tail_fraction',actual['shell_fraction']),('shell_energy',actual['shell_energy'])]:close(ind[k],want)
  independent_rows.append({'case_id':key,'role':'rest',**ind});restrows.append({'domain_id':key,'metrics':actual});rest[model['id']]=(n,g)
  initial,_=load(folder/'initial.npz');src=p['sources'][model['source']];pad=(len(initial)-src['nodes'])//2;cropped=initial[pad:pad+src['nodes'],pad:pad+src['nodes'],pad:pad+src['nodes']].copy();source=json.loads((x.repo/src['published_run']/'campaign.json').read_text());expect=source['cases'][src['case_id']]['final']['state_sha256'];need(state_sha(cropped,np.zeros_like(cropped))==expect,'Original retained source embedding differs')
  outside=np.ones(initial.shape[:3],dtype=bool);outside[pad:pad+src['nodes'],pad:pad+src['nodes'],pad:pad+src['nodes']]=False;need(np.max(abs(initial[outside]-NORTH),initial=0)==0,'North-vacuum extension differs');warmstarts.append({'model':model['id'],'source_state_sha256':expect,'initial_embedding_exact':True});del initial,cropped,v
 case_rows=[];translation_controls=[]
 for model in p['models']:
  nrest,rg=rest[model['id']];family=[r for r in c['cases'].values() if r['model']==model['id']];first=family[0];g=Grid(tuple(first['physical']['grid']),tuple(first['physical']['lengths']),'fixed');n0,v0=load(x.run/'cases'/first['id']/'admitted.npz');firsthist=json.loads((x.run/'cases'/first['id']/'history-combined.json').read_text());log('Independent initial moving energy/current replay',model=model['id']);initial_ind=independent(n0,v0,g)
  for name in ['energy','continuum_energy','momentum','centroid']:compare(initial_ind[name],firsthist[0][name],'initial/'+name)
  compare(rate_metrics(n0,v0,g,p['beta'],model['axis'],p['shell_width']),c['domains'][c['selected_domains'][model['id']]]['admission']['raw_transport_baseline'],'transport')
  independent_rows.append({'case_id':first['id'],'role':'moving_initial',**initial_ind})
  coast=[]
  for t in [0.,.5,1.]:
   nn,vv=coast_reference(nrest,rg,g,p['beta'],model['axis'],t);diag=diagnostics(nn,vv,g);coast.append({'time':t,'centroid':diag['centroid'],'continuum_energy':diag['continuum_energy']});del nn,vv
  velocity=(np.asarray(coast[-1]['centroid'])-coast[0]['centroid'])/1.;translation_controls.append({'model':model['id'],'coasting_reference_samples':coast,'known_coasting_centroid_velocity':velocity.tolist(),'coasting_speed_relative_error':float(np.linalg.norm(velocity-np.eye(3)[model['axis']]*p['beta'])/p['beta']),'scope':'Kinematic projected-cubic reference sampled on the same box; this reference is not evolved by the lattice PDE.'})
  for r in family:
   key=r['id'];log('Recomputing final full-field motion measurements',case_id=key);n,v=load(local(r['final_checkpoint']));need(state_sha(n,v)==r['final_state_sha256'],'Final full state differs');hist=json.loads((x.run/'cases'/key/'history-combined.json').read_text());got=evaluate(hist,n,v,g,nrest,rg.spacing[0],p['beta'],model['axis'],model['q'],p['shell_width'],p['limits']);compare(got,r['assessment']['legacy_motion'],'final/'+key)
   diag=diagnostics(n,v,g)
   for name in ['energy','continuum_energy','momentum','centroid','rms_radius','unit_error','tangency_error']:compare(diag[name],hist[-1][name],key+'/'+name)
   ind=independent(n,v,g)
   for name in ['energy','continuum_energy','momentum','centroid']:compare(ind[name],diag[name],key+'/independent/'+name)
   close(ind['tail_fraction'],got['final']['boundary_shell_energy_fraction']);independent_rows.append({'case_id':key,'role':'moving_final',**ind})
   ref,_=coast_reference(nrest,rg,g,p['beta'],model['axis'],1.);from electron_field_topology.sf_reconstruction import phase_comparison
   compare(phase_comparison(n,ref),r['assessment']['projected_cubic_coast_reference'],'cubic_reference/'+key);compare(own_comoving(n,n0,g,p['beta'],model['axis'],1.,p['fixed_comoving_half_width']),r['assessment']['own_admitted_comoving'],'own_comoving/'+key)
   case_rows.append({'case_id':key,'replayed_motion':got,'independent_density':ind});del n,v,ref
  del n0,v0
 comparisons=[];recorded=json.loads((x.run/'temporal-comparisons.json').read_text())['rows']
 def at(r,t):
  for old in reversed(r['attempts']):
   ap=local(old)
   for s in json.loads((ap/'snapshots.json').read_text()):
    if abs(s['time']-t)<1e-12:
     path=local(s['path']);need(sha(path)==s['sha256'],'Snapshot changed');n,v=load(path);need(state_sha(n,v)==s['state_sha256'],'Snapshot full state differs');return n,v
  raise ValueError('Missing matched-time snapshot')
 for model in p['models']:
  key=c['selected_domains'][model['id']];rows=[c['cases'][key+f'-dt{dt:g}'] for dt in p['time_steps']];need(len({r['initial_state_sha256'] for r in rows})==1,'Family initial states differ')
  for t in p['comparison_times']:
   log('Recomputing matched-time field/rate differences',model=model['id'],time=t);a,av=at(rows[0],t);b,bv=at(rows[1],t);d,dv=at(rows[2],t);item={'model':model['id'],'domain_id':key,'time':t}
   for region,count in [('original_central_73',73),('whole_lab_grid',None)]:
    ab=difference(a,av,b,bv,count);bc=difference(b,bv,d,dv,count);ac=difference(a,av,d,dv,count);item[region]={'coarse_medium':ab,'medium_fine':bc,'coarse_fine':ac,'field_order':observed_order(ab['field_relative_l2'],bc['field_relative_l2']),'rate_order':observed_order(ab['rate_relative_l2'],bc['rate_relative_l2'])}
   old=next(r for r in recorded if r['model']==model['id'] and r['time']==t)
   for pair in ['coarse_medium','medium_fine','coarse_fine']:
    for k,value in item['original_central_73'][pair].items():close(value,old[pair][k],rel=1e-8,abs=1e-18)
   for order in ['field_order','rate_order']:
    val=item['original_central_73'][order]['order'];want=old[order]['order'];need((val is None)==(want is None),'Order-floor decision differs')
    if val is not None:close(val,want,rel=1e-6,abs=1e-7)
   comparisons.append(item);del a,av,b,bv,d,dv
 control=geodesic_control();need(control['passed'],'Closed-form temporal control failed')
 result={'replayed_at':stamp(),'run_id':RUN,'full_payload_files_verified':filecount,'npz_files_verified':len(npzrows),'unique_field_rate_states':len(states),'npz':npzrows,'warm_start_embedding':warmstarts,'stationary_replay':restrows,'case_replay':case_rows,'independent_density_evaluations':independent_rows,'temporal_comparisons_recomputed':comparisons,'translation_reference_controls':translation_controls,'geodesic_control':control,'numeric_scalars_compared':numerical,'maximum_absolute_error_by_scalar':worst,'wall_seconds':time.monotonic()-clock,'environment':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__},'scope':'Read-only full-field replay, explicit independent D4 energy/current contractions, matched-time central/whole-box refinements and kinematic centroid controls. No new optimization or physical-time trajectory; the same model kernels remain unchanged.'}
 x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');log('Full-field analysis complete',files=filecount,npz=len(npzrows),states=len(states),wall_seconds=result['wall_seconds'])
if __name__=='__main__':main()
