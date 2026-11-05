"""S5-B-008 stationary tail-domain screening; no physical-time evolution.

Unchanged D4 nodal action and sf_readmission optimizer. Exact centred extension,
newly free former boundary layers, and recorded pre/post relaxation measurements.
Equation/source map: docs/models/SF-tail-domain-screening.md. Apache-2.0.
"""
import argparse
import csv
import fcntl
import json
from pathlib import Path
import platform
import signal
import subprocess
import sys
import threading
import time
import zipfile
import numpy as np
import scipy
from .sf_motion_diagnostics import ROOT,atomic_json,event,compact,load_rest,sha
from .sf_checkpoints import timestamp
from .sf_time import Grid,densities
from .sf_time_run import MODEL,SCHEME,canonical_sha,state_sha
from .sf_readmission import relax,stationarity,admitted,checkpoint
from .skyrme import NORTH
CONFIG=ROOT/'experiments/configs/s5-b/008-tail-domain-screening/study.json'
SCOPE='Stationary Q1/Q2 finite-domain tail screening only; no trajectory, reflection measurement, isolated-motion, charge, spin or electron acceptance.'
FILES=['sf_tail_domain.py','sf_readmission.py','sf_time.py','sf_time_run.py','sf_time_initial.py','sf_time_controls.py','sf_dynamics.py','skyrme.py','sf_motion_metrics.py','sf_motion_diagnostics.py','sf_dynamics_admission.py','sf_checkpoints.py']
READMISSION_FILES=['sf_readmission.py','sf_time.py','sf_dynamics.py','skyrme.py']
TERMINAL={'stationary','topology_unresolved','stationarity_unresolved'}
STOP=False

def need(ok,message):
    if not ok:raise ValueError(message)

def validate(c):
    need(c['format']=='EFT-tail-domain-v1','Unknown study format')
    need(c['source_seeds']==['q1-n101-L16','q2-n101-L16'],'Only declared Q1/Q2 retained references allowed')
    need(c['domains']==[{'nodes':101,'length':16.},{'nodes':113,'length':17.92},{'nodes':127,'length':20.16}],'Only L16 control and requested L17.92/L20.16 allowed')
    need(c['spacing']==.16 and c['shell_width']==2. and c['tail_fraction_limit']==.001,'Original spacing/shell/tail limit required')
    need(c['common_nodes']==73 and c['profile_half_widths']==[4.,5.,6.,7.,8.],'Fixed common analysis regions required')
    for d in c['domains']:need(abs(d['length']/(d['nodes']-1)-c['spacing'])<1e-14,'Domain spacing changed')
    r=c['readmission']
    need(r['relative_force_l2']==1e-4 and r['acceleration_max']==1e-3 and r['charge_relative_error']==.05,'Declared stricter stationary preparation targets required')
    need(r['iterations_per_pass']==200 and r['checkpoint_every']==25 and r['stagnation_relative_energy']==1e-10,'Original optimizer batching/stagnation policy required')

def exact_extension(n,target_nodes):
    """Same-centre, same-spacing copy: no interpolation, compression or taper."""
    need(n.ndim==4 and n.shape[-1]==3 and len(set(n.shape[:3]))==1 and n.dtype==np.float64,'Float64 cubic unit field required')
    old=n.shape[0];need(old%2==1 and target_nodes>=old and (target_nodes-old)%2==0,'Aligned odd centred grids required')
    out=np.broadcast_to(NORTH,(target_nodes,)*3+(3,)).copy();pad=(target_nodes-old)//2
    sl=tuple(slice(pad,pad+old) for _ in range(3));out[sl]=n
    need(np.array_equal(out[sl],n),'Centred source copy differs')
    return out

def centred_slice(nodes,count):
    need(count<=nodes and count%2==nodes%2,'Unaligned common crop')
    lo=(nodes-count)//2;return (slice(lo,lo+count),)*3

def shell_mask(grid,width):return np.any(abs(grid.points())>=np.asarray(grid.lengths)/2-width,axis=-1)

