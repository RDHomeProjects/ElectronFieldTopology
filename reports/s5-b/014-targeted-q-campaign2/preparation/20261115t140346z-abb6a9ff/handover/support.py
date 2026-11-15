import hashlib,json,os
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
def stamp():
 t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def log(message,**kw):print(json.dumps({'recorded_at':stamp(),'message':message,**kw}),flush=True)
def load(p):return json.loads(Path(p).read_text())
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def need(v,s):
 if not v:raise RuntimeError(s)
def verify_package():
 seen=set()
 for line in (ROOT/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);p=(ROOT/n).resolve();need(p.is_relative_to(ROOT) and n not in seen and p.is_file() and sha(p)==h,'Package mismatch: '+n);seen.add(n)
 actual={f.relative_to(ROOT).as_posix() for f in ROOT.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.name!='SHA256SUMS'}
 need(seen==actual,'Package coverage differs')
 return sha(ROOT/'SHA256SUMS')
def proximity(m):return max(m['relative_force_l2']/1e-4,m['acceleration_max']/1e-3)
def contingency(h,start):
 import numpy as np
 end=h[-1]['iteration'];x=np.array([v['iteration'] for v in h],float)
 if end-start<100:return False,{'reason':'two full50-step windows unavailable'}
 windows=[]
 for lo,hi in [(end-100,end-50),(end-50,end)]:
  grid=np.arange(lo,hi+.1,5.0);force=np.exp(np.interp(grid,x,np.log([max(v['relative_force_l2'],1e-300) for v in h])));accel=np.exp(np.interp(grid,x,np.log([max(v['acceleration_max'],1e-300) for v in h])));joint=np.maximum(force/1e-4,accel/1e-3)
  windows.append({'iterations':[int(lo),int(hi)],'median_joint_gate_multiple':float(np.median(joint)),'median_acceleration':float(np.median(accel))})
 previous,recent=windows;progress=recent['median_joint_gate_multiple']<=.95*previous['median_joint_gate_multiple'];safe=recent['median_acceleration']<=1.1*previous['median_acceleration']
 return progress and safe,{'previous_window':previous,'recent_window':recent,'joint_progress_5pct':progress,'acceleration_not_worse_10pct':safe,'scope':'Uniform5-step log interpolation prevents dense observation counts from dominating window medians; no initial-state improvement override'}
def observation_interval(h,current,q):
 m=h[-1];gap=5 if proximity(m)<=2 else min(20,current+2);reasons=[]
 if len(h)>=3:
  a,b,c=h[-3:]
  for k in ['relative_force_l2','acceleration_max']:
   va,vb,vc=[max(v[k],1e-300) for v in [a,b,c]]
   import math
   s1=(math.log(vb)-math.log(va))/max(1,b['iteration']-a['iteration']);s2=(math.log(vc)-math.log(vb))/max(1,c['iteration']-b['iteration'])
   pred=math.exp(max(-700,min(700,math.log(vb)+s1*(c['iteration']-b['iteration']))))
   if s1*s2<0 or abs(pred-vc)/vc>.25:gap=max(1,current//2);reasons.append(k+' reversal/curvature/prediction discrepancy')
 if len(h)>=4:
  import math
  for k in ['relative_force_l2','acceleration_max']:
   v=h[-4:];slopes=[(math.log(max(b[k],1e-300))-math.log(max(a[k],1e-300)))/max(1,b['iteration']-a['iteration']) for a,b in zip(v,v[1:])]
   if (slopes[1]-slopes[0])*(slopes[2]-slopes[1])<0:
    gap=min(gap,max(1,current//2));reasons.append(k+' log-curve inflection candidate')
 if q==5:
  gap=min(gap,5)
  if abs(abs(m['hopf_integral'])-q)/q>=.03 or m['minimum_corner_cone']<.5:gap=1;reasons.append('representation margin narrowed')
 return max(1,gap),reasons or ['smooth trend; bounded wider spacing']
