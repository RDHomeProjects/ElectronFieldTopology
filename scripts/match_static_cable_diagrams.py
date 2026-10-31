"""Bounded Reidemeister-diagram witness search, beyond polynomial equality.

Documented Spherogram backtracking/simplification preserves knot type. A common
signed canonical Gauss word is a finite-diagram witness; failure is inconclusive.
This changes diagrams only, never a numerical field or its physical energy.
"""
import argparse
import json
from pathlib import Path
import random
import time
import snappy
from spherogram import Link
from electron_field_topology.sf_topology import canonical_gauss


def run(reference,topology,phase,output,seconds=120):
    refs=json.loads(Path(reference).read_text())['cable']['diagrams']
    targets=json.loads(Path(topology).read_text())['phases'][phase]['targets']['primary']
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    if targets.get('components')!=1:
        result={'matched':False,'reason':'not a single extracted component'};out.write_text(json.dumps(result,indent=2)+'\n');return result
    candidates=targets['components_data'][0]['diagrams'];pool={};attempts=0;witness=None
    def transformed(row,seed):
        nonlocal attempts
        random.seed(seed);pd=row.get('simplified_pd') or row.get('pd');link=Link(pd)
        if seed%2:link.backtrack(steps=6,prob_type_1=.2,prob_type_2=.4)
        link.simplify('global',type_III_limit=100);attempts+=1
        return canonical_gauss(link),{'seed':seed,'input_pd':pd,'output_pd':link.PD_code(),
                                     'segments':row['segments'],'view':row['view']}
    for row in refs:
        if not row.get('pd'):continue
        for seed in range(32):
            if time.monotonic()-start>seconds:break
            word,record=transformed(row,seed)
            if word is not None:pool[word]=record
    for row in candidates:
        if not row.get('pd'):continue
        for seed in range(32):
            if time.monotonic()-start>seconds:break
            word,record=transformed(row,seed)
            if word is not None and word in pool:
                witness={'canonical_gauss':word,'reference_path':pool[word],'candidate_path':record};break
        if witness is not None:break
    result={'matched':witness is not None,'witness':witness,'attempts':attempts,'reference_words':len(pool),
            'elapsed_seconds':time.monotonic()-start,'seed_range':[0,31],'seconds_budget':seconds,
            'scope':'replayable finite-diagram witness via documented moves; not continuum isotopy or formal proof',
            'snappy':snappy.__version__}
    out.write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='witness'},flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',required=True);p.add_argument('--topology',required=True)
    p.add_argument('--phase',default='final');p.add_argument('--output',required=True);a=p.parse_args()
    run(a.reference,a.topology,a.phase,a.output)
