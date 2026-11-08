"""Render retained scalar histories; does not run science calculations."""
import argparse,json
from pathlib import Path

def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=Path(__file__).with_name('compact-verification.json'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();d=json.loads(a.input.read_text());a.output.mkdir(parents=True,exist_ok=True);stamp=d['recorded_at'];footer='Assessed UTC '+stamp['utc']+' | Melbourne '+stamp['melbourne']
    plt.rcParams.update({'font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(10,4.3))
    for key,color in [('q17','#2077b4'),('q19','#d15b25')]:
        rows={r['iteration']:r for r in d['optimizer_history'] if r['model']==key};x=sorted(rows)
        axs[0].semilogy(x,[rows[i]['relative_force_l2']/1e-4 for i in x],'o-',label=key.upper(),color=color)
        axs[1].semilogy(x,[rows[i]['acceleration_max']/1e-3 for i in x],'o-',label=key.upper(),color=color)
    for ax,title in zip(axs,['Relative force / limit','Maximum acceleration / limit']):
        ax.axhline(1,color='#444444',ls='--',label='Admission limit');ax.set_xlabel('Preparation iteration (not physical time)');ax.set_title(title);ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Q17/Q19 remain above stationary preparation limits');fig.text(.02,.015,footer,fontsize=6);fig.tight_layout(rect=(0,.05,1,.95));save(fig,a.output/'preparation-residuals');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4.3))
    for key,color in [('q17','#2077b4'),('q19','#d15b25')]:
        rows={r['iteration']:r for r in d['optimizer_history'] if r['model']==key};x=sorted(rows);e0=rows[0]['energy'];ef=rows[200]['energy']
        axs[0].plot(x,[100*(e0-rows[i]['energy'])/e0 for i in x],'o-',label=key.upper(),color=color)
        axs[1].plot([i for i in x if i>=50],[(rows[i]['energy']-ef)/ef*1e6 for i in x if i>=50],'o-',label=key.upper(),color=color)
    axs[0].set_ylabel('Energy decrease from initial (%)');axs[1].set_ylabel('Excess above final energy (ppm)')
    for ax in axs:ax.set_xlabel('Preparation iteration');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Energy decreases while stationarity remains unresolved');fig.text(.02,.015,footer,fontsize=6);fig.tight_layout(rect=(0,.05,1,.95));save(fig,a.output/'preparation-energy');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4.3));rows=d['milestones'];ts=[r['time'] for r in rows]
    axs[0].plot(ts,[r['speed_percent'] for r in rows],'o-',label='Centroid speed error');axs[0].plot(ts,[r['shape_percent'] for r in rows],'s-',label='Original trilinear shape error');axs[0].axhline(1,color='#444',ls='--',label='1% original limit');axs[0].set_ylabel('Relative error (%)')
    axs[1].plot(ts,[r['max_tail_percent'] for r in rows],'o-',label='Maximum observed width-2 tail');axs[1].axhline(.1,color='#444',ls='--',label='0.1% original limit');axs[1].axhline(.09,color='#888',ls=':',label='0.09% runtime reserve');axs[1].set_ylabel('Energy fraction (%)')
    for ax in axs:ax.set_xlabel('Physical model time');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Q2 short reference passes all seven original gates at each milestone');fig.text(.02,.015,footer,fontsize=6);fig.tight_layout(rect=(0,.05,1,.95));save(fig,a.output/'q2-reference');plt.close(fig)

def save(fig,path):
    fig.savefig(path.with_suffix('.png'),dpi=160);fig.savefig(path.with_suffix('.svg'))
    svg=path.with_suffix('.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
if __name__=='__main__':main()
