from pathlib import Path
import json,zipfile,math,hashlib,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
R=Path(__file__).resolve().parent;d=json.loads((R/'INDEPENDENT-REVIEW.json').read_text())
with zipfile.ZipFile(R/'data/completed-evidence.zip') as z:record=json.loads(z.read('record.json'));bulk=json.loads(z.read('BULK-LEDGER.json'));fits=json.loads(z.read('CURVE-FITS.json'))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
colors={'exact-control':'#444444','mesh-129':'#1460a4','mesh-137':'#007f70','mesh-145':'#c35c18','mesh-153':'#9852a3','mesh-161':'#b32d40'}
def save(fig,name):
 fig.text(.01,.005,'Run 20261123t032942z-26dd4a7c | Review UTC '+d['reviewed_at']['utc']+' | Melbourne '+d['reviewed_at']['melbourne'],fontsize=5.5,color='#555555')
 fig.savefig(R/(name+'.png'),dpi=240,bbox_inches='tight');fig.savefig(R/(name+'.svg'),bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(2,1,figsize=(11,8),sharex=True)
for c in record['cases']:
 name=c['case']['id'];h=c['history'];x=[r['accepted_step'] for r in h]
 for a,key,gate in [(ax[0],'relative_force_l2',1e-4),(ax[1],'acceleration_max',1e-3)]:
  y=np.array([r['metrics'][key] for r in h]);a.plot(x,y,color=colors[name],alpha=.28,lw=.8);med=[np.median(y[max(0,i-9):i+1]) for i in range(len(y))];a.plot(x,med,color=colors[name],lw=1.8,ls='--' if name=='exact-control' else '-',label=name)
for a,limit,label in [(ax[0],1e-4,'Relative force'),(ax[1],1e-3,'Maximum zero-rate acceleration')]:
 a.set_yscale('log');a.axhline(limit,color='#287d2c',ls='--',label='Original gate');a.axvline(55,color='gray',ls=':');a.axvspan(55,80,color='gray',alpha=.05);a.set_ylabel(label);a.grid(alpha=.18)
ax[0].legend(ncol=4,fontsize=8);ax[1].set_xlabel('Accepted optimizer updates after native iteration 545');fig.suptitle('No Q21 arm reaches the original residual gates\nThin: actual observations; thick: trailing ten-update medians; vertical line: native restart');fig.tight_layout();save(fig,'matched-residuals')
measured=[x for x in d['endpoints'] if x['case']!='exact-control'];nodes=np.array([x['nodes'] for x in measured]);spacing=np.array([x['spacing'] for x in measured]);angles=np.array([x['final_angle_degrees'] for x in measured]);fig,ax=plt.subplots(2,2,figsize=(12,9))
for a,initial,final,label in [(ax[0,0],'initial_force','final_force','Relative force'),(ax[0,1],'initial_acceleration','final_acceleration','Maximum acceleration')]:
 xx=np.arange(len(measured));a.bar(xx-.18,[x[initial] for x in measured],.36,label='Initial / interpolated',color='#cf8736');a.bar(xx+.18,[x[final] for x in measured],.36,label='After 80 updates',color='#1764a4');a.set_xticks(xx,nodes);a.set_yscale('log');a.set_xlabel('Nodes per axis');a.set_ylabel(label);a.legend(fontsize=8)
a=ax[1,0];a.scatter(nodes,angles,color='#1460a4',zorder=3,label='Measured at update 80');grid=np.linspace(129,193,120)
for m in d['post_hoc_angle_models']:
 y=np.polyval(m['coefficients_highest_power_first'],30.72/(grid-1));y=np.exp(y) if m['model']=='exponential' else y;a.plot(grid,y,lw=1,label=m['model']+' in spacing')
a.axhline(30,color='#287d2c',ls='--',label='Literature sampling warning');a.axvspan(161,193,color='gray',alpha=.12,label='Unmeasured extrapolation');a.set_xlabel('Nodes per axis');a.set_ylabel('Maximum neighbour angle (degrees)');a.legend(fontsize=7);a.set_title('Exploratory geometry fits; no stability prediction')
a=ax[1,1];base=next(x for x in d['endpoints'] if x['case']=='mesh-129');sourceE=next(c['history'][0]['metrics']['energy'] for c in record['cases'] if c['case']['id']=='mesh-129');a.plot(nodes,[100*(next(c for c in record['cases'] if c['case']['id']==x['case'])['history'][0]['metrics']['energy']/sourceE-1) for x in measured],'o-',label='Initialization difference');a.plot(nodes,[100*(x['final_energy']/base['final_energy']-1) for x in measured],'s-',label='Matched 80-update difference');a.set_xlabel('Nodes per axis');a.set_ylabel('Energy difference from 129³ (%)');a.legend(fontsize=8);a.set_title('Small energy differences do not certify stationarity');fig.suptitle('Refinement changes the starting residual, sampling and discrete energy');fig.tight_layout();save(fig,'resolution-and-initialization')
fig,ax=plt.subplots(1,2,figsize=(12,4.5));x=np.array([r['spacing'] for r in fits['responses']]);f=np.array([r['force'] for r in fits['responses']]);j=np.array([r['joint'] for r in fits['responses']]);ax[0].scatter(x,f,color='#1460a4');quad=next(m for m in fits['fits']['force']['models'] if m['model']=='quadratic');xx=np.linspace(x.min(),x.max(),100);ax[0].plot(xx,np.polyval(quad['coefficients_highest_power_first'],xx),color='#b15c17',label='Qualifying force-only quadratic');a,b,c=quad['coefficients_highest_power_first'];v=-b/(2*a);ax[0].annotate('Maximum, not optimum\nN ≈ 147',xy=(v,np.polyval([a,b,c],v)),xytext=(.218,.00135),arrowprops={'arrowstyle':'->'},fontsize=9);ax[0].axhline(1e-4,color='green',ls='--');ax[0].set_ylabel('Median relative force, updates 71–80');ax[0].legend(fontsize=8);ax[1].scatter(x,j,color='#1460a4');ax[1].axhline(1,color='green',ls='--');ax[1].set_ylabel('Joint median residual score');ax[1].set_title('No registered joint-response model qualifies')
for a in ax:
 a.set_xlabel('Spacing at fixed box 30.72');a.grid(alpha=.15)
 for p,h in zip(fits['responses'],x):a.annotate(str(p['nodes']),(h,p['force'] if a is ax[0] else p['joint']),xytext=(4,5),textcoords='offset points',fontsize=8)
fig.tight_layout();save(fig,'registered-response-models')
fig,ax=plt.subplots(figsize=(11,4.8));t=d['timing_seconds'];keys=['metrics_seconds','bulk_audit_seconds','backend_audit_seconds','before_tracked_worker_interval_seconds','checkpoint_seconds','other_tracked_worker_seconds','optimizer_seconds'];labels=['Per-update CPU metrics','Retained-field audit','CPU/CUDA gradient audits','Before tracked worker interval (unassigned)','Checkpoint writes','Other tracked worker overhead','Optimizer steps'];minutes=[t[k]/60 for k in keys];ax.barh(labels,minutes,color=['#175e98','#4a8e86','#729fbe','#9c9c9c','#b2b2b2','#cacaca','#c47e2a']);ax.invert_yaxis();ax.set_xlabel('Recorded minutes');ax.set_title('About 6 h 15 min launch-to-completion; optimizer steps took about 5 min')
for i,v in enumerate(minutes):ax.text(v+.8,i,f'{v:.1f} min',va='center',fontsize=9)
fig.tight_layout();save(fig,'runtime-breakdown')
# Preserve the original uploaded bytes; no scientific source archive is rewritten.
# Original data/completed-evidence.zip is read-only for this reproduction.
print('figures saved',len(list(R.glob('*.png'))))
