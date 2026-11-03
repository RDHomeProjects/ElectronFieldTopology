"""Physical-time solver controls: independent limits, variation and convergence."""
import copy
import json
import numpy as np
import pytest
from electron_field_topology.sf_time import Grid,derivative,acceleration,step,diagnostics,densities
from electron_field_topology.sf_time_controls import wave,manufactured,manufactured_force,pulse
from electron_field_topology.sf_time_run import run,initialize,validate
from electron_field_topology.sf_preview import export_settings


def config(shape=(12,1,1),kind='wave',steps=8,dt=.01):
    initial={'kind':kind}
    if kind=='wave':initial['modes']=[{'amplitude':.35,'wave_numbers':[1,0,0]}]
    return {'case_id':'test','grid':list(shape),'lengths':[2*np.pi]*3,'boundary':'periodic',
            'dt':dt,'steps':steps,'diagnostic_every':1,'checkpoint_every':3,'initial':initial}


@pytest.mark.parametrize('boundary',['periodic','fixed'])
def test_derivative_is_skew_adjoint(boundary):
    rng=np.random.default_rng(42);a=rng.normal(size=(13,7));b=rng.normal(size=a.shape)
    assert abs(np.sum(a*derivative(b,.2,0,boundary))+np.sum(b*derivative(a,.2,0,boundary)))<2e-12


@pytest.mark.parametrize('boundary',['periodic','fixed'])
def test_vacuum_exactly_stationary(boundary):
    g=Grid((9,9,9),(4.,)*3,boundary);u=np.zeros(g.shape+(3,));u[...,2]=1;v=np.zeros_like(u)
    n,w,c=step(u,v,g,.01)
    assert np.array_equal(n,u) and np.array_equal(w,v)
    assert diagnostics(n,w,g)['energy']==0


def test_full_nonlinear_acceleration_constraint_and_energy_variation():
    # A discrete variational identity, not comparison to a second RHS implementation.
    g=Grid((9,9,9),(2*np.pi,)*3);u,v=manufactured(g.points(),.23)
    velocity,a=acceleration(u,v,g)
    assert np.max(abs(np.sum(u*a,axis=-1)+np.sum(v*v,axis=-1)))<1e-13
    eps=2e-6
    def energy(n,w):return np.sum(densities(n,w,g)['hamiltonian_density'])*np.prod(g.spacing)
    derivative_e=(energy(u+eps*v,v+eps*a)-energy(u-eps*v,v-eps*a))/(2*eps)
    assert abs(derivative_e)<2e-10


def test_fixed_box_discrete_energy_variation():
    g=Grid((13,13,13),(8.,)*3,'fixed');xyz=g.points();envelope=np.exp(-np.sum(xyz*xyz,axis=-1))
    raw=np.stack((.1*envelope*np.sin(xyz[...,0]),.12*envelope*np.cos(xyz[...,1]),np.ones(g.shape)),axis=-1)
    u=raw/np.linalg.norm(raw,axis=-1,keepdims=True);u[g.fixed_mask()]=[0,0,1]
    v=np.stack((.1*envelope,.05*envelope,np.zeros(g.shape)),axis=-1);v-=u*np.sum(u*v,axis=-1,keepdims=True);v[g.fixed_mask()]=0
    a=acceleration(u,v,g)[1];eps=2e-6
    def energy(n,w):return np.sum(densities(n,w,g)['hamiltonian_density'])*np.prod(g.spacing)
    assert abs((energy(u+eps*v,v+eps*a)-energy(u-eps*v,v-eps*a))/(2*eps))<2e-10


def test_manufactured_nonlinear_spatial_order():
    errors=[]
    for n in [8,16,32]:
        g=Grid((n,n,n),(2*np.pi,)*3);u,v,exact=manufactured(g.points(),.17,True)
        actual=acceleration(u,v,g,manufactured_force,.17)[1]
        errors.append(np.sqrt(np.mean((actual-exact)**2)))
    assert min(np.log2(np.array(errors[:-1])/errors[1:]))>3.5,errors


