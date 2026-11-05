"""Read-only full NPZ replay plus independent D4/energy/tail/core calculations.

No optimization or physical-time evolution. Apache-2.0.
"""
import argparse,hashlib,json,sys,time
sys.dont_write_bytecode=True
from pathlib import Path
from verify_assessment import verify,retention,stamp,need,close,SOURCE,RUN

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--retention-folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.repo.resolve()/'src'))
    import numpy as np
    from electron_field_topology import sf_tail_domain as t
    from electron_field_topology.sf_readmission import admitted
    from electron_field_topology.skyrme import K,NORTH
    clock=time.monotonic();v=verify(a.evidence,a.repo);ret=retention(a.retention_folder,a.repo,a.run)
    c=json.loads((a.run/'campaign.json').read_text());cfg=json.loads((a.run/'plan.json').read_text());finals={};starts={};rows=[];diffs=[];numeric=0;maximum={}
    def compare(actual,expected,path=''):
        nonlocal numeric
        if isinstance(expected,dict):
            for k,value in expected.items():
                if k not in {'recorded_at','original_stationarity_pass'}:compare(actual[k],value,path+'/'+k)
        elif isinstance(expected,list):
            need(len(actual)==len(expected),'Array length differs: '+path)
            for i,(x,y) in enumerate(zip(actual,expected)):compare(x,y,path+'/'+str(i))
        elif isinstance(expected,bool):need(bool(actual)==expected,'Boolean differs: '+path)
        elif isinstance(expected,(float,int)):
            need(np.isfinite(actual),'Non-finite replay: '+path);need(np.isclose(actual,expected,rtol=1e-8,atol=1e-10),'Replay scalar differs: '+path+f' {actual} != {expected}')
            numeric+=1;maximum[path.split('/')[-1]]=max(maximum.get(path.split('/')[-1],0),float(abs(actual-expected)))
        else:need(actual==expected,'Replay metadata differs: '+path)
    def independent_density(n,h):
        u=n-np.array([0.,0.,1.]);der=[];sig=np.zeros(n.shape[:-1])
        for axis in range(3):
            pads=[(0,0)]*4;pads[axis]=(2,2);extended=np.pad(u,pads,mode='constant')
            idx=np.arange(n.shape[axis])+2
            d=sum(weight*np.take(extended,idx+offset,axis=axis) for offset,weight in [(-2,1.),(-1,-8.),(1,8.),(2,-1.)])/(12*h)
            der.append(d)
            plus=np.take(extended,idx+1,axis=axis);minus=np.take(extended,idx-1,axis=axis)
            sig+=.5*np.sum(((plus-u)/h)**2+((u-minus)/h)**2,axis=-1)+(h*h/12)*np.sum(((plus-2*u+minus)/(h*h))**2,axis=-1)
        e2=sum(np.sum(d*d,axis=-1) for d in der)
        e4=sum(np.sum(np.cross(der[i],der[j])**2,axis=-1) for i,j in [(0,1),(0,2),(1,2)])
        return K*(e2+e4),float(K*np.sum(sig+e4)*h**3)
    for key,row in c['cases'].items():
        print(json.dumps({'recorded_at':stamp(),'message':'Replay full fields','case_id':key}),flush=True)
        nnode=row['nodes'];length=row['length'];g=t.Grid((nnode,)*3,(length,)*3,'fixed')
        for which in ['initial','final']:
            path=a.run/'readmission'/key/('initial.npz' if which=='initial' else 'latest.npz')
            with np.load(path,allow_pickle=False) as data:
                n=data['field'].copy();rate=data['field_rate'].copy()
                need(n.dtype==np.float64 and n.shape==g.shape+(3,) and np.max(abs(rate))==0,'NPZ geometry/rate mismatch')
                need(str(data['model_id'])==t.MODEL and str(data['scheme'])==t.SCHEME and int(data['expected_q'])==row['q'],'NPZ model/scheme/Q mismatch')
                need(float(data['h'])==.16 and str(data['config_sha256'])==t.canonical_sha(row['relax_config']),'NPZ configuration mismatch')
                manifest=json.loads((path.parent/'manifest.json').read_text())
                need(str(data['code_sha256'])==manifest['code_sha256'] and int(data['iteration'])==(0 if which=='initial' else row['result']['iterations']),'NPZ code/iteration mismatch')
            expected=row[which];need(t.state_sha(n,rate)==expected['state_sha256'],'Full state digest differs')
            got=t.measure(n,g,row['q'],cfg);compare(got,expected)
            ed,ham=independent_density(n,.16);dv=.16**3
            axes=[-.5*length+np.arange(nnode)*.16]*3
            shell=np.zeros(g.shape,dtype=bool)
            for i,axis in enumerate(axes):
                shape=[1]*3;shape[i]=nnode;shell|=(abs(axis)>=length/2-2.).reshape(shape)
            energy=float(np.sum(ed)*dv);se=float(np.sum(ed[shell])*dv);fraction=se/energy
            close(energy,expected['continuum_energy']);close(se,expected['shell_energy']);close(fraction,expected['shell_fraction']);close(ham,expected['discrete_hamiltonian'])
            need((fraction<=.001)==expected['tail_gate_pass'],'Independent tail gate differs')
            rows.append({'case_id':key,'state':which,'independent_continuum_energy':energy,'independent_hamiltonian':ham,'independent_shell_energy':se,'independent_shell_fraction':fraction,
                'energy_abs_difference':abs(energy-expected['continuum_energy']),'hamiltonian_abs_difference':abs(ham-expected['discrete_hamiltonian']),'shell_fraction_abs_difference':abs(fraction-expected['shell_fraction'])})
            if which=='initial':
                if nnode==101:starts[row['q']]=n.copy()
                old=starts[row['q']];pad=(nnode-101)//2
                need(np.array_equal(n[pad:pad+101,pad:pad+101,pad:pad+101],old),'Initial embedded core differs')
                extended=np.broadcast_to(NORTH,n.shape).copy();extended[pad:pad+101,pad:pad+101,pad:pad+101]=old
                need(np.array_equal(n,extended),'North padding differs')
            else:finals[key]=(n,g,ed)
            del rate
        need(admitted(row['final']['stationarity'],row['q'],c['source_original_readmission'])==row['final']['original_stationarity_pass'],'Original admission flag differs')
    for pair in json.loads((a.run/'comparisons.json').read_text())['pairs']:
        aa,ga,ea=finals[pair['a']];bb,gb,eb=finals[pair['b']]
        for label,count in [('common_core',73),('original_footprint',101)]:
            ma=(len(aa)-count)//2;mb=(len(bb)-count)//2;sa=(slice(ma,ma+count),)*3;sb=(slice(mb,mb+count),)*3
            delta=bb[sb]-aa[sa];norm=np.sqrt(np.sum((aa[sa]-NORTH)**2));sume=float(np.sum(ea[sa]))
            own={'field_relative_l2':float(np.sqrt(np.sum(delta*delta))/norm),'field_absolute_rms':float(np.sqrt(np.mean(delta*delta))),
                'energy_relative_difference':abs(float(np.sum(eb[sb]))-sume)/abs(sume),'density_relative_l1':float(np.sum(abs(eb[sb]-ea[sa]))/abs(sume))}
            for name,value in own.items():close(value,pair[label][name])
            diffs.append({'a':pair['a'],'b':pair['b'],'region':label,**own})
    result={'replayed_at':stamp(),'run_id':RUN,'source_commit':SOURCE,'fields_replayed':12,'initial_embeddings_bit_exact':6,
        'independent_tail_energy_computations':12,'full_field_pair_regions_recomputed':12,'recorded_numeric_scalars_compared':numeric,
        'maximum_absolute_error_by_scalar':maximum,'rows':rows,'pairs':diffs,'retention':ret,'wall_seconds':time.monotonic()-clock,
        'environment':{'python':sys.version,'numpy':np.__version__,'scipy':__import__('scipy').__version__},
        'scope':'All 12 initial/final NPZ states reexecuted through recorded diagnostics; separate NumPy D4/energy/shell and common-region implementations agree. No optimization path rerun or independent physical-model validation.'}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['replayed_at','fields_replayed','independent_tail_energy_computations','full_field_pair_regions_recomputed','recorded_numeric_scalars_compared','wall_seconds']},indent=2))
if __name__=='__main__':main()
