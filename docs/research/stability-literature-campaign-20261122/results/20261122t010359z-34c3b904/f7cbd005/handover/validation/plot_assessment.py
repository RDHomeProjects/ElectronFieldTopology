"""Optional high-resolution assessment plot; requires matplotlib only for rendering."""
from pathlib import Path
import json,zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
p=Path(__file__).resolve().parents[1]
with zipfile.ZipFile(p/'data/completed-evidence.zip') as z:r=json.loads(z.read('q21/exact/record.json'))
rows=[v for v in r['history'] if v['iteration']>=315];x=[v['iteration'] for v in rows]
fig,axs=plt.subplots(1,3,figsize=(15,4.7),layout='constrained')
for ax,key,limit,label in [(axs[0],'relative_force_l2',.0001,'Relative force'),(axs[1],'acceleration_max',.001,'Maximum acceleration')]:
    y=np.array([v['metrics'][key]/limit for v in rows]);ax.plot(x,y,'o-',color='#2563eb',lw=1.7,ms=4);ax.axhline(1,color='#15803d',ls='--',label='Admission limit');ax.set_ylim(bottom=0);ax.set_title(label);ax.set_xlabel('Optimizer iteration');ax.set_ylabel('Measured value / admission limit');ax.grid(alpha=.2);ax.legend(frameon=False)
for key,limit,label,color in [('tail_fraction',.00075,'Tail shell','#7c3aed'),('guard_fraction',.001,'Guard shell','#d97706')]:axs[2].plot(x,[v['metrics'][key]/limit for v in rows],label=label,lw=2,color=color)
axs[2].axhline(1,color='#15803d',ls='--',label='Admission limit');axs[2].set_ylim(bottom=0);axs[2].set_title('Boundary admission');axs[2].set_xlabel('Optimizer iteration');axs[2].set_ylabel('Measured fraction / admission limit');axs[2].grid(alpha=.2);axs[2].legend(frameon=False)
for ax in axs:ax.xaxis.set_major_locator(MultipleLocator(5))
fig.suptitle('Q21: improvement, but stationarity and boundary admission still fail',fontsize=15)
fig.savefig(p/'assessment/measured-gates.png',dpi=220);plt.close(fig)