def fixed_coordinate_max(grid):
    # Integer offsets keep fixed physical masks identical across aligned domains.
    axes=[abs((np.arange(n)-(n-1)/2)*h) for n,h in zip(grid.shape,grid.spacing)]
    return np.maximum(np.maximum(axes[0][:,None,None],axes[1][None,:,None]),axes[2][None,None,:])

def density_summary(e,grid,width,common_nodes,profile):
    """Energy integrated over explicit fixed/moving laboratory regions."""
    need(e.shape==grid.shape and np.isfinite(e).all() and np.min(e)>=-1e-14,'Invalid continuum energy density')
    dv=float(np.prod(grid.spacing));total=float(np.sum(e)*dv);xyz=grid.points();shell=shell_mask(grid,width)
    energy=float(np.sum(e[shell])*dv);common=centred_slice(grid.shape[0],common_nodes);fixed_radius=fixed_coordinate_max(grid)
    centroid=np.sum(xyz*e[...,None],axis=(0,1,2))*dv/total if total>0 else np.zeros(3)
    radii=np.linalg.norm(xyz-centroid,axis=-1);order=np.argsort(radii.ravel());cum=np.cumsum(e.ravel()[order])
    def radius(f):return float(radii.ravel()[order[min(int(np.searchsorted(cum,f*np.sum(e))),len(order)-1)]]) if total>0 else None
    return {'continuum_energy':total,'shell_energy':energy,'shell_fraction':energy/total if total>0 else None,
        'shell_width':width,'shell_inner_half_lengths':(np.asarray(grid.lengths)/2-width).tolist(),
        'common_cube_nodes':common_nodes,'common_cube_side':(common_nodes-1)*grid.spacing[0],
        'common_cube_energy':float(np.sum(e[common])*dv),'centroid':centroid.tolist(),'radius_95':radius(.95),'radius_99':radius(.99),
        'outside_original_inner_cube_energy':float(np.sum(e[fixed_radius>=6.])*dv),
        'outside_original_box_energy':float(np.sum(e[fixed_radius>8.])*dv),
        'fixed_region_profile':[{'cube_half_width':a,'energy_outside':float(np.sum(e[fixed_radius>=a])*dv)} for a in profile if a<=min(grid.lengths)/2]}

def measure(n,grid,q,c):
    v=np.zeros_like(n);m=stationarity(n,grid);d=densities(n,v,grid)
    s=density_summary(d['energy_density'],grid,c['shell_width'],c['common_nodes'],c['profile_half_widths'])
    s.update(recorded_at=timestamp(),stationarity=m,discrete_hamiltonian=float(np.sum(d['hamiltonian_density'])*np.prod(grid.spacing)),
        integrated_stress=(np.sum(d['stress'],axis=(0,1,2))*np.prod(grid.spacing)).tolist(),
        fixed_field_max=float(np.max(abs(n[grid.fixed_mask()]-NORTH))),state_sha256=state_sha(n,v),
        tail_gate_pass=s['shell_fraction'] is not None and s['shell_fraction']<=c['tail_fraction_limit'],
        preparation_stationarity_pass=admitted(m,q,c['readmission']))
    return s

def compare_fields(a,ga,b,gb,count):
    """No fitted translation, rotation, phase or deformation; same physical nodes."""
    need(np.allclose(ga.spacing,gb.spacing,rtol=0,atol=1e-14),'Common crop requires equal spacing')
    aa=a[centred_slice(len(a),count)];bb=b[centred_slice(len(b),count)]
    den=float(np.linalg.norm(aa-NORTH));ea=densities(a,np.zeros_like(a),ga)['energy_density'][centred_slice(len(a),count)]
    eb=densities(b,np.zeros_like(b),gb)['energy_density'][centred_slice(len(b),count)]
    energy=float(np.sum(ea));diff=bb-aa
    return {'recorded_at':timestamp(),'common_nodes':count,'common_side':(count-1)*ga.spacing[0],
        'field_relative_l2':float(np.linalg.norm(diff)/den) if den>0 else None,
        'field_absolute_rms':float(np.sqrt(np.mean(diff*diff))),
        'energy_relative_difference':abs(float(np.sum(eb))-energy)/abs(energy) if energy else None,
        'density_relative_l1':float(np.sum(abs(eb-ea))/abs(energy)) if energy else None,
        'scope':'Fixed original-centre cube; density derivatives evaluated on each full domain, then cropped. Descriptive differences only; no new convergence tolerance.'}

