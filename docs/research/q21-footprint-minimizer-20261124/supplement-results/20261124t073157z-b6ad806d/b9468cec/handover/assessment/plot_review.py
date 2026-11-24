from pathlib import Path
import json,zipfile,io
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent
d=json.loads((R/'INDEPENDENT-REVIEW.json').read_text())
with zipfile.ZipFile(R/'data/supplement-evidence.zip') as z:
 new=json.loads(z.read('record.json'))['new_cases']
 with zipfile.ZipFile(io.BytesIO(z.read('handover/data/completed-evidence.zip'))) as old:cases=json.loads(old.read('record.json'))['cases']+new
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
colors={'exact-control':'#666666','mesh-129':'#777777','mesh-137':'#9a9a9a','mesh-145':'#a5a077','mesh-153':'#a78aaa','mesh-161':'#759c90','cpu-177':'#1460a4','cpu-193':'#b33126'}
def save(fig,name):
 fig.text(.01,.004,'Review UTC '+d['reviewed_at']['utc']+' | Melbourne '+d['reviewed_at']['melbourne']+' | New run 20261123t130300z-db9ba00c',fontsize=5.5,color='#555');fig.savefig(R/(name+'.png'),dpi=220,bbox_inches='tight');fig.savefig(R/(name+'.svg'),bbox_inches='tight');plt.close(fig)
fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True)
for c in cases:
 label=c['case']['id'];x=[r['accepted_step'] for r in c['history']]
 for ax,key,gate in zip(axes,['relative_force_l2','acceleration_max'],[1e-4,1e-3]):
  ax.semilogy(x,[r['metrics'][key] for r in c['history']],color=colors[label],lw=1.8 if label.startswith('cpu') else .8,alpha=1 if label.startswith('cpu') else .75,label=label)
for ax,key,gate in zip(axes,['Relative force','Maximum acceleration'],[1e-4,1e-3]):
 ax.axhline(gate,color='green',ls='--',lw=1,label='unchanged project gate');ax.axvline(55,color='#333',ls=':',lw=1);ax.set_ylabel(key);ax.grid(alpha=.2)
axes[0].legend(ncol=3,fontsize=8);axes[1].set_xlabel('Accepted updates from the same native iteration-545 parent');axes[0].set_title('Fine CPU branches remain nonstationary after 80 updates');axes[1].text(56,.002,'Native restart at update 55',fontsize=8);fig.tight_layout(rect=(0,.025,1,1));save(fig,'trajectories')
end=[r for r in d['cases'] if r['case']!='exact-control'];nodes=np.array([r['nodes'] for r in end]);angle=np.array([r['neighbour_degrees'] for r in end]);hopf=np.array([100*r['hopf_relative_error'] for r in end]);E=np.array([r['energy'] for r in end])
fig,axes=plt.subplots(2,2,figsize=(11,8))
axes[0,0].plot(nodes,angle,'o-',color='#1460a4');axes[0,0].axhline(30,color='green',ls='--',label='literature warning, not admission');axes[0,0].set_ylabel('Maximum neighbour angle (degrees)');axes[0,0].set_title('Angular sampling improves\n30° warning cleared');axes[0,0].legend(fontsize=8)
axes[0,1].plot(nodes,hopf,'o-',color='#1460a4');axes[0,1].set_ylabel('| |H| − 21 | / 21 (%)');axes[0,1].set_title('Hopf quadrature improves\nNot an exact integer certificate')
axes[1,0].plot(nodes,100*(E/E[0]-1),'o-',label='relative to 129³');axes[1,0].set_ylabel('Energy difference from 129³ (%)');axes[1,0].set_title('Small cross-grid energy changes\nAll endpoints remain unresolved')
a={r['label']:r for r in d['field_audits_summary']};vir=[100*a[('final-' if r['backend']=='cpu' else 'retained-')+r['case']]['virial_proxy'] for r in end];axes[1,1].plot(nodes,vir,'o-',color='#a65424');axes[1,1].set_ylabel('(E2 − E4)/(E2 + E4) (%)');axes[1,1].set_title('E2/E4 balance improves\nScalar proxy only')
for ax in axes.ravel():ax.set_xlabel('Nodes per axis (box 30.72)');ax.grid(alpha=.2);ax.set_xticks(nodes,[str(n) for n in nodes],rotation=40)
fig.tight_layout(rect=(0,.025,1,1));save(fig,'sampling-and-energy')
labels=['q2-reference','retained-mesh-129','retained-mesh-153','retained-mesh-161','final-cpu-177','final-cpu-193'];display=['Q2 reference','Q21 129³','Q21 153³','Q21 161³','Q21 177³','Q21 193³'];rows=[a[x] for x in labels];x=np.arange(len(rows))
fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True)
for key,label,marker in [('component_rms','Whole-box component RMS','o'),('core_vector_rms','Core vector RMS','s'),('acceleration_max','Maximum vector magnitude','^')]:axes[0].semilogy(x,[r[key] for r in rows],marker+'-',label=label)
axes[0].axhline(.001,color='green',ls='--',label='gate applies to maximum only');axes[0].set_ylabel('Model acceleration diagnostic');axes[0].set_title('Whole-box RMS conceals a substantial core residual');axes[0].legend(fontsize=8,ncol=2);axes[0].grid(alpha=.2)
axes[1].bar(x-.17,[100*r['fraction_grid_acceleration_above_0p001'] for r in rows],width=.34,label='whole grid above 0.001')
axes[1].bar(x+.17,[100*r['fraction_grid_acceleration_above_0p01'] for r in rows],width=.34,label='whole grid above 0.01');axes[1].set_ylabel('Fraction of all grid nodes (%)');axes[1].set_xticks(x,display);axes[1].legend(fontsize=8);axes[1].grid(axis='y',alpha=.2)
fig.text(.07,.025,'Core masks and box sizes differ across Q. These are diagnostic comparisons, not a universal suitability ranking.',fontsize=8);fig.tight_layout(rect=(0,.06,1,1));save(fig,'residual-distribution')
fig,ax=plt.subplots(figsize=(11,4.5));left=np.zeros(2)
for key,label,color in [('optimizer_seconds','CPU optimizer','#1460a4'),('backend_audit_seconds','Same-implementation repeats','#d39335'),('metrics_seconds','Measurements','#54957c'),('checkpoint_seconds','Checkpoints','#8a75a3')]:
 values=np.array([sum(r.get('timing',{}).get(key,0) for r in c['history'])/3600 for c in new]);ax.barh(['177³ CPU','193³ CPU'],values,left=left,label=label,color=color);left+=values
ax.set_xlabel('Recorded per-update component hours; supplementary audits/overhead excluded');ax.set_title('CPU runtime is dominated by measurements, with substantial optimizer cost');ax.legend(ncol=2,fontsize=8);fig.tight_layout(rect=(0,.04,1,1));save(fig,'runtime-components')
