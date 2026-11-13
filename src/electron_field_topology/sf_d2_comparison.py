"""Independent D2 variational SF vector field. Initial diagnostics only.
Kinetic v.M.v; sigma nearest-edge positive energy; quartic centered D2 jets.
All derivatives derived from this finite-dimensional action. No time stepper.
"""
import numpy as np
K=1/(32*np.pi**2*np.sqrt(2));NORTH=np.array([0.,0.,1.])
def derivative(a,h,axis,boundary='periodic'):
    if a.shape[axis]==1:return np.zeros_like(a)
    if boundary=='periodic':return (np.roll(a,-1,axis)-np.roll(a,1,axis))/(2*h)
    pads=[(0,0)]*a.ndim;pads[axis]=(1,1);p=np.pad(a,pads);s=[slice(None)]*a.ndim;t=s.copy();s[axis]=slice(2,None);t[axis]=slice(None,-2);return (p[tuple(s)]-p[tuple(t)])/(2*h)
def gradients(a,g):return np.stack([derivative(a,h,i,g.boundary) for i,h in enumerate(g.spacing)],-2)
def shifted(a,k,axis,boundary):
    if boundary=='periodic':return np.roll(a,-k,axis)
    pads=[(0,0)]*a.ndim;pads[axis]=(1,1);p=np.pad(a,pads);s=[slice(None)]*a.ndim;s[axis]=slice(1+k,1+k+a.shape[axis]);return p[tuple(s)]
def sigma_terms(n,g):
    u=n-NORTH;rho=np.zeros(g.shape);force=np.zeros_like(n)
    for i,(h,count) in enumerate(zip(g.spacing,g.shape)):
        if count==1:continue
        f=shifted(u,1,i,g.boundary);b=shifted(u,-1,i,g.boundary)
        rho+=.5*np.sum(((f-u)/h)**2+((u-b)/h)**2,-1);force+=(f-2*u+b)/h**2
    return rho,force
def sigma_rate(n,v,g):
    u=n-NORTH;rate=np.zeros(g.shape)
    for i,(h,count) in enumerate(zip(g.spacing,g.shape)):
        if count==1:continue
        f=shifted(u,1,i,g.boundary);b=shifted(u,-1,i,g.boundary);vf=shifted(v,1,i,g.boundary);vb=shifted(v,-1,i,g.boundary)
        rate+=np.sum((f-u)*(vf-v)+(u-b)*(v-vb),-1)/h**2
    return rate
def acceleration(n,v,g):
    # Match the declared sphere/tangent constraints, without reference currents.
    n=n/np.linalg.norm(n,axis=-1,keepdims=True);v=v-n*np.sum(n*v,-1,keepdims=True)
    if g.boundary=='fixed':mask=g.fixed_mask();n[mask]=NORTH;v[mask]=0
    d=gradients(n-NORTH,g);b=gradients(v,g);q=np.sum(d*d,axis=-1)
    mass=(1+np.sum(q,-1))[...,None,None]*np.eye(3)-np.einsum('...ia,...ib->...ab',d,d)
    mdot=2*np.sum(d*b,axis=(-2,-1))[...,None,None]*np.eye(3)-np.einsum('...ia,...ib->...ab',d,b)-np.einsum('...ia,...ib->...ab',b,d)
    rhs=sigma_terms(n,g)[1];vv=np.sum(v*v,-1)
    for i,h in enumerate(g.spacing):
        di=d[...,i,:];c=-vv[...,None]*di+np.sum(v*di,-1)[...,None]*v
        for j in range(3):
            if i!=j:c+=q[...,j,None]*di-np.sum(di*d[...,j,:],-1)[...,None]*d[...,j,:]
        rhs+=derivative(c,h,i,g.boundary)
    rhs-=np.einsum('...ab,...b->...a',mdot,v)
    sol=np.linalg.solve(mass,np.stack([rhs,n],-1));z,w=sol[...,0],sol[...,1];lam=(-np.sum(v*v,-1)-np.sum(n*z,-1))/np.sum(n*w,-1);a=z+lam[...,None]*w
    if g.boundary=='fixed':a[mask]=0
    return v,a
def densities(n,v,g):
    d=gradients(n-NORTH,g);kin=np.sum(v*v,-1);quartic=np.zeros(g.shape)
    for i in range(3):kin+=np.sum(np.cross(v,d[...,i,:])**2,-1)
    for i,j in [(0,1),(0,2),(1,2)]:quartic+=np.sum(np.cross(d[...,i,:],d[...,j,:])**2,-1)
    cont=K*(kin+np.sum(d*d,axis=(-2,-1))+quartic);ham=K*(kin+sigma_terms(n,g)[0]+quartic)
    mv=v.copy()
    for i in range(3):di=d[...,i,:];mv+=np.sum(di*di,-1)[...,None]*v-np.sum(v*di,-1)[...,None]*di
    flux=-2*K*np.sum(mv[...,None,:]*d,-1)
    return {'energy_density':cont,'hamiltonian_density':ham,'energy_flux':flux}
