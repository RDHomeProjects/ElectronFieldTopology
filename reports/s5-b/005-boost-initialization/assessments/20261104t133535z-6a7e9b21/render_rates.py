"""Render the immutable scalar assessment; no field evolution. Apache-2.0."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
metrics=json.loads((root/'verification.json').read_text())
rows=metrics['case_metrics'];fig,axes=plt.subplots(2,2,figsize=(10,7),sharey=True,layout='constrained')
seeds=[(81,16),(101,16),(101,20)]
for iq,q in enumerate([1,2]):
    for ib,beta in enumerate([.1,.3]):
        ax=axes[iq,ib]
        for axis,style,color in [(0,'-','#167d9a'),(2,'--','#bc6c25')]:
            selected=[next(r for r in rows if r['seed_id']==f'q{q}-n{n}-L{l}' and r['beta']==beta and r['axis']==axis) for n,l in seeds]
            ax.plot(range(3),[100*r['old_rate'] for r in selected],style,color='#7c8188',marker='o',label='Trilinear '+('x' if axis==0 else 'z'))
            ax.plot(range(3),[100*r['new_rate'] for r in selected],style,color=color,marker='s',label='Cubic '+('x' if axis==0 else 'z'))
        ax.set_title(f'Q{q}, beta={beta}')
        ax.set_xticks(range(3),['n81 / L16','n101 / L16','n101 / L20'])
        ax.set_ylim(0,12);ax.grid(axis='y',alpha=.25)
        if ib==0:ax.set_ylabel('Analytic-rate / D4 mismatch (%)')
axes[0,0].legend(fontsize=8,ncol=2)
fig.suptitle('S5-B-005: lower initialization mismatch, conditional candidate',fontsize=14)
fig.supxlabel('Rest mesh and domain; cubic candidates have not been evolved',fontsize=10)
stamp=metrics['verified_at']
fig.text(.5,-.025,'12 beta=.1 cubic cases need fixed-layer readmission.  UTC '+stamp['utc']+'; Melbourne '+stamp['melbourne'],ha='center',fontsize=7)
for ext in ['png','svg']:fig.savefig(root/('rate-comparison.'+ext),dpi=180,bbox_inches='tight')
svg=root/'rate-comparison.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
