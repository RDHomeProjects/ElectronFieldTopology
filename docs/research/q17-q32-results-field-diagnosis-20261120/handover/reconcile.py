"""Compare named claims without equating different fields or operators."""
import json
from pathlib import Path
import subprocess
import numpy as np
from common import ROOT, load, save, sha, stamp
from integrity import baseline

def collect_prior_records(repo, out):
    commit = load(ROOT / 'SOURCES.json')['checkout_commit']
    command = ['git', '-C', str(repo), 'ls-tree', '-r', '--name-only', commit]
    paths = subprocess.check_output(command, text=True).splitlines()
    leaves = {'ASSESSMENT.md', 'RESULTS.json', 'Q2-Q16-CLOSURE.json', 'HIGH-Q-ASSESSMENT.json', 'STATIC-ENDPOINTS.csv', 'ENDPOINTS.json'}
    selected = [p for p in paths if (p.startswith('reports/s5-b/015-') or p.startswith('reports/s5-b/016-')) and Path(p).name in leaves]
    copied = []
    for name in selected:
        data = subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':' + name])
        collected = name + '.txt' if name.endswith('.md') else name
        target = out / 'prior-records' / collected
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        copied.append({'path': name, 'collected_path': 'prior-records/' + collected, 'sha256': sha(target), 'source_commit': commit, 'git_object': commit + ':' + name,
                       'format_note': 'Markdown bytes preserved as plain text; original relative links refer to the pinned Git tree, not a reconstructed document website'})
    result = {'recorded_at': stamp(), 'source_commit': commit, 'documents': copied,
              'scope': 'Byte-exact pinned Git documents collected locally; collection alone is not a new semantic verification of every earlier assertion',
              'missing_study_prefixes': [prefix for prefix in ['reports/s5-b/015-', 'reports/s5-b/016-'] if not any(p.startswith(prefix) for p in selected)]}
    save(out / 'PRIOR-RECORDS.json', result)
    return result

def history_analysis():
    from scipy.stats import spearmanr
    objects, _, _ = baseline()
    rows = []
    for seed in ['q21-axial-7-3', 'q22-cable-source-family']:
        history = objects['continuation/' + seed + '/history.json']
        decisions = objects['continuation/' + seed + '/decisions.json']
        epoch = decisions[-1]['fit_epoch_start']
        recent = [h for h in history if h['iteration'] >= epoch][-32:]
        correlations = {}
        for first, second in [('optimizer_alpha', 'relative_force_l2'), ('optimizer_alpha', 'acceleration_max'), ('relative_force_l2', 'acceleration_max')]:
            x = np.log10([max(h[first], 1e-300) for h in recent])
            y = np.log10([max(h[second], 1e-300) for h in recent])
            varied = np.ptp(x) > 0 and np.ptp(y) > 0
            correlations[first + '__' + second] = {'log_pearson': float(np.corrcoef(x, y)[0, 1]) if varied else None,
                                                  'spearman': float(spearmanr(x, y).statistic) if varied else None}
        rows.append({'seed': seed, 'window_iterations': [h['iteration'] for h in recent], 'epoch_start': epoch,
                     'alpha_min': min(h['optimizer_alpha'] for h in recent), 'alpha_max': max(h['optimizer_alpha'] for h in recent),
                     'correlations': correlations, 'last_three_policy_decisions': decisions[-3:],
                     'scope': 'Dependent, line-search-selected observations; descriptive association, not causal evidence or independent statistical trials'})
    return rows