def source_inventory(source,c):
    validate(c);source=Path(source).resolve()
    spec={'format':'EFT-motion-diagnostics-v1','evidence_sha256':c['source_evidence_sha256'],
        'case_ids':[s+'-b0-a0-dt0.01' for s in c['source_seeds']],
        'comparison_grids':[41],'shell_width':c['shell_width'],'replay_rtol':1e-9,'replay_atol':1e-11}
    ledger,plan,_,_,_=compact(source,spec);files={}
    need(plan['limits']['tail_fraction']==c['tail_fraction_limit'],'Original tail gate differs')
    need(c['readmission']['relative_force_l2']<plan['readmission']['relative_force_l2'] and c['readmission']['acceleration_max']<plan['readmission']['acceleration_max'],'Preparation targets must be stricter than originals')
    for sid in c['source_seeds']:
        n,g=load_rest(source,sid,ledger)
        need(np.isfinite(n).all() and np.max(abs(np.sum(n*n,axis=-1)-1))<1e-10 and np.max(abs(n[g.fixed_mask()]-NORTH))==0,'Invalid original rest field')
        need(g.shape==(101,)*3 and g.lengths==(16.,)*3 and g.spacing[0]==.16,'Source geometry changed')
        files[f'readmission/{sid}/latest.npz']=ledger['seeds'][sid]['field_sha256']
    return {'recorded_at':timestamp(),'source':str(source),'files':files,'input_fingerprint':canonical_sha(files),
        'source_evidence_sha256':c['source_evidence_sha256'],'original_readmission':plan['readmission'],'original_limits':plan['limits'],
        'scope':'Two original stationary fields authenticated without loading motion checkpoints.'},ledger

def seed_continuation(folder,n,g,q,full):
    """Legitimate iteration-zero restart for unchanged readmission, with model-correct metadata."""
    folder.mkdir(parents=True,exist_ok=True)
    codes={s:sha(Path(__file__).with_name(s)) for s in READMISSION_FILES};code=canonical_sha(codes);cfg=canonical_sha(full)
    m=stationarity(n,g);row={'recorded_at':timestamp(),'iteration':0,'pass_index':0,**m}
    atomic_json(folder/'config.json',full)
    atomic_json(folder/'manifest.json',{'started_at':timestamp(),'config_sha256':cfg,'code_sha256':code,'code_hashes':codes,'config':full,
        'model':MODEL,'scheme':SCHEME,'scope':'External exact-extension iteration-zero readmission state; no optimizer iteration has occurred.'})
    checkpoint(folder/'initial.npz',n,g,q,cfg,0,0,code);checkpoint(folder/'latest.npz',n,g,q,cfg,0,0,code)
    atomic_json(folder/'history.json',[row])

def checked_field(folder,full):
    p=folder/'latest.npz';m=json.loads((folder/'manifest.json').read_text())
    codes={s:sha(Path(__file__).with_name(s)) for s in READMISSION_FILES}
    need(m['config_sha256']==canonical_sha(full) and m['code_sha256']==canonical_sha(codes),'Readmission provenance differs')
    with np.load(p,allow_pickle=False) as d:
        n=d['field'].copy();v=d['field_rate'].copy();g=Grid((full['nodes'],)*3,(full['length'],)*3,'fixed')
        need(n.shape==g.shape+(3,) and n.dtype==np.float64 and np.isfinite(n).all(),'Invalid restart state')
        need(str(d['model_id'])==MODEL and str(d['scheme'])==SCHEME and int(d['expected_q'])==full['q'],'Restart model/scheme/Q differs')
        need(str(d['config_sha256'])==canonical_sha(full) and str(d['code_sha256'])==canonical_sha(codes),'Restart digest metadata differs')
        need(float(d['h'])==g.spacing[0] and np.max(abs(v))==0 and np.max(abs(n[g.fixed_mask()]-NORTH))==0,'Restart geometry/rate/boundary differs')
        need(np.max(abs(np.sum(n*n,axis=-1)-1))<1e-10,'Restart unit constraint differs')
    return n,g

