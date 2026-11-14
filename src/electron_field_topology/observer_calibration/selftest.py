"""Independent polynomial and fixed-state controls for the observer integrals."""
from pathlib import Path
import tempfile
import numpy as np
from .calibration import cell_rule,line_rule,integrate_component,normalise,prepare,measure,max_change
from .reference.numerics import OFF_E,OFF_B,points,case
from .reference.observer import metrics

def manufactured():
    # Analytic integral of (1+x+y+z)^2 on [-2,2]^3 = 320.
    n=17;L=8.;o=(.5,0,0);p=points(n,L,o,2,0);native=1+p[...,0]+p[...,1]+p[...,2]
    zero=np.zeros_like(native)
    def exact(q,t):
        a=np.ones_like(q);return a,a
    axes=[cell_rule(n,L,v,2) for v in o]
    sums=integrate_component(native,zero,o,exact,0,0,n,L,0,axes)
    assert abs(sums[0]-320)<1e-10
    assert abs(sums[1]-64)<1e-10 and abs(sums[2]-256)<1e-10 and abs(sums[3]+128)<1e-10
    assert normalise(sums)['vector_decomposition_closure']<1e-13
    # Piecewise-linear kink with a native knot at zero: integral x^2 = 256/3.
    kink=np.abs(p[...,0]);s=integrate_component(kink,zero,o,exact,0,0,n,L,0,axes)
    assert abs(s[0]-256/3)<1e-10
    for count in [33,101]:
        for mid in [False,True]:assert abs(sum(line_rule(count,midpoint=mid)[1])-4)<1e-13
    return {'analytic_polynomial_integral':float(sums[0]),'expected':320.,'piecewise_kink_integral':float(s[0]),'expected_kink':256/3,'status':'passed'}

def qualify(repo):
    result={'manufactured':manufactured(),'fixed_state_controls':[]}
    with tempfile.TemporaryDirectory() as tmp:
        for field in ['hopfion','packet']:
            p={'nodes':17,'length':8.,'field':field,'duration':.05,'steps':24,'angle_degrees':0.,'rotation_code':None}
            f=Path(tmp)/(field+'.npz');c=case(p,repo,f,retain_trace=False)
            with np.load(f,allow_pickle=False) as a:E=a['E'];B=a['B_half']
            e0=E.copy();b0=B.copy();s=prepare(E,B,p,repo);legacy=metrics(E,B,p,repo,33);stream=measure(s,nodes=33);assert max_change(legacy,stream)<2e-12
            g2=measure(s,order=2);g3=measure(s,order=3);assert np.isfinite(list(g3[k] for k in ['evolution_observed_error','total_observed_error'])).all()
            assert np.array_equal(E,e0) and np.array_equal(B,b0)
            result['fixed_state_controls'].append({'field':field,'legacy_streamed_max_difference':max_change(legacy,stream),'gauss2_to3_max_change':max_change(g2,g3),'raw_arrays_unchanged':True})
    result['status']='qualification_passed';return result