def reconcile(cases):
    context = load(ROOT / 'PRIOR-CONTEXT.json')
    q2 = cases.get('q2-control')
    native = context['native_operator_comparison']
    source = baseline()[0]['record.json']
    q22 = next(r for r in source['branches'] if r['q'] == 22)
    claims = [
        {'comparison': 'Earlier Q2 stationary admission versus current high-Q failures',
         'status': 'positive_control_reproduced' if q2 and q2.get('metric_replay_passed') and q2.get('strict_stationary') and q2.get('boundary_admitted') else 'control_replay_pending_or_failed',
         'reason': 'Q2 and Q17–Q32 are different sectors and retained configurations. The earlier positive Q2 result is preserved; it is not disproved by failures of these high-Q seeds.',
         'q2_source_sha256': context['q2']['sha256'], 'earlier_q2_metrics': context['q2']['metrics']},
        {'comparison': 'Earlier small cell-energy residual versus D4 stationarity', 'status': 'different_operator_and_metric_verified_by_prior_same_field_record',
         'reason': 'A recorded same-field Q17 comparison already showed a small historical cell residual alongside failed D4 stationarity. The residual definitions are not numerically interchangeable.',
         'same_field_sha256': native['source_sha256'], 'cell_energy': native['cell_energy'], 'cell_tangent_gradient_component_rms': native['cell_tangent_gradient_component_rms'],
         'd4_energy': native['d4_metrics']['energy'], 'd4_force_ratio': native['d4_metrics']['relative_force_l2'], 'd4_acceleration_max': native['d4_metrics']['acceleration_max'],
         'scope': 'Authenticated prior comparison, not a new replay of the native Q17 full field in this diagnosis'},
        {'comparison': 'Earlier Q22 benchmark versus current Q22 cable endpoint', 'status': 'different_checkpoint_geometry_and_metric',
         'historical_field_sha256': context['anchors']['Q22']['sha256'], 'current_field_sha256': q22['checkpoint_sha256'],
         'historical_nodes': context['anchors']['Q22']['nodes'], 'historical_length': context['anchors']['Q22']['length'],
         'current_nodes': q22['nodes'], 'current_length': q22['length'],
         'reason': 'Equal Q labels do not identify the same configuration. The historical 129-grid/15.36-box native checkpoint is not the current 161-grid/23.04-box cable-family checkpoint; current force is a normalized D4 ratio.'},
        {'comparison': 'Energy improvement versus force/acceleration admission', 'status': 'different_observables',
         'reason': 'The measured energy decreases while residuals oscillate or rebound. Energy descent is preserved as a finding but does not imply either stationarity gate passes.'},
        {'comparison': '500-attempt ceiling versus stopping below 300', 'status': 'ceiling_not_fixed_execution_length',
         'additional_attempts': 225, 'unused_additional_attempts': 1513, 'reason': 'All six reached the corrected registered joint-progress stopping condition. No production observations were obtained in the 300–500 range.'},
        {'comparison': 'Boundary fractions versus D4 total static action', 'status': 'density_definitions_distinguished_without_changing_gates',
         'reason': 'Registered tail/guard fractions use continuum energy_density; the D4 total action uses hamiltonian_density with its sigma correction. Both densities are reported on identical fields. A diagnostic density comparison does not replace the registered gates.'}
    ]
    comparisons = []
    for seed in ['q21-axial-7-3', 'q22-cable-source-family']:
        parent, endpoint = cases.get(seed + '-parent'), cases.get(seed + '-endpoint')
        if not parent or not endpoint:
            continue
        first, last = parent['force_decomposition'], endpoint['force_decomposition']
        numerator_factor = last['projected_force_numerator_l2'] / first['projected_force_numerator_l2']
        denominator_factor = last['registered_sigma_denominator_l2'] / first['registered_sigma_denominator_l2']
        comparisons.append({'seed': seed, 'numerator_factor_endpoint_over_parent': numerator_factor,
                            'denominator_factor_endpoint_over_parent': denominator_factor, 'force_ratio_factor_reconstructed': numerator_factor / denominator_factor,
                            'endpoint_acceleration_peak_in_guard': endpoint['acceleration_peaks'][0]['in_registered_guard'],
                            'endpoint_guard_force_squared_fraction': endpoint['regions']['registered_guard']['force_squared_fraction'],
                            'scope': 'Exact normalization decomposition and measured localization; these do not alone prove boundary causation'})
    return {'recorded_at': stamp(), 'claims': claims, 'parent_endpoint_comparisons': comparisons,
            'unresolved': 'No exact prior assertion was specified by the user. The named documented comparisons are assessed here; unlisted earlier assertions remain unassessed until their field, operator, metric, gate and provenance are identified.',
            'genuine_contradiction_test': 'A disagreement is unexplained only after matching the exact field bytes, operator/source, grid/box, boundary prescription, metric definition, threshold and measurement stage. A failed same-field Q2 replay is a blocking discrepancy, not something to explain away.'}
