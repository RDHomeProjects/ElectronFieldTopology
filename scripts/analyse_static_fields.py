"""Audit saved static fields; never infer knot identity from energy alone.

Run with: uv run --frozen --extra topology python scripts/analyse_static_fields.py
  --case artifacts/s5a-final/q18-129 --output artifacts/s5a-analysis/q18-129
The fields are float32 checkpoints; scalar histories retain original float64 results.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from electron_field_topology.skyrme import normalize,NORTH
from electron_field_topology.sf_topology import preimages,resample,diagram_analysis,VIEWS
from electron_field_topology.knot_diagram import diagram_link


def run(case,output,phases=('initial','final')):
    source=Path(case);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    config=json.loads((source/'config.json').read_text());report={'case':config['case'],'config':config,'phases':{},
        'scope':'finite polygon/checkpoint diagnostics; no continuum isotopy or expert certificate',
        'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for phase in phases:
        path=source/f'{phase}.npz'
        if not path.exists():continue
        data=np.load(path);raw=data['field'].astype(float);u=normalize(raw);h=float(data['h'])
        boundary=[]
        for axis in range(3):
            sl=[slice(None)]*4;sl[axis]=[0,1,len(u)-2,len(u)-1];boundary.append(float(np.max(abs(u[tuple(sl)]-NORTH))))
        row={'checkpoint_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'stored_unit_error':float(np.max(abs(np.linalg.norm(raw,axis=-1)-1))),
            'fixed_boundary_error':max(boundary),'targets':{}}
        for name,target in [('primary',[.000007,.000011,-1.]),('secondary',[.007,.011,-.999915])]:
            p=preimages(u,h,target=target);curves=p.pop('curves');p['components_data']=[]
            p['pairwise_link_checks']=[]
            for i in range(len(curves)):
                for j in range(i+1,len(curves)):
                    pair={'first':i,'second':j,'observations':[]}
                    for count in [256,384]:
                        for view in VIEWS:
                            try:check=diagram_link(resample(curves[i],count),resample(curves[j],count),view)
                            except ValueError as error:check={'status':'unresolved','reason':str(error)}
                            pair['observations'].append({'segments':count,'view':list(view),**check})
                    p['pairwise_link_checks'].append(pair)
            np.savez_compressed(out/f'{phase}-{name}-curves.npz',**{f'curve_{i}':c for i,c in enumerate(curves)})
            for i,curve in enumerate(curves):
                component={'vertices':len(curve)-1,'diagrams':[]}
                for count in [256,384,512]:
                    for view in VIEWS:
                        try:result=diagram_analysis(resample(curve,count),view)
                        except (ValueError,RuntimeError) as error:result={'status':'unresolved','reason':str(error)}
                        component['diagrams'].append({'segments':count,'view':list(view),**result})
                p['components_data'].append(component)
            row['targets'][name]=p
        report['phases'][phase]=row
        (out/'topology.json').write_text(json.dumps(report,indent=2)+'\n')
        print(config['case'],phase,{k:(v['status'],v.get('components')) for k,v in row['targets'].items()},flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',required=True);p.add_argument('--output',required=True)
    p.add_argument('--phases',nargs='+',default=['initial','final']);a=p.parse_args();run(a.case,a.output,a.phases)
