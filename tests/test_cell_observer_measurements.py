from electron_field_topology.cell_observer_measurements.kernel.selftest import manufactured
from electron_field_topology.cell_observer_measurements.fits import test_power as check_power

def test_cell_integration_against_analytic_integrals():
 assert manufactured()['status']=='passed'

def test_nonnegative_power_against_independent_known_curve():
 assert check_power()['status']=='passed'