def compact_evidence(out):
    paths=sorted(p for p in out.rglob('*') if p.is_file() and p.suffix in {'.json','.md','.csv','.png'}
        and p.name not in {'heartbeat.json','launch.json','exit.json','stop-request.json','evidence-hashes.json'})
    atomic_json(out/'evidence-hashes.json',{'recorded_at':timestamp(),'sha256':{p.relative_to(out).as_posix():sha(p) for p in paths}})
    with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths+[out/'evidence-hashes.json']:z.write(p,p.relative_to(out).as_posix())

def output(out,ledger):
    ledger['updated_at']=timestamp();atomic_json(out/'campaign.json',ledger)
    lines=['# S5-B-008 stationary tail-domain screening','',json.dumps(ledger['updated_at']), '',
        f"Status: **{ledger['status']}**. Recorded cases: {len(ledger['cases'])}/6.",'',
        '|Q|L|Status|Initial shell (%)|Final shell (%)|Original 0.1% gate|Strict stationarity|Iterations|',
        '|---|---:|---|---:|---:|---|---|---:|']
    rows=[]
    for key,r in ledger['cases'].items():
        a=r.get('initial',{});b=r.get('final',{});f=b.get('shell_fraction');ii=a.get('shell_fraction')
        lines.append(f"|{r['q']}|{r['length']}|{r['status']}|{100*ii if ii is not None else ''}|{100*f if f is not None else ''}|{b.get('tail_gate_pass','')}|{b.get('preparation_stationarity_pass','')}|{r.get('result',{}).get('iterations','')}|")
        rows.append({'recorded_at_utc':ledger['updated_at']['utc'],'recorded_at_melbourne':ledger['updated_at']['melbourne'],'case_id':key,'q':r['q'],'length':r['length'],'nodes':r['nodes'],'status':r['status'],
            'initial_tail_fraction':ii,'final_tail_fraction':f,'final_shell_energy':b.get('shell_energy'),'final_continuum_energy':b.get('continuum_energy'),
            'tail_gate_pass':b.get('tail_gate_pass'),'strict_stationarity_pass':b.get('preparation_stationarity_pass')})
    lines+=['','The initial larger-grid measurement is an exact north extension, not a re-equilibrated isolated field. Compare post-relaxation results and fixed physical regions.',
        'All six cases are attempted regardless of earlier tail passes. Unresolved stationary/topology cases are retained and cannot qualify a box.',
        SCOPE,'Full checkpoints must be archived and verified before any local deletion.','']
    (out/'SUMMARY.md').write_text('\n'.join(lines))
    if rows:
        with (out/'tail-metrics.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def comparisons(out,ledger,c):
    pairs=[]
    for q in [1,2]:
        rows=[(k,r) for k,r in ledger['cases'].items() if r['q']==q and r['status'] in TERMINAL and 'final' in r]
        for i,(ka,a) in enumerate(rows):
            for kb,b in rows[i+1:]:
                na,ga=checked_field(out/'readmission'/ka,a['relax_config']);nb,gb=checked_field(out/'readmission'/kb,b['relax_config'])
                pair={'a':ka,'b':kb,'q':q,'both_preparation_stationary':a['final']['preparation_stationarity_pass'] and b['final']['preparation_stationarity_pass'],
                    'common_core':compare_fields(na,ga,nb,gb,c['common_nodes']),
                    'original_footprint':compare_fields(na,ga,nb,gb,101)}
                pairs.append(pair)
    return {'recorded_at':timestamp(),'pairs':pairs,'scope':'Three pairwise domain comparisons per Q, with exact physical-node matching; no motion or automatic isolation acceptance.'}

def plot(out,ledger,c):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,5))
    for q,color in [(1,'#167c9a'),(2,'#b56033')]:
        rows=sorted((r for r in ledger['cases'].values() if r['q']==q and 'final' in r),key=lambda r:r['length'])
        for kind,style in [('initial','--o'),('final','-o')]:
            selected=[r for r in rows if r[kind]['shell_fraction'] is not None]
            ax.plot([r['length'] for r in selected],[100*r[kind]['shell_fraction'] for r in selected],style,color=color,label=f'Q{q} {kind}')
    ax.axhline(100*c['tail_fraction_limit'],color='#666',ls=':',label='Original 0.1% gate')
    ax.set(xlabel='Box side (model units)',ylabel='Continuum energy in outer shell (%)',title='Stationary tail-domain screen; shell width 2, spacing 0.16')
    ax.set_xticks([16,17.92,20.16]);ax.legend();ax.grid(alpha=.2)
    fig.text(.02,.01,json.dumps(timestamp()),fontsize=6);fig.tight_layout(rect=(0,.04,1,1));fig.savefig(out/'tail-domain.png',dpi=150);plt.close(fig)

