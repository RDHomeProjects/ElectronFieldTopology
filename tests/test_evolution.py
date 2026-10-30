"""Independent propagator controls; Apache-2.0."""
import numpy as np
import pytest
from electron_field_topology.evolution import FourierMaxwell,grid,cube_diagnostics
from electron_field_topology.fields import hopfion


def test_periodic_plane_wave_and_mean():
    p,dx=grid(17,np.pi)
    e=np.zeros_like(p);b=e.copy()
    e[...,1]=np.cos(p[...,0]);b[...,2]=np.cos(p[...,0])
    e[...,0]=.25  # zero mode must remain fixed
    solver=FourierMaxwell(e,b,dx)
    solver.advance(.73)
    en,bn=solver.fields()
    np.testing.assert_allclose(en[...,1],np.cos(p[...,0]-.73),atol=2e-14)
    np.testing.assert_allclose(bn[...,2],np.cos(p[...,0]-.73),atol=2e-14)
    np.testing.assert_allclose(en[...,0],.25,atol=2e-14)


def test_energy_divergence_and_time_subdivision():
    p,dx=grid(25,4)
    e,b=hopfion(p)
    one=FourierMaxwell(e,b,dx);many=FourierMaxwell(e,b,dx)
    initial=one.energy()
    one.advance(.6)
    for _ in range(8):many.advance(.6/8)
    for actual,expected in zip(one.fields(),many.fields()):
        np.testing.assert_allclose(actual,expected,atol=2e-14)
    assert abs(one.energy()/initial-1)<1e-13
    assert one.divergence_max()<1e-12
    one.advance(-.6)
    projected=FourierMaxwell(e,b,dx)
    for actual,expected in zip(one.fields(),projected.fields()):
        np.testing.assert_allclose(actual,expected,atol=2e-14)


def test_projection_is_measured_not_hidden():
    p,dx=grid(9,np.pi)
    e=np.zeros_like(p);b=e.copy();e[...,0]=np.sin(p[...,0])
    projected=FourierMaxwell(e,b,dx)
    assert projected.initial_projection_relative_l2>0.99
    assert projected.energy()<1e-25
    raw=FourierMaxwell(e,b,dx,project=False)
    raw.advance(.2)
    np.testing.assert_allclose(raw.fields()[0],e,atol=1e-14)
    assert raw.divergence_max()>.9


def test_cube_constant_fields():
    p,dx=grid(11,2)
    e=np.zeros_like(p);b=e.copy();e[...,0]=1;b[...,1]=1
    d=cube_diagnostics(e,b,dx,3)
    assert abs(d['outward_flux'])<1e-14
    assert abs(d['energy']-(6*dx)**3)<1e-12


@pytest.mark.parametrize('n',[4,8])
def test_unsupported_even_grid(n):
    with pytest.raises(ValueError):grid(n,2)


def test_solver_is_independent_of_analytical_evaluator(monkeypatch):
    import electron_field_topology.fields as fields
    p,dx=grid(17,4);e,b=hopfion(p)
    def forbidden(*a,**kw):raise AssertionError('analytical evaluation in solver')
    monkeypatch.setattr(fields,'hopfion',forbidden)
    solver=FourierMaxwell(e,b,dx);solver.advance(.3)
    assert np.isfinite(solver.fields()[0]).all()


def test_propagation_spatial_refinement():
    errors=[]
    for n in [17,25,33]:
        p,dx=grid(n,4.1);e,b=hopfion(p)
        solver=FourierMaxwell(e,b,dx);solver.advance(.5)
        en,bn=solver.fields();er,br=hopfion(p,.5)
        mask=np.max(np.abs(p),axis=-1)<=1.5
        errors.append(np.sqrt(np.sum((en[mask]-er[mask])**2+(bn[mask]-br[mask])**2)/np.sum(er[mask]**2+br[mask]**2)))
    assert errors[2]<errors[1]<errors[0]
    assert errors[-1]<.005


def test_config_rejects_unbounded_or_incoherent_work():
    import json
    from pathlib import Path
    from electron_field_topology.evolution_benchmark import validate
    c=json.loads(Path('experiments/configs/hopfion-s2.json').read_text())
    validate(c)
    c['time_flux']['intervals']=[8,17,32]
    with pytest.raises(ValueError):validate(c)
    c['time_flux']['intervals']=[8,16,32]
    c['spatial']['grids']=[999]
    with pytest.raises(ValueError):validate(c)
