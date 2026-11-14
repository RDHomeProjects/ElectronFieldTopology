"""Descriptive within-configuration fits with a chronological holdout."""
import numpy as np

def fits(history,start_iteration):
    rows=[v for v in history if v['iteration']>=start_iteration];out={}
    if len(rows)<6:return {'scope':'Too few new-tranche observations for curve comparison','metrics':{}}
    cut=max(4,int(len(rows)*.7));train=rows[:cut];test=rows[cut:]
    if not test:return {'scope':'No chronological holdout','metrics':{}}
    origin=train[0]['iteration'];scale=max(train[-1]['iteration']-origin,1);x=np.array([(v['iteration']-origin)/scale for v in train]);xt=np.array([(v['iteration']-origin)/scale for v in test])
    for metric in ['relative_force_l2','acceleration_max']:
        y=np.array([max(v[metric],1e-30) for v in train]);actual=np.array([v[metric] for v in test]);models=[]
        for kind,degree in [('constant',0),('linear',1),('quadratic',2),('exponential',1)]:
            if len(train)<degree+3:continue
            coeff=np.polynomial.polynomial.polyfit(x,np.log(y) if kind=='exponential' else y,degree);pred=np.polynomial.polynomial.polyval(xt,coeff)
            if kind=='exponential':pred=np.exp(np.clip(pred,-700,700))
            rmse=float(np.sqrt(np.mean((pred-actual)**2)));models.append({'model':kind,'coefficients':coeff.tolist(),'origin_iteration':origin,'scale':scale,'holdout_iterations':[v['iteration'] for v in test],'holdout_rmse':rmse,'holdout_rmse_over_mean':rmse/max(float(np.mean(actual)),1e-30),'positive_predictions':bool(np.all(pred>=0))})
        out[metric]=sorted(models,key=lambda v:(v['holdout_rmse'],len(v['coefficients'])))
    return {'scope':'Retrospective within-branch chronological comparison, not prospective acceptance or a physical-time fit; no extrapolated passing time','metrics':out}
