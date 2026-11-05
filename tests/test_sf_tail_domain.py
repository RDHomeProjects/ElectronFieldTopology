"""Tail geometry, exact mapping, unchanged optimizer and honest failure labels."""
import copy
import json
import numpy as np
import pytest
from electron_field_topology import sf_tail_domain as t
from electron_field_topology.sf_time import Grid
from electron_field_topology.sf_readmission import relax
from electron_field_topology.skyrme import NORTH,rational_field

def test_declared_sizes_preserve_spacing_and_no_motion_matrix():
    c=json.loads(t.CONFIG.read_text());t.validate(c)
    assert [(d['nodes'],d['length']) for d in c['domains']]==[(101,16),(113,17.92),(127,20.16)]
    assert all(d['length']/(d['nodes']-1)==.16 for d in c['domains'])
    for key,value in [('spacing',.2),('tail_fraction_limit',.002),('common_nodes',71)]:
        changed=copy.deepcopy(c);changed[key]=value
        with pytest.raises(ValueError):t.validate(changed)

def small_field(nodes=9):
    g=Grid((nodes,)*3,(4.,)*3,'fixed');p=g.points();theta=.15*np.maximum(1-np.sum(p*p,axis=-1),0)**3
    return np.stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1),g

def test_exact_extension_retains_every_original_node_and_releases_old_fixed_layers():
    n,g=small_field();before=n.copy();b=t.exact_extension(n,13)
    assert np.array_equal(n,before) and np.array_equal(b[2:11,2:11,2:11],n)
    assert np.array_equal(b[:2],np.broadcast_to(NORTH,b[:2].shape))
    old_fixed=g.fixed_mask();new_fixed=Grid((13,)*3,(6.,)*3,'fixed').fixed_mask()[2:11,2:11,2:11]
    assert np.any(old_fixed & ~new_fixed)
    with pytest.raises(ValueError):t.exact_extension(n,12)

def test_shell_predicate_matches_independent_integer_grid_count_and_does_not_confuse_fixed_regions():
    g=Grid((9,)*3,(4.,)*3,'fixed');e=np.ones(g.shape)
    r=t.density_summary(e,g,.5,5,[1.,2.])
    count=sum(1 for i in range(9) for j in range(9) for k in range(9) if max(abs(i-4),abs(j-4),abs(k-4))>=3)
    assert r['shell_fraction']==count/9**3
    assert r['continuum_energy']==9**3*.5**3
    assert r['common_cube_energy']==5**3*.5**3
    assert r['outside_original_inner_cube_energy']==0

def test_zero_energy_is_not_reported_as_tail_gate_success():
    g=Grid((9,)*3,(4.,)*3,'fixed');r=t.density_summary(np.zeros(g.shape),g,.5,5,[1.])
    assert r['shell_fraction'] is None and r['radius_99'] is None

def test_common_region_comparison_uses_full_grid_gradients_before_cropping():
    n,g=small_field();b=t.exact_extension(n,13);gb=Grid((13,)*3,(6.,)*3,'fixed')
    r=t.compare_fields(n,g,b,gb,5)
    assert r['field_relative_l2']==0 and r['field_absolute_rms']==0
    assert r['density_relative_l1']<1e-13
    b[6,6,6]=[.1,0,np.sqrt(.99)];r=t.compare_fields(n,g,b,gb,5)
    assert r['field_relative_l2']>0 and r['density_relative_l1']>0

def test_external_iteration_zero_continuation_matches_original_optimizer(tmp_path):
    g=Grid((33,)*3,(8.,)*3,'fixed');n=rational_field(g.points(),alpha=1,beta=1,scale=1.1,cutoff=3.2);n[g.fixed_mask()]=NORTH
    c={'q':1,'nodes':33,'length':8.,'seed_scale':1.1,'seed_cutoff':3.2,'relative_force_l2':1e-3,'acceleration_max':1e-2,'charge_relative_error':.05,'iterations_per_pass':3,'checkpoint_every':2,'stagnation_relative_energy':1e-10}
    direct=tmp_path/'direct';external=tmp_path/'external'
    a=relax(c,direct,pass_limit=1);t.seed_continuation(external,n,g,1,c);b=relax(c,external,pass_limit=1)
    na,_=t.checked_field(direct,c);nb,_=t.checked_field(external,c)
    assert np.array_equal(na,nb) and a['status']==b['status']=='checkpointed'
    changed=copy.deepcopy(c);changed['length']=9.
    with pytest.raises(ValueError):t.checked_field(external,changed)

