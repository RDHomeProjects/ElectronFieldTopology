import os
from pathlib import Path
import numpy as np
from common import canonical,need,save,sha,stamp

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
