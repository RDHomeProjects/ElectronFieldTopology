"""Independent stress/moment controls; Apache-2.0."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology.fields import hopfion
from electron_field_topology.localisation import (energy_moments,integrate_moments,
    stress_energy,density_peak)
from electron_field_topology.localisation_benchmark import reference,validate
from electron_field_topology.relativity import lorentz_matrix,transform_fields


def test_stress_covariance_trace_and_energy_dominance():
    e,b=np.random.default_rng(12).normal(size=(2,40,3));v=[.3,-.4,.2]
    t=stress_energy(e,b);matrix=lorentz_matrix(v)
    transformed=stress_energy(*transform_fields(e,b,v))
    np.testing.assert_allclose(transformed,np.einsum('ij,...jk,lk->...il',matrix,t,matrix),rtol=2e-14,atol=2e-14)
    np.testing.assert_allclose(t,np.swapaxes(t,-1,-2),atol=0)
    np.testing.assert_allclose(-t[...,0,0]+np.trace(t[...,1:,1:],axis1=-2,axis2=-1),0,atol=5e-15)
    assert np.all(np.linalg.norm(t[...,0,1:],axis=-1)<=t[...,0,0]+1e-14)


def test_weighted_two_point_moments_have_known_covariance():
    p=np.array([[-1.,0,0],[3,0,0]]);w=np.array([1.,3]);e=np.ones((2,3));b=np.zeros((2,3))
    m=energy_moments(p,w,e,b)
    np.testing.assert_allclose(m['centroid'],[2,0,0],atol=0)
    np.testing.assert_allclose(m['covariance'],np.diag([3,0,0]),atol=0)
    assert m['central_rms_squared']==3 and m['energy']==6


def test_origin_change_and_coordinate_translation_are_distinct():
    rng=np.random.default_rng(23);p,e,b=rng.normal(size=(3,20,3));w=np.ones(20);a=np.array([.5,-.2,.7])
    m=energy_moments(p,w,e,b);origin=energy_moments(p,w,e,b,origin=a)
    shifted=energy_moments(p-a,w,e,b)
    np.testing.assert_array_equal(m['centroid'],origin['centroid'])
    np.testing.assert_array_equal(m['covariance'],origin['covariance'])
    np.testing.assert_allclose(shifted['centroid'],np.array(m['centroid'])-a,atol=2e-16)
    np.testing.assert_allclose(shifted['covariance'],m['covariance'],atol=5e-16)
    expected=np.array(m['angular_momentum_about_origin'])-np.cross(a,m['momentum'])
    np.testing.assert_allclose(origin['angular_momentum_about_origin'],expected,atol=5e-15)
    np.testing.assert_allclose(m['angular_momentum_about_centroid'],shifted['angular_momentum_about_centroid'],atol=5e-15)


@pytest.mark.parametrize('time',[0,1,2])
def test_energy_density_and_t0_poynting_reductions(time):
    p=np.random.default_rng(7).normal(size=(30,3));r2=np.sum(p*p,axis=-1);x,y,z=p.T
    e,b=hopfion(p,time);u=(np.sum(e*e+b*b,axis=-1))/2
    expected=16*(r2+time*time-2*time*z+1)**2/((r2-time*time+1)**2+4*time*time)**3
    np.testing.assert_allclose(u,expected,rtol=3e-15,atol=1e-15)
    if time==0:
        flow=np.stack([-2*(x*z-y),-2*(x+y*z),x*x+y*y-z*z-1],axis=-1)/(1+r2)[:,None]
        np.testing.assert_allclose(np.cross(e,b),u[:,None]*flow,rtol=8e-15,atol=1e-15)


def test_all_space_radial_moments_and_angular_sign():
    row=integrate_moments(hopfion,0,32)
    np.testing.assert_allclose(row['energy'],2*np.pi**2,rtol=1e-12)
    np.testing.assert_allclose(row['covariance'],np.eye(3)/3,atol=1e-12)
    np.testing.assert_allclose(row['angular_momentum_about_origin'],[0,0,-np.pi**2],atol=1e-11)
    np.testing.assert_allclose(row['momentum'],[0,0,-np.pi**2],atol=1e-11)


def test_boost_reference_offset_and_zero_momentum_frame():
    _,_,r=reference([.6,0,0],0);np.testing.assert_allclose(r,[0,-.3,0],atol=1e-16)
    p,_,r=reference([0,0,-.5],2)
    np.testing.assert_allclose(p[1:],0,atol=2e-15);np.testing.assert_allclose(r,0,atol=2e-15)


def test_bounded_peak_finds_symmetric_t0_center():
    peak=density_peak(hopfion,0,2,9)
    np.testing.assert_allclose(peak['position'],0,atol=1e-7)
    np.testing.assert_allclose(peak['energy_density'],16,rtol=1e-13)


def test_benchmark_bounds_and_invalid_moment_weights():
    c=json.loads((Path(__file__).parents[1]/'experiments/configs/hopfion-s3b.json').read_text());validate(c)
    for key,value in [('orders',[24,40,128]),('radial_order_multiplier',4),('radii',[4,8,100]),('times',[0,1,20]),('peak_grids',[17,33,100]),('velocities',[[0,0,0],[.9,0,0],[0,0,0],[0,0,-.5]])]:
        bad=copy.deepcopy(c);bad[key]=value
        with pytest.raises(ValueError):validate(bad)
    p=np.zeros((2,3));e=np.ones((2,3))
    for w in [[-1,1],[np.nan,1],[0,0]]:
        with pytest.raises(ValueError):energy_moments(p,np.array(w),e,e)
