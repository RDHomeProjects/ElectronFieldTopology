"""Independent controls for sampling, kinetic metrics and immutable replay."""
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology import sf_motion_diagnostics as audit
from electron_field_topology import sf_motion_diagnostics_local as local
from electron_field_topology.sf_lowq_motion import campaign
from electron_field_topology.sf_time import Grid, densities, gradients
from electron_field_topology.skyrme import NORTH


def cfg(digest='a'*64):
    return {'format':'EFT-motion-diagnostics-v1','evidence_sha256':digest,'case_ids':[],
            'comparison_grids':[5,7,9],'shell_width':.5,'replay_rtol':1e-9,'replay_atol':1e-11}


def test_common_time_fit_removes_sampling_bias_for_cubic_centroid():
    def rows(count):return [{'time':float(t),'centroid':[float(t**3),0.,0.]} for t in np.linspace(0,1,count)]
    result=audit.common_time_fit(rows(11),rows(21))
    assert result['original_fit_velocity_difference']>1e-4
    assert result['common_time_velocity_difference']==0
    assert result['max_common_centroid_difference']==0
    assert len(result['common_times'])==11


def test_linear_sampling_is_exact_for_affine_vector_on_anisotropic_grid():
    grid=Grid((9,11,13),(4.,5.,6.),'fixed');x=grid.points()
    field=np.stack((2*x[...,0]+x[...,1],3*x[...,2]-2*x[...,0],np.ones(grid.shape)),axis=-1)
    points=np.array([[.11,-.47,.39],[-.41,.27,-.12],[0.,0.,0.]])
    expected=np.stack((2*points[:,0]+points[:,1],3*points[:,2]-2*points[:,0],np.ones(3)),axis=-1)
    assert np.max(abs(audit.sample_uniform(field,grid,points)-expected))<1e-14
    with pytest.raises(ValueError):audit.sample_uniform(field,grid,np.array([[3.,0.,0.]]))


def test_transport_diagnostics_vacuum_zero_without_mutating_arrays():
    grid=Grid((9,)*3,(4.,)*3,'fixed');n=np.broadcast_to(NORTH,grid.shape+(3,)).copy();v=np.zeros_like(n)
    before=n.copy();result=audit.transport_diagnostics(n,v,grid,.3,0)
    assert result['rate_relative_l2']==0 and result['actual_acceleration_rms']==0
    assert result['tangent_acceleration_difference_rms']==0
    assert np.array_equal(n,before) and not np.any(v)


def test_transport_on_independent_exact_one_dimensional_wave_refines():
    # For n=(sin(theta(x-t)),0,cos(theta(x-t))) the continuum SF quartic
    # term vanishes and any smooth profile is a speed-one great-circle wave.
    # Its exact rate is supplied analytically, independent of the D4 instrument.
    errors=[];accelerations=[]
    for count in (65,129,257):
        grid=Grid((count,1,1),(4.,1.,1.),'fixed');x=grid.points()[...,0]
        r=1-(x/.8)**2;theta=.1*np.maximum(r,0)**6
        tx=np.where(r>0,-1.2*x/.8**2*np.maximum(r,0)**5,0.)
        n=np.stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1)
        v=-tx[...,None]*np.stack((np.cos(theta),np.zeros_like(theta),-np.sin(theta)),axis=-1)
        result=audit.transport_diagnostics(n,v,grid,1.,0)
        errors.append(result['rate_relative_l2']);accelerations.append(result['tangent_acceleration_difference_rms'])
    assert min(errors[i]/errors[i+1] for i in (0,1))>10
    assert min(accelerations[i]/accelerations[i+1] for i in (0,1))>9


def test_classical_metric_matches_direct_kinetic_energy_and_is_positive():
    grid=Grid((13,)*3,(6.,)*3,'fixed');x=grid.points()
    theta=.3*np.exp(-np.sum(x*x,axis=-1));phi=.2*x[...,2]
    n=np.stack((np.sin(theta)*np.cos(phi),np.sin(theta)*np.sin(phi),np.cos(theta)),axis=-1)
    n[grid.fixed_mask()]=NORTH
    result=audit.classical_metric(n,grid);G=np.array(result['metric'])
    assert np.max(abs(G-G.T))<1e-14 and min(result['eigenvalues'])>-1e-13
    translation=np.array([.13,-.07,.03]);omega=np.array([.11,.05,-.09]);phase=.08
    d=gradients(n-NORTH,grid)
    velocity=-np.einsum('i,...ia->...a',translation,d)-np.einsum('...i,...ia->...a',np.cross(omega,x),d)+phase*np.cross([0.,0.,1.],n)
    velocity-=n*np.sum(n*velocity,axis=-1,keepdims=True);velocity[grid.fixed_mask()]=0
    speed=np.r_[translation,omega,phase]
    h0=densities(n,np.zeros_like(n),grid)['hamiltonian_density']
    h1=densities(n,velocity,grid)['hamiltonian_density']
    direct=float(np.sum(h1-h0)*np.prod(grid.spacing))
    assert abs(direct-.5*speed@G@speed)<1e-14
    vacuum=np.broadcast_to(NORTH,n.shape).copy()
    assert np.max(np.abs(audit.classical_metric(vacuum,grid)['metric']))==0


