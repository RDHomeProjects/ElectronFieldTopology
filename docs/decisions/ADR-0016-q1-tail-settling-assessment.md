# ADR-0016: Q1 tail correction, endpoint qualification and motion convergence

UTC: 2026-11-06T13:05:24.404933+00:00; Australia/Melbourne: 2026-11-07T00:05:24.404933+11:00.

Status: assessment recorded; scientific motion/domain gates remain open. Supplements ADR-0015, without changing prior evidence or thresholds.

[The S5-B-009 assessment](../../reports/s5-b/009-q1-tail-settling/assessments/20261106t130524z-7c67deae/ASSESSMENT.md) independently verifies all 52 release files and twelve NPZ checkpoints/eight unique states. L20.16 remains at 0.120638% tail despite deeper force reduction; L22.08 reaches 0.081394% and passes tight final force checks. Both native statuses remain stationarity_unresolved because of Armijo stalls and the predeclared regular-observation certificate. Residual field differences are1.66% in the common core and 4.86% over the original source footprint. No domain-independent motion or electron claim.

Keep endpoint stationarity, tail trend, prescribed observation-window qualification, optimizer termination and physical acceptance distinct. Future controller/reporting changes need small independent controls and a new version; do not retroactively relabel this run or relax original gates. Partial stalled passes count in the current stagnation counter and are not three full200-iteration windows.

Finish the existing archive catalog and append the assessment to PR60; preserve all prior files. Return to S5-B-006 with a small controller/reporting audit, then T=1 cubic Q1/x and Q2/z temporal sentinels at dt=.01/.005/.0025 and fixed common analysis regions. Preserve small-box failures and raw/baseline observables. New larger-domain motion may use the bounded L22.08 Q1/established Q2 rest references only after its own initialization and tail checks. No repeated overnight stationary descent or broad catalogue is warranted by this evidence alone. Mesh/domain/time, isolation, higher-Q, Q18/additional-Q and quantum/probe work remain open and ordered as before.
