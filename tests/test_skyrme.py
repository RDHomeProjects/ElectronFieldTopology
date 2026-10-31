"""Independent static-energy controls before any high-charge relaxation."""
import numpy as np
import pytest
from scipy.integrate import quad
from electron_field_topology.skyrme import (K,NORTH,Energy,numpy_energy,normalize,
    coordinates,rational_field,set_boundary,diagnostics,numpy_cell_energy)


def test_native_energy_and_exact_adjoint_against_independent_cross_product_array(tmp_path):
    rng=np.random.default_rng(20261031);n=9;h=.3
    u=normalize(NORTH+.15*rng.normal(size=(n,n,n,3)))
    native=Energy(n,h,tmp_path,method='forward')
    e,g=native.evaluate(u);er,gr=numpy_energy(u,h)
    np.testing.assert_allclose(e,er,rtol=1e-12,atol=1e-14)
    np.testing.assert_allclose(g,gr,rtol=1e-11,atol=1e-13)
    u=set_boundary(u);v=rng.normal(size=u.shape)
    v=set_boundary(v+NORTH)-set_boundary(np.broadcast_to(NORTH,u.shape))
    v-=u*np.sum(v*u,axis=-1,keepdims=True);v/=np.linalg.norm(v)
    _,g=native.objective(u.ravel());exact=float(g@v.ravel())
    errs=[]
    for eps in [1e-3,1e-4,1e-5]:
        plus=native.objective((u+eps*v).ravel())[0];minus=native.objective((u-eps*v).ravel())[0]
        errs.append(abs((plus-minus)/(2*eps)-exact))
    assert min(errs)<2e-8


def test_constant_and_global_target_rotation(tmp_path):
    n=13;e=Energy(n,.3,tmp_path)
    field=np.broadcast_to(NORTH,(n,n,n,3)).copy()
    parts,g=e.evaluate(field)
    np.testing.assert_allclose(parts,0,atol=1e-28);np.testing.assert_allclose(g,0,atol=1e-14)
    # Interior compact perturbation rotates about fixed north, an exact symmetry.
    field[4:9,4:9,4:9]=normalize([.3,.4,1.])
    angle=.37;c,s=np.cos(angle),np.sin(angle)
    rotation=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
    np.testing.assert_allclose(e.evaluate(field)[0],e.evaluate(field@rotation.T)[0],rtol=1e-13,atol=1e-15)


@pytest.mark.parametrize('scale',[.5,1.,2.])
def test_independent_all_space_analytic_hopf_energy_and_dilation(scale):
    # Hopf submersion has singular values 2 lambda, 2 lambda, 0,
    # lambda=2s/(r²+s²). These densities are independent of the lattice code.
    e2=4*np.pi*K*quad(lambda r:32*scale**2*r*r/(r*r+scale**2)**2,0,np.inf,epsabs=1e-10)[0]
    e4=4*np.pi*K*quad(lambda r:256*scale**4*r*r/(r*r+scale**2)**4,0,np.inf,epsabs=1e-10)[0]
    np.testing.assert_allclose([e2,e4],[scale/np.sqrt(2),1/(np.sqrt(2)*scale)],rtol=1e-12)


def test_sampled_hopf_refinement_and_charge(tmp_path):
    rows=[]
    for n in [25,33,49]:
        h=8/(n-1);u=rational_field(coordinates(n,h),scale=1.,cutoff=3.8)
        e,_=Energy(n,h,tmp_path).evaluate(set_boundary(u));rows.append(sum(e))
    assert abs(rows[2]-rows[1])<abs(rows[1]-rows[0])
    diag=diagnostics(set_boundary(u),h)
    assert abs(abs(diag['hopf_integral'])-1)<.015
    assert diag['unit_error']<1e-14


def test_profile_homogeneous_coordinates_and_boundaries():
    points=coordinates(17,.4)
    for kind,a,b in [('axial',1,1),('axial',2,1),('cable',4,1),('torus72',2,2)]:
        u=rational_field(points,kind,a,b,scale=2.,cutoff=3.)
        np.testing.assert_allclose(np.linalg.norm(u,axis=-1),1,atol=1e-14)
        np.testing.assert_allclose(u[0],np.broadcast_to(NORTH,u[0].shape),atol=1e-14)
    with pytest.raises(ValueError):normalize(np.zeros((2,3)))


def test_pointwise_hopf_densities_against_independent_submersion_formula():
    x=np.array([[.2,.3,.4],[1.,-.4,.8],[0.,0.,0.]])
    for s in [.7,1.3]:
        d=[]
        for i in range(3):
            step=np.eye(3)[i]*1e-5
            d.append((rational_field(x+step,scale=s)-rational_field(x-step,scale=s))/(2e-5))
        r2=np.sum(x*x,axis=-1)
        e2=sum(np.sum(a*a,axis=-1) for a in d)
        e4=sum(np.sum(np.cross(d[i],d[j])**2,axis=-1) for i,j in [(0,1),(0,2),(1,2)])
        np.testing.assert_allclose(e2,32*s*s/(r2+s*s)**2,rtol=2e-8)
        np.testing.assert_allclose(e4,256*s**4/(r2+s*s)**4,rtol=3e-8)


def test_normalized_cell_energy_and_constrained_gradient(tmp_path):
    rng=np.random.default_rng(35);n=9;h=.3
    u=set_boundary(normalize(NORTH+.12*rng.normal(size=(n,n,n,3))))
    eng=Energy(n,h,tmp_path,method='cell')
    np.testing.assert_allclose(eng.evaluate(u)[0],numpy_cell_energy(u,h),rtol=1e-12,atol=1e-14)
    v=np.zeros_like(u);v[2:-2,2:-2,2:-2]=rng.normal(size=(5,5,5,3));v/=np.linalg.norm(v)
    _,g=eng.objective(u.ravel());exact=float(g@v.ravel());eps=1e-4
    delta=(sum(numpy_cell_energy(normalize(u+eps*v),h))-sum(numpy_cell_energy(normalize(u-eps*v),h)))/(2*eps)
    assert abs(delta-exact)<1e-9
    north=np.broadcast_to(NORTH,u.shape).copy()
    np.testing.assert_allclose(eng.evaluate(north)[0],0,atol=1e-28)
    # A lattice-scale checkerboard has positive energy in the cell functional.
    north[2:-2,2:-2,2:-2,0]=.2*(-1.)**np.indices((5,5,5)).sum(axis=0)
    checker=normalize(north)
    np.testing.assert_allclose(eng.evaluate(checker)[0],numpy_cell_energy(checker,h),rtol=1e-12,atol=1e-14)
    assert sum(eng.evaluate(checker)[0])>1e-12
