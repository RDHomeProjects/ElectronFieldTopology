"""Render static scientific figures from the archived admission assessment. Apache-2.0."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


def main():
    ledger = json.loads((HERE/'assessment-verification.json').read_text())
    summary = json.loads((HERE/'summary.json').read_text())
    rows = {r['stage']:r for r in summary['stages']}
    stamp = ledger['assessed_at']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'svg.hashsalt':'sf-dynamics-assessment-20261102'})
    colors = ['#1565c0','#b45309','#b01c79','#067a64','#7c3aed','#c62828']
    branches = ['q17-neighbour','q18-baseline','q18-scale35','q18-scale45','q18-ell025','q19-neighbour']
    labels = ['Q17','Q18 baseline','Q18 scale 3.5','Q18 scale 4.5','Q18 length .25','Q19']
    footer = 'Assessment: '+stamp['utc']+' UTC  |  '+stamp['melbourne']+' Melbourne'
    def save(fig, name):
        fig.text(.02,.015,footer,fontsize=8,color='#444444')
        fig.savefig(HERE/(name+'.png'),dpi=180,facecolor='white')
        fig.savefig(HERE/(name+'.svg'),metadata={'Date':stamp['utc']},facecolor='white')
        p=HERE/(name+'.svg');p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
        plt.close(fig)
    fig, axes = plt.subplots(1,2,figsize=(12,5.4))
    for branch,label,color in zip(branches,labels,colors):
        ns=[n for n in (97,129,161,193) if branch+'-'+str(n) in rows]
        values=[100*rows[branch+'-'+str(n)]['integrals']['stress_frobenius_over_energy'] for n in ns]
        axes[0].plot(ns,values,'o-',label=label,color=color,lw=1.8,ms=4)
        data=next(x for x in ledger['matched_domain_comparisons'] if x['branch']==branch)
        axes[1].plot([15.36,18.432],[100*data['small_stress_over_energy'],100*data['large_stress_over_energy']],
                     'o-',color=color,label=label,lw=1.8,ms=4)
    axes[0].set(title='Mesh refinement: fixed box side 15.36',xlabel='Nodes per axis',
                ylabel='Integrated stress Frobenius norm / rest energy (%)',xticks=[97,129,161,193],ylim=(0,2.35))
    axes[1].set(title='Domain comparison: fixed spacing h = 0.096',xlabel='Box side in model units',
                xticks=[15.36,18.432],ylim=(0,2.35))
    for ax in axes:ax.grid(alpha=.22)
    fig.suptitle('Stress is more sensitive to box size than to mesh refinement',fontsize=14,y=.98)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.07),ncol=3,frameon=False)
    fig.subplots_adjust(left=.08,right=.98,top=.84,bottom=.29,wspace=.22)
    save(fig,'stress-domain-sensitivity')
    fig,axes=plt.subplots(1,2,figsize=(12,5.4))
    for branch,label,color in [(branches[0],labels[0],colors[0]),(branches[1],labels[1],colors[1]),(branches[5],labels[5],colors[5])]:
        for suffix,style,boxlabel in [('-161','--','side 15.36'),('-domain','-','side 18.432')]:
            row=rows[branch+suffix]
            beta=[0,.1,.3,.5,.75,.9]
            energy=[100*max(abs(x['energy_particle_relative_defect']) for x in row['boosts'] if x['beta']==b) for b in beta]
            momentum=[100*max(x['momentum_particle_scaled_defect'] for x in row['boosts'] if x['beta']==b) for b in beta]
            axes[0].plot(beta,energy,style,color=color,lw=1.8,label=label+', '+boxlabel)
            axes[1].plot(beta,momentum,style,color=color,lw=1.8,label=label+', '+boxlabel)
    axes[0].set(title='Energy defect: max over three boost axes',ylabel=r'$|E-\gamma E_0|/(\gamma E_0)$ (%)')
    axes[1].set(title='Momentum defect: max over three boost axes',ylabel=r'$\|P-\gamma\beta E_0\hat{e}_a\|/(\gamma E_0)$ (%)')
    for ax in axes:ax.set(xlabel=r'Formal boost speed $\beta=v/c$',xticks=[0,.1,.3,.5,.75,.9]);ax.grid(alpha=.22)
    fig.suptitle('Kinematic boost diagnostics on matched h = 0.096 fields',fontsize=14,y=.98)
    fig.text(.5,.885,'Tensor identities on contracted rest boxes; no physical-time evolution',ha='center',fontsize=10)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.07),ncol=3,frameon=False,fontsize=9)
    fig.subplots_adjust(left=.08,right=.98,top=.79,bottom=.29,wspace=.30)
    save(fig,'boost-domain-sensitivity')


if __name__ == '__main__': main()
