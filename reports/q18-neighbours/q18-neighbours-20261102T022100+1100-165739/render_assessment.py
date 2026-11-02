"""Plot actual retained assessment samples; no fitted convergence claims. Apache-2.0."""
from io import BytesIO
import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
data=json.loads((HERE/'assessment-verification-20261102.json').read_text())
rows=data['stages'];stamp=data['assessment_finished_at']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colors=['#176b9c','#d47713','#24884c','#8555a5']
branches=[('q18-baseline','Baseline'),('q18-scale35','Scale 3.5'),('q18-scale45','Scale 4.5'),('q18-ell025','Optimizer length .25')]

# Assert the semantic interpretation from the complete machine ledger.
for name,row in data['topology']['stages'].items():
    for target,t in row['final'].items():
        if name.startswith('q18'):
            assert t['component_classes']==['unknot']*3
            assert sorted(abs(p['signed_diagram_link']) for p in t['pairs'])==[1,2,2]
        elif name.startswith(('q17','q19')):assert t['component_classes']==['K72_finite_diagram']
        else:assert t['component_classes']==['cable_polynomial_compatible']

fig,axes=plt.subplots(3,1,figsize=(8.8,10.5))
for ax,q in zip(axes,(17,18,19)):
    current=branches if q==18 else [(f'q{q}-neighbour',f'Q{q} neighbour')]
    for i,(branch,label) in enumerate(current):
        samples=[rows[branch+f'-{n}'] for n in (193,161,129)]
        x=[r['h'] for r in samples];y=[r['energy'] for r in samples]
        ax.plot(x,y,'o-',color=colors[i],label=label,linewidth=1.5,markersize=5)
        domain=rows[branch+'-domain']
        ax.scatter([domain['h']],[domain['energy']],marker='D',s=48,facecolors='none',edgecolors=colors[i],linewidths=1.5)
    reference={17:10.952,18:10.838,19:12.008}[q]
    ax.axhline(reference,color='#666666',ls='--',lw=1.1,label='Published hyperbolic state (different topology)' if q==18 else 'Published K(7,2) branch')
    ax.set_title(f'Q{q}: '+('three-component linked outcomes' if q==18 else 'K(7,2)-compatible finite diagrams'),loc='left',fontweight='bold')
    ax.set_ylabel('Dimensionless energy');ax.set_xlim(.075,.125);ax.set_xticks([.08,.096,.12]);ax.grid(alpha=.2)
    ax.legend(fontsize=8,loc='best',ncol=2 if q==18 else 1)
    ax.set_xlabel('Spacing h; connected circles: fixed side 15.36; open diamonds: side 18.432')
fig.suptitle('Measured mesh and domain comparisons',fontsize=15,fontweight='bold',y=.99)
fig.text(.5,.018,'No extrapolation or uncertainty band. Q18 source-energy agreement does not reproduce its hyperbolic topology.',ha='center',fontsize=8)
fig.text(.5,.002,stamp['utc']+' UTC | '+stamp['melbourne']+' Australia/Melbourne',ha='center',fontsize=7)
fig.tight_layout(rect=(0,.035,1,.97))
for suffix in ('png','svg'):fig.savefig(HERE/('energy-convergence.'+suffix),dpi=180)
plt.close(fig)

state=json.loads((HERE/'campaign.json').read_text())
panels=[('q18-baseline-97','initial','Q18 initial: 97 cubed, h=.16'),
        ('q18-baseline-97','final','Q18 final: 97 cubed, h=.16'),
        ('q17-neighbour-193','final','Q17 final: 193 cubed, h=.08'),
        ('q19-neighbour-193','final','Q19 final: 193 cubed, h=.08')]
fig=plt.figure(figsize=(10,8.8))
with zipfile.ZipFile(HERE/'evidence.zip') as archive:
    for index,(name,phase,title) in enumerate(panels,1):
        ax=fig.add_subplot(2,2,index,projection='3d');ax.set_proj_type('ortho')
        case=Path(state['stages'][name]['directory']).name
        member=f'analysis/{case}/{phase}-primary-curves.npz'
        with np.load(BytesIO(archive.read(member)),allow_pickle=False) as z:
            curves=[z[k] for k in sorted(z.files,key=lambda k:int(k.split('_')[-1]))]
        for i,curve in enumerate(curves):ax.plot(*curve.T,color=colors[i],lw=1.6)
        vertices=np.concatenate(curves);center=(vertices.max(0)+vertices.min(0))/2;radius=max(np.ptp(vertices,axis=0))/2*1.12
        ax.set(xlim=(center[0]-radius,center[0]+radius),ylim=(center[1]-radius,center[1]+radius),zlim=(center[2]-radius,center[2]+radius))
        ax.set_box_aspect((1,1,1));ax.view_init(elev=23,azim=38)
        ax.set_title(title+'\n'+str(len(curves))+' retained component'+('s' if len(curves)!=1 else ''),fontsize=10,fontweight='bold')
        ax.set_xlabel('x',labelpad=0);ax.set_ylabel('y',labelpad=0);ax.set_zlabel('z',labelpad=0);ax.tick_params(labelsize=7)
fig.suptitle('Retained primary-target preimages',fontsize=15,fontweight='bold',y=.99)
fig.text(.5,.028,'Finite curves, independently replayed diagrams; not the complete field or energy density. Panels use their own physical extents.',ha='center',fontsize=8)
fig.text(.5,.008,stamp['utc']+' UTC | '+stamp['melbourne']+' Australia/Melbourne',ha='center',fontsize=7)
fig.subplots_adjust(left=.02,right=.98,bottom=.065,top=.92,hspace=.17,wspace=.03)
for suffix in ('png','svg'):fig.savefig(HERE/('core-preimages.'+suffix),dpi=180)
plt.close(fig)
for path in HERE.glob('*.svg'):
    path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
print('Rendered energy-convergence and core-preimages as PNG/SVG; assessment:',stamp)
