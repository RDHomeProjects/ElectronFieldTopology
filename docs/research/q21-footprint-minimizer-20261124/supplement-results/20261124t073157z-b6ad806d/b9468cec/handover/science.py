"""Read-only footprint curves and qualified local forecasts. No mesh evolution."""
import gc,math,time
import numpy as np
from common import ROOT,need,load,save,csv_write,stamp

def response_fits(history,plan):
    """Chronological holdout beats a last-value baseline; forecasts never certify admission."""
    rows=[r for r in history if r.get('accepted_updates') is not None]
    if len(rows)<plan['minimum_fit_points']:return {'qualified':False,'reason':'insufficient_measured_points','models':[]}
    rows=rows[-30:];x=np.array([r['accepted_updates'] for r in rows],float);x-=x[0]
    if len(set(x))!=len(x):return {'qualified':False,'reason':'duplicate_update_coordinates','models':[]}
    hold=max(3,len(x)//4);models=[];targets={k:np.array([r['metrics'][k] for r in rows],float) for k in ['relative_force_l2','acceleration_max']}
    for kind,degree in [('linear',1),('quadratic',2),('exponential',1)]:
        components={};qualified=True
        for key,y in targets.items():
            if np.any(y<=0):qualified=False;continue
            yy=np.log(y) if kind=='exponential' else y
            c=np.polyfit(x[:-hold],yy[:-hold],degree);pred=np.polyval(c,x[-hold:]);pred=np.exp(np.clip(pred,-700,700)) if kind=='exponential' else pred
            denom=max(float(np.sqrt(np.mean(y[-hold:]**2))),1e-30);rmse=float(np.sqrt(np.mean((pred-y[-hold:])**2))/denom)
            base=float(np.sqrt(np.mean((y[-hold:]-y[-hold-1])**2))/denom);skill=1-rmse/max(base,1e-30)
            c=np.polyfit(x,yy,degree);future=np.polyval(c,x[-1]+np.arange(1,21));future=np.exp(np.clip(future,-700,700)) if kind=='exponential' else future
            valid=bool(rmse<=plan['fit_holdout_relative_rmse_limit'] and skill>=plan['fit_min_skill'] and np.all(future>0))
            components[key]={'holdout_relative_rmse':rmse,'skill_vs_last_value':skill,'qualified':valid,'coefficients_highest_power_first':c.tolist(),'forecast_next_20':future.tolist()};qualified &= valid
        models.append({'model':kind,'qualified':bool(qualified and len(components)==2),'components':components})
    good=[m for m in models if m['qualified']]
    selected=min(good,key=lambda m:max(c['holdout_relative_rmse'] for c in m['components'].values())) if good else None
    return {'qualified':bool(selected),'models':models,'selected':selected,'x_origin_accepted_updates':rows[0]['accepted_updates'],'holdout_points':hold,'admission_inferred':False}

def next_batch(history,plan):
    if len(history)<11:return {'continue':False,'reason':'insufficient_recent_measurements','attempts':0}
    first,last=history[-11],history[-1];keys=['relative_force_l2','acceleration_max']
    gains={k:1-last['metrics'][k]/first['metrics'][k] for k in keys}
    fits=response_fits(history,plan)
    if min(gains.values())<plan['joint_recent_progress']:
        return {'continue':False,'reason':'recent_joint_progress_not_measured','attempts':0,'recent_gains':gains,'fits':fits}
    batch=plan['batch_min'];reason='measured_progress_short_validation_batch'
    if fits['qualified']:
        selected=fits['selected'];limits={'relative_force_l2':plan['registered_gates']['force_limit'],'acceleration_max':plan['registered_gates']['acceleration_limit']}
        predicted=[]
        for key in keys:
            values=selected['components'][key]['forecast_next_20'];hits=[i+1 for i,v in enumerate(values) if v<=limits[key]]
            predicted.append(hits[0] if hits else 20)
        batch=int(np.clip(max(predicted),plan['batch_min'],plan['batch_max']));reason='qualified_joint_curve_horizon'
    # Turning/noisy recent response shortens a forecast, never expands the ceiling.
    for key in keys:
        v=np.array([r['metrics'][key] for r in history[-6:]])
        if np.any(np.diff(v)>0) and np.any(np.diff(v)<0):batch=plan['batch_min'];reason+=';turning_response_shortened'
    return {'continue':True,'reason':reason,'attempts':batch,'recent_gains':gains,'fits':fits}

def patch_row(buffer,required,weights,axes,h):
    bounds=[]
    for a,(lo,hi) in zip(axes,required):
        bounds.append((max(0,int(np.searchsorted(a,lo-buffer,'left'))),min(len(a),int(np.searchsorted(a,hi+buffer,'right')))))
    sl=tuple(slice(a,b) for a,b in bounds);count=math.prod(b-a for a,b in bounds)
    row={'buffer':float(buffer),'nodes':int(count),'node_fraction':count/weights['energy'].size,'bounds_indices':bounds,'bounds_coordinates':[[float(a[lo]),float(a[hi-1])] for a,(lo,hi) in zip(axes,bounds)],'spacing':float(h)}
    for key,w in weights.items():row[key+'_capture_fraction']=float(w[sl].sum()/max(float(w.sum()),1e-300))
    # Face-adjacent band indicates a patch with substantial activity at its interface.
    interior=tuple(slice(min(b,a+2),max(a+2,b-2)) for a,b in bounds)
    for key,w in weights.items():row[key+'_interface_band_fraction']=float(max(0,w[sl].sum()-w[interior].sum())/max(w.sum(),1e-300))
    row['touches_outer_held_layers']=any(lo<2 or hi>len(a)-2 for a,(lo,hi) in zip(axes,bounds))
    row['two_to_one_coarse_cell_count_proxy']=count+(weights['energy'].size-count)/8
    row['proxy_ignores_buffers_overlap_operator_and_diagnostic_overhead']=True
    return row

def footprint(n,g,folder,label,stop=lambda:False):
    from electron_field_topology.sf_readmission import static_value_gradient
    from electron_field_topology.sf_time import densities,acceleration
    from electron_field_topology.skyrme import K
    from evaluations import array_sha,metrics,gate_result
    folder.mkdir(parents=True,exist_ok=True);before=array_sha(n);plan=load(ROOT/'PLAN.json');clock=time.perf_counter()
    m=metrics(n,g,plan['registered_gates']);energy= densities(n,np.zeros_like(n),g)['hamiltonian_density']
    need(np.isclose(float(energy.sum()*np.prod(g.spacing)),m['energy'],rtol=1e-10,atol=1e-10),'Footprint density does not integrate to the native energy')
    _,raw=static_value_gradient(n,g)
    force=-raw/(2*K*np.prod(g.spacing));force-=n*np.sum(n*force,axis=-1,keepdims=True);force[g.fixed_mask()]=0;del raw
    fs=np.einsum('...i,...i->...',force,force);del force;gc.collect();a=acceleration(n,np.zeros_like(n),g)[1];aa=np.einsum('...i,...i->...',a,a);del a;gc.collect()
    axes=[-L/2+np.arange(N)*h for L,N,h in zip(g.lengths,g.shape,g.spacing)]
    core=n[...,2]<0;need(core.any(),'No n3<0 core; automatic patch selection unresolved')
    # Include gradient, energy and residual peaks; energy alone must not set the patch.
    required=core.copy()
    angular=np.zeros(g.shape,dtype=float)
    for axis,h in enumerate(g.spacing):
        left=[slice(None)]*3;right=list(left);left[axis]=slice(None,-1);right[axis]=slice(1,None)
        jump=np.sum((n[tuple(left)]-n[tuple(right)])**2,axis=-1)/h**2
        angular[tuple(left)]+=jump*.5;angular[tuple(right)]+=jump*.5
    for w in [energy,fs,aa,angular]:required[np.unravel_index(np.argmax(w),w.shape)]=True
    coords=np.where(required);bounds=[(float(axes[i][v.min()]),float(axes[i][v.max()])) for i,v in enumerate(coords)]
    weights={'energy':energy,'squared_force':fs,'squared_acceleration':aa,'angular_variation':angular};rows={}
    def sample(b):
        key=round(float(b),9)
        if key not in rows:rows[key]=patch_row(key,bounds,weights,axes,g.spacing[0])
    for b in plan['mapping_initial_buffers']:sample(b)
    # Add samples where capture changes rapidly; resolve the target crossing by bisection.
    for _ in range(3):
        keys=sorted(rows);add=[]
        for lo,hi in zip(keys,keys[1:]):
            low,high=rows[lo],rows[hi]
            change=max(high[k+'_capture_fraction']-low[k+'_capture_fraction'] for k in weights)
            if hi-lo>2*g.spacing[0] and change>.002:add.append((lo+hi)/2)
        for b in add:
            if len(rows)<plan['maximum_footprint_probes_per_field']-8:sample(b)
    target=plan['capture_target']
    def captures(r):return min(r[k+'_capture_fraction'] for k in weights)
    for _ in range(8):
        keys=sorted(rows);pairs=[(lo,hi) for lo,hi in zip(keys,keys[1:]) if captures(rows[lo])<target<=captures(rows[hi])]
        if not pairs:break
        lo,hi=pairs[0]
        if hi-lo<=g.spacing[0]:break
        sample((lo+hi)/2)
    ordered=[rows[k] for k in sorted(rows)];eligible=[r for r in ordered if captures(r)>=target and not r['touches_outer_held_layers']]
    proposed=min(eligible,key=lambda r:r['nodes']) if eligible else None
    flat=[]
    for r in ordered:flat.append({k:(str(v) if isinstance(v,(list,dict)) else v) for k,v in r.items()})
    csv_write(folder/'PATCH-CAPTURE.csv',flat)
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,5))
    for key in weights:ax.plot([r['buffer'] for r in ordered],[r[key+'_capture_fraction'] for r in ordered],'.-',label=key)
    ax.axhline(target,color='black',ls='--',label='exploratory capture target');ax.set(xlabel='Buffer beyond core/hotspot bounding box (model units)',ylabel='Fraction captured',title=label+' — measured footprint curves');ax.legend();fig.tight_layout();fig.savefig(folder/'capture.png',dpi=200);plt.close(fig)
    fig,axs=plt.subplots(2,3,figsize=(12,7))
    for j in range(3):
        for i,(key,w) in enumerate([('Energy density',energy),('Acceleration magnitude',np.sqrt(aa))]):
            plane=np.take(w,w.shape[j]//2,axis=j);im=axs[i,j].imshow(np.log10(np.maximum(plane,1e-16)),origin='lower',cmap='magma');axs[i,j].set_title(key+f'; axis {j} central slice');fig.colorbar(im,ax=axs[i,j],label='log10(model units)')
    fig.suptitle(label+' — native slices, no geometric downsampling');fig.tight_layout();fig.savefig(folder/'slices.png',dpi=180);plt.close(fig)
    need(array_sha(n)==before,'Footprint mapping changed source field')
    result={'recorded_at':stamp(),'label':label,'array_sha256':before,'source_modified':False,'shape':list(g.shape),'lengths':list(g.lengths),'spacing':list(g.spacing),'metrics':m,'gates':gate_result(m,2 if label=='q2-control' else 21,plan['registered_gates']),'energy_density_convention':'Native static Hamiltonian density, verified to integrate to the minimizer objective. Inherited tail/guard metrics retain their original energy_density convention.','required_bbox':bounds,'rows':ordered,'proposed_patch':proposed,'target':target,'selection_scope':'Measured geometric proposal only; capture is not a truncation error bound, coupled-grid qualification or stationarity certificate. Bounding boxes include n3<0 and residual peaks.','elapsed_seconds':time.perf_counter()-clock,'optimizer_attempts':0,'physical_time_steps':0}
    save(folder/'FOOTPRINT.json',result);return result