def test_temporal_order_from_exact_geodesic():
    errors=[]
    g=Grid((1,1,1),(1.,)*3)
    for dt in [.1,.05,.025]:
        u=np.array([[[[0.,0.,1.]]]]);v=np.array([[[[1.,0.,0.]]]])
        for k in range(round(1/dt)):u,v,_=step(u,v,g,dt,k*dt)
        errors.append(np.linalg.norm(u.ravel()-[np.sin(1),0,np.cos(1)]))
    assert min(np.log2(np.array(errors[:-1])/errors[1:]))>3.9


def test_actual_travelling_wave_convergence_and_conservation():
    errors=[]
    modes=[{'amplitude':.35,'wave_numbers':[1,0,0]}]
    for n in [16,32,64]:
        g=Grid((n,1,1),(2*np.pi,1.,1.));u,v=wave(g.points(),0,g.lengths,modes)
        original=diagnostics(u,v,g);dt=1/(2*n)
        for k in range(2*n):u,v,_=step(u,v,g,dt,k*dt)
        final=diagnostics(u,v,g)
        errors.append(np.sqrt(np.mean((u-wave(g.points(),1,g.lengths,modes)[0])**2)))
        assert abs(final['energy']/original['energy']-1)<1e-7
        assert np.linalg.norm(np.array(final['momentum'])-original['momentum'])/original['energy']<1e-6
    assert min(np.log2(np.array(errors[:-1])/errors[1:]))>3.8


@pytest.mark.parametrize('axis',[0,1,2])
def test_coordinate_axis_permutations(axis):
    shape=[1,1,1];shape[axis]=16;g=Grid(tuple(shape),(2*np.pi,)*3)
    k=[0,0,0];k[axis]=1;m=[{'amplitude':.2,'wave_numbers':k}]
    u,v=wave(g.points(),0,g.lengths,m)
    for j in range(10):u,v,_=step(u,v,g,.01,j*.01)
    exact=wave(g.points(),.1,g.lengths,m)[0]
    assert np.sqrt(np.mean((u-exact)**2))<2e-5


def test_manufactured_time_evolution_exercises_all_spatial_directions():
    errors=[]
    for n in [8,12,16]:
        g=Grid((n,n,n),(2*np.pi,)*3);u,v=manufactured(g.points(),0)
        for j in range(10):u,v,_=step(u,v,g,.01,j*.01,manufactured_force)
        errors.append(np.sqrt(np.mean((u-manufactured(g.points(),.1)[0])**2)))
    orders=[np.log(errors[i]/errors[i+1])/np.log([8,12,16][i+1]/[8,12,16][i]) for i in range(2)]
    assert min(orders)>3.4,(errors,orders)


def test_compact_pulse_before_fixed_boundary_interaction():
    g=Grid((97,1,1),(16.,1.,1.),'fixed');u,v=pulse(g.points(),0)
    initial=diagnostics(u,v,g)
    for k in range(20):u,v,_=step(u,v,g,.01,k*.01)
    assert np.sqrt(np.mean((u-pulse(g.points(),.2)[0])**2))<2e-4
    assert np.array_equal(u[g.fixed_mask()],np.broadcast_to([0.,0.,1.],u[g.fixed_mask()].shape))
    assert abs(diagnostics(u,v,g)['energy']/initial['energy']-1)<1e-7


def test_fixed_boundary_reflects_pulse_and_changes_momentum():
    # A fixed wall supplies impulse. It is deliberately not treated as open space.
    g=Grid((129,1,1),(8.,1.,1.),'fixed');u,v=pulse(g.points(),0,centre=1.7,radius=.8)
    original=diagnostics(u,v,g)
    for k in range(800):u,v,_=step(u,v,g,.005,k*.005)
    final=diagnostics(u,v,g)
    assert abs(final['energy']/original['energy']-1)<1e-6
    assert original['momentum'][0]>.95*original['energy']
    assert final['momentum'][0]<-.95*original['energy']


def test_sigma_has_no_spurious_zero_for_checkerboard_mode():
    g=Grid((16,1,1),(2*np.pi,1.,1.));u=np.zeros(g.shape+(3,))
    u[:,0,0,0]=.1*(-1.)**np.arange(16);u[...,2]=np.sqrt(.99);v=np.zeros_like(u)
    assert diagnostics(u,v,g)['energy']>0
    assert np.sum(u[...,0]*acceleration(u,v,g)[1][...,0])<0