@pytest.fixture
def source(tmp_path):
    config=json.loads((audit.ROOT/'experiments/configs/sf-motion/smoke.json').read_text())
    config['seeds']=[{'q':1,'nodes':9,'length':4.,'seed_scale':1.6,'seed_cutoff':1.6}]
    config.update(duration=.2,time_steps=[.02,.01],boundary_shell_width=.5)
    path=tmp_path/'source';campaign(config,path,{'export':{'enabled':False}})
    return path,cfg(audit.sha(path/'evidence.zip'))


def fingerprints(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def test_full_audit_replays_fields_preserves_failed_gates_and_source(source,tmp_path):
    path,config=source;before=fingerprints(path);inv=audit.inventory(path,config)
    assert inv['ready'] and len(inv['files'])==5
    out=tmp_path/'audit';result=audit.audit(path,out,config)
    assert result['status']=='complete_pending_review'
    assert len(result['cases'])==2 and len(result['seeds'])==1 and len(result['pairs'])==1
    assert all(r['all_replays_match'] for r in result['cases'].values())
    assert all(not r['original_case_checks']['topology'] for r in result['cases'].values())
    assert b'\r' not in (out/'case-metrics.csv').read_bytes()
    assert fingerprints(path)==before
    import zipfile
    with zipfile.ZipFile(out/'evidence.zip') as z:
        hashes=json.loads(z.read('evidence-hashes.json'))['sha256']
        assert set(z.namelist())==set(hashes)|{'evidence-hashes.json'}
        for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    again=audit.audit(path,out,config)
    assert again['cases']==result['cases'] and again['pairs']==result['pairs']
    assert fingerprints(path)==before
    changed=copy.deepcopy(config);changed['comparison_grids']=[5,9,11]
    prior_inventory=(out/'inventory.json').read_bytes()
    with pytest.raises(ValueError,match='changed'):audit.audit(path,out,changed)
    assert (out/'inventory.json').read_bytes()==prior_inventory


def test_inventory_missing_field_retains_actionable_path(source):
    path,config=source;inv=audit.inventory(path,config)
    target=next(r for r in inv['files'] if r['relative_path'].endswith('/final.npz'))
    Path(target['path']).unlink();changed=audit.inventory(path,config)
    assert not changed['ready']
    assert changed['missing_or_changed'][0]['path']==target['path']


def test_initial_tamper_detected_without_published_initial_file_hash(source):
    path,config=source;c,plan,pairs,selected,manifests=audit.compact(path,config)
    case=c['cases'][selected[0]];p=audit.attempt_path(path,case)/'initial.npz'
    with np.load(p,allow_pickle=False) as d:values={k:d[k].copy() for k in d.files}
    values['field'][4,4,4]=[.1,0.,np.sqrt(.99)];np.savez_compressed(p,**values)
    with pytest.raises(ValueError,match='Initial state differs'):
        audit.case_audit(path,case,c,plan,manifests,config)


def test_stop_request_saves_status_then_resume_continues(source,tmp_path):
    path,config=source;out=tmp_path/'audit';out.mkdir();(out/'stop-request.json').write_text('{}')
    result=audit.audit(path,out,config)
    assert result['status']=='stopped_checkpoint_retained' and not result['cases']
    (out/'stop-request.json').unlink()
    assert audit.audit(path,out,config)['status']=='complete_pending_review'


def test_config_and_output_guards(source):
    path,config=source
    with pytest.raises(ValueError,match='outside'):audit.audit(path,path/'audit',config)
    bad=copy.deepcopy(config);bad['comparison_grids']=[6]
    with pytest.raises(ValueError):audit.validate_config(bad)
    bad=copy.deepcopy(config);bad['evidence_sha256']='0'*64
    with pytest.raises(ValueError,match='archive differs'):audit.inventory(path,bad)


def test_launcher_identity_and_stop_do_not_signal_other_processes(tmp_path,monkeypatch):
    out=tmp_path/'out';out.mkdir();pointer=tmp_path/'pointer';pointer.write_text(str(out))
    (out/'launch.json').write_text(json.dumps({'pid':123,'process_identity':'old'}))
    monkeypatch.setattr(local,'POINTER',pointer);monkeypatch.setattr(local,'process_identity',lambda pid:'new')
    monkeypatch.setattr('sys.argv',['sf-motion-diagnostics','stop'])
    local.main();assert not (out/'stop-request.json').exists()
    monkeypatch.setattr(local,'process_identity',lambda pid:'old')
    local.main();assert (out/'stop-request.json').exists()
