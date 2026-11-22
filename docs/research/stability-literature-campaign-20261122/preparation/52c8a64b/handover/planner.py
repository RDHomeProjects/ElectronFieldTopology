"""Measured-progress gate and finite-horizon scheduling; no fitted admission."""
import math
import statistics
from common import stamp
from evaluations import fit_history

KEYS = ['relative_force_l2', 'acceleration_max']

def predict(model, x):
    result = 0.
    for coefficient in model['coefficients_highest_power_first']:
        result = result*x + coefficient
    return math.exp(max(-700., min(700., result))) if model['model'] == 'exponential' else result

def distance_events(model, gate, x):
    c = model['coefficients_highest_power_first'][:]
    events = []
    if model['model'] == 'exponential':
        if c[0] < 0:
            root = (math.log(gate)-c[1])/c[0]
            if root > x:
                events.append({'kind': 'formal_gate_crossing', 'distance': root-x})
    elif len(c) == 2:
        if c[0] < 0:
            root = (gate-c[1])/c[0]
            if root > x:
                events.append({'kind': 'formal_gate_crossing', 'distance': root-x})
    else:
        if c[0]:
            turn = -c[1]/(2*c[0])
            if turn > x:
                events.append({'kind': 'quadratic_turn', 'distance': turn-x})
        discriminant = c[1]**2-4*c[0]*(c[2]-gate)
        if c[0] and discriminant >= 0:
            for sign in [-1, 1]:
                root = (-c[1]+sign*math.sqrt(discriminant))/(2*c[0])
                if root > x:
                    events.append({'kind': 'formal_gate_crossing', 'distance': root-x})
    return events

def decide(history, charged, policy, gates, ceiling=20):
    current = history[-1]['iteration']
    result = {'recorded_at': stamp(), 'iteration': current, 'charged_attempts': charged, 'maximum_attempts': ceiling,
              'fit_admission': False, 'budget_extension': False, 'action': 'stop', 'next_attempts': 0}
    if charged >= ceiling:
        return result | {'reason': 'declared_final_tranche_budget_reached'}
    width = policy['comparison_window_points']
    if len(history) < 2*width:
        return result | {'reason': 'insufficient_distinct_observations_for_joint_progress'}
    comparisons = {}
    for key in KEYS:
        previous = statistics.median(row['metrics'][key] for row in history[-2*width:-width])
        recent = statistics.median(row['metrics'][key] for row in history[-width:])
        comparisons[key] = {'previous_median': previous, 'recent_median': recent, 'fractional_improvement': 1-recent/max(previous, 1e-30)}
    result['measured_joint_progress'] = comparisons
    if not all(row['fractional_improvement'] >= policy['minimum_recent_joint_improvement'] for row in comparisons.values()):
        return result | {'reason': 'recent_measured_joint_progress_not_persistent'}
    window = history[-policy['window_points']:]
    fitted = {key: fit_history(window, key) for key in KEYS}
    valid = {key: [model for model in fitted[key].get('models', []) if model['holdout_relative_rmse'] <= policy['holdout_relative_rmse_limit']] for key in KEYS}
    result.update(fits=fitted, valid_model_names={key: [m['model'] for m in models] for key, models in valid.items()})
    remaining = ceiling-charged
    minimum = min(policy['minimum_batch_attempts'], remaining)
    maximum = min(policy['maximum_batch_attempts'], remaining)
    # The first five attempts are a predeclared diagnostic probe supported by
    # the prior measured joint improvement, not a remote crossing prediction.
    if charged == 0:
        return result | {'action': 'continue', 'reason': 'first_declared_five_attempt_probe', 'next_attempts': minimum}
    x = current-window[0]['iteration']
    constraints, forecast_rows = [], []
    for key, models in valid.items():
        gate = gates['force_limit'] if key == 'relative_force_l2' else gates['acceleration_limit']
        for model in models:
            for event in distance_events(model, gate, x):
                fraction = policy['turn_distance_fraction'] if event['kind'] == 'quadratic_turn' else policy['gate_distance_fraction']
                constraints.append({'quantity': key, 'model': model['model'], **event, 'scheduling_distance_fraction': fraction})
    allowed = []
    for horizon in range(minimum, maximum+1):
        checks = {}
        for key, models in valid.items():
            values = [predict(m, x+horizon) for m in models]
            positive = bool(values) and all(math.isfinite(v) and v > 0 for v in values)
            disagreement = (max(values)-min(values))/max(statistics.median(values), 1e-30) if positive else None
            fractional_change = max(abs(v/history[-1]['metrics'][key]-1) for v in values) if positive else None
            checks[key] = {'predictions': values, 'positive': positive, 'relative_model_spread': disagreement, 'maximum_predicted_fractional_change': fractional_change,
                           'passes': len(models) >= policy['minimum_valid_models_per_metric'] and positive and disagreement <= policy['maximum_forecast_disagreement'] and fractional_change <= policy['maximum_forecast_fractional_change']}
        event_ok = all(horizon <= max(minimum, math.floor(c['distance']*c['scheduling_distance_fraction'])) for c in constraints)
        aligned = all(row['passes'] for row in checks.values()) and event_ok
        forecast_rows.append({'horizon': horizon, 'metrics': checks, 'turn_and_gate_distance_constraint_pass': event_ok, 'aligned': aligned})
        if aligned:
            allowed.append(horizon)
    selected = max(allowed) if allowed else minimum
    return result | {'action': 'continue', 'reason': 'validated_short_horizon_alignment' if allowed else 'measured_progress_only_minimum_probe_due_to_fit_uncertainty',
                     'next_attempts': selected, 'forecast_candidates': forecast_rows, 'scheduling_events': constraints,
                     'scope': 'Recent measured joint progress permits a bounded probe. Fit agreement, relative-change and turn/crossing distance constrain block size; none grants scientific admission.'}
