"""Validated one-factor curves, adaptive measurements and bounded candidate proposals."""
import numpy as np
from common import stamp

def response(history,p):
    rows=[r for r in history if r['accepted_step']>0]
    if len(rows)<max(p['minimum_matched_accepted_steps'],p['measurement_attempts']):return {'eligible':False,'reason':'fewer_than_required_committed_updates','accepted_steps':len(rows)}
    window=rows[p['measurement_attempts']-p['response_median_window']:p['measurement_attempts']]
    f=np.array([r['metrics']['relative_force_l2'] for r in window]);a=np.array([r['metrics']['acceleration_max'] for r in window]);g=p['registered_gates'];scores=np.maximum(f/g['force_limit'],a/g['acceleration_limit']);score=max(float(np.median(f))/g['force_limit'],float(np.median(a))/g['acceleration_limit'])
    eligible=all(r['gates']['representation'] and r['gates']['boundary_admitted'] for r in history[:p['measurement_attempts']+1])
    return {'eligible':eligible,'reason':'matched_update_response' if eligible else 'representation_or_boundary_failure','accepted_steps':p['measurement_attempts'],'window_steps':[r['accepted_step'] for r in window],'median_force':float(np.median(f)),'median_acceleration':float(np.median(a)),'score':score,'trajectory_score_mad':float(np.median(abs(scores-np.median(scores)))),'scope':f"Last{p['response_median_window']} observations through accepted update{p['measurement_attempts']}. MAD describes within-trajectory variation, not independent statistical uncertainty."}

def evaluate(model,x):
    xx=(np.asarray(x,float)-model['x_origin'])/model['x_scale'];v=np.polyval(model['coefficients'],xx)
    return np.exp(np.clip(v,-700,700)) if model['model']=='exponential' else v

def fit(samples,key,p):
    usable=[s for s in samples if s['response']['eligible']];x=np.array([s['log2_shift'] for s in usable]);y=np.array([s['response'][key] for s in usable])
    if len(x)<p['minimum_fit_points']:return {'status':'insufficient_matched_points','models':[],'points':len(x)}
    origin=float(x.mean());scale=max(float(np.ptp(x)),1e-12);xx=(x-origin)/scale;constant=np.array([np.mean(np.delete(y,i))-y[i] for i in range(len(y))]);baseline=float(np.sqrt(np.mean(constant**2)));variation=float(np.ptp(y));noise=float(np.median([s['response']['trajectory_score_mad'] for s in usable])) if key=='score' else 0.
    floor=max(1e-12,p['comparison_window_noise_floor_fraction']*noise);den=max(variation,floor);models=[]
    for name,degree in [('linear',1),('quadratic',2),('exponential',1)]:
        if name=='exponential' and np.any(y<=0):continue
        errors=[];turns=[]
        for i in range(len(x)):
            keep=np.arange(len(x))!=i;co=np.polyfit(xx[keep],np.log(y[keep]) if name=='exponential' else y[keep],degree);pred=np.polyval(co,xx[i]);pred=float(np.exp(np.clip(pred,-700,700))) if name=='exponential' else float(pred);errors.append(pred-y[i])
            if name=='quadratic' and co[0]>0:turns.append(float(origin+scale*(-co[1]/(2*co[0]))))
        rmse=float(np.sqrt(np.mean(np.asarray(errors)**2)));skill=1-(rmse/baseline)**2 if baseline>1e-12 else None;co=np.polyfit(xx,np.log(y) if name=='exponential' else y,degree)
        valid=skill is not None and skill>=p['minimum_skill_vs_constant'] and rmse/den<=p['leave_one_out_range_nrmse_limit'] and variation>floor
        m={'model':name,'coefficients':co.tolist(),'x_origin':origin,'x_scale':scale,'leave_one_out_rmse':rmse,'range_normalized_rmse':rmse/den,'skill_vs_constant':skill,'validated':bool(valid)}
        if name=='quadratic' and abs(co[0])>1e-15:m['turn_log2_shift']=float(origin+scale*(-co[1]/(2*co[0])));m['turn_is_minimum']=bool(co[0]>0)
        if name=='quadratic':m['leave_one_out_turns']=turns;m['leave_one_out_turn_spread']=max(turns)-min(turns) if len(turns)==len(x) else None
        models.append(m)
    return {'status':'measured_curve_fit','parameter_coordinate':'log2(Sobolev_shift)','models':models,'points':len(x),'sampled_range':[float(min(x)),float(max(x))],'constant_leave_one_out_rmse':baseline,'measured_response_range':variation,'trajectory_variation_floor':floor,'admission_inferred':False}

def curves(samples,p):return {k:fit(samples,k,p) for k in ['score','median_force','median_acceleration']}

def acceptable(v,baseline,p):
    return v['score']<=baseline['score']*(1-p['minimum_candidate_improvement']) and all(v[k]<=baseline[k]*(1+p['maximum_individual_metric_worsening']) for k in ['median_force','median_acceleration'])

def predictive_pool(curve,p):
    good=[m for m in curve['models'] if m['validated']]
    if not good:return []
    best=min(m['leave_one_out_rmse'] for m in good)
    cap=p['model_competition_rmse_factor']*best+p['model_competition_variation_allowance']*curve['measured_response_range']
    return [m for m in good if m['leave_one_out_rmse']<=cap]

