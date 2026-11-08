"""Authenticate retained fields and recompute measurements without evolving or relaxing them."""
import argparse,hashlib,json,sys,time
from pathlib import Path,PurePosixPath
import sys
sys.dont_write_bytecode=True
from verify_assessment import verify,stamp,need,close,sha,canonical,write_json,RUN

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.repo.resolve()/'src'))
    import numpy as np
    import scipy
    from electron_field_topology.sf_time import Grid,diagnostics,acceleration,sigma_terms
    from electron_field_topology.sf_time_run import state_sha,MODEL,SCHEME
    from electron_field_topology.sf_readmission import stationarity,static_value_gradient
    from electron_field_topology.sf_higher_q import coarse_field,rest_metrics
    from electron_field_topology.sf_motion_metrics import evaluate
    from electron_field_topology.sf_temporal import coast_reference
    from electron_field_topology.sf_reconstruction import phase_comparison
    from electron_field_topology.skyrme import K,NORTH
    clock=time.monotonic();compact=verify(a.repo);folder=Path(__file__).resolve().parent;manifest=json.loads((folder/'release-manifest.json').read_text());c=json.loads((a.run/'campaign.json').read_text());config=json.loads((a.run/'plan.json').read_text());need(c['record_id']==RUN,'Restored run differs')
    comparisons=0;worst=0.
    def compare(got,want,path=''):
        nonlocal comparisons,worst
        if isinstance(want,dict):
            for k,v in want.items():
                if k not in {'recorded_at','scope','topology_scope'}:compare(got[k],v,path+'/'+k)
        elif isinstance(want,list):
            need(len(got)==len(want),'List differs '+path)
            for i,(v,w) in enumerate(zip(got,want)):compare(v,w,path+'/'+str(i))
        elif isinstance(want,bool):need(bool(got)==want,'Boolean differs '+path)
        elif isinstance(want,(int,float)):
            close(float(got),float(want));comparisons+=1;worst=max(worst,abs(float(got)-float(want)))
        else:need(got==want,'Metadata differs '+path)
    def log(message,**extra):print(json.dumps({'recorded_at':stamp(),'message':message,**extra}),flush=True)
    def local(old):
        pp=PurePosixPath(old)
        if pp.is_absolute():
            need(pp.parts.count(RUN)==1 and '..' not in pp.parts,'Unknown archived absolute path');pp=PurePosixPath(*pp.parts[pp.parts.index(RUN)+1:])
        need('..' not in pp.parts,'Unsafe local path');return a.run/Path(pp)
    def load(path):
        with np.load(path,allow_pickle=False) as z:
            n=z['field'].copy();v=z['field_rate'].copy() if 'field_rate' in z else np.zeros_like(n)
        return n,v
    def independent(n,v,g):
        # Explicit fixed-box D4, positive sigma action and two-form contractions.
        # Does not call sf_time.densities, gradients or currents.
        u=n-NORTH;ds=[];sigma=np.zeros(g.shape)
        for axis,h in enumerate(g.spacing):
            pads=[(0,0)]*4;pads[axis]=(2,2);ext=np.pad(u,pads);indices=np.arange(g.shape[axis])+2
            at=lambda offset:np.take(ext,indices+offset,axis=axis)
            d=(at(-2)-8*at(-1)+8*at(1)-at(2))/(12*h);ds.append(d)
            sigma+=.5*np.sum(((at(1)-u)/h)**2+((u-at(-1))/h)**2,axis=-1)+(h*h/12)*np.sum(((at(1)-2*u+at(-1))/(h*h))**2,axis=-1)
        e2=sum(np.sum(d*d,axis=-1) for d in ds);e4=sum(np.sum(np.cross(ds[i],ds[j])**2,axis=-1) for i,j in [(0,1),(0,2),(1,2)])
        kinetic=np.sum(v*v,axis=-1)+sum(np.sum(np.cross(v,d)**2,axis=-1) for d in ds)
        e=K*(kinetic+e2+e4);ham=K*(kinetic+sigma+e4);mom=2*((1+e2)[...,None]*v-sum(d*np.sum(v*d,axis=-1)[...,None] for d in ds))
        dv=float(np.prod(g.spacing));energy=float(np.sum(e)*dv);points=g.points();shell=np.any(abs(points)>=np.asarray(g.lengths)/2-2.,axis=-1)
        return {'continuum_energy':energy,'energy':float(np.sum(ham)*dv),'momentum':[-K*float(np.sum(mom*d)*dv) for d in ds],'centroid':(np.sum(points*e[...,None],axis=(0,1,2))*dv/energy).tolist(),'tail_fraction':float(np.sum(e[shell])*dv/energy)}
    log('Checking every restored payload',files=len(manifest['files']))
    for f in manifest['files']:
        pp=PurePosixPath(f['archive_path']);need(pp.parts[0]=='files' and '..' not in pp.parts,'Unsafe manifest');path=a.run/Path(*pp.parts[1:]);need(path.stat().st_size==f['size'] and sha(path)==f['sha256'],'Payload changed '+str(path))
    npzs=[];state_map={}
    for f in manifest['files']:
        if not f['archive_path'].endswith('.npz'):continue
        pp=Path(f['archive_path']).relative_to('files');path=a.run/pp;n,v=load(path)
        with np.load(path,allow_pickle=False) as z:
            if pp.parts[0]=='sources':
                spec=config['sources'][pp.stem];need(sha(path)==spec['sha256'],'Original input differs');need(str(z['model_id'])==('SF-J2015-static' if pp.stem!='q2' else MODEL) and int(z['expected_q'])==spec['q'],'Original source metadata differs');g=Grid(n.shape[:3],(spec['length'],)*3,'fixed');close(float(z['h']),spec['length']/(spec['nodes']-1))
            elif pp.parts[0]=='rest':
                r=c['rest'][pp.parts[1]];g=Grid((r['nodes'],)*3,(r['length'],)*3,'fixed');mf=json.loads((path.parent/'manifest.json').read_text());need(str(z['config_sha256'])==canonical(r['config']) and str(z['code_sha256'])==mf['code_sha256'],'Rest source/config pin differs');need(int(z['expected_q'])==r['q'] and float(z['h'])==g.spacing[0],'Rest geometry differs')
                need(np.max(abs(v))==0,'Rest checkpoint has a nonzero field rate')
            else:
                r=c['cases'][pp.parts[1]];phy=r['physical'];g=Grid(tuple(phy['grid']),tuple(phy['lengths']),'fixed');mf=json.loads((a.run/'cases'/r['id']/'attempt-000/manifest.json').read_text());need(str(z['physics_sha256'])==canonical(phy) and str(z['code_sha256'])==mf['code_sha256'],'Moving source/config pin differs');close(float(z['time']),int(z['step'])*phy['dt'])
            if pp.parts[0]!='sources':need(str(z['model_id'])==MODEL and str(z['scheme'])==SCHEME,'Model/scheme differs')
            need(n.dtype==v.dtype==np.float64 and n.shape==v.shape==g.shape+(3,) and np.isfinite(n).all() and np.isfinite(v).all(),'Invalid field shape/dtype')
            unit=float(np.max(abs(np.sum(n*n,axis=-1)-1)));tangent=float(np.max(abs(np.sum(n*v,axis=-1))));need(unit<1e-10 and tangent<1e-10,'Constraint failure');need(np.max(abs(n[g.fixed_mask()]-NORTH))==0 and np.max(abs(v[g.fixed_mask()]))==0,'Fixed layers differ')
            state=state_sha(n,v);state_map[pp.as_posix()]=state;npzs.append({'path':pp.as_posix(),'shape':list(g.shape),'state_sha256':state,'unit_squared_norm_error':unit,'tangency_error':tangent,'written_utc':str(z['written_utc']),'written_melbourne':str(z['written_melbourne'])})
        del n,v
    rest=[];independent_rows=[];hotspots=[];g_by_key={}
    for key,r in c['rest'].items():
        log('Replaying initial/final stationary measurements',model=key);g=Grid((r['nodes'],)*3,(r['length'],)*3,'fixed');g_by_key[key]=g
        for role,path,want in [('initial','rest/'+key+'/initial.npz',r['initial']),('final',r['checkpoint'],r['final'])]:
            n,v=load(local(path));actual=rest_metrics(n,g,config);compare(actual,want,key+'/'+role);ind=independent(n,v,g);close(ind['energy'],actual['stationarity']['energy']);close(ind['continuum_energy'],actual['tail']['total_continuum_energy']);close(ind['tail_fraction'],actual['tail']['fraction']);independent_rows.append({'model':key,'role':role,**ind});rest.append({'model':key,'role':role,'measurements':actual})
            if role=='initial':
                source,_=load(a.run/'sources'/(key+'.npz'));expected=source if key=='q2' else coarse_field(source,config['sources'][key],config['coarse_rest']);need(np.array_equal(n,expected),'Source sampling/extension differs');del source,expected
            elif key!='q2':
                aa=acceleration(n,v,g)[1];norm=np.linalg.norm(aa,axis=-1);index=np.unravel_index(np.argmax(norm),norm.shape);pts=g.points();shell=np.any(abs(pts)>=np.asarray(g.lengths)/2-2.,axis=-1);interior=~shell;_,gradient=static_value_gradient(n,g);gradient-=n*np.sum(n*gradient,axis=-1,keepdims=True);gradient[g.fixed_mask()]=0;force=-gradient/(2*K*np.prod(g.spacing));ff=np.sum(force*force,axis=-1)
                hotspots.append({'model':key,'max_acceleration_index':list(map(int,index)),'max_acceleration_position':pts[index].tolist(),'max_acceleration':float(norm[index]),'max_in_width2_shell':float(np.max(norm[shell])),'max_in_interior':float(np.max(norm[interior])),'force_squared_fraction_width2_shell':float(np.sum(ff[shell])/np.sum(ff)),'scope':'Read-only final-field residual localization; not a perturbation or boundary-convergence test.'})
            del n,v
    r=c['cases']['q2-dt0.01'];restq,_=load(a.run/c['rest']['q2']['checkpoint']);rg=g_by_key['q2'];g=Grid(tuple(r['physical']['grid']),tuple(r['physical']['lengths']),'fixed');hist=json.loads((a.run/'cases/q2-dt0.01/history-combined.json').read_text());milestones=[]
    need(state_map['cases/q2-dt0.01/admitted.npz']==r['initial_state_sha256'],'Admitted state hash differs')
    previous='cases/q2-dt0.01/admitted.npz'
    for old in r['attempts']:
        ap=local(old);initial=(ap/'initial.npz').relative_to(a.run).as_posix();need(state_map[initial]==state_map[previous],'Segment initial/resume state differs');previous=(ap/'latest.npz').relative_to(a.run).as_posix()
        for s in json.loads((ap/'snapshots.json').read_text()):need(sha(local(s['path']))==s['sha256'] and state_map[local(s['path']).relative_to(a.run).as_posix()]==s['state_sha256'],'Snapshot pin differs')
    for label,row in r['milestones'].items():
        log('Replaying moving milestone',time=float(label));path=local(row['checkpoint']);need(sha(path)==row['checkpoint_sha256'] and state_map[path.relative_to(a.run).as_posix()]==row['state_sha256'],'Milestone checkpoint differs');n,v=load(path);hh=[x for x in hist if x['time']<=float(label)+1e-12];actual=evaluate(hh,n,v,g,restq,rg.spacing[0],.3,2,2,2.,config['limits']);compare(actual,row['assessment']['legacy_motion'],'milestone/'+label);ref,_=coast_reference(restq,rg,g,.3,2,float(label));phase=phase_comparison(n,ref);compare(phase,row['assessment']['projected_cubic_reference_raw'],'cubic/'+label);diag=diagnostics(n,v,g)
        for k in ['energy','continuum_energy','momentum','centroid','rms_radius','unit_error','tangency_error']:compare(diag[k],hh[-1][k],label+'/'+k)
        ind=independent(n,v,g)
        for k in ['energy','continuum_energy','momentum','centroid']:compare(ind[k],diag[k],label+'/independent/'+k)
        close(ind['tail_fraction'],actual['final']['boundary_shell_energy_fraction']);independent_rows.append({'model':'q2-moving','role':label,**ind});milestones.append({'time':float(label),'replayed_motion':actual,'cubic_reference':phase});del n,v,ref
    result={'recorded_at':stamp(),'run':RUN,'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'wall_seconds':time.monotonic()-clock,'payload_files_verified':len(manifest['files']),'npz_files_verified':len(npzs),'distinct_states':len(set(state_map.values())),'npz_states':npzs,'numeric_comparisons':comparisons,'maximum_absolute_comparison_difference':worst,'rest':rest,'milestones':milestones,'independent_energy_current_contractions':independent_rows,'residual_hotspots':hotspots,'source_embeddings_exact':True,'segment_continuity_exact':True,'disposition':compact['disposition'],'scope':'Read-only re-evaluation of retained fields; no new stationary iterations or physical-time trajectory. Metric replay shares named instruments; energy/current contractions are independently expanded.'}
    a.output.mkdir(parents=True,exist_ok=True);write_json(a.output/'field-verification.json',result);log('Full field replay passed',payload_files=len(manifest['files']),npz_files=len(npzs),numeric_comparisons=comparisons,hotspots=hotspots)
if __name__=='__main__':main()
