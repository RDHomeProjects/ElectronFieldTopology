"""Independent coordinate-dilation audit on a padded observation mesh.

Padding preserves the compact field support under expansion; coefficients stay
fixed. Interpolation/quadrature error is measured, not absorbed into a coupling.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from electron_field_topology.skyrme import Energy,normalize,NORTH


def run(checkpoint,output):
    path=Path(checkpoint);data=np.load(path);field=normalize(data['field'].astype(float));h=float(data['h']);n=len(field)
    margin=int(np.ceil(.02*(n-1)/2))+3;nn=n+2*margin
    out=Path(output);out.mkdir(parents=True,exist_ok=True);eng=Energy(nn,h,out/'native',method='cell')
    rows=[];axis=(np.arange(nn)-(nn-1)/2)
    for scale in [.98,.99,1.,1.01,1.02]:
        old=axis/scale+(n-1)/2;coords=np.array(np.meshgrid(old,old,old,indexing='ij'))
        u=np.stack([map_coordinates(field[...,i],coords,order=1,mode='constant',cval=NORTH[i]) for i in range(3)],axis=-1)
        u=normalize(u);parts,_=eng.evaluate(u)
        rows.append({'scale':scale,'e2':float(parts[0]),'e4':float(parts[1]),'energy':float(sum(parts))})
    base=rows[2];e=base['energy'];algebra=(base['e2']-base['e4'])/e
    comparisons=[]
    for a,b in [(0,4),(1,3)]:
        derivative=(rows[b]['energy']-rows[a]['energy'])/(rows[b]['scale']-rows[a]['scale'])/e
        comparisons.append({'delta':rows[b]['scale']-1,'normalized_energy_derivative':derivative,
                            'difference_from_e2_minus_e4':derivative-algebra})
    for r in rows:
        expected=r['scale']*base['e2']+base['e4']/r['scale']
        r['relative_scaling_law_defect']=(r['energy']-expected)/expected
    report={'checkpoint_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'n':n,'h':h,'padded_n':nn,
            'rows':rows,'normalized_e2_minus_e4':algebra,'finite_difference_comparisons':comparisons,
            'scope':'coordinate-resampled finite-grid audit; not exact continuum scaling or full stability'}
    (out/'scaling.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run(a.checkpoint,a.output)
