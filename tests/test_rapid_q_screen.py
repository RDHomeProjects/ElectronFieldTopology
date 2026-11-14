from electron_field_topology.rapid_q_screen.engine import dst_fft
from electron_field_topology.rapid_q_screen.policy import classify
import numpy as np
from scipy.fft import dstn
def test_odd_extension_matches_independent_scipy_dst():
 a=np.random.default_rng(19).normal(size=(7,9,11,3));assert np.max(abs(dst_fft(a,np)-dstn(a,axes=(0,1,2),type=1,norm='ortho')))<1e-12
def test_slow_or_unresolved_is_not_a_q_rejection():
 p={'charge_relative_error':.05,'unit_limit':1e-10,'force_limit':1e-4,'acceleration_limit':1e-3,'force_ratio_priority':.05,'initial_tail_limit':.00075};m={'relative_force_l2':.1,'acceleration_max':1.,'hopf_integral':-7.,'minimum_corner_cone':.5,'unit_error':0.};r=classify(m,m,7,p);assert r['decision']=='defer_slow';m['hopf_integral']=-5.;assert classify(m,m,7,p)['decision']=='refine_representation'
