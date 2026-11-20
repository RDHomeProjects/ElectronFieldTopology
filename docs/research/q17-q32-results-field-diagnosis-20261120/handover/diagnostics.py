"""Spatial static diagnostics only. No optimizer, RK4 step or field projection."""
import base64
import gc
import hashlib
import html
from pathlib import Path
import struct
import zlib
import numpy as np
from common import load, need, save, stamp

def coordinates(grid):
    return [-length / 2 + np.arange(count) * spacing for length, count, spacing in zip(grid.lengths, grid.shape, grid.spacing)]

def face_distance(grid):
    axes = coordinates(grid)
    return np.maximum(0., np.minimum(np.minimum((grid.lengths[0] / 2 - np.abs(axes[0]))[:, None, None],
                                               (grid.lengths[1] / 2 - np.abs(axes[1]))[None, :, None]),
                                    (grid.lengths[2] / 2 - np.abs(axes[2]))[None, None, :]))

def ratio(a, b):
    return float(a / b) if b else None

def regional_statistics(force, acceleration, energy, hamiltonian, mask):
    return {'nodes': int(np.count_nonzero(mask)), 'volume_fraction': float(np.mean(mask)),
            'force_l2': float(np.linalg.norm(force[mask])), 'acceleration_l2': float(np.linalg.norm(acceleration[mask])),
            'force_max': float(np.max(force[mask])) if np.any(mask) else 0.,
            'acceleration_max': float(np.max(acceleration[mask])) if np.any(mask) else 0.,
            'force_squared_fraction': ratio(np.sum(force[mask] ** 2), np.sum(force ** 2)),
            'acceleration_squared_fraction': ratio(np.sum(acceleration[mask] ** 2), np.sum(acceleration ** 2)),
            'registered_energy_fraction': ratio(np.sum(energy[mask]), np.sum(energy)),
            'hamiltonian_energy_fraction_diagnostic': ratio(np.sum(hamiltonian[mask]), np.sum(hamiltonian))}

def peaks(array, grid, distance, count=10):
    count = min(count, array.size)
    ids = np.argpartition(array.ravel(), -count)[-count:]
    ids = ids[np.argsort(array.ravel()[ids])[::-1]]
    axes = coordinates(grid)
    rows = []
    for flat in ids:
        index = tuple(int(x) for x in np.unravel_index(int(flat), array.shape))
        rows.append({'index': list(index), 'coordinates': [float(axes[i][index[i]]) for i in range(3)],
                     'value': float(array[index]), 'nearest_face_distance': float(distance[index]),
                     'in_registered_tail': bool(distance[index] <= 2.), 'in_registered_guard': bool(distance[index] <= 3.)})
    return rows

def png_rgb(rgb):
    """Lossless scientific heat-map pixels, encoded with the standard library."""
    rgb = np.asarray(rgb, dtype=np.uint8)
    height, width, channels = rgb.shape
    need(channels == 3, 'RGB shape required')
    def chunk(name, data):
        return struct.pack('!I', len(data)) + name + data + struct.pack('!I', zlib.crc32(name + data) & 0xffffffff)
    raw = b''.join(b'\x00' + row.tobytes() for row in rgb)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')

def colours(values, low, high):
    log = np.log10(np.maximum(np.asarray(values), 10. ** low))
    t = np.clip((log - low) / max(high - low, 1e-30), 0, 1)
    anchors = np.array([[20, 10, 55], [60, 45, 125], [35, 130, 140], [100, 195, 90], [250, 230, 45]])
    return np.stack([np.interp(t, np.linspace(0, 1, len(anchors)), anchors[:, i]) for i in range(3)], axis=-1).astype(np.uint8)

