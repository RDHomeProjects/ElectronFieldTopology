"""Policy v2: epoch-local plateau evidence. Offline audit module, not an installed patch.

Model fitting, gates and optimizer are unchanged. Callers must explicitly supply
the epoch associated with their carried plateau count. Do not copy this file
over a pinned running campaign: continuation needs a new recorded policy identity.
"""
import warnings
import numpy as np
from scipy.optimize import least_squares

def fit_model(x,y,name):
 origin=float(x[0]);scale=max(float(x[-1]-x[0]),1.);z=(x-origin)/scale;normal=max(float(np.max(abs(y))),1e-30);v=y/normal
 if name in ('linear','quadratic'):
  c=np.polynomial.polynomial.polyfit(z,v,1 if name=='linear' else 2)
 else:
  # A nonnegative fitted floor is explicit; a zero asymptote is not imposed.
  def fun(c):return c[0]+c[1]*np.exp(-c[2]*z)-v
  best=None
  for floor in [0.,max(0.,float(v[-1])*.8)]:
   r=least_squares(fun,[floor,max(float(v[0])-floor,.001),1.],bounds=([0,0,1e-8],[2,4,100]),max_nfev=300)
   if best is None or np.sum(r.fun*r.fun)<best[0]:best=(float(np.sum(r.fun*r.fun)),r.x)
  c=best[1]
 return {'model':name,'coefficients':c.tolist(),'origin':origin,'scale':scale,'normal':normal}

def predict(m,x):
 z=(np.asarray(x)-m['origin'])/m['scale'];c=m['coefficients']
 return m['normal']*(c[0]+c[1]*np.exp(np.clip(-c[2]*z,-700,700)) if m['model']=='exponential_floor' else np.polynomial.polynomial.polyval(z,c))

def models(rows,key,p):
 x=np.array([r['iteration'] for r in rows],float);y=np.array([r[key] for r in rows],float);out=[];rejected=[]
 if len(rows)<p['fit_minimum'] or np.ptp(x)<=0:return {'accepted':[],'rejected':[],'reason':'insufficient distinct recent observations'}
 for name in ['linear','quadratic','exponential_floor']:
  try:
   errors=[]
   # Two strictly forward validation origins, with the most recent observations withheld.
   for cut in [len(x)-2,len(x)-1]:
    m=fit_model(x[:cut],y[:cut],name);value=float(predict(m,x[cut]));errors.append(abs(value-y[cut])/max(abs(y[cut]),abs(y[0])*.01,1e-30))
   m=fit_model(x,y,name);m['held_out_relative_error']=float(np.mean(errors));m['validation_errors']=errors
   m['score']=m['held_out_relative_error']+.002*len(m['coefficients'])
   if m['held_out_relative_error']>p['validation_relative_limit']:rejected.append({**m,'reason':'forward prediction error exceeds limit'})
   else:out.append(m)
  except (ValueError,RuntimeError,FloatingPointError,np.linalg.LinAlgError) as e:rejected.append({'model':name,'reason':str(e)})
 out.sort(key=lambda m:m['score'])
 return {'accepted':out,'rejected':rejected,'reason':'forward validation; model spread is not a confidence interval'}

