"""Render a timestamped assessment from verified compact records."""
import hashlib, json, shutil, zipfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'assessment-verification.json').read_text())
rows=data['cases'];seeds=data['seeds'];pairs=data['comparisons']
date=data['assessed_at'];stamp=f"UTC {date['utc']}; Australia/Melbourne {date['melbourne']}"
settings=[('n81-L16','L16, h=.20','#0072B2'),('n101-L16','L16, h=.16','#D55E00'),('n101-L20','L20, h=.20','#009E73')]
fig,axes=plt.subplots(1,2,figsize=(11.8,4.7),sharey=True)
for ax,q in zip(axes,[1,2]):
    for suffix,label,color in settings:
        for axis,style in [(0,'-'),(2,'--')]:
            yy=[100*next(r for r in rows if r['case_id']==f'q{q}-{suffix}-b{b:g}-a{axis}-dt0.01')['shape_relative_l2'] for b in [.1,.3]]
            ax.plot([.1,.3],yy,style,color=color,marker='o',label=f'{label}, {"x" if axis==0 else "z"}')
    ax.axhline(1,color='black',ls=':',label='1% case limit')
    ax.set(title=f'Q{q}: recorded translated-field error',xlabel='Initial speed beta (c=1)',xticks=[.1,.3],ylim=(0,2.05))
    ax.grid(alpha=.2)
axes[0].set_ylabel('Relative field L2 error (%)')
axes[1].legend(fontsize=8,loc='upper left',ncol=1)
fig.suptitle('Physical time t=1; dt=.01; two spatial levels do not establish an order',fontsize=11)
fig.text(.01,.01,stamp,fontsize=6.5);fig.tight_layout(rect=(0,.055,1,.94))
fig.savefig(ROOT/'motion-shape-errors.png',dpi=180);plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(11.8,4.7))
x=np.arange(2);width=.23
for i,(suffix,label,color) in enumerate(settings):
    ss=[next(s for s in seeds if s['seed_id']==f'q{q}-{suffix}') for q in [1,2]]
    axes[0].bar(x+(i-1)*width,[100*s['rest_tail_final'] for s in ss],width,color=color,label=label)
    axes[1].bar(x+(i-1)*width,[100*s['stress_frobenius_over_energy'] for s in ss],width,color=color,label=label)
axes[0].axhline(.1,color='black',ls=':',label='0.1% tail limit')
axes[0].set(title='Rest: energy in outer shell of width 2',ylabel='Fraction of in-box continuum energy (%)')
axes[1].set(title='Initial rest: integrated stress / energy',ylabel='Frobenius norm of integrated stress / E (%)')
for ax in axes:
    ax.set_xticks(x,['Q1','Q2']);ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
fig.suptitle('Larger boxes reduce tail and stress diagnostics; isolation remains unaccepted',fontsize=11)
fig.text(.01,.01,stamp,fontsize=6.5);fig.tight_layout(rect=(0,.055,1,.94))
fig.savefig(ROOT/'tail-and-stress.png',dpi=180);plt.close(fig)

