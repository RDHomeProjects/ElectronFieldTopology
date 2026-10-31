"""Independent oriented curve and signed modal helicity controls; Apache-2.0."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology.evolution import grid
from electron_field_topology.fields import hopfion
from electron_field_topology.helicity import coulomb_potential,periodic_helicities,remove_mean,bateman_potentials
from electron_field_topology.linking import gauss_link,trace_closed_line
from electron_field_topology.topology_benchmark import circles,validate


@pytest.mark.parametrize('q',[-2,-1,1,2])
def test_signed_beltrami_potential_and_helicity(q):
    p,dx=grid(17,np.pi);b=np.zeros_like(p);b[...,0]=np.sin(q*p[...,2]);b[...,1]=np.cos(q*p[...,2])
    a,checks=coulomb_potential(b,dx)
    np.testing.assert_allclose(a,b/q,atol=1e-15)
    h=periodic_helicities(np.zeros_like(p),b,dx)
    np.testing.assert_allclose(h['magnetic_helicity'],(2*np.pi)**3/q,rtol=2e-15)
    assert checks['relative_curl_reconstruction_error']<1e-14


@pytest.mark.parametrize('kind',['mean','longitudinal'])
def test_periodic_inadmissible_fields_are_rejected(kind):
    p,dx=grid(17,np.pi);b=np.zeros_like(p)
    if kind=='mean':b[...,0]=1
    else:b[...,0]=np.sin(p[...,0])
    with pytest.raises(ValueError):coulomb_potential(b,dx)
    if kind=='mean':
        fluctuation,removed=remove_mean(b);np.testing.assert_array_equal(removed,[1,0,0]);np.testing.assert_array_equal(fluctuation,0)


def test_periodic_gauge_gradient_invariance():
    p,dx=grid(17,np.pi);b=np.zeros_like(p);b[...,0]=np.sin(p[...,2]);b[...,1]=np.cos(p[...,2])
    a,_=coulomb_potential(b,dx);grad=np.zeros_like(p);grad[...,0]=np.cos(p[...,0]);grad[...,2]=-.3*np.sin(p[...,2])
    np.testing.assert_allclose(dx**3*np.sum((a+grad)*b),dx**3*np.sum(a*b),rtol=2e-15)


def test_bateman_potentials_curl_and_normalisation_at_origin():
    # Direct initial values from alpha=-1 and grad beta=(2,-2i,0).
    a,c=bateman_potentials(np.zeros(3),0)
    np.testing.assert_array_equal(a,[0,2,0]);np.testing.assert_array_equal(c,[-2,0,0])
    p=np.array([.2,-.3,.4]);h=1e-5;da=[];dc=[]
    for axis in np.eye(3):
        ap,cp=bateman_potentials(p+h*axis,.3);am,cm=bateman_potentials(p-h*axis,.3)
        da.append((ap-am)/(2*h));dc.append((cp-cm)/(2*h))
    def curl(j):return np.array([j[1][2]-j[2][1],j[2][0]-j[0][2],j[0][1]-j[1][0]])
    e,b=hopfion(p,.3)
    np.testing.assert_allclose(curl(da),b,atol=2e-9);np.testing.assert_allclose(curl(dc),e,atol=2e-9)


def test_link_orientation_reversal_and_unlinked_control():
    a,b=circles(128);_,unlinked=circles(128,3)
    assert abs(gauss_link(a,b)['linking_integral']+1)<5e-4
    assert abs(gauss_link(a,b[::-1])['linking_integral']-1)<5e-4
    assert abs(gauss_link(a,unlinked)['linking_integral'])<1e-8


@pytest.mark.parametrize('kind',['open','degenerate','intersecting','self_intersecting'])
def test_invalid_curve_inputs_are_rejected(kind):
    a,b=circles(64)
    if kind=='open':a=a[:-1]
    elif kind=='degenerate':a[2]=a[1]
    elif kind=='intersecting':a,b=circles(64,0)
    else:
        a=np.array([[-1,-1,0],[1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0]],dtype=float)
    with pytest.raises(ValueError):gauss_link(a,b)


def test_trace_closure_and_open_budget_are_distinct():
    curve,meta=trace_closed_line(lambda p:np.array([-p[1],p[0],0]),[1,0,0],samples=64,tolerance=1e-10)
    assert meta['closed'];assert meta['closure_gap_before_correction']<1e-8
    np.testing.assert_allclose(meta['arclength'],2*np.pi,atol=1e-8)
    np.testing.assert_allclose(np.linalg.norm(curve[:,:2],axis=1),1,atol=1e-8)
    open_curve,failure=trace_closed_line(lambda p:np.array([1,0,0]),[0,0,0],max_arclength=4)
    assert not failure['closed'] and failure['endpoint_correction']==0
    with pytest.raises(ValueError):gauss_link(open_curve,curve)


def test_topology_config_is_bounded():
    c=json.loads((Path(__file__).parents[1]/'experiments/configs/hopfion-s3d.json').read_text());validate(c)
    for key,value in [('link_segments',[128,256,10000]),('trace_max_arclength',10000),('modal_grid',1001),('trace_tolerances',[1e-5,1e-6,1e-7])]:
        bad=copy.deepcopy(c);bad[key]=value
        with pytest.raises(ValueError):validate(bad)


def test_opposite_chiralities_cancel_without_zero_energy():
    p,dx=grid(17,np.pi);b=np.zeros_like(p);b[...,1]=2*np.cos(p[...,2])
    h=periodic_helicities(np.zeros_like(p),b,dx)
    assert abs(h['magnetic_helicity'])<1e-12
    np.testing.assert_allclose(dx**3*np.sum(b*b)/2,(2*np.pi)**3,rtol=2e-15)
