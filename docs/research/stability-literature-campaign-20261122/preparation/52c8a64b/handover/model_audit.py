"""Read-only normalization, energy decomposition and same-field operator audit."""
import numpy as np
from common import stamp,need
from evaluations import array_sha,metrics,gate_result
from numerics import geometry

def audit(n,g,folder,p):
    from electron_field_topology.skyrme import Energy,K
    before=array_sha(n);d4=metrics(n,g,p);geo=geometry(n,g);need(np.isclose(geo['e2']+geo['e4'],d4['energy'],rtol=2e-12,atol=2e-12),'Independent D4 energy decomposition differs')
    cell=Energy(g.shape[0],g.spacing[0],folder/'native-cell-build','cell');parts,raw=cell.evaluate(n);tangent=raw-n*np.sum(raw*n,axis=-1,keepdims=True);rms=float(np.sqrt(np.mean(tangent[2:-2,2:-2,2:-2]**2))/(K*g.spacing[0]**3))
    need(array_sha(n)==before,'Read-only operator audit mutated field')
    return {'recorded_at':stamp(),'normalization_K':float(K),'K_definition':'1/(32*pi^2*sqrt(2))','continuum_static_energy':'K integral[sum_i |partial_i n|^2 + sum_i<j |partial_i n cross partial_j n|^2] d3x','potential_U':0,'target':'S2 unit vector','boundary':'Two fixed north layers on each face','discrete_sigma':'Fourth-order positive nodal sigma form; not D4-transpose-D4 alone','quartic_derivatives':'Skew D4 with constant-zero exterior for n-NORTH','d4':d4,'d4_gates':gate_result(d4,21,p),'decomposition':geo,'native_cell_on_same_q21_field':{'energy':float(sum(parts)),'e2':float(parts[0]),'e4':float(parts[1]),'historical_style_tangent_gradient_rms':rms,'minimum_corner_cone':cell.minimum_corner_cone,'minimum_interpolant_norm':cell.minimum_interpolant_norm},'source_array_before':before,'source_array_after':array_sha(n),'optimizer_steps':0,'physical_time_steps':0,'scope':'Different discrete functionals and residual norms are named separately; no cell-to-D4 admission transfer or recovered-Q22 claim. Units are dimensionless model units, not SI electron units.'}
