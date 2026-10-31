"""Independent host validation of CUDA arithmetic and device-array solver port."""
import ctypes
from pathlib import Path
import subprocess
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.fft import dstn
from electron_field_topology.sf_gpu import quadrature, dst1n, minimize_array, diagnostics_array
from electron_field_topology.skyrme import (Energy, K, NORTH, normalize, numpy_cell_energy,
                                            rational_field, coordinates, set_boundary, diagnostics)
from electron_field_topology.sf_minimize import minimize_static


@pytest.fixture
def host_kernel(tmp_path):
    import electron_field_topology.sf_gpu as module
    source = Path(module.__file__).with_name("sf_energy_gpu.cu")
    libpath = tmp_path/"host.so"
    subprocess.run(["g++", "-x", "c++", "-std=c++11", "-O2", "-shared", "-fPIC",
                    "-DEFT_HOST_CHECK", str(source), "-o", str(libpath)], check=True)
    lib = ctypes.CDLL(str(libpath)); ptr = ctypes.POINTER(ctypes.c_double)
    fn = lib.sf_cell_color_host
    fn.argtypes = [ctypes.c_int, ctypes.c_double, ptr, ptr, ptr, ptr, ptr, ctypes.c_int]
    def evaluate(u, h):
        n = len(u); grad = np.zeros_like(u); metrics = np.zeros((4, (n-1)**3))
        shape, der = quadrature(); der /= h
        def pointer(a):
            return a.ctypes.data_as(ptr)
        for color in range(8):
            fn(n, h, pointer(u), pointer(grad), pointer(metrics), pointer(shape), pointer(der), color)
        return metrics[:2].sum(axis=1)*K*h**3, grad*K*h**3, metrics[2:].min(axis=1)
    return evaluate


