"""Read-only full-field audit of a completed low-Q campaign. Apache-2.0.

No optimization, physical-time evolution, renderer input or automatic gate release.
Source/equation map: docs/plans/sf-motion-diagnostics.md.
"""
import argparse
import csv
import fcntl
import hashlib
import json
from pathlib import Path
import platform
import re
import signal
import subprocess
import time
import zipfile

import numpy as np
import scipy
from scipy.interpolate import RegularGridInterpolator

from .sf_checkpoints import atomic_json as _atomic_json, timestamp
from .sf_dynamics_admission import sha
from .sf_motion_metrics import evaluate, spatial_metrics, translated_reference
from .sf_time import Grid, acceleration, densities, derivative, gradients
from .sf_time_initial import boosted_static
from .sf_time_run import MODEL, SCHEME, canonical_sha, state_sha
from .skyrme import K, NORTH

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT/'experiments/configs/sf-motion/diagnostics.json'
SCOPE = ('Read-only finite-box field diagnostics and classical kinetic metric; '
         'no new trajectory, quantum spectrum, electric charge or electron acceptance.')
SOURCES = ['sf_motion_diagnostics.py', 'sf_time.py', 'sf_time_initial.py',
           'sf_time_run.py', 'sf_motion_metrics.py', 'sf_readmission.py',
           'sf_dynamics.py', 'sf_time_controls.py', 'skyrme.py',
           'sf_motion_diagnostics_local.py', 'sf_motion_local.py',
           'sf_checkpoints.py', 'sf_dynamics_admission.py']


def atomic_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    _atomic_json(path,value)


def event(message, **values):
    print(json.dumps({'recorded_at': timestamp(), 'message': message, **values}), flush=True)


def validate_config(config):
    if set(config) != {'format', 'evidence_sha256', 'case_ids', 'comparison_grids',
                       'shell_width', 'replay_rtol', 'replay_atol'}:
        raise ValueError('Explicit diagnostic configuration required')
    if config['format'] != 'EFT-motion-diagnostics-v1':
        raise ValueError('Unknown diagnostic format')
    if not re.fullmatch('[0-9a-f]{64}', config['evidence_sha256']):
        raise ValueError('Expected archive SHA-256 required')
    sizes = config['comparison_grids']
    if (not sizes or len(set(sizes)) != len(sizes)
            or any(type(n) is not int or n < 5 or n % 2 != 1 for n in sizes)):
        raise ValueError('Distinct odd diagnostic sampling grids required')
    if (not isinstance(config['case_ids'], list)
            or len(set(config['case_ids'])) != len(config['case_ids'])):
        raise ValueError('Distinct case IDs required')
    for k in ('shell_width', 'replay_rtol', 'replay_atol'):
        if not np.isfinite(config[k]) or config[k] <= 0:
            raise ValueError('Positive diagnostic settings required')


def compact(source, config):
    """Use authenticated compact records rather than their embedded absolute paths."""
    validate_config(config)
    path = Path(source)/'evidence.zip'
    if not path.is_file():
        raise ValueError('Original campaign evidence.zip is missing: '+str(path)+
                         '. Choose --source pointing to the retained campaign; no field is regenerated.')
    if sha(path) != config['evidence_sha256']:
        raise ValueError('Source evidence archive differs from the declared SHA-256')
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or z.testzip() is not None:
            raise ValueError('Duplicate or corrupt evidence member')
        hashes = json.loads(z.read('evidence-hashes.json'))['sha256']
        if set(names) != set(hashes) | {'evidence-hashes.json'}:
            raise ValueError('Evidence member coverage differs')
        for name, digest in hashes.items():
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise ValueError('Evidence member hash differs: '+name)
        campaign = json.loads(z.read('campaign.json'))
        plan = json.loads(z.read('plan.json'))
        pairs = json.loads(z.read('comparisons.json'))['pairs']
        records = {n: json.loads(z.read(n)) for n in names
                   if n.endswith('/manifest.json') and n.startswith('cases/')}
    if campaign['status'] != 'complete_pending_review':
        raise ValueError('A completed source campaign is required')
    if canonical_sha(plan) != campaign['config_sha256']:
        raise ValueError('Source plan digest differs')
    if config['shell_width'] != plan['boundary_shell_width']:
        raise ValueError('Use the original shell convention for replay')
    selected = config['case_ids'] or [k for k, v in campaign['cases'].items()
                                      if v['status'] == 'complete']
    if any(k not in campaign['cases'] or campaign['cases'][k]['status'] != 'complete'
           for k in selected):
        raise ValueError('A selected case is absent or incomplete')
    for name, digest in campaign['source_sha256'].items():
        if sha(Path(__file__).with_name(name)) != digest:
            raise ValueError('Original numerical source changed: '+name)
    # Controls is outside the original eight-file campaign map, but affects run provenance.
    for manifest in records.values():
        if any(sha(Path(__file__).with_name(n)) != d
               for n, d in manifest['physics_source_sha256'].items()):
            raise ValueError('Original time-driver source changed')
    return campaign, plan, pairs, selected, records


