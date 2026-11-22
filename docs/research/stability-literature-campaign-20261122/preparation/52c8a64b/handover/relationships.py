"""Measured matched-step dependencies; fits never grant admission or extrapolate."""
import numpy as np
from evaluations import fit_history
from common import stamp

def scalar_fits(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    if len(x)<5 or len(np.unique(x))!=len(x):return {'status':'insufficient_points_for_validated_curve','points':len(x),'minimum':5,'extrapolation_allowed':False}
    models=[];origin=float(x.mean());scale=max(float(np.ptp(x)),1e-30);xx=(x-origin)/scale
    for name,degree in [('linear',1),('quadratic',2),('exponential',1)]:
        if name=='exponential' and np.any(y<=0):continue
        residuals=[]
        for i in range(len(x)):
            keep=np.arange(len(x))!=i;target=np.log(y[keep]) if name=='exponential' else y[keep];co=np.polyfit(xx[keep],target,degree);pred=np.polyval(co,xx[i]);pred=float(np.exp(np.clip(pred,-700,700))) if name=='exponential' else float(pred);residuals.append(pred-y[i])
        co=np.polyfit(xx,np.log(y) if name=='exponential' else y,degree);error=float(np.sqrt(np.mean(np.asarray(residuals)**2))/max(float(np.mean(abs(y))),1e-30));row={'model':name,'coefficients_highest_power_first':co.tolist(),'x_origin':origin,'x_scale':scale,'leave_one_out_relative_rmse':error,'validated':bool(error<=.25)}
        if name=='quadratic' and abs(co[0])>1e-30:row['fitted_turn_inside_range']=bool(min(x)<origin+scale*(-co[1]/(2*co[0]))<max(x));row['turn']=float(origin+scale*(-co[1]/(2*co[0])))
        models.append(row)
    return {'status':'measured_range_fit_complete','models':models,'sampled_range':[float(min(x)),float(max(x))],'extrapolation_allowed':False,'admission_inferred':False}

def analyze(records,scale_sweep):
    byid={r['arm']['id']:r for r in records};groups=[('bend_amplitude',[('bend-m20',-.02),('bend-m10',-.01),('restart-cg',0.),('bend-p10',.01),('bend-p20',.02)]),('scale',[('scale-98',.98),('restart-cg',1.),('scale-102',1.02)]),('spacing_fixed_box',[('restart-cg',.24),('mesh-129',.18),('mesh-161',.144)]),('length_fixed_spacing',[('restart-cg',23.04),('domain-pad-8',26.88),('domain-pad-16',30.72)])];out=[]
    for name,items in groups:
        rows=[byid[k] for k,_ in items];common=set.intersection(*[{r['step'] for r in a['history']} for a in rows]);step=max(common);matched=[next(r for r in a['history'] if r['step']==step) for a in rows]
        values=[{'arm':k,'parameter':x,'step':step,'metrics':r['metrics'],'gates':r['gates']} for (k,x),r in zip(items,matched)]
        fits={key:scalar_fits([x for _,x in items],[r['metrics'][key] for r in matched]) for key in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction']}
        out.append({'variable':name,'matched_accepted_step':step,'values':values,'fits':fits,'scope':'Same accepted-step index and same restarted CG policy; no equality of objective-call cost or physical time is asserted. Step0 alone is initial mapping sensitivity.'})
    opts=[byid[k] for k in ['restart-cg','sobolev-sd','damped-inertial','projected-lbfgs']];common=set.intersection(*[{r['step'] for r in a['history']} for a in opts]);step=max(common)
    optimizer={'matched_accepted_step':step,'rows':[{'arm':a['arm']['id'],'observation':next(r for r in a['history'] if r['step']==step)} for a in opts],'scope':'Categorical methods: compare matched steps and objective calls; no polynomial across arbitrary optimizer labels.'}
    points=scale_sweep['measured']
    return {'recorded_at':stamp(),'one_factor_groups':out,'optimizer_comparison':optimizer,'static_scale_energy_fit':scalar_fits([p['factor'] for p in points],[p['metrics']['energy'] for p in points]),'time_history_fits':{a['arm']['id']:{k:fit_history(a['history'][-16:],k) for k in ['relative_force_l2','acceleration_max']} for a in records},'candidate_conditions':'Measured unchanged gates only. Fitted optima and turns guide future sample placement; they do not select an unmeasured operating point or certify stability.'}
