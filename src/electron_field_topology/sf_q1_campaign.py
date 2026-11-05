"""Paired Q1 tail settling from an authenticated retained endpoint. Apache-2.0."""
import argparse
import fcntl
import json
from pathlib import Path
import platform
import signal
import subprocess
import sys
import threading
import time
import numpy as np
import scipy
from .sf_motion_diagnostics import ROOT,atomic_json,event,sha
from .sf_checkpoints import timestamp
from .sf_time import Grid
from .sf_time_run import MODEL,SCHEME,canonical_sha,state_sha
from .sf_tail_domain import exact_extension,compare_fields,compact_evidence
from .sf_q1_metrics import measure
from .sf_q1_settling import seed,checked,relax_settling,code_hashes
from .skyrme import NORTH
CONFIG=ROOT/'experiments/configs/s5-b/009-q1-tail-settling/study.json'
SOURCE_RUN='20261105t053203z-576d1edc'
SOURCE_FILE='readmission/q1-n127-L20.16/latest.npz'
SOURCE_SHA='2eafd171bf4f8bb184b89cadb63435970d8eb8b8c44496d61e8d576c237dd343'
SOURCE_STATE='5d56a1586f7bae19c1ee90e208a096556ba3d226eddc1d2b870bee924fb7d832'
SCOPE='Q1 stationary optimizer/tail settling only; no trajectory, reflection test, independent basin, physical-mesh convergence, isolated motion, charge, spin or electron acceptance.'
TERMINAL={'settled','stationarity_unresolved','topology_unresolved','settling_budget_exhausted'}
STOP=False

def need(ok,message):
    if not ok:raise ValueError(message)

def validate(c):
    need(c['format']=='EFT-q1-tail-settling-v1','Unknown study format')
    need(c['domains']==[{'nodes':127,'length':20.16},{'nodes':139,'length':22.08}],'Declared paired domains only')
    need(c['spacing']==.16 and c['shell_width']==2. and c['tail_fraction_limit']==.001,'Original spacing/shell limit required')
    need(c['common_nodes']==73 and c['profile_half_widths']==[4.,5.,6.,7.,8.,9.],'Fixed physical profiles required')
    need(c['max_iterations_per_case']==1200 and c['observe_every']==100 and c['stable_intervals']==3,'Declared overnight work allocation required')
    for key,value in {'tail_fraction_change':1e-7,'shell_energy_change':1e-7,'core_field_relative_change':1e-5,'hamiltonian_relative_change':1e-9}.items():need(c[key]==value,'Settling threshold differs: '+key)
    r=c['readmission']
    need(r=={'relative_force_l2':1e-9,'acceleration_max':1e-8,'charge_relative_error':.05,'iterations_per_pass':200,'checkpoint_every':25,'stagnation_relative_energy':1e-14},'Strict preparation policy differs')
    for d in c['domains']:need(abs(d['length']/(d['nodes']-1)-c['spacing'])<1e-14,'Spacing differs')

def source_inventory(source,c):
    validate(c);source=Path(source).resolve();path=source/SOURCE_FILE
    need(path.is_file(),'Retained Q1 endpoint missing: '+str(path))
    need(sha(path)==SOURCE_SHA,'Retained Q1 endpoint SHA-256 differs; no substitute/regeneration permitted')
    record=json.loads((ROOT/f'reports/s5-b/008-tail-domain-screening/runs/{SOURCE_RUN}/campaign.json').read_text())['cases']['q1-n127-L20.16']
    need(record['final_checkpoint_sha256']==SOURCE_SHA and record['final']['state_sha256']==SOURCE_STATE,'Published source record differs')
    codes={n:sha(Path(__file__).with_name(n)) for n in ['sf_readmission.py','sf_time.py','sf_dynamics.py','skyrme.py']}
    g=Grid((127,)*3,(20.16,)*3,'fixed')
    with np.load(path,allow_pickle=False) as d:
        n=d['field'].copy();v=d['field_rate'].copy()
        need(n.shape==g.shape+(3,) and n.dtype==np.float64 and np.isfinite(n).all(),'Invalid source field')
        need(str(d['model_id'])==MODEL and str(d['scheme'])==SCHEME and int(d['expected_q'])==1 and float(d['h'])==g.spacing[0],'Source model/grid/Q differs')
        need(str(d['config_sha256'])==canonical_sha(record['relax_config']) and str(d['code_sha256'])==canonical_sha(codes),'Source embedded identity differs')
        need(np.max(abs(v))==0 and np.max(abs(n[g.fixed_mask()]-NORTH))==0 and np.max(abs(np.sum(n*n,axis=-1)-1))<1e-10,'Invalid source constraints')
        need(state_sha(n,v)==SOURCE_STATE,'Source state differs')
    inv={'recorded_at':timestamp(),'source':str(source),'files':{SOURCE_FILE:SOURCE_SHA},'input_fingerprint':canonical_sha({SOURCE_FILE:SOURCE_SHA}),
        'source_run':SOURCE_RUN,'source_state_sha256':SOURCE_STATE,'original_readmission':record['relax_config'],
        'source_release':'archive-workstation-20261105t063134z-4cd07212','scope':'Only authenticated Q1 L20.16 endpoint required; Q2 references remain unchanged.'}
    return inv,n

