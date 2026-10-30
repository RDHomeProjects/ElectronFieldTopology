"""Independent controls for perturbation construction/observation; Apache-2.0."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.fft import fftn,fftfreq
from electron_field_topology.evolution import FourierMaxwell,grid
from electron_field_topology.fields import hopfion
from electron_field_topology.perturbations import (duality,invariants,null_scores,
    seeded_gaussian,fourier_cube,cube_energy)
from electron_field_topology.perturbation_benchmark import validate


def test_duality_has_independent_complex_reference_and_inverse():
    e,b=np.random.default_rng(4).normal(size=(2,20,3));angle=.37
    et,bt=duality(e,b,angle);reference=np.exp(1j*angle)*(e+1j*b)
    np.testing.assert_allclose(et+1j*bt,reference,atol=1e-15)
    back=duality(et,bt,-angle)
    for x,y in zip(back,[e,b]):np.testing.assert_allclose(x,y,atol=1e-15)
    np.testing.assert_allclose(np.sum(et*et+bt*bt,axis=-1),np.sum(e*e+b*b,axis=-1),atol=5e-15)


@pytest.mark.parametrize('time',[0,.5,1])
def test_analytic_controls_preserve_both_null_conditions(time):
    p=np.random.default_rng(9).normal(size=(40,3));e,b=hopfion(p,time)
    for fields in [(1.1*e,1.1*b),duality(e,b,.2)]:
        assert null_scores(*fields)['combined_null_score']<1e-14


def test_seed_reproduction_curl_constraint_and_gradient_negative_control():
    p,dx=grid(25,4)
    e,b,meta=seeded_gaussian(p,dx,11,.8)
    e2,b2,meta2=seeded_gaussian(p,dx,11,.8)
    np.testing.assert_array_equal(e,e2);assert meta==meta2
    solver=FourierMaxwell(e,b,dx,project=False)
    assert solver.divergence_max()<1e-13
    assert np.linalg.norm(np.mean(e,axis=(0,1,2)))<1e-16
    eg,bg,_=seeded_gaussian(p,dx,11,.8,mode='gradient')
    assert FourierMaxwell(eg,bg,dx,project=False).divergence_max()>.01
    removed=FourierMaxwell(eg,bg,dx)
    assert removed.initial_projection_relative_l2>.999
    assert removed.energy()<1e-26


def test_spectral_curl_sign_against_single_analytic_mode():
    p,dx=grid(17,np.pi);axis=2*np.pi*fftfreq(17,d=dx)
    k=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1)
    a=np.zeros_like(p);a[...,2]=np.sin(p[...,0])
    from scipy.fft import ifftn
    curl=ifftn(1j*np.cross(k,fftn(a,axes=(0,1,2))),axes=(0,1,2)).real
    np.testing.assert_allclose(curl[...,1],-np.cos(p[...,0]),atol=4e-15)
    np.testing.assert_allclose(curl[...,[0,2]],0,atol=4e-15)


def test_fourier_observer_origin_and_off_grid_phase():
    p,dx=grid(17,np.pi);e=np.zeros_like(p)
    e[...,0]=.3;e[...,1]=np.cos(2*p[...,0]-.4);e[...,2]=np.sin(p[...,1]+p[...,2])
    axis=np.linspace(-1.2,1.2,13)
    sampled=fourier_cube(fftn(e,axes=(0,1,2)),dx,axis)
    x,y,z=np.meshgrid(axis,axis,axis,indexing='ij')
    np.testing.assert_allclose(sampled[...,0],.3,atol=1e-15)
    np.testing.assert_allclose(sampled[...,1],np.cos(2*x-.4),atol=3e-15)
    np.testing.assert_allclose(sampled[...,2],np.sin(y+z),atol=3e-15)
    ones=np.ones_like(sampled);zeros=np.zeros_like(sampled)
    np.testing.assert_allclose(cube_energy(ones,zeros,axis),1.5*2.4**3,atol=1e-13)


def test_perturbed_plane_waves_superpose_with_conserved_difference_energy():
    p,dx=grid(17,np.pi);e=np.zeros_like(p);b=e.copy();e[...,1]=np.cos(p[...,0]);b[...,2]=e[...,1]
    de=np.zeros_like(p);db=de.copy();de[...,0]=.05*np.cos(p[...,2]);db[...,1]=de[...,0]
    base=FourierMaxwell(e,b,dx,project=False);total=FourierMaxwell(e+de,b+db,dx,project=False)
    initial=dx**3*np.sum(de*de+db*db)/2
    base.advance(.4);total.advance(.4);be,bb=base.fields();ce,cb=total.fields()
    expected_e=np.zeros_like(p);expected_b=expected_e.copy();expected_e[...,0]=.05*np.cos(p[...,2]-.4);expected_b[...,1]=expected_e[...,0]
    np.testing.assert_allclose(ce-be,expected_e,atol=2e-15);np.testing.assert_allclose(cb-bb,expected_b,atol=2e-15)
    np.testing.assert_allclose(dx**3*np.sum((ce-be)**2+(cb-bb)**2)/2,initial,rtol=2e-15)
    assert null_scores(ce,cb)['combined_null_score']>1e-3


def test_config_bounds_and_rejected_modes():
    c=json.loads((Path(__file__).parents[1]/'experiments/configs/hopfion-s3c.json').read_text());validate(c)
    for key,value in [('spatial',{'half_extent':6.1,'grids':[25,49,999]}),('times',[0,1,100]),('amplitudes',[.1,1,10]),('flux_intervals',[8,16,10000])]:
        bad=copy.deepcopy(c);bad[key]=value
        with pytest.raises(ValueError):validate(bad)
    p,dx=grid(9,3)
    with pytest.raises(ValueError):seeded_gaussian(p,dx,11,.8,'hidden projection')
    with pytest.raises(ValueError):duality(np.ones(3),np.ones(3),np.nan)
