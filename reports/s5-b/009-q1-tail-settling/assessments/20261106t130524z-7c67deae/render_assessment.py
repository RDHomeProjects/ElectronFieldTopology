"""Render recorded metrics only; no solver or scientific-field calculation. Apache-2.0."""
import argparse,json,zipfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from verify_assessment import stamp

def main():
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(args.evidence) as z:
  c=json.loads(z.read('campaign.json'));p=json.loads(z.read('comparisons.json'));fig,ax=plt.subplots(1,2,figsize=(11,4.6))
  for key,r in c['cases'].items():
   rows=json.loads(z.read(f'readmission/{key}/observations.json'));x=[q['iteration'] for q in rows]
   ax[0].plot(x,[100*q['shell_fraction'] for q in rows],'-o',label=f"L={r['length']}")
   ax[1].semilogy(x,[q['stationarity']['relative_force_l2'] for q in rows],'-o',label=f"L={r['length']}")
  ax[0].axhline(.1,color='#555',ls=':',label='Original 0.1% shell limit');ax[1].axhline(1e-9,color='#555',ls=':',label='Strict force target')
  ax[0].set(ylabel='Energy in outer shell (%)',title='Tail trend; final endpoints retained')
  ax[1].set(ylabel='Relative force',title='Endpoint force and prescribed sampling differ')
  for aa in ax:aa.set_xlabel('Optimization iteration (not physical time)');aa.grid(alpha=.2);aa.legend(fontsize=8)
  fig.suptitle('S5-B-009: both native statuses remain stationarity_unresolved')
  fig.text(.01,.01,json.dumps(stamp()),fontsize=6);fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(args.output/'settling-history.png',dpi=160);plt.close(fig)
  fig,ax=plt.subplots(1,2,figsize=(11,4.6))
  for key,r in c['cases'].items():
   profile=r['final']['fixed_region_profile'];ax[0].semilogy([v['cube_half_width'] for v in profile],[v['energy_outside'] for v in profile],'-o',label=f"L={r['length']}")
  ax[0].set(xlabel='Fixed cube half-width (model units)',ylabel='Absolute energy outside fixed cube',title='Exterior energy rises despite lower moving-shell fraction');ax[0].legend();ax[0].grid(alpha=.2)
  rr=p['regions'];x=list(range(len(rr)));w=.32
  ax[1].bar([v-w/2 for v in x],[100*r['field_relative_l2'] for r in rr],w,label='Raw field relative L2')
  ax[1].bar([v+w/2 for v in x],[100*r['density_relative_l1'] for r in rr],w,label='Energy-density relative L1')
  ax[1].set_xticks(x,[str(r['common_nodes'])+'³' for r in rr]);ax[1].set(xlabel='Same-centre common analysis region',ylabel='Domain difference (%)',title='Small density differences do not equal field convergence');ax[1].legend(fontsize=8);ax[1].grid(axis='y',alpha=.2)
  fig.text(.01,.01,json.dumps(stamp()),fontsize=6);fig.tight_layout(rect=(0,.05,1,1));fig.savefig(args.output/'domain-sensitivity.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