def output(out,d):
    import csv
    d['updated_at']=timestamp();atomic_json(out/'campaign.json',d)
    lines=['# S5-B-009 paired Q1 stationary tail settling','',json.dumps(d['updated_at']),'',f"Status: **{d['status']}**. Cases: {len(d['cases'])}/2.",'',
        '|Case|Status|Iterations|Tail (%)|0.1% shell gate|Strict stationarity|Settled|','|---|---|---:|---:|---|---|---|']
    rows=[]
    for key,r in d['cases'].items():
        f=r.get('final',r.get('initial',{}));frac=f.get('shell_fraction');it=r.get('result',{}).get('iterations',0)
        lines.append(f"|{key}|{r['status']}|{it}|{100*frac if frac is not None else ''}|{f.get('tail_gate_pass','')}|{f.get('preparation_stationarity_pass','')}|{r['status']=='settled'}|")
        rows.append({'recorded_at_utc':d['updated_at']['utc'],'recorded_at_melbourne':d['updated_at']['melbourne'],'case_id':key,'status':r['status'],'iterations':it,'tail_fraction':frac,'shell_energy':f.get('shell_energy'),'continuum_energy':f.get('continuum_energy'),'strict_stationarity':f.get('preparation_stationarity_pass'),'tail_pass':f.get('tail_gate_pass'),'settled':r['status']=='settled'})
    lines+=['','Initial north extension is a geometric control. Settling uses three distinct 100-iteration intervals and tighter force targets; it is independent of passing the shell limit.',
        'A budget or numerical-stagnation endpoint is unresolved and retained. All intermediate observation fields are archived. No automatic motion qualification.',SCOPE,'']
    (out/'SUMMARY.md').write_text('\n'.join(lines))
    if rows:
        with (out/'tail-metrics.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def compare_final(out,d,c):
    keys=list(d['cases']);a,b=[d['cases'][k] for k in keys]
    na,ga=checked(out/'readmission'/keys[0],a['relax_config']);nb,gb=checked(out/'readmission'/keys[1],b['relax_config'])
    return {'recorded_at':timestamp(),'a':keys[0],'b':keys[1],'both_settled':all(r['status']=='settled' for r in [a,b]),
        'regions':[compare_fields(na,ga,nb,gb,n) for n in [73,101,127]],
        'scope':'Raw same-centre equal-spacing comparison; derivatives on full domains before cropping; no domain-independence acceptance threshold.'}

def plot(out,d,c):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for key in d['cases']:
        p=out/'readmission'/key/'observations.json'
        if not p.exists():continue
        rows=json.loads(p.read_text());x=[r['iteration'] for r in rows]
        axes[0].plot(x,[100*r['shell_fraction'] for r in rows],'-o',label=key)
        axes[1].semilogy(x,[max(r['stationarity']['relative_force_l2'],1e-20) for r in rows],'-o',label=key)
    axes[0].axhline(.1,ls=':',color='black',label='Original 0.1% gate');axes[0].set(ylabel='Outer-shell energy (%)')
    axes[1].axhline(c['readmission']['relative_force_l2'],ls=':',color='black');axes[1].set(ylabel='Relative force')
    for ax in axes:ax.set_xlabel('Optimization iteration (not physical time)');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle('Q1 tail settling; original Hamiltonian and shell criterion');fig.text(.01,.01,json.dumps(timestamp()),fontsize=6)
    fig.tight_layout(rect=(0,.05,1,.92));fig.savefig(out/'tail-domain.png',dpi=150);plt.close(fig)

def campaign(source,out,c,pass_limit=None):
    global STOP
    STOP=False;source=Path(source).resolve();out=Path(out).resolve();validate(c)
    need(out!=source and not out.is_relative_to(source),'Output must be separate from original input')
    out.mkdir(parents=True,exist_ok=True);lock=(out/'.campaign.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('Campaign already running')
    inv,original_n=source_inventory(source,c);identity={'config_sha256':canonical_sha(c),'input_fingerprint':inv['input_fingerprint'],'source_sha256':code_hashes()}
    if (out/'campaign.json').exists():
        d=json.loads((out/'campaign.json').read_text());need(all(d[k]==v for k,v in identity.items()),'Code/config/input differs')
    else:
        need(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip(),'Commit preparation before native computation')
        d={'record_id':out.name,'started_at':timestamp(),**identity,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'source_worktree_dirty':False,'scope':SCOPE,'cases':{},'environment':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform()}}
    need(not d.get('status','').startswith('complete'),'Completed campaign is immutable')
    d['status']='working';d.pop('error',None);atomic_json(out/'plan.json',c);atomic_json(out/'inventory.json',inv);output(out,d)
    try:
        for domain in c['domains']:
            if STOP or (out/'stop-request.json').exists():raise KeyboardInterrupt
            key=f'q1-n{domain["nodes"]}-L{domain["length"]:g}';folder=out/'readmission'/key;r=d['cases'].get(key)
            if r and r['status'] in TERMINAL:
                need(sha(folder/'latest.npz')==r['final_checkpoint_sha256'],'Completed endpoint changed');continue
            if r is None:
                n=exact_extension(original_n,domain['nodes']);g=Grid((domain['nodes'],)*3,(domain['length'],)*3,'fixed')
                full={**c['readmission'],**domain,'q':1,'external_initial':{'source_sha256':SOURCE_SHA,'initial_state_sha256':state_sha(n,np.zeros_like(n))}}
                seed(folder,n,g,full)
                r={'id':key,'q':1,**domain,'status':'working','relax_config':full,'initial_checkpoint_sha256':sha(folder/'initial.npz'),'initial':measure(n,g,1,c),
                    'embedding':{'recorded_at':timestamp(),'source_nodes':127,'padding_nodes_each_face':(domain['nodes']-127)//2,'source_core_copied_bit_exact':True,'outside_extension':'north','formerly_fixed_layers_become_free':domain['nodes']>127}}
                d['cases'][key]=r;atomic_json(folder/'embedding.json',r['embedding']);output(out,d)
            need(sha(folder/'initial.npz')==r['initial_checkpoint_sha256'],'Initial field changed')
            if r.get('resume_checkpoint_sha256'):need(sha(folder/'latest.npz')==r['resume_checkpoint_sha256'],'Sealed stopped checkpoint changed')
            checked(folder,r['relax_config']);r.pop('resume_checkpoint_sha256',None);r['status']='working';output(out,d)
            event('START paired stationary settling',case_id=key)
            result=relax_settling(r['relax_config'],folder,c,pass_limit=pass_limit)
            n,g=checked(folder,r['relax_config']);r.update(result=result,status=result['status'],final=measure(n,g,1,c),resume_checkpoint_sha256=sha(folder/'latest.npz'))
            r['final']['previous_preparation_stationarity_pass']=__import__('electron_field_topology.sf_readmission',fromlist=['admitted']).admitted(r['final']['stationarity'],1,inv['original_readmission'])
            if r['status'] in TERMINAL:r['final_checkpoint_sha256']=r['resume_checkpoint_sha256']
            atomic_json(folder/'tail-assessment.json',{'recorded_at':timestamp(),'initial':r['initial'],'final':r['final'],'status':r['status']});output(out,d)
            event('FINISHED paired stationary case',case_id=key,status=r['status'],tail_fraction=r['final']['shell_fraction'],iterations=result['iterations'])
            if r['status']=='interrupted':raise KeyboardInterrupt
            if r['status']=='checkpointed':d['status']='checkpointed';output(out,d);compact_evidence(out);return d
        need(len(d['cases'])==2,'Paired case coverage differs')
        d['status']='complete_pending_review' if all(r['status']=='settled' for r in d['cases'].values()) else 'complete_with_unresolved_pending_review'
        atomic_json(out/'comparisons.json',compare_final(out,d,c));plot(out,d,c)
    except KeyboardInterrupt:d['status']='stopped_checkpoint_retained'
    except Exception as e:d['status']='error';d['error']=str(e);output(out,d);compact_evidence(out);raise
    need(sha(source/SOURCE_FILE)==SOURCE_SHA,'Original input changed during run')
    output(out,d);compact_evidence(out);return d

def main():
    global STOP
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,default=CONFIG);p.add_argument('--preflight',action='store_true');a=p.parse_args();c=json.loads(a.config.read_text())
    if a.preflight:print(json.dumps(source_inventory(a.source,c)[0],indent=2));return 0
    def stop(*_):
        global STOP
        STOP=True;raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop);a.output.mkdir(parents=True,exist_ok=True);clock=time.monotonic();done=threading.Event()
    def heart():
        while not done.wait(30):atomic_json(a.output/'heartbeat.json',{'recorded_at':timestamp(),'wall_seconds':time.monotonic()-clock})
    threading.Thread(target=heart,daemon=True).start()
    try:r=campaign(a.source,a.output,c);code=0 if r['status'].startswith('complete') else 2
    except Exception as e:
        atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':'error','error':str(e),'wall_seconds':time.monotonic()-clock});raise
    finally:done.set()
    atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':r['status'],'wall_seconds':time.monotonic()-clock,'exit_code':code});event('SUMMARY',status=r['status'],output=str(a.output),evidence=str(a.output/'evidence.zip'));return code
if __name__=='__main__':sys.exit(main())