def case(name):return next(r for r in rows if r['case_id']==name)
seedtable='\n'.join(f"|{s['seed_id']}|{s['energy']:.9f}|{s['relative_force_l2']:.6g}|{s['acceleration_max']:.6g}|{s['hopf_integral']:.7f}|{100*s['rest_tail_final']:.5f}%|{100*s['stress_frobenius_over_energy']:.4f}%|" for s in seeds)
q2table='\n'.join(f"|{b:g}|{'rest' if not b else ('x' if a==0 else 'z')}|{r['speed_relative_error']*100 if b else r['speed_absolute_error']:.6g}{'%' if b else ' model units'}|{r['shape_relative_l2']*100:.6f}%|{r['momentum_drift_over_E0']*100:.6f}%|{r['tail_final']*100:.6f}%|{r['failed_checks'] or 'all pass'}|" for b,a in [(0,0),(.1,0),(.1,2),(.3,0),(.3,2)] for r in [case(f'q2-n101-L20-b{b:g}-a{a}-dt0.01')])
temporal=[p for p in pairs if p['kind']=='temporal']
body=f'''# Assessment of the low-Q physical-time campaign

Assessed: {stamp}.

Disposition: **bounded Q2 low-speed case passes; global motion acceptance remains unreleased**.

## Evidence and verification

Campaign: `lowq-motion-2026-11-03T104629-568611+1100-30672`.
Started UTC {data['campaign_started_at']['utc']}; Melbourne {data['campaign_started_at']['melbourne']}.
Finished UTC {data['campaign_finished_at']['utc']}; Melbourne {data['campaign_finished_at']['melbourne']}.
Elapsed 61,165.614 seconds: 16 hours 59 minutes 25.614 seconds.

The submitted archive SHA-256 is `{data['archive_sha256']}` and matches the workstation output.
All 390 ZIP members pass CRC validation; all 389 listed SHA-256 hashes match, with no missing,
extra or duplicate members. The separately supplied summary is byte-identical to the archived one.
The hash index is not self-hashed; the external whole-archive digest covers it.

The verifier replays 960 saved scalar-history rows, 540 case-check flags and all 70 comparison
pairs (30 temporal, 20 spatial, 20 domain). Six stationary candidates and all 60 expected cases
are present, with one complete attempt each and final physical time t=1. No external forcing,
work or impulse is recorded. All runs use the neutral model, the declared D4 action/RK4 scheme,
and fixed reflecting boundaries. The rest geometry and moving-axis contracted-resolution
planning are explicit in the retained configurations.

Eight campaign numerical source files match snapshots reconstructed from the retained handoff
and the pinned GitHub base. All run manifests report clean commit
`{data['run_commits'][0]}`. This is source-content corroboration; the complete workstation Git
repository and full field checkpoints are not in the submission.

Verification is independent replay of retained scalar histories, arithmetic and decision logic.
Shape norms, Hopf quadrature, cell-cone margins, tail fractions, radii and stress integrals require
full fields for independent recalculation. For those quantities, the report authenticates the
recorded values and rechecks their threshold arithmetic; it does not claim new field analysis.

## Outcome against the declared checks

|Check|Pass|Fail|Interpretation|
|---|---:|---:|---|
|Discrete energy drift|60|0|Worst relative drift 2.02821e-8; limit 1e-3|
|Momentum change / initial discrete energy|56|4|Failures are Q2, beta=.3, x direction on the two h=.2 boxes|
|Saved unit/tangency constraints|60|0|Recorded saved-state errors satisfy 1e-10|
|Translated-static field shape|42|18|Limit 1%; all failures are at beta=.3|
|Centroid speed|60|0|Moving relative errors 0.01650% to 0.93487%; limit 1%|
|Recorded Hopf/cone diagnostics|60|0|Approximate integral and positive-cone checks, not an integer certificate|
|Outer-shell energy|10|50|Only the Q2 L20 family clears the 0.1% limit|
|Initial particle E/P comparisons|60|0|Bounded initial check; does not establish particle physics|
|Initial radius-based clearance|60|0|Smallest post-window margin 1.58594 model length units|
|All case checks together|6|54|Only Q2 L20 rest and beta=.1 along x/z, at both dt values|

Failure counts overlap: the 50 tail, 18 shape and four momentum failures are not disjoint cases.
Both rest and moving states must be considered. All 30 Q1 cases fail at least the tail check;
all 20 Q2 L16 cases also fail that check. All ten Q2 L20 cases pass the tail check, but four
beta=.3 cases fail shape and two of those also fail momentum.

## Rest admission, tails and stress

All six candidates satisfy the declared lattice stationarity, acceleration, unit, cone and
approximate Hopf limits. Their residuals are not equally small: Q1 L20 is markedly more relaxed
than Q1 L16. This changes the source-state error between comparisons and must be retained.

|Rest candidate|Discrete energy|Relative force|Max acceleration|Hopf integral|Final rest tail|Initial stress norm / E|
|---|---:|---:|---:|---:|---:|---:|
{seedtable}

At matched rest spacing h=.2, increasing L16 to L20 reduces the final rest shell fraction by
63.20% for Q1 and 78.47% for Q2. Q1 still has 0.12760% in the shell, above the 0.1% limit;
Q2 has 0.03330%, comfortably below it. The corresponding normalized stress norms fall by
20.41% and 23.90%, respectively. The discrete rest energies change by only -0.18408% and
-0.05637%. Energy agreement alone therefore remains a weak isolation diagnostic.

The shell fraction uses in-box continuum energy density, with width 2. L16 and L20 shells
start at absolute coordinate 6 and 8, respectively. It is not a measurement of escaped energy,
the unknown energy outside the box, or a direct numerical error bound. Its small changes in
the rest runs and its presence initially indicate a persistent tail; this evidence does not
identify reflected radiation as the cause of failure.

The domain comparison also changes the fresh seed cutoff from 6.4 to 8 and independently
readmits the field in each box. It is an end-to-end domain comparison, rather than a pure
boundary perturbation applied to identical central initial data. Further comparisons should
retain this distinction. Reflecting walls and nonzero tails preclude an inference of exact
boundary independence from the 99%-radius clearance calculation.

![Tail and stress comparison](tail-and-stress.png)

## Motion at low and moderate speeds

The most useful bounded reference is Q2 on L20 at beta=.1. At dt=.01, x motion has fitted
centroid speed 0.09998136673 (relative error 0.0186333%), field error 0.648089%, momentum
change / E0 0.0284659%, and final tail 0.0320163%. Z motion also passes, with speed error
0.823993% and shape error 0.487366%. Passing these cases does not close spatial/domain
convergence, longer-time behaviour or perturbation stability.

|Q2 L20 beta|Direction|Speed error|Shape error|Momentum change / E0|Final tail|Failed checks, dt=.01|
|---|---|---:|---:|---:|---:|---|
{q2table}

At beta=.3, shape errors range from about 0.82875% to 1.86575% across all geometries and
directions. Every x-directed beta=.3 family fails the 1% shape check. Q2's larger box has
shape errors of 1.53006% (x) and 1.10171% (z); its x momentum error is 0.136749%, above
the 0.1% limit. The h=.16 Q2 L16 x momentum error drops to 0.0923872%, but its shape and
tail checks still fail. A larger box alone does not remove the moderate-speed discrepancy.

All moving centroid speeds satisfy the predeclared 1% check, but z-directed errors commonly
remain near 0.7-0.94%. Motion of the energy centroid, field-shape preservation and momentum
conservation are separate observables. Agreement of the centroid alone does not imply a
rigidly transported localized solution.

![Shape error comparison](motion-shape-errors.png)

## Temporal, spatial and domain comparisons

Halving dt from .02 to .01 leaves the reported endpoint shape errors almost unchanged:
the largest absolute change in relative L2 error is 1.71109e-8. The largest paired endpoint
continuum-energy difference is 8.68747e-9 relative. Thus reducing dt alone is unlikely to
resolve the observed percent-level field discrepancy on this matrix.

There is an additional sampling issue in the original comparison: diagnostics every five
steps means speed is fitted to 11 time samples for dt=.02 and 21 for dt=.01. Fitting at
identical saved physical times reduces the maximum temporal velocity difference from
{max(p['centroid_velocity_difference'] for p in temporal):.9g} to
{max(p['matched_time_velocity_difference'] for p in temporal):.9g} model velocity units.
The maximum common-time centroid difference is
{max(p['matched_centroid_max_difference'] for p in temporal):.9g}.
Much of the original temporal speed difference therefore reflects sample weighting of a
slightly nonlinear centroid trajectory, rather than a timestep integration discrepancy.

At fixed L16, h=.20 to .16 reduces moving shape errors by 19.67-32.43% in every paired
motion family. This is useful evidence of spatial sensitivity, not a measured convergence
order. Centroid speed errors do not improve monotonically in every direction. The largest
spatial pair velocity difference is .00244680; the largest matched-rest-spacing domain pair
difference is .000399329 model velocity units. Directional interpolation/sampling, differences
in the relaxed source state, discrete Lorentz errors and finite boundaries remain hypotheses;
the compact evidence cannot isolate their respective contributions.

The same-spacing L20 moving grids preserve at least the planned contracted-axis resolution,
but their rounded node counts need not have exactly the same lab spacing as L16. A third
spatial level, matched-time diagnostics and comparisons of full fields on common coordinates
are needed for a stronger convergence statement. The existing pair file compares scalar
error magnitudes, not the L2 norm of the difference between two computed endpoint fields.

## Energy, topology and boost interpretation

The conserved numerical quantity is the discrete Hamiltonian. Continuum diagnostic energy
also varies slightly: its worst history-relative change is 2.19528e-4 (0.0219528%), much
larger than the discrete energy drift but still small. They should not be interchanged.
Saved constraints follow projection; small post-projection defects alone do not demonstrate
integration accuracy. The retained projection corrections are small but nonzero (largest
recorded nodal field correction 1.42532e-7; rate correction 6.90541e-6).

The largest endpoint change of Hopf quadrature relative to nominal Q is 1.40687e-4
(0.0140687%). All reported endpoint cell-cone margins stay positive, minimum .886786.
These are encouraging retained diagnostics. They do not establish exact topology throughout
every physical step or a complete knot identification.

Initial particle energy defects are at most .157419% and momentum defects .421381%, below
the 1% initialization limit. Finite-box stress-adjusted comparison defects reach .124768%
and .296329%, respectively. These are formal comparisons of a sampled boosted field with
rest-field integrals; they do not replace the physical-time trajectory or demonstrate
isolated Lorentz covariance. Reproducing the retained formulae is distinct from proving
them exact for these finite-box/interpolated states.

## Recommended next work

1. Preserve and publish this bounded result, including every failed check and exact source
   hashes. Mark low-Q motion as partially demonstrated, with the global gate still open.
2. Before another broad production matrix, run a focused local diagnostic on retained fields:
   common-time centroid fits; initial boosted-field residual/acceleration; reference-interpolation
   consistency at t=0; and full-field endpoint comparisons on common coordinates. Keep the
   scientific grid separate from renderer exports. None of these field diagnostics was executed
   by this compact-record review.
3. Use a third spatial level for a small subset: beta=.3 x (worst shape/momentum) and a z
   comparison, with matched-time output. For Q1 additionally test a larger box at fixed h and
   quantify rest-tail/stress and initial-state changes. Select box size by measured convergence;
   do not weaken the tail or shape limits to obtain a pass. No new run is launched here.
4. Keep Q2 L20 beta=.1 as a provisional numerical reference. Retain Q1 for the separately
   proposed spin/quantization-method benchmark once its numerical domain issues are controlled.
   A good Q2 motion control is not an electron identification or an inference about spin.
5. Defer Q17/Q19 production free flight until this motion diagnostic is understood. Keep Q18
   fresh fine-start/conditioning and additional-Q comparisons (including optional Q20/Q24) in
   the plan. The separate electromagnetic-model feasibility assessment can proceed alongside
   this numerical work.

No isolated long-time stability, perturbation spectrum, high-Q motion, electromagnetic
charge, quantum spin/statistics, detector outcome or electron-model acceptance follows from
this campaign. This review uses AI-assisted arithmetic and source inspection; independent
scientific peer review is not claimed. There is no arbitrary overall runtime cap proposed.

## Reproduction

From this assessment directory, using an environment with Python and NumPy:

```bash
python3 verify_assessment.py --archive evidence.zip --summary ORIGINAL-SUMMARY.md --output replay
```

The verifier writes a newly timestamped ledger and case/comparison CSV files under `replay`.
It does not run or import the solver. `build_report.py` additionally uses Matplotlib to render
the report and figures from the retained verification ledger. Bulk field and preview files
remain on the workstation. The supplied evidence archive is unchanged.
'''
(ROOT/'ASSESSMENT.md').write_text(body)
readme=f'''# Low-Q results assessment package

Recorded: {stamp}.

Read ASSESSMENT.md first. This records a compact-evidence review of six stationary rest
candidates and 60 completed cases, with six bounded case passes and the global motion gate open.

Contents: the unchanged submitted evidence.zip and summary; a reproducible scalar verifier;
timestamped verification ledger; case/comparison CSV tables; two scientific figures; and
eight source snapshots matched to the workstation campaign hashes. These snapshots document
source provenance; they are not a complete installable solver or a replacement checkout.

No local full-field solve, GitHub write, pull request or merge is performed by these files.
The report identifies which measurements were independently replayed and which need fields.

Replay with Python and NumPy:

```bash
python3 verify_assessment.py --archive evidence.zip --summary ORIGINAL-SUMMARY.md --output replay
```

The source evidence archive's SHA-256 is {data['archive_sha256']}.
SHA256SUMS covers every package member except itself.
'''
(ROOT/'README.md').write_text(readme)
shutil.copyfile('/workspace/scratch/a825e53302cb/upload/evidence(1).zip',ROOT/'evidence.zip')
shutil.copyfile('/workspace/scratch/a825e53302cb/upload/SUMMARY(1).md',ROOT/'ORIGINAL-SUMMARY.md')
