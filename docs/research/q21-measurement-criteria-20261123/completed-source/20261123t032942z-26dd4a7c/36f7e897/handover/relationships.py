"""Measured response curves, conservative validation and adaptive mesh acquisition."""
import numpy as np

def window(history,horizon,width=10):
    rows=[r for r in history if horizon-width<r['accepted_step']<=horizon]
    if len(rows)!=width:return {'eligible':False,'reason':'unmatched accepted-step horizon'}
    force=float(np.median([r['metrics']['relative_force_l2'] for r in rows]));acc=float(np.median([r['metrics']['acceleration_max'] for r in rows]))
    return {'eligible':all(r['gates']['representation'] and r['gates']['boundary_admitted'] for r in rows),'force':force,'acceleration':acc,'joint':max(force/1e-4,acc/1e-3),'horizon':horizon,'width':width}

def better(candidate,baseline,p):
    return bool(candidate.get('eligible') and baseline.get('eligible') and candidate['joint']<=(1-p['minimum_joint_improvement'])*baseline['joint'] and all(candidate[k]<=(1+p['maximum_component_worsening'])*baseline[k] for k in ['force','acceleration']))

def fit_curve(points,key,p):
    pts=sorted(points,key=lambda r:r['spacing']);x=np.asarray([r['spacing'] for r in pts]);y=np.asarray([r[key] for r in pts]);result=[]
    if len(x)<p['minimum_fit_points'] or len(set(x))!=len(x):return {'status':'insufficient_distinct_matched_points','points':len(x),'models':[],'supported_optimum':False}
    scale=max(float(np.ptp(y)),.05*float(np.median(abs(y))),1e-12)
    for name,degree in [('linear',1),('quadratic',2),('exponential',1)]:
        if name=='exponential' and np.any(y<=0):continue
        preds=[];constant=[]
        for i in range(len(x)):
            keep=np.arange(len(x))!=i;target=np.log(y[keep]) if name=='exponential' else y[keep];coef=np.polyfit(x[keep],target,degree);v=np.polyval(coef,x[i]);preds.append(float(np.exp(np.clip(v,-700,700))) if name=='exponential' else float(v));constant.append(float(np.mean(y[keep])))
        mse=float(np.mean((np.asarray(preds)-y)**2));cmse=float(np.mean((np.asarray(constant)-y)**2));err=np.sqrt(mse)/scale;skill=0. if cmse<=1e-24 else 1-mse/cmse
        coef=np.polyfit(x,np.log(y) if name=='exponential' else y,degree)
        result.append({'model':name,'coefficients_highest_power_first':coef.tolist(),'loo_range_nrmse':float(err),'loo_skill_vs_constant':skill,'eligible':bool(err<=p['leave_one_out_nrmse_limit'] and skill>=p['minimum_skill_vs_constant']),'support':[float(x.min()),float(x.max())]})
    return {'status':'validated_model_available' if any(m['eligible'] for m in result) else 'no_validated_response_curve','models':result,'points':len(x),'supported_optimum':False,'scope':'Finite-horizon response versus actual spacing; no stationary-solution convergence or optimum inferred automatically'}

def acquire(points,used,p,blocked=()):
    """Explore below hard limits, concentrating on measured changes of slope."""
    available=[n for n in range(137,194,8) if n not in used and n not in blocked]
    if not available:return None
    pts=sorted(points,key=lambda x:x['nodes']);scores=[]
    for n in available:
        lower=[x for x in pts if x['nodes']<n];upper=[x for x in pts if x['nodes']>n]
        if not lower or not upper:continue
        l,u=lower[-1],upper[0];gap=u['nodes']-l['nodes'];gradient=abs(u['joint']-l['joint'])/max(abs(l['joint']),abs(u['joint']),1e-12)
        # A neighbouring change of slope raises priority; its existence is measured,
        # not a claim of a mathematical inflection from two samples.
        turns=0
        i=pts.index(l)
        if i>0:
            before=pts[i-1];s1=(l['joint']-before['joint'])/(l['nodes']-before['nodes']);s2=(u['joint']-l['joint'])/gap;turns=abs(s2-s1)/max(abs(s1),abs(s2),1e-12)
        scores.append((gap*(1+gradient+turns)-abs(n-(l['nodes']+u['nodes'])/2),n))
    if not scores:return min(available)
    return max(scores)[1]

def propose_supported(points,used,p):
    """A fitted interior minimum requires joint/component model agreement."""
    models={key:fit_curve(points,key,p) for key in ['joint','force','acceleration']}
    good={k:[m for m in v['models'] if m['eligible']] for k,v in models.items()}
    if not all(good.values()):return None,models
    low=max(m['support'][0] for ms in good.values() for m in ms);high=min(m['support'][1] for ms in good.values() for m in ms)
    options=[]
    for n in range(137,194,8):
        h=p['fixed_length']/(n-1)
        if n in used or not low<=h<=high:continue
        preds={}
        for k,ms in good.items():
            vs=[float(np.exp(np.polyval(m['coefficients_highest_power_first'],h))) if m['model']=='exponential' else float(np.polyval(m['coefficients_highest_power_first'],h)) for m in ms]
            if min(vs)<=0 or (max(vs)-min(vs))/max(abs(np.mean(vs)),1e-12)>.25:break
            preds[k]=float(np.mean(vs))
        if len(preds)==3:options.append((preds['joint'],n,preds))
    if not options:return None,models
    best=min(options);baseline=next((r for r in points if r['nodes']==129),None)
    if baseline is None or not better({'eligible':True,**best[2]},baseline,p):return None,models
    return {'nodes':best[1],'spacing':p['fixed_length']/(best[1]-1),'predicted':best[2],'kind':'validated_within_support_interpolation_to_be_measured','admission_granted':False},models

def spatial_comparison(cases,p):
    baseline=next((r for r in cases if r['case']['id']=='mesh-129'),None);comparisons=[]
    if baseline is None:return {'status':'no_reset_baseline','comparisons':[],'convergence_certified':False}
    for r in cases:
        if r['case']['start']=='exact' or r['case']['nodes']==129:continue
        for horizon in [0,30,80,120]:
            b=next((x for x in baseline['history'] if x['accepted_step']==horizon),None);a=next((x for x in r['history'] if x['accepted_step']==horizon),None)
            if a is None or b is None or 'energy' not in a['metrics'] or 'energy' not in b['metrics']:continue
            error=abs(a['metrics']['energy']-b['metrics']['energy'])/max(abs(b['metrics']['energy']),1e-30)
            comparisons.append({'nodes':r['case']['nodes'],'horizon':horizon,'stage':'interpolation_only' if horizon==0 else 'matched_finite_accepted_horizon','energy_relative_difference':error,'original_mesh_energy_limit':p['registered_gates']['mesh_energy_limit'],'energy_difference_within_original_limit':bool(error<=p['registered_gates']['mesh_energy_limit']),'baseline_all_readiness':b['gates'].get('all_readiness_gates',False),'candidate_all_readiness':a['gates'].get('all_readiness_gates',False),'convergence_certified':False})
    return {'status':'measured_comparisons','comparisons':comparisons,'convergence_certified':False,'scope':'The original2% mesh-energy diagnostic is retained. Interpolation or unequal nonstationary endpoints cannot certify stationary spatial convergence.'}
