"""Independent mathematical and immutable retained-field controls for S5-B-005."""
import copy
import hashlib
import json
import zipfile
import numpy as np
import pytest
from electron_field_topology.sf_time import Grid
from electron_field_topology.sf_reconstruction import sample_cubic, boosted_cubic, phase_comparison
from electron_field_topology import sf_boost_study as study
from electron_field_topology import sf_boost_local as local
from electron_field_topology.sf_lowq_motion import campaign
from electron_field_topology.skyrme import NORTH


def config():return json.loads(study.CONFIG.read_text())


@pytest.mark.parametrize('axis',[0,1,2])
def test_normalized_affine_vector_and_exact_derivative_on_anisotropic_grid(axis):
    g=Grid((9,11,13),(4.,5.,6.),'fixed');p=g.points()
    matrix=np.array([[.2,.3,-.1],[.1,-.2,.2],[.02,.05,.07]])
    raw=np.einsum('...i,ai->...a',p,matrix)+[.2,.4,2.]
    points=np.array([[.23,-.31,.17],[-.42,.11,-.29]])
    value=np.einsum('...i,ai->...a',points,matrix)+[.2,.4,2.]
    norm=np.linalg.norm(value,axis=-1,keepdims=True);expected=value/norm
    jet=(matrix[:,axis]-expected*np.sum(expected*matrix[:,axis],axis=-1,keepdims=True))/norm
    n,d=sample_cubic(raw,g,points,axis,chunk=1)
    assert np.max(abs(n-expected))<1e-14 and np.max(abs(d-jet))<1e-14


def test_independent_analytic_mesh_order_node_and_boundary_controls():
    measured=study.controls(config())
    assert measured['passed'] and all(measured['checks'].values())
    assert len(measured['rows'])==18 and len(measured['orders'])==9


def test_constant_north_exterior_and_chunk_invariance_preserve_input():
    g=Grid((9,)*3,(4.,)*3,'fixed');p=g.points();field=study.analytical(p,0)[0]
    field[g.fixed_mask()]=NORTH;before=field.copy()
    points=np.array([[.1,-.2,.3],[2.1,0,0],[-2.1,0,0],[0,2.1,0],[0,0,-2.1]])
    a,da=sample_cubic(field,g,points,2,chunk=1);b,db=sample_cubic(field,g,points,2,chunk=100)
    assert np.array_equal(a,b) and np.array_equal(da,db)
    assert np.array_equal(a[1:],np.tile(NORTH,(4,1))) and not np.any(da[1:])
    assert np.array_equal(field,before)


def test_ambiguous_interpolant_zero_is_rejected():
    g=Grid((9,)*3,(4.,)*3,'fixed');field=np.zeros(g.shape+(3,));field[...,0]=1;field[5:,...,0]=-1
    with pytest.raises(ValueError,match='zero'):sample_cubic(field,g,np.array([[.25,0,0]]))


def test_subluminal_and_data_guards():
    g=Grid((9,)*3,(4.,)*3,'fixed');field=np.broadcast_to(NORTH,g.shape+(3,)).copy()
    with pytest.raises(ValueError):boosted_cubic(field,g,g,1.,0)
    with pytest.raises(ValueError):sample_cubic(field.astype('float32'),g,np.zeros((1,3)))
    with pytest.raises(ValueError):sample_cubic(field,g,np.array([[float('nan'),0,0]]))


def test_restricted_phase_fit_recovers_known_angle_without_spatial_rotation():
    g=Grid((9,)*3,(4.,)*3,'fixed');n=study.analytical(g.points(),0)[0];angle=.71
    rotated=n.copy();z=(n[...,0]+1j*n[...,1])*np.exp(1j*angle);rotated[...,0]=z.real;rotated[...,1]=z.imag
    r=phase_comparison(rotated,n)
    assert abs(r['global_internal_phase_radians']-angle)<1e-14
    assert r['raw_relative_l2']>.1 and r['phase_registered_relative_l2']<1e-14
    assert phase_comparison(np.broadcast_to(NORTH,n.shape),np.broadcast_to(NORTH,n.shape))['phase_identifiable'] is False
    reversed_field=n[::-1].copy()
    assert phase_comparison(reversed_field,n)['phase_registered_relative_l2']>.1


