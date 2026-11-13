"""Small Yee Maxwell validation with exact staggered initial/boundary values.
E on edges at t=n*dt; B on faces at t=(n-1/2)*dt. c=eps0=mu0=1.
Hopfion uses exact driven outer guard layers; interior error only, not isolation.
"""
if not __debug__:raise RuntimeError('Run without Python optimization')
import argparse,hashlib,html,json,secrets,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
OFF_E=[(.5,0,0),(0,.5,0),(0,0,.5)];OFF_B=[(0,.5,.5),(.5,0,.5),(.5,.5,0)]
def stamp():
    t=datetime.now(timezone.utc);return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}
def derivative(a,h,axis,forward):return (np.roll(a,-1,axis)-a)/h if forward else (a-np.roll(a,1,axis))/h
def curl(f,h,forward):
    return np.stack([derivative(f[(i+2)%3],h,(i+1)%3,forward)-derivative(f[(i+1)%3],h,(i+2)%3,forward) for i in range(3)])
def points(n,length,offset,axis,phase):
    h=length/n;axes=[-length/2+(np.arange(n)+offset[i])*h for i in range(3)];p=np.stack(np.meshgrid(*axes,indexing='ij'),-1);p[...,axis]+=phase*h;return p

def case(n,axis,phase,kind,hopfion=None,length=8.,duration=.2):
    h=length/n;steps=max(1,int(np.ceil(duration/(.25*h/np.sqrt(3)))));dt=duration/steps
    def exact(p,t):
        if kind=='plane':
            q=np.sin(2*np.pi*(p[...,0]-t)/length);e=np.zeros_like(p);b=e.copy();e[...,1]=q;b[...,2]=q;return e,b
        return hopfion(p,t)
    ep=[points(n,length,o,axis,phase) for o in OFF_E];bp=[points(n,length,o,axis,phase) for o in OFF_B]
    e=np.array([exact(p,0.)[0][...,i] for i,p in enumerate(ep)]);b=np.array([exact(p,-dt/2)[1][...,i] for i,p in enumerate(bp)])
    mask=np.zeros((n,)*3,dtype=bool)
    for i in range(3):s=[slice(None)]*3;s[i]=[0,1,n-2,n-1];mask[tuple(s)]=True
    for j in range(steps):
        b-=dt*curl(e,h,True)
        if kind!='plane':
            for i,p in enumerate(bp):b[i][mask]=exact(p[mask],(j+.5)*dt)[1][...,i]
        e+=dt*curl(b,h,False)
        if kind!='plane':
            for i,p in enumerate(ep):e[i][mask]=exact(p[mask],(j+1)*dt)[0][...,i]
    errors={};numerator=0.;denominator=0.
    for label,fields,coords,t,part in [('E',e,ep,duration,0),('B',b,bp,duration-dt/2,1)]:
        num=0.;den=0.
        for i,p in enumerate(coords):
            roi=np.ones((n,)*3,dtype=bool) if kind=='plane' else np.all(abs(p)<=length/4,axis=-1)
            ref=exact(p,t)[part][...,i];num+=float(np.sum((fields[i][roi]-ref[roi])**2));den+=float(np.sum(ref[roi]**2))
        errors[label+'_relative_l2']=float(np.sqrt(num/max(den,1e-30)));numerator+=num;denominator+=den
    errors['combined_native_space_time_relative_l2']=float(np.sqrt(numerator/max(denominator,1e-30)))
    if not all(np.isfinite(value) for value in errors.values()):raise ValueError('Nonfinite Maxwell error')
    return {'nodes':n,'spacing':h,'axis':axis,'phase':phase,'kind':kind,'steps':steps,'dt':dt,'electric_time':duration,'magnetic_time':duration-dt/2,'errors':errors,'scope':'Plane: periodic exact control. Hopfion: exact driven two-layer boundary and fixed interior cube; each component compared at its own Yee location/time. No collocated energy, isolated-particle or topology claim.'}