def test_unresolved_native_topology_label_is_preserved_in_external_readmission(tmp_path):
    g=Grid((9,)*3,(4.,)*3,'fixed');n=rational_field(g.points(),alpha=1,beta=1,scale=1.,cutoff=1.6);n[g.fixed_mask()]=NORTH
    c={'q':1,'nodes':9,'length':4.,'relative_force_l2':1e-4,'acceleration_max':1e-3,'charge_relative_error':.05,'iterations_per_pass':3,'checkpoint_every':2,'stagnation_relative_energy':1e-10}
    t.seed_continuation(tmp_path,n,g,1,c);r=relax(c,tmp_path)
    assert r['status']=='topology_unresolved' and (tmp_path/'latest.npz').exists()
    cfg={'shell_width':.5,'common_nodes':5,'profile_half_widths':[1.],'tail_fraction_limit':.001,'readmission':c}
    m=t.measure(n,g,1,cfg);assert not m['preparation_stationarity_pass']

def test_local_launch_retains_only_verified_handover_files_and_refuses_overwrite(tmp_path,monkeypatch):
    import hashlib
    from electron_field_topology import sf_tail_local as local
    package=tmp_path/'package';package.mkdir();(package/'README.md').write_text('fixture handover')
    def ledger():
        (package/'SHA256SUMS').write_text(hashlib.sha256((package/'README.md').read_bytes()).hexdigest()+'  README.md\n')
    ledger();monkeypatch.setenv('EFT_TAIL_HANDOVER',str(package))
    monkeypatch.setattr(local,'source_inventory',lambda *_:({'input_fingerprint':'fixture'},{}))
    monkeypatch.setattr(local,'process_identity',lambda _: {'fixture_identity':True})
    class Child:pid=987654
    monkeypatch.setattr(local.subprocess,'Popen',lambda *a,**k:Child())
    monkeypatch.setattr(local,'POINTER',tmp_path/'artifacts/CURRENT');cfg=tmp_path/'config.json';cfg.write_text('{}');out=tmp_path/'artifacts/run'
    local.launch(tmp_path/'source',cfg,out)
    assert (out/'handover/README.md').read_bytes()==(package/'README.md').read_bytes()
    (package/'README.md').write_text('changed fixture');ledger()
    with pytest.raises(ValueError,match='snapshot differs'):local.launch(tmp_path/'source',cfg,out)
    assert (out/'handover/README.md').read_text()=='fixture handover'

def test_completed_campaign_cannot_be_resumed_by_local_launcher(tmp_path,monkeypatch):
    import sys
    from electron_field_topology import sf_tail_local as local
    (tmp_path/'campaign.json').write_text(json.dumps({'status':'complete_pending_review'}))
    monkeypatch.setattr(local,'current',lambda :(tmp_path,{}));monkeypatch.setattr(local,'alive',lambda _:False)
    monkeypatch.setattr(sys,'argv',['tail-local','resume'])
    with pytest.raises(ValueError,match='immutable'):local.main()

def test_fixed_coordinate_profiles_include_identical_lattice_planes_across_domains():
    for nodes,length in [(101,16.),(113,17.92),(127,20.16)]:
        g=Grid((nodes,)*3,(length,)*3,'fixed');radius=t.fixed_coordinate_max(g)
        # abs(x)<4 contains offsets -24..24 at h=.16 in every domain.
        assert np.count_nonzero(radius<4.)==49**3
        # abs(x)<=8 contains exactly the original 101-cubed footprint.
        assert np.count_nonzero(radius<=8.)==101**3
