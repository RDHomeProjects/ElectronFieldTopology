"""Render the recorded temporal-study CSVs; no solver, interpolation or physics changes."""
import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
P=Path(__file__).resolve().parent
m=json.loads((P/'assessment-metadata.json').read_text());at=m['recorded_at'];footer=f"Assessed {at['utc']} UTC | {at['melbourne']} Australia/Melbourne"
rows=list(csv.DictReader((P/'case-metrics.csv').open()));fine={r['model']:r for r in rows if float(r['dt'])==.0025};colors=['#2767a4','#e37c27'];plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,3,figsize=(12,4.5))
for ax,key,limit,title in zip(axes,['maximum_observed_tail_fraction','legacy_shape_relative_l2','speed_relative_error'],[.1,1,1],['Maximum observed tail','Historical shape error','Centroid speed error']):
 values=[float(fine[k][key])*100 for k in ['q1-x','q2-z']];bars=ax.bar(['Q1 / x','Q2 / z'],values,color=colors,width=.6);ax.axhline(limit,color='#9c2525',ls='--',lw=1.5,label=f'Original limit {limit:g}%');ax.set_title(title);ax.set_ylabel('Percent');ax.set_ylim(0,max(max(values)*1.3,limit*1.32));ax.legend(fontsize=8,loc='upper right')
 for bar,value in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+ax.get_ylim()[1]*.025,f'{value:.4g}%',ha='center')
fig.suptitle('Tail-controlled T1 motion, finest time step dt = 0.0025',y=.98,fontsize=14);fig.text(.5,.025,footer,ha='center',fontsize=7);fig.tight_layout(rect=[0,.07,1,.93])
for ext in ['png','svg']:fig.savefig(P/f'motion-gates.{ext}',dpi=180)
plt.close(fig)
rows=list(csv.DictReader((P/'temporal-metrics.csv').open()));fig,axes=plt.subplots(1,2,figsize=(11,4.5))
for ax,key,title in zip(axes,['field_order','rate_order'],['Field refinement order','Field-rate refinement order']):
 for model,color in zip(['q1-x','q2-z'],colors):
  rs=[r for r in rows if r['model']==model];ax.plot([float(r['time']) for r in rs],[float(r[key]) if r[key] else np.nan for r in rs],'-o',color=color,label=model.upper())
 ax.axhline(4,color='#555',ls='--',lw=1);ax.set_xticks([.25,.5,.75,1]);ax.set_xlabel('Physical time (c = 1 model units)');ax.set_ylabel('log₂(coarse–medium / medium–fine)');ax.set_title(title);ax.set_ylim(3.96,4.04);ax.legend()
axes[0].annotate('Q2 at T=.25: below 10⁻¹² floor; no order',(.26,3.97),fontsize=8)
fig.suptitle('Matched-time refinement on each family’s fixed central 73³ lab nodes',y=.98,fontsize=13);fig.text(.5,.025,footer,ha='center',fontsize=7);fig.tight_layout(rect=[0,.07,1,.93])
for ext in ['png','svg']:fig.savefig(P/f'temporal-orders.{ext}',dpi=180)
plt.close(fig)

# Matplotlib path strings contain harmless trailing spaces; normalize new SVG text.
for path in P.glob("*.svg"):
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines())+"\n")
