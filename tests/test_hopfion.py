"""Independent limits, symbolic identities and convergence; Apache-2.0."""
import numpy as np
import pytest
import sympy as s
from scipy.integrate import quad
from electron_field_topology import hopfion
from electron_field_topology.diagnostics import (
    energy_flow, maxwell_residuals, sphere_flux, sphere_integrals)


def cartesian(points, time):
    # Separate polynomial reduction of the rational Bateman expression.
    x, y, z = points.T
    a, b = x-1j*y, time-z-1j
    d = x*x+y*y+z*z-(time-1j)**2
    return np.stack((4*(b*b-a*a), -4j*(a*a+b*b), 8*a*b), axis=-1)/d[:, None]**3


@pytest.mark.parametrize('time', [-1.2, 0., .7, 2.])
def test_independent_cartesian_expression(time):
    p = np.random.default_rng(1729).uniform(-3, 3, (80, 3))
    e, b = hopfion(p, time)
    np.testing.assert_allclose(e+1j*b, cartesian(p, time), rtol=2e-13, atol=2e-14)


def test_origin_and_vectorisation():
    e, b = hopfion([0, 0, 0])
    np.testing.assert_array_equal(e, [-4, 0, 0])
    np.testing.assert_array_equal(b, [0, 4, 0])
    assert hopfion(np.zeros((2, 4, 3)))[0].shape == (2, 4, 3)


def test_null_invariants_and_radial_energy():
    p = np.random.default_rng(50).uniform(-2, 2, (100, 3))
    for time in [0., .4, 2.]:
        e, b = hopfion(p, time)
        u, _ = energy_flow(e, b)
        assert np.max(np.abs(np.sum(e*b, axis=-1))/u) < 1e-13
        assert np.max(np.abs(np.sum(e*e-b*b, axis=-1))/u) < 1e-13
    e, b = hopfion(p)
    np.testing.assert_allclose(energy_flow(e, b)[0], 16/(1+np.sum(p*p, axis=-1))**4,
                               rtol=2e-13)
    radial, _ = quad(lambda r: 64*np.pi*r*r/(1+r*r)**4, 0, np.inf)
    assert abs(radial-2*np.pi**2) < 1e-10


def test_symbolic_maxwell_for_cartesian_reference():
    # Exact algebra on an independently reduced polynomial; no numerical derivative.
    x, y, z, t = s.symbols('x y z t', real=True)
    a, b = x-s.I*y, t-z-s.I
    d = x*x+y*y+z*z-(t-s.I)**2
    f = s.Matrix([4*(b*b-a*a), -4*s.I*(a*a+b*b), 8*a*b])/d**3
    curl = s.Matrix([s.diff(f[2],y)-s.diff(f[1],z),
                     s.diff(f[0],z)-s.diff(f[2],x),
                     s.diff(f[1],x)-s.diff(f[0],y)])
    assert s.factor(sum(s.diff(f[i], q) for i, q in enumerate((x,y,z)))) == 0
    assert all(s.expand(s.factor(v)) == 0 for v in s.diff(f,t)+s.I*curl)


def test_residual_second_order_convergence():
    p = np.random.default_rng(1729).uniform(-1, 1, (40, 3))
    errors = []
    for h in [.04, .02, .01]:
        r = maxwell_residuals(p, .37, h)
        errors.append(max(np.max(np.abs(v)) for v in r.values()))
    # Centred differences have O(h^2) truncation: ratio should approach four.
    assert 3.5 < errors[0]/errors[1] < 4.5
    assert 3.5 < errors[1]/errors[2] < 4.5
    assert errors[-1] < .01


def test_offcentre_flux_convergence():
    errors = [abs(sphere_flux(1.4, n, .7, (.3,-.2,.1))['electric_flux'])
              for n in [8, 16, 32]]
    assert errors[1] < errors[0]/100
    assert errors[2] < 1e-11


def test_volume_quadrature_against_independent_radial_integral():
    radius = 4
    exact, _ = quad(lambda r: 64*np.pi*r*r/(1+r*r)**4, 0, radius)
    errors = [abs(sphere_integrals(radius, n)['energy']-exact) for n in [8,16,32]]
    assert errors[-1] < 1e-10
    assert errors[-1] < errors[0]/1000


@pytest.mark.parametrize('points,time', [([1,2], 0), ([0,np.nan,0],0), ([0,0,0],np.inf)])
def test_bad_inputs(points,time):
    with pytest.raises(ValueError):
        hopfion(points,time)

@pytest.mark.parametrize('radius,time', [(.7,0.), (1.4,.7), (2.5,2.)])
def test_flux_multiple_enclosing_surfaces(radius,time):
    flux = sphere_flux(radius,48,time,(.3,-.2,.1))
    assert abs(flux['electric_flux']) < 2e-11


def test_localisation_quadrature_convergence():
    # Finite-time moving-sphere integral. Coarse orders expose convergence;
    # orders 20+ already saturate round-off and cannot show a meaningful ratio.
    values = [sphere_integrals(2,n,2,(0,0,-1))['energy'] for n in [8,16,32]]
    assert abs(values[2]-values[1])/(2*np.pi**2) < 1e-9
    assert abs(values[2]-values[1]) < abs(values[1]-values[0])/100