def attempt_path(source, case):
    name = Path(case['attempts'][-1]).name
    if not re.fullmatch(r'attempt-\d{3,}', name):
        raise ValueError('Unrecognized retained attempt directory')
    return Path(source)/'cases'/case['id']/name


def inventory(source, config):
    source = Path(source).expanduser().resolve()
    campaign, plan, pairs, selected, manifests = compact(source, config)
    seeds = sorted({campaign['cases'][k]['seed_id'] for k in selected})
    files = []
    def add(relative, expected=None):
        p = source/relative
        row = {'path': str(p), 'relative_path': str(relative), 'expected_sha256': expected}
        if not p.is_file():
            row['status'] = 'missing'
        else:
            row['sha256'] = sha(p)
            row['status'] = 'verified' if expected else 'present_metadata_and_state_checked_during_audit'
            if expected and row['sha256'] != expected:
                row['status'] = 'hash_mismatch'
        files.append(row)
    for sid in seeds:
        add(Path('readmission')/sid/'latest.npz', campaign['seeds'][sid]['field_sha256'])
    for name in selected:
        case = campaign['cases'][name];base = attempt_path(source, case).relative_to(source)
        add(base/'initial.npz')
        add(base/'final.npz', case['final_checkpoint_sha256'])
    bad = [r for r in files if r['status'] in ('missing', 'hash_mismatch')]
    fingerprint = canonical_sha({'evidence': config['evidence_sha256'],
                                 'files': {r['relative_path']: r.get('sha256') for r in files}})
    with zipfile.ZipFile(source/'evidence.zip') as z:
        member_count=len(json.loads(z.read('evidence-hashes.json'))['sha256'])
    return {'recorded_at': timestamp(), 'ready': not bad, 'source_campaign': str(source),
            'evidence_sha256': config['evidence_sha256'], 'archive_members_verified':
            member_count,
            'selected_cases': selected, 'selected_seeds': seeds, 'files': files,
            'missing_or_changed': bad, 'input_fingerprint': fingerprint,
            'scope': 'Initial files have no published file digest; metadata and regenerated-state checks follow.'}


def load_rest(source, sid, campaign):
    p = Path(source)/'readmission'/sid/'latest.npz'
    row = campaign['seed_configs'][sid]
    if sha(p) != campaign['seeds'][sid]['field_sha256']:
        raise ValueError('Retained rest field changed: '+sid)
    with np.load(p, allow_pickle=False) as d:
        n = d['field'].copy();v = d['field_rate'].copy();h = float(d['h'])
        if str(d['model_id']) != MODEL or str(d['scheme']) != SCHEME or int(d['expected_q']) != row['q']:
            raise ValueError('Retained rest model/scheme/Q differs')
    grid = Grid((row['nodes'],)*3, (row['length'],)*3, 'fixed')
    if n.dtype != np.float64 or n.shape != grid.shape+(3,) or h != grid.spacing[0] or np.max(abs(v)) != 0:
        raise ValueError('Retained rest precision/geometry/rate differs')
    return n, grid


