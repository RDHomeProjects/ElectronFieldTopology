"""Reproduce report algebra; not a field solver or physical-model acceptance.

Created 2026-11-01 UTC; every execution records UTC and Melbourne timestamps.
Uses only the repository's existing locked development dependencies.
Software: Apache-2.0. Source equations and scope: README.md in this directory.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
from zoneinfo import ZoneInfo

import numpy as np
import scipy
from scipy.integrate import quad
from scipy.linalg import eigvalsh
import sympy as s


def timestamp():
    now = datetime.now(timezone.utc)
    return {"utc": now.isoformat(), "melbourne": now.astimezone(ZoneInfo("Australia/Melbourne")).isoformat()}


def verify():
    started = timestamp()
    checks = []

    def record(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail, "checked_at": timestamp()})
        if not passed:
            raise ArithmeticError(name + ": " + str(detail))

    def zero(name, expr):
        values = list(expr) if isinstance(expr, s.MatrixBase) else [expr]
        reduced = [s.simplify(v) for v in values]
        record(name, all(v == 0 for v in reduced), [str(v) for v in reduced])

    r = s.symbols("rho", positive=True)
    u = 1 / s.sqrt(1+r*r)
    # Euler-Lagrange of our dimensionless radial functional, m=3.
    zero("m3_radial_equation", s.diff(u, r, 2) + u*(1-u*u)/r**2 - 3*r*r*u**5)
    densities = [s.diff(u, r)**2, (1-u*u)**2/(2*r*r), r*r*u**6]
    expected = [s.pi/16, s.pi/8, s.pi/16]
    numeric_integrals = []
    for name, density, exact in zip(("profile_gradient", "angular_curvature", "potential"), densities, expected):
        zero("integral_"+name, s.integrate(density, (r, 0, s.oo))-exact)
        value, estimate = quad(s.lambdify(r, density, "numpy"), 0, np.inf, epsabs=1e-12, epsrel=1e-12)
        error = abs(value-float(exact))
        record("quadrature_"+name, error < 1e-11, {"value": value, "absolute_error": error, "quad_error_estimate": estimate})
        numeric_integrals.append(value)
    zero("total_energy_pi_over_four", sum(expected)-s.pi/4)
    zero("derrick_E4_equals_3E0", expected[0]+expected[1]-3*expected[2])
    lam = s.symbols("lambda", positive=True)
    dilation = (expected[0]+expected[1])/lam + expected[2]*lam**3
    zero("dilation_stationarity", s.diff(dilation, lam).subs(lam, 1))
    zero("dilation_second_derivative", s.diff(dilation, lam, 2).subs(lam, 1)-3*s.pi/4)
    # Vibration operator obtained from our radial energy, with n fixed.
    W = s.simplify((-1+3*u*u)/r**2 + 15*r*r*u**4)
    numerator = 2+r*r+14*r**4
    zero("radial_second_variation_W", W-numerator/(r*r*(1+r*r)**2))
    record("radial_second_variation_positive", s.Poly(numerator, r).all_coeffs() == [14, 0, 1, 0, 2],
           {"W": str(W), "domain": "rho>0; fixed boundary, fixed n", "not_full_stability": True})
    # Check the apparent factor-two discrepancy in 0812.4225v1, Eqs.20/21.
    v20 = (1+3*(1-r*r)/(1+r*r))/(4*r*r) + s.Rational(15,2)*r*r/(1+r*r)**2
    v21_printed = numerator/(r*r*(1+r*r)**2)
    zero("vibration_eq20_is_half_W", 2*v20-W)
    zero("vibration_printed_eq21_is_twice_eq20", v21_printed-2*v20)
    # Full hedgehog Q is regular even though n=rhat is not at r=0.
    x, y, z = s.symbols("x y z", real=True)
    r0 = s.symbols("r0", positive=True)
    denom = s.sqrt(x*x+y*y+z*z+r0*r0)
    zero("hedgehog_unit_quaternion", (r0/denom)**2+sum((v/denom)**2 for v in (x,y,z))-1)
    # A provisional Abelian core projection: not a unique physical observable.
    enc = -r*r/(1+r*r)
    density = -1/(2*s.pi*r*(1+r*r)**2)
    zero("projected_core_gauss_balance", s.diff(enc, r)-4*s.pi*r*r*density)
    zero("projected_core_total_charge_in_units_e0", s.integrate(4*s.pi*r*r*density, (r,0,s.oo))+1)
    th, ph = s.symbols("theta phi", real=True)
    n = s.Matrix([s.sin(th)*s.cos(ph), s.sin(th)*s.sin(ph), s.cos(th)])
    sphere = s.simplify(n.dot(n.diff(th).cross(n.diff(ph))))
    zero("oriented_unit_sphere_degree", s.integrate(sphere, (ph,0,2*s.pi), (th,0,s.pi))/(4*s.pi)-1)
    # Explicit ordinary source-free Maxwell fields outside the pointwise n-map.
    t, k, c, a, b = s.symbols("t k c a b", real=True, nonzero=True)
    f, g = s.cos(k*(z-c*t)), s.cos(k*(z+c*t))
    E, B = s.Matrix([a*f,b*g,0]), s.Matrix([b*g/c,a*f/c,0])
    coords = (x,y,z)
    def div(v): return sum(s.diff(v[i],coords[i]) for i in range(3))
    def curl(v): return s.Matrix([s.diff(v[2],y)-s.diff(v[1],z), s.diff(v[0],z)-s.diff(v[2],x), s.diff(v[1],x)-s.diff(v[0],y)])
    zero("maxwell_counterexample_div_E", div(E))
    zero("maxwell_counterexample_div_B", div(B))
    zero("maxwell_counterexample_faraday", curl(E)+B.diff(t))
    zero("maxwell_counterexample_ampere", E.diff(t)-c*c*curl(B))
    zero("maxwell_counterexample_dot_formula", E.dot(B)-2*a*b*f*g/c)
    record("maxwell_counterexample_nonzero_dot", E.dot(B).subs({t:0,z:0,a:1,b:1,c:1}) == 2, "E.B=2 at the selected dimensionless event; this is not an experiment")
    # Pullback area form H=dA wedge dB is decomposable, independent of dynamics.
    A, D = s.symbols("A0:4"), s.symbols("D0:4")
    H = lambda i,j: A[i]*D[j]-A[j]*D[i]
    zero("pullback_area_pfaffian", H(0,1)*H(2,3)-H(0,2)*H(1,3)+H(0,3)*H(1,2))
    # Frozen static principal symbol, generic spatial first derivatives.
    I = s.eye(3)
    gs = [s.Matrix(s.symbols(f"g{i}_0:3")) for i in range(3)]
    ks = s.symbols("k0:3")
    av = s.Matrix(s.symbols("a0:3"))
    w = s.symbols("omega")  # omega here means physical omega/c.
    N = lambda v: v.dot(v)*I-v*v.T
    M = sum((N(v) for v in gs), s.zeros(3))
    bv = sum((ks[i]*gs[i] for i in range(3)), s.zeros(3,1))
    qform = sum((w*av.cross(v)).dot(w*av.cross(v)) for v in gs)
    qform -= sum((ks[i]*av.cross(gs[j])-ks[j]*av.cross(gs[i])).dot(ks[i]*av.cross(gs[j])-ks[j]*av.cross(gs[i])) for i in range(3) for j in range(i+1,3))
    proposed = (w*w-sum(ki*ki for ki in ks))*M+N(bv)
    zero("generic_static_principal_symbol", s.hessian(qform, list(av))/2-proposed)
    zero("isotropic_static_symbol", proposed.subs(dict(zip(sum((list(v) for v in gs), []), [1,0,0,0,1,0,0,0,1]))).subs(dict(zip(ks,[0,0,1])))-s.diag(2*w*w-1,2*w*w-1,2*w*w-2))
    record("constant_vacuum_kinetic_hessian_zero", M.subs({v:0 for vec in gs for v in vec}) == s.zeros(3), "No quadratic derivative action about a constant vacuum")
    # Differentiate the FULL quartic density in a time-dependent local jet.
    h, gg, eps = s.symbols("h g epsilon", real=True)
    xi = [w,0,0,1]
    background = [s.Matrix([0,0,h]), s.Matrix([gg,0,0]), s.Matrix([0,gg,0]), s.zeros(3,1)]
    perturbed = [background[i]+eps*xi[i]*av for i in range(4)]
    quartic = sum(perturbed[0].cross(perturbed[i]).dot(perturbed[0].cross(perturbed[i])) for i in range(1,4))/2
    quartic -= sum(perturbed[i].cross(perturbed[j]).dot(perturbed[i].cross(perturbed[j])) for i in range(1,4) for j in range(i+1,4))/2
    full_second = s.diff(quartic,eps,2).subs(eps,0)
    jet_symbol = s.simplify(s.hessian(full_second,list(av))/2)
    zero("time_dependent_local_jet_symbol", jet_symbol-s.diag(gg**2*(w*w-1)+h*h, gg**2*(w*w-1)+h*h,2*gg**2*(w*w-1)))
    record("local_jet_negative_speed_squared", s.simplify(1-h*h/(gg*gg)).subs({h:2,gg:1}) == -3,
           {"squared_speeds_over_c2": [-3,-3,1], "scope": "allowed first jet; not a constructed global on-shell solution or observed instability"})
    rng = np.random.default_rng(20261101)
    extremes = [1.,0.]
    for _ in range(128):
        G = rng.normal(size=(3,3))
        direction = rng.normal(size=3); direction /= np.linalg.norm(direction)
        m = sum((np.dot(v,v)*np.eye(3)-np.outer(v,v) for v in G), np.zeros((3,3)))
        bnum = direction@G
        Bnum = m-(np.dot(bnum,bnum)*np.eye(3)-np.outer(bnum,bnum))
        vals = eigvalsh(Bnum,m)
        extremes = [min(extremes[0],float(vals.min())),max(extremes[1],float(vals.max()))]
    record("static_numeric_crosscheck_128", extremes[0] >= -1e-12 and extremes[1] <= 1+1e-12,
           {"min_squared_speed_over_c2":extremes[0],"max_squared_speed_over_c2":extremes[1],"seed":20261101,"proof":False})
    result = {"started_at":started,"completed_at":timestamp(),"disposition":"analytic_audit_complete; charged_dynamics_deferred; additional_Q_followup_required",
              "scope":"symbolic identities, one-dimensional quadrature and local principal-symbol crosschecks; no GPU or field evolution",
              "environment":{"python":platform.python_version(),"sympy":s.__version__,"numpy":np.__version__,"scipy":scipy.__version__},
              "provenance":{"base_commit":"42376b46fb52771a7d22138c29689d519c290619","verification_script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
              "checks":checks,"passed":len(checks),"failed":0,
              "energy":{"dimensionless_total":sum(numeric_integrals),"exact":"pi/4","illustrative_r0_fm_from_rounded_source_inputs":float(1.44*s.pi/(4*.511))},
              "not_established":["general Maxwell equivalence","full constrained strong hyperbolicity","full nonradial stability","unique finite-core electromagnetic observable","electron identification","new Q simulations"]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write a new dated ledger; otherwise only print summary")
    args = parser.parse_args()
    result = verify()
    if args.output:
        if args.output.exists():
            raise FileExistsError("Retain existing evidence; choose a new output path: "+str(args.output))
        args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:result[key] for key in ("started_at","completed_at","disposition","passed","failed","energy")},indent=2))


if __name__ == "__main__":
    main()