@pytest.fixture
def source(tmp_path):
    c=json.loads((study.ROOT/'experiments/configs/sf-motion/smoke.json').read_text())
    c['seeds']=[{'q':1,'nodes':9,'length':4.,'seed_scale':1.6,'seed_cutoff':1.6}]
    c.update(duration=.04,time_steps=[.02,.01],boundary_shell_width=.5)
    path=tmp_path/'source';campaign(c,path,{'export':{'enabled':False}})
    cfg=config();cfg.update(evidence_sha256=study.sha(path/'evidence.zip'),shell_width=.5,
                            sampling_nodes=5,expected_cases=1,expected_seeds=1)
    return path,cfg


def fingerprint(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def test_end_to_end_read_only_replay_resume_evidence_and_failed_gates(source,tmp_path):
    path,cfg=source;before=fingerprint(path);out=tmp_path/'study'
    result=study.run(path,out,cfg)
    assert result['status']=='complete_pending_review' and len(result['cases'])==1
    row=next(iter(result['cases'].values()))
    assert row['initial']['old_replay_bit_exact'] and not row['original_case_checks']['topology']
    assert row['comoving']['cube_side']>0
    assert set(row['comoving']['reference_comparisons'])=={'candidate_cubic','historical_trilinear'}
    assert fingerprint(path)==before and b'\r' not in (out/'case-metrics.csv').read_bytes()
    with zipfile.ZipFile(out/'evidence.zip') as z:
        hashes=json.loads(z.read('evidence-hashes.json'))['sha256']
        assert set(z.namelist())==set(hashes)|{'evidence-hashes.json'}
        for n,h in hashes.items():assert hashlib.sha256(z.read(n)).hexdigest()==h
    again=study.run(path,out,cfg);assert again['cases']==result['cases'] and fingerprint(path)==before
    changed=copy.deepcopy(cfg);changed['sampling_nodes']=7
    with pytest.raises(ValueError,match='changed'):study.run(path,out,changed)


def test_stop_request_saves_unit_checkpoint_and_resume(source,tmp_path):
    path,cfg=source;out=tmp_path/'study';out.mkdir();(out/'stop-request.json').write_text('{}')
    result=study.run(path,out,cfg);assert result['status']=='stopped_checkpoint_retained' and not result['cases']
    (out/'stop-request.json').unlink();assert study.run(path,out,cfg)['status']=='complete_pending_review'


def test_source_corruption_and_wrong_output_block_execution(source):
    path,cfg=source
    with pytest.raises(ValueError,match='outside'):study.run(path,path/'wrong',cfg)
    campaign_data,manifests,selected,inv=study.selected_inputs(path,cfg)
    case=campaign_data['cases'][selected[0]];initial=study.attempt_path(path,case)/'initial.npz'
    with np.load(initial,allow_pickle=False) as d:values={k:d[k].copy() for k in d.files}
    values['field'][4,4,4]=[.1,0.,np.sqrt(.99)];np.savez_compressed(initial,**values)
    with pytest.raises(ValueError,match='bit-exact'):study.case_record(path,case,campaign_data,manifests,cfg)


def test_selected_coverage_guard(source):
    path,cfg=source;cfg['expected_cases']=30
    with pytest.raises(ValueError,match='coverage'):study.selected_inputs(path,cfg)


def test_launcher_identity_mismatch_never_signals_another_process(tmp_path,monkeypatch):
    out=tmp_path/'output';out.mkdir();pointer=tmp_path/'pointer';pointer.write_text(str(out))
    (out/'launch.json').write_text(json.dumps({'pid':123,'process_identity':'old'}))
    monkeypatch.setattr(local,'POINTER',pointer);monkeypatch.setattr(local,'process_identity',lambda pid:'new')
    monkeypatch.setattr('sys.argv',['sf-boost-local','stop']);local.main()
    assert not (out/'stop-request.json').exists()
    monkeypatch.setattr(local,'process_identity',lambda pid:'old');local.main()
    assert (out/'stop-request.json').exists()
