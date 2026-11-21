"""Check the requested backend before creating a run; no optimizer steps."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from common import ROOT, load, need, stamp

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--backend', choices=['auto', 'cpu', 'cuda'], required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo / 'src'))
    from electron_field_topology.sf_time import Grid
    from engine import Engine
    from integrity import source_run
    spec = load(ROOT / 'PLAN.json')['q21']
    with np.load(source_run(args.repo) / spec['source_field']['path'], allow_pickle=False) as z:
        source_backend = str(z['backend'])
        n = z['n'].copy()
    kind = source_backend if args.backend == 'auto' else args.backend
    engine = Engine(kind)
    device = None
    if kind == 'cuda':
        free, total = engine.xp.cuda.runtime.memGetInfo()
        need(free >= 2 * 1024**3, 'Less than 2 GiB free CUDA memory; choose cpu explicitly before creating a run')
        device = engine.port.identity()
    grid = Grid((97,) * 3, (23.04,) * 3, 'fixed')
    audit = engine.audit(engine.xp.asarray(n), grid)
    print(json.dumps({'recorded_at': stamp(), 'status': 'backend_probe_pass', 'requested': args.backend, 'selected': kind,
                      'source_backend': source_backend, 'backend_transfer': kind != source_backend, 'cuda_identity': device,
                      'energy_gradient_audit': audit, 'optimizer_steps': 0, 'physical_time_steps': 0}), flush=True)

if __name__ == '__main__':
    main()
