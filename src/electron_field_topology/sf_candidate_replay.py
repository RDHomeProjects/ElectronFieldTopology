"""Repeat frozen full-field candidate measurements without relaxation or evolution.

Read-only scientific re-evaluation; writes only to a new output directory.
It shares the named frozen instruments and is not independent physics validation.
Apache-2.0.
"""
import argparse,importlib.util,json,math,sys,time
from pathlib import Path
import numpy as np
from .sf_higher_q_sources import ROOT,load,event,need
from .sf_checkpoints import timestamp,atomic_json
from .sf_candidate_survey import metrics,comparison
from .sf_candidate_motion import rest_state,at,local_path,temporal_comparison
from .sf_time import Grid,diagnostics
from .sf_time_run import state_sha
from .sf_temporal import coast_reference
from .sf_motion_metrics import evaluate
from .sf_reconstruction import phase_comparison
def equal(got,want,path='',counts=None):
    counts=counts if counts is not None else {'numeric':0,'max_absolute_difference':0.}
    if isinstance(want,dict):
        for k,v in want.items():
            if k not in {'recorded_at','scope','topology_scope'}:equal(got[k],v,path+'/'+k,counts)
    elif isinstance(want,list):
        need(len(got)==len(want),'List differs '+path)
        for i,(a,b) in enumerate(zip(got,want)):equal(a,b,path+'/'+str(i),counts)
    elif isinstance(want,bool):need(bool(got)==want,'Gate differs '+path)
    elif isinstance(want,(int,float)):
        need(math.isfinite(got) and math.isclose(got,want,rel_tol=1e-8,abs_tol=1e-11),'Numeric replay differs '+path);counts['numeric']+=1;counts['max_absolute_difference']=max(counts['max_absolute_difference'],abs(got-want))
    else:need(got==want,'Value differs '+path)
    return counts
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case');a=p.parse_args();out=a.run.resolve();need(not a.output.exists(),'Replay requires a new output directory');need(not a.output.resolve().is_relative_to(out),'Do not write replay outputs into the immutable run')
    spec=importlib.util.spec_from_file_location('candidate_seal_audit',ROOT/'scripts/check_candidate_survey.py');tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool);event('Authenticating complete run before replay');audit=tool.audit(out,ROOT)
    d=load(out/'campaign.json');c=load(out/'plan.json');counts={'numeric':0,'max_absolute_difference':0.};clock=time.monotonic();rest=[];cases=[]
    needed={r['rest_id'] for r in d['cases'].values() if not a.case or r['id']==a.case}
    if a.case:need(a.case in d['cases'],'Unknown case ID')
    for r in d['rest'].values():
        if a.case and r['id'] not in needed:continue
        g=Grid((r['nodes'],)*3,(r['length'],)*3,'fixed');event('Replaying stationary field',rest_id=r['id'])
        for role,path,want in [('initial',out/'rest'/r['id']/'initial.npz',r['initial']),('final',out/r['checkpoint'],r['final'])]:
            with np.load(path,allow_pickle=False) as z:n=z['field'].copy();v=z['field_rate'].copy()
            need(v.dtype==n.dtype==np.float64 and np.max(abs(v))==0 and n.shape==g.shape+(3,),'Rest precision/geometry/rate differs');got=metrics(n,g,c);equal(got,want,r['id']+'/'+role,counts);rest.append({'rest_id':r['id'],'role':role,'metrics':got})
    for r in d['cases'].values():
        if a.case and r['id']!=a.case:continue
        if not r.get('physical') or r.get('final_time',0)<=0:cases.append({'case_id':r['id'],'status':r['status'],'scope':'No positive-time evolved endpoint to replay; admitted/checkpoint seals remain audited'});continue
        parent=d['rest'][r['rest_id']];nrest,rg=rest_state(out,parent);g=Grid(tuple(r['physical']['grid']),tuple(r['physical']['lengths']),'fixed');hist=load(out/'cases'/r['id']/'history-combined.json');targets={float(k):v['assessment'] for k,v in r['milestones'].items()};targets[r['final_time']]=r.get('assessment',targets.get(r['final_time']));records=[]
        for t,want in sorted(targets.items()):
            if not want or t<=0:continue
            event('Replaying moving endpoint',case_id=r['id'],time=t);n,v=at(out,r,t);hh=[x for x in hist if x['time']<=t+1e-12];legacy=evaluate(hh,n,v,g,nrest,rg.spacing[0],r['beta'],r['axis'],r['q'],c['shell_width'],c['limits']);equal(legacy,want['legacy_motion'],r['id']+'/legacy',counts);ref,_=coast_reference(nrest,rg,g,r['beta'],r['axis'],t);phase=phase_comparison(n,ref);equal(phase,want['projected_cubic_reference_raw'],r['id']+'/cubic',counts);diag=diagnostics(n,v,g)
            for k in ['energy','continuum_energy','momentum','centroid','unit_error','tangency_error','rms_radius']:equal(diag[k],hh[-1][k],r['id']+'/'+k,counts)
            records.append({'time':t,'legacy_motion':legacy,'projected_cubic_reference_raw':phase,'state_sha256':state_sha(n,v)})
        cases.append({'case_id':r['id'],'native_status':r['status'],'endpoints':records})
    comparisons=[]
    if not a.case:
        for key,row in d['comparisons'].items():
            event('Replaying matched comparison',comparison=key);kind=row.get('kind')
            if key.endswith('-temporal'):
                qkey=key.split('-')[0];selection=d['selected'][qkey];fine=selection.get('levels',{}).get('fine',{}).get('primary_rest');rows=[d['cases'].get(fine+f'-z-dt{dt:g}') for dt in c['time_steps']] if fine else [None]*3;got=temporal_comparison(out,rows,c)
            elif kind in {'fixed-box-physical-mesh','matched-spacing-domain'}:
                left,right=[d['cases'].get(x) if x else None for x in row['case_ids']];got=comparison(out,left,right,c,row['role'],kind)
            elif kind=='same-grid-fresh-warm-rest':
                left,right=[d['rest'][x] for x in row['rest_ids']];n,_=rest_state(out,left);m,_=rest_state(out,right)
                from .skyrme import NORTH
                got={**row,'field_relative_l2':float(np.linalg.norm(n-m)/max(np.linalg.norm(m-NORTH),1e-30)),'energy_relative_difference':abs(left['final']['stationarity']['energy']-right['final']['stationarity']['energy'])/abs(right['final']['stationarity']['energy'])}
            else:raise ValueError('Unknown comparison type '+key)
            equal(got,row,key,counts);comparisons.append({'id':key,'replayed':got})
    a.output.mkdir(parents=True);result={'recorded_at':timestamp(),'run':d['record_id'],'scope':'Frozen-instrument full-field replay, no new trajectory/optimization. Between-snapshot diagnostic histories are authenticated and reused, not reconstructed from absent fields.','case_selection':a.case,'audit':audit,'numeric_comparisons':counts,'rest':rest,'cases':cases,'comparisons':comparisons,'wall_seconds':time.monotonic()-clock,'python':sys.version,'numpy':np.__version__};atomic_json(a.output/'field-replay.json',result);event('Read-only field replay passed',output=str(a.output/'field-replay.json'),counts=counts)
if __name__=='__main__':main()
