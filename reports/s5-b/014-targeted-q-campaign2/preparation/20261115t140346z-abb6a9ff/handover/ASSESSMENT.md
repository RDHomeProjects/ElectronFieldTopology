# Completed targeted Q analysis — assessment

[Browser assessment](ASSESSMENT.html) · [Machine-readable audit](ASSESSMENT.json) · [Original evidence](data/completed-evidence.zip)

All600 allocated production steps completed. No new candidate passed every static admission gate. The70 compact payload hashes and9 JSON seals passed; all518 recorded CPU/device gradient audits passed. Twenty full NPZ fields remain local and were not independently replayed by this assessment. Preserve every original source run and full field.

| Endpoint | Force / limit | Acceleration / limit | Tail / limit |
|---|---:|---:|---:|
| Q8,121³ | 0.579 | 1.203 | 0.781 |
| Q10,145³ | 5.112 | 10.294 | 0.514 |
| Q5 coarse restart,97³ | 531.764 | 874.165 | 2.272 |
| Q5 fine restart,121³ | 46.935 | 87.396 | 2.447 |

Each ratio must be ≤1, alongside unchanged representation and normalization gates. Q8 force passes; acceleration remains20.3% above its limit. Q10 improved overall but both recent residual trends worsened. Its best joint observation at208 is not a retained full checkpoint; retained200 is available. Q5 coarse restarting avoids the earlier representation loss through100; the finer grid improves residuals but does not solve tail admission. Q4/Q6 retained-state residual maps are primarily core-localized; this motivates a controlled optimizer-memory comparison, not a claim of an optimizer defect.

The prior extension rule was obeyed, but improvement from the run start could keep extending after recent progress stalled. Campaign2 removes that override. Profile measurements and checkpoint work rather than extrapolating whole-run speed from the27–38× disposable GPU step speedups. Dense adaptive sampling occurred almost every step in Q8/Q10. Retrospective curve fits do not validate a passing-time forecast.

## User-directed next campaign

Record the completed outcomes and prepare a distinct bounded campaign: Q8 first150 steps then up to two conditional50-step batches, maximum250; Q10 an additional150-step continuation before read-only diagnosis; Q4 two50-step arms from the same1300 checkpoint, clearing conjugacy memory only in the trial with alpha held equal; Q5 two50-step domains at equal spacing0.192, from the retained121³ iteration100 field with matching restarts. Q6 relaxation remains unallocated; Q7/Q9 remain deferred. Total maximum600 new production steps. All gates unchanged and no automatic motion.
