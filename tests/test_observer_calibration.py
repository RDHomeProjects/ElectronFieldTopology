from electron_field_topology.observer_calibration.selftest import manufactured

def test_cell_aware_quadrature_against_analytic_polynomial_and_kink():
    assert manufactured()['status']=='passed'
