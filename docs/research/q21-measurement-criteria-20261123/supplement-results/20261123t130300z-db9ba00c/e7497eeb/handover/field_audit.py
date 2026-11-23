"""Read-only native residuals and paper-style display surfaces; no stability claim."""
import gc,sys,time,math
from pathlib import Path
import numpy as np
from criteria_common import ROOT,need,save,sha,stamp,load
sys.path.insert(0,str(ROOT/'legacy'))
from diagnostics import tangent,masks
from evaluations import array_sha,gate_result,derivative_check

def distribution(v,regions,g,thresholds=()):
 square=np.einsum('...i,...i->...',v,v);mag=np.sqrt(square);total=float(square.sum());peak=np.unravel_index(int(np.argmax(square)),square.shape)
 out={'maximum_vector_magnitude':float(mag[peak]),'vector_rms':float(np.sqrt(square.mean())),'component_rms':float(np.sqrt(square.mean()/3)),'quantiles_vector_magnitude':{str(q):float(np.quantile(mag,q)) for q in [.5,.9,.95,.99,.999]},'peak_index':list(map(int,peak)),'peak_position':[float(-L/2+i*h) for L,i,h in zip(g.lengths,peak,g.spacing)],'regions':{}}
 for name,mask in regions.items():
  count=int(mask.sum());out['regions'][name]={'nodes':count,'node_fraction':count/square.size,'squared_residual_fraction':float(square[mask].sum()/max(total,1e-30)),'maximum_vector_magnitude':float(mag[mask].max()) if count else None,'vector_rms':float(np.sqrt(square[mask].mean())) if count else None,'above_threshold_fraction_of_region':{str(t):float(np.mean(mag[mask]>t)) if count else None for t in thresholds}}
 out['above_threshold_fraction_of_whole_grid']={str(t):float(np.mean(mag>t)) for t in thresholds};return out

def images(n,g,folder,label):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from mpl_toolkits.mplot3d.art3d import Poly3DCollection
 from electron_field_topology.sf_renderer import triangles
 stride=max(1,math.ceil((n.shape[0]-1)/64));display=n[::stride,::stride,::stride];start=-np.asarray(g.lengths)/2;spacing=np.asarray(g.spacing)*stride
 fig=plt.figure(figsize=(14,4.8));levels=[(-.8,'Sutcliffe tube convention'),(-.9,'Hietarinta–Salo inner surface'),(-.95,'Jennings tube convention')]
 geometry=[]
 for i,(level,title) in enumerate(levels):
  ax=fig.add_subplot(1,3,i+1,projection='3d');surface,colors=triangles(display[...,2],display[...,0],start,spacing,level);original_count=len(surface)
  if len(surface)>5000:indices=np.linspace(0,len(surface)-1,5000).astype(int);surface=surface[indices];colors=colors[indices]
  if len(surface):
   collection=Poly3DCollection(surface,facecolors=plt.get_cmap('coolwarm')((colors+1)/2),edgecolors='none',alpha=.92);ax.add_collection3d(collection)
  points=g.points();occupied=n[...,2]<-.5
  extent=max(2.,float(np.max(np.abs(points[occupied])))+1) if occupied.any() else 2.;del points
  for setter in (ax.set_xlim,ax.set_ylim,ax.set_zlim):setter(-extent,extent)
  ax.set_box_aspect((1,1,1));ax.view_init(24,-55);ax.set_title(title+'\n$n_3=$'+str(level),fontsize=10);ax.set_xlabel('x');ax.set_ylabel('y');ax.set_zlabel('z')
  geometry.append({'level':level,'display_stride':stride,'native_array_changed':False,'display_triangles_before_cap':original_count,'display_triangles_drawn':len(surface),'display_mesh_is_not_a_topology_certificate':True})
 now=stamp();fig.suptitle(label+' — native field; display sampling only',fontsize=12);fig.text(.01,.01,'UTC '+now['utc']+' | Melbourne '+now['melbourne']+'\nColors show n1; view surfaces do not identify a knot or establish stability.',fontsize=7);fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(folder/'author-surfaces.png',dpi=180);plt.close(fig)
 return geometry