def map_svg(path, grid, arrays, indices, title):
    keys = [('force', 'Projected force magnitude'), ('acceleration', 'Static acceleration magnitude'),
            ('energy', 'Registered continuum energy density'), ('hamiltonian', 'D4 Hamiltonian density (diagnostic)')]
    width, height = 1440, 1130
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#172033}</style>',
             '<defs><linearGradient id="magnitude"><stop offset="0" stop-color="rgb(20,10,55)"/><stop offset="25%" stop-color="rgb(60,45,125)"/><stop offset="50%" stop-color="rgb(35,130,140)"/><stop offset="75%" stop-color="rgb(100,195,90)"/><stop offset="100%" stop-color="rgb(250,230,45)"/></linearGradient></defs>',
             f'<text x="30" y="30" font-size="20">{html.escape(title)}</text>',
             '<text x="30" y="55" font-size="13">Logarithmic colours; raw model magnitudes, no pointwise force admission gate. Full-grid slice pixels; no field interpolation.</text>']
    for col, (key, label) in enumerate(keys):
        parts.append(f'<rect x="{60+col*350}" y="65" width="270" height="10" fill="url(#magnitude)"/>')
        data = arrays[key]
        maximum = max(float(np.max(data)), 1e-30)
        high = float(np.log10(maximum))
        low = high - 8
        for axis, index in enumerate(indices):
            x, y, size = 60 + col * 350, 115 + axis * 330, 270
            image = np.take(data, index, axis=axis).T[::-1]
            encoded = base64.b64encode(png_rgb(colours(image, low, high))).decode()
            parts.append(f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="data:image/png;base64,{encoded}" style="image-rendering:pixelated"/>')
            parts.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="none" stroke="#64748b"/>')
            others = [i for i in range(3) if i != axis]
            coordinate = coordinates(grid)[axis][index]
            parts.append(f'<text x="{x}" y="{y-28}" font-size="12">{html.escape(label)}</text>')
            parts.append(f'<text x="{x}" y="{y-10}" font-size="12">{"xyz"[axis]}={coordinate:.4g}; log10 colour range {low:.2f} to {high:.2f}</text>')
            parts.append(f'<text x="{x}" y="{y+size+18}" font-size="12">{"xyz"[others[0]]}: {-grid.lengths[others[0]]/2:.3g} to {grid.lengths[others[0]]/2:.3g}; {"xyz"[others[1]]} increases upward</text>')
    parts += ['<text x="30" y="1110" font-size="13">Dark pixels include vacuum/values below the displayed range. Quantitative peak and shell statistics use every grid node.</text>', '</svg>']
    Path(path).write_text('\n'.join(parts) + '\n')

def admission(metrics, q, gates):
    strict = bool(metrics['relative_force_l2'] <= gates['force_limit'] and metrics['acceleration_max'] <= gates['acceleration_limit'] and abs(abs(metrics['hopf_integral']) - q) / q <= gates['charge_relative_error'] and metrics['minimum_corner_cone'] > 0 and metrics['unit_error'] < gates['unit_limit'])
    boundary = bool(metrics['tail_fraction'] <= gates['initial_tail_limit'] and metrics['guard_fraction'] <= gates['tail_guard_limit'])
    return strict, boundary

def analyse(n, grid, spec, gates, folder):
    from electron_field_topology.sf_readmission import static_value_gradient, stationarity
    from electron_field_topology.sf_time import sigma_terms, densities, acceleration
    from electron_field_topology.skyrme import K
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    before = hashlib.sha256(memoryview(np.ascontiguousarray(n)).cast('B')).hexdigest()
    need(n.dtype == np.float64 and n.shape == grid.shape + (3,) and np.isfinite(n).all(), 'Invalid field dtype/shape/value')
    need(np.max(np.abs(n[grid.fixed_mask()] - [0., 0., 1.])) < 1e-12, 'Held layers differ; diagnosis never projects the input')
    reference = stationarity(n, grid)
    data = densities(n, np.zeros_like(n), grid)
    energy, hamiltonian = data['energy_density'], data['hamiltonian_density']
    del data
    distance = face_distance(grid)
    tail, guard = distance <= gates['shell_width'], distance <= gates['guard_width']
    reference.update(tail_fraction=float(np.sum(energy[tail]) / np.sum(energy)), guard_fraction=float(np.sum(energy[guard]) / np.sum(energy)))
    for key, expected in spec['expected'].items():
        if isinstance(expected, (int, float)) and not isinstance(expected, bool) and key in reference:
            need(np.isclose(reference[key], expected, rtol=1e-6, atol=1e-10), 'Retained metric replay differs: ' + spec['id'] + '/' + key)
    value, gradient = static_value_gradient(n, grid)
    raw_gradient_norm = float(np.linalg.norm(gradient))
    gradient -= n * np.sum(n * gradient, axis=-1, keepdims=True)
    gradient[grid.fixed_mask()] = 0
    gradient /= -2 * K * np.prod(grid.spacing)
    force = np.linalg.norm(gradient, axis=-1)
    del gradient
    sigma = sigma_terms(n, grid)[1]
    denominator = float(np.linalg.norm(sigma))
    free_denominator = float(np.linalg.norm(sigma[~grid.fixed_mask()]))
    held_denominator = float(np.linalg.norm(sigma[grid.fixed_mask()]))
    del sigma
    gc.collect()
    avector = acceleration(n, np.zeros_like(n), grid)[1]
    amag = np.linalg.norm(avector, axis=-1)
    del avector
    numerator = float(np.linalg.norm(force))
    need(np.isclose(numerator / max(denominator, 1e-30), reference['relative_force_l2'], rtol=2e-10, atol=2e-11), 'Independent force decomposition differs')
    need(np.isclose(float(np.max(amag)), reference['acceleration_max'], rtol=2e-10, atol=2e-11), 'Independent acceleration maximum differs')
    ham_energy = float(np.sum(hamiltonian) * np.prod(grid.spacing))
    need(np.isclose(ham_energy, value, rtol=2e-10, atol=2e-11), 'Hamiltonian sum and D4 static action differ')
    regions = {'held_layers': grid.fixed_mask(), 'registered_tail': tail, 'registered_guard': guard, 'interior_outside_guard': ~guard}
    stats = {name: regional_statistics(force, amag, energy, hamiltonian, mask) for name, mask in regions.items()}
    # Every cube-shell grid layer is measured; no spatial feature is skipped by a
    # sparse sampling schedule. Radius profiles add finer physical interpretation.
    layer = np.rint(distance / min(grid.spacing)).astype(np.int32)
    shell_profiles = []
    for index in range(int(np.max(layer)) + 1):
        mask = layer == index
        shell_profiles.append({'layer': index, 'nearest_face_distance': float(index * min(grid.spacing)),
                               **regional_statistics(force, amag, energy, hamiltonian, mask)})
    axes = coordinates(grid)
    radius = np.sqrt(axes[0][:, None, None]**2 + axes[1][None, :, None]**2 + axes[2][None, None, :]**2)
    radial = np.floor(radius / min(grid.spacing)).astype(np.int32)
    radial_profiles = []
    for index in range(int(np.max(radial)) + 1):
        mask = radial == index
        radial_profiles.append({'radial_bin': index, 'radius_lower': float(index * min(grid.spacing)), 'radius_upper': float((index + 1) * min(grid.spacing)),
                                **regional_statistics(force, amag, energy, hamiltonian, mask)})
    fpeaks, apeaks = peaks(force, grid, distance), peaks(amag, grid, distance)
    arrays = {'force': force, 'acceleration': amag, 'energy': energy, 'hamiltonian': hamiltonian}
    map_svg(folder / 'central-slices.svg', grid, arrays, [s // 2 for s in grid.shape], spec['id'] + ' — central planes')
    map_svg(folder / 'acceleration-peak-slices.svg', grid, arrays, apeaks[0]['index'], spec['id'] + ' — planes through maximum acceleration')
    strict, admitted = admission(reference, spec['q'], gates)
    if spec['kind'] == 'control':
        need(strict and admitted, 'Retained Q2 positive control fails its original gates')
    after = hashlib.sha256(memoryview(np.ascontiguousarray(n)).cast('B')).hexdigest()
    need(before == after, 'Diagnosis mutated the input field')
    result = {'recorded_at': stamp(), 'id': spec['id'], 'source_sha256': spec['sha256'], 'field_array_sha256_before': before, 'field_array_sha256_after': after,
              'q': spec['q'], 'shape': list(grid.shape), 'lengths': list(grid.lengths), 'spacing': list(grid.spacing), 'reference_metrics': reference,
              'metric_replay_passed': True, 'strict_stationary': strict, 'boundary_admitted': admitted,
              'force_decomposition': {'raw_energy_gradient_l2': raw_gradient_norm, 'projected_force_numerator_l2': numerator,
                                      'registered_sigma_denominator_l2': denominator, 'free_node_sigma_denominator_l2_diagnostic': free_denominator,
                                      'held_node_sigma_denominator_l2_diagnostic': held_denominator, 'registered_ratio_reconstructed': numerator / max(denominator, 1e-30)},
              'energy_definition_check': {'registered_boundary_density': 'sf_time.densities.energy_density (continuum density)',
                                          'd4_action_density': 'sf_time.densities.hamiltonian_density', 'registered_continuum_energy': float(np.sum(energy) * np.prod(grid.spacing)),
                                          'd4_static_action': float(value), 'd4_hamiltonian_energy': ham_energy,
                                          'hamiltonian_tail_fraction_diagnostic': stats['registered_tail']['hamiltonian_energy_fraction_diagnostic'],
                                          'hamiltonian_guard_fraction_diagnostic': stats['registered_guard']['hamiltonian_energy_fraction_diagnostic'],
                                          'gate_definition_changed': False},
              'regions': stats, 'force_peaks': fpeaks, 'acceleration_peaks': apeaks,
              'profile_scope': 'Every cube-shell grid layer plus radial bins of one grid spacing; metrics always use all nodes',
              'optimizer_steps': 0, 'physical_time_steps': 0, 'field_resampled': False, 'field_projected_by_diagnosis': False,
              'scope': 'Instantaneous static acceleration evaluation, not time evolution; side-by-side density definitions are diagnostic, not replacement gates'}
    save(folder / 'shell-profiles.json', shell_profiles)
    save(folder / 'radial-profiles.json', radial_profiles)
    save(folder / 'record.json', result)
    return result