def load_state(source, case, manifests, which):
    base = attempt_path(source, case);path = base/(which+'.npz')
    if which == 'final' and sha(path) != case['final_checkpoint_sha256']:
        raise ValueError('Retained final checkpoint changed')
    manifest = manifests[f'cases/{case["id"]}/{base.name}/manifest.json']
    grid = Grid(tuple(case['physical']['grid']), tuple(case['physical']['lengths']), 'fixed')
    with np.load(path, allow_pickle=False) as d:
        n = d['field'].copy();v = d['field_rate'].copy()
        expected_step = 0 if which == 'initial' else case['physical']['steps']
        if (str(d['model_id']) != MODEL or str(d['scheme']) != SCHEME
                or str(d['physics_sha256']) != canonical_sha(case['physical'])
                or str(d['code_sha256']) != manifest['code_sha256']
                or int(d['step']) != expected_step
                or float(d['time']) != expected_step*case['physical']['dt']):
            raise ValueError('Retained checkpoint metadata differs')
    if n.dtype != np.float64 or v.dtype != np.float64 or n.shape != grid.shape+(3,) or v.shape != n.shape:
        raise ValueError('Retained state precision/shape differs')
    if not np.isfinite(n).all() or not np.isfinite(v).all():
        raise ValueError('Nonfinite retained state')
    if which == 'final' and state_sha(n,v) != case['result']['state_sha256']:
        raise ValueError('Retained final array digest differs')
    return n,v,grid


def fit(rows):
    t = np.array([r['time'] for r in rows]);x = np.array([r['centroid'] for r in rows])
    return np.linalg.lstsq(np.stack([t-t[0], np.ones(len(t))], axis=-1), x, rcond=None)[0][0]


def common_time_fit(a, b):
    aa = {round(r['time'],12):r for r in a};bb = {round(r['time'],12):r for r in b}
    times = sorted(aa.keys() & bb.keys())
    if len(times) < 3:
        raise ValueError('At least three shared physical times required')
    av = fit([aa[t] for t in times]);bv = fit([bb[t] for t in times])
    return {'common_times': times, 'velocity_a': av.tolist(), 'velocity_b': bv.tolist(),
            'common_time_velocity_difference': float(np.linalg.norm(av-bv)),
            'original_fit_velocity_difference': float(np.linalg.norm(fit(a)-fit(b))),
            'max_common_centroid_difference': max(float(np.linalg.norm(np.array(aa[t]['centroid'])-bb[t]['centroid'])) for t in times)}


def sample_uniform(field, grid, points):
    """Raw linear interpolation, without renormalizing or changing stored fields."""
    axes = [-l/2+np.arange(n)*h for n,l,h in zip(grid.shape,grid.lengths,grid.spacing)]
    return RegularGridInterpolator(axes,field,method='linear',bounds_error=True)(points)


def field_difference(na,va,nb,vb):
    scale = max(float(np.linalg.norm(na-NORTH)),float(np.linalg.norm(nb-NORTH)),1e-30)
    rates = max(float(np.linalg.norm(va)),float(np.linalg.norm(vb)),1e-30)
    delta = float(np.linalg.norm(na-nb));dv = float(np.linalg.norm(va-vb))
    return {'field_relative_l2': delta/scale, 'field_rms': float(np.sqrt(np.mean((na-nb)**2))),
            'rate_relative_l2': dv/rates, 'rate_difference_over_field_scale': dv/scale,
            'rate_rms': float(np.sqrt(np.mean((va-vb)**2))),
            'scope': 'Rate-relative values near zero rates are ill-conditioned; use absolute/scaled rate differences too.'}