@pytest.mark.parametrize("kind", ["constant", "random", "hopf", "antipodal"])
def test_exact_cuda_cell_function_host_execution_against_native_and_independent_energy(host_kernel, tmp_path, kind):
    n = 9; h = .3
    rng = np.random.default_rng(35)
    u = set_boundary(normalize(NORTH+.12*rng.normal(size=(n, n, n, 3))))
    if kind == "constant":
        u[:] = NORTH
    elif kind == "hopf":
        u = set_boundary(rational_field(coordinates(n, h), scale=.6, cutoff=1.))
    elif kind == "antipodal":
        u[:] = NORTH; u[4, 4, 4] = -NORTH
    parts, grad, minima = host_kernel(u, h)
    native = Energy(n, h, tmp_path/"native", method="cell")
    ref, gref = native.evaluate(u)
    np.testing.assert_allclose(parts, ref, rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(grad, gref, rtol=1e-11, atol=1e-13)
    np.testing.assert_allclose(minima, [native.minimum_interpolant_norm, native.minimum_corner_cone], atol=1e-14)
    np.testing.assert_allclose(parts, numpy_cell_energy(u, h), rtol=1e-12, atol=1e-14)
    if kind == "antipodal":
        assert minima[1] <= 0  # Unresolved corner cone must remain rejected.
    if kind == "random":
        v = np.zeros_like(u); v[2:-2, 2:-2, 2:-2] = rng.normal(size=(5, 5, 5, 3))
        v -= u*np.sum(u*v, axis=-1, keepdims=True); v /= np.linalg.norm(v)
        eps = 1e-4
        delta = (sum(numpy_cell_energy(normalize(u+eps*v), h))-
                 sum(numpy_cell_energy(normalize(u-eps*v), h)))/(2*eps)
        assert abs(delta-np.sum(grad*v)) < 1e-9


@pytest.mark.parametrize("shape", [(3, 4, 5), (5, 6, 7, 3), (13, 13, 13, 3)])
def test_fft_dst_matches_scipy_and_is_self_inverse(shape):
    a = np.random.default_rng(6).normal(size=shape)
    ref = dstn(a, axes=(0, 1, 2), type=1, norm="ortho")
    np.testing.assert_allclose(dst1n(a, np), ref, rtol=1e-12, atol=1e-13)
    np.testing.assert_allclose(dst1n(dst1n(a, np), np), a, rtol=1e-12, atol=1e-13)
    if len(shape) == 3:
        direct = a.copy()
        for axis in range(3):
            m = shape[axis]; k = np.arange(1, m+1)
            matrix = np.sqrt(2/(m+1))*np.sin(np.pi*k[:, None]*k[None, :]/(m+1))
            direct = np.moveaxis(np.tensordot(matrix, direct, axes=(1, axis)), 0, axis)
        np.testing.assert_allclose(dst1n(a, np), direct, atol=1e-13)


def test_array_solver_and_diagnostics_against_existing_cpu_implementation(tmp_path):
    h = .2; u = set_boundary(rational_field(coordinates(17, h), scale=.6, cutoff=1.3))
    a, sa = minimize_static(Energy(17, h, tmp_path/"a"), u, 5, lambda f, i: None, lambda: False)
    b, sb = minimize_array(Energy(17, h, tmp_path/"b"), u, 5, lambda f, i: None, lambda: False, np)
    assert sa == sb
    np.testing.assert_allclose(a, b, rtol=1e-11, atol=1e-12)
    da, db = diagnostics(a, h), diagnostics_array(a, h, np)
    for key in ("hopf_integral", "unit_error", "max_neighbour_angle", "mean_topological_b"):
        np.testing.assert_allclose(da[key], db[key], rtol=1e-12, atol=1e-13)


def test_cuda_device_validation_when_available(tmp_path):
    try:
        import cupy as cp
        if cp.cuda.runtime.getDeviceCount() == 0:
            pytest.skip("No CUDA GPU: device execution not tested")
    except (ImportError, RuntimeError):
        pytest.skip("No accessible CUDA GPU: device execution not tested")
    from electron_field_topology.sf_gpu_timing import validate_device
    assert validate_device(cp, tmp_path)["passed"]


def test_paired_harness_protocol_with_explicit_numpy_test_double(tmp_path, monkeypatch):
    """Exercise orchestration only; this test double supplies no GPU evidence."""
    from electron_field_topology import sf_gpu, sf_gpu_timing
    class ArrayTestDouble:
        def __getattr__(self, name):
            return getattr(np, name)
        asnumpy = staticmethod(np.asarray)
        cuda = SimpleNamespace(get_current_stream=lambda: SimpleNamespace(synchronize=lambda: None))
        get_default_memory_pool = staticmethod(lambda: SimpleNamespace(total_bytes=lambda: 0, used_bytes=lambda: 0))
    def cpu_engine(n, h, block_size=128):
        return Energy(n, h, tmp_path/"test-double")
    monkeypatch.setattr(sf_gpu, "GPUEnergy", cpu_engine)
    xp = ArrayTestDouble()
    assert sf_gpu_timing.validate_device(xp, tmp_path/"checks")["passed"]
    args = SimpleNamespace(case="q1", cpu_threads=1, steps=1, repeats=1, label="test", block_size=128)
    row = sf_gpu_timing.run_grid(args, 33, tmp_path, xp)
    assert row["validation"]["passed"]
    assert row["gpu"]["short_solve"]["results"] == row["cpu"]["short_solve"]["results"]


def test_missing_gpu_aborts_and_retains_error_without_fallback(tmp_path, monkeypatch):
    import json
    import sys
    from electron_field_topology import sf_gpu, sf_gpu_timing
    def missing():
        raise RuntimeError("No CUDA device: test control")
    monkeypatch.setattr(sf_gpu, "cupy_module", missing)
    out = tmp_path/"no-gpu"
    monkeypatch.setattr(sys, "argv", ["sf_gpu_timing", "--output", str(out)])
    with pytest.raises(RuntimeError, match="No CUDA device"):
        sf_gpu_timing.main()
    result = json.loads((out/"timing.json").read_text())
    assert result["error"]["type"] == "RuntimeError" and result["cases"] == []
