"""Small independent controls for corrected acquisition and observation."""
from pathlib import Path
import numpy as np
from .qualification import qualify
from .dependencies import fit_models,features,choose,predict
from .observer import observe
from .numerics import OFF_E,points

def test(repo):
 result=qualify(repo)
 cubic=[{'x':x,'y':1+x**3} for x in [-1.,-.6,-.2,.2,.6,1.]]
 fs=features(cubic,fit_models(cubic)[0]);assert any(k=='possible_inflection' for k,v in fs);assert not any(k=='turning_point' for k,v in fs)
 quadratic=[{'x':x,'y':.01+(x-.4)**2} for x in [0.,.2,.7,1.]];fs2=features(quadratic,fit_models(quadratic)[0]);assert any(k=='turning_point' and abs(v-.4)<1e-7 for k,v in fs2)
 n=17;L=8.;h=L/n;native=np.array([2*points(n,L,o,2,0)[...,i]+i for i,o in enumerate(OFF_E)]);line=np.linspace(-1,1,9);target=np.stack(np.meshgrid(line,line,line,indexing='ij'),-1);v=observe(native,OFF_E,target,h,L);ref=np.stack([2*target[...,i]+i for i in range(3)],-1);err=float(np.max(abs(v-ref)));assert err<1e-12
 power=[{'x':x,'y':.00001+.07*x**2,'variable':'spacing'} for x in [.05,.06,.08,.1,.12,.15,.18]];models=fit_models(power);p=next(m for m in models if m['model']=='offset_power');pe=float(max(abs(predict(p,np.array([.07,.11]))-(.00001+.07*np.array([.07,.11])**2))));assert pe<1e-8
 result['corrected_features']={'stationary_inflection_not_extremum':True,'quadratic_extremum_retained':True,'cubic_features':fs};result['observer_linear_exactness']=err;result['manufactured_offset_power_error']=pe
 return result

if __name__=='__main__':
 import argparse,json
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);a=p.parse_args();r=test(a.repo.resolve());print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='qualification_passed' else 1)
