"""Independent residual check prevents optimizer flags becoming physics claims."""
import numpy as np
from electron_field_topology.skyrme import Energy,K,rational_field,coordinates,set_boundary
from electron_field_topology.sf_minimize import minimize_static


def test_small_cell_minimisation_decreases_energy_and_reports_measured_residual(tmp_path):
    h=.2;u=set_boundary(rational_field(coordinates(17,h),scale=.6,cutoff=1.3))
    eng=Energy(17,h,tmp_path,method='cell');initial=sum(eng.evaluate(u)[0]);rows=[]
    final,result=minimize_static(eng,u,5,lambda field,i:rows.append(sum(eng.evaluate(field)[0])),lambda:False)
    assert len(rows)==result['iterations'] and rows[-1]<initial
    assert all(b<=a+1e-12 for a,b in zip([initial]+rows,rows))
    parts,g=eng.evaluate(final);tangent=g-final*np.sum(g*final,axis=-1,keepdims=True)
    residual=np.sqrt(np.mean(tangent[2:-2,2:-2,2:-2]**2))/(K*h**3)
    if result['status']=='gradient_stationary':assert residual<1e-3