def classical_metric(n, grid):
    """T=K integral v.M.v = .5 G_ab qdot_a qdot_b, derived for this SF action."""
    d = gradients(n-NORTH,grid);points = grid.points();modes = [-d[...,i,:] for i in range(3)]
    basis = np.eye(3)
    for e in basis:
        orbital = np.cross(e,points)
        modes.append(-np.einsum('...i,...ia->...a',orbital,d))
    modes.append(np.cross(basis[2],n))
    fixed = grid.fixed_mask()
    for i,m in enumerate(modes):
        m = m-n*np.sum(n*m,axis=-1,keepdims=True);m[fixed]=0;modes[i]=m
    trace = np.sum(d*d,axis=(-2,-1));G = np.empty((7,7));dv = np.prod(grid.spacing)
    for j,mode in enumerate(modes):
        acted = (1+trace)[...,None]*mode-np.einsum('...ia,...i->...a',d,np.einsum('...ia,...a->...i',d,mode))
        for i,other in enumerate(modes):G[i,j]=2*K*float(np.sum(other*acted))*dv
    G = (G+G.T)*.5
    return {'basis': ['translation_x','translation_y','translation_z','rotation_x','rotation_y','rotation_z','internal_phase_z'],
            'metric': G.tolist(), 'eigenvalues': np.linalg.eigvalsh(G).tolist(),
            'rotational_diagonal': np.diag(G)[3:6].tolist(), 'internal_phase_inertia': float(G[6,6]),
            'scope': 'Classical finite-box kinetic Gram matrix in model units; symmetry-related null directions may occur. No inversion or spin assignment.'}


def face_diagnostics(n, v, grid, width):
    data = densities(n,v,grid);energy = data['energy_density'];total = float(np.sum(energy));points=grid.points()
    result = {}
    for axis in range(3):
        other = [i for i in range(3) if i!=axis];area = float(np.prod([grid.spacing[i] for i in other]))
        for sign in (-1,1):
            mask = sign*points[...,axis] >= grid.lengths[axis]/2-width
            coordinate = sign*(grid.lengths[axis]/2-width)
            index = int(round((coordinate+grid.lengths[axis]/2)/grid.spacing[axis]))
            plane = np.take(data['energy_flux'][...,axis],index,axis=axis)
            result[f'{"xyz"[axis]}{"+" if sign>0 else "-"}'] = {
                'shell_fraction': float(np.sum(energy[mask])/max(total,1e-30)),
                'plane_coordinate': float(-grid.lengths[axis]/2+index*grid.spacing[axis]),
                'instantaneous_outward_plane_flux': float(sign*np.sum(plane)*area)}
    return {'faces': result, 'scope': 'Per-face shells overlap at edges/corners; flux is an endpoint rectangular-plane diagnostic, not integrated escaped energy or a discrete Noether flux.'}


def transport_diagnostics(n, v, grid, beta, axis):
    dn = derivative(n-NORTH,grid.spacing[axis],axis,'fixed')
    d2n = derivative(dn,grid.spacing[axis],axis,'fixed')
    project = lambda x:x-n*np.sum(n*x,axis=-1,keepdims=True)
    rate = project(-beta*dn);rate[grid.fixed_mask()]=0
    a = acceleration(n,v,grid)[1];expected_tangent=project(beta*beta*d2n)
    delta=project(a)-expected_tangent;delta[grid.fixed_mask()]=0
    return {'rate_relative_l2': float(np.linalg.norm(v-rate)/max(np.linalg.norm(v),np.linalg.norm(rate),1e-30)) if beta else None,
            'rate_difference_rms': float(np.sqrt(np.mean((v-rate)**2))),
            'tangent_acceleration_difference_rms': float(np.sqrt(np.mean(delta**2))),
            'tangent_acceleration_difference_max': float(np.max(np.linalg.norm(delta,axis=-1))),
            'tangent_acceleration_relative_l2': float(np.linalg.norm(delta)/max(np.linalg.norm(project(a)),np.linalg.norm(expected_tangent),1e-30)) if beta else None,
            'actual_acceleration_rms': float(np.sqrt(np.mean(a*a))),
            'scope': 'D4 transport identity diagnostic. Interpolant/discretization errors and imperfect static equilibrium contribute; not a continuum residual theorem.'}


