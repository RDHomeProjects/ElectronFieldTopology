"""Independent covariance controls; Apache-2.0."""
import numpy as np
import pytest
from electron_field_topology.fields import hopfion
from electron_field_topology.relativity import (lorentz_matrix,transform_events,transform_fields,
    field_tensor,fields_from_tensor,boosted_hopfion)


@pytest.mark.parametrize('v',[(0,0,0),(.6,0,0),(0,0,.6),(.2,-.3,.4)])
def test_metric_inverse_and_nonnull_tensor_reference(v):
    v=np.array(v);l=lorentz_matrix(v);eta=np.diag([-1,1,1,1])
    np.testing.assert_allclose(l.T@eta@l,eta,atol=2e-15)
    np.testing.assert_allclose(lorentz_matrix(-v)@l,np.eye(4),atol=2e-15)
    rng=np.random.default_rng(73);e,b=rng.normal(size=(2,30,3))
    tensor=field_tensor(e,b)
    ft=np.einsum('ij,...jk,lk->...il',l,tensor,l)
    ref=fields_from_tensor(ft);actual=transform_fields(e,b,v)
    for a,r in zip(actual,ref):np.testing.assert_allclose(a,r,atol=3e-15)
    en,bn=actual
    np.testing.assert_allclose(np.sum(e*b,axis=-1),np.sum(en*bn,axis=-1),atol=6e-15)
    np.testing.assert_allclose(np.sum(e*e-b*b,axis=-1),np.sum(en*en-bn*bn,axis=-1),atol=1e-14)


def test_single_axis_sign_from_feynman_table():
    v=np.array([.6,0,0]);e=np.array([1.,2.,3.]);b=np.array([4.,5.,6.]);g=1.25
    en,bn=transform_fields(e,b,v)
    np.testing.assert_allclose(en,[1,g*(2-.6*6),g*(3+.6*5)],atol=1e-15)
    np.testing.assert_allclose(bn,[4,g*(5+.6*3),g*(6-.6*2)],atol=1e-15)


def test_time_array_and_common_events():
    rng=np.random.default_rng(19);events=rng.uniform(-1,1,(20,4));v=np.array([.2,-.3,.4])
    e,b=hopfion(events[:,1:],events[:,0])
    for i in range(len(events)):
        es,bs=hopfion(events[i,1:],events[i,0])
        np.testing.assert_allclose(e[i],es,atol=1e-15)
        np.testing.assert_allclose(b[i],bs,atol=1e-15)
    target=transform_events(events,lorentz_matrix(v))
    en,bn=boosted_hopfion(target[:,1:],target[:,0],v)
    er,br=transform_fields(e,b,v)
    np.testing.assert_allclose(en,er,atol=1e-14)
    np.testing.assert_allclose(bn,br,atol=1e-14)
    back=transform_fields(en,bn,-v)
    for a,r in zip(back,(e,b)):np.testing.assert_allclose(a,r,atol=1e-14)


def test_identity_and_collinear_composition():
    p=np.array([[.2,.3,.4],[-.3,.5,-.7]])
    for a,b in zip(boosted_hopfion(p,.4,[0,0,0]),hopfion(p,.4)):
        np.testing.assert_array_equal(a,b)
    v,w=.3,-.4;total=(v+w)/(1+v*w)
    np.testing.assert_allclose(lorentz_matrix([w,0,0])@lorentz_matrix([v,0,0]),lorentz_matrix([total,0,0]),atol=2e-15)


def test_noncollinear_composition_uses_full_matrix():
    l1=lorentz_matrix([.4,0,0]);l2=lorentz_matrix([0,.3,0]);l=l2@l1
    assert not np.allclose(l,l1@l2)
    # Product is not symmetric, whereas a pure boost is: a rotation is present.
    assert np.max(np.abs(l-l.T))>.05
    event=np.array([.2,.3,-.4,.7]);f=field_tensor([1,2,3],[2,-1,4])
    seq=l2@(l1@f@l1.T)@l2.T
    np.testing.assert_allclose(seq,l@f@l.T,atol=2e-15)
    np.testing.assert_allclose(transform_events(transform_events(event,l1),l2),transform_events(event,l),atol=2e-15)


@pytest.mark.parametrize('v',[[1,0,0],[0,0,np.nan],[1,2], [.8,.8,0]])
def test_bad_velocity(v):
    with pytest.raises(ValueError):lorentz_matrix(v)


def test_maxwell_callback_against_independent_plane_wave():
    from electron_field_topology.diagnostics import maxwell_residuals
    def plane_wave(p,t):
        z=np.zeros(p.shape[:-1]);a=np.cos(p[...,2]-t)
        return np.stack([a,z,z],axis=-1),np.stack([z,a,z],axis=-1)
    p=np.random.default_rng(9).normal(size=(12,3))
    r=maxwell_residuals(p,.3,.01,field=plane_wave)
    for value in r.values():np.testing.assert_allclose(value,0,atol=3e-14)


def test_boosted_maxwell_refinement_and_wrong_time_control():
    from electron_field_topology.diagnostics import maxwell_residuals
    p=np.random.default_rng(4).uniform(-1,1,(30,3));v=np.array([.6,0,0])
    correct=lambda p,t:boosted_hopfion(p,t,v)
    def wrong(p,t):
        event=np.concatenate([np.full(p.shape[:-1]+(1,),t),p],axis=-1)
        source=transform_events(event,lorentz_matrix(-v))
        return transform_fields(*hopfion(source[...,1:],t),v)
    fine=maxwell_residuals(p,.3,.01,field=correct)
    coarse=maxwell_residuals(p,.3,.02,field=correct)
    for k in fine:
        ratio=np.linalg.norm(coarse[k])/np.linalg.norm(fine[k])
        assert 3.7<ratio<4.3
    bad=maxwell_residuals(p,.3,.01,field=wrong)
    assert np.linalg.norm(bad['ampere'])>100*np.linalg.norm(fine['ampere'])


def test_benchmark_configuration_is_bounded():
    import copy
    import json
    from pathlib import Path
    from electron_field_topology.relativity_benchmark import validate
    c=json.loads((Path(__file__).parents[1]/'experiments/configs/hopfion-s3a.json').read_text())
    validate(c)
    for key,value in [('orders',[24,40,128]),('radii',[4,8,100]),
                      ('event_count',10000),('velocities',[[.9,0,0]]),
                      ('difference_steps',[.04,.03,.01])]:
        bad=copy.deepcopy(c);bad[key]=value
        with pytest.raises(ValueError):validate(bad)
