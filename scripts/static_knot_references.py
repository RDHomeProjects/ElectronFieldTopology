"""Independent cable-parameter and published hyperbolic-diagram references."""
import json
from pathlib import Path
import numpy as np
import snappy
from spherogram import Link
from electron_field_topology.sf_topology import cable_reference,diagram_analysis,jones_a,VIEWS


def run(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True);rows=[]
    for count in [256,384,512]:
        curve=cable_reference(count)
        np.savez_compressed(out/f'cable-reference-{count}.npz',curve=curve)
        for view in VIEWS:
            try:r=diagram_analysis(curve,view)
            except ValueError as error:r={'status':'unresolved','reason':str(error)}
            rows.append({'segments':count,'view':list(view),**r})
    link=Link('10_139');link.simplify('basic');manifold=link.exterior()
    report={'cable':{'construction':'Jennings Eq. 3.7, (Z1,Z0)=(t^4,t^6+.5t^3) on S3; stereographic curve',
                     'diagrams':rows},'hyperbolic':{'name':'10_139','source_label':'H4.851','pd':link.PD_code(),
                     'jones_A':jones_a(link),'numerical_volume':float(manifold.volume()),
                     'solution_type':manifold.solution_type()},
            'software':{'snappy':snappy.__version__},'scope':'finite diagrams and numerical complement references, not continuum field solutions'}
    (out/'references.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Reference diagrams retained',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();run(a.output)