def seed_audit(source, sid, campaign, config):
    n,grid = load_rest(source,sid,campaign)
    return {'recorded_at': timestamp(), 'seed_id':sid, 'grid':list(grid.shape), 'lengths':list(grid.lengths),
            'spatial': spatial_metrics(n,np.zeros_like(n),grid,config['shell_width']),
            'classical_metric': classical_metric(n,grid),
            'faces':face_diagnostics(n,np.zeros_like(n),grid,config['shell_width']), 'scope':SCOPE}


def case_audit(source, case, campaign, plan, manifests, config):
    rest,rg = load_rest(source,case['seed_id'],campaign)
    ni,vi,grid = load_state(source,case,manifests,'initial')
    if case['beta']:
        rebuilt_n,rebuilt_v = boosted_static(rest,rg.spacing[0],grid,case['beta'],case['axis'])
    else:
        rebuilt_n,rebuilt_v = rest.copy(),np.zeros_like(rest)
    if state_sha(ni,vi) != state_sha(rebuilt_n,rebuilt_v):
        raise ValueError('Initial state differs from reconstruction using the authenticated rest field')
    transport = transport_diagnostics(ni,vi,grid,case['beta'],case['axis'])
    initial_faces = face_diagnostics(ni,vi,grid,config['shell_width'])
    initial_reference = translated_reference(rest,rg.spacing[0],grid,case['beta'],case['axis'],0.)
    initial_reference_error = float(np.linalg.norm(ni-initial_reference)/max(np.linalg.norm(initial_reference-NORTH),1e-30))
    del ni,vi,rebuilt_n,rebuilt_v,initial_reference
    n,v,_ = load_state(source,case,manifests,'final')
    with zipfile.ZipFile(Path(source)/'evidence.zip') as z:
        history=json.loads(z.read(f'cases/{case["id"]}/history-combined.json'))
    measured = evaluate(history,n,v,grid,rest,rg.spacing[0],case['beta'],case['axis'],case['q'],config['shell_width'],plan['limits'])
    old=case['assessment'];checks={}
    for key in ('translated_static_field_relative_l2','speed_absolute_error','max_energy_relative_drift','max_momentum_drift_over_initial_energy'):
        checks[key]=bool(np.isclose(measured[key],old[key],rtol=config['replay_rtol'],atol=config['replay_atol']))
    for key in ('continuum_energy','radius_99','boundary_shell_energy_fraction','hopf_integral','minimum_corner_cone'):
        checks[key]=bool(np.isclose(measured['final'][key],old['final'][key],rtol=config['replay_rtol'],atol=config['replay_atol']))
    result={'recorded_at':timestamp(),'case_id':case['id'],'seed_id':case['seed_id'],
            'beta':case['beta'],'axis':case['axis'],'dt':case['physical']['dt'],
            'initial_state_reconstructed_bit_exact':True,'initial_reference_field_relative_l2':initial_reference_error,
            'initial_transport':transport,'initial_faces':initial_faces,
            'final_faces':face_diagnostics(n,v,grid,config['shell_width']),
            'recomputed_endpoint':measured,'original_case_checks':old['checks'],
            'replay_matches':checks,'all_replays_match':all(checks.values()),'scope':SCOPE}
    return result


def pair_audit(source, pair, campaign, manifests, config):
    a=campaign['cases'][pair['a']];b=campaign['cases'][pair['b']]
    na,va,ga=load_state(source,a,manifests,'final');nb,vb,gb=load_state(source,b,manifests,'final')
    result={'recorded_at':timestamp(),'a':pair['a'],'b':pair['b'],'kind':pair['kind'],'samples':[]}
    if pair['kind']=='temporal':
        if ga!=gb:raise ValueError('Temporal final grids differ')
        result['full_grid_difference']=field_difference(na,va,nb,vb)
        with zipfile.ZipFile(Path(source)/'evidence.zip') as z:
            ha=json.loads(z.read(f'cases/{a["id"]}/history-combined.json'));hb=json.loads(z.read(f'cases/{b["id"]}/history-combined.json'))
        result['centroid']=common_time_fit(ha,hb)
    # Common central cube: same physical region, explicit sampling refinement.
    half=min(*ga.lengths,*gb.lengths)/2-config['shell_width']
    if half<=0:raise ValueError('No common central comparison region')
    for size in config['comparison_grids']:
        axis=np.linspace(-half,half,size);points=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1)
        xa=sample_uniform(na,ga,points);ya=sample_uniform(va,ga,points)
        xb=sample_uniform(nb,gb,points);yb=sample_uniform(vb,gb,points)
        result['samples'].append({'sampling_nodes':size,'cube_side':2*half,'spacing':2*half/(size-1),
                                  **field_difference(xa,ya,xb,yb)})
    result['scope']='Raw componentwise linear interpolation on common central cubes; no field renormalization. Sampling refinement does not refine the scientific calculation or test exterior tails.'
    return result