def fourier_plane(n,length=8.,duration=.2):
    from electron_field_topology.evolution import FourierMaxwell
    p=points(n,length,(0,0,0),0,0.);q=np.sin(2*np.pi*p[...,0]/length);e=np.zeros_like(p);b=e.copy();e[...,1]=q;b[...,2]=q
    solver=FourierMaxwell(e,b,length/n,project=False);solver.advance(duration);ee,bb=solver.fields();ref=np.sin(2*np.pi*(p[...,0]-duration)/length);er=ee[...,1]-ref;br=bb[...,2]-ref
    return {'nodes':n,'relative_l2':float(np.sqrt((np.sum(er*er)+np.sum(br*br))/(2*np.sum(ref*ref)))),'scope':'Collocated periodic plane wave at a common physical time; separate exact-solution error, not direct pointwise Yee-array subtraction.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);a=p.parse_args();repo=a.repo.expanduser().resolve();sys.path.insert(0,str(repo/'src'))
    expected_sources={'fields.py': '1926edeeabb360b77f87eb8f00bcce412ab102b540d9d5282e56007e0f577688', 'evolution.py': 'c1a3b8820fc192ce25fca332004623be838d400404830ddbabaf97d35d3d8735'}
    for name,h in expected_sources.items():
        if hashlib.sha256((repo/'src/electron_field_topology'/name).read_bytes()).hexdigest()!=h:raise ValueError('Maxwell source changed: '+name)
    from electron_field_topology.fields import hopfion
    cfg=json.loads(a.plan.read_text());expected={'nodes':[33,49,65],'axes':[2,0],'phases':[0.,.25,.5,.75],'length':8.,'duration':.2};assert cfg==expected,'Bounded Maxwell plan differs'
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    qp=repo/'artifacts/METHOD-QUALIFICATION-CURRENT'
    if not qp.is_file():raise ValueError('Run qualification first')
    qualification=Path(qp.read_text().strip())
    if json.loads(qualification.read_text())['status']!='qualification_passed':raise ValueError('Qualification incomplete')
    out=repo/'artifacts/maxwell-yee-alignment'/(datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+secrets.token_hex(4));out.mkdir(parents=True);(repo/'artifacts/MAXWELL-YEE-ALIGNMENT-CURRENT').write_text(str(out)+'\n')
    r={'recorded_at':stamp(),'status':'working','output':str(out),'plan':cfg,'script_sha256':sha(Path(__file__)),'python':sys.version,'numpy':np.__version__,'dependency_sha256':{name:sha(repo/name) for name in ['pyproject.toml','uv.lock']},'source_sha256':{n:sha(repo/'src/electron_field_topology'/n) for n in ['fields.py','evolution.py']},'cases':[],'fourier_controls':[]}
    def save():
        (out/'study.json').write_text(json.dumps(r,indent=2)+'\n');(out/'status.json').write_text(json.dumps({k:v for k,v in r.items() if k!='cases'}|{'completed_cases':len(r['cases'])},indent=2)+'\n')
    try:
        for n in cfg['nodes']:
            r['fourier_controls'].append(fourier_plane(n));r['cases'].append(case(n,0,0.,'plane'));save()
            for axis in cfg['axes']:
                for phase in cfg['phases']:
                    print(json.dumps({'recorded_at':stamp(),'message':'Yee Hopfion alignment','nodes':n,'axis':axis,'phase':phase}),flush=True)
                    r['cases'].append(case(n,axis,phase,'hopfion',hopfion));save()
        r.update(status='complete_pending_review',finished_at=stamp());save();rows=''
        for c in r['cases']:rows+=f'<tr><td>{c["kind"]}</td><td>{c["nodes"]}</td><td>{c["axis"]}</td><td>{c["phase"]}</td><td>{c["errors"]["combined_native_space_time_relative_l2"]:.8g}</td></tr>'
        (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Maxwell Yee alignment</title><style>body{font:16px system-ui;margin:30px}td,th{padding:9px}</style><h1>Maxwell Yee validation</h1><p>'+html.escape(json.dumps(r['finished_at']))+'</p><p>Separate Maxwell control; no SF Q3 validation. Hopfion boundary values are analytically prescribed. E/B errors use native staggered space/time samples. No energy-conservation, exact-nullness or knot-persistence claim.</p><table><tr><th>Field</th><th>N</th><th>Axis</th><th>Phase</th><th>Combined relative L2</th></tr>'+rows+'</table></html>')
        (out/'qualification.json').write_bytes(qualification.read_bytes());(out/Path(__file__).name).write_bytes(Path(__file__).read_bytes());(out/'CASE_PLAN.json').write_bytes(a.plan.read_bytes());(out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file()))
        with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in out.iterdir():
                if f.is_file() and f.name!='evidence.zip':z.write(f,f.name)
        print('Upload: '+str(out/'evidence.zip'));print('Browser report: '+str(out/'REPORT.html'))
    except BaseException as e:r.update(status='error',error=str(e),finished_at=stamp());save();raise
if __name__=='__main__':main()
