"""Independent variations, topology guards and stationary readmission."""
import copy
import json
import numpy as np
import pytest
from electron_field_topology.sf_time import Grid,retract,acceleration,densities
from electron_field_topology.sf_readmission import static_value_gradient,cone,stationarity,relax,checkpoint
from electron_field_topology.sf_time_run import initialize
from electron_field_topology.sf_dynamics_admission import sha
from electron_field_topology.skyrme import NORTH,K


def test_static_gradient_against_independent_finite_variation_and_dynamic_equilibrium():
    rng=np.random.default_rng(16);g=Grid((11,)*3,(6.,)*3,'fixed')
    n=np.broadcast_to(NORTH,g.shape+(3,)).copy();n[3:-3,3:-3,3:-3,:2]=rng.normal(size=(5,5,5,2))*.04
    n,v=retract(n,np.zeros_like(n),g);direction=rng.normal(size=n.shape);direction-=n*np.sum(direction*n,axis=-1,keepdims=True);direction[g.fixed_mask()]=0
    e,grad=static_value_gradient(n,g);eps=1e-6
    # Densities and full physical-time acceleration are separate code paths.
    def value(raw):
        u,_=retract(raw,np.zeros_like(raw),g)
        return np.sum(densities(u,np.zeros_like(u),g)['hamiltonian_density'])*np.prod(g.spacing)
    assert abs((value(n+eps*direction)-value(n-eps*direction))/(2*eps)-np.sum(grad*direction))<1e-9
    assert abs(value(n)-e)<1e-13
    f=-grad/(2*K*np.prod(g.spacing));f-=n*np.sum(n*f,axis=-1,keepdims=True)
    d=__import__('electron_field_topology.sf_time',fromlist=['gradients']).gradients(n-NORTH,g)
    m=(1+np.sum(d*d,axis=(-2,-1)))[...,None,None]*np.eye(3)-np.einsum('...ia,...ib->...ab',d,d)
    a=acceleration(n,v,g)[1];ma=np.einsum('...ab,...b->...a',m,a);ma-=n*np.sum(n*ma,axis=-1,keepdims=True)
    assert np.max(abs((ma-f)[~g.fixed_mask()]))<1e-12


def test_cell_cone_detects_unresolved_opposing_corners():
    n=np.broadcast_to(NORTH,(3,3,3,3)).copy();assert cone(n)==1
    n[0,0,0]=-NORTH;assert cone(n)<0


def settings(nodes=33,length=8.):
    return {'q':1,'nodes':nodes,'length':length,'seed_scale':1.1,'seed_cutoff':length*.4,
            'relative_force_l2':1e-3,'acceleration_max':1e-2,'charge_relative_error':.05,
            'iterations_per_pass':10,'checkpoint_every':5,'stagnation_relative_energy':1e-10}


def test_unresolved_topology_is_retained_and_not_called_stationary(tmp_path):
    c=settings(9);r=relax(c,tmp_path)
    assert r['status']=='topology_unresolved'
    assert (tmp_path/'initial.npz').is_file() and (tmp_path/'latest.npz').is_file()
    assert r['final']['relative_force_l2']>c['relative_force_l2']


def test_readmission_decreases_own_action_and_resumes_without_old_static_files(tmp_path):
    c=settings();r=relax(c,tmp_path,pass_limit=1)
    assert r['status']=='checkpointed';assert r['final']['energy']<r['initial']['energy']
    r2=relax(c,tmp_path,pass_limit=1)
    assert r2['iterations']>r['iterations'] and r2['final']['energy']<r['final']['energy']
    changed=copy.deepcopy(c);changed['relative_force_l2']*=2
    with pytest.raises(ValueError,match='changed'):relax(changed,tmp_path,pass_limit=1)


def test_lattice_import_checks_scheme_zero_velocity_and_sha(tmp_path):
    g=Grid((9,)*3,(4.,)*3,'fixed');n=np.broadcast_to(NORTH,g.shape+(3,)).copy();p=tmp_path/'n.npz'
    checkpoint(p,n,g,1,'cfg',0,0,'code')
    config={'initial':{'kind':'lattice_checkpoint','path':str(p),'sha256':sha(p),'expected_q':1}}
    u,v,_=initialize(config,g);assert np.array_equal(u,n) and np.max(abs(v))==0
    config['initial']['sha256']='0'*64
    with pytest.raises(ValueError,match='SHA'):initialize(config,g)
