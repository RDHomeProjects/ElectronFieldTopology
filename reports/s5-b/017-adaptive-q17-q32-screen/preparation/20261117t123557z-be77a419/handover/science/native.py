import shutil,subprocess,uuid
from pathlib import Path
import numpy as np
from common import ROOT,load,save,sha,stamp,log,need
from .numeric import metrics,stationary

def read_field(path,anchor,key='field'):
 need(sha(path)==anchor.get('sha256',anchor.get('checkpoint_sha256')),'Authenticated field hash differs: '+str(path))
 with np.load(path,allow_pickle=False) as z:
  n=z[key].copy();need(n.dtype==np.float64 and n.shape==(anchor['nodes'],)*3+(3,) and np.isfinite(n).all(),'Native field precision/geometry differs')
  if 'expected_q' in z:need(int(z['expected_q'])==anchor.get('q',2),'Native Q metadata differs')
  if 'h' in z:need(abs(float(z['h'])-anchor.get('spacing',anchor['length']/(anchor['nodes']-1)))<1e-12,'Native spacing differs')
 return n

def control(repo,out,p):
 from electron_field_topology.sf_time import Grid
 a=load(ROOT/'ANCHORS.json')['Q2'];source=Path.home()/'ElectronFieldTopology-repository-admin/artifacts/s5-b/010-intermediate-q-survey/20261109t134425z-89d28344'/a['checkpoint']
 need(source.is_file(),'Required retained Q2 control absent: '+str(source))
 n=read_field(source,a);g=Grid((a['nodes'],)*3,(a['length'],)*3,'fixed');m=metrics(n,g,p)
 for k in ['energy','relative_force_l2','acceleration_max','hopf_integral']:
  need(np.isclose(m[k],a['expected_metrics'][k],rtol=1e-6,atol=1e-10),'Q2 measured reference metric differs: '+k)
 need(stationary(m,2,p),'Q2 instrument control is not strictly admitted')
 folder=out/'sources';folder.mkdir(parents=True,exist_ok=True);target=folder/'q2-reference.npz'
 if not target.exists():shutil.copy2(source,target)
 need(sha(target)==a['checkpoint_sha256'],'Copied Q2 control differs')
 r={'recorded_at':stamp(),'status':'control_pass','source':str(source),'sha256':sha(source),'metrics':m,'nodes':a['nodes'],'length':a['length'],'q':2,'field':str(target)};save(out/'Q2-CONTROL.json',r);return r

def bridge(repo,out,p,allow_restore=True):
 from electron_field_topology.sf_time import Grid
 from electron_field_topology.skyrme import Energy,K
 anchors=load(ROOT/'ANCHORS.json');home=Path.home();chosen=None
 for label in ['Q22','Q17']:
  a=anchors[label];paths=[home/a['path']]
  if label=='Q17':
   paths.extend([home/'ElectronFieldTopology-repository-admin/artifacts/s5-b/007-higher-q-motion/20261108t022631z-7e649031/sources/q17.npz',out/'restored/extra/r001/20261108t022631z-7e649031/sources/q17.npz'])
   for folder in sorted(home.glob('EFT-restored*')):paths.append(folder/'extra/r001/20261108t022631z-7e649031/sources/q17.npz')
   for folder in sorted(out.glob('restored*')):paths.append(folder/'extra/r001/20261108t022631z-7e649031/sources/q17.npz')
  for path in paths:
   if path.is_file() and sha(path)==a['sha256']:chosen=(label,a,path);break
  if chosen:break
 if chosen is None and allow_restore:
  destination=out/'restored'
  if destination.exists():destination=out/('restored-'+uuid.uuid4().hex[:8]);log('Previous partial restore preserved; using a new recovery directory',destination=str(destination))
  catalog='data/archives/20261108t130946z-bb3606a9/CATALOG.json'
  argv=['python3','scripts/workstation_archive.py','restore','--catalog',catalog,'--destination',str(destination),'--roots','r001']
  log('Restoring existing verified Q17 archive locally; no new solve',argv=argv,payload_gib=1.41)
  subprocess.run(argv,cwd=repo,check=True)
  path=destination/'extra/r001/20261108t022631z-7e649031/sources/q17.npz'
  need(path.is_file(),'Restore completed without declared native Q17 source');chosen=('Q17',anchors['Q17'],path)
 if chosen is None:
  r={'recorded_at':stamp(),'status':'explicitly_deferred_native_field_unavailable','reason':'No authenticated native Q22/Q17 field; no fresh seed substituted','relaxation_steps':0};save(out/'NATIVE-BRIDGE.json',r);return r
 label,a,source=chosen;n=read_field(source,a);g=Grid((a['nodes'],)*3,(a['length'],)*3,'fixed')
 need(np.max(abs(n[g.fixed_mask()]-[0,0,1]))<1e-12,'Native field does not satisfy held layers; no projection permitted')
 cell=Energy(a['nodes'],a['spacing'],out/'native-cell-build',method='cell');parts,grad=cell.evaluate(n);grad-=n*np.sum(n*grad,axis=-1,keepdims=True);grad[g.fixed_mask()]=0
 energy=float(sum(parts));residual=float(np.sqrt(np.mean(grad[2:-2,2:-2,2:-2]**2))/(K*a['spacing']**3))
 need(np.isclose(energy,a['energy'],rtol=1e-8,atol=1e-10),'Native historical cell energy replay differs')
 need(np.isclose(residual,a['cpu_residual'],rtol=1e-5,atol=1e-10),'Native historical cell gradient replay differs')
 d4=metrics(n,g,p);target=out/'sources'/('native-'+label.lower()+'.npz');target.parent.mkdir(exist_ok=True)
 if not target.exists():shutil.copy2(source,target)
 r={'recorded_at':stamp(),'status':'native_operator_comparison_complete','field':label,'q':a['q'],'source':str(source),'source_sha256':sha(source),'shape':list(g.shape),'lengths':list(g.lengths),'spacing':list(g.spacing),'cell_energy':energy,'cell_tangent_gradient_component_rms':residual,'d4_metrics':d4,'d4_stationary':stationary(d4,a['q'],p),'field_resampled':False,'field_projected':False,'relaxation_steps':0,'scope':'Identical retained field bytes/grid/box; operator metrics have different definitions. Individual D4 failure does not block other families.'};save(out/'NATIVE-BRIDGE.json',r);return r
