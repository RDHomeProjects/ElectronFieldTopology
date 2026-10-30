"""Power-gradient, independent core and catalogue controls; Apache-2.0."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology.candidates import candidate,coordinates,potentials,reference,catalogue,core_curve,core_level,trace_core
from electron_field_topology.fields import hopfion
from electron_field_topology.candidate_benchmark import validate


@pytest.mark.parametrize('pair',[(1,1),(2,1),(2,3),(3,2)])
def test_independent_symbolic_power_gradients(pair):
    import sympy as s
    x,y,z,t=s.symbols('x y z t',real=True);r2=x*x+y*y+z*z;d=r2-(t-s.I)**2
    alpha=(r2-t*t-1+2*s.I*z)/d;beta=2*(x-s.I*y)/d;p,q=pair
    fa=s.Matrix([s.diff(alpha**p,v) for v in [x,y,z]]);fb=s.Matrix([s.diff(beta**q,v) for v in [x,y,z]])
    evaluate=s.lambdify((x,y,z,t),fa.cross(fb),'numpy',cse=True)
    points=np.random.default_rng(17).uniform(-1,1,(20,3));expected=np.asarray(evaluate(*points.T,.3)).squeeze().T
    e,b=candidate(points,.3,p,q)
    np.testing.assert_allclose(e+1j*b,expected,rtol=3e-13,atol=3e-13)


def test_baseline_vectorised_times_and_regular_zeros():
    points=np.random.default_rng(4).normal(size=(12,3));times=np.linspace(0,1,12)
    for a,b in zip(candidate(points,times,1,1),hopfion(points,times)):np.testing.assert_array_equal(a,b)
    e,b=candidate(np.zeros(3),0,2,3);np.testing.assert_array_equal(e,0);np.testing.assert_array_equal(b,0)


@pytest.mark.parametrize('pair',[(0,1),(-1,2),(1.5,2),(True,1),(6,1)])
def test_invalid_or_unbudgeted_kernel_powers(pair):
    with pytest.raises(ValueError):candidate(np.zeros(3),0,*pair)


def test_ledger_distinguishes_policy_from_invalidity():
    rows=catalogue([[1,1],[0,1],[2,2],[4,5],[True,1]])
    assert [r['status'] for r in rows]==['admitted','invalid_parameters','deferred_link_family','deferred_budget','invalid_parameters']
    assert reference(2,3)['energy']==reference(3,2)['energy']
    assert reference(2,3)['momentum']!=reference(3,2)['momentum']


def test_analytic_core_derivative_and_tangency():
    theta=np.linspace(.1,6,19);h=1e-6
    for p,q in [(1,1),(2,3),(3,2)]:
        for sign in [1,-1]:
            points,tangent=core_curve(theta,.75,p,q,sign)
            plus,_=core_curve(theta+h,.75,p,q,sign);minus,_=core_curve(theta-h,.75,p,q,sign)
            np.testing.assert_allclose(tangent,(plus-minus)/(2*h),rtol=3e-8,atol=1e-8)
            b=candidate(points,.75,p,q)[1]
            assert np.max(np.linalg.norm(np.cross(tangent,b),axis=-1)/(np.linalg.norm(tangent,axis=-1)*np.linalg.norm(b,axis=-1)))<1e-12
            value,level=core_level(points,.75,p,q);np.testing.assert_allclose(value,sign*level,atol=1e-14)


def test_family_potential_curl_is_field():
    points=np.array([[.2,-.3,.4],[.3,.2,-.1]]);h=1e-5;da=[];dc=[]
    for axis in np.eye(3):
        a1,c1=potentials(points+h*axis,.3,2,3);a0,c0=potentials(points-h*axis,.3,2,3)
        da.append((a1-a0)/(2*h));dc.append((c1-c0)/(2*h))
    def curl(j):return np.stack([j[1][:,2]-j[2][:,1],j[2][:,0]-j[0][:,2],j[0][:,1]-j[1][:,0]],axis=-1)
    e,b=candidate(points,.3,2,3)
    np.testing.assert_allclose(curl(da),b,atol=2e-8);np.testing.assert_allclose(curl(dc),e,atol=2e-8)


def test_bounded_catalogue_configuration():
    c=json.loads((Path(__file__).parents[1]/'experiments/configs/bateman-s4a.json').read_text());validate(c)
    for key,value in [('pairs',[[2,5]]),('trace_max_arclength',10000),('slice_grid',9999),('orders',[64,128,256])]:
        bad=copy.deepcopy(c);bad[key]=value
        with pytest.raises(ValueError):validate(bad)


def test_knot_trace_scans_returns_and_preserves_core():
    curve,meta=trace_core(2,3,0,1,phase=.8,tolerance=1e-9,max_arclength=30,samples=64)
    assert meta['closed'] and meta['accepted_return']['closure_gap']<1e-6
    assert meta['max_core_level_relative_error']<1e-5
    assert len(meta['section_returns'])>1
    assert meta['section_returns'][0]['closure_gap']>1e-3
    np.testing.assert_array_equal(curve[-1],curve[0])
