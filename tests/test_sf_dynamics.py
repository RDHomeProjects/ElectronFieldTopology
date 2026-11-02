"""Independent metric, analytic wave, quadrature and provenance controls."""
import copy
import hashlib
import json
import numpy as np
import pytest
from electron_field_topology import sf_dynamics_admission as admission
from electron_field_topology.sf_dynamics import (
    lagrangian, stress_energy, currents, cell_integrals, boost_integrals,
    perturbation, sphere_step)
from electron_field_topology.sf_checkpoints import checkpoint
from electron_field_topology.skyrme import (
    K, NORTH, Energy, coordinates, numpy_cell_energy, set_boundary)


def sample(n=9, h=.5):
    xyz = coordinates(n, h)
    theta = .4*np.exp(-np.sum(xyz*xyz, axis=-1))
    phi = .2*np.sin(xyz[..., 0])*np.exp(-np.sum(xyz*xyz, axis=-1))
    u = np.stack((np.sin(theta)*np.cos(phi), np.sin(theta)*np.sin(phi), np.cos(theta)), axis=-1)
    return set_boundary(u)


def test_verified_instruments():
    result = admission.verify_instruments()
    assert result['passed'], result
    assert result['started_at']['utc'] and result['finished_at']['melbourne']


def test_arbitrary_time_jet_lorentz_and_target_rotation():
    rng = np.random.default_rng(9)
    d = rng.normal(size=(8, 3, 3)); d[..., 2] = 0
    v = rng.normal(size=(8, 3)); v[..., 2] = 0
    original = stress_energy(d, v)
    for axis in range(3):
        beta = .73; gamma = 1/np.sqrt(1-beta*beta)
        newd = d.copy(); newd[:, axis] = gamma*(d[:, axis]-beta*v)
        newv = gamma*(v-beta*d[:, axis])
        matrix = np.eye(4); matrix[0, 0] = matrix[axis+1, axis+1] = gamma
        matrix[0, axis+1] = matrix[axis+1, 0] = gamma*beta
        expected = np.einsum('im,...mn,jn->...ij', matrix, original, matrix)
        np.testing.assert_allclose(stress_energy(newd, newv), expected, atol=3e-12, rtol=2e-13)
    rotation, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    np.testing.assert_allclose(stress_energy(d@rotation, v@rotation), original, atol=3e-12)


def test_exact_great_circle_right_moving_wave():
    # n=(sin(theta),0,cos(theta)), theta=f(x-t); all derivative crosses vanish.
    theta = .31; slope = .7
    tangent = np.array([np.cos(theta), 0, -np.sin(theta)])
    d = np.zeros((3, 3)); d[0] = slope*tangent; v = -slope*tangent
    assert abs(lagrangian(d, v)) < 1e-14
    t = stress_energy(d, v)
    np.testing.assert_allclose(t[:2, :2], 2*slope*slope, atol=1e-14)
    np.testing.assert_allclose(t[2:, :], 0, atol=1e-14)


def test_vacuum_and_slab_independence(tmp_path):
    vacuum = np.broadcast_to(NORTH, (9, 9, 9, 3)).copy()
    result = cell_integrals(vacuum, .5)
    assert result['energy'] == 0
    assert result['kinetic_tangent_min'] == result['kinetic_tangent_max'] == 1
    u = sample(); a = cell_integrals(u, .5, slab=1); b = cell_integrals(u, .5, slab=4)
    np.testing.assert_allclose(a['energy_parts'], numpy_cell_energy(u, .5), rtol=2e-13)
    np.testing.assert_allclose(a['integrated_stress'], b['integrated_stress'], atol=2e-15)
    e = Energy(9, .5, tmp_path)
    parts, _ = e.evaluate(u)
    np.testing.assert_allclose(parts, a['energy_parts'], rtol=2e-13)
    assert a['kinetic_tangent_min'] >= 1-1e-14
    assert a['max_local_kinetic_condition'] >= 1


def test_nonstationary_stress_is_not_hidden_as_particle_boost():
    # A static scalar-gradient jet has E=a^2, Sxx=a^2, Syy=Szz=-a^2.
    energy = 2.; stress = np.diag([2., -2., -2.])
    rows = boost_integrals(energy, stress, [.5])
    assert rows[0]['energy_particle_relative_defect'] == pytest.approx(.25)
    assert rows[1]['energy_particle_relative_defect'] == pytest.approx(-.25)
    with pytest.raises(ValueError): boost_integrals(energy, stress, [1.])


def test_sphere_variations_are_tangent_and_preserve_faces():
    u = sample()
    for mode in range(4):
        w = perturbation(u, .5, mode)
        assert np.max(abs(np.sum(u*w, axis=-1))) < 1e-14
        trial = sphere_step(u, w, .002)
        assert np.max(abs(np.linalg.norm(trial, axis=-1)-1)) < 1e-14
        assert np.array_equal(trial[:2], u[:2])
        assert np.array_equal(trial[:, :2], u[:, :2])
        assert np.array_equal(trial[:, :, :2], u[:, :, :2])


