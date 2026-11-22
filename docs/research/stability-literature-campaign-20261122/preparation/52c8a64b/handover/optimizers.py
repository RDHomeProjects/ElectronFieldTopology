"""Matched D4 energy-descending methods. Iterations are not physical time."""
import os
from pathlib import Path
import numpy as np
from scipy.fft import dstn
from common import canonical,need,save,sha,stamp
from engine import Engine,dst_fft

class ComparisonEngine(Engine):
    def step_method(self,s,g,method):
        if method=='cg':return self.step(s,g)
        from electron_field_topology.skyrme import K
        xp=self.xp;n=s['n'];mask=xp.asarray(g.fixed_mask());vol=float(np.prod(g.spacing));interior=(slice(2,-2),)*3
        def tangent(a):
            a=a-n*xp.sum(n*a,axis=-1,keepdims=True);a[mask]=0;return a
        value,raw=self.value(n,g);gradient=tangent(raw/(2*K*vol))
        axes=[4*xp.sin(xp.pi*xp.arange(1,count-3)/(2*(count-3)))**2/h**2 for count,h in zip(g.shape,g.spacing)]
        symbol=.25+sum(xp.reshape(v,tuple(len(v) if i==j else 1 for i in range(3))) for j,v in enumerate(axes))
        transform=lambda a:dstn(a,axes=(0,1,2),type=1,norm='ortho') if self.kind=='cpu' else dst_fft(a,xp)
        def inverse(v):
            z=xp.zeros_like(v);z[interior]=transform(transform(v[interior])/symbol[...,None]);return tangent(z)
        z=inverse(gradient);pairs=s.setdefault('pairs',[])
        if method=='sd':direction=-z
        elif method=='inertial':direction=-z if s['direction'] is None else -z+.5*tangent(s['direction'])
        elif method=='lbfgs':
            clean=[]
            for a,b in pairs:
                a,b=tangent(a),tangent(b);ys=float(xp.sum(a*b))
                if ys>1e-12*max(float(xp.linalg.norm(a)*xp.linalg.norm(b)),1e-30):clean.append((a,b,1/ys))
            pairs[:]=[(a,b) for a,b,_ in clean];v=gradient.copy();alphas=[]
            for a,b,rho in reversed(clean):
                aa=rho*float(xp.sum(a*v));alphas.append(aa);v-=aa*b
            r=inverse(v)
            for (a,b,rho),aa in zip(clean,reversed(alphas)):r+=a*(aa-rho*float(xp.sum(b*r)))
            direction=-tangent(r)
        else:raise ValueError(method)
        if float(xp.sum(direction*gradient))>=0:direction=-z;pairs.clear()
        slope=float(2*K*vol*xp.sum(gradient*direction));margin=self.cone(n)
        need(margin>0,'Representation cone failed before alternative-method step')
        maximum=float(xp.max(xp.linalg.norm(direction,axis=-1)));alpha=min(s['alpha']*1.6,min(.15,.25*margin)/max(maximum,1e-30));accepted=False;calls=1
        for _ in range(45):
            trial=n+alpha*direction;trial/=xp.linalg.norm(trial,axis=-1,keepdims=True);trial[mask]=xp.asarray([0.,0.,1.])
            next_value,next_raw=self.value(trial,g);calls+=1
            if np.isfinite(next_value) and next_value<=value+1e-4*alpha*slope:accepted=True;break
            alpha*=.5
        if not accepted or alpha*maximum<1e-14:return False,{'reason':'Armijo search stalled','objective_calls':calls}
        if method=='lbfgs':
            new_g=next_raw/(2*K*vol);new_g-=trial*xp.sum(trial*new_g,axis=-1,keepdims=True);new_g[mask]=0
            project=lambda a:a-trial*xp.sum(trial*a,axis=-1,keepdims=True)
            delta=project(trial-n);delta[mask]=0;yy=new_g-project(gradient);yy[mask]=0
            if float(xp.sum(delta*yy))>1e-12*max(float(xp.linalg.norm(delta)*xp.linalg.norm(yy)),1e-30):pairs.append((delta,yy))
            del pairs[:-3]
        s.update(n=trial,old_g=gradient,old_z=z,direction=direction,alpha=alpha,iteration=s['iteration']+1)
        return True,{'energy':next_value,'objective_calls':calls,'accepted_step_max':alpha*maximum,'method':method,'lbfgs_pairs':len(pairs)}

def write_state(path,s,engine,identity):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');arrays={}
    for k in ['n','old_g','old_z','direction']:arrays[k]=engine.host(s[k]) if s.get(k) is not None else np.empty(0,dtype=np.float64)
    for i,(a,b) in enumerate(s.get('pairs',[])):arrays['pair_s_'+str(i)]=engine.host(a);arrays['pair_y_'+str(i)]=engine.host(b)
    with tmp.open('wb') as f:
        np.savez(f,**arrays,alpha=float(s['alpha']),iteration=int(s['iteration']),backend=engine.kind,identity_sha256=canonical(identity),pair_count=len(s.get('pairs',[])))
        f.flush();os.fsync(f.fileno())
    tmp.replace(p);save(p.with_suffix('.seal.json'),{'recorded_at':stamp(),'sha256':sha(p),'identity_sha256':canonical(identity)})

def read_state(path,engine,identity):
    p=Path(path);seal=__import__('json').loads(p.with_suffix('.seal.json').read_text());need(seal['sha256']==sha(p) and seal['identity_sha256']==canonical(identity),'Branch checkpoint seal differs')
    with np.load(p,allow_pickle=False) as z:
        need(str(z['identity_sha256'])==canonical(identity) and str(z['backend'])==engine.kind,'Branch checkpoint identity/backend differs')
        s={'alpha':float(z['alpha']),'iteration':int(z['iteration'])}
        for k in ['n','old_g','old_z','direction']:
            a=z[k];need(a.dtype==np.float64 and np.isfinite(a).all(),'Checkpoint array precision/values differ')
            s[k]=engine.xp.asarray(a).copy() if a.size else None
        s['pairs']=[(engine.xp.asarray(z['pair_s_'+str(i)]).copy(),engine.xp.asarray(z['pair_y_'+str(i)]).copy()) for i in range(int(z['pair_count']))]
    return s
