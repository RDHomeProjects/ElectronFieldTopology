"""Render the review from verified compact records; no full-field computation."""
from pathlib import Path
import json,zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
v=json.loads((ROOT/'review-verification.json').read_text())
with zipfile.ZipFile(ROOT/'diagnostic-evidence.zip') as z:d=json.loads(z.read('diagnostic.json'))
with zipfile.ZipFile(ROOT/'original-motion-evidence.zip') as z:old=json.loads(z.read('campaign.json'))
stamp=f"UTC {v['assessed_at']['utc']}; Melbourne {v['assessed_at']['melbourne']}"
settings=[('n81-L16','L16 h=.20','#0072B2'),('n101-L16','L16 h=.16','#D55E00'),('n101-L20','L20 h=.20','#009E73')]
fig,axes=plt.subplots(1,2,figsize=(11.8,4.8),sharey=True)
for ax,q in zip(axes,[1,2]):
    for suffix,label,color in settings:
        for axis,style in [(0,'-'),(2,'--')]:
            yy=[100*d['cases'][f'q{q}-{suffix}-b{b:g}-a{axis}-dt0.01']['initial_transport']['rate_relative_l2'] for b in [.1,.3]]
            ax.plot([.1,.3],yy,style,color=color,marker='o',label=f'{label}, {"x" if axis==0 else "z"}')
    ax.set(title=f'Q{q}',xlabel='Boost beta (c=1)',xticks=[.1,.3],ylim=(4.5,12));ax.grid(alpha=.2)
axes[0].set_ylabel('Initial field-rate / D4 transport mismatch (%)')
axes[1].legend(fontsize=8,loc='lower right',ncol=1)
fig.suptitle('Initial derivative consistency: finer rest mesh reduces the mismatch',fontsize=12)
fig.text(.01,.04,'This is an internal-field derivative diagnostic, not a centroid speed error or a physical acceptance threshold.',fontsize=8)
fig.text(.01,.01,stamp,fontsize=6.5);fig.tight_layout(rect=(0,.09,1,.94))
fig.savefig(ROOT/'initial-transport-mismatch.png',dpi=180);plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(11.8,4.8),sharey=True)
labels=['Rx','Ry','Rz','Phase'];x=np.arange(4)
for ax,q in zip(axes,[1,2]):
    base=np.array(d['seeds'][f'q{q}-n81-L16']['classical_metric']['metric'])
    for shift,suffix,label,color in [(-.18,'n101-L16','h .20 -> .16, L16','#D55E00'),(.18,'n101-L20','L16 -> L20, h .20','#009E73')]:
        target=np.array(d['seeds'][f'q{q}-{suffix}']['classical_metric']['metric'])
        ax.bar(x+shift,100*(np.diag(target)[3:]/np.diag(base)[3:]-1),.34,label=label,color=color)
    ax.set(title=f'Q{q}',xticks=x,xticklabels=labels,ylim=(0,9));ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
axes[0].set_ylabel('Change in classical kinetic coefficient (%)')
fig.suptitle('Inertia remains sensitive to grid and domain, despite small energy changes',fontsize=12)
fig.text(.01,.04,'Seven-mode Gram matrices are classical; near-dependent axial/phase directions require a symmetry analysis.',fontsize=8)
fig.text(.01,.01,stamp,fontsize=6.5);fig.tight_layout(rect=(0,.09,1,.94))
fig.savefig(ROOT/'inertia-sensitivity.png',dpi=180);plt.close(fig)

