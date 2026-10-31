"""Exact manufactured section returns and independent-control rejection checks."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from electron_field_topology.offcore import trace_line,trace_candidate
from electron_field_topology.return_map import torus_field,torus_check,section_coordinates,compare_returns
from electron_field_topology.returnmap_benchmark import validate,settings


@pytest.mark.parametrize('omega',[.5,np.sqrt(2)])
def test_analytic_torus_return_angles_and_known_periodicity(omega):
    phi=.3;seed=[2+.5*np.cos(phi),0,.5*np.sin(phi)]
    curve,meta=trace_line(torus_field(omega),seed,section_normal=[0,1,0],max_arclength=80,
                          tolerance=1e-10,max_step=.15,samples=128)
    result=torus_check(curve,meta,omega,phi)
    assert result['return_count']>=5 and result['max_wrapped_angle_error']<1e-7
    assert result['max_torus_equation_error']<1e-8
    assert meta['closed']==(omega==.5)
    plane=section_coordinates(meta)
    assert max(abs(r['plane_residual']) for r in plane['returns'])<1e-10
    if omega!=.5:
        assert meta['endpoint_correction']==0 and meta['status']=='unresolved_budget'
        assert plane['angular_interpretation']=='not_assigned'


def test_manufactured_torus_cartesian_field_is_independent_embedding_derivative():
    theta=np.array([.2,.7,2.1]);phi=np.array([.3,1.5,-.4]);omega=np.sqrt(2)
    rho=2+.5*np.cos(phi)
    positions=np.stack([rho*np.cos(theta),rho*np.sin(theta),.5*np.sin(phi)],axis=-1)
    analytic=np.stack([-rho*np.sin(theta)-.5*omega*np.sin(phi)*np.cos(theta),
                       rho*np.cos(theta)-.5*omega*np.sin(phi)*np.sin(theta),.5*omega*np.cos(phi)],axis=-1)
    np.testing.assert_allclose(np.array([torus_field(omega)(p) for p in positions]),analytic,atol=1e-14)


def test_return_plane_coordinates_and_short_budget_prefix():
    field=lambda p:np.array([-p[1],p[0],.15])
    _,short=trace_line(field,[1,0,0],max_arclength=10,tolerance=1e-10)
    _,long=trace_line(field,[1,0,0],max_arclength=20,tolerance=1e-10)
    match=compare_returns(long,short)
    assert match['repeatable'] and match['common_returns']>=1
    for row in section_coordinates(long)['returns']:
        assert np.linalg.norm(row['plane_coordinates'])==pytest.approx(row['closure_gap'],abs=1e-12)
    altered=copy.deepcopy(short);altered['section_returns'][0]['position'][0]+=.01
    assert compare_returns(long,altered)['comparison']=='control_sensitive'
    empty=copy.deepcopy(short);empty['section_returns']=[]
    assert compare_returns(long,empty)['comparison']=='insufficient_returns'


def test_changed_event_count_in_common_interval_is_not_silently_accepted():
    field=lambda p:np.array([-p[1],p[0],0.])
    _,meta=trace_line(field,[1,0,0],max_arclength=20)
    bad=copy.deepcopy(meta);bad['section_returns']=bad['section_returns'][:-1]
    assert compare_returns(meta,bad)['repeatable'] is False


def test_sections_are_transverse_and_supplied_normal_not_mutated():
    field=lambda p:np.array([-p[1],p[0],0.]);normal=np.array([0.,2.,0.])
    _,meta=trace_line(field,[1,0,0],section_normal=normal,max_arclength=8)
    np.testing.assert_array_equal(normal,[0,2,0]);assert meta['closed']
    with pytest.raises(ValueError,match='transverse'):trace_line(field,[1,0,0],section_normal=[1,0,0])
    for bad in [[0,0,0],[1,2],[np.nan,1,2]]:
        with pytest.raises(ValueError):trace_line(field,[1,0,0],section_normal=bad)


def test_fixed_experiment_has_eleven_settings_and_only_one_changed_control():
    c=json.loads((Path(__file__).parents[1]/'experiments/configs/returnmap-s4c.json').read_text());validate(c)
    rows=settings(c);assert len(rows)==11
    for _,key,_,setting in rows:
        assert sum(setting[k]!=c['baseline'][k] for k in c['baseline'])==(key is not None)
    c['variations']['max_arclength'].append(1000)
    with pytest.raises(ValueError):validate(c)