def write_summary(out, ledger):
    cases=list(ledger['cases'].values());mismatches=sum(not r['all_replays_match'] for r in cases)
    written=timestamp()
    lines=['# Full-field low-Q motion diagnostics','',
           f"UTC: {written['utc']}; Melbourne: {written['melbourne']}.",'',
           f"Status: **{ledger['status']}**. Rest audits {len(ledger['seeds'])}/{ledger['expected']['seeds']}; "
           f"case audits {len(cases)}/{ledger['expected']['cases']}; pair audits {len(ledger['pairs'])}/{ledger['expected']['pairs']}.",
           f'Endpoint replay mismatches: {mismatches}. Original failed case checks are retained.','',
           '| Case | Initial transport-rate mismatch | Tangent acceleration mismatch RMS | Shape error | Endpoint replay |',
           '|---|---:|---:|---:|---|']
    for r in cases:
        lines.append(f"|{r['case_id']}|{r['initial_transport']['rate_relative_l2']}|{r['initial_transport']['tangent_acceleration_difference_rms']:.6g}|{r['recomputed_endpoint']['translated_static_field_relative_l2']:.6g}|{r['all_replays_match']}|")
    lines+=['',SCOPE,'No automated promotion to higher-Q motion or quantum/charged acceptance.','']
    (out/'SUMMARY.md').write_text('\n'.join(lines))
    columns=['recorded_utc','recorded_melbourne','case_id','beta','axis','dt','initial_rate_mismatch','initial_acceleration_mismatch_rms','shape_relative_l2','all_replays_match']
    with (out/'case-metrics.csv').open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n');w.writeheader()
        for r in cases:w.writerow({'recorded_utc':r['recorded_at']['utc'],'recorded_melbourne':r['recorded_at']['melbourne'],
          'case_id':r['case_id'],'beta':r['beta'],'axis':r['axis'],'dt':r['dt'],
          'initial_rate_mismatch':r['initial_transport']['rate_relative_l2'],
          'initial_acceleration_mismatch_rms':r['initial_transport']['tangent_acceleration_difference_rms'],
          'shape_relative_l2':r['recomputed_endpoint']['translated_static_field_relative_l2'],
          'all_replays_match':r['all_replays_match']})


