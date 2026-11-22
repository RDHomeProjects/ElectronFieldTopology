from common import stamp

def dispositions(records,curvature):
    groups={
      'slow_relaxation':['exact-cg'],
      'optimizer_dependence':['restart-cg','sobolev-sd','damped-inertial','projected-lbfgs'],
      'symmetry_breaking':['bend-m20','bend-m10','bend-p10','bend-p20'],
      'scale_balance':['scale-98','scale-102'],
      'fixed_box_resolution':['mesh-129','mesh-161'],
      'fixed_spacing_domain':['domain-pad-8','domain-pad-16'],
      'competing_initial_configuration':['fresh-torus72','fresh-torus23'],
      'negative_curvature_directions':['curvature-minus','curvature-plus']}
    found={r['arm']['id']:r for r in records};entries=[]
    for name,ids in groups.items():entries.append({'option':name,'disposition':'measured' if all(i in found for i in ids) else 'pending','arms':[{'id':i,'status':found[i]['status'],'final_gates':found[i]['final']['gates']} for i in ids if i in found]})
    entries += [
      {'option':'action_normalization_and_operator_equivalence','disposition':'measured_read_only','record':'MODEL-AUDIT.json','finding':'D4 energy is independently decomposed; same Q21 field is also measured under the native-cell functional. Residual definitions and units remain distinct.'},
      {'option':'matrix_free_constrained_curvature','disposition':'measured_tested_subspace','result':curvature,'limitation':'Not a full-space minimum eigenvalue or stability proof at an unconverged endpoint.'},
      {'option':'elastic_rod_description','disposition':'measured_geometric_diagnostics','details':'Closed south-preimage length, bending and two-resolution writhe; framed twist is independently qualified. Open/unresolved extraction stays explicit. This is not a fitted replacement action.'},
      {'option':'internal_rotation_isospin','disposition':'model_applicability_assessed','current_action':'Neutral massless SF; no potential U','finding':'The nonzero-frequency bound in Harland etal requires omega<min(1,mu). The current massless limit mu=0 has no positive interval satisfying that condition. Finite-box oscillations would not reproduce localized full-space isospinning solitons.','next_model_if_authorized':'Specify a potential, units, conserved isospin and constrained pseudoenergy; qualify its gradient and controls as a separate model study. No conclusion that all possible time-dependent massless solutions are impossible.'},
      {'option':'supercurrent_coupling','disposition':'model_applicability_assessed','finding':'The cited TCGL coupling can remove stability of a reduced FS model. This is relevant to physical model extension, not a repair for a neutral-SF optimizer. No gauge/supercurrent field is silently added.'},
      {'option':'periodic_helical_buckling','disposition':'geometry_applicability_assessed','finding':'Published R2 x S1 buckling thresholds belong to a periodic string geometry. Fixed-box symmetry-breaking is investigated here; the periodic model is not substituted.'},
      {'option':'existence_theory','disposition':'scope_assessed_abstract_only','finding':'Lin-Yang supports existence for an infinite subset in full space; it does not enumerate our charges or certify discrete endpoints. It supplies no additional numerical knob.'},
      {'option':'translation_and_motion','disposition':'conditional_on_static_boundary_and_mesh_admission','finding':'Rest/boost pairs and timestep refinement are a finite-lattice screen only. A boost is not used to disguise an unadmitted rest state.'}]
    return {'recorded_at':stamp(),'options':entries,'scope':'Every identified option has a measured branch, a conditional numerical check or an explicit model/applicability disposition. Assessed is not synonymous with experimentally resolved.'}
