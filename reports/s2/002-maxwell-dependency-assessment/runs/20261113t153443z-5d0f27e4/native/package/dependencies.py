"""Empirical models and bounded adaptive acquisition; Apache-2.0."""
import numpy as np
from scipy.optimize import least_squares

def fitted(name,x,y,origin,scale):
    z=(np.asarray(x)-origin)/scale
    if name=='exponential':
        if np.any(np.asarray(y)<=0):raise ValueError('Exponential response must be positive')
        b,a=np.polyfit(z,np.log(y),1)
        result=least_squares(lambda c:np.exp(np.clip(c[0]+c[1]*z,-700,700))-y,[a,b],max_nfev=400)
        if not result.success:raise ValueError('Exponential fit did not converge')
        return result.x.tolist()
    degree={'constant':0,'linear':1,'quadratic':2,'cubic':3}[name]
    return np.polynomial.polynomial.polyfit(z,y,degree).tolist()

def predict(model,x):
    z=(np.asarray(x)-model['origin'])/model['scale'];c=model['coefficients']
    return np.exp(np.clip(c[0]+c[1]*z,-700,700)) if model['model']=='exponential' else np.polynomial.polynomial.polyval(z,c)

def fit_models(rows):
    x=np.array([r['x'] for r in rows]);y=np.array([r['y'] for r in rows]);origin=float(min(x));scale=float(np.ptp(x));models=[]
    names=['constant','linear','quadratic','exponential']+(['cubic'] if len(rows)>=6 else [])
    # Avoid manufacturing turning points from rounding-scale variation.
    if np.ptp(y)<=1e-12:names=['constant']
    for name in names:
        try:
            c=fitted(name,x,y,origin,scale);model={'model':name,'origin':origin,'scale':scale,'coefficients':c,'units':'response is fractional relative L2; z=(x-origin)/scale; polynomial coefficients in ascending z powers, exponential exp(c0+c1*z)'}
            residual=[]
            for i in range(len(rows)):
                keep=np.arange(len(rows))!=i;cv={**model,'coefficients':fitted(name,x[keep],y[keep],origin,scale)};residual.append(float(predict(cv,x[i])-y[i]))
            model['development_loo_rmse']=float(np.sqrt(np.mean(np.array(residual)**2)))
            model['development_max_residual']=float(max(abs(predict(model,x)-y)));models.append(model)
        except (ValueError,FloatingPointError,np.linalg.LinAlgError):continue
    if not models:raise ValueError('No finite candidate fits')
    return sorted(models,key=lambda m:(m['development_loo_rmse'],len(m['coefficients'])))

def features(rows,model,budget=None):
    rows=sorted(rows,key=lambda r:r['x']);x=np.array([r['x'] for r in rows]);y=np.array([r['y'] for r in rows]);out=[]
    if np.ptp(y)<=1e-12:return out
    if model['model']!='exponential':
        c=model['coefficients'];d=np.polynomial.polynomial.polyder(c)
        for root in np.polynomial.polynomial.polyroots(d):
            if abs(root.imag)<1e-9:
                v=model['origin']+root.real*model['scale']
                if x[0]<v<x[-1]:out.append(('turning_point',float(v)))
    slope=np.diff(y)/np.diff(x);curvature=2*np.diff(slope)/(x[2:]-x[:-2])
    for i in range(len(curvature)-1):
        if curvature[i]*curvature[i+1]<0:out.append(('possible_inflection',float((x[i+1]+x[i+2])/2)))
    if budget is not None:
        grid=np.linspace(x[0],x[-1],257);yy=predict(model,grid)-budget
        out.extend(('accuracy_crossing',float((a+b)/2)) for a,b,ya,yb in zip(grid[:-1],grid[1:],yy[:-1],yy[1:]) if ya*yb<0)
    return out

def choose(rows,candidates,options):
    models=fit_models(rows);primary=models[0];ordered=sorted(rows,key=lambda r:r['x']);x=np.array([r['x'] for r in ordered]);y=np.array([r['y'] for r in ordered]);span=float(np.ptp(x));yrange=max(float(np.ptp(y)),1e-12);fs=features(rows,primary,options['accuracy_budget_fraction']);choices=[]
    for a,b in zip(x[:-1],x[1:]):
        available=[v for v in candidates if a<v['x']<b]
        if not available:continue
        local=[(kind,v) for kind,v in fs if a<v<b and np.sum(abs(x-v)<.1*span)<3]
        target=local[0][1] if local else (a+b)/2
        candidate=min(available,key=lambda v:abs(v['x']-target));v=candidate['x']
        spread=float(np.ptp([predict(m,v) for m in models[:2]])) if len(models)>1 else 0.
        endpoint_residual=float(max(abs(predict(primary,np.array([a,b]))-np.array([next(r['y'] for r in ordered if r['x']==a),next(r['y'] for r in ordered if r['x']==b)]))))
        score=(b-a)/span*(1+4*bool(local)+min(spread/yrange,10)+min(endpoint_residual/yrange,10))
        choices.append({**candidate,'score':score,'bracket':[float(a),float(b)],'reason':local[0][0] if local else 'coverage_residual_and_model_disagreement','features':[{'kind':k,'x':p} for k,p in fs],'predicted_y':float(predict(primary,v)),'model':primary})
    if not choices:return None
    return max(choices,key=lambda c:(c['score'],-c['x']))

def feature_width(rows,model,options):
    x=sorted(r['x'] for r in rows);fs=features(rows,model,options['accuracy_budget_fraction']);span=x[-1]-x[0];width=0.
    for _,v in fs:
        brackets=[b-a for a,b in zip(x[:-1],x[1:]) if a<=v<=b]
        if brackets:width=max(width,min(brackets)/span)
    return width
