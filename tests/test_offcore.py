"""Independent analytical curves, transport and rejection controls for S4-B."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology.offcore import trace_line,trace_candidate,transport_velocity,initial_null_checks
from electron_field_topology.knot_diagram import knot_determinant,diagram_link,invariant_gate,VIEWS,_determinant
from electron_field_topology.candidates import coordinates,core_curve,candidate
from electron_field_topology.linking import gauss_link
from electron_field_topology.offcore_benchmark import validate


def torus(a,b,n=128):
    t=np.linspace(0,2*np.pi,n+1)
    x=np.stack(((2+np.cos(b*t))*np.cos(a*t),(2+np.cos(b*t))*np.sin(a*t),np.sin(b*t)),axis=-1)
    x[-1]=x[0];return x


@pytest.mark.parametrize('a,b,expected',[(1,1,1),(2,3,3),(2,5,5)])
@pytest.mark.parametrize('segments',[64,128,256])
def test_independent_torus_invariants_across_projections_and_orientation(a,b,expected,segments):
    curve=torus(a,b,segments)
    for view in VIEWS:
        assert knot_determinant(curve,view)['determinant']==expected
        assert knot_determinant(curve[::-1],view)['determinant']==expected
    mirrored=curve.copy();mirrored[:,0]*=-1
    assert invariant_gate(mirrored)['determinant']==expected
    assert invariant_gate(curve)['knot_type']=='not_identified'


def test_exact_integer_determinant_pivoting_against_symbolic_control():
    import sympy
    for seed in range(12):
        matrix=np.random.default_rng(seed).integers(-4,5,(6,6))
        assert _determinant(matrix)==int(sympy.Matrix(matrix.tolist()).det())


def test_signed_link_diagram_independent_gauss_and_unlinked_controls():
    t=np.linspace(0,2*np.pi,129)
    a=np.stack((np.cos(t),np.sin(t),np.zeros_like(t)),axis=-1)
    b=np.stack((1+np.cos(t),np.zeros_like(t),np.sin(t)),axis=-1);a[-1]=a[0];b[-1]=b[0]
    assert abs(gauss_link(a,b)['linking_integral']+1)<.001
    for view in VIEWS:
        assert diagram_link(a,b,view)['linking_number']==-1
        assert diagram_link(a,b[::-1],view)['linking_number']==1
        assert diagram_link(a,b+[5,0,0],view)['linking_number']==0


def test_open_intersecting_and_irregular_projections_are_rejected():
    curve=torus(2,3);curve[-1]+=[.1,0,0]
    with pytest.raises(ValueError,match='open curve'):knot_determinant(curve)
    bow=np.array([[0,0,0],[1,1,0],[0,1,0],[1,0,0],[0,0,0]],float)
    with pytest.raises(ValueError,match='self-intersecting'):knot_determinant(bow)
    with pytest.raises(ValueError):knot_determinant(torus(1,1),[0,0,0])


def test_analytic_circle_closes_and_helix_does_not_get_closed():
    circle=lambda p:np.array([-p[1],p[0],0.])
    points,meta=trace_line(circle,[1,0,0],max_arclength=8,samples=64)
    assert meta['closed'] and abs(meta['accepted_return']['arclength']-2*np.pi)<1e-7
    np.testing.assert_allclose(points[:,0]**2+points[:,1]**2,1,atol=2e-8)
    assert meta['accepted_return']['tangent_mismatch']<1e-6
    helix=lambda p:np.array([-p[1],p[0],.1])
    points,meta=trace_line(helix,[1,0,0],max_arclength=8,samples=64)
    assert meta['status']=='unresolved_budget' and not meta['closed']
    assert meta['section_returns'] and meta['endpoint_correction']==0
    assert np.linalg.norm(points[-1]-points[0])>.1
    with pytest.raises(ValueError):knot_determinant(points)


def test_later_return_scanned_for_published_trefoil_control():
    seed=core_curve(.8,0,2,3,1)[0]
    _,meta=trace_candidate(seed,0,2,3,max_arclength=30,samples=64)
    assert meta['closed'] and meta['section_returns'][0]['closure_gap']>1e-3
    assert meta['accepted_return']['closure_gap']<1e-6


@pytest.mark.parametrize('seed',[[0,0,0],[1e-10,0,0],[1,0,0]])
def test_exact_and_near_field_zeros_do_not_supply_directions(seed):
    curve,meta=trace_candidate(seed,0,2,3)
    assert meta['status']=='near_zero_guard' and meta['function_evaluations']==0
    assert len(curve)==1 and not meta['closed']


def test_domain_and_evaluation_budgets_are_retained_as_distinct_outcomes():
    constant=lambda p:np.array([1.,0,0])
    curve,meta=trace_line(constant,[0,0,0],radius=2,max_arclength=8)
    assert meta['status']=='observation_radius' and abs(curve[-1,0]-2)<1e-10
    curve,meta=trace_line(constant,[0,0,0],max_evaluations=10)
    assert meta['status']=='evaluation_budget' and meta['function_evaluations']==10 and len(curve)==1
    _,meta=trace_line(lambda p:np.array([np.nan,0,0]),[0,0,0])
    assert meta['status']=='invalid_field'


def test_normalised_flow_extension_and_coordinate_transport_away_from_cores():
    seed=np.random.default_rng(7).uniform(-1,1,(20,3));v=transport_velocity(seed,0)
    np.testing.assert_allclose(np.linalg.norm(v,axis=-1),1,atol=1e-14)
    for t in [.25,.75]:
        x=seed+t*v
        for initial,later in zip(coordinates(seed,0),coordinates(x,t)):
            np.testing.assert_allclose(initial,later,atol=1e-14)
        e,b=candidate(x,t,2,3);velocity=np.cross(e,b)/(.5*np.sum(e*e+b*b,axis=-1))[:,None]
        np.testing.assert_allclose(velocity,transport_velocity(x,t),atol=1e-14)
    assert np.isfinite(transport_velocity([0,0,0],0)).all()


def test_sampled_initial_condition_residual_refines_without_global_claim():
    points=np.random.default_rng(9).uniform(-1,1,(16,3));result=initial_null_checks(points,2,3)
    assert result['max_normalised_null']<1e-12
    values=[r['max_normalised_complex_curl'] for r in result['complex_curl']]
    assert 3.5<values[0]/values[1]<4.5 and 3.5<values[1]/values[2]<4.5
    with pytest.raises(ValueError):initial_null_checks(np.zeros((2,3)),2,3)


@pytest.mark.parametrize('key,value',[('max_arclength',800),('tolerance',1e-15),('samples',True),('max_evaluations',100000)])
def test_trace_input_budgets_are_enforced(key,value):
    with pytest.raises(ValueError):trace_line(lambda x:np.array([1,0,0]),[0,0,0],**{key:value})


def test_frozen_configuration_cannot_expand_search_or_hide_boolean_powers():
    c=json.loads((Path(__file__).parents[1]/'experiments/configs/offcore-s4b.json').read_text());validate(c)
    for key,value in [('pairs',[[True,1]]),('arclength_budgets',[80,800]),('times',[0,.75,1])]:
        bad=copy.deepcopy(c);bad[key]=value
        with pytest.raises(ValueError):validate(bad)