metrics='\n'.join(f"|{r['seed_id']}|{r['rotation_x']:.6f}|{r['rotation_y']:.6f}|{r['rotation_z']:.6f}|{r['internal_phase']:.6f}|{r['smallest_gram_eigenvalue']:.7f}|" for r in sorted(v['kinetic_metrics'],key=lambda r:r['seed_id']))
near='\n'.join(f"|{r['seed_id']}|{r['axial_combination_norm_squared']:.7f}|{r['axial_combination_normalized']*100:.5f}%|" for r in sorted(v['kinetic_metrics'],key=lambda r:r['seed_id']))
rate_table='\n'.join(f"|Q{q}|{b:g}|{'x' if a==0 else 'z'}|{100*d['cases'][f'q{q}-n81-L16-b{b:g}-a{a}-dt0.01']['initial_transport']['rate_relative_l2']:.3f}%|{100*d['cases'][f'q{q}-n101-L16-b{b:g}-a{a}-dt0.01']['initial_transport']['rate_relative_l2']:.3f}%|" for q in [1,2] for b,a in [(.1,0),(.1,2),(.3,0),(.3,2)])
body=f'''# Scientific assessment of retained full-field motion diagnostics

Assessed: {stamp}.

**Disposition: endpoint replay confirmed; initialization and domain sensitivity remain;
the global motion gate stays open.** No new physical-time solve was performed in this review.

## Integrity and scope

The two uploaded ZIPs are byte-identical, SHA-256
`{v['diagnostic_archive_sha256']}`. One dataset was reviewed. The separate summary
matches its archived copy. All 142 indexed member hashes and ZIP CRCs verify, with
143 members including the index. The linked original motion archive has SHA-256
`{v['original_archive_sha256']}`; all 389 indexed hashes verify too.

The workstation reports clean diagnostic commit `{v['diagnostic_git_commit']}`.
All 13 recorded diagnostic/numerical source hashes match the retained handoff source
snapshots. The inventory's 126 file references and fingerprint link to the six original
rest and 60 initial/final states. Sixty initial-state reconstructions are reported
bit-exact, and all 540 endpoint numeric comparisons match within the declared replay
tolerances. All six rest metrics and all 70 pair records are accounted for.

This review independently rechecks hashes, record consistency, threshold arithmetic,
equal-time scalar fits, matrix symmetry/eigenvalues and the summary statistics. The
workstation's full-field results are authenticated records; the raw scientific field
arrays remain local and were not independently recalculated in this review. Initial
checkpoint files have no older independently published file checksum: the diagnostic
records their bytes and checks their reconstructed state on the workstation. Source
content matching is not a separate retrieval of the complete unpublished Git commit.

The diagnostic finished 4 November 2026 at 11:08:40 AEDT / 00:08:40 UTC. The terminal
exit record reports 984.524 seconds (16 minutes 24.5 seconds), including authentication.
The archived ledger interval begins after initial authentication, so it is shorter.
The six original bounded case passes and overlapping failures (50 tail, 18 shape,
four momentum) are preserved. Successful replay does not turn failed physics checks
into passes or release isolated free flight, stability or electron acceptance.

## 1. Boost reconstruction is reproducible; derivative consistency is limited

Initial field comparison with the declared translated reference is at machine precision:
the largest relative L2 difference is 1.15160e-15. This verifies the implemented
construction against its own declared interpolant; it is not an independent continuum
boost solution.

The tangent field time derivative supplied by the normalized trilinear interpolant
differs from the lattice translation generator P_n[-beta D_a n] by **5.986-10.980%**.
These percentages concern internal-field time derivatives, not centroid velocity.
The best previously reported centroid error of .0186% and an initial derivative
mismatch of about 9.75% therefore refer to different observables and can coexist.

|Q|beta|Axis|h=.20, L16|h=.16, L16|
|---|---:|---|---:|---:|
{rate_table}

The mismatches decrease for every moving family when the rest mesh is refined, and
are identical between the two dt cases sharing the same initial data. A larger box
at the same nominal rest spacing leaves comparable rate mismatches. Their scale and
trend make initialization/interpolation a strong target for investigation.

This is not proof that the time integrator is defective or that interpolation explains
all shape error. The two constructions differentiate different finite-grid objects.
Normalized trilinear reconstruction is only piecewise smooth; at cell interfaces its
derivative can have a jump. In particular, exact-node evaluation uses a one-sided cell
choice in the current sampler. The D4 translation generator samples neighboring nodes.
Their differences can be substantial even when the initial sampled n fields agree.
The solver's finite-h action also lacks exact continuum boost symmetry.

The relative tangent-acceleration diagnostic ranges from about 31.7% to 101.5% in
moving cases. Its denominator is an acceleration norm, and absolute RMS values differ
greatly with beta and field. It is not a percent speed error or an instability rate.
Absolute RMS residuals do not improve monotonically under every refinement: for
example Q1 beta=.1 x increases from .002916 to .003865 as h is reduced at L16.
RMS comparisons across different box volumes additionally include dilution by the
number of sampled nodes. These residuals should diagnose patterns, not serve as
new retrospective acceptance limits.

![Initial field-rate consistency](initial-transport-mismatch.png)

## 2. Time integration is well controlled for this observation window

The largest actual full-grid endpoint field difference between dt=.02 and .01 is
3.80045e-7 relative, or **0.0000380%**. That is far below the percent-level spatial,
domain and translated-shape differences in this campaign. The maximum equal-time
centroid velocity difference is 1.10131e-8 model units, independently replayed from
the original scalar histories.

The earlier two fits used 11 versus 21 saved diagnostic times. Equal-time fitting
removes most of that sampling difference. This supports prioritizing initialization
and spatial/domain controls over another global reduction of dt for this same t=1
window. It is not a measured temporal order from three dt levels, a long-time error
bound, or a proof that every observable is temporally converged.

## 3. Cross-resolution and cross-domain fields remain different

Using the 65-cubed raw comparison samples on each pair's common central cube:

|Comparison|Q1 field L2 difference|Q2 field L2 difference|
|---|---:|---:|
|h=.20 versus .16, same L16|2.108-2.157%|1.507-1.573%|
|L16 versus L20, same rest h=.20|7.174-7.462%|3.119-3.326%|

These are comparisons between two computed fields. They differ from each trajectory's
error against its own translated static reference. They include different independently
readmitted source equilibria, seed cutoff changes and possible symmetry registration
effects. They are not a direct estimate of a single trajectory's error against the
unknown continuum solution.

The resting cases already have differences of 2.157% (Q1 spatial), 1.558% (Q2 spatial),
7.174% (Q1 domain) and 3.122% (Q2 domain). Since each rest trajectory changes very little
relative to its own initial state, much of the pair difference likely originates in
the source equilibria. This is an inference, not a measured t=0 pair decomposition.
The current pair audit compared final states; explicit common-grid initial/residual
comparisons are still needed to separate static-state and evolution contributions.

The raw vector comparisons do not register global internal phase or spatial pose.
An allowed internal-phase rotation can change n's componentwise norm without changing
energy density. Compare phase-invariant observables too, and record both unregistered
and consistently registered fields. Establish any transformation from rest states and
hold it fixed for the corresponding moving comparison. Spatial registration must
transform the boost direction consistently; it must not hide x/z dependence.

The three 33/49/65 comparison sampling grids are useful quadrature/interpolant checks,
not three physical solver meshes. Domain differences change by up to about 1.40%
relative between the last two sampling levels, and spatial differences by up to 3.79%
relative. Those changes are small relative to the main field differences but do not
justify a convergence-order claim. The central cubes exclude outer shells and cannot
validate tails or infinite-domain isolation.

## 4. Classical inertia is informative, but not ready for a quantum spectrum

The diagonal coefficients below are entries of the seven-mode finite-box kinetic
Gram matrix, with T=.5 G_AB qdot_A qdot_B, in the declared model units. They are not
quantum angular momenta or energy eigenvalues.

|Rest field|G_RxRx|G_RyRy|G_RzRz|G_phase,phase|Smallest Gram eigenvalue|
|---|---:|---:|---:|---:|---:|
{metrics}

At fixed h=.20, increasing L16 to L20 changes Q1's Rz coefficient by **7.705%** and
internal-phase inertia by **8.039%**. Q2's corresponding changes are **2.511%** and
**2.583%**. The original discrete rest energies change by only .184% and .056% in
magnitude. Static energy agreement is therefore insufficient to validate inertia.
At fixed L16, refinement changes the displayed coefficients by about 2.28-2.60% for
Q1 and 1.28-1.35% for Q2. A third physical mesh and further domain control remain needed.

![Classical inertia sensitivity](inertia-sensitivity.png)

All retained Gram eigenvalues are positive, but this is a kinetic Gram construction,
not an energy Hessian or nonlinear stability test. There are nearly dependent axial
rotation/internal-phase directions. For the combination with coefficients (1,Q) in
the (Rz, phase) subspace, define C=G_RzRz+2Q G_Rz,phase+Q^2 G_phase,phase.

|Rest field|C|C / (G_RzRz + Q^2 G_phase,phase)|
|---|---:|---:|
{near}

This pattern is consistent with the axial character of the source fields. It does
not prove an exact symmetry or null mode on a Cartesian fixed box. A naive inverse
of all seven coordinates can amplify the small eigenvalues and produce spurious
collective energies. Establish genuine symmetries, coordinate dependencies and their
continuum/domain limits before quotienting any mode or constructing a Hamiltonian.
The numerical matrix alone does not select a fermionic quantization prescription.

The supplied Krusch/Speight and Cork papers support this staged approach: configuration
topology and kinetic metrics matter, and a rigid static shape/energy comparison is
insufficient. Their separate quantization assumptions do not derive classical spin,
electric charge, detector probabilities or Stern-Gerlach outcomes here. No mass term,
electromagnetic coupling or quantum solver has been added to the neutral action.

## 5. Boundaries and recommended next decision

The original tail findings persist: Q2 L20 clears the declared shell criterion, while
Q1 L20 still fails it. Per-face fractions and endpoint fluxes are retained, but shells
overlap at edges/corners, and a pair of instantaneous flux samples cannot establish
reflected radiation history or net energy lost from the box. No measured reflection
cause is established by this diagnostic.

Recommended sequence:

1. Publish the diagnostic and this assessment, preserving the original six bounded
   passes, failed gates, exact source identities and all comparison definitions.
2. Compare the current boost reconstruction with a smoother, consistently differentiated
   reconstruction on a few retained rest fields, first without new evolution. Validate
   known analytic fields at exact nodes, shifted/off-node points and boundary extensions;
   test normalization/tangency and event-time derivatives. Keep the old initializer as
   an explicit reference variant. Do not overwrite v with a fitted D4 derivative merely
   to force the diagnostic residual to zero.
3. Add common-grid initial-state and comoving-residual comparisons, phase-invariant
   observables and documented symmetry registration. These existing-field diagnostics
   can distinguish source-state differences before a costly third-grid matrix.
4. If the initialization controls support improvement, run a small controlled beta=.3
   x/z evolution comparison, then a third physical spatial level and a larger Q1 box
   at matched h. Keep action, precision and acceptance limits fixed; validate the
   expected order of the chosen reconstruction rather than assuming it from the PDE
   stencil. A tail pass alone does not establish inertia or isolated-domain convergence.
5. Keep Q2 low-speed motion as a provisional neutral numerical reference. Q17/Q19
   motion follows adequate low-Q control; retain Q18 fresh fine-start/conditioning and
   additional-Q work, including optional Q20/Q24, after this dynamics tranche.
6. Continue the separate charged-theory feasibility assessment. The conditional Q1/Q2
   FR/quantization-method stage follows converged inertia and symmetry controls. This
   does not silently replace the stronger classical-emergence hypothesis or count an
   assumed quantum rule as derived. Experimental apparatus/detector tests remain later.

No new production matrix is launched by this assessment. The result narrows the next
numerical question without identifying an electron or rejecting every possible
topological field theory. AI-assisted analysis; independent scientific peer review
has not been performed.

## Reproduction

```bash
python3 verify_review.py --diagnostic diagnostic-evidence.zip \\
  --original original-motion-evidence.zip --summary ORIGINAL-SUMMARY.md --output replay
```

This requires NumPy. It replays compact records and matrix/scalar algebra, not full
fields. The script writes a fresh UTC/Melbourne ledger and LF CSV tables. Build this
report/figures with build_review.py after verification; that additionally uses Matplotlib.
Both source archives are unchanged. Source snapshots document the handed-off code and
are not a complete standalone solver checkout.
'''
(ROOT/'ASSESSMENT.md').write_text(body)
(ROOT/'README.md').write_text(f'''# Assessed full-field motion diagnostics

Recorded: {stamp}.

Read [the scientific assessment](ASSESSMENT.md). It records zero endpoint replay
mismatches, initial derivative and spatial/domain sensitivity, and unconverged classical
inertia. The global motion gate stays open; original failures remain unchanged.

Contents include both unchanged evidence archives, a reproducible compact-record
verifier, timestamped verification/CSV tables, source snapshots and scientific figures.
No full scientific field arrays are included, and no new trajectory is claimed.

```bash
python3 verify_review.py --diagnostic diagnostic-evidence.zip \\
  --original original-motion-evidence.zip --summary ORIGINAL-SUMMARY.md --output replay
```

The report distinguishes full-field results recorded on the workstation from the
hash, scalar, matrix and consistency checks independently repeated in this review.
''')
