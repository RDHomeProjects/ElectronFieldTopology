"""Pure array diagnostics and descriptive chronological trend fitting."""
import numpy as np

def spatial_summary(n,raw,spacing,fixed,old_state=None):
 from scipy.fft import dstn
 projected=raw-n*np.sum(n*raw,axis=-1,keepdims=True);projected[fixed]=0
 magnitude=np.linalg.norm(projected,axis=-1);active=~fixed;peak=np.unravel_index(np.argmax(magnitude),magnitude.shape)
 edge=np.minimum.reduce([np.minimum(np.arange(v),np.arange(v)[::-1]).reshape(tuple(v if i==j else 1 for i in range(3)))*spacing[j]+np.zeros(magnitude.shape) for j,v in enumerate(magnitude.shape)])
 shell=active&(edge<=2.0);core=active&~shell;power=magnitude**2;total=float(power.sum())
 part=projected[2:-2,2:-2,2:-2];spectrum=dstn(part,axes=(0,1,2),type=1,norm='ortho');frequency=np.zeros(part.shape[:3],bool)
 for axis,count in enumerate(part.shape[:3]):frequency|=(np.arange(count).reshape(tuple(count if i==axis else 1 for i in range(3)))>=.75*count)
 spectral_power=np.sum(spectrum**2,axis=-1)
 report={'projected_raw_gradient_max':float(magnitude.max()),'projected_raw_gradient_rms_active':float(np.sqrt(np.mean(power[active]))),'peak_index':[int(v) for v in peak],'peak_position':[float((i-(s-1)/2)*h) for i,s,h in zip(peak,magnitude.shape,spacing)],'peak_boundary_distance':float(edge[peak]),'gradient_power_fraction_shell_width2':float(power[shell].sum()/max(total,1e-300)),'gradient_power_fraction_core':float(power[core].sum()/max(total,1e-300)),'high_frequency_DST_power_fraction':float(spectral_power[frequency].sum()/max(float(spectral_power.sum()),1e-300)),'scope':'Projected raw static energy gradient; not the model acceleration field. High-frequency power is descriptive, not a proven numerical floor.'}
 if old_state:
  report['optimizer']={k:old_state[k] for k in ['iteration','alpha']}
  report['optimizer']['at_periodic_200_step_restart']=old_state['iteration']%200==0
  for k in ['old_g','old_z','direction']:
   a=old_state.get(k);report['optimizer'][k+'_present']=a is not None
   if a is not None:
    flat=a.ravel();grad=projected.ravel();report['optimizer'][k+'_norm']=float(np.linalg.norm(flat));report['optimizer'][k+'_cos_current_raw_gradient']=float(np.dot(flat,grad)/max(np.linalg.norm(flat)*np.linalg.norm(grad),1e-300))
 return report,magnitude

def curve_fits(history):
 out={}
 for metric,gate in [('relative_force_l2',1e-4),('acceleration_max',1e-3)]:
  h=[v for v in history if v[metric]>0];x=np.array([v['iteration'] for v in h],float);y=np.array([v[metric] for v in h],float)
  if len(x)<6:out[metric]={'status':'insufficient observations'};continue
  split=max(4,int(.7*len(x)));split=min(split,len(x)-1);origin=float(x[0]);scale=max(float(x[split-1]-x[0]),1);z=(x-origin)/scale;models=[]
  for name,degree in [('constant',0),('linear',1),('quadratic',2),('exponential',1)]:
   yy=np.log(y) if name=='exponential' else y;c=np.polynomial.polynomial.polyfit(z[:split],yy[:split],degree);pred=np.polynomial.polynomial.polyval(z[split:],c)
   if name=='exponential':pred=np.exp(np.clip(pred,-700,700))
   rmse=float(np.sqrt(np.mean((pred-y[split:])**2)));models.append({'model':name,'coefficients':c.tolist(),'origin':origin,'scale':scale,'holdout_RMSE':rmse,'normalized_holdout_RMSE':rmse/float(np.mean(y[split:])),'negative_prediction':bool((pred<0).any())})
  out[metric]={'models':sorted(models,key=lambda v:v['holdout_RMSE']),'train_count':split,'holdout_count':len(x)-split,'scope':'Retrospective chronological holdout on correlated observations; descriptive only, no automated gate crossing or budget extension'}
 return out
