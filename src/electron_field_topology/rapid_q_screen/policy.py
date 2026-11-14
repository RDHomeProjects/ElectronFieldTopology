import numpy as np
def representation(m,q,p):return bool(np.isfinite(m['relative_force_l2']) and abs(abs(m['hopf_integral'])-q)/q<=p['charge_relative_error'] and m['minimum_corner_cone']>0 and m['unit_error']<p['unit_limit'])
def stationary(m,q,p):return representation(m,q,p) and m['relative_force_l2']<=p['force_limit'] and m['acceleration_max']<=p['acceleration_limit']
def classify(m,initial,q,p,tail=None):
 if not representation(m,q,p):return {'decision':'refine_representation','reason':'Measured representation lost or unresolved; not a physical Q rejection'}
 if stationary(m,q,p):
  good=tail is not None and tail<=p['initial_tail_limit']
  return {'decision':'static_survivor' if good else 'boundary_followup','reason':'Strict finite-grid stationarity measured; boost admission and motion remain untested'}
 ratio=m['relative_force_l2']/max(initial['relative_force_l2'],1e-30)
 return {'decision':'priority_continue' if ratio<=p['force_ratio_priority'] else 'defer_slow','force_ratio':ratio,'reason':'Compute priority only; early decay is not a stationarity prediction or Q rejection'}
def trend(rows):
 rows=[r for r in rows if r.get('relative_force_l2',0)>0];out=[]
 if len(rows)<3:return {'models':[],'scope':'insufficient observations'}
 x=np.array([r['iteration'] for r in rows],float);y=np.array([r['relative_force_l2'] for r in rows]);origin=float(x.min());scale=max(float(np.ptp(x)),1.);z=(x-origin)/scale
 for name,degree in [('constant',0),('linear',1),('quadratic',2)]:
  if len(rows)<degree+3:continue
  c=np.polynomial.polynomial.polyfit(z,y,degree);res=[]
  for i in range(len(x)):
   keep=np.arange(len(x))!=i;cc=np.polynomial.polynomial.polyfit(z[keep],y[keep],degree);res.append(float(np.polynomial.polynomial.polyval(z[i],cc)-y[i]))
  out.append({'model':name,'coefficients':c.tolist(),'origin':origin,'scale':scale,'loo_rmse':float(np.sqrt(np.mean(np.square(res))))})
 c=np.polynomial.polynomial.polyfit(z,np.log(y),1);res=[]
 for i in range(len(x)):
  keep=np.arange(len(x))!=i;cc=np.polynomial.polynomial.polyfit(z[keep],np.log(y[keep]),1);res.append(float(np.exp(np.polynomial.polynomial.polyval(z[i],cc))-y[i]))
 out.append({'model':'exponential','coefficients':c.tolist(),'origin':origin,'scale':scale,'loo_rmse':float(np.sqrt(np.mean(np.square(res))))})
 return {'models':sorted(out,key=lambda m:(m['loo_rmse'],len(m['coefficients']))),'scope':'Retrospective/descriptive relaxation trend; no terminal prediction validation or physical-time fit'}
def interval(rows,current,p):
 lo,hi=p['observe_interval_limits']
 if len(rows)<3:return min(hi,current+5),{'reason':'initial coverage'}
 a,b,c=rows[-3:];fa,fb,fc=[max(v['relative_force_l2'],1e-30) for v in [a,b,c]];prediction=np.log(fb)+(np.log(fb)-np.log(fa))*(c['iteration']-b['iteration'])/max(b['iteration']-a['iteration'],1)
 residual=abs(np.exp(np.clip(prediction,-700,700))-fc)/fc;turn=(fb-fa)*(fc-fb)<0
 nxt=max(lo,current//2) if turn or residual>p['progress_prediction_relative_limit'] else min(hi,current+5)
 return nxt,{'reason':'force reversal or prediction residual' if turn or residual>p['progress_prediction_relative_limit'] else 'smooth trend; widen observation interval','relative_prediction_residual':float(residual),'force_turn':bool(turn)}
