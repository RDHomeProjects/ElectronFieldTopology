"""Descriptive development fits, with explicitly nonnegative power candidates."""
import numpy as np
from scipy.optimize import least_squares
from .kernel.reference.dependencies import fit_models,predict as base_predict,features

def power_fit(x,y,offset,scale):
 z=np.asarray(x)/scale;y=np.asarray(y);yscale=max(float(max(y)),1e-20)
 if np.any(y<=0):raise ValueError('Power response must be positive')
 initial=[.01,.99,2.] if offset else [1.,2.]
 lower=[0.,0.,.2] if offset else [0.,.2];upper=[np.inf,np.inf,6.] if offset else [np.inf,6.]
 def fn(c):return c[0]+c[1]*z**c[2] if offset else c[0]*z**c[1]
 result=least_squares(lambda c:fn(c)-y/yscale,initial,bounds=(lower,upper),max_nfev=2000,gtol=1e-13,xtol=1e-13,ftol=1e-13)
 if not result.success:raise ValueError('Constrained power fit failed')
 c=result.x
 return [float(c[0]*yscale),float(c[1]*yscale),float(c[2])] if offset else [float(c[0]*yscale),float(c[1])]
def predict(m,x):
 c=m['coefficients'];z=np.asarray(x)/m['scale']
 if m['model']=='pure_power':return c[0]*z**c[1]
 if m['model']=='nonnegative_offset_power':return c[0]+c[1]*z**c[2]
 return base_predict(m,x)
def models(rows):
 # Avoid the archived exploratory unconstrained offset-power candidate.
 safe=[{**v,'variable':'cell_measured_spacing'} for v in rows];out=fit_models(safe);x=np.array([r['x'] for r in rows]);y=np.array([r['y'] for r in rows]);scale=float(max(x))
 for offset,name in [(False,'pure_power'),(True,'nonnegative_offset_power')]:
  try:
   m={'model':name,'origin':0.,'scale':scale,'coefficients':power_fit(x,y,offset,scale),'units':'fractional norm; z=h/max(h); pure A*z^p or nonnegative a+b*z^p','extrapolation':'no continuum or production-optimum certificate'}
   residual=[]
   for i in range(len(rows)):
    keep=np.arange(len(rows))!=i;cv={**m,'coefficients':power_fit(x[keep],y[keep],offset,scale)};residual.append(float(predict(cv,x[i])-y[i]))
   m['development_loo_rmse']=float(np.sqrt(np.mean(np.square(residual))));m['development_max_residual']=float(max(abs(predict(m,x)-y)));out.append(m)
  except (ValueError,FloatingPointError,np.linalg.LinAlgError):continue
 return sorted(out,key=lambda m:(m['development_loo_rmse'],len(m['coefficients'])))
def test_power():
 rows=[{'x':h,'y':2e-5+.05*h*h} for h in [.05,.06,.075,.09,.11,.13,.16,.18]];m=next(m for m in models(rows) if m['model']=='nonnegative_offset_power');error=float(max(abs(predict(m,np.array([.07,.12]))-(2e-5+.05*np.array([.07,.12])**2))))
 assert m['coefficients'][0]>=0 and m['coefficients'][1]>=0 and error<1e-8
 return {'manufactured_nonnegative_offset_power_max_error':error,'status':'passed'}
