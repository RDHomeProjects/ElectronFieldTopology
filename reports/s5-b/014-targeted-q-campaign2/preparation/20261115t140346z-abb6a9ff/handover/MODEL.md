# Controlled Q continuation and domain/memory campaign2

This is a preparation specification. New outcomes remain pending until the local run completes and is assessed. All static D4 science gates, float64 precision, fixed-boundary treatment, source hashes and dependency locks remain unchanged.

| Work | Treatment | Maximum added accepted production steps |
|---|---|---:|
| Q8 | 121³,box23.04,exact optimizer continuation from600; first150,then two conditional50-step extensions | 250 |
| Q10 | 145³,box23.04,exact continuation from300; diagnose after its continuation stage | 150 |
| Q4 control | 121³,box23.04,exact continuation from1300 | 50 |
| Q4 trial | Same starting field; clear old_g/old_z/direction only, preserving alpha and native iteration | 50 |
| Q5 control | 121³,box23.04,from completed fine endpoint100 | 50 |
| Q5 expanded | 145³,box27.648,spacing0.192; exact aligned vacuum embedding of same parent | 50 |

Q5 resets conjugacy memory and alpha to1 in both arms so domain is the geometric comparison. The original121 samples are copied bitwise into the145 grid at index12:133 on every axis; vacuum is added outside. No interpolation or seed rescaling occurs. The old held boundary layers become interior degrees of freedom in the expanded box, an intended consequence of moving the boundary. Record initial metric changes and all gate decisions before evolution.

Q4's alpha remains exactly the parent value in both arms. Clearing three arrays is one treatment of conjugacy memory; no reset of alpha, change of restart cadence, preconditioner, action, grid, box or seed is introduced. Paired Q4/Q5 arms use the same five-step measurement schedule and a common qualified backend within each pair. The normal200-iteration restart behavior remains unchanged.

Q8 extensions require recent progress: uniformly sample the most recent and preceding50-step windows at five-step positions using log interpolation; require ≥5% improvement in median joint gate multiple and no >10% worsening of median acceleration. Initial-state improvement cannot override a recent plateau. Initial150-step allocation has no progress-based early cutoff; scientific admission failures, stationarity and solver stalls always stop early. Q10 receives its separate150-step maximum without Q8 extension gating.

Stop at measured representation failure, solver stall or strict stationarity. A stationary endpoint whose tail fails remains a boundary follow-up. No motion follows automatically. Q6 receives no new production steps until Q4 outcomes are reviewed; Q7/Q9 remain explicitly deferred. UTC and Australia/Melbourne timestamps accompany run records, qualification, observations and reports.

Local preflight checks all20 completed parent fields, the selected original Q4 checkpoint, source hashes and CPU metric replay. Disposable CPU/CUDA continuation tests qualify every actual treatment; a common CPU backend is used if paired automatic selections differ. No mid-branch backend fallback. Independent CPU/device audits remain at observations. Component timing distinguishes synchronized optimizer work, CPU stationarity/Hopf, CPU tail, CPU/device gradient audits and checkpoint compression. Timings do not automatically change gate evaluation or solver behavior.

Retain compact source archives, all new initial/latest/milestone NPZ states, their hashes and the original parent fields. An observed best iteration is not automatically a retained field. This bounded campaign is not a continuum stability proof, exact integer-topology certificate or electron acceptance.
