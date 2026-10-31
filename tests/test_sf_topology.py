"""Independent polygon and manufactured-preimage controls for static fields."""
import numpy as np
import pytest
from electron_field_topology.sf_topology import preimages,resample,pd_code,diagram_analysis,jones_a
from electron_field_topology.skyrme import rational_field,coordinates
from electron_field_topology.knot_diagram import VIEWS


def test_manufactured_hopf_preimage_closed_and_spatially_resolved():
    u=rational_field(coordinates(49,.16),scale=1.,cutoff=3.6)
    p=preimages(u,.16)
    assert p['status']=='closed_components' and p['components']==1
    curve=p['curves'][0]
    np.testing.assert_array_equal(curve[0],curve[-1])
    assert len(curve)>100


def test_figure_eight_pd_and_numerical_complement_control():
    snappy=pytest.importorskip('snappy');from spherogram import Link
    t=np.linspace(.013,2*np.pi+.013,385)
    c=np.array([(2+np.cos(2*t))*np.cos(3*t),(2+np.cos(2*t))*np.sin(3*t),np.sin(4*t)]).T;c[-1]=c[0]
    polys=[]
    for view in VIEWS:
        link=Link(pd_code(c,view));link.simplify('global')
        assert link.exterior().is_isometric_to(snappy.Manifold('4_1'))
        polys.append(jones_a(link))
    assert polys==[{'-8':1,'-4':-1,'0':1,'4':-1,'8':1}]*3


def test_trefoil_jones_control_and_reversal():
    pytest.importorskip('snappy')
    t=np.linspace(.013,2*np.pi+.013,257)
    c=np.array([(2+np.cos(3*t))*np.cos(2*t),(2+np.cos(3*t))*np.sin(2*t),np.sin(3*t)]).T;c[-1]=c[0]
    a=diagram_analysis(c);b=diagram_analysis(c[::-1])
    assert a['jones_A']==b['jones_A']
    assert a['jones_A'] in [{'4':1,'12':1,'16':-1},{'-16':-1,'-12':1,'-4':1}]
    assert a['crossings']==3
