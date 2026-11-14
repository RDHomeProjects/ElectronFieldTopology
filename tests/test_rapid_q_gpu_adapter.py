"""Independent CPU controls for the bundled D4 adapter; host tests, not CUDA."""
import numpy as np
from electron_field_topology import sf_time as cpu
from electron_field_topology.sf_readmission import static_value_gradient
from electron_field_topology.sf_time_gpu import ArrayTime


def test_bundled_adapter_matches_cpu_on_declared_control_geometries():
    grids = [cpu.Grid((9,11,13),(4.,5.,7.),'fixed'),
             cpu.Grid((7,8,9),(4.,5.,7.),'periodic'),
             cpu.Grid((17,1,1),(8.,1.,1.),'fixed'),
             cpu.Grid((1,1,1),(2.,2.,2.),'periodic')]
    for grid in grids:
        x,y,z=np.moveaxis(grid.points(),-1,0)
        a=.16*np.sin(.7*x+.3*y)*np.cos(.4*z)
        b=.11*np.cos(.3*x-.6*y+.2*z)
        n=np.stack((a,b,np.sqrt(1-a*a-b*b)),axis=-1)
        v=np.stack((.03*np.cos(x),.02*np.sin(y+z),np.zeros_like(x)),axis=-1)
        n,v=cpu.retract(n,v,grid);port=ArrayTime(np)
        for name in ['gradients','sigma_terms']:
            actual=getattr(port,name)(n,grid);expected=getattr(cpu,name)(n,grid)
            pairs=zip(actual,expected) if isinstance(actual,tuple) else [(actual,expected)]
            for actual,expected in pairs:np.testing.assert_allclose(actual,expected,rtol=1e-13,atol=1e-13)
        for actual,expected in zip(port.static_value_gradient(n,grid),static_value_gradient(n,grid)):
            np.testing.assert_allclose(actual,expected,rtol=1e-13,atol=1e-13)
        for actual,expected in zip(port.acceleration(n,v,grid),cpu.acceleration(n,v,grid)):
            np.testing.assert_allclose(actual,expected,rtol=1e-13,atol=1e-13)
        for name,expected in cpu.densities(n,v,grid).items():
            np.testing.assert_allclose(port.densities(n,v,grid)[name],expected,rtol=1e-13,atol=1e-13)
        nn,vv=n.copy(),v.copy()
        for k in range(4):
            n,v,_=cpu.step(n,v,grid,.002,k*.002)
            nn,vv,_=port.step(nn,vv,grid,.002,k*.002)
        np.testing.assert_allclose(nn,n,rtol=1e-13,atol=1e-13)
        np.testing.assert_allclose(vv,v,rtol=1e-13,atol=1e-13)
        assert port.execution_kind=='numpy-test-double'


def test_bundled_adapter_rejects_float32_upload():
    port=ArrayTime(np);n=np.zeros((3,3,3,3),dtype=np.float32)
    try:port.upload(n,n)
    except ValueError as e:assert 'Float64' in str(e)
    else:raise AssertionError('Float32 upload was accepted')
