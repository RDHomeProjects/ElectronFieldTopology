"""Adversarial fixed-layer interpolation probe, not a soliton run. Apache-2.0."""
import argparse,json
from pathlib import Path
import numpy as np
from electron_field_topology.sf_checkpoints import timestamp
from electron_field_topology.sf_time import Grid
from electron_field_topology.sf_reconstruction import sample_cubic
from electron_field_topology.sf_time_initial import sample_static
from electron_field_topology.skyrme import NORTH

def measure():
    rest=Grid((81,)*3,(16.,)*3,'fixed')
    field=np.broadcast_to(NORTH,rest.shape+(3,)).copy()
    field[2,40,40]=[np.sin(.1),0,np.cos(.1)]
    rows=[]
    for beta in [.1,.3]:
        gamma=1/np.sqrt(1-beta*beta);count=2*int(np.ceil(80*gamma/2))+1
        lab=-8+16/(count-1);points=np.array([[lab*gamma,0.,0.]])
        old,_=sample_static(field,.2,points,0);new,jet=sample_cubic(field,rest,points,0)
        rows.append({'beta':beta,'lab_nodes_longitudinal':count,'inner_fixed_lab_coordinate':lab,
            'rest_coordinate':float(points[0,0]),'trilinear_deviation':float(abs(old-NORTH).max()),
            'cubic_deviation':float(abs(new-NORTH).max()),'cubic_rate':float(abs(-gamma*beta*jet).max())})
    return {'recorded_at':timestamp(),'scope':'Manufactured two-north-layer interpolation probe; not measured soliton field data.',
            'rest_fixed_layers_exact':bool(np.array_equal(field[rest.fixed_mask()],np.broadcast_to(NORTH,field[rest.fixed_mask()].shape))),
            'rows':rows}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=measure();a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