def fitted_candidate(samples,p):
    c=curves(samples,p);good=predictive_pool(c['score'],p);observed=[s for s in samples if s['response']['eligible']];base=next((s['response'] for s in observed if abs(s['log2_shift']+2)<1e-10),None)
    stable_quad=[m for m in good if m.get('turn_is_minimum') and m.get('leave_one_out_turn_spread') is not None and m['leave_one_out_turn_spread']<=p['maximum_validated_optimum_spread_log2']]
    if base is None or (len(good)<2 and not stable_quad):return None,c
    support='multi_model_consensus' if len(good)>=2 else 'validated_quadratic_with_stable_leave_one_out_turn'
    lo=max(p['hard_log2_bounds'][0],min(s['log2_shift'] for s in observed)-p['maximum_extrapolation_log2_distance']);hi=min(p['hard_log2_bounds'][1],max(s['log2_shift'] for s in observed)+p['maximum_extrapolation_log2_distance']);grid=np.linspace(lo,hi,601);minima=[]
    for m in good:
        y=evaluate(m,grid)
        if not np.isfinite(y).all() or np.any(y<=0):return None,c
        minima.append(float(grid[np.argmin(y)]))
    if max(minima)-min(minima)>p['maximum_validated_optimum_spread_log2']:return None,c
    x=float(np.median(minima));pred={'score':float(np.median([evaluate(m,x) for m in good]))}
    for key in ['median_force','median_acceleration']:
        ms=predictive_pool(c[key],p)
        if not ms:return None,c
        pred[key]=float(np.median([evaluate(m,x) for m in ms]))
    if not all(np.isfinite(v) and v>0 for v in pred.values()) or not acceptable(pred,base,p):return None,c
    mode='interpolation' if min(s['log2_shift'] for s in observed)<=x<=max(s['log2_shift'] for s in observed) else 'bounded_extrapolation'
    return {'log2_shift':round(x,6),'shift':float(2**round(x,6)),'mode':mode,'predicted_response':pred,'model_minima_log2':minima,'model_names':[m['model'] for m in good],'optimum_support':support,'admission_inferred':False},c

def next_sample(samples,p):
    observed=sorted(s['log2_shift'] for s in samples);eligible=[s for s in samples if s['response']['eligible']]
    if not eligible:return None
    candidate,c=fitted_candidate(samples,p);proposals=[]
    if candidate:proposals.append((candidate['log2_shift'],'measure_fitted_optimum_before_long_validation'))
    best=min(eligible,key=lambda s:s['response']['score'])
    # A new extrapolation sample is at most half an octave beyond measured
    # coverage, and never outside the declared global shift range.
    if len(eligible)>=5:
        sorted_good=sorted(eligible,key=lambda s:s['log2_shift'])
        if best is sorted_good[0] and best['response']['score']<.98*sorted_good[1]['response']['score']:proposals.append((best['log2_shift']-.5,'bounded_left_extension_of_measured_improvement'))
        if best is sorted_good[-1] and best['response']['score']<.98*sorted_good[-2]['response']['score']:proposals.append((best['log2_shift']+.5,'bounded_right_extension_of_measured_improvement'))
    # Refine near a fitted turn, then where slopes change around the measured
    # best region; uncertainty cannot authorize an unbounded extrapolation.
    for m in c['score']['models']:
        if m.get('turn_is_minimum') and min(observed)<=m['turn_log2_shift']<=max(observed):proposals.append((m['turn_log2_shift'],'additional_measurement_near_curve_turn'))
    neighbors=sorted([(abs((a+b)/2-best['log2_shift']),-(b-a),(a+b)/2) for a,b in zip(observed,observed[1:])])
    proposals += [(x,'local_midpoint_refinement_when_fit_is_uncertain') for _,_,x in neighbors]
    for x,reason in proposals:
        x=round(float(x),6)
        if p['hard_log2_bounds'][0]<=x<=p['hard_log2_bounds'][1] and min(abs(x-y) for y in observed)>=p['adaptive_minimum_log2_separation']:
            return {'recorded_at':stamp(),'log2_shift':x,'shift':float(2**x),'reason':reason,'fits':c,'admission_inferred':False}
    return None

def select(samples,p):
    admitted=[s for s in samples if s.get('all_readiness_gates')]
    if admitted:
        s=min(admitted,key=lambda x:x.get('response',{}).get('score',float('inf')));return {'log2_shift':s['log2_shift'],'shift':s['shift'],'mode':'measured_readiness_confirmation','source_case':s['case']}
    candidate,c=fitted_candidate(samples,p)
    if candidate:
        if any(abs(candidate['log2_shift']-s['log2_shift'])<1e-6 for s in samples):candidate['mode']='measured_value_reconfirmation'
        return candidate|{'fits':c}
    good=[s for s in samples if s['response']['eligible']];base=next((s['response'] for s in good if abs(s['log2_shift']+2)<1e-10),None)
    if base is not None:
        better=[s for s in good if acceptable(s['response'],base,p)]
        if better:
            s=min(better,key=lambda x:x['response']['score']);return {'log2_shift':s['log2_shift'],'shift':s['shift'],'mode':'best_measured_value_without_validated_optimum','source_case':s['case'],'fits':c}
    return {'mode':'no_supported_improvement','fits':c,'reason':'No qualified fitted optimum or measured joint improvement over baseline; no long confirmation allocated'}