def evidence(out):
    transient={'evidence-hashes.json','exit.json','launch.json','stop-request.json'}
    files=sorted(p for p in out.rglob('*') if p.is_file() and p.suffix in ('.json','.md','.csv') and p.name not in transient)
    atomic_json(out/'evidence-hashes.json',{'recorded_at':timestamp(),'sha256':{str(p.relative_to(out)):sha(p) for p in files}})
    with zipfile.ZipFile(out/'evidence.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in files+[out/'evidence-hashes.json']:z.write(p,str(p.relative_to(out)))


def audit(source, out, config):
    source=Path(source).expanduser().resolve();out=Path(out).expanduser().resolve()
    if out==source or out.is_relative_to(source):raise ValueError('Diagnostic output must be outside the source campaign')
    out.mkdir(parents=True,exist_ok=True)
    lock=(out/'.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('Diagnostic output is already in use')
    inv=inventory(source,config)
    if not inv['ready']:
        atomic_json(out/'inventory-not-ready.json',inv)
        raise ValueError('Missing or changed full fields; see inventory-not-ready.json. No reconstruction or solve was started.')
    c,plan,pairs,selected,manifests=compact(source,config)
    selected_pairs=[p for p in pairs if p['a'] in selected and p['b'] in selected]
    files={name:sha(Path(__file__).with_name(name)) for name in SOURCES}
    identity={'config_sha256':canonical_sha(config),'input_fingerprint':inv['input_fingerprint'],'source_sha256':files}
    path=out/'diagnostic.json'
    if path.exists():
        ledger=json.loads(path.read_text())
        if any(ledger[k]!=v for k,v in identity.items()):raise ValueError('Diagnostic config/source/inputs changed; use a new output')
    else:
        ledger={'started_at':timestamp(),**identity,'source_campaign':str(source),'seeds':{},'cases':{},'pairs':{},
                'expected':{'seeds':len(inv['selected_seeds']),'cases':len(selected),'pairs':len(selected_pairs)}}
        try:
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
        except (OSError,subprocess.CalledProcessError):commit=None;dirty=None
        atomic_json(out/'manifest.json',{'recorded_at':timestamp(),'model':MODEL,'scheme':SCHEME,'git_commit':commit,
          'git_worktree_dirty':dirty,'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
          'platform':platform.platform(),'config':config,**identity,'scope':SCOPE})
    atomic_json(out/'inventory.json',inv)
    atomic_json(out/'config.json',config)
    def checkpoint():
        ledger['updated_at']=timestamp();atomic_json(path,ledger);write_summary(out,ledger)
    def requested_stop():
        if (out/'stop-request.json').exists():raise KeyboardInterrupt
    ledger['status']='working';ledger.pop('error',None);checkpoint()
    try:
        for sid in inv['selected_seeds']:
            requested_stop()
            if sid in ledger['seeds']:continue
            event('START rest audit',seed_id=sid)
            row=seed_audit(source,sid,c,config);atomic_json(out/'seeds'/f'{sid}.json',row);ledger['seeds'][sid]=row;checkpoint()
            event('FINISHED rest audit',seed_id=sid)
        for name in selected:
            requested_stop()
            if name in ledger['cases']:continue
            event('START case audit',case_id=name)
            row=case_audit(source,c['cases'][name],c,plan,manifests,config)
            atomic_json(out/'cases'/f'{name}.json',row);ledger['cases'][name]=row;checkpoint()
            event('FINISHED case audit',case_id=name,replay_matches=row['all_replays_match'])
        for p in selected_pairs:
            requested_stop()
            key=p['a']+'__'+p['b']
            if key in ledger['pairs']:continue
            event('START field comparison',kind=p['kind'],a=p['a'],b=p['b'])
            row=pair_audit(source,p,c,manifests,config);atomic_json(out/'pairs'/f'{key}.json',row)
            ledger['pairs'][key]=row;checkpoint()
        ledger['status']='complete_pending_review'
    except KeyboardInterrupt:
        ledger['status']='stopped_checkpoint_retained'
    except Exception as error:
        ledger['status']='error';ledger['error']=str(error);checkpoint();evidence(out);raise
    checkpoint();evidence(out);event('SUMMARY',status=ledger['status'],output=str(out))
    return ledger


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--config',type=Path,default=CONFIG);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--preflight',action='store_true');a=p.parse_args();config=json.loads(a.config.read_text())
    if a.preflight:
        result=inventory(a.source,config);atomic_json(a.output,result)
        print(json.dumps({'recorded_at':timestamp(),'ready':result['ready'],'files':len(result['files']),
                          'missing_or_changed':result['missing_or_changed'],'inventory':str(a.output)},indent=2))
        return 0 if result['ready'] else 2
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
    started=time.monotonic();result=audit(a.source,a.output,config)
    atomic_json(a.output/'exit.json',{'recorded_at':timestamp(),'status':result['status'],
                                    'wall_seconds':time.monotonic()-started,'scope':SCOPE})
    return 0 if result['status']=='complete_pending_review' else 2


if __name__=='__main__':raise SystemExit(main())