def measure(n,g,folder,label,expected=None,draw=True,q=21):
 from electron_field_topology.sf_readmission import stationarity,static_value_gradient
 from electron_field_topology.sf_time import acceleration,sigma_terms,gradients
 from electron_field_topology.skyrme import K,NORTH
 from scipy.ndimage import label as components
 from evaluations import metrics
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);before=array_sha(n);clock=time.perf_counter();p=load(ROOT/'legacy/PLAN.json')['registered_gates']
 measured=metrics(n,g,p)
 if expected:
  for key in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']:
   need(np.isclose(measured[key],expected[key],rtol=1e-6,atol=1e-10),'Full-field replay differs for '+label+': '+key)
 metrics_seconds=time.perf_counter()-clock
 xyz,regions=masks(n,g);del xyz
 timer=time.perf_counter();energy,raw=static_value_gradient(n,g);force=tangent(-raw/(2*K*np.prod(g.spacing)),n,g);del raw
 fs=distribution(force,regions,g);del force;gc.collect();force_seconds=time.perf_counter()-timer
 timer=time.perf_counter();a=acceleration(n,np.zeros_like(n),g)[1];acc=distribution(a,regions,g,[.001,.01]);del a;gc.collect();acc_seconds=time.perf_counter()-timer
 timer=time.perf_counter();sigma,unused=sigma_terms(n,g);e2=float(K*np.prod(g.spacing)*sigma.sum());del sigma,unused;d=gradients(n-NORTH,g)
 e4=float(K*np.prod(g.spacing)*sum(np.sum(np.cross(d[...,i,:],d[...,j,:])**2) for i,j in [(0,1),(0,2),(1,2)]));del d;gc.collect()
 need(np.isclose(e2+e4,energy,rtol=1e-10,atol=1e-10),'Energy-component sum differs');levels=[]
 for threshold in [-.8,-.9,-.95]:
  mask=n[...,2]<threshold;count=int(mask.sum());_,number=components(mask);levels.append({'n3_less_than':threshold,'native_occupied_nodes':count,'occupied_volume':count*float(np.prod(g.spacing)),'six_neighbour_voxel_components':number,'not_knot_or_link_identification':True})
 component_seconds=time.perf_counter()-timer;drawn=images(n,g,folder,label) if draw else {'status':'not_requested_for_test'}
 need(array_sha(n)==before,'Read-only audit changed field bytes')
 record={'recorded_at':stamp(),'label':label,'source_array_sha256':before,'shape':list(n.shape),'lengths':list(g.lengths),'spacing':list(g.spacing),'metrics':measured,'gates':gate_result(measured,q,p),'force':fs,'acceleration':acc,'energy_components':{'nodal_sigma_e2':e2,'D4_skyrme_e4':e4,'sum':e2+e4,'continuum_inspired_virial_proxy':(e2-e4)/(e2+e4) if e2+e4 else None,'proxy_is_not_exact_fixed_lattice_scaling_derivative':True,'no_new_gate':True},'native_level_sets':levels,'display_surfaces':drawn,'timing_seconds':{'metric_replay':metrics_seconds,'force_distribution':force_seconds,'acceleration_distribution':acc_seconds,'components_and_level_sets':component_seconds,'total':time.perf_counter()-clock},'source_modified':False,'optimizer_attempts':0,'physical_time_steps':0}
 save(folder/'MEASUREMENTS.json',record);(folder/'REPORT.html').write_text('<!doctype html><meta charset="utf-8"><title>'+label+'</title><h1>'+label+'</h1><p>Read-only native measurements. Display surfaces are not knot identification or stability evidence.</p><p><a href="MEASUREMENTS.json">All measurements and timestamps</a></p>'+('<img style="max-width:100%" src="author-surfaces.png" alt="Author-style field surfaces">' if draw else '')+'\n');return record

def qualify_derivative(n,g,folder):
 result=derivative_check(n,g,{'epsilons':[.001,.0003,.0001],'rtol':.002,'atol':1e-7});save(Path(folder)/'DIRECTIONAL-DERIVATIVE.json',result);need(result['passed'],'Independent directional-derivative qualification failed');return result