def campaign(source,out,c,pass_limit=None):
    global STOP
    STOP=False;source=Path(source).resolve();out=Path(out).resolve();validate(c)
    need(not (out==source or out.is_relative_to(source)),'Output must be separate from original inputs')
    out.mkdir(parents=True,exist_ok=True);lock=(out/'.campaign.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('Campaign already running')
    inv,original=source_inventory(source,c);codes={s:sha(Path(__file__).with_name(s)) for s in FILES}
    identity={'config_sha256':canonical_sha(c),'input_fingerprint':inv['input_fingerprint'],'source_sha256':codes}
    if (out/'campaign.json').exists():
        ledger=json.loads((out/'campaign.json').read_text());need(all(ledger[k]==v for k,v in identity.items()),'Source/config/inputs changed; preserve run and use a fresh output')
    else:
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip())
        need(not dirty,'Commit the staged study before native computation')
        ledger={'record_id':out.name,'started_at':timestamp(),**identity,'source_commit':commit,'source_worktree_dirty':False,
            'scope':SCOPE,'cases':{},'source_original_readmission':inv['original_readmission'],
            'environment':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform()}}
    need(not ledger.get('status','').startswith('complete'),'Completed campaign is immutable; use a fresh output')
    ledger['status']='working';atomic_json(out/'plan.json',c);atomic_json(out/'inventory.json',inv);output(out,ledger)
    try:
        for sid in c['source_seeds']:
            original_n,original_grid=load_rest(source,sid,original);q=original['seed_configs'][sid]['q']
            for domain in c['domains']:
                if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt
                key=f'q{q}-n{domain["nodes"]}-L{domain["length"]:g}';folder=out/'readmission'/key
                r=ledger['cases'].get(key)
                if r and r['status'] in TERMINAL:
                    need(sha(folder/'latest.npz')==r['final_checkpoint_sha256'],'Completed checkpoint changed');continue
                if r is None:
                    n=exact_extension(original_n,domain['nodes']);g=Grid((domain['nodes'],)*3,(domain['length'],)*3,'fixed')
                    full={**c['readmission'],**domain,'q':q,'external_initial':{'method':'exact-centered-north-extension','source_rest_sha256':inv['files'][f'readmission/{sid}/latest.npz'],'initial_state_sha256':state_sha(n,np.zeros_like(n))}}
                    seed_continuation(folder,n,g,q,full)
                    r={'id':key,'q':q,**domain,'status':'working','relax_config':full,'initial_checkpoint_sha256':sha(folder/'initial.npz'),
                        'initial':measure(n,g,q,c),'embedding':{'recorded_at':timestamp(),'source_nodes':101,'padding_nodes_each_face':(domain['nodes']-101)//2,
                        'source_core_copied_bit_exact':True,'outside_extension':'north','formerly_fixed_layers_become_free':domain['nodes']>101}}
                    ledger['cases'][key]=r;atomic_json(folder/'embedding.json',r['embedding']);output(out,ledger)
                need(sha(folder/'initial.npz')==r['initial_checkpoint_sha256'],'Initial checkpoint changed')
                if r.get('resume_checkpoint_sha256'):need(sha(folder/'latest.npz')==r['resume_checkpoint_sha256'],'Sealed stopped checkpoint changed')
                checked_field(folder,r['relax_config'])
                r.pop('resume_checkpoint_sha256',None);r['status']='working';output(out,ledger)
                event('START stationary readmission',case_id=key)
                result=relax(r['relax_config'],folder,pass_limit=pass_limit);r.update(result=result,status=result['status'])
                n,g=checked_field(folder,r['relax_config']);r['final']=measure(n,g,q,c)
                r['final']['original_stationarity_pass']=admitted(r['final']['stationarity'],q,inv['original_readmission'])
                r['resume_checkpoint_sha256']=sha(folder/'latest.npz')
                if r['status'] in TERMINAL:r['final_checkpoint_sha256']=r['resume_checkpoint_sha256']
                atomic_json(folder/'tail-assessment.json',{'recorded_at':timestamp(),'initial':r['initial'],'final':r['final'],'status':r['status']})
                output(out,ledger);event('FINISHED stationary case',case_id=key,status=r['status'],tail_fraction=r['final']['shell_fraction'])
                if r['status']=='interrupted':raise KeyboardInterrupt
                if r['status']=='checkpointed':ledger['status']='checkpointed';output(out,ledger);compact_evidence(out);return ledger
        need(len(ledger['cases'])==6,'Case coverage differs')
        ledger['status']='complete_pending_review' if all(r['status']=='stationary' for r in ledger['cases'].values()) else 'complete_with_unresolved_pending_review'
        atomic_json(out/'comparisons.json',comparisons(out,ledger,c));plot(out,ledger,c)
    except KeyboardInterrupt:ledger['status']='stopped_checkpoint_retained'
    except Exception as error:
        ledger['status']='error';ledger['error']=str(error);output(out,ledger);compact_evidence(out);raise
    for relative,digest in inv['files'].items():need(sha(source/relative)==digest,'Original input changed during study')
    output(out,ledger);compact_evidence(out);return ledger