def test_missing_fields_are_accounted_for_without_fabrication(tmp_path):
    # General scientific outcomes are data, independent of numerical instrument success.
    config = json.loads(admission.CONFIG.read_text())
    assert config['overall_wall_seconds'] is None
    assert len(admission.published(config)) == 31
    inventory = admission.inventory(tmp_path, config)
    assert len(inventory['fields']) == 31
    assert all(row['status'] == 'missing' for row in inventory['fields'])


def test_partial_collection_and_negative_scientific_result_preserved(tmp_path):
    out = tmp_path
    manifest = {'fields': [{'stage': 'done', 'expected_sha256': 'fixture', 'status': 'verified'},
                           {'stage': 'missing', 'expected_sha256': 'absent', 'status': 'missing'}]}
    (out/'manifest.json').write_text(json.dumps(manifest))
    (out/'instruments.json').write_text(json.dumps({'recorded_at': admission.timestamp(), 'passed': True}))
    case = out/'cases/done'; case.mkdir(parents=True)
    result = {'recorded_at': admission.timestamp(), 'manifest_sha256': admission.sha(out/'manifest.json'),
              'field_sha256': 'fixture', 'stage': 'done', 'numerical_checks_passed': True,
              'integrals': {'energy': 1., 'stress_frobenius_over_energy': .2, 'max_local_kinetic_condition': 2.},
              'curvature_probes': [{'variations': [{'second_variation': -1.}]}]}
    (case/'result.json').write_text(json.dumps(result))
    summary = admission.collect(out)
    assert summary['status'] == 'partial_or_failed'
    assert summary['completed_endpoints'] == 1
    assert summary['stages'][0]['curvature_probes'][0]['variations'][0]['second_variation'] == -1
    assert (out/'evidence.zip').is_file()
    assert json.loads((out/'RUN_COMPLETE.json').read_text())['status'] == 'partial_or_failed'
    result['field_sha256'] = 'wrong'; (case/'result.json').write_text(json.dumps(result))
    with pytest.raises(ValueError, match='provenance'): admission.collect(out)


def test_field_authentication_and_no_silent_normalization(tmp_path):
    u = sample(); path = tmp_path/'field.npz'
    checkpoint(path, u, .5, 1, 0, 0, 'fixture-config')
    reference = float(sum(numpy_cell_energy(u, .5)))
    expected = {'checkpoint_sha256': admission.sha(path), 'q': 1, 'n': 9, 'h': .5,
                'stage': 'fixture', 'config_sha256': 'fixture-config', 'final': {'energy': reference}}
    config = {'curvature_stages': ['fixture'], 'curvature_epsilons': [.002, .001, .0005],
              'slab_cells': 2, 'speeds': [0., .5, .9]}
    result = admission.audit_field(path, expected, config, tmp_path/'build')
    assert result['numerical_checks_passed']
    assert len(result['curvature_probes']) == 4
    assert len(result['boosts']) == 9
    assert result['admission'].endswith('physical_time_solver_pending')
    bad = dict(expected, checkpoint_sha256='0'*64)
    with pytest.raises(ValueError, match='SHA-256'): admission.audit_field(path, bad, config, tmp_path)
    bad = dict(expected, config_sha256='wrong')
    with pytest.raises(ValueError, match='metadata'): admission.audit_field(path, bad, config, tmp_path)
    u[3, 3, 3] *= 1.001
    with pytest.raises(ValueError, match='Unit nodal'): cell_integrals(u, .5)


def test_opposite_corner_and_wrong_published_record_are_rejected(tmp_path):
    u = sample(); u[3:5, 3:5, 3:5] = -NORTH
    with pytest.raises(ValueError, match='interpolation|hemisphere'):
        cell_integrals(u, .5)
    config = copy.deepcopy(json.loads(admission.CONFIG.read_text()))
    config['record_hashes']['summary.json'] = '0'*64
    with pytest.raises(ValueError, match='record changed'): admission.published(config)


def test_vacuum_quadratic_variation_matches_wave_energy(tmp_path):
    # On the constant vacuum the quartic term is fourth order in amplitude.
    u = np.broadcast_to(NORTH, (9, 9, 9, 3)).copy(); w = perturbation(u, .5, 0)
    engine = Energy(9, .5, tmp_path)
    values = []
    for eps in (.01, .005, .0025):
        parts, _ = engine.evaluate(sphere_step(u, w, eps)); values.append(parts[0]/eps**2)
    assert abs(values[1]-values[2]) < abs(values[0]-values[1])/3.9
    assert values[-1] > 0
