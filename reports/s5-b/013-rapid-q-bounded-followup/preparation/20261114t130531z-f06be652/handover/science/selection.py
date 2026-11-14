"""Representation-first reuse, with every alternative and deferral retained."""
import math
from electron_field_topology.rapid_q_screen.policy import representation,stationary

def select_prior(candidates,plan):
    alternatives=[]
    for rest_id,row in candidates:
        latest=row.get('latest') or row.get('final');m=latest['stationarity'];tail=latest['tail']['fraction'];q=row['q']
        represented=representation(m,q,plan);strict=stationary(m,q,plan)
        category=0 if strict and tail<=plan['initial_tail_limit'] else 1 if strict else 2 if represented else 3
        proximity=max(m['relative_force_l2']/plan['force_limit'],m['acceleration_max']/plan['acceleration_limit'])
        alternatives.append({'rest_id':rest_id,'native_status':row['status'],'nodes':row['nodes'],'length':row['length'],'category':category,'representation_pass':represented,'strict_stationarity_pass':strict,'tail_pass':tail<=plan['initial_tail_limit'],'force':m['relative_force_l2'],'acceleration':m['acceleration_max'],'gate_proximity':proximity,'checkpoint_sha256':row['checkpoint_sha256']})
    if not alternatives:raise ValueError('No prior candidates')
    alternatives.sort(key=lambda v:(v['category'],v['gate_proximity'],v['nodes'],v['rest_id']))
    return {'primary_rest_id':alternatives[0]['rest_id'],'alternatives':alternatives,'rule':'Represented strict-and-tail, strict boundary follow-up, represented unresolved, then unresolved representation; gate proximity within bucket. All alternatives retained; no cross-mesh energy ranking.'}

def allocation_ledger(broad,priority):
    selected={v['seed']['id'] for v in priority};ledger=[]
    for row in broad:
        seed=row['seed']['id'];decision=row['classification']['decision']
        if decision=='priority_continue':allocation='allocated_priority_stage' if seed in selected else 'deferred_priority_capacity'
        elif decision in ['defer_slow','defer_resolution','refine_representation','prior_unresolved','boundary_followup']:allocation='deferred_'+decision
        else:allocation='measured_static_endpoint'
        ledger.append({'phase':'broad','seed':seed,'q':row['q'],'native_screen_decision':decision,'allocation_status':allocation,'whole_Q_rejected':False})
    for row in priority:
        ledger.append({'phase':'priority','seed':row['seed']['id'],'q':row['q'],'native_screen_decision':row['classification']['decision'],'allocation_status':'completed_static_survivor' if row['classification']['decision']=='static_survivor' else 'completed_boundary_followup' if row['classification']['decision']=='boundary_followup' else 'deferred_solver_stall' if row.get('reason') else 'budget_exhausted_unresolved','whole_Q_rejected':False})
    return ledger