def test_boosted_initial_velocity_matches_independent_event_difference():
    from electron_field_topology.sf_time_initial import sample_static,boosted_static
    g=Grid((17,17,17),(8.,)*3,'fixed');xyz=g.points();angle=.3*np.exp(-np.sum(xyz*xyz,axis=-1))
    field=np.stack((np.sin(angle),np.zeros_like(angle),np.cos(angle)),axis=-1)
    field[g.fixed_mask()]=[0,0,1];beta=.3;gamma=1/np.sqrt(1-beta*beta)
    u,v=boosted_static(field,.5,g,beta,0)
    rest=g.points();rest[...,0]*=gamma;eps=1e-6
    a=rest.copy();b=rest.copy();a[...,0]-=gamma*beta*eps;b[...,0]+=gamma*beta*eps
    fd=(sample_static(field,.5,a,0)[0]-sample_static(field,.5,b,0)[0])/(2*eps)
    indices=rest[...,0]/.5+8;mask=abs(indices-np.round(indices))>1e-5
    np.testing.assert_allclose(v[mask],fd[mask],atol=2e-10)
    assert np.max(abs(np.sum(u*v,axis=-1)))<1e-14


@pytest.mark.parametrize('q',[1,2])
def test_unrelaxed_low_q_seed_short_evolution(q):
    g=Grid((17,17,17),(8.,)*3,'fixed');c=config(g.shape,'rational',2,.001)
    c['lengths']=list(g.lengths);c['boundary']='fixed';c['initial'].update(q=q,scale=1.,cutoff=2.8)
    u,v,meta=initialize(c,g);original=diagnostics(u,v,g)
    assert 'unrelaxed' in meta['scope']
    for k in range(2):u,v,_=step(u,v,g,.001,k*.001)
    final=diagnostics(u,v,g)
    assert final['unit_error']<1e-14 and final['tangency_error']<1e-14
    assert abs(final['energy']/original['energy']-1)<1e-7


def test_profile_cannot_change_numerics_and_invalid_presentation_is_ignored(tmp_path):
    c=config((9,9,9),steps=4)
    no=run(c,tmp_path/'off')
    profile={'export':{'grid':[5,5,5],'every_steps':2,'vtk':True},
             'presentation':{'colors':'invalid-for-renderer-only'}}
    yes=run(c,tmp_path/'on',profile)
    assert no['state_sha256']==yes['state_sha256']
    assert no['final']==yes['final']
    assert yes['preview_frames']==3 and no['preview_frames']==0
    # Selecting other cases or grids must not suppress the physical calculation.
    profile['export'].update(case_ids=['other'],grid=[99,99,99])
    filtered=run(c,tmp_path/'filtered',profile)
    assert filtered['state_sha256']==no['state_sha256'] and filtered['preview_frames']==0
    with pytest.raises(ValueError,match='Unknown visualization'):export_settings({'export':{'dt':.1}})


def test_checkpoint_resume_is_bit_exact_and_has_no_gui_dependency(tmp_path):
    c=config(steps=8)
    whole=run(c,tmp_path/'whole')
    part=run(c,tmp_path/'part',stop_after=3)
    assert part['status']=='checkpointed'
    resumed=run(c,tmp_path/'resumed',profile={'export':{'grid':[6,1,1],'every_steps':2,'vtk':False}},resume=tmp_path/'part/final.npz')
    assert resumed['state_sha256']==whole['state_sha256']
    changed=copy.deepcopy(c);changed['dt']*=.5
    with pytest.raises(ValueError,match='Resume model'):run(changed,tmp_path/'bad',resume=tmp_path/'part/final.npz')
    with pytest.raises(ValueError,match='new or empty'):run(c,tmp_path/'whole')


def test_validation_rejects_unsupported_physics_and_unresolved_time_step():
    c=config();c['colors']=8
    with pytest.raises(ValueError,match='Unknown physical'):validate(c)
    del c['colors'];c['dt']=1
    with pytest.raises(ValueError,match='dt/h'):validate(c)


def test_solver_and_renderer_imports_are_independent():
    import subprocess,sys
    subprocess.run([sys.executable,'-c',"import sys;import electron_field_topology.sf_time_run;assert 'matplotlib' not in sys.modules"],check=True)
    subprocess.run([sys.executable,'-c',"import sys;import electron_field_topology.sf_renderer;assert 'electron_field_topology.sf_time' not in sys.modules"],check=True)
