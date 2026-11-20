"""Declared rational-map starts; labels are not final knot identifications."""
import numpy as np
def catalogue(p):
 out=[]
 for q in p['q_values']:
  a,b=min([(a,q//a) for a in range(1,q+1) if q%a==0 and a>=q//a],key=lambda x:max(x))
  out.append(dict(id=f'q{q}-axial-{a}-{b}',q=q,kind='axial',alpha=a,beta=b,scale=4.,cutoff=8.8,amplitude=1.))
  a,b=min([(a,b) for a in range(1,q) for b in range(1,q) if 2*a+7*b==q],key=lambda x:(abs(2*x[0]-7*x[1]),sum(x)))
  out.append(dict(id=f'q{q}-torus72-{a}-{b}',q=q,kind='torus72',alpha=a,beta=b,scale=4.,cutoff=8.8,amplitude=4.))
 out.extend([dict(id='q22-cable-source-family',q=22,kind='cable',alpha=4,beta=1,scale=4.,cutoff=7.2,amplitude=8.),dict(id='q22-torus54-source-family',q=22,kind='torus54',alpha=3,beta=2,scale=4.,cutoff=7.2,amplitude=4.)])
 return out
def field(g,s):
 from electron_field_topology.skyrme import rational_field,NORTH
 a,b=s['alpha'],s['beta'];degree=a*b if s['kind']=='axial' else (2*a+7*b if s['kind']=='torus72' else (4*a+5*b if s['kind']=='torus54' else 4*a+6*b))
 if degree!=s['q']:raise ValueError('Rational-map degree differs from declared label')
 n=rational_field(g.points(),**{k:v for k,v in s.items() if k not in ['q','id']})
 # Same small smooth target-space perturbation for all starts, vanishing in vacuum.
 x=g.points();omega=.005*(1-n[...,2])[...,None]*np.stack([np.sin(.7*x[...,0]+.3*x[...,1]),np.sin(.5*x[...,1]-.4*x[...,2]),np.sin(.3*x[...,2]+.2*x[...,0])],axis=-1)
 theta=np.linalg.norm(omega,axis=-1);cross=np.cross(omega,n)
 n=n+np.sinc(theta/np.pi)[...,None]*cross+(.5*np.sinc(theta/(2*np.pi))**2)[...,None]*np.cross(omega,cross);n/=np.linalg.norm(n,axis=-1,keepdims=True)
 if np.max(abs(n[g.fixed_mask()]-NORTH))>1e-12:raise ValueError('Seed support reaches fixed layers')
 n[g.fixed_mask()]=NORTH;return n