def decide(history,p,remaining,plateau_count=0,*,plateau_epoch):
 lo,hi=p['batch_limits'];obslo,obshi=p['observe_limits'];last=history[-1];iteration=last['iteration']
 # The established optimizer resets conjugacy every 200 accepted iterations.
 epoch=(iteration//200)*200
 rows=[r for r in history if r['iteration']>=epoch][-p['fit_window']:]
 result={'iteration':iteration,'remaining_attempts':remaining,'fit_epoch_start':epoch,'plateau_epoch':epoch,'policy_version':2,'models':{},'gate_pass':False,'method':'adaptive optimizer iteration count; optimizer alpha policy unchanged'}
 if remaining<=0:return {**result,'action':'stop','reason':'declared attempt budget exhausted','steps':0,'observe':obslo}
 for key in ['relative_force_l2','acceleration_max','energy']:result['models'][key]=models(rows,key,p)
 near=max(last['relative_force_l2']/p['force_limit'],last['acceleration_max']/p['acceleration_limit'])<3
 a=rows[max(0,len(rows)//2-1)];improvements={}
 for key,gate in [('relative_force_l2',p['force_limit']),('acceleration_max',p['acceleration_limit'])]:
  improvements[key]=(a[key]-last[key])/max(a[key],1e-30)
 energy_ok=bool(last['energy']<=a['energy']+1e-11*max(abs(a['energy']),1.))
 distinct=len(set(r['iteration'] for r in rows))
 sufficient=distinct>=p['fit_minimum'] and rows[-1]['iteration']>rows[0]['iteration']
 joint=(energy_ok and all(last[k]<=gate or improvements[k]>=p['recent_joint_progress'] for k,gate in [('relative_force_l2',p['force_limit']),('acceleration_max',p['acceleration_limit'])])) if sufficient else None
 result.update(recent_improvement=improvements,recent_joint_progress=joint,energy_nonincreasing=energy_ok,progress_evidence_sufficient=sufficient,distinct_epoch_observations=distinct)
 # Changes of slope/curvature shorten both the allocation and observation spacing.
 turn=False
 if len(rows)>=4:
  for key in ['relative_force_l2','acceleration_max']:
   ys=np.array([r[key] for r in rows[-4:]]);xs=np.array([r['iteration'] for r in rows[-4:]]);slopes=np.diff(ys)/np.maximum(np.diff(xs),1)
   turn=turn or bool(slopes[-1]*slopes[-2]<0 or (slopes[-1]-slopes[-2])*(slopes[-2]-slopes[-3])<0)
 valid=all(result['models'][k]['accepted'] for k in ['relative_force_l2','acceleration_max'])
 previous_count=plateau_count if plateau_epoch==epoch else 0
 stagnant=sufficient and not joint
 count=previous_count+1 if stagnant and iteration>=p['minimum_before_plateau'] else 0
 result['plateau_count']=count
 if count>=p['plateau_decisions']:
  return {**result,'action':'stop','reason':'repeated absence of measured joint progress after exploratory allocation; not a physical Q rejection','steps':0,'observe':obslo}
 if not energy_ok:return {**result,'action':'stop','reason':'measured energy increase requires numerical diagnosis','steps':0,'observe':obslo,'systemic_fault':True}
 if not valid or turn:
  steps=min(10 if not turn else lo,remaining);reason='short exploratory batch: insufficient/unreliable fit' if not turn else 'observed slope/curvature turn'
 else:
  horizon=max(lo,min(hi,int(.5*max(rows[-1]['iteration']-rows[0]['iteration'],lo*2))))
  event=horizon;why='validated extrapolation horizon';future=np.arange(1,horizon+1)
  for key,gate in [('relative_force_l2',p['force_limit']),('acceleration_max',p['acceleration_limit'])]:
   candidates=result['models'][key]['accepted'];best=candidates[0];good=[m for m in candidates if m['score']<=best['score']*1.5+.01]
   forecasts=np.stack([predict(m,iteration+future) for m in good]);centre=np.median(forecasts,axis=0)
   # Stop relying on extrapolation when positivity or model agreement fails.
   bad=np.where((forecasts.min(axis=0)<=0)|((forecasts.max(axis=0)-forecasts.min(axis=0))/np.maximum(abs(centre),gate) > p['model_disagreement_limit']))[0]
   if len(bad) and bad[0]+1<event:event=int(bad[0]+1);why='model disagreement/positivity horizon'
   crossing=np.where(centre<=gate*1.2)[0]
   if last[key]>gate*1.2 and len(crossing) and crossing[0]+1<event:event=max(1,int((crossing[0]+1)*.5));why='approaching measured admission threshold'
  steps=min(remaining,max(lo,min(hi,event)));reason=why
  if not joint:steps=min(steps,10);reason+='; recent joint progress not yet measured'
 observe=obslo if near or turn else min(obshi,max(obslo,steps//4))
 return {**result,'action':'continue','reason':reason,'steps':int(steps),'observe':int(observe),'turn_detected':bool(turn),'predicted_pass':False}
