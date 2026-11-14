import math
def catalogue(plan):
 out=[]
 for q in plan['q_values']:
  divisors=[(a,q//a) for a in range(1,q+1) if q%a==0 and a>=q//a];a,b=min(divisors,key=lambda v:(max(v),v));scale=2.8*(q/3)**.25
  base={'q':q,'scale':scale,'cutoff':8.8,'bend':0.,'amplitude':1.,'perturbation':.005}
  first={**base,'id':f'q{q}-axial{a}-{b}','family':'axial','alpha':a,'beta':b}
  pairs=[(aa,bb) for aa in range(1,q) for bb in range(1,q) if 2*aa+3*bb==q]
  if q>=5 and pairs:
   aa,bb=min(pairs,key=lambda v:(sum(v),max(v)));second={**base,'id':f'q{q}-trefoil32-{aa}-{bb}','family':'trefoil32','alpha':aa,'beta':bb}
  elif (a,b)!=(q,1):second={**base,'id':f'q{q}-axial{q}-1','family':'axial','alpha':q,'beta':1}
  else:second={**first,'id':f'q{q}-bent','bend':.65}
  if q==2:first.update(id='q2-retained-reference',family='reference')
  # Reproduce the previously measured seed variants exactly at Q3/Q4/Q7.
  if q==3:first.update(id='q3-axial',scale=2.8);second={**first,'id':'q3-bent','bend':.65}
  if q==4:first.update(id='q4-axial22',scale=3.2,bend=.2);second.update(id='q4-axial41',scale=3.2,bend=.2)
  if q==7:first.update(id='q7-axial',scale=4.,bend=.25);second.update(id='q7-trefoil',alpha=2,beta=1,scale=3.8,bend=.25,amplitude=2.)
  out.extend([first,second])
 return out