def main():
    global STOP
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,default=CONFIG);p.add_argument('--preflight',action='store_true')
    a=p.parse_args();c=json.loads(a.config.read_text())
    if a.preflight:
        result=source_inventory(a.source,c)[0];atomic_json(a.output,result);print(json.dumps(result,indent=2));return 0
    def stop(*_):
        global STOP
        STOP=True;raise KeyboardInterrupt
    if (a.output/'campaign.json').is_file():
        need(not json.loads((a.output/'campaign.json').read_text())['status'].startswith('complete'),'Completed campaign is immutable; use a fresh output')
    signal.signal(signal.SIGTERM,stop);a.output.mkdir(parents=True,exist_ok=True);clock=time.monotonic();done=threading.Event()
    def heart():
        while not done.wait(30):atomic_json(a.output/'heartbeat.json',{'recorded_at':timestamp(),'wall_seconds':time.monotonic()-clock})
    threading.Thread(target=heart,daemon=True).start()
    try:
        r=campaign(a.source,a.output,c)
        code=0 if r['status'].startswith('complete') else 2
    except Exception as error:
        atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':'error','error':str(error),'wall_seconds':time.monotonic()-clock});raise
    finally:done.set()
    atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':r['status'],'wall_seconds':time.monotonic()-clock,'exit_code':code})
    event('SUMMARY',status=r['status'],output=str(a.output),evidence=str(a.output/'evidence.zip'));return code
if __name__=='__main__':sys.exit(main())
